# -*- coding: utf-8 -*-
"""
v3.0/gl_visualizer.py
PyQt6 QOpenGLWidget を用いた GPU ハードウェアアクセラレーション描画エンジン。
- 3段階 / 2段階 / 垂直落下 軌道モード対応
- 四つ角面取り（チャンファー）付き幾何学ポリゴン描画
- 半音ノーツの装飾（スリット2分割 / サイドライン明暗適応 / センター芯線 / なし）完全対応
- ハーモニカ本体 90px高3Dプレート ＆ 丸穴（直径30px）＆ 内側穴番号 (+24px)
- 穴下の音名表示：「4音グリッド表示（田の字・発音セル点灯）」＆「1音表示 (従来)」完全対応
- 連動レバーリング (use_ring) ＆ 着地発光 (is_glow_on)
- 静的レイヤー (背景・本体・穴番号・4音グリッド・凡例) の GPU QPixmap テクスチャキャッシュ
- 60〜144FPS V-Sync 完全同期 ＆ マウスホイールコマ送りスクラブ
"""

import os
import bisect
import time
import math
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QRect, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage, QTransform,
    QPolygonF, QFontMetricsF, QRadialGradient
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from config import (
    CANVAS_WIDTH, W_PITCH, D_HOLE,
    get_canvas_height_by_ratio, get_y_trajectory_params,
    get_layout_params, get_lever_highlight_color, get_portable_path,
    format_hole_number
)
from harmonica_map import (
    is_note_in_range, get_note_name, get_hole_4_notes, BLOW_NOTES_MIDI
)


def _calc_trajectory_x(yv, lane_l, lane_r, dest_l, dest_r, y_col, y_str, h_diag):
    """斜め収束軌道のX座標計算"""
    if yv >= y_str or h_diag <= 0:
        return dest_l, dest_r, (dest_l + dest_r) * 0.5
    if yv <= y_col:
        return lane_l, lane_r, (lane_l + lane_r) * 0.5
    ratio = (yv - y_col) / h_diag
    xl = lane_l + (dest_l - lane_l) * ratio
    xr = lane_r + (dest_r - lane_r) * ratio
    return xl, xr, (xl + xr) * 0.5


def _draw_bordered_text_qt(painter, rect: QRectF, text: str, font: QFont,
                           text_color: QColor, border_color: QColor = QColor("#000000"),
                           border_w: float = 1.5, alignment=Qt.AlignmentFlag.AlignCenter):
    """黒フチ付きテキストを描画して可読性を極限まで高めるヘルパー"""
    painter.setFont(font)
    painter.setPen(border_color)
    bw = max(1.0, border_w)
    for dx in (-bw, bw):
        for dy in (-bw, bw):
            painter.drawText(rect.translated(dx, dy), alignment, text)
    painter.drawText(rect.translated(0, -bw), alignment, text)
    painter.drawText(rect.translated(0, bw), alignment, text)
    painter.drawText(rect.translated(-bw, 0), alignment, text)
    painter.drawText(rect.translated(bw, 0), alignment, text)
    painter.setPen(text_color)
    painter.drawText(rect, alignment, text)


class HarmonicaGLWidget(QOpenGLWidget):
    """OpenGLハードウェアアクセラレーションによる超高速・高精度ビジュアライザー描画Widget"""

    seek_step_requested = pyqtSignal(int, int)  # (steps, modifier_flags)
    note_mute_changed = pyqtSignal()

    def __init__(self, clock_bridge, parent=None):
        super().__init__(parent)
        self.clock = clock_bridge

        # 描画設定パラメータ
        self.inst_type = "16穴 (64音・C調)"
        self.aspect_ratio = "16:9"
        self.trajectory_mode = "3段階 (練習標準)"
        self.lever_deco_mode = "センターライン (芯線)"
        self.lang_mode = "ドレミ"
        self.note_speed_ratio = 1.0
        self.default_bpm = 120.0
        self.show_notes = True
        self.show_grid = True
        self.show_bar_lines = True
        self.show_grid4 = "4音グリッド表示"  # "4音グリッド表示" or "1音表示 (従来)"
        self.show_hole_num = True
        self.hole_num_style = "実機標準 (低音ドット付)"
        self.show_legend = True
        self.show_lookahead = True
        self.use_ring = True          # レバーリング連動
        self.is_glow_on = True        # 着地発光
        self.note_opacity = 100
        self.loop_enabled = False
        self.loop_a_sec = 0.0
        self.loop_b_sec = None

        # 背景画像パラメータ
        self.bg_image_enabled = True
        self.bg_image_path = ""
        self.bg_dim_ratio = 60
        self.bg_fit_mode = "中央トリミング (画面いっぱい)"
        self.bg_rotation = 0
        self._cached_bg_path = ""
        self._cached_bg_image = None

        # スキン装飾パラメータ
        self.skin_enabled = True
        self.skin_mouthpiece_path = ""
        self.skin_lever_off_path = ""
        self.skin_lever_on_path = ""
        self._pix_mouthpiece = None
        self._pix_lever_off = None
        self._pix_lever_on = None
        self._load_skins()

        # カラー定義
        self.color_bg = QColor("#0d0d0d")
        self.color_blow = QColor("#FF9900")
        self.color_draw = QColor("#00FFFF")
        self.color_blow_hi = QColor(get_lever_highlight_color("#FF9900"))
        self.color_draw_hi = QColor(get_lever_highlight_color("#00FFFF"))
        self.color_led_off = QColor("#080808")
        self.color_measure_line = QColor("#3a3a3a")
        self.color_measure_text = QColor("#777777")
        self.color_grid_line = QColor(255, 255, 255, 24)
        self.color_white = QColor("#FFFFFF")
        self.color_black = QColor("#000000")

        # 事前アロケーション済ペン・ブラシ・フォント
        self.pen_none = QPen(Qt.PenStyle.NoPen)
        self.pen_measure = QPen(self.color_measure_line, 1.0)
        self.pen_center_blow = QPen(self.color_blow_hi, 2.0)
        self.pen_center_draw = QPen(self.color_draw_hi, 2.0)
        self.pen_center_blow.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.pen_center_draw.setCapStyle(Qt.PenCapStyle.RoundCap)

        self.font_hole = QFont("Arial", 11, QFont.Weight.Bold)
        self.font_note = QFont("Meiryo UI", 9, QFont.Weight.Bold)
        self.font_grid4 = QFont("Meiryo UI", 8, QFont.Weight.Bold)
        self.font_measure = QFont("Arial", 9, QFont.Weight.Bold)

        # 運指エディタ & インタラクティブ変更モード
        self.timeline = None
        self.fingering_edit_mode = False
        self.mute_edit_mode = False
        self.hide_muted_notes = False
        self.on_fingering_changed_callback = None
        self.toast_msg = ""
        self.toast_expire = 0.0

        # タイムラインデータ
        self.midi_notes = []
        self.note_start_secs = []
        self.max_note_dur_sec = 5.0
        self.measures = []
        self.measure_start_secs = []

        # 静的背景QPixmapキャッシュ
        self._static_pixmap = None
        self._static_dirty = True
        self._cached_wh_scale = None

        # FPS測定
        self._fps_count = 0
        self._fps_last_time = time.perf_counter()
        self._current_fps = 0.0

        # V-Sync連動フレーム更新タイマー
        self._frame_timer = QTimer(self)
        self._frame_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._frame_timer.timeout.connect(self.update)
        self._frame_timer.start(8)  # 実ディスプレイV-Syncへ自動同期

    def get_fps(self) -> float:
        """現在の実測レンダリングFPSを返却"""
        return self._current_fps

    def set_aspect_ratio(self, ratio: str):
        self.aspect_ratio = str(ratio)
        self.invalidate_static_cache()

    def set_trajectory_mode(self, mode: str):
        self.trajectory_mode = str(mode)
        self.invalidate_static_cache()

    def set_lang_mode(self, mode: str):
        self.lang_mode = str(mode)
        self.invalidate_static_cache()

    def set_note_speed_ratio(self, ratio: float):
        self.note_speed_ratio = max(0.1, float(ratio))
        self.update()

    def set_default_bpm(self, bpm: float):
        self.default_bpm = max(10.0, float(bpm))
        self.update()

    def set_show_grid(self, show: bool):
        self.show_grid = bool(show)
        self.invalidate_static_cache()

    def set_show_bar_lines(self, show: bool):
        self.show_bar_lines = bool(show)
        self.update()

    def set_show_grid4(self, val):
        """穴下の音名 ('4音グリッド表示' or '1音表示 (従来)')"""
        if isinstance(val, bool):
            self.show_grid4 = "4音グリッド表示" if val else "1音表示 (従来)"
        else:
            self.show_grid4 = str(val)
        self.invalidate_static_cache()

    def set_show_hole_num(self, show: bool):
        self.show_hole_num = bool(show)
        self.invalidate_static_cache()

    def set_hole_num_style(self, style: str):
        self.hole_num_style = str(style)
        self.invalidate_static_cache()

    def set_show_legend(self, show: bool):
        self.show_legend = bool(show)
        self.invalidate_static_cache()

    def set_show_notes(self, show: bool):
        self.show_notes = bool(show)
        self.update()

    def set_show_lookahead(self, show: bool):
        self.show_lookahead = bool(show)
        self.update()

    def set_use_ring(self, enabled: bool):
        """レバーリング連動ON/OFF"""
        self.use_ring = bool(enabled)
        self.update()

    def set_show_glow(self, enabled: bool):
        """着地発光ON/OFF"""
        self.is_glow_on = bool(enabled)
        self.update()

    def set_theme_colors(self, blow_hex: str, draw_hex: str):
        """カラーテーマ (吹音・吸音) 設定"""
        self.color_blow = QColor(blow_hex)
        self.color_draw = QColor(draw_hex)
        self.color_blow_hi = QColor(get_lever_highlight_color(blow_hex))
        self.color_draw_hi = QColor(get_lever_highlight_color(draw_hex))
        self.pen_center_blow = QPen(self.color_blow_hi, 2.0)
        self.pen_center_draw = QPen(self.color_draw_hi, 2.0)
        self.pen_center_blow.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.pen_center_draw.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.invalidate_static_cache()

    def set_lever_deco_mode(self, mode: str):
        """半音ノーツ装飾 (センターライン (芯線) / センター半割 (スリット) / サイドライン (明暗適応) / 装飾なし)"""
        self.lever_deco_mode = str(mode)
        self.update()

    def set_note_opacity(self, opacity: int):
        """ノーツ不透過度 (20% 〜 100%)"""
        self.note_opacity = max(20, min(100, int(opacity)))
        self.update()

    def set_fingering_edit_mode(self, enabled: bool):
        """運指変更モード (クリック循環) の有効/無効切替"""
        self.fingering_edit_mode = bool(enabled)
        active = bool(enabled or getattr(self, "mute_edit_mode", False))
        self.setMouseTracking(active)
        if not active:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_mute_edit_mode(self, enabled: bool):
        """ノーツ除外・非表示モードの有効/無効切替"""
        self.mute_edit_mode = bool(enabled)
        active = bool(enabled or getattr(self, "fingering_edit_mode", False))
        self.setMouseTracking(active)
        if not active:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def show_toast(self, msg: str, duration: float = 2.5):
        """画面中央にフローティングトーストHUDを一時表示"""
        self.toast_msg = str(msg)
        self.toast_expire = time.time() + duration
        self.update()

    def wheelEvent(self, event):
        """キャンバス上でのマウスホイール操作による前後スクラブ"""
        delta = event.angleDelta().y()
        if not delta:
            return
        notches = int(delta / 120) if abs(delta) >= 120 else (1 if delta > 0 else -1)
        steps = -notches  # 手前回転で時間進む、奥回転で巻き戻る
        modifiers = int(event.modifiers().value)
        self.seek_step_requested.emit(steps, modifiers)
        event.accept()

    def set_hide_muted_notes(self, hide: bool):
        """除外ノーツ完全非表示フラグ設定"""
        self.hide_muted_notes = bool(hide)
        self.update()

    def _hit_test_note(self, cx: float, cy: float, editable_only: bool = False) -> dict:
        """指定座標 (cx, cy) に存在するノーツを逆算ヒットテスト"""
        if not getattr(self, "show_notes", True) or not self.midi_notes:
            return None

        w = self.width()
        h = self.height()
        base_h = float(get_canvas_height_by_ratio(self.aspect_ratio))
        scale = min(w / float(CANVAS_WIDTH), h / base_h)
        x_offset = (w - CANVAS_WIDTH * scale) * 0.5
        y_offset = (h - base_h * scale) * 0.5

        cur_sec = self.clock.get_current_base_sec(lookahead_sec=0.008)
        px_per_sec = 2.0 * getattr(self, "default_bpm", 120.0) * self.note_speed_ratio * scale
        if px_per_sec <= 0:
            return None

        y_center, y_col, y_str, y_hole, h_diag, h_str = get_y_trajectory_params(base_h, self.trajectory_mode)
        visible_indices, x_start_base, x_shift, x_shift_notes = get_layout_params(self.inst_type, 1.0)
        y_col_s = y_offset + y_col * scale
        y_str_s = y_offset + y_str * scale
        y_hole_s = y_offset + y_hole * scale
        h_diag_s = h_diag * scale
        is_straight_mode = ("垂直落下" in str(self.trajectory_mode))

        idx_start = bisect.bisect_left(self.note_start_secs, cur_sec - self.max_note_dur_sec)
        for i in range(len(self.midi_notes) - 1, idx_start - 1, -1):
            nd = self.midi_notes[i]
            if editable_only and (not nd.get("is_editable", False) or nd.get("is_muted", False)):
                continue
            if getattr(self, "hide_muted_notes", False) and not getattr(self, "mute_edit_mode", False) and nd.get("is_muted", False):
                continue
            n_start = nd["start_sec"]
            n_end = nd["end_sec"]
            y_bot = y_hole_s - (n_start - cur_sec) * px_per_sec
            y_top = y_hole_s - (n_end - cur_sec) * px_per_sec

            note_in_range = nd.get("in_range", True)
            if is_straight_mode and not note_in_range:
                continue
            y_limit_bot = y_hole_s if note_in_range else y_col_s
            y_vis_top = max(y_offset, y_top)
            y_vis_bot = min(y_limit_bot, y_bot)

            if y_vis_bot <= y_vis_top:
                continue

            if (y_vis_top - 4) <= cy <= (y_vis_bot + 4):
                dest_cx = x_offset + nd["dest_x_base"] * scale
                dest_l = dest_cx - 6.0 * scale
                dest_r = dest_cx + 6.0 * scale

                note_val = nd["note"]
                simulated_note = note_val + 36 if "バス" in self.inst_type else note_val
                lane_idx = simulated_note - 48
                lane_l = x_offset + (72 + lane_idx * 16) * scale - (x_shift_notes * scale)
                lane_r = lane_l + 16.0 * scale

                if is_straight_mode:
                    xl = dest_l
                    xr = dest_r
                else:
                    xl, xr, _ = _calc_trajectory_x(cy, lane_l, lane_r, dest_l, dest_r, y_col_s, y_str_s, h_diag_s)

                margin = max(4.0, 5.0 * scale)
                if (xl - margin) <= cx <= (xr + margin):
                    return nd

        return None

    def _hit_test_editable_note(self, cx: float, cy: float) -> dict:
        """指定座標 (cx, cy) に存在する変更可能ノーツを逆算ヒットテスト"""
        return self._hit_test_note(cx, cy, editable_only=True)

    def _toggle_note_mute(self, nd: dict):
        """ノーツの発音/除外 (Mute) 状態を反転 (Shift+右クリック)"""
        start_sec = nd["start_sec"]
        raw_pitch = nd.get("raw_note", nd["note"])
        key = f"{round(start_sec, 3)}_{raw_pitch}"
        new_muted = not nd.get("is_muted", False)
        from harmonica_map import SONG_MUTED_NOTES, save_song_profile
        SONG_MUTED_NOTES[key] = new_muted

        # 単音化モード（高音優先/低音優先）設定時のみ、有効化した際に同タイミングの重複ノーツを自動除外 (シーソー動作)
        mono_mode = getattr(self.timeline, "monophonic_mode", "すべて有効") if self.timeline else "すべて有効"
        if not new_muted and mono_mode != "すべて有効":
            for other_nd in (self.midi_notes or []):
                if other_nd is not nd and not other_nd.get("is_muted", False):
                    overlap = min(nd["end_sec"], other_nd["end_sec"]) - max(nd["start_sec"], other_nd["start_sec"])
                    if overlap >= 0.03:
                        other_raw_pitch = other_nd.get("raw_note", other_nd["note"])
                        other_key = f"{round(other_nd['start_sec'], 3)}_{other_raw_pitch}"
                        SONG_MUTED_NOTES[other_key] = True

        if self.timeline and self.timeline.filepath:
            save_song_profile(self.timeline.filepath)

        if self.timeline:
            self.timeline.rebind_fingerings(self.inst_type)

        self.invalidate_static_cache()
        self.update()
        self.note_mute_changed.emit()

        note_name = nd.get("name_jp", "") if self.lang_mode == "ドレミ" else nd.get("name_cde", "")
        if new_muted:
            self.show_toast(f"🔇 ノーツ非表示: {note_name} を除外しました")
        else:
            self.show_toast(f"🔔 ノーツ復帰: {note_name} を演奏対象に設定しました")

    def _cycle_note_fingering(self, nd: dict):
        """ノーツの変え指候補を循環し、即座に保存・再バインド・HUD通知"""
        pitch = nd["note"]
        start_tick = nd["start_tick"]
        lookup_note = pitch + 36 if "バス" in self.inst_type else pitch

        from harmonica_map import (
            FINGERING_CANDIDATES,
            SONG_FINGERING_OVERRIDES,
            save_song_fingering
        )

        if lookup_note not in FINGERING_CANDIDATES:
            return

        candidates = FINGERING_CANDIDATES[lookup_note]
        cur_override = SONG_FINGERING_OVERRIDES.get((start_tick, lookup_note))
        if cur_override is not None and 0 <= cur_override < len(candidates):
            cur_idx = cur_override
        else:
            cur_idx = 0
            f_hole = nd.get("hole", 1)
            f_act = nd.get("action", "吹")
            f_lev = nd.get("lever", "OFF")
            for c_i, cand in enumerate(candidates):
                if cand["hole"] == f_hole and cand["action"] == f_act and cand["lever"] == f_lev:
                    cur_idx = c_i
                    break

        next_idx = (cur_idx + 1) % len(candidates)
        SONG_FINGERING_OVERRIDES[(start_tick, lookup_note)] = next_idx

        if self.timeline and self.timeline.filepath:
            save_song_fingering(self.timeline.filepath)

        if self.timeline:
            self.timeline.rebind_fingerings(self.inst_type)

        new_cand = candidates[next_idx]
        nd["fingering"] = new_cand
        nd["hole"] = new_cand["hole"]
        nd["action"] = new_cand["action"]
        nd["lever"] = new_cand["lever"]
        nd["is_lever_on"] = (new_cand["lever"] == "ON")

        self.invalidate_static_cache()
        self.update()

        note_name = nd.get("name_jp", "") if self.lang_mode == "ドレミ" else nd.get("name_cde", "")
        cand_str = f"{new_cand['hole']}穴 {new_cand['action']} {new_cand['lever']}"
        self.show_toast(f"⟳ 運指切替: {note_name} → {cand_str}")

        if self.on_fingering_changed_callback:
            self.on_fingering_changed_callback(nd, new_cand)

    def mousePressEvent(self, event):
        """キャンバスクリック時のノーツ除外・循環・除外トグル処理"""
        pos = event.position()
        btn = event.button()
        mods = event.modifiers()

        # 1. ノーツ除外・非表示モード時: 左クリックで直接発音/除外 (Mute) トグル
        if btn == Qt.MouseButton.LeftButton and getattr(self, "mute_edit_mode", False):
            hit_note = self._hit_test_note(pos.x(), pos.y(), editable_only=False)
            if hit_note is not None:
                self._toggle_note_mute(hit_note)
                event.accept()
                return

        # 2. かえ指編集モード時: 左クリックで直接変え指循環
        if btn == Qt.MouseButton.LeftButton and getattr(self, "fingering_edit_mode", False):
            hit_note = self._hit_test_editable_note(pos.x(), pos.y())
            if hit_note is not None:
                self._cycle_note_fingering(hit_note)
                event.accept()
                return

        # 3. Shift + 右クリック または 中クリック: いつでもノーツの発音/除外 (Mute) トグル
        if (btn == Qt.MouseButton.RightButton and (mods & Qt.KeyboardModifier.ShiftModifier)) or (btn == Qt.MouseButton.MiddleButton):
            hit_note = self._hit_test_note(pos.x(), pos.y(), editable_only=False)
            if hit_note is not None:
                self._toggle_note_mute(hit_note)
                event.accept()
                return

        # 4. 通常の右クリック: 編集モードでなくても即座に変え指循環 (変更可能ノーツの場合)
        if btn == Qt.MouseButton.RightButton and not (mods & Qt.KeyboardModifier.ShiftModifier):
            hit_note = self._hit_test_editable_note(pos.x(), pos.y())
            if hit_note is not None:
                self._cycle_note_fingering(hit_note)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """マウス移動時のカーソル形状切替 (ノーツ上では指アイコン)"""
        pos = event.position()
        if getattr(self, "mute_edit_mode", False):
            hit_note = self._hit_test_note(pos.x(), pos.y(), editable_only=False)
            if hit_note is not None:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        elif getattr(self, "fingering_edit_mode", False):
            hit_note = self._hit_test_editable_note(pos.x(), pos.y())
            if hit_note is not None:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def set_loop_markers(self, a_sec: float = 0.0, b_sec: float = None, enabled: bool = True):
        """A-Bループ区間マーカー設定"""
        self.loop_a_sec = max(0.0, float(a_sec)) if a_sec is not None else 0.0
        self.loop_b_sec = float(b_sec) if b_sec is not None else None
        self.loop_enabled = bool(enabled)
        self.update()

    def set_timeline_data(self, timeline_data):
        """MidiTimelineData のノーツおよび小節データをセット"""
        self.timeline = timeline_data
        self.midi_notes = timeline_data.main_notes
        self.note_start_secs = [n["start_sec"] for n in self.midi_notes]
        self.max_note_dur_sec = max((n["dur_sec"] for n in self.midi_notes), default=5.0)
        self.measures = timeline_data.measures_timeline
        self.measure_start_secs = [m["start_sec"] for m in self.measures]
        self.inst_type = timeline_data.inst_type
        self.default_bpm = getattr(timeline_data, "default_bpm", 120.0)
        self.invalidate_static_cache()

    def invalidate_static_cache(self):
        self._static_dirty = True
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._static_dirty = True

    # =========================================================================
    # 背景画像 & スキン設定 API
    # =========================================================================
    def _load_skins(self):
        """skins/ ディレクトリ内のテクスチャをロード"""
        skins_dir = get_portable_path("skins")
        mp_path = self.skin_mouthpiece_path or os.path.join(skins_dir, "マウスピース.png")
        if os.path.isfile(mp_path):
            self._pix_mouthpiece = QPixmap(mp_path)
        else:
            self._pix_mouthpiece = None

        lo_path = self.skin_lever_off_path or os.path.join(skins_dir, "レバーオフ.png")
        if os.path.isfile(lo_path):
            self._pix_lever_off = QPixmap(lo_path)
        else:
            self._pix_lever_off = None

        lon_path = self.skin_lever_on_path or os.path.join(skins_dir, "レバーオン.png")
        if os.path.isfile(lon_path):
            self._pix_lever_on = QPixmap(lon_path)
        else:
            self._pix_lever_on = None

    def set_background_image(self, path: str, dim_ratio: int = None, fit_mode: str = None, rotation: int = None, enabled: bool = None):
        """背景画像パス・減光比率・フィットモード・回転・表示有効を一括更新"""
        self.bg_image_path = str(path) if path else ""
        if dim_ratio is not None:
            self.bg_dim_ratio = max(0, min(100, int(dim_ratio)))
        if fit_mode is not None:
            self.bg_fit_mode = str(fit_mode)
        if rotation is not None:
            self.bg_rotation = int(rotation)
        if enabled is not None:
            self.bg_image_enabled = bool(enabled)
        self._cached_bg_image = None
        self.invalidate_static_cache()

    def set_background_dim(self, dim_ratio: int):
        """背景の暗さ/減光オーバーレイ比率 (0% 〜 100%)"""
        self.bg_dim_ratio = max(0, min(100, int(dim_ratio)))
        self.invalidate_static_cache()

    def set_background_fit_mode(self, fit_mode: str):
        """背景フィットモード (トリミング / 全体表示 / 引き伸ばし)"""
        self.bg_fit_mode = str(fit_mode)
        self.invalidate_static_cache()

    def set_background_rotation(self, rotation: int):
        """背景回転 (0, 90, 180, 270)"""
        self.bg_rotation = int(rotation)
        self.invalidate_static_cache()

    def clear_background_image(self):
        """背景画像を解除"""
        self.bg_image_path = ""
        self._cached_bg_image = None
        self.invalidate_static_cache()

    def set_canvas_bg_color(self, bg_name: str, is_chromakey: bool = False):
        """キャンバス背景色設定 (クロマキー素材プレビュー連動)"""
        if not is_chromakey or "ノーマル" in bg_name:
            self.color_bg = QColor("#0d0d0d")
        elif "グリーン" in bg_name:
            self.color_bg = QColor("#00FF00")
        elif "ブルー" in bg_name:
            self.color_bg = QColor("#0000FF")
        elif "マゼンタ" in bg_name:
            self.color_bg = QColor("#FF00FF")
        else:
            self.color_bg = QColor("#0d0d0d")
        self.invalidate_static_cache()

    def set_skin_enabled(self, enabled: bool):
        """ハーモニカスキン画像の有効/無効"""
        self.skin_enabled = bool(enabled)
        self.invalidate_static_cache()

    def set_custom_skins(self, mouthpiece_path: str = "", lever_off_path: str = "", lever_on_path: str = ""):
        """カスタムスキン画像のパスを設定"""
        self.skin_mouthpiece_path = str(mouthpiece_path)
        self.skin_lever_off_path = str(lever_off_path)
        self.skin_lever_on_path = str(lever_on_path)
        self._load_skins()
        self.invalidate_static_cache()

    def _rebuild_static_pixmap(self, w: int, h: int, scale: float, x_offset: float, y_offset: float):
        """ハーモニカ本体、カバープレート、丸穴、穴番号、穴下音名（4音グリッド/1音）、凡例をQPixmapに事前ベイク"""
        dpr = self.devicePixelRatioF()
        pix = QPixmap(int(w * dpr), int(h * dpr))
        pix.setDevicePixelRatio(dpr)
        pix.fill(self.color_bg)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        base_h = float(get_canvas_height_by_ratio(self.aspect_ratio))
        disp_w = CANVAS_WIDTH * scale
        disp_h = base_h * scale

        # 0. 背景画像の描画
        if self.bg_image_enabled and self.bg_image_path and os.path.isfile(self.bg_image_path):
            try:
                if self.bg_image_path != self._cached_bg_path or self._cached_bg_image is None:
                    from PyQt6.QtGui import QImageReader
                    reader = QImageReader(self.bg_image_path)
                    reader.setAutoTransform(True)
                    self._cached_bg_image = reader.read()
                    self._cached_bg_path = self.bg_image_path

                if self._cached_bg_image and not self._cached_bg_image.isNull():
                    img = self._cached_bg_image
                    if self.bg_rotation != 0:
                        tr = QTransform()
                        tr.rotate(self.bg_rotation)
                        img = img.transformed(tr, Qt.TransformationMode.SmoothTransformation)

                    img_w = img.width()
                    img_h = img.height()
                    if img_w > 0 and img_h > 0:
                        dest_rect = QRectF(x_offset, y_offset, disp_w, disp_h)
                        p.save()
                        p.setClipRect(dest_rect)
                        if "全体" in self.bg_fit_mode or "収める" in self.bg_fit_mode:
                            img_scale = min(disp_w / img_w, disp_h / img_h)
                            fw = img_w * img_scale
                            fh = img_h * img_scale
                            fx = x_offset + (disp_w - fw) * 0.5
                            fy = y_offset + (disp_h - fh) * 0.5
                            p.drawImage(QRectF(fx, fy, fw, fh), img)
                        elif "引き伸ばし" in self.bg_fit_mode:
                            p.drawImage(dest_rect, img)
                        elif "横幅" in self.bg_fit_mode:
                            sc_f = disp_w / max(1, img_w)
                            new_h = img_h * sc_f
                            fy = y_offset + (disp_h - new_h) * 0.5
                            p.drawImage(QRectF(x_offset, fy, disp_w, new_h), img)
                        elif "縦幅" in self.bg_fit_mode:
                            sc_f = disp_h / max(1, img_h)
                            new_w = img_w * sc_f
                            fx = x_offset + (disp_w - new_w) * 0.5
                            p.drawImage(QRectF(fx, y_offset, new_w, disp_h), img)
                        else:
                            img_scale = max(disp_w / img_w, disp_h / img_h)
                            sw = disp_w / img_scale
                            sh = disp_h / img_scale
                            sx = (img_w - sw) * 0.5
                            sy = (img_h - sh) * 0.5
                            p.drawImage(dest_rect, img, QRectF(sx, sy, sw, sh))

                        if self.bg_dim_ratio > 0:
                            alpha = int(round(255 * (min(100, max(0, self.bg_dim_ratio)) / 100.0)))
                            p.fillRect(dest_rect, QColor(0, 0, 0, alpha))
                        p.restore()
            except Exception as ex:
                print(f"[Warning] Background image draw error: {ex}")

        y_center, y_col, y_str, y_hole, h_diag, h_str = get_y_trajectory_params(base_h, self.trajectory_mode)
        visible_indices, x_start_base, x_shift, x_shift_notes = get_layout_params(self.inst_type, 1.0)
        total_w_base = len(visible_indices) * W_PITCH

        x_start = x_offset + x_start_base * scale
        total_w = total_w_base * scale
        y_center_s = y_offset + y_center * scale
        y_hole_s = y_offset + y_hole * scale
        y_col_s = y_offset + y_col * scale
        y_str_s = y_offset + y_str * scale
        w_pitch_s = W_PITCH * scale
        d_hole_s = D_HOLE * scale
        is_straight_mode = ("垂直落下" in str(self.trajectory_mode))

        is_bright_bg = self.color_bg.name().upper() in ("#00FF00", "#0000FF", "#FF00FF")

        # 1. 縦ガイド線 ＆ 1穴4分割サブガイド線 ＆ オクターブ変形ガイド線
        if self.show_grid:
            grid_sub_col = QColor(0, 0, 0, 20) if is_bright_bg else QColor(255, 255, 255, 18)
            grid_bnd_col = QColor(0, 0, 0, 45) if is_bright_bg else QColor(255, 255, 255, 30)
            grid_oct_col = QColor(0, 0, 0, 50) if is_bright_bg else QColor(255, 255, 255, 35)

            if is_straight_mode:
                for k in range(len(visible_indices)):
                    hx = x_start + k * w_pitch_s
                    for sub in (1, 2, 3):
                        sx = hx + sub * 12.0 * scale
                        p.setPen(QPen(grid_sub_col, max(1.0, 1.0 * scale)))
                        p.drawLine(QPointF(sx, y_offset), QPointF(sx, y_hole_s))
                    abs_idx = visible_indices[k]
                    is_oct = (abs_idx % 4 == 0)
                    p.setPen(QPen(grid_oct_col if is_oct else grid_bnd_col, max(1.0, (1.5 if is_oct else 1.0) * scale), Qt.PenStyle.DashLine if is_oct else Qt.PenStyle.SolidLine))
                    p.drawLine(QPointF(hx, y_offset), QPointF(hx, y_hole_s))
                p.setPen(QPen(grid_oct_col, max(1.0, 1.5 * scale), Qt.PenStyle.DashLine))
                p.drawLine(QPointF(x_start + total_w, y_offset), QPointF(x_start + total_w, y_hole_s))
            else:
                # 上部60音レーン (y_offset 〜 y_col_s)
                for idx in range(58):
                    gx = x_offset + (24.0 + idx * 16.0) * scale
                    p.setPen(QPen(grid_sub_col, max(1.0, 1.0 * scale)))
                    p.drawLine(QPointF(gx, y_offset), QPointF(gx, y_col_s))
                p.setPen(QPen(grid_bnd_col, max(1.0, 1.0 * scale)))
                p.drawLine(QPointF(x_offset + 24.0 * scale, y_offset), QPointF(x_offset + 24.0 * scale, y_col_s))
                p.drawLine(QPointF(x_offset + 936.0 * scale, y_offset), QPointF(x_offset + 936.0 * scale, y_col_s))

                # 下部直下区間 (y_str_s 〜 y_hole_s)
                if y_str_s < y_hole_s:
                    p.setPen(QPen(grid_sub_col, max(1.0, 1.0 * scale)))
                    p.drawLine(QPointF(x_start, y_str_s), QPointF(x_start + total_w, y_str_s))
                    for k in range(len(visible_indices)):
                        hx = x_start + k * w_pitch_s
                        for sub in (1, 2, 3):
                            sx = hx + sub * 12.0 * scale
                            p.setPen(QPen(grid_sub_col, max(1.0, 1.0 * scale)))
                            p.drawLine(QPointF(sx, y_str_s), QPointF(sx, y_hole_s))
                        p.setPen(QPen(grid_bnd_col, max(1.0, 1.0 * scale)))
                        p.drawLine(QPointF(hx, y_str_s), QPointF(hx, y_hole_s))
                    p.drawLine(QPointF(x_start + total_w, y_str_s), QPointF(x_start + total_w, y_hole_s))

                # ★ オクターブ変形ガイド線 (上部12音ごと ➔ 中間変形斜線 ➔ 下部4穴ごと)
                pen_oct = QPen(grid_oct_col, max(1.0, 1.5 * scale), Qt.PenStyle.DashLine)
                p.setPen(pen_oct)
                for k in range(len(visible_indices) + 1):
                    abs_idx = visible_indices[k] if k < len(visible_indices) else (visible_indices[-1] + 1)
                    if abs_idx % 4 == 0:
                        x_bot = x_start + k * w_pitch_s
                        lane_idx = (abs_idx // 4) * 12
                        x_top = x_offset + (72.0 + lane_idx * 16.0) * scale - (x_shift_notes * scale)
                        # 上部
                        p.drawLine(QPointF(x_top, y_offset), QPointF(x_top, y_col_s))
                        # 中間変形区間
                        if y_str_s > y_col_s:
                            p.drawLine(QPointF(x_top, y_col_s), QPointF(x_bot, y_str_s))
                        # 下部
                        p.drawLine(QPointF(x_bot, y_str_s), QPointF(x_bot, y_hole_s))

        # 2. ハーモニカ本体 (高さ90pxカバープレート ＆ 丸穴 D_HOLE=30px)
        plate_rect = QRectF(x_start - 15.0 * scale, y_center_s - 45.0 * scale, total_w + 30.0 * scale, 90.0 * scale)
        if self.skin_enabled and self._pix_mouthpiece and not self._pix_mouthpiece.isNull():
            p.drawPixmap(plate_rect.toRect(), self._pix_mouthpiece)
        else:
            p.setPen(QPen(QColor("#777777"), max(1.0, 2.0 * scale)))
            p.setBrush(QColor("#2d2f31"))
            p.drawRoundedRect(plate_rect, 15.0 * scale, 15.0 * scale)

        # 穴 (真円 丸穴 D_HOLE=30px) & 穴番号 (+24px 内側)
        self.font_hole.setPointSizeF(max(6.5, 10.0 * scale))
        for k, idx in enumerate(visible_indices):
            cx = x_start + k * w_pitch_s + w_pitch_s * 0.5
            hole_rect = QRectF(cx - d_hole_s * 0.5, y_center_s - d_hole_s * 0.5, d_hole_s, d_hole_s)
            p.setPen(QPen(QColor("#333333"), max(1.0, 1.2 * scale)))
            p.setBrush(self.color_led_off)  # #080808
            p.drawEllipse(hole_rect)

            if self.show_hole_num:
                num_rect = QRectF(cx - w_pitch_s * 0.5, y_center_s + 14.0 * scale, w_pitch_s, 20.0 * scale)
                num_str = format_hole_number(k, self.inst_type, getattr(self, "hole_num_style", "実機標準 (低音ドット付)"))
                _draw_bordered_text_qt(p, num_rect, num_str, self.font_hole, self.color_white, self.color_black, border_w=1.5 * scale)

        # 3. 穴下の音名表示 (田の字4音グリッド / 1音表示)
        show_4grid = (self.show_grid4 is True or "4音" in str(self.show_grid4))
        is_jp = (self.lang_mode == "ドレミ")

        if show_4grid:
            grid_top = y_center_s + 47.0 * scale
            cell_w = 23.0 * scale
            cell_h = 15.0 * scale
            cell_defs = [(0, 0, "吹", "OFF"), (0, 1, "吸", "OFF"), (1, 0, "吹", "ON"), (1, 1, "吸", "ON")]
            self.font_grid4.setPointSizeF(max(5.0, 7.5 * scale))
            p.setFont(self.font_grid4)

            for k, idx in enumerate(visible_indices):
                hole_abs = idx + 1
                cx = x_start + k * w_pitch_s + w_pitch_s * 0.5
                grid_left = cx - cell_w
                h4 = get_hole_4_notes(hole_abs, self.inst_type)

                for r_idx, c_idx, act, lev in cell_defs:
                    cx0 = grid_left + c_idx * cell_w
                    cy0 = grid_top + r_idx * cell_h
                    c_rect = QRectF(cx0, cy0, cell_w, cell_h)
                    c_fill = QColor("#181818") if r_idx == 0 else QColor("#101010")
                    c_out = QColor("#383838") if r_idx == 0 else QColor("#2C2C2C")
                    t_col = QColor("#CCCCCC") if r_idx == 0 else QColor("#888888")

                    p.setPen(QPen(c_out, max(1.0, 1.0 * scale)))
                    p.setBrush(c_fill)
                    p.drawRect(c_rect)

                    if self.lang_mode != "なし":
                        cell_midi = h4.get((act, lev))
                        cell_txt = get_note_name(cell_midi, is_japanese=is_jp) if cell_midi is not None else ""
                        p.setPen(t_col)
                        p.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, cell_txt)
        elif self.lang_mode != "なし":
            mode_key = "16穴" if "16穴" in self.inst_type else ("14穴" if "14穴" in self.inst_type else ("12穴 標準" if "標準" in self.inst_type else "12穴 バス"))
            blow_notes = BLOW_NOTES_MIDI.get(mode_key, BLOW_NOTES_MIDI["16穴"])
            self.font_note.setPointSizeF(max(6.0, 9.5 * scale))
            note_col = QColor("#000000") if is_bright_bg else QColor("#AAAAAA")

            for k, idx in enumerate(visible_indices):
                cx = x_start + k * w_pitch_s + w_pitch_s * 0.5
                n_midi = blow_notes[k] if k < len(blow_notes) else 60
                note_text = get_note_name(n_midi, is_japanese=is_jp)
                rect_note = QRectF(cx - w_pitch_s * 0.5, y_center_s + 50.0 * scale, w_pitch_s, 20.0 * scale)
                _draw_bordered_text_qt(p, rect_note, note_text, self.font_note, note_col, self.color_black, border_w=1.5 * scale)

        # 4. 判定ライン (エメラルドグリーン発光)
        p.setPen(QPen(QColor(0, 255, 204, 180), max(1.0, 2.0 * scale)))
        p.drawLine(QPointF(x_start, y_hole_s), QPointF(x_start + total_w, y_hole_s))

        # 5. 凡例 (吹/吸カラー: スライドレバー上部の右端余白へ配置)
        if self.show_legend:
            leg_w = 78.0 * scale
            leg_h = 44.0 * scale
            leg_x = min(x_offset + (CANVAS_WIDTH - 6.0) * scale - leg_w, x_start + total_w + 6.0 * scale)
            leg_y = y_center_s - 92.0 * scale
            p.setPen(QPen(QColor("#333333"), 1.0))
            p.setBrush(QColor(20, 20, 20, 210))
            p.drawRoundedRect(QRectF(leg_x, leg_y, leg_w, leg_h), 4.0 * scale, 4.0 * scale)

            # 吹 (オレンジ)
            p.setPen(self.pen_none)
            p.setBrush(self.color_blow)
            p.drawEllipse(QPointF(leg_x + 12.0 * scale, leg_y + 13.0 * scale), 5.5 * scale, 5.5 * scale)
            p.setPen(self.color_white)
            p.drawText(QRectF(leg_x + 21.0 * scale, leg_y + 3.0 * scale, 54.0 * scale, 20.0 * scale),
                       Qt.AlignmentFlag.AlignVCenter, "吹 Blow")

            # 吸 (水色)
            p.setPen(self.pen_none)
            p.setBrush(self.color_draw)
            p.drawEllipse(QPointF(leg_x + 12.0 * scale, leg_y + 31.0 * scale), 5.5 * scale, 5.5 * scale)
            p.setPen(self.color_white)
            p.drawText(QRectF(leg_x + 21.0 * scale, leg_y + 21.0 * scale, 54.0 * scale, 20.0 * scale),
                       Qt.AlignmentFlag.AlignVCenter, "吸 Draw")

        p.end()
        self._static_pixmap = pix
        self._static_dirty = False
        self._cached_wh_scale = (w, h, scale, x_offset, y_offset)

    def paintGL(self):
        """毎フレームのGPU描画ループ（ガベージコレクションゼロ・O(log N)抽出）"""
        self._fps_count += 1
        now = time.perf_counter()
        dt = now - self._fps_last_time
        if dt >= 0.5:
            self._current_fps = self._fps_count / dt
            self._fps_count = 0
            self._fps_last_time = now

        w, h = self.width(), self.height()
        base_h = float(get_canvas_height_by_ratio(self.aspect_ratio))
        scale = min(w / float(CANVAS_WIDTH), h / base_h)

        disp_w = CANVAS_WIDTH * scale
        disp_h = base_h * scale
        x_offset = (w - disp_w) * 0.5
        y_offset = (h - disp_h) * 0.5

        if self._static_dirty or self._static_pixmap is None or self._cached_wh_scale != (w, h, scale, x_offset, y_offset):
            self._rebuild_static_pixmap(w, h, scale, x_offset, y_offset)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. 静的レイヤーを描画
        painter.drawPixmap(0, 0, self._static_pixmap)

        # 2. 現在の楽曲秒数
        cur_sec = self.clock.get_current_base_sec(lookahead_sec=0.008)

        # レイアウトパラメータ取得
        y_center, y_col, y_str, y_hole, h_diag, h_str = get_y_trajectory_params(base_h, self.trajectory_mode)
        visible_indices, x_start_base, x_shift, x_shift_notes = get_layout_params(self.inst_type, 1.0)
        total_w_base = len(visible_indices) * W_PITCH

        y_center_s = y_offset + y_center * scale
        y_col_s = y_offset + y_col * scale
        y_str_s = y_offset + y_str * scale
        y_hole_s = y_offset + y_hole * scale
        h_diag_s = h_diag * scale
        x_start = x_offset + x_start_base * scale
        total_w = total_w_base * scale
        w_pitch_s = W_PITCH * scale
        d_hole_s = D_HOLE * scale

        px_per_sec = 2.0 * getattr(self, "default_bpm", 120.0) * self.note_speed_ratio * scale
        max_vis_sec = cur_sec + ((y_hole_s - y_offset) / px_per_sec) if px_per_sec > 0 else cur_sec + 5.0
        is_straight_mode = ("垂直落下" in str(self.trajectory_mode))

        # 3. 小節線の描画
        if self.show_bar_lines and self.measures and px_per_sec > 0:
            m_idx_start = bisect.bisect_left(self.measure_start_secs, cur_sec - 0.2)
            painter.setFont(self.font_measure)
            painter.setPen(self.pen_measure)
            y_plate_top = y_center_s - 45.0 * scale
            for mi in range(m_idx_start, len(self.measures)):
                m_data = self.measures[mi]
                m_sec = m_data["start_sec"]
                if m_sec > max_vis_sec:
                    break
                ym = y_hole_s - (m_sec - cur_sec) * px_per_sec
                if y_offset <= ym <= y_plate_top:
                    mx_start = x_start if is_straight_mode else (x_offset + 24.0 * scale)
                    mx_end = (x_start + total_w) if is_straight_mode else (x_offset + 936.0 * scale)
                    painter.drawLine(QPointF(mx_start, ym), QPointF(mx_end, ym))
                    painter.setPen(self.color_measure_text)
                    painter.drawText(QPointF(mx_start + 4.0 * scale, ym - 2.0 * scale), str(m_data["measure_num"]))
                    painter.setPen(self.pen_measure)

        # 3.5. A-Bループ境界線の描画
        if self.loop_enabled and px_per_sec > 0:
            for l_sec, l_tag, l_col in ((self.loop_a_sec, "[A]", QColor("#00E5FF")), (self.loop_b_sec, "[B]", QColor("#FFD700"))):
                if l_sec is not None:
                    yl = y_hole_s - (l_sec - cur_sec) * px_per_sec
                    if y_offset <= yl <= y_hole_s:
                        painter.setPen(QPen(l_col, 2.0, Qt.PenStyle.DashLine))
                        painter.drawLine(QPointF(x_start, yl), QPointF(x_start + total_w, yl))
                        painter.setPen(l_col)
                        painter.setFont(self.font_measure)
                        painter.drawText(QPointF(x_start + total_w - 28.0 * scale, yl - 3.0 * scale), l_tag)

        # 4. 落下ノーツの二分探索描画
        active_holes = {}        # hole_num -> action ("吹" / "吸")
        active_hole_cells = set() # (hole_num, action, lever)
        active_hole_notes = {}    # hole_num -> note_val
        lever_pressed = False

        if self.show_notes and self.midi_notes and px_per_sec > 0:
            idx_start = bisect.bisect_left(self.note_start_secs, cur_sec - self.max_note_dur_sec)

            for i in range(idx_start, len(self.midi_notes)):
                nd = self.midi_notes[i]
                n_start = nd["start_sec"]
                if n_start > max_vis_sec:
                    break
                n_end = nd["end_sec"]
                if n_end < cur_sec:
                    continue

                is_muted = nd.get("is_muted", False)
                if is_muted and getattr(self, "hide_muted_notes", False) and not getattr(self, "mute_edit_mode", False):
                    continue

                # 現在発音中判定 (除外ノーツは発光・レバーリング連動させない)
                if not is_muted and (n_start <= cur_sec < n_end):
                    h_num = nd["hole"]
                    act = nd["action"]
                    lev = nd["lever"]
                    active_holes[h_num] = act
                    active_hole_cells.add((h_num, act, lev))
                    if h_num not in active_hole_notes:
                        active_hole_notes[h_num] = nd["note"]
                    if lev == "ON":
                        lever_pressed = True

                y_bot = y_hole_s - (n_start - cur_sec) * px_per_sec
                y_top = y_hole_s - (n_end - cur_sec) * px_per_sec

                note_in_range = nd.get("in_range", True)
                if is_straight_mode and not note_in_range:
                    continue
                y_limit_bot = y_hole_s if note_in_range else y_col_s
                y_vis_top = max(y_offset, y_top)
                y_vis_bot = min(y_limit_bot, y_bot)
                if y_vis_bot <= y_vis_top:
                    continue

                dest_cx = x_offset + nd["dest_x_base"] * scale
                dest_l = dest_cx - 6.0 * scale
                dest_r = dest_cx + 6.0 * scale

                note_val = nd["note"]
                simulated_note = note_val + 36 if "バス" in self.inst_type else note_val
                lane_idx = simulated_note - 48
                # 12穴のノーツシフトは x_shift_notes を使用
                lane_l = x_offset + (72 + lane_idx * 16) * scale - (x_shift_notes * scale)
                lane_r = lane_l + 16.0 * scale

                length = max(1.0, y_vis_bot - y_vis_top)
                ch_base = min(3.5 * scale, length / 3.0)
                ch_top = ch_base if (y_offset <= y_top < y_limit_bot) else 0.0
                ch_bot = ch_base if (y_offset < y_bot <= y_limit_bot) else 0.0

                y_r_start = y_vis_top + ch_top
                y_r_end = y_vis_bot - ch_bot

                if is_straight_mode:
                    x_l_func = lambda yv: dest_l
                    x_r_func = lambda yv: dest_r
                    x_m_func = lambda yv: dest_cx
                    active_bends = ()
                else:
                    x_l_func = lambda yv: _calc_trajectory_x(yv, lane_l, lane_r, dest_l, dest_r, y_col_s, y_str_s, h_diag_s)[0]
                    x_r_func = lambda yv: _calc_trajectory_x(yv, lane_l, lane_r, dest_l, dest_r, y_col_s, y_str_s, h_diag_s)[1]
                    x_m_func = lambda yv: _calc_trajectory_x(yv, lane_l, lane_r, dest_l, dest_r, y_col_s, y_str_s, h_diag_s)[2]
                    bend_ys = ((y_col_s, y_str_s) if h_str > 0 else (y_col_s,)) if note_in_range else ()
                    active_bends = [by for by in bend_ys if y_r_start < by < y_r_end]

                is_blow = (nd["action"] == "吹")
                is_lever_on = (nd["lever"] == "ON")
                if is_muted:
                    if getattr(self, "mute_edit_mode", False):
                        fill_color = QColor(130, 40, 50, 110)
                    else:
                        fill_color = QColor(100, 100, 100, 85)
                else:
                    base_color = self.color_blow if is_blow else self.color_draw
                    if self.note_opacity < 100:
                        alpha = int(255 * (self.note_opacity / 100.0))
                        fill_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)
                    else:
                        fill_color = base_color

                use_split_slit = bool(not is_muted and is_lever_on and "スリット" in self.lever_deco_mode)

                if use_split_slit:
                    # 1. センター半割 (スリット): 左右2本のレール状ポリゴンに分割描画
                    slit_w = max(1.5, min(2.8 * scale, 3.2))

                    left_pts = []
                    if ch_top > 0.5:
                        left_pts.append(QPointF(x_l_func(y_vis_top) + ch_top, y_vis_top))
                        left_pts.append(QPointF(x_m_func(y_vis_top) - slit_w * 0.5, y_vis_top))
                        left_pts.append(QPointF(x_m_func(y_r_start) - slit_w * 0.5, y_r_start))
                    else:
                        left_pts.append(QPointF(x_l_func(y_vis_top), y_vis_top))
                        left_pts.append(QPointF(x_m_func(y_vis_top) - slit_w * 0.5, y_vis_top))
                    for by in active_bends:
                        left_pts.append(QPointF(x_m_func(by) - slit_w * 0.5, by))
                    if ch_bot > 0.5:
                        left_pts.append(QPointF(x_m_func(y_r_end) - slit_w * 0.5, y_r_end))
                        left_pts.append(QPointF(x_m_func(y_vis_bot) - slit_w * 0.5, y_vis_bot))
                        left_pts.append(QPointF(x_l_func(y_vis_bot) + ch_bot, y_vis_bot))
                        left_pts.append(QPointF(x_l_func(y_r_end), y_r_end))
                    else:
                        left_pts.append(QPointF(x_m_func(y_vis_bot) - slit_w * 0.5, y_vis_bot))
                        left_pts.append(QPointF(x_l_func(y_vis_bot), y_vis_bot))
                    for by in reversed(active_bends):
                        left_pts.append(QPointF(x_l_func(by), by))
                    if ch_top > 0.5:
                        left_pts.append(QPointF(x_l_func(y_r_start), y_r_start))

                    right_pts = []
                    if ch_top > 0.5:
                        right_pts.append(QPointF(x_m_func(y_vis_top) + slit_w * 0.5, y_vis_top))
                        right_pts.append(QPointF(x_r_func(y_vis_top) - ch_top, y_vis_top))
                        right_pts.append(QPointF(x_r_func(y_r_start), y_r_start))
                    else:
                        right_pts.append(QPointF(x_m_func(y_vis_top) + slit_w * 0.5, y_vis_top))
                        right_pts.append(QPointF(x_r_func(y_vis_top), y_vis_top))
                    for by in active_bends:
                        right_pts.append(QPointF(x_r_func(by), by))
                    if ch_bot > 0.5:
                        right_pts.append(QPointF(x_r_func(y_r_end), y_r_end))
                        right_pts.append(QPointF(x_r_func(y_vis_bot) - ch_bot, y_vis_bot))
                        right_pts.append(QPointF(x_m_func(y_vis_bot) + slit_w * 0.5, y_vis_bot))
                        right_pts.append(QPointF(x_m_func(y_r_end) + slit_w * 0.5, y_r_end))
                    else:
                        right_pts.append(QPointF(x_r_func(y_vis_bot), y_vis_bot))
                        right_pts.append(QPointF(x_m_func(y_vis_bot) + slit_w * 0.5, y_vis_bot))
                    for by in reversed(active_bends):
                        right_pts.append(QPointF(x_m_func(by) + slit_w * 0.5, by))
                    if ch_top > 0.5:
                        right_pts.append(QPointF(x_m_func(y_r_start) + slit_w * 0.5, y_r_start))

                    painter.setPen(self.pen_none)
                    painter.setBrush(fill_color)
                    painter.drawPolygon(QPolygonF(left_pts))
                    painter.drawPolygon(QPolygonF(right_pts))

                else:
                    # 通常ノーツ / 芯線 / サイドライン
                    poly_pts = []
                    if ch_top > 0.5:
                        poly_pts.append(QPointF(x_l_func(y_vis_top) + ch_top, y_vis_top))
                        poly_pts.append(QPointF(x_r_func(y_vis_top) - ch_top, y_vis_top))
                        poly_pts.append(QPointF(x_r_func(y_r_start), y_r_start))
                    else:
                        poly_pts.append(QPointF(x_l_func(y_vis_top), y_vis_top))
                        poly_pts.append(QPointF(x_r_func(y_vis_top), y_vis_top))

                    for by in active_bends:
                        poly_pts.append(QPointF(x_r_func(by), by))

                    if ch_bot > 0.5:
                        poly_pts.append(QPointF(x_r_func(y_r_end), y_r_end))
                        poly_pts.append(QPointF(x_r_func(y_vis_bot) - ch_bot, y_vis_bot))
                        poly_pts.append(QPointF(x_l_func(y_vis_bot) + ch_bot, y_vis_bot))
                        poly_pts.append(QPointF(x_l_func(y_r_end), y_r_end))
                    else:
                        poly_pts.append(QPointF(x_r_func(y_vis_bot), y_vis_bot))
                        poly_pts.append(QPointF(x_l_func(y_vis_bot), y_vis_bot))

                    for by in reversed(active_bends):
                        poly_pts.append(QPointF(x_l_func(by), by))

                    if ch_top > 0.5:
                        poly_pts.append(QPointF(x_l_func(y_r_start), y_r_start))

                    painter.setPen(self.pen_none)
                    painter.setBrush(fill_color)
                    painter.drawPolygon(QPolygonF(poly_pts))

                    # 非表示モード時：除外ノーツには破線赤枠、通常ノーツには薄い白枠を表示
                    if getattr(self, "mute_edit_mode", False):
                        if is_muted:
                            painter.setPen(QPen(QColor(244, 63, 94, 210), max(1.5, 1.8 * scale), Qt.PenStyle.DashLine))
                            painter.setBrush(Qt.BrushStyle.NoBrush)
                            painter.drawPolygon(QPolygonF(poly_pts))
                        else:
                            painter.setPen(QPen(QColor(255, 255, 255, 80), 1.0))
                            painter.setBrush(Qt.BrushStyle.NoBrush)
                            painter.drawPolygon(QPolygonF(poly_pts))

                    # 運指変更モード時：編集可能ノーツの強調白枠表示 (除外ノーツは非表示)
                    if not is_muted and getattr(self, "fingering_edit_mode", False) and nd.get("is_editable", False):
                        painter.setPen(QPen(QColor(255, 255, 255, 230), max(1.8, 2.0 * scale)))
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawPolygon(QPolygonF(poly_pts))

                    # 半音ノーツ装飾 (除外ノーツは装飾しない)
                    if not is_muted and is_lever_on:
                        line_alpha = fill_color.alpha()
                        if "2本" in self.lever_deco_mode or "ダブル" in self.lever_deco_mode:
                            pen_col = self.color_blow_hi if is_blow else self.color_draw_hi
                            pen_d = QPen(QColor(pen_col.red(), pen_col.green(), pen_col.blue(), line_alpha), max(1.2, 1.4 * scale))
                            pen_d.setCapStyle(Qt.PenCapStyle.RoundCap)
                            painter.setPen(pen_d)
                            d_off = max(1.6, 2.2 * scale)
                            # 左ライン
                            line_pts_l = [QPointF(round(x_m_func(y_vis_top) - d_off), y_vis_top)]
                            for by in active_bends:
                                line_pts_l.append(QPointF(round(x_m_func(by) - d_off), by))
                            line_pts_l.append(QPointF(round(x_m_func(y_vis_bot) - d_off), y_vis_bot))
                            for lj in range(len(line_pts_l) - 1):
                                painter.drawLine(line_pts_l[lj], line_pts_l[lj + 1])
                            # 右ライン
                            line_pts_r = [QPointF(round(x_m_func(y_vis_top) + d_off), y_vis_top)]
                            for by in active_bends:
                                line_pts_r.append(QPointF(round(x_m_func(by) + d_off), by))
                            line_pts_r.append(QPointF(round(x_m_func(y_vis_bot) + d_off), y_vis_bot))
                            for lj in range(len(line_pts_r) - 1):
                                painter.drawLine(line_pts_r[lj], line_pts_r[lj + 1])
                        elif "センターライン" in self.lever_deco_mode:
                            pen_col = self.color_blow_hi if is_blow else self.color_draw_hi
                            pen_c = QPen(QColor(pen_col.red(), pen_col.green(), pen_col.blue(), line_alpha), max(1.6, 2.0 * scale))
                            pen_c.setCapStyle(Qt.PenCapStyle.RoundCap)
                            painter.setPen(pen_c)
                            line_pts = [QPointF(round(x_m_func(y_vis_top)), y_vis_top)]
                            for by in active_bends:
                                line_pts.append(QPointF(round(x_m_func(by)), by))
                            line_pts.append(QPointF(round(x_m_func(y_vis_bot)), y_vis_bot))
                            for lj in range(len(line_pts) - 1):
                                painter.drawLine(line_pts[lj], line_pts[lj + 1])
                        elif "サイドライン" in self.lever_deco_mode:
                            # サイドライン (明暗適応ハイライト)
                            stripe_w = min(4.5 * scale, max(2.5, 3.2 * scale))
                            side_pts = []
                            if ch_top > 0.5:
                                side_pts.append(QPointF(x_r_func(y_vis_top) - ch_top, y_vis_top))
                                side_pts.append(QPointF(x_r_func(y_r_start), y_r_start))
                            else:
                                side_pts.append(QPointF(x_r_func(y_vis_top), y_vis_top))
                            for by in active_bends:
                                side_pts.append(QPointF(x_r_func(by), by))
                            if ch_bot > 0.5:
                                side_pts.append(QPointF(x_r_func(y_r_end), y_r_end))
                                side_pts.append(QPointF(x_r_func(y_vis_bot) - ch_bot, y_vis_bot))
                                side_pts.append(QPointF(max(x_l_func(y_vis_bot) + ch_bot, x_r_func(y_vis_bot) - ch_bot - stripe_w), y_vis_bot))
                                side_pts.append(QPointF(max(x_l_func(y_r_end), x_r_func(y_r_end) - stripe_w), y_r_end))
                            else:
                                side_pts.append(QPointF(x_r_func(y_vis_bot), y_vis_bot))
                                side_pts.append(QPointF(max(x_l_func(y_vis_bot), x_r_func(y_vis_bot) - stripe_w), y_vis_bot))
                            for by in reversed(active_bends):
                                side_pts.append(QPointF(max(x_l_func(by), x_r_func(by) - stripe_w), by))
                            if ch_top > 0.5:
                                side_pts.append(QPointF(max(x_l_func(y_r_start), x_r_func(y_r_start) - stripe_w), y_r_start))
                                side_pts.append(QPointF(max(x_l_func(y_vis_top) + ch_top, x_r_func(y_vis_top) - ch_top - stripe_w), y_vis_top))
                            else:
                                side_pts.append(QPointF(max(x_l_func(y_vis_top), x_r_func(y_vis_top) - stripe_w), y_vis_top))

                            hi_col = self.color_blow_hi if is_blow else self.color_draw_hi
                            painter.setPen(self.pen_none)
                            painter.setBrush(hi_col)
                            painter.drawPolygon(QPolygonF(side_pts))

                # 落下追従音名ラベル描画 (除外ノーツは通常非描画、非表示モード中は "✕ ド" 表示)
                should_draw_label = (not is_muted) or (is_muted and getattr(self, "mute_edit_mode", False))
                if should_draw_label and self.show_lookahead and self.lang_mode != "なし" and (not is_straight_mode or note_in_range) and (y_vis_bot - y_vis_top >= 8.0 * scale):
                    label_y = y_vis_bot - 8.5 * scale if (y_vis_bot - y_vis_top >= 17.0 * scale) else (y_vis_top + y_vis_bot) * 0.5
                    label_x = x_m_func(label_y)
                    raw_name = nd["name_jp"] if self.lang_mode == "ドレミ" else nd["name_cde"]
                    lbl_text = f"✕ {raw_name}" if is_muted else raw_name

                    self.font_note.setPointSizeF(max(6.0, 8.5 * scale))
                    text_rect = QRectF(label_x - 30.0 * scale, label_y - 10.0 * scale, 60.0 * scale, 20.0 * scale)
                    text_color = QColor("#FDA4AF") if is_muted else self.color_white
                    _draw_bordered_text_qt(painter, text_rect, lbl_text, self.font_note, text_color, self.color_black, border_w=1.2 * scale)

        # 5. スライドレバー (スキンまたはプロシージャル3Dメタル)
        lever_x = x_start + total_w
        if self.skin_enabled and (self._pix_lever_on or self._pix_lever_off):
            lever_rect = QRectF(lever_x, y_center_s - 24.0 * scale, 48.0 * scale, 48.0 * scale)
            if lever_pressed and self._pix_lever_on and not self._pix_lever_on.isNull():
                painter.drawPixmap(lever_rect.toRect(), self._pix_lever_on)
            elif not lever_pressed and self._pix_lever_off and not self._pix_lever_off.isNull():
                painter.drawPixmap(lever_rect.toRect(), self._pix_lever_off)
            else:
                self._draw_procedural_lever(painter, lever_x, y_center_s, scale, lever_pressed)
        else:
            self._draw_procedural_lever(painter, lever_x, y_center_s, scale, lever_pressed)

        # 6. 発音中穴の丸穴LED・レバーリング連動・着地発光・穴下音名ハイライト
        show_4grid = (self.show_grid4 is True or "4音" in str(self.show_grid4))
        is_jp = (self.lang_mode == "ドレミ")

        for k, idx in enumerate(visible_indices):
            hole_num = idx + 1
            act = active_holes.get(hole_num)
            if act is not None:
                cx = x_start + k * w_pitch_s + w_pitch_s * 0.5
                act_color = self.color_blow if act == "吹" else self.color_draw

                # A. 丸穴LEDネオン点灯 (直径30px穴内)
                painter.setPen(self.pen_none)
                painter.setBrush(act_color)
                painter.drawEllipse(QPointF(cx, y_center_s), (d_hole_s * 0.5) - 1.5, (d_hole_s * 0.5) - 1.5)

                # B. レバーリング連動 (use_ring: レバーON時に穴外周に太い吹吸カラーのリングを描画)
                if lever_pressed and self.use_ring:
                    painter.setPen(QPen(act_color, max(2.0, 3.0 * scale)))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    ring_r = 21.0 * scale
                    painter.drawEllipse(QPointF(cx, y_center_s), ring_r, ring_r)

                # C. 着地発光 (is_glow_on: 判定ライン上の半円グロー扇形 - 滑らかな放射状アルファグラデーション)
                if self.is_glow_on:
                    pie_r = 32.0 * scale
                    painter.setPen(self.pen_none)
                    glow_grad = QRadialGradient(QPointF(cx, y_hole_s), pie_r)
                    glow_grad.setColorAt(0.0, QColor(255, 255, 255, 210))
                    glow_grad.setColorAt(0.5, QColor(255, 255, 255, 100))
                    glow_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                    painter.setBrush(QBrush(glow_grad))
                    painter.drawPie(QRectF(cx - pie_r, y_hole_s - pie_r, pie_r * 2.0, pie_r * 2.0), 0, 180 * 16)

                # D. 穴下音名のリアルタイムハイライト
                if show_4grid:
                    h4 = get_hole_4_notes(hole_num, self.inst_type)
                    grid_top = y_center_s + 47.0 * scale
                    cell_w = 23.0 * scale
                    cell_h = 15.0 * scale
                    grid_left = cx - cell_w
                    cell_defs = [(0, 0, "吹", "OFF"), (0, 1, "吸", "OFF"), (1, 0, "吹", "ON"), (1, 1, "吸", "ON")]

                    for r_idx, c_idx, a_val, l_val in cell_defs:
                        if (hole_num, a_val, l_val) in active_hole_cells:
                            cx0 = grid_left + c_idx * cell_w
                            cy0 = grid_top + r_idx * cell_h
                            c_rect = QRectF(cx0, cy0, cell_w, cell_h)
                            c_bg = self.color_blow if a_val == "吹" else self.color_draw

                            painter.setPen(QPen(QColor("#FFFFFF"), max(1.0, 1.5 * scale)))
                            painter.setBrush(c_bg)
                            painter.drawRect(c_rect)

                            if self.lang_mode != "なし":
                                cell_midi = h4.get((a_val, l_val))
                                cell_txt = get_note_name(cell_midi, is_japanese=is_jp) if cell_midi is not None else ""
                                painter.setFont(self.font_grid4)
                                painter.setPen(QColor("#000000"))
                                painter.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, cell_txt)
                elif self.lang_mode != "なし" and hole_num in active_hole_notes:
                    # 1音表示モード：鳴っている実音を白文字・黒フチで強調表示
                    cur_note = active_hole_notes[hole_num]
                    note_text = get_note_name(cur_note, is_japanese=is_jp)
                    rect_note = QRectF(cx - w_pitch_s * 0.5, y_center_s + 50.0 * scale, w_pitch_s, 20.0 * scale)
                    _draw_bordered_text_qt(painter, rect_note, note_text, self.font_note, self.color_white, self.color_black, border_w=2.0 * scale)

        # 7. モードHUDバナー (運指変更モード / 非表示モード) & フローティングトースト描画
        if getattr(self, "mute_edit_mode", False):
            banner_rect = QRectF(x_start + 10.0 * scale, y_offset + 8.0 * scale, total_w - 20.0 * scale, 24.0 * scale)
            painter.setPen(QPen(QColor("#F43F5E"), 1.0))
            painter.setBrush(QColor(36, 12, 20, 225))
            painter.drawRoundedRect(banner_rect, 4.0 * scale, 4.0 * scale)
            painter.setPen(QColor("#FDA4AF"))
            font_banner = QFont("Meiryo UI", max(8, int(9.5 * scale)), QFont.Weight.Bold)
            painter.setFont(font_banner)
            painter.drawText(banner_rect, Qt.AlignmentFlag.AlignCenter, "🔇 非表示モード有効：画面上のノーツをクリックして発音／非表示（除外）を切替 [M]")
        elif getattr(self, "fingering_edit_mode", False):
            banner_rect = QRectF(x_start + 10.0 * scale, y_offset + 8.0 * scale, total_w - 20.0 * scale, 24.0 * scale)
            painter.setPen(QPen(QColor("#00E5FF"), 1.0))
            painter.setBrush(QColor(14, 20, 32, 215))
            painter.drawRoundedRect(banner_rect, 4.0 * scale, 4.0 * scale)
            painter.setPen(QColor("#00E5FF"))
            font_banner = QFont("Meiryo UI", max(8, int(9.5 * scale)), QFont.Weight.Bold)
            painter.setFont(font_banner)
            painter.drawText(banner_rect, Qt.AlignmentFlag.AlignCenter, "🎯 かえ指モード有効：白枠ノーツをクリックして吹吸・穴番号を切替 [F]")

        if self.toast_msg and time.time() < self.toast_expire:
            toast_w = min(420.0 * scale, total_w * 0.7)
            toast_h = 32.0 * scale
            toast_rect = QRectF(x_start + (total_w - toast_w) * 0.5, y_center_s - 95.0 * scale, toast_w, toast_h)
            painter.setPen(QPen(QColor("#38BDF8"), 1.5))
            painter.setBrush(QColor(15, 23, 42, 235))
            painter.drawRoundedRect(toast_rect, 6.0 * scale, 6.0 * scale)
            painter.setPen(QColor("#F8FAFC"))
            font_toast = QFont("Meiryo UI", max(9, int(11.0 * scale)), QFont.Weight.Bold)
            painter.setFont(font_toast)
            painter.drawText(toast_rect, Qt.AlignmentFlag.AlignCenter, self.toast_msg)

        painter.end()

    def _draw_procedural_lever(self, painter, lever_x, y_center_s, scale, lever_pressed):
        """テクスチャ画像がない場合のプロシージャルメタリックレバー描画 (v2.1準拠)"""
        btn_w = max(1.0, 16.0 * scale)
        btn_h = max(1.0, 36.0 * scale)
        if lever_pressed:
            painter.setPen(self.pen_none)
            painter.setBrush(QColor("#3a3a3a"))
            painter.drawRoundedRect(QRectF(lever_x, y_center_s - 12.0 * scale, 12.0 * scale, 24.0 * scale), 3.0 * scale, 3.0 * scale)
            painter.setBrush(QColor("#DCDCDC"))
            painter.setPen(QPen(QColor("#777777"), max(1.0, 1.2 * scale)))
            painter.drawEllipse(QRectF(lever_x + 3.0 * scale, y_center_s - btn_h * 0.5, btn_w, btn_h))
        else:
            painter.setPen(self.pen_none)
            painter.setBrush(QColor("#555555"))
            painter.drawRoundedRect(QRectF(lever_x, y_center_s - 12.0 * scale, 24.0 * scale, 24.0 * scale), 3.0 * scale, 3.0 * scale)
            painter.setBrush(QColor("#ECECEC"))
            painter.setPen(QPen(QColor("#888888"), max(1.0, 1.2 * scale)))
            painter.drawEllipse(QRectF(lever_x + 22.0 * scale, y_center_s - btn_h * 0.5, btn_w, btn_h))

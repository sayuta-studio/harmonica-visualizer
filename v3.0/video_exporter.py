# -*- coding: utf-8 -*-
"""
v3.0/video_exporter.py
PyQt6 オフスクリーン高速レンダリング ＆ FFmpeg GPU/CPU パイプエンコーダー。
- QImage + QPainter による高精度オフスクリーン描画
- v2.1完全準拠：90px高3Dプレート、丸穴(直径30px)、内側穴番号(+24px)、4音グリッド(田の字)/1音動的表示、レバーリング連動、着地発光
- 半音ノーツ装飾4モード (スリット2分割 / サイドライン明暗適応 / センター芯線 / なし)
- タイトル配置テンプレート6種 ＆ クロマキー背景色 (グリーン/ブルー/マゼンタ/黒)
- 内部MIDIガイド音＋伴奏＋メトロノーム＋外部音源の高音質WAV物理合成 (synthesize_midi_to_wav)
- Windows Media Foundation (h264_mf) GPUハードウェアアクセラレーション対応 (libx264フォールバック)
"""

import os
import sys
import time
import bisect
import subprocess
import math
import threading
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QImage, QPainter, QColor, QPen, QBrush, QFont, QFontMetricsF, QPolygonF, QTransform, QRadialGradient
)

from config import (
    CANVAS_WIDTH, W_PITCH, D_HOLE,
    get_canvas_height_by_ratio, get_y_trajectory_params,
    get_layout_params, get_lever_highlight_color, get_portable_path,
    format_hole_number
)
from harmonica_map import (
    is_note_in_range, get_note_name, get_hole_4_notes, BLOW_NOTES_MIDI
)
from audio_engine import get_reverb_filter_arg, synthesize_midi_to_wav


def check_ffmpeg_available() -> bool:
    """システムで ffmpeg コマンドが実行可能か判定"""
    try:
        res = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def _calc_trajectory_x(yv, lane_l, lane_r, dest_l, dest_r, y_col, y_str, h_diag):
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


def _fit_font(text: str, base_font: QFont, max_w: float, min_pt: float = 6.0) -> QFont:
    """枠幅 max_w を超える場合に文字サイズを自動縮小した QFont を返す"""
    if not text or max_w <= 0:
        return base_font
    font = QFont(base_font)
    fm = QFontMetricsF(font)
    text_w = fm.horizontalAdvance(text)
    if text_w > max_w:
        ratio = max_w / text_w
        cur_pt = font.pointSizeF()
        if cur_pt <= 0:
            cur_pt = float(font.pointSize())
        new_pt = max(min_pt, cur_pt * ratio * 0.98)
        font.setPointSizeF(new_pt)
    return font


class OffscreenVisualizerRenderer:
    """オフスクリーンでの高速フレーム描画エンジン"""

    def __init__(self, timeline, width=1920, height=1080, aspect_ratio="16:9", settings=None):
        self.timeline = timeline
        self.width = int(width)
        self.height = int(height)
        self.aspect_ratio = str(aspect_ratio)
        self.settings = dict(settings or {})

        # 設定の展開
        self.inst_type = self.settings.get("inst_type") or (self.timeline.inst_type if self.timeline else "16穴 (64音・C調)")
        self.trajectory_mode = self.settings.get("trajectory_mode", "3段階 (練習標準)")
        self.lang_mode = self.settings.get("lang_mode", "ドレミ")
        self.lever_deco_mode = self.settings.get("lever_deco_mode", "センターライン (芯線)")
        self.note_speed_ratio = float(self.settings.get("note_speed_ratio", self.settings.get("fall_speed_ratio", 1.0)))
        self.default_bpm = float(self.settings.get("default_bpm", getattr(self.timeline, "default_bpm", 120.0) if self.timeline else 120.0))
        self.show_notes = bool(self.settings.get("show_notes", True))
        self.show_grid = bool(self.settings.get("show_grid", True))
        self.show_bar_lines = bool(self.settings.get("show_bar_lines", True))
        self.show_grid4 = self.settings.get("show_grid4", "4音グリッド表示")
        self.show_hole_num = bool(self.settings.get("show_hole_num", True))
        self.hole_num_style = str(self.settings.get("hole_num_style", "実機標準 (低音ドット付)"))
        self.show_legend = bool(self.settings.get("show_legend", True))
        self.show_lookahead = bool(self.settings.get("show_lookahead", True))
        self.use_ring = bool(self.settings.get("use_ring", True))
        self.is_glow_on = bool(self.settings.get("show_glow", self.settings.get("is_glow_on", True)))
        self.note_opacity = int(self.settings.get("note_opacity", 100))

        # テーマカラー & 背景色
        bg_col_name = str(self.settings.get("canvas_bg_color", self.settings.get("bg_color", "#0d0d0d")))
        if "グリーン" in bg_col_name:
            self.color_bg = QColor("#00FF00")
        elif "ブルー" in bg_col_name:
            self.color_bg = QColor("#0000FF")
        elif "マゼンタ" in bg_col_name:
            self.color_bg = QColor("#FF00FF")
        elif bg_col_name.startswith("#"):
            self.color_bg = QColor(bg_col_name)
        else:
            self.color_bg = QColor("#0d0d0d")

        self.color_blow = QColor(self.settings.get("color_blow", "#FF9900"))
        self.color_draw = QColor(self.settings.get("color_draw", "#00FFFF"))
        self.color_blow_hi = QColor(get_lever_highlight_color(self.color_blow.name()))
        self.color_draw_hi = QColor(get_lever_highlight_color(self.color_draw.name()))
        self.color_measure_line = QColor("#3a3a3a")
        self.color_white = QColor("#FFFFFF")
        self.color_black = QColor("#000000")

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

        # 出力スタイル & タイトル
        self.export_style = self.settings.get("export_style", "完成動画 (背景・タイトル合成)")
        self.is_chromakey_mode = ("クロマキー素材" in self.export_style)
        self.is_transparent_mode = ("完全背景透過" in self.export_style)

        # 背景画像＆スキン
        self.bg_image_path = "" if (self.is_chromakey_mode or self.is_transparent_mode) else self.settings.get("bg_image_path", "")
        self.bg_dim_ratio = int(self.settings.get("bg_dim_ratio", 60))
        self.bg_fit_mode = self.settings.get("bg_fit_mode", "トリミング (比率維持拡大)")
        self.bg_rotation = int(self.settings.get("bg_rotation", 0))
        self.skin_enabled = bool(self.settings.get("skin_enabled", self.settings.get("use_skin", True)))

        # スキン画像
        skins_dir = get_portable_path("skins")
        mp_path = self.settings.get("skin_mouthpiece_path", "") or os.path.join(skins_dir, "マウスピース.png")
        self._img_mouthpiece = QImage(mp_path) if os.path.isfile(mp_path) else None
        lo_path = self.settings.get("skin_lever_off_path", "") or os.path.join(skins_dir, "レバーオフ.png")
        self._img_lever_off = QImage(lo_path) if os.path.isfile(lo_path) else None
        lon_path = self.settings.get("skin_lever_on_path", "") or os.path.join(skins_dir, "レバーオン.png")
        self._img_lever_on = QImage(lon_path) if os.path.isfile(lon_path) else None

        # 静的背景事前ベイク
        self.base_image = None
        self._build_static_base_image()

    def _build_static_base_image(self):
        """静的不変レイヤー (背景、ガイド線、90pxカバープレート、丸穴、穴番号、穴下音名、凡例) をQImageに事前描画"""
        w, h = self.width, self.height
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        if self.is_transparent_mode:
            img.fill(QColor(0, 0, 0, 0))
        else:
            img.fill(self.color_bg)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        base_h = float(get_canvas_height_by_ratio(self.aspect_ratio))
        scale = min(w / float(CANVAS_WIDTH), h / base_h)
        x_offset = (w - CANVAS_WIDTH * scale) * 0.5
        y_offset = (h - base_h * scale) * 0.5
        disp_w = CANVAS_WIDTH * scale
        disp_h = base_h * scale

        # 0. 背景画像 (完成動画モード時のみ)
        if not self.is_chromakey_mode and not self.is_transparent_mode and self.bg_image_path and os.path.isfile(self.bg_image_path):
            try:
                from PyQt6.QtGui import QImageReader
                reader = QImageReader(self.bg_image_path)
                reader.setAutoTransform(True)
                bg_raw = reader.read()
                if not bg_raw.isNull():
                    if self.bg_rotation != 0:
                        tr = QTransform()
                        tr.rotate(self.bg_rotation)
                        bg_raw = bg_raw.transformed(tr, Qt.TransformationMode.SmoothTransformation)

                    dest_rect = QRectF(x_offset, y_offset, disp_w, disp_h)
                    p.save()
                    p.setClipRect(dest_rect)
                    if "全体" in self.bg_fit_mode or "収める" in self.bg_fit_mode:
                        scaled = bg_raw.scaled(int(disp_w), int(disp_h), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        px = x_offset + (disp_w - scaled.width()) * 0.5
                        py = y_offset + (disp_h - scaled.height()) * 0.5
                        p.drawImage(QRectF(px, py, scaled.width(), scaled.height()), scaled)
                    elif any(k in self.bg_fit_mode for k in ("引き伸ば", "引き延ば", "比率無視", "変形", "ストレッチ")):
                        scaled = bg_raw.scaled(int(disp_w), int(disp_h), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        p.drawImage(dest_rect, scaled)
                    elif "横幅" in self.bg_fit_mode:
                        sc_f = disp_w / max(1, bg_raw.width())
                        new_h = int(bg_raw.height() * sc_f)
                        scaled = bg_raw.scaled(int(disp_w), max(1, new_h), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        py = y_offset + (disp_h - new_h) * 0.5
                        p.drawImage(QRectF(x_offset, py, disp_w, new_h), scaled)
                    elif "縦幅" in self.bg_fit_mode:
                        sc_f = disp_h / max(1, bg_raw.height())
                        new_w = int(bg_raw.width() * sc_f)
                        scaled = bg_raw.scaled(max(1, new_w), int(disp_h), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        px = x_offset + (disp_w - new_w) * 0.5
                        p.drawImage(QRectF(px, y_offset, new_w, disp_h), scaled)
                    else:
                        scaled = bg_raw.scaled(int(disp_w), int(disp_h), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                        sx = (scaled.width() - disp_w) * 0.5
                        sy = (scaled.height() - disp_h) * 0.5
                        p.drawImage(dest_rect, scaled, QRectF(sx, sy, disp_w, disp_h))

                    if self.bg_dim_ratio > 0:
                        dim_alpha = int(255 * (self.bg_dim_ratio / 100.0))
                        p.fillRect(dest_rect, QColor(0, 0, 0, dim_alpha))
                    p.restore()
            except Exception as e:
                print(f"[VideoExporter] 背景描画例外: {e}")

        y_center, y_col, y_str, y_hole, h_diag, h_str = get_y_trajectory_params(int(base_h), self.trajectory_mode)
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
                for idx in range(58):
                    gx = x_offset + (24.0 + idx * 16.0) * scale
                    p.setPen(QPen(grid_sub_col, max(1.0, 1.0 * scale)))
                    p.drawLine(QPointF(gx, y_offset), QPointF(gx, y_col_s))
                p.setPen(QPen(grid_bnd_col, max(1.0, 1.0 * scale)))
                p.drawLine(QPointF(x_offset + 24.0 * scale, y_offset), QPointF(x_offset + 24.0 * scale, y_col_s))
                p.drawLine(QPointF(x_offset + 936.0 * scale, y_offset), QPointF(x_offset + 936.0 * scale, y_col_s))

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
                        p.drawLine(QPointF(x_top, y_offset), QPointF(x_top, y_col_s))
                        if y_str_s > y_col_s:
                            p.drawLine(QPointF(x_top, y_col_s), QPointF(x_bot, y_str_s))
                        p.drawLine(QPointF(x_bot, y_str_s), QPointF(x_bot, y_hole_s))

        # 2. ハーモニカ本体 (高さ90pxカバープレート ＆ 丸穴 D_HOLE=30px)
        plate_rect = QRectF(x_start - 15.0 * scale, y_center_s - 45.0 * scale, total_w + 30.0 * scale, 90.0 * scale)
        if self.skin_enabled and self._img_mouthpiece and not self._img_mouthpiece.isNull():
            p.drawImage(plate_rect, self._img_mouthpiece)
        else:
            p.setPen(QPen(QColor("#777777"), max(1.0, 2.0 * scale)))
            p.setBrush(QColor("#2d2f31"))
            p.drawRoundedRect(plate_rect, 15.0 * scale, 15.0 * scale)

        self.font_hole.setPointSizeF(max(6.5, 10.0 * scale))
        for k, idx in enumerate(visible_indices):
            cx = x_start + k * w_pitch_s + w_pitch_s * 0.5
            hole_rect = QRectF(cx - d_hole_s * 0.5, y_center_s - d_hole_s * 0.5, d_hole_s, d_hole_s)
            p.setPen(QPen(QColor("#333333"), max(1.0, 1.2 * scale)))
            p.setBrush(QColor("#080808"))
            p.drawEllipse(hole_rect)

            if self.show_hole_num:
                num_rect = QRectF(cx - w_pitch_s * 0.5, y_center_s + 14.0 * scale, w_pitch_s, 20.0 * scale)
                num_str = format_hole_number(k, self.inst_type, getattr(self, "hole_num_style", "実機標準 (低音ドット付)"))
                _draw_bordered_text_qt(p, num_rect, num_str, self.font_hole, self.color_white, self.color_black, border_w=1.5 * scale)

        # 3. 穴下の音名表示 (4音グリッド / 1音表示)
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

            p.setPen(self.pen_none)
            p.setBrush(self.color_blow)
            p.drawEllipse(QPointF(leg_x + 12.0 * scale, leg_y + 13.0 * scale), 5.5 * scale, 5.5 * scale)
            p.setPen(self.color_white)
            p.drawText(QRectF(leg_x + 21.0 * scale, leg_y + 3.0 * scale, 54.0 * scale, 20.0 * scale),
                       Qt.AlignmentFlag.AlignVCenter, "吹 Blow")

            p.setPen(self.pen_none)
            p.setBrush(self.color_draw)
            p.drawEllipse(QPointF(leg_x + 12.0 * scale, leg_y + 31.0 * scale), 5.5 * scale, 5.5 * scale)
            p.setPen(self.color_white)
            p.drawText(QRectF(leg_x + 21.0 * scale, leg_y + 21.0 * scale, 54.0 * scale, 20.0 * scale),
                       Qt.AlignmentFlag.AlignVCenter, "吸 Draw")

        p.end()
        self.base_image = img

    def render_frame_bytes(self, cur_sec: float, title_overlay: dict = None,
                           t_in_video: float = 0.0, total_video_dur: float = 0.0,
                           fade_in: bool = False, fade_out: bool = False,
                           fade_title_mode: str = "フェード中もタイトル表示",
                           fade_in_sec: float = 1.5, fade_out_sec: float = 1.5) -> bytes:
        """指定秒数におけるオフスクリーン1フレームをBGRAバイト列で高速返却"""
        w, h = self.width, self.height
        frame_img = self.base_image.copy()

        p = QPainter(frame_img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        base_h = float(get_canvas_height_by_ratio(self.aspect_ratio))
        scale = min(w / float(CANVAS_WIDTH), h / base_h)
        x_offset = (w - CANVAS_WIDTH * scale) * 0.5
        y_offset = (h - base_h * scale) * 0.5

        y_center, y_col, y_str, y_hole, h_diag, h_str = get_y_trajectory_params(int(base_h), self.trajectory_mode)
        visible_indices, x_start_base, x_shift, x_shift_notes = get_layout_params(self.inst_type, 1.0)
        total_w_base = len(visible_indices) * W_PITCH

        x_start = x_offset + x_start_base * scale
        total_w = total_w_base * scale
        y_center_s = y_offset + y_center * scale
        y_hole_s = y_offset + y_hole * scale
        y_col_s = y_offset + y_col * scale
        y_str_s = y_offset + y_str * scale
        h_diag_s = h_diag * scale
        d_hole_s = D_HOLE * scale
        w_pitch_s = W_PITCH * scale
        is_straight_mode = ("垂直落下" in str(self.trajectory_mode))

        px_per_sec = 2.0 * self.default_bpm * self.note_speed_ratio * scale
        max_vis_sec = cur_sec + ((y_hole_s - y_offset) / px_per_sec) if px_per_sec > 0 else cur_sec + 5.0

        # 1. 小節線描画
        measures = self.timeline.measures_timeline if self.timeline else []
        m_secs = [m["start_sec"] for m in measures]
        y_plate_top = y_center_s - 45.0 * scale
        if self.show_bar_lines and measures and px_per_sec > 0:
            idx_m = bisect.bisect_left(m_secs, cur_sec - 0.5)
            p.setPen(self.pen_measure)
            p.setFont(self.font_measure)
            for m in measures[idx_m:]:
                m_sec = m["start_sec"]
                if m_sec > max_vis_sec:
                    break
                ym = y_hole_s - (m_sec - cur_sec) * px_per_sec
                if y_offset <= ym <= y_plate_top:
                    mx_start = x_start if is_straight_mode else (x_offset + 24.0 * scale)
                    mx_end = (x_start + total_w) if is_straight_mode else (x_offset + 936.0 * scale)
                    p.drawLine(QPointF(mx_start, ym), QPointF(mx_end, ym))
                    p.setPen(QColor("#777777"))
                    p.drawText(QPointF(mx_start + 6.0 * scale, ym - 3.0 * scale), str(m["measure_num"]))
                    p.setPen(self.pen_measure)

        # 2. 落下ノーツ描画
        active_holes = {}
        active_hole_cells = set()
        active_hole_notes = {}
        lever_pressed = False
        notes = self.timeline.main_notes if self.timeline else []
        n_secs = [n["start_sec"] for n in notes]

        if self.show_notes and notes and px_per_sec > 0:
            idx_n = bisect.bisect_left(n_secs, cur_sec - 5.0)
            for nd in notes[idx_n:]:
                if nd.get("is_muted", False):
                    continue
                n_start = nd["start_sec"]
                if n_start > max_vis_sec:
                    break
                n_end = nd["end_sec"]
                if n_end < cur_sec:
                    continue

                if n_start <= cur_sec < n_end:
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
                base_color = self.color_blow if is_blow else self.color_draw
                if self.note_opacity < 100:
                    alpha = int(255 * (self.note_opacity / 100.0))
                    fill_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)
                else:
                    fill_color = base_color

                use_split_slit = bool(is_lever_on and "スリット" in self.lever_deco_mode)

                if use_split_slit:
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

                    p.setPen(self.pen_none)
                    p.setBrush(fill_color)
                    p.drawPolygon(QPolygonF(left_pts))
                    p.drawPolygon(QPolygonF(right_pts))
                else:
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

                    p.setPen(self.pen_none)
                    p.setBrush(fill_color)
                    p.drawPolygon(QPolygonF(poly_pts))

                    if is_lever_on:
                        line_alpha = fill_color.alpha()
                        if "2本" in self.lever_deco_mode or "ダブル" in self.lever_deco_mode:
                            pen_col = self.color_blow_hi if is_blow else self.color_draw_hi
                            pen_d = QPen(QColor(pen_col.red(), pen_col.green(), pen_col.blue(), line_alpha), max(1.2, 1.4 * scale))
                            pen_d.setCapStyle(Qt.PenCapStyle.RoundCap)
                            p.setPen(pen_d)
                            d_off = max(1.6, 2.2 * scale)
                            line_pts_l = [QPointF(round(x_m_func(y_vis_top) - d_off), y_vis_top)]
                            for by in active_bends:
                                line_pts_l.append(QPointF(round(x_m_func(by) - d_off), by))
                            line_pts_l.append(QPointF(round(x_m_func(y_vis_bot) - d_off), y_vis_bot))
                            for lj in range(len(line_pts_l) - 1):
                                p.drawLine(line_pts_l[lj], line_pts_l[lj + 1])
                            line_pts_r = [QPointF(round(x_m_func(y_vis_top) + d_off), y_vis_top)]
                            for by in active_bends:
                                line_pts_r.append(QPointF(round(x_m_func(by) + d_off), by))
                            line_pts_r.append(QPointF(round(x_m_func(y_vis_bot) + d_off), y_vis_bot))
                            for lj in range(len(line_pts_r) - 1):
                                p.drawLine(line_pts_r[lj], line_pts_r[lj + 1])
                        elif "センターライン" in self.lever_deco_mode:
                            pen_col = self.color_blow_hi if is_blow else self.color_draw_hi
                            pen_c = QPen(QColor(pen_col.red(), pen_col.green(), pen_col.blue(), line_alpha), max(1.6, 2.0 * scale))
                            pen_c.setCapStyle(Qt.PenCapStyle.RoundCap)
                            p.setPen(pen_c)
                            line_pts = [QPointF(round(x_m_func(y_vis_top)), y_vis_top)]
                            for by in active_bends:
                                line_pts.append(QPointF(round(x_m_func(by)), by))
                            line_pts.append(QPointF(round(x_m_func(y_vis_bot)), y_vis_bot))
                            for lj in range(len(line_pts) - 1):
                                p.drawLine(line_pts[lj], line_pts[lj + 1])
                        elif "サイドライン" in self.lever_deco_mode:
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
                            p.setPen(self.pen_none)
                            p.setBrush(hi_col)
                            p.drawPolygon(QPolygonF(side_pts))

                # 落下追従音名ラベル描画
                if self.show_lookahead and self.lang_mode != "なし" and (not is_straight_mode or note_in_range) and (y_vis_bot - y_vis_top >= 8.0 * scale):
                    label_y = y_vis_bot - 8.5 * scale if (y_vis_bot - y_vis_top >= 17.0 * scale) else (y_vis_top + y_vis_bot) * 0.5
                    label_x = x_m_func(label_y)
                    lbl_text = nd["name_jp"] if self.lang_mode == "ドレミ" else nd["name_cde"]
                    self.font_note.setPointSizeF(max(6.0, 8.5 * scale))
                    text_rect = QRectF(label_x - 30.0 * scale, label_y - 10.0 * scale, 60.0 * scale, 20.0 * scale)
                    _draw_bordered_text_qt(p, text_rect, lbl_text, self.font_note, self.color_white, self.color_black, border_w=1.2 * scale)

        # 3. スライドレバー描画
        lever_x = x_start + total_w
        if self.skin_enabled and (self._img_lever_on or self._img_lever_off):
            lever_rect = QRectF(lever_x, y_center_s - 24.0 * scale, 48.0 * scale, 48.0 * scale)
            if lever_pressed and self._img_lever_on and not self._img_lever_on.isNull():
                p.drawImage(lever_rect, self._img_lever_on)
            elif not lever_pressed and self._img_lever_off and not self._img_lever_off.isNull():
                p.drawImage(lever_rect, self._img_lever_off)
            else:
                self._draw_procedural_lever(p, lever_x, y_center_s, scale, lever_pressed)
        else:
            self._draw_procedural_lever(p, lever_x, y_center_s, scale, lever_pressed)

        # 4. 発音中穴の丸穴LED・レバーリング・着地発光・穴下音名ハイライト
        show_4grid = (self.show_grid4 is True or "4音" in str(self.show_grid4))
        is_jp = (self.lang_mode == "ドレミ")

        for k, idx in enumerate(visible_indices):
            hole_num = idx + 1
            act = active_holes.get(hole_num)
            if act is not None:
                cx = x_start + k * w_pitch_s + w_pitch_s * 0.5
                act_color = self.color_blow if act == "吹" else self.color_draw

                # A. 丸穴LED点灯
                p.setPen(self.pen_none)
                p.setBrush(act_color)
                p.drawEllipse(QPointF(cx, y_center_s), (d_hole_s * 0.5) - 1.5, (d_hole_s * 0.5) - 1.5)

                # B. レバーリング連動
                if lever_pressed and self.use_ring:
                    p.setPen(QPen(act_color, max(2.0, 3.0 * scale)))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    ring_r = 21.0 * scale
                    p.drawEllipse(QPointF(cx, y_center_s), ring_r, ring_r)

                # C. 着地発光 (滑らかな放射状アルファグラデーション)
                if self.is_glow_on:
                    pie_r = 32.0 * scale
                    p.setPen(self.pen_none)
                    glow_grad = QRadialGradient(QPointF(cx, y_hole_s), pie_r)
                    glow_grad.setColorAt(0.0, QColor(255, 255, 255, 210))
                    glow_grad.setColorAt(0.5, QColor(255, 255, 255, 100))
                    glow_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                    p.setBrush(QBrush(glow_grad))
                    p.drawPie(QRectF(cx - pie_r, y_hole_s - pie_r, pie_r * 2.0, pie_r * 2.0), 0, 180 * 16)

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

                            p.setPen(QPen(QColor("#FFFFFF"), max(1.0, 1.5 * scale)))
                            p.setBrush(c_bg)
                            p.drawRect(c_rect)

                            if self.lang_mode != "なし":
                                cell_midi = h4.get((a_val, l_val))
                                cell_txt = get_note_name(cell_midi, is_japanese=is_jp) if cell_midi is not None else ""
                                p.setFont(self.font_grid4)
                                p.setPen(QColor("#000000"))
                                p.drawText(c_rect, Qt.AlignmentFlag.AlignCenter, cell_txt)
                elif self.lang_mode != "なし" and hole_num in active_hole_notes:
                    cur_note = active_hole_notes[hole_num]
                    note_text = get_note_name(cur_note, is_japanese=is_jp)
                    rect_note = QRectF(cx - w_pitch_s * 0.5, y_center_s + 50.0 * scale, w_pitch_s, 20.0 * scale)
                    _draw_bordered_text_qt(p, rect_note, note_text, self.font_note, self.color_white, self.color_black, border_w=2.0 * scale)

        # 5. タイトル配置テンプレート描画 & フェード処理
        fade_alpha = 0
        f_in_dur = max(0.1, float(fade_in_sec))
        f_out_dur = max(0.1, float(fade_out_sec))
        if fade_in and total_video_dur > 0 and t_in_video < f_in_dur:
            fade_alpha = int(255 * (1.0 - t_in_video / f_in_dur))
        elif fade_out and total_video_dur > 0 and t_in_video > (total_video_dur - f_out_dur):
            fade_alpha = int(255 * ((t_in_video - (total_video_dur - f_out_dur)) / f_out_dur))

        has_title = (not self.is_chromakey_mode and not self.is_transparent_mode and title_overlay and title_overlay.get("enabled", False))

        if has_title and fade_title_mode == "画面と一緒にフェードイン":
            self._draw_title_overlay(p, cur_sec, title_overlay, x_start, y_offset, total_w, scale)

        if fade_alpha > 0 and not self.is_transparent_mode:
            p.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, fade_alpha))

        if has_title and fade_title_mode != "画面と一緒にフェードイン":
            if not (fade_title_mode == "フェード中はタイトル非表示" and t_in_video < f_in_dur):
                self._draw_title_overlay(p, cur_sec, title_overlay, x_start, y_offset, total_w, scale)

        p.end()
        ptr = frame_img.constBits()
        ptr.setsize(frame_img.sizeInBytes())
        return bytes(ptr)

    def render_frame_qimage(self, cur_sec: float, title_overlay: dict = None) -> QImage:
        """指定秒数におけるオフスクリーン1フレームをQImageで返却 (静止画プレビュー用)"""
        raw_b = self.render_frame_bytes(cur_sec, title_overlay=title_overlay)
        return QImage(raw_b, self.width, self.height, self.width * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()

    render_single_frame_qimage = render_frame_qimage

    def _draw_title_overlay(self, painter, cur_sec, overlay_info, x_start, y_offset, total_w, scale):
        """タイトル配置テンプレート (イントロ中央 / 左上常時 / 右上常時 など)"""
        tpl = overlay_info.get("template", "なし")
        title_text = str(overlay_info.get("title", "")).strip()
        credit_text = str(overlay_info.get("credit", "")).strip()
        if tpl == "なし" or (not title_text and not credit_text):
            return

        w, h = self.width, self.height
        intro_dur = float(overlay_info.get("intro_dur", 2.5))
        show_intro = ("イントロ中央" in tpl and cur_sec < intro_dur)
        show_left = ("左上常時" in tpl)
        show_right = ("右上常時" in tpl)

        if show_intro:
            fade = 1.0
            if cur_sec < 0.35:
                fade = max(0.15, cur_sec / 0.35)
            elif cur_sec > intro_dur - 0.45:
                fade = max(0.0, (intro_dur - cur_sec) / 0.45)

            base_f_t = QFont("Meiryo UI", max(14, int(28.0 * scale)), QFont.Weight.Bold)
            base_f_c = QFont("Meiryo UI", max(10, int(15.0 * scale)), QFont.Weight.Bold)
            fm_t = QFontMetricsF(base_f_t)
            fm_c = QFontMetricsF(base_f_c)

            raw_w_t = fm_t.horizontalAdvance(title_text) if title_text else 0.0
            raw_w_c = fm_c.horizontalAdvance(credit_text) if credit_text else 0.0
            max_text_w = max(raw_w_t, raw_w_c)

            max_card_w = w * 0.88
            ideal_card_w = max(360.0 * scale, max_text_w + 80.0 * scale)
            card_w = min(max_card_w, ideal_card_w)
            card_h = (130.0 if (title_text and credit_text) else 90.0) * scale
            cx0 = (w - card_w) * 0.5
            cy0 = max(15.0 * scale, h * 0.22 - card_h * 0.5)
            card_rect = QRectF(cx0, cy0, card_w, card_h)

            painter.setPen(QPen(QColor(0, 210, 255, int(210 * fade)), max(1.0, 2.0 * scale)))
            painter.setBrush(QColor(12, 16, 26, int(225 * fade)))
            painter.drawRoundedRect(card_rect, 12.0 * scale, 12.0 * scale)

            # アクセントライン
            painter.setPen(QPen(QColor(255, 165, 30, int(200 * fade)), max(1.0, 2.0 * scale)))
            painter.drawLine(QPointF(cx0 + 18.0 * scale, cy0 + 6.0 * scale), QPointF(cx0 + card_w - 18.0 * scale, cy0 + 6.0 * scale))

            avail_w = card_w - 40.0 * scale
            f_t = _fit_font(title_text, base_f_t, avail_w, min_pt=max(8.0, 9.0 * scale))
            f_c = _fit_font(credit_text, base_f_c, avail_w, min_pt=max(6.0, 7.0 * scale))

            if title_text and credit_text:
                _draw_bordered_text_qt(painter, QRectF(cx0, cy0 + 12.0 * scale, card_w, 48.0 * scale), title_text, f_t, QColor(255, 255, 255, int(255 * fade)), QColor(0, 0, 0, int(255 * fade)), border_w=2.0 * scale)
                _draw_bordered_text_qt(painter, QRectF(cx0, cy0 + 68.0 * scale, card_w, 32.0 * scale), credit_text, f_c, QColor(0, 229, 255, int(240 * fade)), QColor(0, 0, 0, int(255 * fade)), border_w=1.5 * scale)
            elif title_text:
                _draw_bordered_text_qt(painter, card_rect, title_text, f_t, QColor(255, 255, 255, int(255 * fade)), QColor(0, 0, 0, int(255 * fade)), border_w=2.0 * scale)
            else:
                _draw_bordered_text_qt(painter, card_rect, credit_text, f_c, QColor(0, 229, 255, int(240 * fade)), QColor(0, 0, 0, int(255 * fade)), border_w=1.5 * scale)

        if (show_left or show_right) and (not show_intro or cur_sec >= intro_dur):
            base_f_t = QFont("Meiryo UI", max(10, int(13.0 * scale)), QFont.Weight.Bold)
            base_f_c = QFont("Meiryo UI", max(8, int(10.0 * scale)))
            fm_t = QFontMetricsF(base_f_t)
            fm_c = QFontMetricsF(base_f_c)

            raw_w_t = fm_t.horizontalAdvance(title_text) if title_text else 0.0
            raw_w_c = fm_c.horizontalAdvance(credit_text) if credit_text else 0.0
            max_text_w = max(raw_w_t, raw_w_c)

            max_card_w = w * 0.45
            ideal_card_w = max(120.0 * scale, max_text_w + 36.0 * scale)
            card_w = min(max_card_w, ideal_card_w)
            card_h = (52.0 if (title_text and credit_text) else 34.0) * scale
            cx0 = (w - card_w - 20.0 * scale) if show_right else (20.0 * scale)
            cy0 = 18.0 * scale
            card_rect = QRectF(cx0, cy0, card_w, card_h)

            painter.setPen(QPen(QColor(80, 130, 170, 180), max(1.0, 1.2 * scale)))
            painter.setBrush(QColor(14, 18, 28, 195))
            painter.drawRoundedRect(card_rect, 8.0 * scale, 8.0 * scale)

            avail_w = card_w - 20.0 * scale
            f_t = _fit_font(title_text, base_f_t, avail_w, min_pt=max(6.0, 7.0 * scale))
            f_c = _fit_font(credit_text, base_f_c, avail_w, min_pt=max(5.0, 6.0 * scale))

            if title_text and credit_text:
                _draw_bordered_text_qt(painter, QRectF(cx0, cy0 + 4.0 * scale, card_w, 24.0 * scale), title_text, f_t, self.color_white, self.color_black, border_w=1.5 * scale)
                _draw_bordered_text_qt(painter, QRectF(cx0, cy0 + 26.0 * scale, card_w, 20.0 * scale), credit_text, f_c, QColor("#B2EBF2"), self.color_black, border_w=1.0 * scale)
            elif title_text:
                _draw_bordered_text_qt(painter, card_rect, title_text, f_t, self.color_white, self.color_black, border_w=1.5 * scale)
            else:
                _draw_bordered_text_qt(painter, card_rect, credit_text, f_c, QColor("#B2EBF2"), self.color_black, border_w=1.0 * scale)

    def _draw_procedural_lever(self, painter, lever_x, y_center_s, scale, lever_pressed):
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


class VideoExportThread(QThread):
    """FFmpeg への非同期ストリーミング動画書き出しワーカースレッド"""

    sig_progress = pyqtSignal(int, int, float, float, float)  # frame, total_frames, elapsed_sec, fps, eta_sec
    sig_finished = pyqtSignal(bool, str, str)  # success, output_path, err_msg

    def __init__(self, timeline, export_config: dict, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.config = dict(export_config)
        self._is_cancelled = False
        self._ffmpeg_process = None

    def cancel(self):
        self._is_cancelled = True
        if self._ffmpeg_process:
            try:
                self._ffmpeg_process.terminate()
            except Exception:
                pass

    def run(self):
        temp_audio_path = None
        try:
            width = int(self.config.get("width", 1920))
            height = int(self.config.get("height", 1080))
            fps = int(self.config.get("fps", 60))
            aspect_ratio = self.config.get("aspect_ratio", "16:9")
            output_path = os.path.abspath(self.config.get("output_path", "output/export.mp4"))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            start_sec = max(0.0, float(self.config.get("start_sec", 0.0)))
            end_sec = float(self.config.get("end_sec", self.timeline.total_duration_sec if self.timeline else 60.0))
            duration_sec = max(0.5, end_sec - start_sec)

            # 余白・フェード・カウントイン設定
            intro_sec = float(self.config.get("intro_sec", 0.0))
            outro_sec = float(self.config.get("outro_sec", 2.0))
            fade_in = bool(self.config.get("fade_in", False))
            fade_out = bool(self.config.get("fade_out", False))
            fade_in_sec = float(self.config.get("fade_in_sec", 1.5))
            fade_out_sec = float(self.config.get("fade_out_sec", 1.5))
            fade_title_mode = str(self.config.get("fade_title_mode", "フェード中もタイトル表示"))

            is_count_in = bool(self.config.get("is_count_in", False))
            count_in_measures = int(self.config.get("count_in_measures", 0))
            is_metro = bool(self.config.get("is_metro", False))
            metronome_pattern = str(self.config.get("metronome_pattern", "標準（頭拍強調）"))

            num = getattr(self.timeline, "time_sig_num", 4) if self.timeline else 4
            den = getattr(self.timeline, "time_sig_den", 4) if self.timeline else 4
            bpm = getattr(self.timeline, "default_bpm", 120.0) if self.timeline else 120.0
            count_in_dur = ((60.0 / bpm) * (4.0 / den) * num * count_in_measures) if (is_count_in and count_in_measures > 0) else 0.0

            total_video_dur = intro_sec + count_in_dur + duration_sec + outro_sec
            total_frames = int(round(total_video_dur * fps))

            # 1. オフスクリーンレンダラー初期化
            export_style = self.config.get("settings", {}).get("export_style", "")
            is_transparent_mov = ("完全背景透過" in export_style or output_path.lower().endswith(".mov"))

            renderer = OffscreenVisualizerRenderer(
                timeline=self.timeline,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                settings=self.config.get("settings", {})
            )

            # 2. 音声合成 (WAVファイル作成)
            audio_source = str(self.config.get("audio_source", "MIDIガイド音 (内部音源)"))
            audio_path = str(self.config.get("audio_path", ""))
            ext_audio_pcm = None

            if "無音" in audio_source:
                temp_audio_path = None
            else:
                if audio_path and os.path.isfile(audio_path):
                    try:
                        from audio_engine import load_external_audio_pcm
                        ext_audio_pcm = load_external_audio_pcm(audio_path, sample_rate=44100)
                    except Exception as e:
                        print(f"[VideoExportThread] 外部音源デコードエラー: {e}")

                ext_audio_mode = str(self.config.get("ext_audio_mode", "頭出し確認 (再生:両方 / 動画:外部のみ)"))
                if ("伴奏音源" in audio_source or "マイク録音" in audio_source) and ext_audio_pcm is not None:
                    ext_audio_mode = "動画:外部のみ"

                ext_offset_ms = int(self.config.get("ext_audio_offset_ms", 0))
                ext_vol_pct = float(self.config.get("ext_audio_vol_pct", 100.0))
                yt_limiter = bool(self.config.get("yt_limiter", True))

                temp_audio_dir = os.path.join(os.path.dirname(output_path), "..", "temp")
                os.makedirs(temp_audio_dir, exist_ok=True)
                temp_audio_path = os.path.join(temp_audio_dir, f"export_synth_{int(time.time())}.wav")

                midi_notes = self.timeline.main_notes if self.timeline else []
                acc_notes = self.timeline.accomp_notes if self.timeline else []
                measures = self.timeline.measures_timeline if self.timeline else []
                current_bpm = bpm

                synthesize_midi_to_wav(
                    midi_notes=midi_notes,
                    current_bpm=current_bpm,
                    max_duration=duration_sec,
                    is_count_in=is_count_in,
                    is_metro=is_metro,
                    output_wav_path=temp_audio_path,
                    time_sig_num=num,
                    time_sig_den=den,
                    count_in_measures=count_in_measures,
                    measures_timeline=measures,
                    metronome_pattern=metronome_pattern,
                    ticks_per_beat=getattr(self.timeline, "ticks_per_beat", 480) if self.timeline else 480,
                    sample_rate=44100,
                    tick_to_sec_fn=getattr(self.timeline, "tick_to_sec", None),
                    accompaniment_notes=acc_notes,
                    part_play_mode=self.config.get("part_mode", "全パート再生"),
                    intro_sec=intro_sec,
                    outro_sec=outro_sec,
                    ext_audio_pcm=ext_audio_pcm,
                    ext_audio_mode=ext_audio_mode,
                    ext_audio_offset_ms=ext_offset_ms,
                    ext_audio_vol_pct=ext_vol_pct,
                    sec_a_in_song=start_sec,
                    yt_limiter=yt_limiter,
                    mixer_settings=self.config.get("mixer_settings", None)
                )

            # 3. FFmpeg コマンドライン構築
            cmd = [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-s", f"{width}x{height}",
                "-pix_fmt", "bgra",
                "-r", str(fps),
                "-i", "-",  # stdinから映像パイプ入力
            ]

            reverb_enabled = bool(self.config.get("reverb_enabled", False))
            reverb_type = self.config.get("reverb_type", "ルーム (自然な部屋鳴り)")
            reverb_wet_pct = int(self.config.get("reverb_wet_pct", 35))

            if temp_audio_path and os.path.isfile(temp_audio_path):
                cmd.extend(["-i", temp_audio_path])
                af_filters = []
                if reverb_enabled and reverb_wet_pct > 0:
                    af_filters.append(get_reverb_filter_arg(reverb_type, reverb_wet_pct))

                # 音声フェードイン・フェードアウトの連動 (動画課題 4)
                if fade_in and fade_in_sec > 0:
                    af_filters.append(f"afade=t=in:ss=0:d={fade_in_sec:.2f}")
                if fade_out and fade_out_sec > 0:
                    fade_out_st = max(0.0, total_video_dur - fade_out_sec)
                    af_filters.append(f"afade=t=out:st={fade_out_st:.2f}:d={fade_out_sec:.2f}")

                # 動画音声ボリューム制御 (動画課題 8)
                export_audio_vol_pct = float(self.config.get("export_audio_vol_pct", 100.0))
                if abs(export_audio_vol_pct - 100.0) > 0.5:
                    vol_gain = max(0.0, min(2.5, export_audio_vol_pct / 100.0))
                    af_filters.append(f"volume={vol_gain:.2f}")

                # YouTube True Peak リミッター (-1.0 dBFS ≒ 0.89125) をボリューム等の最終段に適用
                yt_limiter = bool(self.config.get("yt_limiter", True))
                if yt_limiter:
                    af_filters.append("alimiter=limit=0.89125:level=0:asc=0:attack=5:release=50")

                if af_filters:
                    cmd.extend(["-af", ",".join(af_filters)])

                if is_transparent_mov:
                    cmd.extend(["-c:a", "pcm_s16le", "-ar", "48000"])
                else:
                    cmd.extend(["-c:a", "aac", "-b:a", "320k", "-ar", "48000"])

            if is_transparent_mov:
                cmd.extend(["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", output_path])
            else:
                encoder = self.config.get("codec", "自動")
                if "mf" in encoder.lower() or "自動" in encoder or "gpu" in encoder.lower():
                    cmd.extend(["-c:v", "h264_mf", "-b:v", "10000k"])
                else:
                    cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "18"])
                cmd.extend(["-pix_fmt", "yuv420p", output_path])

            print(f"[VideoExportThread] FFmpeg command: {' '.join(cmd)}")

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self._ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )

            # stderr ドレインスレッド (Windowsパイプバッファ詰まりによるデッドロック防止)
            stderr_chunks = []
            def _drain_stderr_worker(proc):
                try:
                    while True:
                        chunk = proc.stderr.read(1024)
                        if not chunk:
                            break
                        stderr_chunks.append(chunk.decode("utf-8", errors="ignore"))
                except Exception:
                    pass

            t_drain = threading.Thread(target=_drain_stderr_worker, args=(self._ffmpeg_process,), daemon=True)
            t_drain.start()

            # 4. フレームレンダリング＆ストリーミングパイプ
            t_start = time.perf_counter()
            title_overlay = self.config.get("title_overlay", {})

            for f_idx in range(total_frames):
                if self._is_cancelled:
                    if self._ffmpeg_process:
                        try:
                            self._ffmpeg_process.terminate()
                            self._ffmpeg_process.wait(timeout=1.0)
                        except Exception:
                            pass
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except Exception:
                            pass
                    self.sig_finished.emit(False, "", "ユーザーによってキャンセルされました")
                    return

                t_in_video = f_idx / fps
                if t_in_video < intro_sec:
                    cur_sec = start_sec
                elif t_in_video < intro_sec + count_in_dur:
                    cur_sec = start_sec - (intro_sec + count_in_dur - t_in_video)
                elif t_in_video < intro_sec + count_in_dur + duration_sec:
                    cur_sec = start_sec + (t_in_video - (intro_sec + count_in_dur))
                else:
                    cur_sec = end_sec

                raw_bytes = renderer.render_frame_bytes(
                    cur_sec,
                    title_overlay=title_overlay,
                    t_in_video=t_in_video,
                    total_video_dur=total_video_dur,
                    fade_in=fade_in,
                    fade_out=fade_out,
                    fade_title_mode=fade_title_mode,
                    fade_in_sec=fade_in_sec,
                    fade_out_sec=fade_out_sec
                )

                try:
                    self._ffmpeg_process.stdin.write(raw_bytes)
                except Exception as e:
                    print(f"[VideoExportThread] stdin write error: {e}")
                    break

                if f_idx % 15 == 0 or f_idx == total_frames - 1:
                    t_now = time.perf_counter()
                    elapsed = max(0.001, t_now - t_start)
                    cur_fps = (f_idx + 1) / elapsed
                    rem_frames = total_frames - (f_idx + 1)
                    eta = rem_frames / cur_fps if cur_fps > 0 else 0.0
                    self.sig_progress.emit(f_idx + 1, total_frames, elapsed, cur_fps, eta)

            try:
                self._ffmpeg_process.stdin.close()
            except Exception:
                pass

            t_drain.join(timeout=2.0)
            ret_code = self._ffmpeg_process.wait()
            stderr_out = "".join(stderr_chunks)

            if ret_code == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                self.sig_finished.emit(True, output_path, "")
            else:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except Exception:
                        pass
                self.sig_finished.emit(False, "", f"FFmpeg error (code {ret_code}):\n{stderr_out[-500:]}")

        except Exception as e:
            self.sig_finished.emit(False, "", str(e))
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass


def render_single_frame_qimage(timeline, export_config: dict, cur_sec: float = 0.0) -> QImage:
    """指定時刻におけるオフスクリーン描画QImageを返却 (1フレーム静止画確認用)"""
    width = int(export_config.get("width", 1920))
    height = int(export_config.get("height", 1080))
    aspect_ratio = export_config.get("aspect_ratio", "16:9")
    renderer = OffscreenVisualizerRenderer(
        timeline=timeline,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        settings=export_config.get("settings", {})
    )
    title_overlay = export_config.get("title_overlay", {})
    return renderer.render_frame_qimage(cur_sec, title_overlay=title_overlay)

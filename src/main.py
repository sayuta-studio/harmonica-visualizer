# -*- coding: utf-8 -*-
"""
v3.0/main.py
Harmonica Visualizer v3.0 - メインエントリーポイント (PyQt6 64-bit OpenGL Edition)
- クラシックL型レイアウト（上部操作ストリップ ＋ 左側GPU全画面 ＋ 右側4タブ操作サイドバー）
- 60FPS〜144FPS ハードウェアアクセラレーション (V-Sync)
- 完全非同期ロックフリー共有クロック (GIL音声競合ゼロ)
- A-Bループ練習・小節ジャンプ・ステップアップ練習・移調・メトロノーム統合
- 将来機能（背景画像・マイク録音・外部音源・MP4出力）のUIプレースホルダー配置
"""

import os
import sys
import time
import copy
import numpy as np

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QFont, QKeySequence, QShortcut, QDragEnterEvent, QDropEvent,
    QPainter, QPen, QColor, QPixmap, QPolygon
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QSlider, QLabel, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QAbstractSpinBox, QMenu,
    QFileDialog, QFrame, QSizePolicy, QTabWidget, QScrollArea,
    QLineEdit, QColorDialog, QMessageBox, QInputDialog
)

from ipc_state import SharedClockBridge
from midi_timeline import MidiTimelineData
from gl_visualizer import HarmonicaGLWidget
from audio_engine import AudioEngine, AudioRecorder, AuditionPlayer, apply_harmonica_reverb_numpy
from dialogs import PartSelectDialog, AudioTrackMixerDialog
import settings_manager
import harmonica_map
from harmonica_map import CURRENT_SONG_PRESET, apply_fingering_preset
from config import get_portable_path

# 共通ダークモードスタイルシート (DAW仕様 クラシックL型)
MODERN_DARK_STYLE = f"""
QMainWindow {{
    background-color: #121215;
}}
QWidget {{
    color: #E0E0E6;
    font-family: 'Meiryo UI', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 11px;
}}
QFrame#panelFrame {{
    background-color: #18181D;
    border: 1px solid #282832;
    border-radius: 8px;
}}
QFrame#groupFrame {{
    background-color: #1C1C23;
    border: 1px solid #2A2A38;
    border-radius: 6px;
    padding: 4px;
}}
QFrame#lcdFrame {{
    background-color: #090C10;
    border: 1px solid #1E2836;
    border-radius: 6px;
    padding: 2px 8px;
}}
QLabel#lcdText {{
    color: #38BDF8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    font-weight: bold;
}}
QLabel#lcdStatus {{
    color: #34D399;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    font-weight: bold;
}}
QLabel#groupHeader {{
    color: #38BDF8;
    font-size: 11px;
    font-weight: bold;
}}
QLabel#statusMsg {{
    color: #FBBF24;
    font-size: 11px;
    font-weight: bold;
}}
QPushButton {{
    background-color: #262630;
    color: #F0F0F5;
    border: 1px solid #363645;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #343444;
    border-color: #4A4A60;
}}
QPushButton:pressed {{
    background-color: #1C1C24;
    border-color: #00BFFF;
}}
QPushButton#playBtn {{
    background-color: #006699;
    border-color: #0099DD;
    font-size: 12px;
    padding: 4px 14px;
}}
QPushButton#playBtn:hover {{
    background-color: #0088CC;
    border-color: #33BBFF;
}}
QPushButton#stopBtn {{
    background-color: #3A2020;
    border-color: #553030;
}}
QPushButton#stopBtn:hover {{
    background-color: #552828;
    border-color: #883A3A;
}}
QPushButton#recBtn {{
    background-color: #4A1515;
    border-color: #7A2525;
    color: #FFAAAA;
}}
QPushButton#recBtn:hover {{
    background-color: #6A1D1D;
    border-color: #AA3030;
}}
QPushButton#actionBtn {{
    background-color: #1E3A5F;
    border-color: #2E5C8A;
}}
QPushButton#actionBtn:hover {{
    background-color: #28507E;
    border-color: #3E7DBA;
}}
QPushButton#futureBtn {{
    background-color: #222228;
    color: #888899;
    border: 1px dashed #444455;
}}
QPushButton#futureBtn:hover {{
    background-color: #2A2A33;
    color: #AAAAFF;
    border-color: #666688;
}}
QComboBox {{
    background-color: #22222A;
    color: #FFFFFF;
    border: 1px solid #343442;
    border-radius: 4px;
    padding: 2px 20px 2px 6px;
    min-width: 48px;
}}
QComboBox:hover {{
    border-color: #00BFFF;
}}
QComboBox:disabled {{
    background-color: #16161D;
    color: #555566;
    border-color: #262632;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #2D2D3A;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    background-color: #1E1E26;
}}
QComboBox::drop-down:hover {{
    background-color: #282836;
}}
QComboBox::drop-down:disabled {{
    background-color: #14141A;
    border-left-color: #1E1E26;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94A3B8;
    width: 0px;
    height: 0px;
}}
QComboBox::down-arrow:hover {{
    border-top-color: #38BDF8;
}}
QComboBox::down-arrow:disabled {{
    border-top-color: #444455;
}}
QComboBox QAbstractItemView {{
    background-color: #1A1A22;
    border: 1px solid #383848;
    selection-background-color: #0088CC;
    color: #FFFFFF;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #22222A;
    color: #FFFFFF;
    border: 1px solid #343442;
    border-radius: 4px;
    padding: 2px 4px;
    font-weight: bold;
    font-size: 11px;
}}
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #00BFFF;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: #38BDF8;
    background-color: #1A1A24;
}}
QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: #16161D;
    color: #555566;
    border-color: #262632;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 0px;
    height: 0px;
    border: none;
}}
QLineEdit {{
    background-color: #22222A;
    color: #FFFFFF;
    border: 1px solid #343442;
    border-radius: 4px;
    padding: 2px 6px;
}}
QLineEdit:hover {{
    border-color: #00BFFF;
}}
QLineEdit:disabled {{
    background-color: #16161D;
    color: #555566;
    border-color: #262632;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: #252530;
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: #0099DD;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 1px solid #888888;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: #00E5FF;
    border-color: #FFFFFF;
}}
QLabel:disabled {{
    color: #555566;
}}
QCheckBox {{
    spacing: 5px;
    color: #C0C0D0;
}}
QCheckBox:disabled {{
    color: #555566;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #444455;
    background-color: #202028;
}}
QCheckBox::indicator:checked {{
    background-color: #0099DD;
    border-color: #00BFFF;
}}
QCheckBox::indicator:disabled {{
    background-color: #16161D;
    border-color: #262632;
}}
QTabWidget::pane {{
    border: 1px solid #282835;
    background-color: #16161C;
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: #202028;
    color: #A0A0B0;
    padding: 6px 12px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: bold;
    font-size: 11px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: #16161C;
    color: #38BDF8;
    border-bottom: 2px solid #00BFFF;
}}
QTabBar::tab:hover:!selected {{
    background-color: #282835;
    color: #FFFFFF;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QLabel#badgeLabel {{
    background-color: #0F2A1D;
    color: #00E676;
    border: 1px solid #165338;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 10px;
}}
QToolTip {{
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #38BDF8;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}
"""


class HarmonicaSeekSlider(QSlider):
    """A-Bループ区間ハイライト描画対応のカスタムシークスライダー"""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.loop_a_ratio = None
        self.loop_b_ratio = None
        self.loop_enabled = False

    def set_loop_range(self, a_ratio: float, b_ratio: float, enabled: bool = True):
        self.loop_a_ratio = a_ratio
        self.loop_b_ratio = b_ratio
        self.loop_enabled = enabled
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.loop_enabled and self.loop_a_ratio is not None and self.loop_b_ratio is not None:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w = self.width()
            h = self.height()
            margin = 7
            track_w = max(1, w - margin * 2)
            xa = margin + max(0.0, min(1.0, self.loop_a_ratio)) * track_w
            xb = margin + max(0.0, min(1.0, self.loop_b_ratio)) * track_w
            if xb > xa:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 229, 255, 60))
                p.drawRoundedRect(QRectF(xa, h * 0.5 - 3, xb - xa, 6), 3, 3)

                p.setPen(QPen(QColor("#00E5FF"), 2))
                p.drawLine(QPointF(xa, h * 0.5 - 7), QPointF(xa, h * 0.5 + 7))
                p.setPen(QPen(QColor("#FFD700"), 2))
                p.drawLine(QPointF(xb, h * 0.5 - 7), QPointF(xb, h * 0.5 + 7))
            p.end()


class MarqueeLabel(QLabel):
    """
    電光掲示板（マーキースクロール）対応ステータスラベル
    - 表示枠に収まる場合は静止表示
    - 表示枠を超える長文の場合:
      1. 先頭で約1.6秒静止
      2. 左へスムーズにスクロール
      3. 末尾で約1.2秒静止
      4. 最大2周スクロール後、先頭位置に戻って自動停止（静止）
      5. 停止中にマウスを乗せるとスクロールを再開
      6. setTextで新しい文言が設定されたら周回カウントをリセットして再判定
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._scroll_x = 0.0
        self._loop_count = 0
        self._max_loops = 2
        self._is_stopped = False
        self._state = "idle"
        self._pause_frames = 0
        self._padding_x = 8

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

        if text:
            self.setText(text)

    def setText(self, text: str):
        self._full_text = str(text) if text is not None else ""
        self._scroll_x = 0.0
        self._loop_count = 0
        self._is_stopped = False
        self._state = "pause_start"
        self._pause_frames = 55  # 55 * 30ms ≈ 1.65秒
        super().setText("")  # super側を空文字にしてQLabel既定のテキスト描画を抑止
        self.setToolTip(self._full_text)
        self._check_overflow()
        self.update()

    def text(self) -> str:
        return self._full_text

    def _check_overflow(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        avail_w = max(1, self.width() - self._padding_x * 2)
        if text_w > avail_w:
            if not self._is_stopped and not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._scroll_x = 0.0
            self._state = "idle"

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_overflow()

    def enterEvent(self, event):
        super().enterEvent(event)
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        avail_w = max(1, self.width() - self._padding_x * 2)
        if text_w > avail_w:
            if self._is_stopped:
                # 2周完了して停止している場合、マウスホバーでスクロール再開！
                self._is_stopped = False
                self._loop_count = 0
                self._scroll_x = 0.0
                self._state = "pause_start"
                self._pause_frames = 20  # ホバー時は少し短めの待機
                if not self._timer.isActive():
                    self._timer.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def _on_tick(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        avail_w = max(1, self.width() - self._padding_x * 2)

        if text_w <= avail_w:
            self._scroll_x = 0.0
            self._timer.stop()
            self._state = "idle"
            self.update()
            return

        max_scroll = text_w - avail_w + 14

        if self._state == "pause_start":
            self._pause_frames -= 1
            if self._pause_frames <= 0:
                self._state = "scrolling"

        elif self._state == "scrolling":
            self._scroll_x += 1.2
            if self._scroll_x >= max_scroll:
                self._scroll_x = max_scroll
                self._state = "pause_end"
                self._pause_frames = 40  # 末尾で約1.2秒待機

        elif self._state == "pause_end":
            self._pause_frames -= 1
            if self._pause_frames <= 0:
                self._loop_count += 1
                if self._loop_count >= self._max_loops:
                    # 2周完了：先頭に戻して停止
                    self._is_stopped = True
                    self._scroll_x = 0.0
                    self._timer.stop()
                    self._state = "idle"
                else:
                    # 2周目へ
                    self._scroll_x = 0.0
                    self._state = "pause_start"
                    self._pause_frames = 40

        self.update()

    def paintEvent(self, event):
        # スタイルシートの背景・角丸・枠線を描画
        super().paintEvent(event)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip_rect = self.rect().adjusted(self._padding_x, 1, -self._padding_x, -1)
        p.setClipRect(clip_rect)

        font = self.font()
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#FBBF24"))

        fm = p.fontMetrics()
        text_y = int((self.height() + fm.ascent() - fm.descent()) / 2)
        text_x = self._padding_x - int(self._scroll_x)

        p.drawText(text_x, text_y, self._full_text)
        p.end()


class HarmonicaMainWindow(QMainWindow):
    """v3.0 メインアプリケーションウィンドウ (クラシックL型レイアウト)"""

    sig_loop_wrapped = pyqtSignal()
    sig_playback_finished = pyqtSignal()

    def _set_elided_label_text(self, label: QLabel, text: str, full_tooltip: str = "", max_width: int = 280):
        """可変長テキスト・ファイル名を安全に中略表示 (ElideMiddle) し、ラベル幅の肥大化・枠はみ出しを防ぐ"""
        label.setMinimumWidth(0)
        label.setMaximumWidth(max_width)
        label.setToolTip(full_tooltip or text)
        fm = label.fontMetrics()
        elided = fm.elidedText(text, Qt.TextElideMode.ElideMiddle, max_width)
        label.setText(elided)

    def _configure_sidebar_combo(self, combo: QComboBox, max_width: int = 240):
        """サイドバー内コンボボックスの最小サイズヒント膨張を防ぎ、親フレームの横幅を固定枠内に保つ"""
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(1)
        if max_width > 0:
            combo.setMaximumWidth(max_width)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harmonica Visualizer v3.1.0 [PyQt6 64-bit OpenGL Edition]")
        self.resize(1380, 880)
        self.setMinimumSize(980, 680)
        self.setAcceptDrops(True)

        # 0. デフォルト3Dスキン生成
        import config
        config.generate_default_skins()

        # 1. ユーザー設定ロード
        self.user_settings = settings_manager.load_settings()

        # 2. 共有クロック・タイムライン・音響エンジン初期化
        self.clock = SharedClockBridge()
        self.timeline = MidiTimelineData()
        self.audio_engine = AudioEngine(self.clock)
        self.audio_recorder = AudioRecorder()
        self.audition_player = AuditionPlayer()
        self._ext_pcm = None
        self._ext_channel = None
        self._ext_pending_start = False
        self.is_seeking = False
        self._is_loading_midi = False
        self.loop_playback = bool(self.user_settings.get("loop_enabled", False))

        # 録音・外部音源・リバーブ状態
        self.is_recording = False
        self.last_recorded_path = None
        self.ext_audio_path = self.user_settings.get("ext_audio_path", "")
        self.ext_audio_mode = self.user_settings.get("ext_audio_mode", "頭出し確認 (再生:両方 / 動画:外部のみ)")
        self.ext_offset_ms = int(self.user_settings.get("ext_audio_offset_ms", 0))
        self.ext_volume = int(self.user_settings.get("ext_audio_volume", 80))
        self.reverb_enabled = bool(self.user_settings.get("reverb_enabled", False))
        self.reverb_type = self.user_settings.get("reverb_type", "ルーム (自然な部屋鳴り)")
        self.reverb_wet_pct = int(self.user_settings.get("reverb_wet_pct", 35))

        # ループ折り返し ＆ 曲末尾終了通知シグナル接続
        self.sig_loop_wrapped.connect(self._handle_loop_wrapped)
        self.audio_engine.on_loop_wrapped_callback = self.sig_loop_wrapped.emit
        self.sig_playback_finished.connect(self._handle_playback_finished)
        self.audio_engine.on_playback_finished_callback = self.sig_playback_finished.emit

        # 3. UIの構築 (L型構造)
        self._init_ui()
        self._setup_shortcuts()

        # 4. 定周期UI更新タイマー (30Hz) ＆ リバーブ変更デバウンスタイマー
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(33)
        self.ui_timer.timeout.connect(self._on_ui_tick)

        self._reverb_debounce_timer = QTimer(self)
        self._reverb_debounce_timer.setSingleShot(True)
        self._reverb_debounce_timer.setInterval(180)
        self._reverb_debounce_timer.timeout.connect(self._refresh_live_audition_reverb)

        # 外部音源ズレ補正のデバウンスタイマー (連打時の多重再生＆ディスクI/O抑制)
        self._ext_resync_timer = QTimer(self)
        self._ext_resync_timer.setSingleShot(True)
        self._ext_resync_timer.setInterval(60)
        self._ext_resync_timer.timeout.connect(self._do_ext_audio_resync)

        self._ext_save_timer = QTimer(self)
        self._ext_save_timer.setSingleShot(True)
        self._ext_save_timer.setInterval(500)
        self._ext_save_timer.timeout.connect(self._do_ext_offset_save)

        self.ui_timer.start()

        # 5. ユーザー設定の反映
        self._apply_user_settings()

        # 6. 組み込み高品位クロマチック音階デモを即座に展開・ロード
        self.timeline.load_demo(inst_type=self.inst_combo.currentText())
        if hasattr(self, "inst_combo") and self.timeline.inst_type:
            self.inst_combo.blockSignals(True)
            self.inst_combo.setCurrentText(self.timeline.inst_type)
            self.inst_combo.blockSignals(False)
        self.gl_widget.set_timeline_data(self.timeline)
        self.audio_engine.load_timeline(self.timeline)
        self.clock.set_total_duration(self.timeline.total_duration_sec)
        self.clock.set_anchor(0.0, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_STOPPED)

        try:
            cleaned = self.combo_count_in.currentText().replace("小節", "").strip().split()[0]
            ci_m = int(cleaned)
        except Exception:
            ci_m = 1
        self.audio_engine.set_count_in(ci_m)

        self._update_track_list()
        self._update_song_info_labels()
        self._reset_loop_ranges_to_song()
        self.gl_widget.on_fingering_changed_callback = self._on_canvas_fingering_changed
        self._visual_edit_target = "practice"
        self.combo_fing_preset.blockSignals(True)
        self.combo_fing_preset.setCurrentText(harmonica_map.CURRENT_SONG_PRESET)
        self.combo_fing_preset.blockSignals(False)

    # =========================================================================
    # UI構築: クラシックL型レイアウト
    # =========================================================================
    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # =====================================================================
        # 1. 上部操作パネル (スリムな3段ストリップ: ファイル/シーク/LCD/ループ/速度)
        # =====================================================================
        top_panel = QFrame(self)
        top_panel.setObjectName("panelFrame")
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(10, 6, 10, 6)
        top_layout.setSpacing(5)

        # --- 行 1: ファイル読込 + 曲名 + パート選択 + 小節ジャンプ + 速度% ---
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.btn_open = QPushButton("📂 開く", self)
        self.btn_open.setFixedWidth(68)
        self.btn_open.setToolTip("MIDIファイル (.mid, .midi) を開く (画面へのドラッグ＆ドロップも可)")
        self.btn_open.clicked.connect(self._on_open_file)
        row1.addWidget(self.btn_open)

        self.btn_recent_menu = QPushButton("▼", self)
        self.btn_recent_menu.setFixedWidth(22)
        self.btn_recent_menu.setToolTip("最近開いたMIDIファイルの履歴を表示")
        self.btn_recent_menu.clicked.connect(self._show_recent_files_menu)
        row1.addWidget(self.btn_recent_menu)

        # 曲名表示ボックス (伸縮)
        self.lbl_song_title = QLabel("Demo (Chromatic Scale).mid", self)
        self.lbl_song_title.setMinimumWidth(140)
        self.lbl_song_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_song_title.setStyleSheet("background-color: #0E0E12; border: 1px solid #22222E; border-radius: 4px; padding: 2px 8px; color: #38BDF8; font-weight: bold;")
        row1.addWidget(self.lbl_song_title, stretch=1)

        # パート選択ボタン & モード
        self.btn_track_detail = QPushButton("🎼 パート", self)
        self.btn_track_detail.setFixedWidth(72)
        self.btn_track_detail.setToolTip("MIDIトラック一覧から主旋律（複数選択で合奏・ハモリ複合可）と伴奏を選択")
        self.btn_track_detail.clicked.connect(self._on_open_part_dialog)
        row1.addWidget(self.btn_track_detail)

        self.part_combo = QComboBox(self)
        self.part_combo.addItems(["全パート再生", "主旋律ソロ", "伴奏のみ(カラオケ)"])
        self.part_combo.setFixedWidth(124)
        self.part_combo.setToolTip("再生パート切替：全パート / 主旋律ソロ / 伴奏のみ(カラオケ)")
        self.part_combo.setCurrentText(self.user_settings.get("part_mode", "全パート再生"))
        self.part_combo.currentTextChanged.connect(self._on_part_mode_changed)
        row1.addWidget(self.part_combo)

        row1.addWidget(QLabel("|", self))

        # 小節ジャンプ
        row1.addWidget(QLabel("小節:", self))
        self.spin_jump = QSpinBox(self)
        self.spin_jump.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_jump.setRange(1, 999)
        self.spin_jump.setValue(1)
        self.spin_jump.setFixedWidth(46)
        self.spin_jump.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_jump.setToolTip("移動先の小節番号を指定 [直接入力してEnterで移動 / マウスホイールで増減 / +・- キー]")
        row1.addWidget(self.spin_jump)

        self.lbl_jump_total = QLabel("/ 1 小節", self)
        row1.addWidget(self.lbl_jump_total)

        self.btn_jump = QPushButton("移動", self)
        self.btn_jump.setFixedWidth(42)
        self.btn_jump.setToolTip("指定した小節の先頭へジャンプ")
        self.btn_jump.clicked.connect(self._on_jump_measure)
        row1.addWidget(self.btn_jump)

        row1.addWidget(QLabel("|", self))

        # 再生速度% (ステップボタン付き)
        row1.addWidget(QLabel("速度:", self))
        self.btn_spd_minus = QPushButton("-5", self)
        self.btn_spd_minus.setFixedWidth(32)
        self.btn_spd_minus.setToolTip("再生テンポを -5% 遅くする [↓キー]")
        self.btn_spd_minus.clicked.connect(lambda: self._adjust_speed(-5))
        row1.addWidget(self.btn_spd_minus)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.speed_slider.setRange(10, 300)
        self.speed_slider.setValue(int(round(float(self.user_settings.get("speed_ratio", 1.0)) * 100)))
        self.speed_slider.setFixedWidth(80)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        row1.addWidget(self.speed_slider)

        self.lbl_speed_val = QLabel(f"{self.speed_slider.value()}%", self)
        self.lbl_speed_val.setFixedWidth(48)
        row1.addWidget(self.lbl_speed_val)

        self.btn_spd_plus = QPushButton("+5", self)
        self.btn_spd_plus.setFixedWidth(32)
        self.btn_spd_plus.setToolTip("再生テンポを +5% 速くする [↑キー]")
        self.btn_spd_plus.clicked.connect(lambda: self._adjust_speed(5))
        row1.addWidget(self.btn_spd_plus)

        self.btn_spd_100 = QPushButton("100%", self)
        self.btn_spd_100.setFixedWidth(52)
        self.btn_spd_100.setToolTip("再生テンポを原曲速度 (100%) に戻す")
        self.btn_spd_100.clicked.connect(lambda: self.speed_slider.setValue(100))
        row1.addWidget(self.btn_spd_100)

        top_layout.addLayout(row1)

        # --- 行 2: 再生トランスポート ➔ シークバー ➔ LCD風ステータス液晶 ---
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        # トランスポートボタン群 (頭出し・5秒送り戻しを削除しシーク領域拡大)
        self.btn_play = QPushButton("▶ 再生", self)
        self.btn_play.setObjectName("playBtn")
        self.btn_play.setFixedWidth(92)
        self.btn_play.setToolTip("再生 / 一時停止 [Space / Enter]")
        self.btn_play.clicked.connect(self._on_play_toggle)
        row2.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ 停止", self)
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setFixedWidth(62)
        self.btn_stop.setToolTip("停止して曲の先頭(またはA点)へ戻る [Esc / Backspace / 0]")
        self.btn_stop.clicked.connect(self._on_stop)
        row2.addWidget(self.btn_stop)

        # 録音ボタン (ワンクリックマイク録音)
        self.btn_rec = QPushButton("🔴 録音", self)
        self.btn_rec.setObjectName("recBtn")
        self.btn_rec.setFixedWidth(68)
        self.btn_rec.setToolTip("マイク演奏録音の開始 / 停止 [R / *]")
        self.btn_rec.clicked.connect(self._on_record_toggle)
        row2.addWidget(self.btn_rec)

        row2.addWidget(QLabel("|", self))

        # シークスライダー
        self.lbl_time_cur = QLabel("00:00.0", self)
        self.lbl_time_cur.setFixedWidth(56)
        self.lbl_time_cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(self.lbl_time_cur)

        self.seek_slider = HarmonicaSeekSlider(Qt.Orientation.Horizontal, self)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setToolTip("再生位置のシーク (キャンバス上のマウスホイールでも前後移動可)")
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        row2.addWidget(self.seek_slider, stretch=1)

        self.lbl_time_total = QLabel("00:13.6", self)
        self.lbl_time_total.setFixedWidth(56)
        self.lbl_time_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(self.lbl_time_total)

        row2.addWidget(QLabel("|", self))

        # LCD風ステータス液晶
        lcd_frame = QFrame(self)
        lcd_frame.setObjectName("lcdFrame")
        lcd_layout = QHBoxLayout(lcd_frame)
        lcd_layout.setContentsMargins(6, 2, 6, 2)
        lcd_layout.setSpacing(12)

        self.lbl_lcd_status = QLabel("停止中", self)
        self.lbl_lcd_status.setObjectName("lcdStatus")
        self.lbl_lcd_status.setFixedWidth(58)
        self.lbl_lcd_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lcd_layout.addWidget(self.lbl_lcd_status)

        self.lbl_lcd_pos = QLabel("位置: 001小節 . 01拍", self)
        self.lbl_lcd_pos.setObjectName("lcdText")
        lcd_layout.addWidget(self.lbl_lcd_pos)

        self.lbl_lcd_sig = QLabel("拍子: 4/4", self)
        self.lbl_lcd_sig.setObjectName("lcdText")
        lcd_layout.addWidget(self.lbl_lcd_sig)

        self.lbl_lcd_bpm = QLabel("テンポ: 120BPM(100%)", self)
        self.lbl_lcd_bpm.setObjectName("lcdText")
        lcd_layout.addWidget(self.lbl_lcd_bpm)

        row2.addWidget(lcd_frame)
        top_layout.addLayout(row2)

        # --- 行 3: メトロノーム + A-Bループ + 移調 + 拡張ステータスバー + サイドバー切替 ---
        row3 = QHBoxLayout()
        row3.setSpacing(6)

        row3.addWidget(QLabel("拍子音:", self))
        self.combo_metro = QComboBox(self)
        self.combo_metro.addItems(["標準（頭拍強調）", "小節頭のみ", "全拍均一", "なし"])
        self.combo_metro.setFixedWidth(138)
        self.combo_metro.setToolTip("メトロノームのクリック音パターンを選択")
        self.combo_metro.setCurrentText(self.user_settings.get("metronome_mode", "標準（頭拍強調）"))
        self.combo_metro.currentTextChanged.connect(self._on_metro_changed)
        row3.addWidget(self.combo_metro)

        row3.addWidget(QLabel("前奏:", self))
        self.combo_count_in = QComboBox(self)
        self.combo_count_in.addItems(["0小節", "1小節", "2小節"])
        self.combo_count_in.setFixedWidth(64)
        count_in_cfg = self.user_settings.get("count_in_mode", "1小節")
        if " " in count_in_cfg:
            count_in_cfg = count_in_cfg.replace(" ", "")
        self.combo_count_in.setCurrentText(count_in_cfg)
        self.combo_count_in.setToolTip("再生開始前に鳴らすカウントイン（準備拍）の小節数")
        self.combo_count_in.currentTextChanged.connect(self._on_count_in_changed)
        row3.addWidget(self.combo_count_in)

        row3.addWidget(QLabel("|", self))

        # A-Bループ
        self.chk_loop = QCheckBox("ループ", self)
        self.chk_loop.setChecked(self.loop_playback)
        self.chk_loop.setToolTip("A-B区間リピート再生のON/OFF [ショートカット: L]")
        self.chk_loop.toggled.connect(self._on_loop_toggled)
        row3.addWidget(self.chk_loop)

        self.btn_set_a = QPushButton("[A]", self)
        self.btn_set_a.setObjectName("actionBtn")
        self.btn_set_a.setFixedWidth(32)
        self.btn_set_a.setToolTip("現在の再生小節をループ開始点(A点)に設定 [ショートカット: A]")
        self.btn_set_a.clicked.connect(self._on_set_loop_a)
        row3.addWidget(self.btn_set_a)

        self.spin_loop_a = QSpinBox(self)
        self.spin_loop_a.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_loop_a.setKeyboardTracking(False)
        self.spin_loop_a.setRange(1, 999)
        self.spin_loop_a.setValue(1)
        self.spin_loop_a.setFixedWidth(44)
        self.spin_loop_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_loop_a.setToolTip("ループ開始小節 (A点) [直接入力 / マウスホイールで変更]")
        self.spin_loop_a.valueChanged.connect(self._on_loop_spin_changed)
        row3.addWidget(self.spin_loop_a)

        row3.addWidget(QLabel("〜", self))

        self.btn_set_b = QPushButton("[B]", self)
        self.btn_set_b.setObjectName("actionBtn")
        self.btn_set_b.setFixedWidth(32)
        self.btn_set_b.setToolTip("現在の再生小節をループ終了点(B点)に設定 [ショートカット: B]")
        self.btn_set_b.clicked.connect(self._on_set_loop_b)
        row3.addWidget(self.btn_set_b)

        self.spin_loop_b = QSpinBox(self)
        self.spin_loop_b.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_loop_b.setKeyboardTracking(False)
        self.spin_loop_b.setRange(1, 999)
        self.spin_loop_b.setValue(12)
        self.spin_loop_b.setFixedWidth(44)
        self.spin_loop_b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_loop_b.setToolTip("ループ終了小節 (B点) [直接入力 / マウスホイールで変更]")
        self.spin_loop_b.valueChanged.connect(self._on_loop_spin_changed)
        row3.addWidget(self.spin_loop_b)

        self.btn_reset_ab = QPushButton("全曲", self)
        self.btn_reset_ab.setFixedWidth(42)
        self.btn_reset_ab.setToolTip("A-Bループ区間を解除して全曲(1小節目〜末尾)に戻す")
        self.btn_reset_ab.clicked.connect(self._on_reset_loop_ab)
        row3.addWidget(self.btn_reset_ab)

        row3.addWidget(QLabel("|", self))

        # 移調 (±24半音＝2オクターブ対応 ＆ ±1Octボタン ＆ 伴奏移調連動)
        row3.addWidget(QLabel("移調:", self))

        self.btn_trans_down_oct = QPushButton("-12", self)
        self.btn_trans_down_oct.setFixedWidth(36)
        self.btn_trans_down_oct.setToolTip("1オクターブ下げる (-12半音)")
        self.btn_trans_down_oct.clicked.connect(lambda: self.spin_transpose.setValue(max(-24, self.spin_transpose.value() - 12)))
        row3.addWidget(self.btn_trans_down_oct)

        self.btn_trans_minus_1 = QPushButton("-1", self)
        self.btn_trans_minus_1.setFixedWidth(28)
        self.btn_trans_minus_1.setToolTip("半音下げる (-1半音)")
        self.btn_trans_minus_1.clicked.connect(lambda: self.spin_transpose.setValue(max(-24, self.spin_transpose.value() - 1)))
        row3.addWidget(self.btn_trans_minus_1)

        self.spin_transpose = QSpinBox(self)
        self.spin_transpose.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_transpose.setRange(-24, 24)
        self.spin_transpose.setValue(int(self.user_settings.get("transpose", 0)))
        self.spin_transpose.setSuffix("st")
        self.spin_transpose.setFixedWidth(46)
        self.spin_transpose.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_transpose.setToolTip("半音単位の移調 (-24〜+24半音 / ±2オクターブ) [直接入力 / マウスホイールで変更]")
        self.spin_transpose.valueChanged.connect(self._on_transpose_changed)
        row3.addWidget(self.spin_transpose)

        self.btn_trans_plus_1 = QPushButton("+1", self)
        self.btn_trans_plus_1.setFixedWidth(28)
        self.btn_trans_plus_1.setToolTip("半音上げる (+1半音)")
        self.btn_trans_plus_1.clicked.connect(lambda: self.spin_transpose.setValue(min(24, self.spin_transpose.value() + 1)))
        row3.addWidget(self.btn_trans_plus_1)

        self.btn_trans_up_oct = QPushButton("+12", self)
        self.btn_trans_up_oct.setFixedWidth(36)
        self.btn_trans_up_oct.setToolTip("1オクターブ上げる (+12半音)")
        self.btn_trans_up_oct.clicked.connect(lambda: self.spin_transpose.setValue(min(24, self.spin_transpose.value() + 12)))
        row3.addWidget(self.btn_trans_up_oct)

        self.chk_transpose_accomp = QCheckBox("伴奏連動", self)
        self.chk_transpose_accomp.setChecked(bool(self.user_settings.get("transpose_accomp", True)))
        self.chk_transpose_accomp.setToolTip("ON: 伴奏も一緒に移調 / OFF: 主旋律ノーツのみ移調（伴奏は原曲キー維持）")
        self.chk_transpose_accomp.toggled.connect(self._on_transpose_changed)
        row3.addWidget(self.chk_transpose_accomp)

        # ステータス即時メッセージ (大幅拡張 stretch=1 / 電光掲示板マーキー対応)
        self.lbl_status_msg = MarqueeLabel("準備完了", self)
        self.lbl_status_msg.setObjectName("statusMsg")
        self.lbl_status_msg.setMinimumWidth(140)
        self.lbl_status_msg.setStyleSheet("background-color: #101016; border: 1px solid #282836; border-radius: 4px; padding: 2px 8px; color: #FBBF24; font-weight: bold;")
        self.lbl_status_msg.setToolTip("直近の操作・通知メッセージ")
        row3.addWidget(self.lbl_status_msg, stretch=1)

        # サイドバー折りたたみトグルボタン
        self.btn_toggle_sidebar = QPushButton("▶ 全画面", self)
        self.btn_toggle_sidebar.setFixedWidth(68)
        self.btn_toggle_sidebar.setToolTip("右側の操作サイドバーを表示 / 非表示にしてキャンバスを全画面化")
        self.btn_toggle_sidebar.clicked.connect(self._on_toggle_sidebar)
        row3.addWidget(self.btn_toggle_sidebar)

        top_layout.addLayout(row3)
        main_layout.addWidget(top_panel)

        # =====================================================================
        # 2. メインL字領域 (左側: OpenGL GPUビジュアライザー / 右側: 4タブサイドバー)
        # =====================================================================
        lower_layout = QHBoxLayout()
        lower_layout.setSpacing(6)

        # --- 左側: OpenGL GPUビジュアライザー (100%全空間自動伸縮) ---
        self.gl_widget = HarmonicaGLWidget(self.clock, parent=self)
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.gl_widget.seek_step_requested.connect(self._on_canvas_wheel_seek)
        self.gl_widget.note_mute_changed.connect(self._on_canvas_note_mute_changed)
        lower_layout.addWidget(self.gl_widget, stretch=1)

        # --- 右側: 4タブ切替サイドバー (幅370px) ---
        self.sidebar_frame = QFrame(self)
        self.sidebar_frame.setObjectName("panelFrame")
        self.sidebar_frame.setFixedWidth(370)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(6)

        self.tab_widget = QTabWidget(self.sidebar_frame)

        # 4つのタブを構築
        self._build_tab_practice()
        self._build_tab_design()
        self._build_tab_audio()
        self._build_tab_export()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        sidebar_layout.addWidget(self.tab_widget, stretch=1)

        # サイドバー最下部: リアルタイム GPU レンダリング FPS バッジ
        sb_foot = QHBoxLayout()
        self.lbl_fps = QLabel("● GPU 60.0 FPS", self)
        self.lbl_fps.setObjectName("badgeLabel")
        sb_foot.addWidget(self.lbl_fps)
        sb_foot.addStretch()

        btn_save_all = QPushButton("💾 設定を保存", self)
        btn_save_all.setToolTip("現在の全設定を settings.json に保存")
        btn_save_all.clicked.connect(lambda: (self._save_current_settings(), self.lbl_status_msg.setText("💾 設定を保存しました")))
        sb_foot.addWidget(btn_save_all)

        sidebar_layout.addLayout(sb_foot)
        lower_layout.addWidget(self.sidebar_frame)

        main_layout.addLayout(lower_layout, stretch=1)

    # =========================================================================
    # タブ 1: 【🎵 練習】
    # =========================================================================
    def _build_tab_practice(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 6, 4, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setMaximumWidth(340)
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 1. 🎷 ハーモニカモデル ＆ 運指設定グループ
        f_inst = QFrame()
        f_inst.setObjectName("groupFrame")
        f_inst.setMaximumWidth(328)
        l_inst = QVBoxLayout(f_inst)
        l_inst.setContentsMargins(6, 6, 6, 6)
        l_inst.setSpacing(6)

        l_inst.addWidget(QLabel("🎷 <b>ハーモニカモデル:</b>"))
        r_model = QHBoxLayout()
        self.inst_combo = QComboBox(self)
        self.inst_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.inst_combo.setMinimumContentsLength(8)
        self.inst_combo.addItems([
            "16穴 (64音・C調)",
            "14穴 (56音・C調)",
            "12穴 (48音・C調・標準)",
            "12穴 (48音・バス)"
        ])
        self.inst_combo.setCurrentText(self.user_settings.get("inst_type", "16穴 (64音・C調)"))
        self.inst_combo.setToolTip("使用するクロマチックハーモニカの穴数・音域モデルを選択")
        self.inst_combo.currentTextChanged.connect(self._on_inst_changed)
        self._configure_sidebar_combo(self.inst_combo, max_width=180)
        r_model.addWidget(self.inst_combo, stretch=1)

        self.btn_range_check = QPushButton("🔍 音域チェック", self)
        self.btn_range_check.setFixedWidth(92)
        self.btn_range_check.setStyleSheet("font-size: 11px; padding: 3px 6px;")
        self.btn_range_check.setToolTip("現在の曲の音域と選択中モデルの適合性を診断し、最適な推奨移調量を提案")
        self.btn_range_check.clicked.connect(self._on_check_pitch_range)
        r_model.addWidget(self.btn_range_check)
        l_inst.addLayout(r_model)

        r_fing = QHBoxLayout()
        r_fing.addWidget(QLabel("運指規則:"))
        self.combo_fing_preset = QComboBox(self)
        self.combo_fing_preset.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_fing_preset.addItems(["スライド最小化 (標準)", "スライド優先 (異名同音)"])
        from harmonica_map import normalize_fingering_preset
        self.combo_fing_preset.setCurrentText(normalize_fingering_preset(self.user_settings.get("fingering_preset", "スライド最小化 (標準)")))
        self.combo_fing_preset.setToolTip("同音異穴が存在するノーツの自動運指選択ルール（最小化＝スライドOFF優先 / 優先＝同音異名ON活用）")
        self.combo_fing_preset.currentTextChanged.connect(self._on_fingering_preset_changed)
        self._configure_sidebar_combo(self.combo_fing_preset, max_width=230)
        r_fing.addWidget(self.combo_fing_preset, stretch=1)
        l_inst.addLayout(r_fing)

        r_mono = QHBoxLayout()
        r_mono.addWidget(QLabel("重なり音:"))
        self.combo_monophonic_mode = QComboBox(self)
        self.combo_monophonic_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_monophonic_mode.addItems(["すべて有効", "高音優先 (上パート)", "低音優先 (下パート)"])
        self.combo_monophonic_mode.setToolTip("和音やハモリが重なった際の単音化ルール (キャンバス上のShift+右クリックで個別変更可)")
        self.combo_monophonic_mode.currentTextChanged.connect(self._on_monophonic_mode_changed)
        self._configure_sidebar_combo(self.combo_monophonic_mode, max_width=230)
        r_mono.addWidget(self.combo_monophonic_mode, stretch=1)
        l_inst.addLayout(r_mono)

        r_edit_modes = QVBoxLayout()
        r_edit_modes.setSpacing(4)

        self.chk_fing_edit = QCheckBox("🎯 かえ指モード (運指切替) [F]", self)
        self.chk_fing_edit.setToolTip("ON: キャンバス上の白枠ノーツをクリックして穴番号・吹吸を循環切替 (ショートカット: F)")
        self.chk_fing_edit.toggled.connect(self._on_fingering_edit_mode_toggled)
        r_edit_modes.addWidget(self.chk_fing_edit)

        self.chk_mute_edit = QCheckBox("🔇 非表示モード (ノーツ除外/復活) [M]", self)
        self.chk_mute_edit.setToolTip("ON: 再生中や停止中に画面上のノーツを直接クリックして発音／非表示（除外）を切替 (ショートカット: M)")
        self.chk_mute_edit.toggled.connect(self._on_mute_edit_mode_toggled)
        r_edit_modes.addWidget(self.chk_mute_edit)

        self.chk_hide_muted_notes = QCheckBox("除外ノーツを画面から消す", self)
        self.chk_hide_muted_notes.setToolTip("OFF: 除外ノーツを半透明グレーで表示 (非表示モードで再クリック復帰可) / ON: 画面から完全非表示 (非表示モード中は薄く半透明表示)")
        self.chk_hide_muted_notes.toggled.connect(self._on_hide_muted_notes_toggled)
        r_edit_modes.addWidget(self.chk_hide_muted_notes)

        l_inst.addLayout(r_edit_modes)

        r_fbtns = QHBoxLayout()
        self.btn_edit_fing = QPushButton("🎼 運指一覧エディタ...", self)
        self.btn_edit_fing.setToolTip("曲全体のノーツ運指・発音/除外を一覧テーブルで検索・編集します")
        self.btn_edit_fing.clicked.connect(self._on_open_fingering_dialog)
        r_fbtns.addWidget(self.btn_edit_fing, stretch=1)

        self.btn_reset_fing = QPushButton("🔄 初期化", self)
        self.btn_reset_fing.setFixedWidth(72)
        self.btn_reset_fing.setToolTip("この曲の個別変え指・除外ノーツ設定をすべて初期状態にリセットします")
        self.btn_reset_fing.setStyleSheet("background-color: #4A1D1D; color: #FECACA; font-weight: bold; border-radius: 4px; padding: 4px;")
        self.btn_reset_fing.clicked.connect(self._on_reset_song_fingering)
        r_fbtns.addWidget(self.btn_reset_fing)
        l_inst.addLayout(r_fbtns)

        v_box.addWidget(f_inst)

        # 2. ⚡ ノーツ落下速度グループ
        f_fall = QFrame()
        f_fall.setObjectName("groupFrame")
        f_fall.setMaximumWidth(328)
        l_fall = QVBoxLayout(f_fall)
        l_fall.setContentsMargins(6, 6, 6, 6)
        r_fall = QHBoxLayout()
        r_fall.addWidget(QLabel("落下速度:"))
        self.fall_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.fall_slider.setRange(50, 200)
        self.fall_slider.setValue(int(round(float(self.user_settings.get("fall_speed_ratio", 1.0)) * 100)))
        self.fall_slider.setToolTip("ノーツの視覚的な落下スピード倍率 (再生テンポには影響しません)")
        self.fall_slider.valueChanged.connect(self._on_fall_speed_changed)
        r_fall.addWidget(self.fall_slider)

        self.lbl_fall_val = QLabel(f"{self.fall_slider.value()}%", self)
        self.lbl_fall_val.setMinimumWidth(36)
        r_fall.addWidget(self.lbl_fall_val)

        btn_fall_100 = QPushButton("100%", self)
        btn_fall_100.setFixedWidth(44)
        btn_fall_100.setToolTip("落下速度を標準(100%)にリセット")
        btn_fall_100.clicked.connect(lambda: self.fall_slider.setValue(100))
        r_fall.addWidget(btn_fall_100)

        l_fall.addLayout(r_fall)
        v_box.addWidget(f_fall)

        # 3. 📈 ステップアップ練習グループ
        f_stepup = QFrame()
        f_stepup.setObjectName("groupFrame")
        f_stepup.setMaximumWidth(328)
        l_sp = QVBoxLayout(f_stepup)
        l_sp.setContentsMargins(6, 6, 6, 6)
        l_sp.setSpacing(6)

        l_sp.addWidget(QLabel("📈 <b>ステップアップ練習 (A-Bループ連動):</b>"))
        self.chk_stepup = QCheckBox("ループ毎にテンポ自動UP", self)
        self.chk_stepup.setChecked(bool(self.user_settings.get("stepup_enabled", False)))
        self.chk_stepup.setToolTip("A-Bループが1周するごとに再生速度を自動的に引き上げて反復練習します")
        self.chk_stepup.toggled.connect(self._on_stepup_toggled)
        l_sp.addWidget(self.chk_stepup)

        r_sp1 = QHBoxLayout()
        r_sp1.addWidget(QLabel("開始:"))
        self.spin_sp_start = QSpinBox(self)
        self.spin_sp_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_sp_start.setRange(10, 300)
        self.spin_sp_start.setValue(int(self.user_settings.get("stepup_start_pct", 70)))
        self.spin_sp_start.setSuffix("%")
        self.spin_sp_start.setFixedWidth(54)
        self.spin_sp_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_sp_start.setToolTip("練習開始時の再生速度% [直接入力 / マウスホイールで変更]")
        self.spin_sp_start.valueChanged.connect(lambda _: self._save_current_settings())
        r_sp1.addWidget(self.spin_sp_start)

        r_sp1.addWidget(QLabel("目標:"))
        self.spin_sp_target = QSpinBox(self)
        self.spin_sp_target.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_sp_target.setRange(10, 300)
        self.spin_sp_target.setValue(int(self.user_settings.get("stepup_target_pct", 100)))
        self.spin_sp_target.setSuffix("%")
        self.spin_sp_target.setFixedWidth(54)
        self.spin_sp_target.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_sp_target.setToolTip("到達目標の再生速度% [直接入力 / マウスホイールで変更]")
        self.spin_sp_target.valueChanged.connect(lambda _: self._save_current_settings())
        r_sp1.addWidget(self.spin_sp_target)

        r_sp1.addWidget(QLabel("増分:"))
        self.combo_sp_step = QComboBox(self)
        self.combo_sp_step.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_sp_step.setMinimumContentsLength(4)
        self.combo_sp_step.addItems(["+1%", "+2%", "+5%", "+10%"])
        self.combo_sp_step.setCurrentText(f"+{self.user_settings.get('stepup_step_pct', 5)}%")
        self.combo_sp_step.setFixedWidth(58)
        self.combo_sp_step.setToolTip("ループ1周ごとの速度増加量")
        self.combo_sp_step.currentTextChanged.connect(lambda _: self._save_current_settings())
        r_sp1.addWidget(self.combo_sp_step)
        l_sp.addLayout(r_sp1)
        v_box.addWidget(f_stepup)

        # 4. 🔊 練習時の再生音源 (伴奏切替)
        f_prac_audio = QFrame()
        f_prac_audio.setObjectName("groupFrame")
        f_prac_audio.setMaximumWidth(328)
        l_pa = QVBoxLayout(f_prac_audio)
        l_pa.setContentsMargins(6, 6, 6, 6)
        l_pa.setSpacing(6)
        l_pa.addWidget(QLabel("🔊 <b>練習時の再生音源 (伴奏切替):</b>"))

        r_pa = QHBoxLayout()
        r_pa.addWidget(QLabel("再生音源:"))
        self.combo_prac_audio_mode = QComboBox(self)
        self.combo_prac_audio_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_prac_audio_mode.addItems([
            "ガイド音のみ (伴奏ミュート)",
            "伴奏 ＋ ガイド音 (両方再生)",
            "伴奏のみ (ガイド音オフ)"
        ])
        raw_mode = str(self.user_settings.get("ext_audio_mode", "伴奏 ＋ ガイド音 (両方再生)"))
        if "伴奏のみ" in raw_mode or "外部音源のみ" in raw_mode:
            cur_p_mode = "伴奏のみ (ガイド音オフ)"
        elif "ガイド音のみ" in raw_mode or "外部音源オフ" in raw_mode or "伴奏ミュート" in raw_mode:
            cur_p_mode = "ガイド音のみ (伴奏ミュート)"
        else:
            cur_p_mode = "伴奏 ＋ ガイド音 (両方再生)"
        self.combo_prac_audio_mode.setCurrentText(cur_p_mode)
        self.combo_prac_audio_mode.setToolTip("練習再生時に鳴らす音源の構成（MIDIガイド単体練習 vs 外部伴奏合わせ）")
        self._configure_sidebar_combo(self.combo_prac_audio_mode, max_width=230)
        self.combo_prac_audio_mode.currentTextChanged.connect(self._on_ext_mode_changed)
        r_pa.addWidget(self.combo_prac_audio_mode, stretch=1)
        l_pa.addLayout(r_pa)

        self.lbl_prac_ext_status = QLabel("伴奏音源: 未設定 (MIDIガイド再生)", self)
        self.lbl_prac_ext_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.lbl_prac_ext_status.setWordWrap(True)
        if getattr(self, "ext_audio_path", "") and os.path.exists(self.ext_audio_path):
            self.lbl_prac_ext_status.setText(f"伴奏音源: {os.path.basename(self.ext_audio_path)}")
            self.lbl_prac_ext_status.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        l_pa.addWidget(self.lbl_prac_ext_status)

        v_box.addWidget(f_prac_audio)

        v_box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "🎵 練習")

    # =========================================================================
    # タブ 2: 【🎨 画面作り】
    # =========================================================================
    def _build_tab_design(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 6, 4, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setMaximumWidth(340)
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 0. 🎯 編集対象ターゲットの切り替え (v3.1.0)
        f_target = QFrame()
        f_target.setObjectName("groupFrame")
        f_target.setMaximumWidth(328)
        f_target.setStyleSheet("QFrame#groupFrame { border: 1px solid #38BDF8; background-color: #0F172A; }")
        l_target = QVBoxLayout(f_target)
        l_target.setContentsMargins(6, 6, 6, 6)
        l_target.setSpacing(4)
        l_target.addWidget(QLabel("🎯 <b>編集対象のスタイルを選択:</b>"))

        r_tgt = QHBoxLayout()
        self.combo_visual_target = QComboBox(self)
        self.combo_visual_target.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_visual_target.addItems([
            "🎯 練習用の画面スタイル (標準)",
            "🎬 動画プリセットの画面スタイル"
        ])
        self.combo_visual_target.setToolTip("編集・カスタマイズする表示対象（日常の練習画面 vs 動画書き出しプリセット）を切り替え")
        self._configure_sidebar_combo(self.combo_visual_target, max_width=310)
        self.combo_visual_target.currentTextChanged.connect(self._on_visual_target_changed)
        r_tgt.addWidget(self.combo_visual_target)
        l_target.addLayout(r_tgt)

        self.lbl_visual_target_hint = QLabel("現在: 練習用スタイルを編集中（常時16:9・日常の作業環境）", self)
        self.lbl_visual_target_hint.setStyleSheet("color: #38BDF8; font-size: 10px;")
        self.lbl_visual_target_hint.setWordWrap(True)
        l_target.addWidget(self.lbl_visual_target_hint)

        # 動画プリセット選択・保存操作バー (画面作りタブ直結)
        self.w_design_preset_bar = QWidget(self)
        l_dpb = QVBoxLayout(self.w_design_preset_bar)
        l_dpb.setContentsMargins(0, 4, 0, 0)
        l_dpb.setSpacing(4)

        r_dpb_top = QHBoxLayout()
        r_dpb_top.addWidget(QLabel("プリセット:"))
        self.combo_design_preset = QComboBox(self)
        self.combo_design_preset.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._configure_sidebar_combo(self.combo_design_preset, max_width=230)
        self.combo_design_preset.setToolTip("編集対象の動画プリセット（動画出力タブと完全同期）")
        self.combo_design_preset.currentTextChanged.connect(self._on_video_preset_changed)
        r_dpb_top.addWidget(self.combo_design_preset, stretch=1)
        l_dpb.addLayout(r_dpb_top)

        r_dpb_btns = QHBoxLayout()
        self.btn_design_preset_save = QPushButton("💾 保存", self)
        self.btn_design_preset_save.setToolTip("現在の画面デザインを選択中のプリセットに上書き保存")
        self.btn_design_preset_save.clicked.connect(self._on_save_video_preset)
        r_dpb_btns.addWidget(self.btn_design_preset_save)

        self.btn_design_preset_save_as = QPushButton("➕ 別名保存...", self)
        self.btn_design_preset_save_as.setToolTip("現在の画面デザインで新しい動画プリセットを作成")
        self.btn_design_preset_save_as.clicked.connect(self._on_save_as_video_preset)
        r_dpb_btns.addWidget(self.btn_design_preset_save_as)

        self.btn_design_preset_reset = QPushButton("↺ 初期化", self)
        self.btn_design_preset_reset.setToolTip("公式プリセットは初期値へ復元、自作プリセットは削除します")
        self.btn_design_preset_reset.clicked.connect(self._on_reset_or_delete_video_preset)
        r_dpb_btns.addWidget(self.btn_design_preset_reset)
        l_dpb.addLayout(r_dpb_btns)

        self.w_design_preset_bar.setVisible(False)
        l_target.addWidget(self.w_design_preset_bar)
        v_box.addWidget(f_target)

        # 1. 演奏・ノーツ表示（練習・動画共通）
        f_disp = QFrame()
        f_disp.setObjectName("groupFrame")
        f_disp.setMaximumWidth(328)
        l_disp = QVBoxLayout(f_disp)
        l_disp.setContentsMargins(6, 6, 6, 6)
        l_disp.setSpacing(6)

        l_disp.addWidget(QLabel("🎵 <b>演奏・ノーツ表示（共通）:</b>"))

        r_traj = QHBoxLayout()
        r_traj.addWidget(QLabel("ノーツ軌道:"))
        self.traj_combo = QComboBox(self)
        self.traj_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.traj_combo.addItems(["3段階 (練習標準)", "2段階 (ビジュアル)", "垂直落下 (穴直上)"])
        self.traj_combo.setCurrentText(self.user_settings.get("trajectory_mode", "3段階 (練習標準)"))
        self.traj_combo.setToolTip("ノーツが画面上部からハーモニカ穴へ向かう軌道の形状")
        self.traj_combo.currentTextChanged.connect(self._on_traj_changed)
        self._configure_sidebar_combo(self.traj_combo, max_width=230)
        r_traj.addWidget(self.traj_combo, stretch=1)
        l_disp.addLayout(r_traj)

        r_lang = QHBoxLayout()
        r_lang.addWidget(QLabel("音名表記:"))
        self.lang_combo = QComboBox(self)
        self.lang_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lang_combo.addItems(["ドレミ", "CDE"])
        self.lang_combo.setCurrentText(self.user_settings.get("lang_mode", "ドレミ"))
        self.lang_combo.setToolTip("画面上の音名表示（ドレミ / 英語音名 CDE）")
        self.lang_combo.currentTextChanged.connect(self._on_lang_changed)
        self._configure_sidebar_combo(self.lang_combo, max_width=230)
        r_lang.addWidget(self.lang_combo, stretch=1)
        l_disp.addLayout(r_lang)
        v_box.addWidget(f_disp)

        # 2. 画面比率（動画制作・構図プレビュー）
        self.f_ratio = QFrame()
        self.f_ratio.setObjectName("groupFrame")
        self.f_ratio.setMaximumWidth(328)
        self.f_ratio.setEnabled(False)  # 初期状態（練習用スタイル編集時）は16:9固定
        l_ratio = QVBoxLayout(self.f_ratio)
        l_ratio.setContentsMargins(6, 6, 6, 6)
        l_ratio.setSpacing(6)

        l_ratio.addWidget(QLabel("📐 <b>画面比率（動画プリセット編集時のみ有効）:</b>"))

        r_ratio = QHBoxLayout()
        r_ratio.addWidget(QLabel("比率:"))
        self.ratio_combo = QComboBox(self)
        self.ratio_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ratio_combo.addItems(["16:9 (横長・練習標準)", "9:16 (縦長・Shorts/TikTok)", "4:3 (スタンダード)"])
        saved_ratio = str(self.user_settings.get("aspect_ratio", "16:9"))
        for item_idx in range(self.ratio_combo.count()):
            if saved_ratio in self.ratio_combo.itemText(item_idx):
                self.ratio_combo.setCurrentIndex(item_idx)
                break
        self.ratio_combo.setToolTip("書き出す動画の構図に合わせてフレームをプレビュー表示します（練習スタイル編集時は16:9固定）")
        self.ratio_combo.currentTextChanged.connect(self._on_ratio_changed)
        self._configure_sidebar_combo(self.ratio_combo, max_width=230)
        r_ratio.addWidget(self.ratio_combo, stretch=1)
        l_ratio.addLayout(r_ratio)

        lbl_ratio_note = QLabel("※「🎬 動画プリセットの画面スタイル」選択時のみ変更可能です。（「🎯 練習用」は常に広々とした16:9表示になります）")
        lbl_ratio_note.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 1.3;")
        lbl_ratio_note.setWordWrap(True)
        l_ratio.addWidget(lbl_ratio_note)
        v_box.addWidget(self.f_ratio)

        # 2. カラーテーマ & 吹吸カラー選択
        f_col = QFrame()
        f_col.setObjectName("groupFrame")
        f_col.setMaximumWidth(328)
        l_col = QVBoxLayout(f_col)
        l_col.setContentsMargins(6, 6, 6, 6)
        l_col.setSpacing(6)

        r_theme = QHBoxLayout()
        r_theme.addWidget(QLabel("カラーテーマ:"))
        self.combo_theme = QComboBox(self)
        self.combo_theme.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_theme.addItems(["ノーマル", "サクラ", "クールネオン", "モノクロ", "カスタム"])
        self.combo_theme.setCurrentText(self.user_settings.get("color_theme", "ノーマル"))
        self.combo_theme.setToolTip("ノーツ全体のプリセットカラーテーマ")
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed)
        self._configure_sidebar_combo(self.combo_theme, max_width=230)
        r_theme.addWidget(self.combo_theme, stretch=1)
        l_col.addLayout(r_theme)

        r_pickers = QHBoxLayout()
        r_pickers.addWidget(QLabel("吹(Blow):"))
        self.btn_col_blow = QPushButton("", self)
        self.btn_col_blow.setFixedSize(48, 22)
        self.btn_col_blow.setToolTip("吹音ノーツの色を選択")
        self._update_color_btn(self.btn_col_blow, self.user_settings.get("color_blow", "#FF5500"))
        self.btn_col_blow.clicked.connect(self._choose_color_blow)
        r_pickers.addWidget(self.btn_col_blow)

        r_pickers.addSpacing(10)
        r_pickers.addWidget(QLabel("吸(Draw):"))
        self.btn_col_draw = QPushButton("", self)
        self.btn_col_draw.setFixedSize(48, 22)
        self.btn_col_draw.setToolTip("吸音ノーツの色を選択")
        self._update_color_btn(self.btn_col_draw, self.user_settings.get("color_draw", "#00BFFF"))
        self.btn_col_draw.clicked.connect(self._choose_color_draw)
        r_pickers.addWidget(self.btn_col_draw)
        l_col.addLayout(r_pickers)

        r_deco = QHBoxLayout()
        r_deco.addWidget(QLabel("レバーON装飾:"))
        self.combo_lever = QComboBox(self)
        self.combo_lever.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_lever.addItems(["センターライン (芯線)", "センターライン2本 (ダブル芯線)", "センター半割 (スリット)", "サイドライン (明暗適応)", "装飾なし"])
        self.combo_lever.setCurrentText(self.user_settings.get("lever_deco_mode", "センターライン (芯線)"))
        self.combo_lever.setToolTip("スライドレバーON（半音）ノーツの視覚的アクセント装飾")
        self.combo_lever.currentTextChanged.connect(self._on_lever_changed)
        self._configure_sidebar_combo(self.combo_lever, max_width=230)
        r_deco.addWidget(self.combo_lever, stretch=1)
        l_col.addLayout(r_deco)

        r_op = QHBoxLayout()
        r_op.addWidget(QLabel("不透過度:"))
        self.slider_op = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_op.setRange(20, 100)
        self.slider_op.setValue(int(self.user_settings.get("note_opacity", 100)))
        self.slider_op.setToolTip("ノーツバー全体の不透過度 (透明度)")
        self.slider_op.valueChanged.connect(self._on_opacity_changed)
        r_op.addWidget(self.slider_op)
        self.lbl_op_val = QLabel(f"{self.slider_op.value()}%", self)
        r_op.addWidget(self.lbl_op_val)
        l_col.addLayout(r_op)
        v_box.addWidget(f_col)

        # 3. 表示要素チェックボックス群 (2列グリッド)
        f_chk = QFrame()
        f_chk.setObjectName("groupFrame")
        f_chk.setMaximumWidth(328)
        l_chk = QVBoxLayout(f_chk)
        l_chk.setContentsMargins(6, 6, 6, 6)
        l_chk.setSpacing(4)

        grid_chk = QGridLayout()
        grid_chk.setHorizontalSpacing(10)
        grid_chk.setVerticalSpacing(4)

        self.chk_notes = QCheckBox("落下ノーツ", self)
        self.chk_notes.setChecked(bool(self.user_settings.get("show_notes", True)))
        self.chk_notes.setToolTip("落下してくるノーツバーを表示")
        self.chk_notes.toggled.connect(lambda v: (self.gl_widget.set_show_notes(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_notes, 0, 0)

        self.chk_lookahead = QCheckBox("ノーツ音名", self)
        self.chk_lookahead.setChecked(bool(self.user_settings.get("show_lookahead", True)))
        self.chk_lookahead.setToolTip("落下ノーツの直上に音名(ドレミ/CDE)を追従表示")
        self.chk_lookahead.toggled.connect(lambda v: (self.gl_widget.set_show_lookahead(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_lookahead, 0, 1)

        self.chk_grid = QCheckBox("レーンガイド線", self)
        self.chk_grid.setChecked(bool(self.user_settings.get("show_grid", True)))
        self.chk_grid.setToolTip("縦の穴レーン境界線とオクターブ変形ガイド線を表示")
        self.chk_grid.toggled.connect(lambda v: (self.gl_widget.set_show_grid(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_grid, 1, 0)

        self.chk_hole_num = QCheckBox("穴番号", self)
        self.chk_hole_num.setChecked(bool(self.user_settings.get("show_hole_num", True)))
        self.chk_hole_num.setToolTip("ハーモニカ各ホールの穴番号を表示")
        self.chk_hole_num.toggled.connect(lambda v: (self.gl_widget.set_show_hole_num(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_hole_num, 1, 1)

        self.chk_ring = QCheckBox("レバーONリング", self)
        self.chk_ring.setChecked(bool(self.user_settings.get("show_ring", self.user_settings.get("use_ring", True))))
        self.chk_ring.setToolTip("スライドレバーON発音時に穴の外周リングを強調点灯")
        self.chk_ring.toggled.connect(lambda v: (self.gl_widget.set_use_ring(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_ring, 2, 0)

        self.chk_glow = QCheckBox("着地グロー発光", self)
        self.chk_glow.setChecked(bool(self.user_settings.get("show_glow", True)))
        self.chk_glow.setToolTip("ノーツが穴に着地した瞬間に扇形のグロー発光エフェクトを表示")
        self.chk_glow.toggled.connect(lambda v: (self.gl_widget.set_show_glow(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_glow, 2, 1)

        self.chk_legend = QCheckBox("吹吸の凡例", self)
        self.chk_legend.setChecked(bool(self.user_settings.get("show_legend", True)))
        self.chk_legend.setToolTip("画面右側（スライドレバー上部）に吹(Blow)/吸(Draw)のカラー凡例を表示")
        self.chk_legend.toggled.connect(lambda v: (self.gl_widget.set_show_legend(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_legend, 3, 0)

        self.chk_bar_lines = QCheckBox("小節線", self)
        self.chk_bar_lines.setChecked(bool(self.user_settings.get("show_bar_lines", True)))
        self.chk_bar_lines.setToolTip("横の小節境界線と小節番号を表示")
        self.chk_bar_lines.toggled.connect(lambda v: (self.gl_widget.set_show_bar_lines(v), self._save_current_settings()))
        grid_chk.addWidget(self.chk_bar_lines, 3, 1)

        l_chk.addLayout(grid_chk)

        r_hole_style = QHBoxLayout()
        r_hole_style.addWidget(QLabel("穴番号表記:"))
        self.combo_hole_num_style = QComboBox(self)
        self.combo_hole_num_style.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_hole_num_style.addItems(["実機標準 (低音ドット付)", "通し番号 (1〜)"])
        cur_hstyle = self.user_settings.get("hole_num_style", "実機標準 (低音ドット付)")
        self.combo_hole_num_style.setCurrentText("通し番号 (1〜)" if "通し番号" in cur_hstyle else "実機標準 (低音ドット付)")
        self.combo_hole_num_style.setToolTip("実機表記（C4基準1〜12、16穴:·1〜·4、14穴:・・）か、左端基準の通し番号（1〜）かを選択")
        self.combo_hole_num_style.currentTextChanged.connect(self._on_hole_num_style_changed)
        self._configure_sidebar_combo(self.combo_hole_num_style, max_width=230)
        r_hole_style.addWidget(self.combo_hole_num_style, stretch=1)
        l_chk.addLayout(r_hole_style)

        r_grid4 = QHBoxLayout()
        r_grid4.addWidget(QLabel("穴下ノート表示:"))
        self.combo_grid4 = QComboBox(self)
        self.combo_grid4.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_grid4.addItems(["4音グリッド表示", "1音表示 (従来)", "非表示"])
        self.combo_grid4.setCurrentText(self.user_settings.get("grid4_mode", self.user_settings.get("show_grid4", "4音グリッド表示")))
        self.combo_grid4.setToolTip("穴の下に配置する音名（田の字4音グリッド / 単一吹音表示 / 非表示）")
        self.combo_grid4.currentTextChanged.connect(self._on_grid4_changed)
        self._configure_sidebar_combo(self.combo_grid4, max_width=230)
        r_grid4.addWidget(self.combo_grid4, stretch=1)
        l_chk.addLayout(r_grid4)
        v_box.addWidget(f_chk)

        # 4. 背景画像 & 減光 (コントラスト)
        f_bg = QFrame()
        f_bg.setObjectName("groupFrame")
        f_bg.setMaximumWidth(328)
        l_bg = QVBoxLayout(f_bg)
        l_bg.setContentsMargins(6, 6, 6, 6)
        l_bg.setSpacing(6)
        l_bg.addWidget(QLabel("🖼️ <b>背景画像 & 減光 (コントラスト):</b>"))

        self.chk_bg_enable = QCheckBox("背景画像の表示", self)
        self.chk_bg_enable.setChecked(bool(self.user_settings.get("bg_image_enabled", True)))
        self.chk_bg_enable.setToolTip("カスタム背景画像描画のON/OFF")
        self.chk_bg_enable.toggled.connect(self._on_bg_enable_toggled)
        l_bg.addWidget(self.chk_bg_enable)

        cur_bg = self.user_settings.get("bg_image_path", "")
        self.lbl_bg_info = QLabel(self)
        self.lbl_bg_info.setMinimumWidth(0)
        self.lbl_bg_info.setStyleSheet("color: #94A3B8; font-size: 10px;")
        if cur_bg and os.path.exists(cur_bg):
            self._set_elided_label_text(self.lbl_bg_info, f"画像: {os.path.basename(cur_bg)}", cur_bg, max_width=270)
        else:
            self.lbl_bg_info.setText("画像: 未設定 (ダーク背景)")
            self.lbl_bg_info.setToolTip("")
        l_bg.addWidget(self.lbl_bg_info)

        r_bg_btn = QHBoxLayout()
        self.btn_select_bg = QPushButton("📂 画像選択...", self)
        self.btn_select_bg.setToolTip("背景画像 (PNG/JPG/WebP等) を選択 [画面へのドラッグ＆ドロップも可]")
        self.btn_select_bg.clicked.connect(self._on_select_bg_image)
        r_bg_btn.addWidget(self.btn_select_bg)

        self.btn_clear_bg = QPushButton("🗑 解除", self)
        self.btn_clear_bg.setFixedWidth(56)
        self.btn_clear_bg.setToolTip("背景画像を解除して通常ダーク背景に戻す")
        self.btn_clear_bg.clicked.connect(self._on_clear_bg_image)
        r_bg_btn.addWidget(self.btn_clear_bg)
        l_bg.addLayout(r_bg_btn)

        # 配置 (フィットモード)
        r_fit = QHBoxLayout()
        r_fit.addWidget(QLabel("配置:"))
        self.combo_bg_fit = QComboBox(self)
        self.combo_bg_fit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_bg_fit.addItems([
            "中央トリミング (画面いっぱい)",
            "画面内に収める (全体表示)",
            "横幅に合わせる",
            "縦幅に合わせる",
            "画面に引き伸ばす (比率無視)"
        ])
        cur_fit = self.user_settings.get("bg_fit_mode", "中央トリミング (画面いっぱい)")
        if "引き伸ば" in cur_fit or "引き延ば" in cur_fit:
            self.combo_bg_fit.setCurrentText("画面に引き伸ばす (比率無視)")
        else:
            self.combo_bg_fit.setCurrentText(cur_fit)
        self.combo_bg_fit.setToolTip("背景画像の画面フィット方式（中央トリミング / 全体表示 / 比率を無視して画面全体に引き伸ばす）")
        self.combo_bg_fit.currentTextChanged.connect(self._on_bg_fit_changed)
        self._configure_sidebar_combo(self.combo_bg_fit, max_width=230)
        r_fit.addWidget(self.combo_bg_fit, stretch=1)
        l_bg.addLayout(r_fit)

        # 回転
        self.bg_rotation_deg = int(self.user_settings.get("bg_rotation", 0))
        r_rot = QHBoxLayout()
        r_rot.addWidget(QLabel("回転:"))
        self.btn_bg_rot = QPushButton(f"⟳ 90°回転 ({self.bg_rotation_deg}°)", self)
        self.btn_bg_rot.setToolTip("クリックするごとに背景画像を時計回りに90度回転")
        self.btn_bg_rot.clicked.connect(self._on_rotate_bg_image)
        r_rot.addWidget(self.btn_bg_rot)
        l_bg.addLayout(r_rot)

        # 減光 (暗さ) スライダー
        r_dim = QHBoxLayout()
        r_dim.addWidget(QLabel("暗さ:"))
        self.slider_bg_dim = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_bg_dim.setRange(0, 100)
        self.slider_bg_dim.setValue(int(self.user_settings.get("bg_dim_ratio", 60)))
        self.slider_bg_dim.setToolTip("背景画像の上に重ねる黒幕の濃さ（ノーツ視認性向上）")
        self.slider_bg_dim.valueChanged.connect(self._on_bg_dim_changed)
        r_dim.addWidget(self.slider_bg_dim)

        self.lbl_bg_dim_val = QLabel(f"{self.slider_bg_dim.value()}%", self)
        self.lbl_bg_dim_val.setFixedWidth(36)
        r_dim.addWidget(self.lbl_bg_dim_val)
        l_bg.addLayout(r_dim)
        v_box.addWidget(f_bg)

        # 5. ハーモニカスキン装飾
        f_skin = QFrame()
        f_skin.setObjectName("groupFrame")
        f_skin.setMaximumWidth(328)
        l_skin = QVBoxLayout(f_skin)
        l_skin.setContentsMargins(6, 6, 6, 6)
        l_skin.setSpacing(6)
        l_skin.addWidget(QLabel("🎷 <b>ハーモニカスキン装飾:</b>"))

        self.chk_skin = QCheckBox("カスタム表示適用", self)
        self.chk_skin.setChecked(bool(self.user_settings.get("skin_enabled", True)))
        self.chk_skin.setToolTip("ハーモニカ本体のマウスピース・カバープレート・スライドレバーのカスタムスキンを表示")
        self.chk_skin.toggled.connect(self._on_skin_toggled)
        l_skin.addWidget(self.chk_skin)

        r_skin_btns = QHBoxLayout()
        self.btn_custom_skin = QPushButton("🎨 スキン選択...", self)
        self.btn_custom_skin.setToolTip("本体カバー（メタル/ウッド/マットブラック/ゴールド）やスライドレバーのスキンを切り替え")
        self.btn_custom_skin.clicked.connect(self._on_select_custom_skin)
        r_skin_btns.addWidget(self.btn_custom_skin)

        self.btn_reset_skin = QPushButton("↺ 初期化", self)
        self.btn_reset_skin.setToolTip("標準のメタルスキン・シルバーレバーに戻す")
        self.btn_reset_skin.clicked.connect(self._on_reset_preset_skin)
        r_skin_btns.addWidget(self.btn_reset_skin)
        l_skin.addLayout(r_skin_btns)
        v_box.addWidget(f_skin)

        v_box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "🎨 画面作り")

    # =========================================================================
    # タブ 3: 【🎙️ 録音・音響】
    # =========================================================================
    def _build_tab_audio(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 6, 4, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setMaximumWidth(340)
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 1. 音量制御
        f_vol = QFrame()
        f_vol.setObjectName("groupFrame")
        f_vol.setMaximumWidth(328)
        l_vol = QVBoxLayout(f_vol)
        l_vol.setContentsMargins(6, 6, 6, 6)
        l_vol.setSpacing(6)
        l_vol.addWidget(QLabel("🔊 <b>音量制御 ＆ パート音色:</b>"))

        r_vol = QHBoxLayout()
        r_vol.addWidget(QLabel("マスター音量:"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(self.user_settings.get("volume", 100)))
        self.vol_slider.setToolTip("MIDI全体の再生マスター音量")
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        r_vol.addWidget(self.vol_slider)

        self.lbl_vol_val = QLabel(f"{self.vol_slider.value()}%", self)
        self.lbl_vol_val.setMinimumWidth(36)
        r_vol.addWidget(self.lbl_vol_val)
        l_vol.addLayout(r_vol)

        r_gas = QHBoxLayout()
        r_gas.addWidget(QLabel("ガイド音源:"))
        self.combo_guide_audio = QComboBox(self)
        self.combo_guide_audio.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_guide_audio.addItems([
            "Windows標準MIDI (推奨)",
            "内蔵軽量シンセ (遅延0ms)"
        ])
        raw_guide = self.user_settings.get("guide_audio_engine", "Windows標準MIDI (推奨)")
        cur_guide = "内蔵軽量シンセ (遅延0ms)" if "内蔵" in raw_guide or "シンセ" in raw_guide else "Windows標準MIDI (推奨)"
        self.combo_guide_audio.setCurrentText(cur_guide)
        self.combo_guide_audio.setToolTip("再生に使用するMIDI音源エンジン")
        self.combo_guide_audio.currentTextChanged.connect(self._on_guide_audio_changed)
        self._configure_sidebar_combo(self.combo_guide_audio, max_width=230)
        r_gas.addWidget(self.combo_guide_audio, stretch=1)
        l_vol.addLayout(r_gas)

        self.chk_force_harmonica = QCheckBox("主旋律をハーモニカ音色に固定", self)
        self.chk_force_harmonica.setChecked(bool(self.user_settings.get("force_harmonica", True)))
        self.chk_force_harmonica.setToolTip("MIDIファイル内の楽器指定に関わらず主旋律パートをハーモニカ音色(GM 22)で再生")
        self.chk_force_harmonica.toggled.connect(lambda v: setattr(self.audio_engine, "force_main_harmonica", v))
        l_vol.addWidget(self.chk_force_harmonica)
        v_box.addWidget(f_vol)

        # 2. 🎙️ マイク録音 (ワンクリック録音)
        f_rec = QFrame()
        f_rec.setObjectName("groupFrame")
        f_rec.setMaximumWidth(328)
        f_rec.setStyleSheet("QFrame#groupFrame { border: 1px solid #7F1D1D; }")
        l_rec = QVBoxLayout(f_rec)
        l_rec.setContentsMargins(6, 6, 6, 6)
        l_rec.setSpacing(6)
        l_rec.addWidget(QLabel("🎙️ <b>マイク演奏録音 (ワンクリック録音):</b>"))

        self.lbl_rec_status = QLabel("● 待機中 (上部 [🔴録音] で開始)", self)
        self.lbl_rec_status.setStyleSheet("color: #94A3B8; font-weight: bold;")
        l_rec.addWidget(self.lbl_rec_status)

        # デバイス選択
        r_dev = QHBoxLayout()
        r_dev.addWidget(QLabel("マイク:"))
        self.combo_rec_dev = QComboBox(self)
        self.combo_rec_dev.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_rec_dev.setMinimumContentsLength(8)
        self.combo_rec_dev.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_rec_dev.setToolTip("使用するマイク入力デバイスを選択")
        self._refresh_audio_devices()
        self._configure_sidebar_combo(self.combo_rec_dev, max_width=230)
        r_dev.addWidget(self.combo_rec_dev)

        btn_ref_dev = QPushButton("🔄", self)
        btn_ref_dev.setFixedWidth(28)
        btn_ref_dev.setToolTip("マイク入力デバイス一覧を再取得")
        btn_ref_dev.clicked.connect(self._refresh_audio_devices)
        r_dev.addWidget(btn_ref_dev)
        l_rec.addLayout(r_dev)

        # チャンネル選択
        r_ch = QHBoxLayout()
        r_ch.addWidget(QLabel("チャンネル:"))
        self.combo_rec_ch = QComboBox(self)
        self.combo_rec_ch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_rec_ch.addItems(["モノラル (1ch・DAW編集向き)", "ステレオ (2ch)"])
        ch_idx = 0 if int(self.user_settings.get("rec_channels", 1)) == 1 else 1
        self.combo_rec_ch.setCurrentIndex(ch_idx)
        self.combo_rec_ch.setToolTip("録音のチャンネル数 (モノラル推奨)")
        self._configure_sidebar_combo(self.combo_rec_ch, max_width=230)
        r_ch.addWidget(self.combo_rec_ch, stretch=1)
        l_rec.addLayout(r_ch)

        # テイク＆試聴 (2段に分離して横幅溢れを物理的に防止)
        self.lbl_rec_take = QLabel("録音テイク: 未録音", self)
        self.lbl_rec_take.setMinimumWidth(0)
        self.lbl_rec_take.setMaximumWidth(310)
        self.lbl_rec_take.setStyleSheet("color: #64748B; font-size: 11px;")
        l_rec.addWidget(self.lbl_rec_take)

        r_take = QHBoxLayout()
        r_take.setSpacing(4)
        self.btn_rec_listen = QPushButton("▶ 試聴", self)
        self.btn_rec_listen.setFixedWidth(64)
        self.btn_rec_listen.setEnabled(False)
        self.btn_rec_listen.setToolTip("選択中・直前に録音したテイクを単体試聴再生")
        self.btn_rec_listen.clicked.connect(self._on_rec_listen_toggle)
        r_take.addWidget(self.btn_rec_listen)

        self.btn_select_rec_take = QPushButton("📂 テイク選択...", self)
        self.btn_select_rec_take.setToolTip("過去に録音したテイクや外部WAVファイルを選択して採用")
        self.btn_select_rec_take.clicked.connect(self._on_select_rec_take)
        r_take.addWidget(self.btn_select_rec_take, stretch=1)

        btn_open_rec = QPushButton("📁 保存先", self)
        btn_open_rec.setFixedWidth(68)
        btn_open_rec.setToolTip("録音されたWAVファイルが保存されるフォルダを開く")
        btn_open_rec.clicked.connect(self._on_open_rec_folder)
        r_take.addWidget(btn_open_rec)
        l_rec.addLayout(r_take)

        # 録音ズレ補正 (マイクインターフェース遅延微調整)
        r_rec_off = QHBoxLayout()
        r_rec_off.addWidget(QLabel("録音ズレ補正:"))
        r_rec_off.addStretch()
        self.spin_rec_offset = QSpinBox(self)
        self.spin_rec_offset.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_rec_offset.setRange(-2000, 2000)
        self.spin_rec_offset.setValue(int(self.user_settings.get("rec_offset_ms", 0)))
        self.spin_rec_offset.setSuffix(" ms")
        self.spin_rec_offset.setSingleStep(10)
        self.spin_rec_offset.setFixedWidth(90)
        self.spin_rec_offset.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_rec_offset.setToolTip("マイクやオーディオインターフェースの録音遅延・タイミングを微調整 [直接入力 / マウスホイール]")
        self.spin_rec_offset.valueChanged.connect(lambda v: (self.user_settings.update({"rec_offset_ms": int(v)}), self._save_current_settings()))
        r_rec_off.addWidget(self.spin_rec_offset)

        btn_rec_z = QPushButton("0ms", self)
        btn_rec_z.setFixedWidth(42)
        btn_rec_z.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        btn_rec_z.setToolTip("録音ズレ補正を0msにリセット")
        btn_rec_z.clicked.connect(lambda: self.spin_rec_offset.setValue(0))
        r_rec_off.addWidget(btn_rec_z)
        l_rec.addLayout(r_rec_off)

        v_box.addWidget(f_rec)

        # 3. ✨ ハーモニカ用リバーブ (空間残響エフェクト)
        f_rev = QFrame()
        f_rev.setObjectName("groupFrame")
        f_rev.setMaximumWidth(328)
        l_rev = QVBoxLayout(f_rev)
        l_rev.setContentsMargins(6, 6, 6, 6)
        l_rev.setSpacing(6)
        l_rev.addWidget(QLabel("✨ <b>ハーモニカ用リバーブ (空間残響エフェクト):</b>"))

        self.chk_reverb = QCheckBox("リバーブを適用", self)
        self.chk_reverb.setChecked(bool(self.user_settings.get("reverb_enabled", False)))
        self.chk_reverb.setToolTip("録音テイクおよび動画出力音声にリバーブ残響を適用")
        self.chk_reverb.toggled.connect(self._on_reverb_toggled)
        l_rev.addWidget(self.chk_reverb)

        r_rev_type = QHBoxLayout()
        r_rev_type.addWidget(QLabel("空間タイプ:"))
        self.combo_reverb_type = QComboBox(self)
        self.combo_reverb_type.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_reverb_type.addItems(["ルーム (自然な部屋鳴り)", "ホール (豊かな広がり)", "プレート (透明感のある響き)"])
        self.combo_reverb_type.setCurrentText(self.user_settings.get("reverb_type", "ルーム (自然な部屋鳴り)"))
        self.combo_reverb_type.setToolTip("リバーブの空間タイプ")
        self.combo_reverb_type.currentTextChanged.connect(self._on_reverb_type_changed)
        self._configure_sidebar_combo(self.combo_reverb_type, max_width=230)
        r_rev_type.addWidget(self.combo_reverb_type, stretch=1)
        l_rev.addLayout(r_rev_type)

        r_rev2 = QHBoxLayout()
        self.lbl_reverb_wet = QLabel(f"深さ: {self.user_settings.get('reverb_wet_pct', 35)}%", self)
        self.lbl_reverb_wet.setMinimumWidth(65)
        r_rev2.addWidget(self.lbl_reverb_wet)

        self.slider_reverb_wet = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_reverb_wet.setRange(0, 100)
        self.slider_reverb_wet.setValue(int(self.user_settings.get("reverb_wet_pct", 35)))
        self.slider_reverb_wet.setToolTip("リバーブ残響の深さ・ウェット比率 (0%〜100%)")
        self.slider_reverb_wet.valueChanged.connect(self._on_reverb_slider_changed)
        r_rev2.addWidget(self.slider_reverb_wet)
        l_rev.addLayout(r_rev2)
        v_box.addWidget(f_rev)

        # 4. 🎵 伴奏・外部音源 (D&D対応)
        f_ext = QFrame()
        f_ext.setObjectName("groupFrame")
        f_ext.setMaximumWidth(328)
        l_ext = QVBoxLayout(f_ext)
        l_ext.setContentsMargins(6, 6, 6, 6)
        l_ext.setSpacing(6)
        l_ext.addWidget(QLabel("🎵 <b>伴奏・外部音源 (D&D対応):</b>"))

        r_ext1 = QHBoxLayout()
        btn_ext_open = QPushButton("📂 伴奏音源を選択", self)
        btn_ext_open.setFixedHeight(24)
        btn_ext_open.setToolTip("外部の伴奏オーディオファイル (MP3/WAV/M4A/FLAC等) を選択 [ドラッグ＆ドロップ可]")
        btn_ext_open.clicked.connect(self._on_select_ext_audio)
        r_ext1.addWidget(btn_ext_open, stretch=1)

        btn_ext_clear = QPushButton("✕ 解除", self)
        btn_ext_clear.setFixedWidth(54)
        btn_ext_clear.setFixedHeight(24)
        btn_ext_clear.setToolTip("音源を解除")
        btn_ext_clear.clicked.connect(self._on_clear_ext_audio)
        r_ext1.addWidget(btn_ext_clear)
        l_ext.addLayout(r_ext1)

        self.lbl_ext_audio = QLabel("未選択 (MP3/WAV等をD&D可)", self)
        self.lbl_ext_audio.setMinimumWidth(0)
        self.lbl_ext_audio.setStyleSheet("color: #64748B; font-size: 11px; background-color: #121218; border: 1px solid #22222E; border-radius: 3px; padding: 2px 6px;")
        if self.ext_audio_path and os.path.exists(self.ext_audio_path):
            base_name = os.path.basename(self.ext_audio_path)
            fm = self.lbl_ext_audio.fontMetrics()
            self.lbl_ext_audio.setText(fm.elidedText(base_name, Qt.TextElideMode.ElideMiddle, 280))
            self.lbl_ext_audio.setToolTip(self.ext_audio_path)
            self.lbl_ext_audio.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px; background-color: #121218; border: 1px solid #22222E; border-radius: 3px; padding: 2px 6px;")
        l_ext.addWidget(self.lbl_ext_audio)

        r_ext2 = QHBoxLayout()
        r_ext2.addWidget(QLabel("再生モード:"))
        self.combo_ext_mode = QComboBox(self)
        self.combo_ext_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_ext_mode.addItems([
            "伴奏 ＋ ガイド音 (両方再生)",
            "伴奏のみ (ガイド音オフ)",
            "ガイド音のみ (伴奏ミュート)"
        ])
        raw_mode = str(self.user_settings.get("ext_audio_mode", "伴奏 ＋ ガイド音 (両方再生)"))
        if "伴奏のみ" in raw_mode or "外部音源のみ" in raw_mode:
            cur_mode = "伴奏のみ (ガイド音オフ)"
        elif "ガイド音のみ" in raw_mode or "外部音源オフ" in raw_mode or "伴奏ミュート" in raw_mode:
            cur_mode = "ガイド音のみ (伴奏ミュート)"
        else:
            cur_mode = "伴奏 ＋ ガイド音 (両方再生)"
        self.combo_ext_mode.setCurrentText(cur_mode)
        self.combo_ext_mode.setToolTip("スピーカー再生時の出力構成（伴奏合わせ・カラオケ練習・単独練習）")
        self.combo_ext_mode.currentTextChanged.connect(self._on_ext_mode_changed)
        self._configure_sidebar_combo(self.combo_ext_mode, max_width=230)
        r_ext2.addWidget(self.combo_ext_mode, stretch=1)
        l_ext.addLayout(r_ext2)

        r_ext_vol = QHBoxLayout()
        r_ext_vol.addWidget(QLabel("伴奏音量:"))
        self.slider_ext_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_ext_vol.setRange(0, 200)
        self.slider_ext_vol.setValue(int(self.user_settings.get("ext_audio_volume", 80)))
        self.slider_ext_vol.setToolTip("外部伴奏音源の音量レベル (0%〜200%)")
        self.slider_ext_vol.valueChanged.connect(self._on_ext_vol_changed)
        r_ext_vol.addWidget(self.slider_ext_vol)

        self.lbl_ext_vol = QLabel(f"{self.slider_ext_vol.value()}%", self)
        self.lbl_ext_vol.setMinimumWidth(36)
        r_ext_vol.addWidget(self.lbl_ext_vol)
        l_ext.addLayout(r_ext_vol)

        # 頭出しオフセット
        r_off = QHBoxLayout()
        r_off.addWidget(QLabel("同期ズレ補正:"))
        self.spin_ext_offset = QSpinBox(self)
        self.spin_ext_offset.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_ext_offset.setRange(-5000, 5000)
        self.spin_ext_offset.setValue(int(self.user_settings.get("ext_audio_offset_ms", 0)))
        self.spin_ext_offset.setSuffix(" ms")
        self.spin_ext_offset.setSingleStep(10)
        self.spin_ext_offset.setFixedWidth(90)
        self.spin_ext_offset.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_ext_offset.setToolTip("MIDIと外部伴奏音源の発音タイミングのズレを調整 [直接入力 / マウスホイールで変更 / [ ] キーで±10ms]")
        self.spin_ext_offset.valueChanged.connect(self._on_ext_offset_changed)
        r_off.addWidget(self.spin_ext_offset)

        btn_z = QPushButton("0ms", self)
        btn_z.setFixedWidth(38)
        btn_z.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        btn_z.setToolTip("同期オフセットを0msにリセット")
        btn_z.clicked.connect(lambda: self.spin_ext_offset.setValue(0))
        r_off.addWidget(btn_z)
        l_ext.addLayout(r_off)

        # 微調整ボタン 4連
        r_fine = QHBoxLayout()
        for label, val in [("-10ms", -10), ("-1ms", -1), ("+1ms", 1), ("+10ms", 10)]:
            btn = QPushButton(label, self)
            btn.setFixedWidth(52)
            btn.setStyleSheet("font-size: 11px; padding: 2px 4px;")
            btn.setToolTip(f"同期オフセットを {label} 微調整")
            btn.clicked.connect(lambda _, d=val: self._on_ext_offset_adjust(d))
            r_fine.addWidget(btn)
        l_ext.addLayout(r_fine)

        # 試聴ボタン
        r_aud = QHBoxLayout()
        self.btn_ext_audition = QPushButton("▶ 試聴", self)
        self.btn_ext_audition.setFixedWidth(78)
        self.btn_ext_audition.setStyleSheet("background-color: #1E3A5F; font-weight: bold;")
        self.btn_ext_audition.setToolTip("設定したオフセット位置から外部伴奏音源を試聴再生")
        self.btn_ext_audition.clicked.connect(self._on_ext_audition_play)
        r_aud.addWidget(self.btn_ext_audition)

        self.btn_ext_restart = QPushButton("⏮ 先頭", self)
        self.btn_ext_restart.setFixedWidth(78)
        self.btn_ext_restart.setToolTip("外部伴奏音源を0秒(ファイル先頭)から試聴再生")
        self.btn_ext_restart.clicked.connect(self._on_ext_audition_restart)
        r_aud.addWidget(self.btn_ext_restart)

        self.btn_ext_stop = QPushButton("⏹ 停止", self)
        self.btn_ext_stop.setFixedWidth(78)
        self.btn_ext_stop.setToolTip("外部伴奏音源の試聴を停止")
        self.btn_ext_stop.clicked.connect(self._on_ext_audition_stop)
        r_aud.addWidget(self.btn_ext_stop)
        l_ext.addLayout(r_aud)

        has_ext = bool(self.ext_audio_path and os.path.exists(self.ext_audio_path))
        self.btn_ext_audition.setEnabled(has_ext)
        self.btn_ext_restart.setEnabled(has_ext)
        self.btn_ext_stop.setEnabled(has_ext)

        v_box.addWidget(f_ext)

        v_box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "🎙️ 録音・音響")

    # =========================================================================
    # タブ 4: 【🎬 動画出力】
    # =========================================================================
    def _build_tab_export(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 6, 4, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setMaximumWidth(340)
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 0. 🗂️ 動画出力プリセット管理
        f_preset = QFrame()
        f_preset.setObjectName("groupFrame")
        f_preset.setMaximumWidth(328)
        l_preset = QVBoxLayout(f_preset)
        l_preset.setContentsMargins(6, 6, 6, 6)
        l_preset.setSpacing(6)
        l_preset.addWidget(QLabel("🗂️ <b>動画出力プリセット:</b>"))

        r_pre_top = QHBoxLayout()
        r_pre_top.addWidget(QLabel("プリセット:"))
        self.combo_video_preset = QComboBox(self)
        self.combo_video_preset.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._configure_sidebar_combo(self.combo_video_preset, max_width=230)
        self.combo_video_preset.setToolTip("目的別の動画出力設定プリセット（縦横比・解像度・装飾・タイトル・音量を一括切替）")
        self.combo_video_preset.currentTextChanged.connect(self._on_video_preset_changed)
        r_pre_top.addWidget(self.combo_video_preset, stretch=1)
        l_preset.addLayout(r_pre_top)

        r_pre_ops = QHBoxLayout()
        self.btn_preset_save = QPushButton("💾 保存", self)
        self.btn_preset_save.setToolTip("現在の動画設定および動画用デザインを選択中のプリセットに上書き保存")
        self.btn_preset_save.clicked.connect(self._on_save_video_preset)
        r_pre_ops.addWidget(self.btn_preset_save)

        self.btn_preset_save_as = QPushButton("➕ 別名保存...", self)
        self.btn_preset_save_as.setToolTip("現在の設定で新しい動画プリセットを作成")
        self.btn_preset_save_as.clicked.connect(self._on_save_as_video_preset)
        r_pre_ops.addWidget(self.btn_preset_save_as)

        self.btn_preset_reset = QPushButton("↺ 初期化", self)
        self.btn_preset_reset.setToolTip("公式プリセットは初期値へ復元、自作プリセットは削除します")
        self.btn_preset_reset.clicked.connect(self._on_reset_or_delete_video_preset)
        r_pre_ops.addWidget(self.btn_preset_reset)
        l_preset.addLayout(r_pre_ops)

        self.btn_copy_practice_visual = QPushButton("📋 現在の「練習画面」の見た目を反映", self)
        self.btn_copy_practice_visual.setFixedHeight(26)
        self.btn_copy_practice_visual.setStyleSheet("background-color: #1E293B; border: 1px solid #10B981; color: #6EE7B7; font-weight: bold; font-size: 11px; border-radius: 3px;")
        self.btn_copy_practice_visual.setToolTip("練習画面で設定されている配色・スキン・音名・装飾の見た目を、現在選択中の動画プリセットにコピーしてプレビューに反映します")
        self.btn_copy_practice_visual.clicked.connect(self._on_copy_practice_visual_to_preset)
        l_preset.addWidget(self.btn_copy_practice_visual)

        self.btn_jump_design_for_video = QPushButton("🎨 このプリセットの画面デザインを編集...", self)
        self.btn_jump_design_for_video.setFixedHeight(24)
        self.btn_jump_design_for_video.setStyleSheet("background-color: #18181B; border: 1px solid #6366F1; color: #A5B4FC; font-size: 11px; border-radius: 3px;")
        self.btn_jump_design_for_video.setToolTip("画面作りタブへ移動し、この動画プリセットのデザイン（比率・色・スキン等）を編集します")
        self.btn_jump_design_for_video.clicked.connect(self._on_jump_design_for_video)
        l_preset.addWidget(self.btn_jump_design_for_video)

        v_box.addWidget(f_preset)

        # 1. 動画レンダリング品質＆解像度
        f_exp = QFrame()
        f_exp.setObjectName("groupFrame")
        f_exp.setMaximumWidth(328)
        l_exp = QVBoxLayout(f_exp)
        l_exp.setContentsMargins(6, 6, 6, 6)
        l_exp.setSpacing(6)
        l_exp.addWidget(QLabel("🎬 <b>動画レンダリング品質 ＆ 解像度:</b>"))

        r_style = QHBoxLayout()
        r_style.addWidget(QLabel("出力スタイル:"))
        self.combo_exp_style = QComboBox(self)
        self.combo_exp_style.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_style.addItems([
            "完成動画 (背景・タイトル合成)",
            "クロマキー素材 (背景・タイトルなし)",
            "完全背景透過 (アルファ付き透過素材 .mov)"
        ])
        self.combo_exp_style.setToolTip("動画の出力フォーマットスタイル")
        self.combo_exp_style.currentTextChanged.connect(self._on_export_style_changed)
        self._configure_sidebar_combo(self.combo_exp_style, max_width=230)
        r_style.addWidget(self.combo_exp_style, stretch=1)
        l_exp.addLayout(r_style)

        self.r_bg_chroma = QHBoxLayout()
        self.lbl_exp_bg = QLabel("クロマキー背景色:")
        self.lbl_exp_bg.setEnabled(False)
        self.r_bg_chroma.addWidget(self.lbl_exp_bg)
        self.combo_exp_bg = QComboBox(self)
        self.combo_exp_bg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_bg.addItems(["ノーマル（黒）", "グリーンバック", "ブルーバック", "マゼンタ（ピンク）"])
        self.combo_exp_bg.setEnabled(False)
        self.combo_exp_bg.setToolTip("クロマキー透過合成用の単色背景色")
        self.combo_exp_bg.currentTextChanged.connect(self._on_chroma_bg_changed)
        self.r_bg_chroma.addWidget(self.combo_exp_bg, stretch=1)
        l_exp.addLayout(self.r_bg_chroma)

        r_res = QHBoxLayout()
        r_res.addWidget(QLabel("解像度:"))
        self.combo_exp_res = QComboBox(self)
        self.combo_exp_res.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_res.addItems(["Full HD (1920x1080・推奨)", "720p (1280x720・軽量)", "4K (3840x2160・高精細)"])
        self.combo_exp_res.setToolTip("出力動画のピクセル解像度")
        r_res.addWidget(self.combo_exp_res, stretch=1)
        l_exp.addLayout(r_res)

        r_fps = QHBoxLayout()
        r_fps.addWidget(QLabel("フレームレート:"))
        self.combo_exp_fps = QComboBox(self)
        self.combo_exp_fps.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_fps.addItems(["60 FPS (滑らか・推奨)", "30 FPS (軽量)"])
        self.combo_exp_fps.setToolTip("動画のフレームレート (60FPS推奨)")
        r_fps.addWidget(self.combo_exp_fps, stretch=1)
        l_exp.addLayout(r_fps)

        r_enc = QHBoxLayout()
        r_enc.addWidget(QLabel("エンコーダー:"))
        self.combo_exp_codec = QComboBox(self)
        self.combo_exp_codec.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_codec.addItems(["自動 (MediaFoundation GPU優先)", "MediaFoundation GPU (高速)", "CPU libx264 (高画質標準)"])
        self.combo_exp_codec.setToolTip("動画エンコードエンジン")
        self._configure_sidebar_combo(self.combo_exp_codec, max_width=230)
        r_enc.addWidget(self.combo_exp_codec, stretch=1)
        l_exp.addLayout(r_enc)

        r_rng = QHBoxLayout()
        r_rng.addWidget(QLabel("範囲:"))
        self.spin_exp_start = QDoubleSpinBox(self)
        self.spin_exp_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_exp_start.setRange(0.0, 9999.0)
        self.spin_exp_start.setValue(0.0)
        self.spin_exp_start.setSuffix("s")
        self.spin_exp_start.setFixedWidth(50)
        self.spin_exp_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_exp_start.setToolTip("動画書き出しの開始秒 [直接入力 / マウスホイールで変更]")
        r_rng.addWidget(self.spin_exp_start)

        r_rng.addWidget(QLabel("〜"))

        self.spin_exp_end = QDoubleSpinBox(self)
        self.spin_exp_end.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_exp_end.setRange(0.1, 9999.0)
        self.spin_exp_end.setValue(float(getattr(self.timeline, "total_duration_sec", 60.0)))
        self.spin_exp_end.setSuffix("s")
        self.spin_exp_end.setFixedWidth(50)
        self.spin_exp_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_exp_end.setToolTip("動画書き出しの終了秒 [直接入力 / マウスホイールで変更]")
        r_rng.addWidget(self.spin_exp_end)

        self.btn_set_ab_range = QPushButton("🔁 A-B", self)
        self.btn_set_ab_range.setFixedWidth(52)
        self.btn_set_ab_range.setToolTip("現在設定されているA-Bループの小節範囲（開始秒〜終了秒）を動画の出力範囲にコピーします")
        self.btn_set_ab_range.clicked.connect(self._on_set_ab_range_to_export)
        r_rng.addWidget(self.btn_set_ab_range)

        self.btn_reset_exp_range = QPushButton("↺ 全曲", self)
        self.btn_reset_exp_range.setFixedWidth(52)
        self.btn_reset_exp_range.setToolTip("動画書き出し範囲を曲全体 (0.0s〜総尺) にリセットします")
        self.btn_reset_exp_range.clicked.connect(self._on_reset_export_range)
        r_rng.addWidget(self.btn_reset_exp_range)
        l_exp.addLayout(r_rng)

        r_margin = QHBoxLayout()
        r_margin.addWidget(QLabel("前余白:"))
        self.combo_exp_intro = QComboBox(self)
        self.combo_exp_intro.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_exp_intro.setMinimumContentsLength(4)
        self.combo_exp_intro.addItems(["0秒", "1秒", "2秒", "3秒", "5秒"])
        self.combo_exp_intro.setCurrentText(str(self.user_settings.get("export_intro_sec", "1秒")))
        self.combo_exp_intro.setFixedWidth(58)
        self.combo_exp_intro.setToolTip("動画冒頭（演奏開始前）に追加する無音・静止余白時間")
        r_margin.addWidget(self.combo_exp_intro)

        r_margin.addWidget(QLabel("後余白:"))
        self.combo_exp_outro = QComboBox(self)
        self.combo_exp_outro.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_exp_outro.setMinimumContentsLength(4)
        self.combo_exp_outro.addItems(["0秒", "1秒", "2秒", "3秒", "5秒"])
        self.combo_exp_outro.setCurrentText(str(self.user_settings.get("export_outro_sec", "2秒")))
        self.combo_exp_outro.setFixedWidth(58)
        self.combo_exp_outro.setToolTip("動画末尾（演奏終了後）に追加する余韻時間")
        r_margin.addWidget(self.combo_exp_outro)
        l_exp.addLayout(r_margin)
        v_box.addWidget(f_exp)

        # 2. 動画の音声トラック設定
        f_aud = QFrame()
        f_aud.setObjectName("groupFrame")
        f_aud.setMaximumWidth(328)
        l_aud = QVBoxLayout(f_aud)
        l_aud.setContentsMargins(6, 6, 6, 6)
        l_aud.setSpacing(6)
        l_aud.addWidget(QLabel("🎵 <b>動画の音声トラック設定:</b>"))

        r_asrc = QHBoxLayout()
        r_asrc.addWidget(QLabel("クイック指定:"))
        self.combo_exp_audio = QComboBox(self)
        self.combo_exp_audio.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_audio.addItems([
            "伴奏音源 (外部音源優先)",
            "マイク録音テイク (演奏収録)",
            "MIDIガイド音 (内部音源)",
            "無音 (映像のみ)"
        ])
        self.combo_exp_audio.setToolTip("動画に合成する音声ソースのクイック設定")
        self._configure_sidebar_combo(self.combo_exp_audio, max_width=230)
        self.combo_exp_audio.currentTextChanged.connect(self._on_quick_audio_source_changed)
        r_asrc.addWidget(self.combo_exp_audio, stretch=1)
        l_aud.addLayout(r_asrc)

        # マルチトラック・ミキサー設定行
        r_mix_btn = QHBoxLayout()
        self.btn_open_mixer = QPushButton("🎚️ 音声トラック・ミキサー設定...", self)
        self.btn_open_mixer.setFixedHeight(26)
        self.btn_open_mixer.setStyleSheet("font-weight: bold; background-color: #1E293B; border: 1px solid #38BDF8; color: #38BDF8; border-radius: 3px;")
        self.btn_open_mixer.setToolTip("外部伴奏・マイク録音・MIDI伴奏を複数同時に組み合わせて動画に合成・バランス調整")
        self.btn_open_mixer.clicked.connect(self._on_open_audio_mixer_dialog)
        r_mix_btn.addWidget(self.btn_open_mixer)
        l_aud.addLayout(r_mix_btn)

        self.lbl_mixer_summary = QLabel("構成: 伴奏音源(100%)", self)
        self.lbl_mixer_summary.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.lbl_mixer_summary.setWordWrap(True)
        l_aud.addWidget(self.lbl_mixer_summary)

        self.chk_exp_reverb = QCheckBox("音声にリバーブを適用", self)
        self.chk_exp_reverb.setChecked(bool(self.user_settings.get("reverb_enabled", False)))
        self.chk_exp_reverb.setToolTip("書き出す動画の音声トラックにハーモニカ用リバーブエフェクトを適用")
        l_aud.addWidget(self.chk_exp_reverb)

        self.chk_yt_limiter = QCheckBox("YouTube推奨 リミッター (-1.0dBFS)", self)
        self.chk_yt_limiter.setChecked(bool(self.user_settings.get("yt_limiter", True)))
        self.chk_yt_limiter.setToolTip("YouTubeの音声基準に準拠し、動画エンコード時の音割れを防ぐためピークを-1.0dBFSに自動抑制")
        self.chk_yt_limiter.toggled.connect(self._save_current_settings)
        l_aud.addWidget(self.chk_yt_limiter)

        r_exp_vol = QHBoxLayout()
        r_exp_vol.addWidget(QLabel("動画音声音量:"))
        self.slider_exp_audio_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_exp_audio_vol.setRange(0, 200)
        self.slider_exp_audio_vol.setValue(int(self.user_settings.get("export_audio_volume", 100)))
        self.slider_exp_audio_vol.setToolTip("書き出す動画の音声トラック全体の音量バランス (0%〜200%)")
        r_exp_vol.addWidget(self.slider_exp_audio_vol)
        self.lbl_exp_audio_vol = QLabel(f"{self.slider_exp_audio_vol.value()}%", self)
        self.lbl_exp_audio_vol.setFixedWidth(38)
        self.slider_exp_audio_vol.valueChanged.connect(lambda v: (self.lbl_exp_audio_vol.setText(f"{v}%"), self._save_current_settings()))
        r_exp_vol.addWidget(self.lbl_exp_audio_vol)
        l_aud.addLayout(r_exp_vol)

        r_yt_preset = QHBoxLayout()
        self.btn_yt_vol_preset = QPushButton("📊 YouTube最適音量に自動解析", self)
        self.btn_yt_vol_preset.setFixedHeight(26)
        self.btn_yt_vol_preset.setStyleSheet("font-size: 11px; padding: 2px 8px; background-color: #2D1A1A; border: 1px solid #7F1D1D; color: #FCA5A5; font-weight: bold; border-radius: 3px;")
        self.btn_yt_vol_preset.setToolTip("動画全体の音量をITU-R BS.1770規準で実際に測定し、YouTubeのラウドネス基準（-14 LUFS / True Peak -1.0 dBFS）で音質劣化・自動減衰されない最適音量％を自動算出・設定")
        self.btn_yt_vol_preset.clicked.connect(self._apply_youtube_volume_preset)
        r_yt_preset.addWidget(self.btn_yt_vol_preset)
        l_aud.addLayout(r_yt_preset)

        v_box.addWidget(f_aud)

        # 3. タイトル・クレジット表示
        f_tit = QFrame()
        f_tit.setObjectName("groupFrame")
        f_tit.setMaximumWidth(328)
        l_tit = QVBoxLayout(f_tit)
        l_tit.setContentsMargins(6, 6, 6, 6)
        l_tit.setSpacing(6)
        l_tit.addWidget(QLabel("✨ <b>タイトル ＆ クレジット表示:</b>"))

        self.chk_exp_title = QCheckBox("タイトル・クレジットを表示", self)
        self.chk_exp_title.setChecked(True)
        self.chk_exp_title.setToolTip("動画内に曲名タイトルやクレジット文字列をオーバーレイ合成（透過MOV・クロマキー時は自動OFF）")
        l_tit.addWidget(self.chk_exp_title)

        r_tpl = QHBoxLayout()
        self.lbl_title_tpl = QLabel("配置テンプレート:")
        r_tpl.addWidget(self.lbl_title_tpl)
        self.combo_title_template = QComboBox(self)
        self.combo_title_template.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_title_template.addItems([
            "イントロ中央のみ",
            "左上常時",
            "右上常時",
            "イントロ中央＋左上常時",
            "イントロ中央＋右上常時",
            "なし"
        ])
        self.combo_title_template.setToolTip("タイトルカードの画面上配置位置")
        self._configure_sidebar_combo(self.combo_title_template, max_width=230)
        r_tpl.addWidget(self.combo_title_template, stretch=1)
        l_tit.addLayout(r_tpl)

        self.lbl_exp_title = QLabel("曲名 (タイトル):")
        l_tit.addWidget(self.lbl_exp_title)
        self.txt_exp_title = QLineEdit(self)
        self.txt_exp_title.setPlaceholderText("曲名を入力")
        self.txt_exp_title.setText(self.timeline.filename or "")
        self.txt_exp_title.setToolTip("動画に表示する楽曲名")
        l_tit.addWidget(self.txt_exp_title)

        self.lbl_exp_credit = QLabel("演奏者・クレジット:")
        l_tit.addWidget(self.lbl_exp_credit)
        self.txt_exp_credit = QLineEdit(self)
        self.txt_exp_credit.setPlaceholderText("演奏者名・楽器名等")
        self.txt_exp_credit.setText("Chromatic Harmonica Solo")
        self.txt_exp_credit.setToolTip("動画に表示する演奏者名・楽器名等")
        l_tit.addWidget(self.txt_exp_credit)

        r_fade = QHBoxLayout()
        self.chk_fade_in = QCheckBox("フェードイン:", self)
        self.chk_fade_in.setChecked(bool(self.user_settings.get("export_fade_in", True)))
        self.chk_fade_in.setToolTip("動画冒頭のフェードイン効果")
        self.chk_fade_in.toggled.connect(lambda v: (self.spin_fade_in.setEnabled(v), self._save_current_settings()))
        r_fade.addWidget(self.chk_fade_in)

        self.spin_fade_in = QDoubleSpinBox(self)
        self.spin_fade_in.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_fade_in.setRange(0.0, 5.0)
        self.spin_fade_in.setSingleStep(0.5)
        self.spin_fade_in.setDecimals(1)
        self.spin_fade_in.setSuffix("s")
        self.spin_fade_in.setFixedWidth(54)
        self.spin_fade_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_fade_in.setValue(float(self.user_settings.get("export_fade_in_sec", 1.5)))
        self.spin_fade_in.setToolTip("動画冒頭のフェードイン秒数 (0.0〜5.0秒) [直接入力 / マウスホイールで変更]")
        self.spin_fade_in.setEnabled(self.chk_fade_in.isChecked())
        self.spin_fade_in.valueChanged.connect(lambda _: self._save_current_settings())
        r_fade.addWidget(self.spin_fade_in)

        self.chk_fade_out = QCheckBox("フェードアウト:", self)
        self.chk_fade_out.setChecked(bool(self.user_settings.get("export_fade_out", True)))
        self.chk_fade_out.setToolTip("動画末尾のフェードアウト効果")
        self.chk_fade_out.toggled.connect(lambda v: (self.spin_fade_out.setEnabled(v), self._save_current_settings()))
        r_fade.addWidget(self.chk_fade_out)

        self.spin_fade_out = QDoubleSpinBox(self)
        self.spin_fade_out.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_fade_out.setRange(0.0, 5.0)
        self.spin_fade_out.setSingleStep(0.5)
        self.spin_fade_out.setDecimals(1)
        self.spin_fade_out.setSuffix("s")
        self.spin_fade_out.setFixedWidth(54)
        self.spin_fade_out.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_fade_out.setValue(float(self.user_settings.get("export_fade_out_sec", 1.5)))
        self.spin_fade_out.setToolTip("動画末尾のフェードアウト秒数 (0.0〜5.0秒) [直接入力 / マウスホイールで変更]")
        self.spin_fade_out.setEnabled(self.chk_fade_out.isChecked())
        self.spin_fade_out.valueChanged.connect(lambda _: self._save_current_settings())
        r_fade.addWidget(self.spin_fade_out)

        l_tit.addLayout(r_fade)

        r_ftitle = QHBoxLayout()
        self.lbl_fade_title = QLabel("フェード対象:")
        r_ftitle.addWidget(self.lbl_fade_title)
        self.combo_fade_title = QComboBox(self)
        self.combo_fade_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_fade_title.addItems(["フェード中もタイトル表示", "画面と一緒にフェードイン", "フェード中はタイトル非表示"])
        self.combo_fade_title.setCurrentText(str(self.user_settings.get("export_fade_title_mode", "フェード中もタイトル表示")))
        self.combo_fade_title.setToolTip("フェードイン/アウト時のタイトルカードの表示連動動作")
        self._configure_sidebar_combo(self.combo_fade_title, max_width=230)
        r_ftitle.addWidget(self.combo_fade_title, stretch=1)
        l_tit.addLayout(r_ftitle)
        v_box.addWidget(f_tit)

        # 4. 出力実行
        f_btn = QFrame()
        f_btn.setObjectName("groupFrame")
        f_btn.setMaximumWidth(328)
        l_btn = QVBoxLayout(f_btn)
        l_btn.setContentsMargins(6, 6, 6, 6)
        l_btn.setSpacing(8)

        self.btn_preview_frame = QPushButton("📸 現在フレームをプレビュー", self)
        self.btn_preview_frame.setToolTip("現在の再生位置の1フレームを出力解像度でテスト描画して確認します")
        self.btn_preview_frame.clicked.connect(self._on_preview_frame)
        l_btn.addWidget(self.btn_preview_frame)

        self.btn_export_video = QPushButton("🎥 MP4動画の書き出し開始", self)
        self.btn_export_video.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_export_video.setToolTip("設定したパラメータで動画の書き出し処理を開始")
        self.btn_export_video.clicked.connect(self._on_start_video_export)
        l_btn.addWidget(self.btn_export_video)

        btn_open_out_dir = QPushButton("📂 出力フォルダを開く", self)
        btn_open_out_dir.setToolTip("書き出した動画が保存される output フォルダをエクスプローラーで開きます")
        btn_open_out_dir.clicked.connect(self._on_open_output_folder)
        l_btn.addWidget(btn_open_out_dir)

        v_box.addWidget(f_btn)

        v_box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tab_widget.addTab(tab, "🎬 動画出力")

    # =========================================================================
    # ショートカットキー設定
    # =========================================================================
    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self._on_play_toggle)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, activated=self._on_return_key_pressed)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, activated=self._on_return_key_pressed)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self._on_stop)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self, activated=self._on_stop)
        QShortcut(QKeySequence("0"), self, activated=self._on_stop)
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, activated=self._on_rewind)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, activated=self._on_rewind)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, activated=lambda: self._seek_relative(-5.0))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=lambda: self._seek_relative(5.0))
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, activated=lambda: self._adjust_speed(5))
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, activated=lambda: self._adjust_speed(-5))
        QShortcut(QKeySequence("+"), self, activated=lambda: self._jump_measure_delta(1))
        QShortcut(QKeySequence("="), self, activated=lambda: self._jump_measure_delta(1))
        QShortcut(QKeySequence("-"), self, activated=lambda: self._jump_measure_delta(-1))
        QShortcut(QKeySequence("A"), self, activated=self._on_set_loop_a)
        QShortcut(QKeySequence("B"), self, activated=self._on_set_loop_b)
        QShortcut(QKeySequence("L"), self, activated=lambda: self.chk_loop.toggle())
        QShortcut(QKeySequence("R"), self, activated=self._on_record_toggle)
        QShortcut(QKeySequence("*"), self, activated=self._on_record_toggle)
        QShortcut(QKeySequence("F"), self, activated=lambda: self.chk_fing_edit.toggle())
        QShortcut(QKeySequence("M"), self, activated=lambda: self.chk_mute_edit.toggle())
        QShortcut(QKeySequence("["), self, activated=lambda: self._on_ext_offset_adjust(-10))
        QShortcut(QKeySequence("]"), self, activated=lambda: self._on_ext_offset_adjust(10))

    def _on_return_key_pressed(self):
        """Enter / Return キー押下時: スピンボックス・入力欄フォーカス中は入力を確定し、通常時は再生/一時停止"""
        fw = QApplication.focusWidget()
        if fw is not None:
            parent = fw.parentWidget()
            if fw is self.spin_jump or parent is self.spin_jump:
                self.spin_jump.interpretText()
                fw.clearFocus()
                self._on_jump_measure()
                return
            if isinstance(fw, QAbstractSpinBox):
                fw.interpretText()
                fw.clearFocus()
                return
            if isinstance(parent, QAbstractSpinBox):
                parent.interpretText()
                fw.clearFocus()
                return
            if isinstance(fw, QLineEdit):
                fw.clearFocus()
                return
        self._on_play_toggle()

    def _jump_measure_delta(self, delta: int):
        total_m = len(self.timeline.measures_timeline) if self.timeline and self.timeline.measures_timeline else 999
        new_m = max(1, min(total_m, self.spin_jump.value() + delta))
        self.spin_jump.setValue(new_m)
        self._on_jump_measure()

    def _on_visual_target_changed(self, target_text: str):
        """画面作りタブで編集する対象（練習用スタイル vs 動画プリセット）の切り替え"""
        if "動画プリセット" in target_text:
            self._visual_edit_target = "video"
            active_p = settings_manager.get_active_preset_dict(self.user_settings)
            p_name = self.user_settings.get("active_video_preset", "📱 YouTube Shorts (縦型・解説)")
            ratio = active_p.get("aspect_ratio", "16:9")
            is_chroma = "クロマキー" in active_p.get("export_style", "")
            chroma_col = active_p.get("export_bg_color", "ノーマル（黒）")
            self._apply_visual_dict_to_ui_and_gl(active_p, aspect_ratio=ratio, is_chromakey=is_chroma, chroma_color=chroma_col)
            if hasattr(self, "lbl_visual_target_hint"):
                self.lbl_visual_target_hint.setText(f"現在: 動画プリセット [{p_name}] を編集中（比率: {ratio}）")
                self.lbl_visual_target_hint.setStyleSheet("color: #F43F5E; font-size: 10px; font-weight: bold;")
            if hasattr(self, "f_ratio"):
                self.f_ratio.setEnabled(True)
            if hasattr(self, "w_design_preset_bar"):
                self.w_design_preset_bar.setVisible(True)
        else:
            self._visual_edit_target = "practice"
            pv = self.user_settings.get("practice_visual", settings_manager.DEFAULT_PRACTICE_VISUAL)
            self._apply_visual_dict_to_ui_and_gl(pv, aspect_ratio="16:9", is_chromakey=False, chroma_color="ノーマル（黒）")
            if hasattr(self, "lbl_visual_target_hint"):
                self.lbl_visual_target_hint.setText("現在: 練習用スタイルを編集中（常時16:9・日常の作業環境）")
                self.lbl_visual_target_hint.setStyleSheet("color: #38BDF8; font-size: 10px;")
            if hasattr(self, "f_ratio"):
                self.f_ratio.setEnabled(False)
            if hasattr(self, "w_design_preset_bar"):
                self.w_design_preset_bar.setVisible(False)

    def _on_tab_changed(self, index: int):
        if index in (0, 2):
            # 練習タブ / 録音音響タブ: 常に「練習用スタイル」・全画面 16:9 で表示
            pv = self.user_settings.get("practice_visual", settings_manager.DEFAULT_PRACTICE_VISUAL)
            self._apply_visual_dict_to_ui_and_gl(pv, aspect_ratio="16:9", is_chromakey=False, chroma_color="ノーマル（黒）")
        elif index == 3:
            # 動画出力タブ: 選択中の動画プリセット（Shorts 9:16やMV設定等）を完全反映プレビュー
            active_p = settings_manager.get_active_preset_dict(self.user_settings)
            ratio = active_p.get("aspect_ratio", "16:9")
            is_chroma = "クロマキー" in active_p.get("export_style", "")
            chroma_col = active_p.get("export_bg_color", "ノーマル（黒）")
            self._apply_visual_dict_to_ui_and_gl(active_p, aspect_ratio=ratio, is_chromakey=is_chroma, chroma_color=chroma_col)
        elif index == 1:
            # 画面作りタブ: 選択中のターゲット（練習用 or 動画プリセット）に応じた設定を反映
            if getattr(self, "_visual_edit_target", "practice") == "video":
                active_p = settings_manager.get_active_preset_dict(self.user_settings)
                ratio = active_p.get("aspect_ratio", "16:9")
                is_chroma = "クロマキー" in active_p.get("export_style", "")
                chroma_col = active_p.get("export_bg_color", "ノーマル（黒）")
                self._apply_visual_dict_to_ui_and_gl(active_p, aspect_ratio=ratio, is_chromakey=is_chroma, chroma_color=chroma_col)
            else:
                pv = self.user_settings.get("practice_visual", settings_manager.DEFAULT_PRACTICE_VISUAL)
                self._apply_visual_dict_to_ui_and_gl(pv, aspect_ratio="16:9", is_chromakey=False, chroma_color="ノーマル（黒）")

    def _handle_playback_finished(self):
        """非ループ再生の曲末到達ハンドラ"""
        self._on_stop()
        self.lbl_status_msg.setText("⏹ 曲の末尾に到達しました")

    def _on_guide_audio_changed(self, engine_name: str):
        self.audio_engine.set_guide_audio_engine(engine_name)
        self.user_settings["guide_audio_engine"] = str(engine_name)
        self._save_current_settings()
        self.lbl_status_msg.setText(f"ガイド音源切替: {engine_name}")

    def _on_chroma_bg_changed(self, val: str):
        is_chroma = ("クロマキー" in self.combo_exp_style.currentText()) and (self.tab_widget.currentIndex() == 3)
        self.gl_widget.set_canvas_bg_color(val, is_chromakey=is_chroma)

    # =========================================================================
    # ビジュアル設定の抽出・適用ヘルパー (v3.1.0)
    # =========================================================================
    def _get_current_visual_dict_from_ui(self) -> dict:
        """現在の 🎨 画面作り タブの各ウィジェットからビジュアル設定辞書を抽出"""
        return {
            "trajectory_mode": self.traj_combo.currentText() if hasattr(self, "traj_combo") else "3段階 (練習標準)",
            "lang_mode": self.lang_combo.currentText() if hasattr(self, "lang_combo") else "ドレミ",
            "color_theme": self.combo_theme.currentText() if hasattr(self, "combo_theme") else "ノーマル",
            "color_blow": self.gl_widget.color_blow.name() if hasattr(self.gl_widget, "color_blow") else "#FF5500",
            "color_draw": self.gl_widget.color_draw.name() if hasattr(self.gl_widget, "color_draw") else "#00BFFF",
            "lever_deco_mode": self.combo_lever.currentText() if hasattr(self, "combo_lever") else "センターライン (芯線)",
            "note_opacity": self.slider_op.value() if hasattr(self, "slider_op") else 100,
            "show_notes": self.chk_notes.isChecked() if hasattr(self, "chk_notes") else True,
            "show_lookahead": self.chk_lookahead.isChecked() if hasattr(self, "chk_lookahead") else True,
            "show_grid": self.chk_grid.isChecked() if hasattr(self, "chk_grid") else True,
            "show_bar_lines": self.chk_bar_lines.isChecked() if hasattr(self, "chk_bar_lines") else True,
            "show_hole_num": self.chk_hole_num.isChecked() if hasattr(self, "chk_hole_num") else True,
            "hole_num_style": self.combo_hole_num_style.currentText() if hasattr(self, "combo_hole_num_style") else "実機標準 (低音ドット付)",
            "grid4_mode": self.combo_grid4.currentText() if hasattr(self, "combo_grid4") else "4音グリッド表示",
            "show_ring": self.chk_ring.isChecked() if hasattr(self, "chk_ring") else True,
            "show_glow": self.chk_glow.isChecked() if hasattr(self, "chk_glow") else True,
            "show_legend": self.chk_legend.isChecked() if hasattr(self, "chk_legend") else True,
            "bg_image_enabled": self.chk_bg_enable.isChecked() if hasattr(self, "chk_bg_enable") else True,
            "bg_image_path": getattr(self.gl_widget, "bg_image_path", ""),
            "bg_dim_ratio": self.slider_bg_dim.value() if hasattr(self, "slider_bg_dim") else 60,
            "bg_fit_mode": self.combo_bg_fit.currentText() if hasattr(self, "combo_bg_fit") else "中央トリミング (画面いっぱい)",
            "bg_rotation": getattr(self, "bg_rotation_deg", 0),
            "skin_enabled": self.chk_skin.isChecked() if hasattr(self, "chk_skin") else True,
            "skin_mouthpiece_path": getattr(self.gl_widget, "skin_mouthpiece_path", ""),
            "skin_lever_off_path": getattr(self.gl_widget, "skin_lever_off_path", ""),
            "skin_lever_on_path": getattr(self.gl_widget, "skin_lever_on_path", ""),
        }

    def _apply_visual_dict_to_ui_and_gl(self, vis: dict, aspect_ratio: str = "16:9", is_chromakey: bool = False, chroma_color: str = "ノーマル（黒）"):
        """指定されたビジュアル設定辞書をUIウィジェットおよびGLキャンバスへ一括適用"""
        if not vis or not isinstance(vis, dict):
            return

        # GLウィジェットへの反映
        self.gl_widget.set_aspect_ratio(aspect_ratio)
        self.gl_widget.set_canvas_bg_color(chroma_color, is_chromakey=is_chromakey)
        self.gl_widget.set_theme_colors(vis.get("color_blow", "#FF5500"), vis.get("color_draw", "#00BFFF"))
        self.gl_widget.set_lever_deco_mode(vis.get("lever_deco_mode", "センターライン (芯線)"))
        self.gl_widget.set_note_opacity(vis.get("note_opacity", 100))
        self.gl_widget.set_show_notes(vis.get("show_notes", True))
        self.gl_widget.set_show_lookahead(vis.get("show_lookahead", True))
        self.gl_widget.set_show_grid(vis.get("show_grid", True))
        self.gl_widget.set_show_bar_lines(vis.get("show_bar_lines", True))
        self.gl_widget.set_show_hole_num(vis.get("show_hole_num", True))
        self.gl_widget.set_hole_num_style(vis.get("hole_num_style", "実機標準 (低音ドット付)"))
        self.gl_widget.set_use_ring(vis.get("show_ring", True))
        self.gl_widget.set_show_glow(vis.get("show_glow", True))
        self.gl_widget.set_show_legend(vis.get("show_legend", True))
        g4_mode = vis.get("grid4_mode", "4音グリッド表示")
        self.gl_widget.set_show_grid4(g4_mode)
        traj_m = vis.get("trajectory_mode", "3段階 (練習標準)")
        self.gl_widget.set_trajectory_mode(traj_m)

        self.gl_widget.set_background_image(
            vis.get("bg_image_path", ""),
            dim_ratio=int(vis.get("bg_dim_ratio", 60)),
            fit_mode=str(vis.get("bg_fit_mode", "中央トリミング (画面いっぱい)")),
            rotation=int(vis.get("bg_rotation", 0)),
            enabled=bool(vis.get("bg_image_enabled", True))
        )
        self.gl_widget.set_skin_enabled(bool(vis.get("skin_enabled", True)))
        self.gl_widget.set_custom_skins(
            mouthpiece_path=vis.get("skin_mouthpiece_path", ""),
            lever_off_path=vis.get("skin_lever_off_path", ""),
            lever_on_path=vis.get("skin_lever_on_path", "")
        )

        # UIコントロールへの同期 (blockSignals 徹底)
        for w_name, val, is_combo, is_slider, is_check in (
            ("traj_combo", traj_m, True, False, False),
            ("lang_combo", vis.get("lang_mode", "ドレミ"), True, False, False),
            ("combo_theme", vis.get("color_theme", "ノーマル"), True, False, False),
            ("combo_lever", vis.get("lever_deco_mode", "センターライン (芯線)"), True, False, False),
            ("slider_op", int(vis.get("note_opacity", 100)), False, True, False),
            ("chk_notes", bool(vis.get("show_notes", True)), False, False, True),
            ("chk_lookahead", bool(vis.get("show_lookahead", True)), False, False, True),
            ("chk_grid", bool(vis.get("show_grid", True)), False, False, True),
            ("chk_bar_lines", bool(vis.get("show_bar_lines", True)), False, False, True),
            ("chk_hole_num", bool(vis.get("show_hole_num", True)), False, False, True),
            ("combo_hole_num_style", vis.get("hole_num_style", "実機標準 (低音ドット付)"), True, False, False),
            ("combo_grid4", g4_mode, True, False, False),
            ("chk_ring", bool(vis.get("show_ring", True)), False, False, True),
            ("chk_glow", bool(vis.get("show_glow", True)), False, False, True),
            ("chk_legend", bool(vis.get("show_legend", True)), False, False, True),
            ("chk_bg_enable", bool(vis.get("bg_image_enabled", True)), False, False, True),
            ("combo_bg_fit", vis.get("bg_fit_mode", "中央トリミング (画面いっぱい)"), True, False, False),
            ("slider_bg_dim", int(vis.get("bg_dim_ratio", 60)), False, True, False),
            ("chk_skin", bool(vis.get("skin_enabled", True)), False, False, True),
        ):
            w = getattr(self, w_name, None)
            if w is not None:
                w.blockSignals(True)
                if is_combo:
                    w.setCurrentText(str(val))
                elif is_slider:
                    w.setValue(int(val))
                elif is_check:
                    w.setChecked(bool(val))
                w.blockSignals(False)

        if hasattr(self, "lbl_op_val") and hasattr(self, "slider_op"):
            self.lbl_op_val.setText(f"{self.slider_op.value()}%")
        if hasattr(self, "lbl_bg_dim_val") and hasattr(self, "slider_bg_dim"):
            self.lbl_bg_dim_val.setText(f"{self.slider_bg_dim.value()}%")
        if hasattr(self, "btn_col_blow"):
            self._update_color_btn(self.btn_col_blow, vis.get("color_blow", "#FF5500"))
        if hasattr(self, "btn_col_draw"):
            self._update_color_btn(self.btn_col_draw, vis.get("color_draw", "#00BFFF"))
        self.gl_widget.update()

    def _build_export_render_settings(self, preset: dict = None) -> dict:
        """選択中の動画プリセット（または引数指定プリセット）から動画レンダラー向け設定辞書を統一生成"""
        if preset is None:
            preset = settings_manager.get_active_preset_dict(self.user_settings)

        exp_style = preset.get("export_style", self.combo_exp_style.currentText() if hasattr(self, "combo_exp_style") else "完成動画 (背景・タイトル合成)")
        bg_col = preset.get("export_bg_color", self.combo_exp_bg.currentText() if hasattr(self, "combo_exp_bg") else "ノーマル（黒）")

        return {
            "inst_type": self.inst_combo.currentText(),
            "trajectory_mode": preset.get("trajectory_mode", "3段階 (練習標準)"),
            "lang_mode": preset.get("lang_mode", "ドレミ"),
            "lever_deco_mode": preset.get("lever_deco_mode", "センターライン (芯線)"),
            "note_speed_ratio": self.gl_widget.note_speed_ratio,
            "default_bpm": getattr(self.timeline, "default_bpm", 120.0),
            "show_notes": preset.get("show_notes", True),
            "show_grid": preset.get("show_grid", True),
            "show_bar_lines": preset.get("show_bar_lines", True),
            "show_grid4": preset.get("grid4_mode", "4音グリッド表示"),
            "show_hole_num": preset.get("show_hole_num", True),
            "hole_num_style": preset.get("hole_num_style", "実機標準 (低音ドット付)"),
            "show_legend": preset.get("show_legend", False),
            "show_lookahead": preset.get("show_lookahead", True),
            "use_ring": preset.get("show_ring", True),
            "show_glow": preset.get("show_glow", True),
            "note_opacity": preset.get("note_opacity", 100),
            "color_blow": preset.get("color_blow", "#FF5500"),
            "color_draw": preset.get("color_draw", "#00BFFF"),
            "canvas_bg_color": bg_col if "クロマキー" in exp_style else "#0d0d0d",
            "export_style": exp_style,
            "skin_enabled": preset.get("skin_enabled", True),
            "skin_mouthpiece_path": preset.get("skin_mouthpiece_path", "") or getattr(self.gl_widget, "skin_mouthpiece_path", ""),
            "skin_lever_off_path": preset.get("skin_lever_off_path", "") or getattr(self.gl_widget, "skin_lever_off_path", ""),
            "skin_lever_on_path": preset.get("skin_lever_on_path", "") or getattr(self.gl_widget, "skin_lever_on_path", ""),
            "bg_image_path": preset.get("bg_image_path", ""),
            "bg_fit_mode": preset.get("bg_fit_mode", "中央トリミング (画面いっぱい)"),
            "bg_rotation": preset.get("bg_rotation", 0),
            "bg_dim_ratio": preset.get("bg_dim_ratio", 60),
            "bg_image_enabled": preset.get("bg_image_enabled", True),
        }

    # =========================================================================
    # 設定の反映と永続化
    # =========================================================================
    def _apply_user_settings(self):
        s = self.user_settings
        self.gl_widget.set_theme_colors(s.get("color_blow", "#FF5500"), s.get("color_draw", "#00BFFF"))
        self.gl_widget.set_lever_deco_mode(s.get("lever_deco_mode", "センターライン (芯線)"))
        self.gl_widget.set_note_opacity(s.get("note_opacity", 100))
        self.gl_widget.set_show_notes(s.get("show_notes", True))
        self.gl_widget.set_show_lookahead(s.get("show_lookahead", True))
        self.gl_widget.set_show_grid(s.get("show_grid", True))
        self.gl_widget.set_show_bar_lines(s.get("show_bar_lines", True))
        if hasattr(self, "chk_bar_lines"):
            self.chk_bar_lines.setChecked(bool(s.get("show_bar_lines", True)))
        self.gl_widget.set_show_hole_num(s.get("show_hole_num", True))
        self.gl_widget.set_hole_num_style(s.get("hole_num_style", "実機標準 (低音ドット付)"))
        if hasattr(self, "combo_hole_num_style"):
            cur_style = s.get("hole_num_style", "実機標準 (低音ドット付)")
            self.combo_hole_num_style.blockSignals(True)
            self.combo_hole_num_style.setCurrentText("通し番号 (1〜)" if "通し番号" in cur_style else "実機標準 (低音ドット付)")
            self.combo_hole_num_style.blockSignals(False)
        self.gl_widget.set_use_ring(s.get("show_ring", s.get("use_ring", True)))
        self.gl_widget.set_show_glow(s.get("show_glow", True))
        self.gl_widget.set_show_legend(s.get("show_legend", True))
        g4_mode = s.get("grid4_mode", s.get("show_grid4", "4音グリッド表示"))
        self.gl_widget.set_show_grid4(g4_mode)

        self.audio_engine.force_main_harmonica = bool(s.get("force_harmonica", True))
        self.audio_engine.set_metronome_mode(s.get("metronome_mode", "標準（頭拍強調）"))
        try:
            cleaned = str(s.get("count_in_mode", "1小節")).replace("小節", "").strip().split()[0]
            ci_m = int(cleaned)
        except Exception:
            ci_m = 1
        self.audio_engine.set_count_in(ci_m)

        # ガイド音源 & リミッター
        guide_eng = s.get("guide_audio_engine", "Windows標準MIDI (WinMM / 推奨)")
        if hasattr(self, "combo_guide_audio"):
            self.combo_guide_audio.blockSignals(True)
            self.combo_guide_audio.setCurrentText(guide_eng)
            self.combo_guide_audio.blockSignals(False)
        self.audio_engine.set_guide_audio_engine(guide_eng)

        if hasattr(self, "chk_yt_limiter"):
            self.chk_yt_limiter.setChecked(bool(s.get("yt_limiter", True)))

        # 動画出力設定
        if hasattr(self, "combo_exp_intro"):
            self.combo_exp_intro.setCurrentText(str(s.get("export_intro_sec", "1秒")))
        if hasattr(self, "combo_exp_outro"):
            self.combo_exp_outro.setCurrentText(str(s.get("export_outro_sec", "2秒")))
        if hasattr(self, "chk_fade_in"):
            self.chk_fade_in.setChecked(bool(s.get("export_fade_in", True)))
        if hasattr(self, "spin_fade_in"):
            self.spin_fade_in.setValue(float(s.get("export_fade_in_sec", 1.5)))
        if hasattr(self, "chk_fade_out"):
            self.chk_fade_out.setChecked(bool(s.get("export_fade_out", True)))
        if hasattr(self, "spin_fade_out"):
            self.spin_fade_out.setValue(float(s.get("export_fade_out_sec", 1.5)))
        if hasattr(self, "combo_fade_title"):
            self.combo_fade_title.setCurrentText(str(s.get("export_fade_title_mode", "フェード中もタイトル表示")))

        # 画面比率同期
        if hasattr(self, "ratio_combo"):
            saved_ratio = str(s.get("aspect_ratio", "16:9"))
            self.ratio_combo.blockSignals(True)
            for item_idx in range(self.ratio_combo.count()):
                if saved_ratio in self.ratio_combo.itemText(item_idx):
                    self.ratio_combo.setCurrentIndex(item_idx)
                    break
            self.ratio_combo.blockSignals(False)

        # 軌跡モード同期
        if hasattr(self, "traj_combo"):
            traj_m = str(s.get("trajectory_mode", "3段階 (練習標準)"))
            self.traj_combo.blockSignals(True)
            self.traj_combo.setCurrentText(traj_m)
            self.traj_combo.blockSignals(False)
            self.gl_widget.set_trajectory_mode(traj_m)

        # 動画音声ボリューム設定同期
        if hasattr(self, "slider_exp_audio_vol"):
            vol_val = int(s.get("export_audio_volume", 100))
            self.slider_exp_audio_vol.setValue(vol_val)
            if hasattr(self, "lbl_exp_audio_vol"):
                self.lbl_exp_audio_vol.setText(f"{vol_val}%")

        # 背景画像・スキン
        self.gl_widget.set_background_image(
            s.get("bg_image_path", ""),
            dim_ratio=int(s.get("bg_dim_ratio", 60)),
            fit_mode=str(s.get("bg_fit_mode", "トリミング (比率維持拡大)")),
            rotation=int(s.get("bg_rotation", 0)),
            enabled=bool(s.get("bg_image_enabled", True))
        )
        self.gl_widget.set_skin_enabled(bool(s.get("skin_enabled", True)))
        self.gl_widget.set_custom_skins(
            mouthpiece_path=s.get("skin_mouthpiece_path", ""),
            lever_off_path=s.get("skin_lever_off_path", ""),
            lever_on_path=s.get("skin_lever_on_path", "")
        )
        self._update_transpose_lock_state()
        self._refresh_video_preset_combo()
        if hasattr(self, "combo_video_preset"):
            self._on_video_preset_changed(self.combo_video_preset.currentText())

    def _save_current_settings(self):
        self.user_settings["inst_type"] = self.inst_combo.currentText()
        self.user_settings["trajectory_mode"] = self.traj_combo.currentText()
        self.user_settings["lang_mode"] = self.lang_combo.currentText()
        ratio_raw = self.ratio_combo.currentText()
        clean_ratio = "9:16" if "9:16" in ratio_raw else ("4:3" if "4:3" in ratio_raw else "16:9")
        self.user_settings["aspect_ratio"] = clean_ratio
        self.user_settings["speed_ratio"] = self.speed_slider.value() / 100.0
        self.user_settings["fall_speed_ratio"] = self.fall_slider.value() / 100.0
        self.user_settings["volume"] = self.vol_slider.value()
        self.user_settings["part_mode"] = self.part_combo.currentText()
        self.user_settings["loop_enabled"] = self.loop_playback
        self.user_settings["transpose"] = self.spin_transpose.value()
        self.user_settings["transpose_accomp"] = self.chk_transpose_accomp.isChecked()
        self.user_settings["metronome_mode"] = self.combo_metro.currentText()
        self.user_settings["count_in_mode"] = self.combo_count_in.currentText()
        self.user_settings["stepup_enabled"] = self.chk_stepup.isChecked()
        self.user_settings["stepup_start_pct"] = self.spin_sp_start.value()
        self.user_settings["stepup_target_pct"] = self.spin_sp_target.value()
        try:
            self.user_settings["stepup_step_pct"] = int(self.combo_sp_step.currentText().replace("+", "").replace("%", ""))
        except ValueError:
            self.user_settings["stepup_step_pct"] = 5
        self.user_settings["color_theme"] = self.combo_theme.currentText()
        self.user_settings["lever_deco_mode"] = self.combo_lever.currentText()
        if hasattr(self, "combo_hole_num_style"):
            self.user_settings["hole_num_style"] = self.combo_hole_num_style.currentText()
        self.user_settings["note_opacity"] = self.slider_op.value()
        self.user_settings["bg_image_path"] = getattr(self.gl_widget, "bg_image_path", "")
        self.user_settings["bg_dim_ratio"] = self.slider_bg_dim.value()
        self.user_settings["bg_fit_mode"] = self.combo_bg_fit.currentText()
        self.user_settings["bg_rotation"] = getattr(self, "bg_rotation_deg", 0)
        self.user_settings["skin_enabled"] = self.chk_skin.isChecked()
        self.user_settings["skin_mouthpiece_path"] = getattr(self.gl_widget, "skin_mouthpiece_path", "")
        self.user_settings["skin_lever_off_path"] = getattr(self.gl_widget, "skin_lever_off_path", "")
        self.user_settings["skin_lever_on_path"] = getattr(self.gl_widget, "skin_lever_on_path", "")
        if hasattr(self, "combo_guide_audio"):
            self.user_settings["guide_audio_engine"] = self.combo_guide_audio.currentText()
        if hasattr(self, "chk_yt_limiter"):
            self.user_settings["yt_limiter"] = self.chk_yt_limiter.isChecked()
        if hasattr(self, "slider_exp_audio_vol"):
            self.user_settings["export_audio_volume"] = self.slider_exp_audio_vol.value()
        if hasattr(self, "combo_exp_intro"):
            self.user_settings["export_intro_sec"] = self.combo_exp_intro.currentText()
        if hasattr(self, "combo_exp_outro"):
            self.user_settings["export_outro_sec"] = self.combo_exp_outro.currentText()
        if hasattr(self, "chk_fade_in"):
            self.user_settings["export_fade_in"] = self.chk_fade_in.isChecked()
        if hasattr(self, "spin_fade_in"):
            self.user_settings["export_fade_in_sec"] = round(self.spin_fade_in.value(), 1)
        if hasattr(self, "chk_fade_out"):
            self.user_settings["export_fade_out"] = self.chk_fade_out.isChecked()
        if hasattr(self, "spin_fade_out"):
            self.user_settings["export_fade_out_sec"] = round(self.spin_fade_out.value(), 1)
        if hasattr(self, "combo_fade_title"):
            self.user_settings["export_fade_title_mode"] = self.combo_fade_title.currentText()
        if hasattr(self, "chk_notes"):
            self.user_settings["show_notes"] = self.chk_notes.isChecked()
        if hasattr(self, "chk_lookahead"):
            self.user_settings["show_lookahead"] = self.chk_lookahead.isChecked()
        if hasattr(self, "chk_grid"):
            self.user_settings["show_grid"] = self.chk_grid.isChecked()
        if hasattr(self, "chk_bar_lines"):
            self.user_settings["show_bar_lines"] = self.chk_bar_lines.isChecked()
        if hasattr(self, "chk_hole_num"):
            self.user_settings["show_hole_num"] = self.chk_hole_num.isChecked()
        if hasattr(self, "chk_ring"):
            self.user_settings["show_ring"] = self.chk_ring.isChecked()
        if hasattr(self, "chk_glow"):
            self.user_settings["show_glow"] = self.chk_glow.isChecked()
        if hasattr(self, "chk_legend"):
            self.user_settings["show_legend"] = self.chk_legend.isChecked()
        if hasattr(self, "chk_bg_enable"):
            self.user_settings["bg_image_enabled"] = self.chk_bg_enable.isChecked()
        if hasattr(self, "combo_grid4"):
            self.user_settings["grid4_mode"] = self.combo_grid4.currentText()

        # ビジュアル設定の二重保存分岐 (v3.1.0: 練習用スタイル vs 動画プリセット)
        vis_cur = self._get_current_visual_dict_from_ui()
        if getattr(self, "_visual_edit_target", "practice") == "video":
            active_p_name = self.user_settings.get("active_video_preset", "📱 YouTube Shorts (縦型・解説)")
            if "video_presets" not in self.user_settings:
                self.user_settings["video_presets"] = copy.deepcopy(settings_manager.DEFAULT_VIDEO_PRESETS)
            if active_p_name in self.user_settings["video_presets"]:
                self.user_settings["video_presets"][active_p_name].update(vis_cur)
                self.user_settings["video_presets"][active_p_name]["aspect_ratio"] = clean_ratio
        else:
            if "practice_visual" not in self.user_settings:
                self.user_settings["practice_visual"] = copy.deepcopy(settings_manager.DEFAULT_PRACTICE_VISUAL)
            self.user_settings["practice_visual"].update(vis_cur)

        settings_manager.save_settings(self.user_settings)

    def _get_count_in_duration(self) -> float:
        try:
            cleaned = self.combo_count_in.currentText().replace("小節", "").strip().split()[0]
            num_m = int(cleaned)
        except Exception:
            num_m = 0
        if num_m <= 0 or not self.timeline:
            return 0.0
        num = getattr(self.timeline, "time_sig_num", 4)
        den = getattr(self.timeline, "time_sig_den", 4)
        bpm = getattr(self.timeline, "default_bpm", 120.0)
        beat_dur = (60.0 / bpm) * (4.0 / den)
        return num_m * num * beat_dur

    def _on_count_in_changed(self, val: str):
        self.user_settings["count_in_mode"] = str(val)
        try:
            cleaned = str(val).replace("小節", "").strip().split()[0]
            m_val = int(cleaned)
        except Exception:
            m_val = 0
        if hasattr(self, "audio_engine"):
            self.audio_engine.set_count_in(m_val)
        self._save_current_settings()

    def _on_grid4_changed(self, mode: str):
        self.user_settings["grid4_mode"] = str(mode)
        self.gl_widget.set_show_grid4(mode)
        self._save_current_settings()

    def _refresh_video_preset_combo(self, select_name: str = None):
        """動画プリセットコンボボックスの選択肢を再構築し、指定プリセットを選択"""
        if not hasattr(self, "combo_video_preset"):
            return
        presets = self.user_settings.get("video_presets", {})
        active = select_name or self.user_settings.get("active_video_preset", "🎥 演奏解説・練習用 (横型・標準)")
        if active not in presets and presets:
            active = list(presets.keys())[0]

        for combo_name in ("combo_video_preset", "combo_design_preset"):
            combo = getattr(self, combo_name, None)
            if combo is not None:
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(list(presets.keys()))
                if active in presets:
                    combo.setCurrentText(active)
                combo.blockSignals(False)

        self._update_preset_button_states(active)

    def _update_preset_button_states(self, preset_name: str):
        """プリセットの種類（公式か自作か）に応じて初期化/削除ボタンの表示・テキストを更新"""
        is_official = preset_name in settings_manager.DEFAULT_VIDEO_PRESETS
        for btn_name in ("btn_preset_reset", "btn_design_preset_reset"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                if is_official:
                    btn.setText("↺ 初期化")
                    btn.setToolTip("公式プリセットの設定値を初期状態に復元します")
                else:
                    btn.setText("🗑️ 削除")
                    btn.setToolTip("この自作動画プリセットを削除します")

    def _on_video_preset_changed(self, preset_name: str):
        """動画プリセット切り替えハンドラ：動画出力タブUIおよびGLプレビューを同期"""
        if not preset_name:
            return
        presets = self.user_settings.get("video_presets", {})
        if preset_name not in presets:
            return

        self.user_settings["active_video_preset"] = preset_name
        p = presets[preset_name]

        for combo_name in ("combo_video_preset", "combo_design_preset"):
            combo = getattr(self, combo_name, None)
            if combo is not None and combo.currentText() != preset_name:
                combo.blockSignals(True)
                combo.setCurrentText(preset_name)
                combo.blockSignals(False)

        # 動画出力タブ各コントロールへの反映（シグナルブロック徹底）
        if hasattr(self, "combo_exp_style"):
            self.combo_exp_style.blockSignals(True)
            self.combo_exp_style.setCurrentText(p.get("export_style", "完成動画 (背景・タイトル合成)"))
            self.combo_exp_style.blockSignals(False)
            self._on_export_style_changed(self.combo_exp_style.currentText())

        if hasattr(self, "combo_exp_bg"):
            self.combo_exp_bg.blockSignals(True)
            self.combo_exp_bg.setCurrentText(p.get("export_bg_color", "ノーマル（黒）"))
            self.combo_exp_bg.blockSignals(False)

        if hasattr(self, "combo_exp_res"):
            self.combo_exp_res.blockSignals(True)
            self.combo_exp_res.setCurrentText(p.get("export_resolution", "Full HD (1920x1080・推奨)"))
            self.combo_exp_res.blockSignals(False)

        if hasattr(self, "combo_exp_fps"):
            self.combo_exp_fps.blockSignals(True)
            self.combo_exp_fps.setCurrentText(p.get("export_fps", "60 FPS (滑らか・推奨)"))
            self.combo_exp_fps.blockSignals(False)

        if hasattr(self, "combo_exp_intro"):
            self.combo_exp_intro.blockSignals(True)
            self.combo_exp_intro.setCurrentText(str(p.get("export_intro_sec", "1秒")))
            self.combo_exp_intro.blockSignals(False)

        if hasattr(self, "combo_exp_outro"):
            self.combo_exp_outro.blockSignals(True)
            self.combo_exp_outro.setCurrentText(str(p.get("export_outro_sec", "2秒")))
            self.combo_exp_outro.blockSignals(False)

        if hasattr(self, "chk_fade_in"):
            self.chk_fade_in.blockSignals(True)
            self.chk_fade_in.setChecked(bool(p.get("export_fade_in", True)))
            self.chk_fade_in.blockSignals(False)

        if hasattr(self, "spin_fade_in"):
            self.spin_fade_in.blockSignals(True)
            self.spin_fade_in.setValue(float(p.get("export_fade_in_sec", 1.5)))
            self.spin_fade_in.setEnabled(self.chk_fade_in.isChecked())
            self.spin_fade_in.blockSignals(False)

        if hasattr(self, "chk_fade_out"):
            self.chk_fade_out.blockSignals(True)
            self.chk_fade_out.setChecked(bool(p.get("export_fade_out", True)))
            self.chk_fade_out.blockSignals(False)

        if hasattr(self, "spin_fade_out"):
            self.spin_fade_out.blockSignals(True)
            self.spin_fade_out.setValue(float(p.get("export_fade_out_sec", 1.5)))
            self.spin_fade_out.setEnabled(self.chk_fade_out.isChecked())
            self.spin_fade_out.blockSignals(False)

        if hasattr(self, "combo_fade_title"):
            self.combo_fade_title.blockSignals(True)
            self.combo_fade_title.setCurrentText(str(p.get("export_fade_title_mode", "フェード中もタイトル表示")))
            self.combo_fade_title.blockSignals(False)

        if hasattr(self, "chk_exp_title"):
            self.chk_exp_title.blockSignals(True)
            self.chk_exp_title.setChecked(bool(p.get("export_title_enabled", True)))
            self.chk_exp_title.blockSignals(False)

        if hasattr(self, "combo_title_template"):
            self.combo_title_template.blockSignals(True)
            self.combo_title_template.setCurrentText(str(p.get("export_title_template", "イントロ中央＋右上常時")))
            self.combo_title_template.blockSignals(False)

        if hasattr(self, "combo_exp_audio"):
            self.combo_exp_audio.blockSignals(True)
            self.combo_exp_audio.setCurrentText(str(p.get("audio_quick_mode", "伴奏音源 (外部音源優先)")))
            self.combo_exp_audio.blockSignals(False)

        if hasattr(self, "chk_exp_reverb"):
            self.chk_exp_reverb.blockSignals(True)
            self.chk_exp_reverb.setChecked(bool(p.get("reverb_enabled", False)))
            self.chk_exp_reverb.blockSignals(False)

        if hasattr(self, "chk_yt_limiter"):
            self.chk_yt_limiter.blockSignals(True)
            self.chk_yt_limiter.setChecked(bool(p.get("yt_limiter", True)))
            self.chk_yt_limiter.blockSignals(False)

        if hasattr(self, "slider_exp_audio_vol"):
            vol_val = int(p.get("export_audio_volume", 100))
            self.slider_exp_audio_vol.blockSignals(True)
            self.slider_exp_audio_vol.setValue(vol_val)
            self.slider_exp_audio_vol.blockSignals(False)
            if hasattr(self, "lbl_exp_audio_vol"):
                self.lbl_exp_audio_vol.setText(f"{vol_val}%")

        self._update_preset_button_states(preset_name)

        # 現在のタブが動画出力タブ(3)、または画面作りタブ(1)で動画プリセット編集中ならGLに即時反映
        cur_tab = self.tab_widget.currentIndex() if hasattr(self, "tab_widget") else 0
        if cur_tab == 3 or (cur_tab == 1 and getattr(self, "_visual_edit_target", "practice") == "video"):
            asp = str(p.get("aspect_ratio", "16:9"))
            is_chroma = ("クロマキー" in str(p.get("export_style", "")))
            bg_col = str(p.get("export_bg_color", "ノーマル（黒）"))
            self._apply_visual_dict_to_ui_and_gl(p, aspect_ratio=asp, is_chromakey=is_chroma, chroma_color=bg_col)

    def _on_save_video_preset(self):
        """現在の動画設定および動画用ビジュアル設定を選択中プリセットに上書き保存"""
        active = self.combo_video_preset.currentText()
        if not active:
            return
        presets = self.user_settings.setdefault("video_presets", {})
        target = presets.setdefault(active, {})

        if getattr(self, "_visual_edit_target", "practice") == "video":
            cur_vis = self._get_current_visual_dict_from_ui()
            target.update(cur_vis)

        ratio_raw = self.ratio_combo.currentText() if hasattr(self, "ratio_combo") else "16:9"
        clean_ratio = "9:16" if "9:16" in ratio_raw else ("4:3" if "4:3" in ratio_raw else "16:9")
        target["aspect_ratio"] = clean_ratio
        if hasattr(self, "combo_exp_style"):
            target["export_style"] = self.combo_exp_style.currentText()
        if hasattr(self, "combo_exp_bg"):
            target["export_bg_color"] = self.combo_exp_bg.currentText()
        if hasattr(self, "combo_exp_res"):
            target["export_resolution"] = self.combo_exp_res.currentText()
        if hasattr(self, "combo_exp_fps"):
            target["export_fps"] = self.combo_exp_fps.currentText()
        if hasattr(self, "combo_exp_intro"):
            target["export_intro_sec"] = self.combo_exp_intro.currentText()
        if hasattr(self, "combo_exp_outro"):
            target["export_outro_sec"] = self.combo_exp_outro.currentText()
        if hasattr(self, "chk_fade_in"):
            target["export_fade_in"] = self.chk_fade_in.isChecked()
        if hasattr(self, "spin_fade_in"):
            target["export_fade_in_sec"] = self.spin_fade_in.value()
        if hasattr(self, "chk_fade_out"):
            target["export_fade_out"] = self.chk_fade_out.isChecked()
        if hasattr(self, "spin_fade_out"):
            target["export_fade_out_sec"] = self.spin_fade_out.value()
        if hasattr(self, "combo_fade_title"):
            target["export_fade_title_mode"] = self.combo_fade_title.currentText()
        if hasattr(self, "chk_exp_title"):
            target["export_title_enabled"] = self.chk_exp_title.isChecked()
        if hasattr(self, "combo_title_template"):
            target["export_title_template"] = self.combo_title_template.currentText()
        if hasattr(self, "combo_exp_audio"):
            target["audio_quick_mode"] = self.combo_exp_audio.currentText()
        if hasattr(self, "chk_exp_reverb"):
            target["reverb_enabled"] = self.chk_exp_reverb.isChecked()
        if hasattr(self, "chk_yt_limiter"):
            target["yt_limiter"] = self.chk_yt_limiter.isChecked()
        if hasattr(self, "slider_exp_audio_vol"):
            target["export_audio_volume"] = self.slider_exp_audio_vol.value()

        self._save_current_settings()
        QMessageBox.information(self, "プリセット保存", f"プリセット「{active}」に現在の設定を保存しました。")

    def _on_save_as_video_preset(self):
        """現在の設定をもとに新しい名前で動画プリセットを保存"""
        cur_active = self.combo_video_preset.currentText()
        presets = self.user_settings.setdefault("video_presets", {})
        base_dict = copy.deepcopy(presets.get(cur_active, {}))

        new_name, ok = QInputDialog.getText(
            self, "新規プリセット作成",
            "新しい動画プリセット名を入力してください:",
            QLineEdit.EchoMode.Normal,
            f"{cur_active} (コピー)"
        )
        if not ok or not new_name.strip():
            return
        name = new_name.strip()
        if name in presets:
            reply = QMessageBox.question(
                self, "上書き確認",
                f"プリセット「{name}」は既に存在します。上書きしますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if getattr(self, "_visual_edit_target", "practice") == "video":
            base_dict.update(self._get_current_visual_dict_from_ui())
        if hasattr(self, "combo_exp_style"):
            base_dict["export_style"] = self.combo_exp_style.currentText()
        if hasattr(self, "combo_exp_bg"):
            base_dict["export_bg_color"] = self.combo_exp_bg.currentText()
        if hasattr(self, "combo_exp_res"):
            base_dict["export_resolution"] = self.combo_exp_res.currentText()
        if hasattr(self, "combo_exp_fps"):
            base_dict["export_fps"] = self.combo_exp_fps.currentText()
        if hasattr(self, "combo_exp_intro"):
            base_dict["export_intro_sec"] = self.combo_exp_intro.currentText()
        if hasattr(self, "combo_exp_outro"):
            base_dict["export_outro_sec"] = self.combo_exp_outro.currentText()
        if hasattr(self, "chk_fade_in"):
            base_dict["export_fade_in"] = self.chk_fade_in.isChecked()
        if hasattr(self, "spin_fade_in"):
            base_dict["export_fade_in_sec"] = self.spin_fade_in.value()
        if hasattr(self, "chk_fade_out"):
            base_dict["export_fade_out"] = self.chk_fade_out.isChecked()
        if hasattr(self, "spin_fade_out"):
            base_dict["export_fade_out_sec"] = self.spin_fade_out.value()
        if hasattr(self, "combo_fade_title"):
            base_dict["export_fade_title_mode"] = self.combo_fade_title.currentText()
        if hasattr(self, "chk_exp_title"):
            base_dict["export_title_enabled"] = self.chk_exp_title.isChecked()
        if hasattr(self, "combo_title_template"):
            base_dict["export_title_template"] = self.combo_title_template.currentText()
        if hasattr(self, "combo_exp_audio"):
            base_dict["audio_quick_mode"] = self.combo_exp_audio.currentText()
        if hasattr(self, "chk_exp_reverb"):
            base_dict["reverb_enabled"] = self.chk_exp_reverb.isChecked()
        if hasattr(self, "chk_yt_limiter"):
            base_dict["yt_limiter"] = self.chk_yt_limiter.isChecked()
        if hasattr(self, "slider_exp_audio_vol"):
            base_dict["export_audio_volume"] = self.slider_exp_audio_vol.value()

        presets[name] = base_dict
        self.user_settings["active_video_preset"] = name
        self._refresh_video_preset_combo(select_name=name)
        self._on_video_preset_changed(name)
        self._save_current_settings()
        QMessageBox.information(self, "作成完了", f"新規プリセット「{name}」を作成しました。")

    def _on_reset_or_delete_video_preset(self):
        """公式プリセットなら初期値にリセット、自作プリセットなら削除"""
        active = self.combo_video_preset.currentText()
        if not active:
            return
        presets = self.user_settings.setdefault("video_presets", {})
        if active in settings_manager.DEFAULT_VIDEO_PRESETS:
            reply = QMessageBox.question(
                self, "初期化確認",
                f"公式プリセット「{active}」の設定を標準の初期値に戻しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                presets[active] = copy.deepcopy(settings_manager.DEFAULT_VIDEO_PRESETS[active])
                self._on_video_preset_changed(active)
                self._save_current_settings()
                QMessageBox.information(self, "初期化完了", f"「{active}」を初期設定に復元しました。")
        else:
            reply = QMessageBox.question(
                self, "プリセット削除確認",
                f"自作プリセット「{active}」を削除してもよろしいですか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                presets.pop(active, None)
                fallback = "🎥 演奏解説・練習用 (横型・標準)"
                if fallback not in presets and presets:
                    fallback = list(presets.keys())[0]
                self.user_settings["active_video_preset"] = fallback
                self._refresh_video_preset_combo(select_name=fallback)
                self._on_video_preset_changed(fallback)
                self._save_current_settings()
                QMessageBox.information(self, "削除完了", f"プリセット「{active}」を削除しました。")

    def _on_copy_practice_visual_to_preset(self):
        """現在の練習画面の見た目設定（色、装飾、音名、凡例、背景、スキン）を選択中の動画プリセットにコピー"""
        active = self.combo_video_preset.currentText()
        if not active:
            return
        presets = self.user_settings.setdefault("video_presets", {})
        target = presets.setdefault(active, {})
        prac = self.user_settings.get("practice_visual", {})

        for k in settings_manager.VISUAL_KEYS:
            if k in prac:
                target[k] = prac[k]

        asp = str(target.get("aspect_ratio", "16:9"))
        is_chroma = ("クロマキー" in str(target.get("export_style", "")))
        bg_col = str(target.get("export_bg_color", "ノーマル（黒）"))
        self._apply_visual_dict_to_ui_and_gl(target, aspect_ratio=asp, is_chromakey=is_chroma, chroma_color=bg_col)
        self._save_current_settings()
        QMessageBox.information(
            self, "反映完了",
            f"現在の「練習画面」の見た目設定をプリセット「{active}」にコピーしました。\n動画プレビュー画面に即時反映されています。"
        )

    def _on_jump_design_for_video(self):
        """「🎨 このプリセットの画面デザインを編集...」ボタン：画面作りタブに移動し、ターゲットを動画プリセットに設定"""
        self.tab_widget.setCurrentIndex(1)
        if hasattr(self, "combo_visual_target"):
            self.combo_visual_target.setCurrentIndex(1)

    def _on_export_style_changed(self, style: str):
        is_chroma = ("クロマキー" in style)
        is_trans = ("完全背景透過" in style)
        self.combo_exp_bg.setEnabled(is_chroma)
        if hasattr(self, "lbl_exp_bg"):
            self.lbl_exp_bg.setEnabled(is_chroma)

        title_enabled = (not is_chroma and not is_trans)
        if hasattr(self, "chk_exp_title"):
            self.chk_exp_title.setEnabled(title_enabled)
        if hasattr(self, "combo_title_template"):
            self.combo_title_template.setEnabled(title_enabled)
        if hasattr(self, "lbl_title_tpl"):
            self.lbl_title_tpl.setEnabled(title_enabled)
        if hasattr(self, "txt_exp_title"):
            self.txt_exp_title.setEnabled(title_enabled)
        if hasattr(self, "txt_exp_credit"):
            self.txt_exp_credit.setEnabled(title_enabled)
        if hasattr(self, "lbl_exp_title"):
            self.lbl_exp_title.setEnabled(title_enabled)
        if hasattr(self, "lbl_exp_credit"):
            self.lbl_exp_credit.setEnabled(title_enabled)
        if hasattr(self, "combo_fade_title"):
            self.combo_fade_title.setEnabled(title_enabled)
        if hasattr(self, "lbl_fade_title"):
            self.lbl_fade_title.setEnabled(title_enabled)

        if hasattr(self, "btn_export_video") and self.btn_export_video:
            if is_trans:
                self.btn_export_video.setText("🎥 透過MOV動画素材の書き出し開始")
            else:
                self.btn_export_video.setText("🎥 MP4動画の書き出し開始")
        self._on_chroma_bg_changed(self.combo_exp_bg.currentText())

    def _on_canvas_wheel_seek(self, steps: int, modifiers: int = 0):
        """キャンバス上でのホイール回転による高精度前後スクラブ (Shift: 1/4拍, Ctrl: 1小節, 通常: 1拍)"""
        if not self.timeline or not self.timeline.measures_timeline:
            return
        tpb = getattr(self.timeline, "ticks_per_beat", 480)
        time_sig_num = getattr(self.timeline, "time_sig_num", 4)
        if modifiers & 0x02000000:  # Qt.KeyboardModifier.ShiftModifier
            step_ticks = max(1, tpb // 4)
        elif modifiers & 0x04000000:  # Qt.KeyboardModifier.ControlModifier
            step_ticks = tpb * time_sig_num
        else:
            step_ticks = tpb
        cur_sec = self.clock.get_current_base_sec()
        cur_tick = self.timeline.sec_to_tick(cur_sec)
        target_tick = max(0, min(self.timeline.total_ticks, cur_tick + steps * step_ticks))
        target_sec = self.timeline.tick_to_sec(target_tick)
        self._seek_to_time(target_sec)

    def _seek_to_time(self, target_sec: float):
        """指定時刻への高精度シークおよび音源・クロック同期"""
        target_sec = max(0.0, min(self.timeline.total_duration_sec, target_sec))
        st = self.clock.get_state()
        self.clock.set_anchor(target_sec, speed_ratio=self.speed_slider.value() / 100.0, state=st)
        self.audio_engine.seek(target_sec)
        self._sync_ext_audio_playback(st == SharedClockBridge.STATE_PLAYING, target_sec)
        self._update_time_label(target_sec)

    def _on_canvas_note_mute_changed(self):
        """キャンバス上でのノーツ発音/除外切替ハンドラ"""
        if self.timeline:
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.seek(self.clock.get_current_base_sec())
        self.audio_engine.play_ui_click()
        self.lbl_status_msg.setText("🔇 ノーツの発音/除外を切り替えました")
        self._check_out_of_range_and_notify()

    def _on_toggle_sidebar(self):
        """右側4タブ操作サイドバーの表示 / 折りたたみ切替"""
        is_visible = self.sidebar_frame.isVisible()
        self.sidebar_frame.setVisible(not is_visible)
        self.btn_toggle_sidebar.setText("◀ パネル" if is_visible else "▶ 全画面")

    def _on_future_feature_clicked(self, feature_name: str, step_name: str):
        self.lbl_status_msg.setText(f"ℹ️ {feature_name} は {step_name} で実装予定です")
        QMessageBox.information(
            self, "将来実装機能",
            f"【{feature_name}】\n\nこの機能はロードマップの「{step_name}」にて実装・統合予定です。\n現在はレイアウトプレースホルダーとして配置されています。"
        )

    # =========================================================================
    # カラーテーマ・装飾ハンドラ
    # =========================================================================
    def _update_color_btn(self, btn: QPushButton, hex_str: str):
        btn.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #FFFFFF; border-radius: 4px;")
        btn.setToolTip(hex_str)

    def _choose_color_blow(self):
        cur = QColor(self.user_settings.get("color_blow", "#FF5500"))
        col = QColorDialog.getColor(cur, self, "吹音色 (Blow) の選択")
        if col.isValid():
            hex_str = col.name().upper()
            self.user_settings["color_blow"] = hex_str
            self._update_color_btn(self.btn_col_blow, hex_str)
            self.combo_theme.setCurrentText("カスタム")
            self.gl_widget.set_theme_colors(hex_str, self.user_settings.get("color_draw", "#00BFFF"))
            self._save_current_settings()

    def _choose_color_draw(self):
        cur = QColor(self.user_settings.get("color_draw", "#00BFFF"))
        col = QColorDialog.getColor(cur, self, "吸音色 (Draw) の選択")
        if col.isValid():
            hex_str = col.name().upper()
            self.user_settings["color_draw"] = hex_str
            self._update_color_btn(self.btn_col_draw, hex_str)
            self.combo_theme.setCurrentText("カスタム")
            self.gl_widget.set_theme_colors(self.user_settings.get("color_blow", "#FF5500"), hex_str)
            self._save_current_settings()

    def _on_theme_changed(self, theme_name: str):
        if theme_name in settings_manager.THEME_PRESETS:
            blow, draw = settings_manager.THEME_PRESETS[theme_name]
            self.user_settings["color_blow"] = blow
            self.user_settings["color_draw"] = draw
            self._update_color_btn(self.btn_col_blow, blow)
            self._update_color_btn(self.btn_col_draw, draw)
            self.gl_widget.set_theme_colors(blow, draw)
            self._save_current_settings()

    def _on_lever_changed(self, mode: str):
        self.gl_widget.set_lever_deco_mode(mode)
        self._save_current_settings()

    def _on_opacity_changed(self, val: int):
        self.lbl_op_val.setText(f"{val}%")
        self.gl_widget.set_note_opacity(val)
        self._save_current_settings()

    # =========================================================================
    # 背景画像 & スキンハンドラ
    # =========================================================================
    def _on_bg_enable_toggled(self, checked: bool):
        self.gl_widget.bg_image_enabled = checked
        self.gl_widget.update()
        self.lbl_status_msg.setText(f"🖼️ 背景画像表示: {'ON' if checked else 'OFF'}")
        self._save_current_settings()

    def _on_select_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "背景画像を選択", "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.webp);;全ファイル (*)"
        )
        if path:
            self._set_bg_image(path)

    def _set_bg_image(self, filepath: str):
        self.gl_widget.set_background_image(
            filepath,
            dim_ratio=self.slider_bg_dim.value(),
            fit_mode=self.combo_bg_fit.currentText(),
            rotation=self.bg_rotation_deg
        )
        self._set_elided_label_text(self.lbl_bg_info, f"画像: {os.path.basename(filepath)}", filepath, max_width=270)
        self.lbl_status_msg.setText(f"🖼️ 背景画像を設定しました: {os.path.basename(filepath)}")
        self._save_current_settings()

    def _on_clear_bg_image(self):
        self.gl_widget.clear_background_image()
        self.lbl_bg_info.setText("画像: 未設定 (ダーク背景)")
        self.lbl_bg_info.setToolTip("")
        self.lbl_status_msg.setText("🗑️ 背景画像を解除しました")
        self._save_current_settings()

    def _on_bg_fit_changed(self, mode: str):
        self.gl_widget.set_background_fit_mode(mode)
        self._save_current_settings()

    def _on_rotate_bg_image(self):
        self.bg_rotation_deg = (self.bg_rotation_deg + 90) % 360
        self.btn_bg_rot.setText(f"⟳ 90°回転 ({self.bg_rotation_deg}°)")
        self.gl_widget.set_background_rotation(self.bg_rotation_deg)
        self._save_current_settings()

    def _on_bg_dim_changed(self, val: int):
        self.lbl_bg_dim_val.setText(f"{val}%")
        self.gl_widget.set_background_dim(val)
        self._save_current_settings()

    def _on_skin_toggled(self, checked: bool):
        self.gl_widget.set_skin_enabled(checked)
        self.lbl_status_msg.setText(f"🎷 ハーモニカスキン: {'ON' if checked else 'OFF'}")
        self._save_current_settings()

    def _on_select_custom_skin(self):
        from dialogs import SkinSelectDialog
        dlg = SkinSelectDialog(self.user_settings, parent=self)
        if dlg.exec():
            res = dlg.get_selected_skins()
            self.user_settings["skin_mouthpiece_path"] = res["mouthpiece_path"]
            self.user_settings["skin_lever_off_path"] = res["lever_off_path"]
            self.user_settings["skin_lever_on_path"] = res["lever_on_path"]
            self.user_settings["skin_enabled"] = res["skin_enabled"]
            self.chk_skin.setChecked(res["skin_enabled"])
            self.gl_widget.set_skin_enabled(res["skin_enabled"])
            self.gl_widget.set_custom_skins(
                mouthpiece_path=res["mouthpiece_path"],
                lever_off_path=res["lever_off_path"],
                lever_on_path=res["lever_on_path"]
            )
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()
            self._save_current_settings()
            self.lbl_status_msg.setText("🎨 ハーモニカスキン設定を更新しました")

    def _on_reset_preset_skin(self):
        from config import get_portable_path
        skins_dir = get_portable_path("skins")
        self.gl_widget.set_custom_skins(
            mouthpiece_path=os.path.join(skins_dir, "マウスピース_メタル.png"),
            lever_off_path=os.path.join(skins_dir, "レバーオフ_シルバー.png"),
            lever_on_path=os.path.join(skins_dir, "レバーオン_シルバー.png")
        )
        self.user_settings["skin_mouthpiece_path"] = os.path.join(skins_dir, "マウスピース_メタル.png")
        self.user_settings["skin_lever_off_path"] = os.path.join(skins_dir, "レバーオフ_シルバー.png")
        self.user_settings["skin_lever_on_path"] = os.path.join(skins_dir, "レバーオン_シルバー.png")
        self.gl_widget.invalidate_static_cache()
        self.gl_widget.update()
        self._save_current_settings()
        self.lbl_status_msg.setText("↺ スキンを標準メタル・シルバーに初期化しました")

    def _on_fingering_preset_changed(self, preset_name: str):
        import harmonica_map
        harmonica_map.CURRENT_SONG_PRESET = preset_name
        harmonica_map.apply_fingering_preset(preset_name)
        if self.timeline and self.timeline.filepath:
            harmonica_map.save_song_fingering(self.timeline.filepath)
        self.timeline.rebind_fingerings(self.inst_combo.currentText())
        self.gl_widget.set_timeline_data(self.timeline)
        self.lbl_status_msg.setText(f"運指プリセット: {preset_name}")
        self._save_current_settings()

    def _on_fingering_edit_mode_toggled(self, checked: bool):
        if checked and hasattr(self, "chk_mute_edit") and self.chk_mute_edit.isChecked():
            self.chk_mute_edit.blockSignals(True)
            self.chk_mute_edit.setChecked(False)
            self.chk_mute_edit.blockSignals(False)
            self.gl_widget.set_mute_edit_mode(False)
        self.gl_widget.set_fingering_edit_mode(checked)
        if checked:
            self.lbl_status_msg.setText("🎯 かえ指モード: 有効 (白枠ノーツをクリックして吹吸・穴番号を切替 / Fキーで解除)")
        else:
            self.lbl_status_msg.setText("待機中...")

    def _on_mute_edit_mode_toggled(self, checked: bool):
        if checked and hasattr(self, "chk_fing_edit") and self.chk_fing_edit.isChecked():
            self.chk_fing_edit.blockSignals(True)
            self.chk_fing_edit.setChecked(False)
            self.chk_fing_edit.blockSignals(False)
            self.gl_widget.set_fingering_edit_mode(False)
        self.gl_widget.set_mute_edit_mode(checked)
        if checked:
            self.lbl_status_msg.setText("🔇 ノーツ非表示モード: 有効 (ノーツをクリックして発音/除外・非表示を切替 / Mキーで解除)")
        else:
            self.lbl_status_msg.setText("待機中...")

    def _on_canvas_fingering_changed(self, nd: dict, cand: dict):
        self.audio_engine.play_ui_click()
        note_name = nd.get("name_jp", "")
        cand_str = f"{cand['hole']}穴 {cand['action']} {cand['lever']}"
        self.lbl_status_msg.setText(f"🎯 運指切替: {note_name} → {cand_str}")
        self._update_transpose_lock_state()

    def _on_open_fingering_dialog(self):
        from dialogs import FingeringEditorDialog
        dlg = FingeringEditorDialog(
            timeline=self.timeline,
            clock=self.clock,
            audio_engine=self.audio_engine,
            gl_widget=self.gl_widget,
            parent=self
        )
        if dlg.exec():
            if hasattr(self, "combo_fing_preset"):
                self.combo_fing_preset.blockSignals(True)
                self.combo_fing_preset.setCurrentText(harmonica_map.normalize_fingering_preset(harmonica_map.CURRENT_SONG_PRESET))
                self.combo_fing_preset.blockSignals(False)
            if hasattr(self, "combo_monophonic_mode"):
                self.combo_monophonic_mode.blockSignals(True)
                self.combo_monophonic_mode.setCurrentText(harmonica_map.CURRENT_MONOPHONIC_MODE)
                self.combo_monophonic_mode.blockSignals(False)
            self._update_song_info_labels()
            self._update_transpose_lock_state()
            self.lbl_status_msg.setText("💾 変え指設定を保存・適用しました")

    def _on_reset_song_fingering(self):
        from dialogs import confirm_dialog
        if confirm_dialog(
            self,
            "運指データの初期化確認",
            f"曲「{self.timeline.filename}」の個別運指データをすべて初期化（リセット）し、\n運指プリセットの初期状態へ戻しますか？",
            default_yes=False
        ):
            harmonica_map.reset_song_fingering(self.timeline.filepath)
            self.timeline.rebind_fingerings(self.inst_combo.currentText())
            if self.audio_engine:
                self.audio_engine.load_timeline(self.timeline)
                self.audio_engine.seek(self.clock.get_current_base_sec())
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()
            self._check_out_of_range_and_notify()
            self._update_transpose_lock_state()
            self.lbl_status_msg.setText("🔄 曲別の運指・除外データを初期状態にリセットしました")

    # =========================================================================
    # A-Bループ ＆ 小節ジャンプ制御
    # =========================================================================
    def _reset_loop_ranges_to_song(self):
        total_m = len(self.timeline.measures_timeline) if self.timeline.measures_timeline else 12
        self.spin_loop_a.blockSignals(True)
        self.spin_loop_b.blockSignals(True)
        self.spin_jump.blockSignals(True)

        self.spin_loop_a.setRange(1, total_m)
        self.spin_loop_b.setRange(1, total_m)
        self.spin_jump.setRange(1, total_m)

        self.spin_loop_a.setValue(1)
        self.spin_loop_b.setValue(total_m)
        self.spin_jump.setValue(1)
        self.lbl_jump_total.setText(f"/ {total_m} 小節")

        self.spin_loop_a.blockSignals(False)
        self.spin_loop_b.blockSignals(False)
        self.spin_jump.blockSignals(False)

        self._update_loop_range()

    def _on_set_loop_a(self):
        cur_sec = max(0.0, self.clock.get_current_base_sec())
        m, _, _, _, _ = self.timeline.get_measure_and_beat(cur_sec)
        val_b = self.spin_loop_b.value()
        if m > val_b:
            self.spin_loop_b.setValue(m)
        self.spin_loop_a.setValue(m)
        self._update_loop_range()

    def _on_set_loop_b(self):
        cur_sec = max(0.0, self.clock.get_current_base_sec())
        m, _, _, _, _ = self.timeline.get_measure_and_beat(cur_sec)
        val_a = self.spin_loop_a.value()
        if m < val_a:
            self.spin_loop_a.setValue(m)
        self.spin_loop_b.setValue(m)
        self._update_loop_range()

    def _on_reset_loop_ab(self):
        total_m = len(self.timeline.measures_timeline) if self.timeline.measures_timeline else 12
        self.spin_loop_a.setValue(1)
        self.spin_loop_b.setValue(total_m)
        self._update_loop_range()
        self.lbl_status_msg.setText("🔁 A-Bループ区間を全曲にリセットしました")

    def _on_loop_spin_changed(self):
        val_a = self.spin_loop_a.value()
        val_b = self.spin_loop_b.value()
        sender = self.sender()
        if val_a > val_b:
            if sender == self.spin_loop_b:
                self.spin_loop_a.blockSignals(True)
                self.spin_loop_a.setValue(val_b)
                self.spin_loop_a.blockSignals(False)
            else:
                self.spin_loop_b.blockSignals(True)
                self.spin_loop_b.setValue(val_a)
                self.spin_loop_b.blockSignals(False)
        self._update_loop_range()

    def _update_loop_range(self):
        val_a = self.spin_loop_a.value()
        val_b = self.spin_loop_b.value()
        a_sec = self.timeline.get_sec_for_measure(val_a)
        b_sec = self.timeline.get_measure_end_sec(val_b)
        tot_sec = self.timeline.total_duration_sec

        a_ratio = (a_sec / tot_sec) if tot_sec > 0 else 0.0
        b_ratio = (b_sec / tot_sec) if tot_sec > 0 else 1.0

        self.seek_slider.set_loop_range(a_ratio, b_ratio, self.loop_playback)
        self.gl_widget.set_loop_markers(a_sec, b_sec, self.loop_playback)
        self.audio_engine.set_loop_range(a_sec, b_sec, self.loop_playback)
        self._save_current_song_profile()
        self.lbl_status_msg.setText(f"🔁 A-Bループ区間: {val_a:03d} 〜 {val_b:03d} 小節")

    def _on_jump_measure(self):
        m = self.spin_jump.value()
        sec = self.timeline.get_sec_for_measure(m)
        st = self.clock.get_state()
        self.clock.set_anchor(sec, speed_ratio=self.speed_slider.value() / 100.0, state=st)
        self.audio_engine.seek(sec)
        self._sync_ext_audio_playback(st == SharedClockBridge.STATE_PLAYING, sec)
        self.lbl_status_msg.setText(f"⏩ {m:03d} 小節の頭へジャンプしました")

    def _update_transpose_lock_state(self):
        """カスタム運指が1件以上存在する場合、音名ズレ防止のため移調コントロールをロック"""
        locked = harmonica_map.has_custom_fingering()
        for w_name in ("btn_trans_down_oct", "btn_trans_minus_1", "spin_transpose", "btn_trans_plus_1", "btn_trans_up_oct", "chk_transpose_accomp"):
            w = getattr(self, w_name, None)
            if w is not None:
                w.setEnabled(not locked)
        if hasattr(self, "spin_transpose"):
            if locked:
                self.spin_transpose.setStyleSheet("background-color: #2D1A10; border: 1px solid #D97706; color: #FBBF24; font-weight: bold;")
                self.spin_transpose.setToolTip(
                    "🔒 カスタム運指（変え指）が設定されているため、音名ズレ防止のため移調をロックしています。\n"
                    "移調を変更したい場合は、練習タブの「🔄 初期化」から個別運指をリセットしてください。"
                )
            else:
                self.spin_transpose.setStyleSheet("")
                self.spin_transpose.setToolTip("半音単位の移調 (-24〜+24半音 / ±2オクターブ) [直接入力 / マウスホイールで変更]")

    def _on_transpose_changed(self, *args):
        val = self.spin_transpose.value()
        trans_acc = self.chk_transpose_accomp.isChecked()
        self.timeline.set_transpose(val, trans_acc)
        self.gl_widget.set_timeline_data(self.timeline)
        self.audio_engine.set_transpose(val, trans_acc)
        self._save_current_song_profile()
        sign = f"+{val}" if val > 0 else str(val)
        acc_str = " (伴奏含む)" if trans_acc else " (主旋律のみ)"
        self.lbl_status_msg.setText(f"🎹 移調: {sign} st ({'原曲キー' if val == 0 else f'{sign}半音'}){acc_str}")
        self._check_out_of_range_and_notify()
        self._save_current_settings()

    def _on_metro_changed(self, val: str):
        self.audio_engine.set_metronome_mode(val)
        self.lbl_status_msg.setText(f"⏱ メトロノーム: {val}")
        self._save_current_settings()

    def _on_stepup_toggled(self, checked: bool):
        self.user_settings["stepup_enabled"] = bool(checked)
        self._stepup_running = False
        if checked:
            self.chk_loop.setChecked(True)
            self._is_stepup_auto_adjusting = True
            try:
                self.speed_slider.setValue(self.spin_sp_start.value())
            finally:
                self._is_stepup_auto_adjusting = False
            self._stepup_running = True
        self.lbl_status_msg.setText(f"📈 ステップアップ練習: {'ON' if checked else 'OFF'}")
        self._save_current_settings()

    def _handle_loop_wrapped(self):
        """ループ折り返し時にバックグラウンド音声スレッドから安全に発火"""
        loop_start_sec = self.audio_engine.loop_a_sec if (self.loop_playback and self.audio_engine.loop_a_sec is not None) else 0.0
        cur_sec = self.clock.get_current_base_sec()
        if cur_sec < loop_start_sec:
            self._loop_waiting_for_a_sec = loop_start_sec
            self._sync_ext_audio_playback(False)
        else:
            self._loop_waiting_for_a_sec = None
            self._sync_ext_audio_playback(self.clock.get_state() == SharedClockBridge.STATE_PLAYING, loop_start_sec)

        if self.chk_stepup.isChecked():
            start_pct = int(self.spin_sp_start.value())
            target_pct = int(self.spin_sp_target.value())
            try:
                step_pct = int(self.combo_sp_step.currentText().replace("+", "").replace("%", ""))
            except ValueError:
                step_pct = 5
            cur_pct = self.speed_slider.value()
            if cur_pct < target_pct:
                new_pct = min(target_pct, cur_pct + step_pct)
                self._is_stepup_auto_adjusting = True
                try:
                    self.speed_slider.setValue(new_pct)
                finally:
                    self._is_stepup_auto_adjusting = False
                if new_pct >= target_pct:
                    self.lbl_status_msg.setText(f"🎯 目標速度 {target_pct}% に到達しました！（ループ継続）")
                else:
                    self.lbl_status_msg.setText(f"📈 ステップアップ: {cur_pct}% ➔ {new_pct}% (目標 {target_pct}%)")
            else:
                self.lbl_status_msg.setText(f"🎯 目標速度 {target_pct}% で反復練習中")

    # =========================================================================
    # ファイル読込とドラッグ＆ドロップ
    # =========================================================================
    IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif', '.tiff')
    AUDIO_EXTS = ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.mp4', '.wma')

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in ('.mid', '.midi') or ext in self.IMAGE_EXTS or ext in self.AUDIO_EXTS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            ext = os.path.splitext(filepath)[1].lower()
            if ext in ('.mid', '.midi'):
                self._load_midi_file(filepath)
                event.acceptProposedAction()
                break
            elif ext in self.IMAGE_EXTS:
                self._set_bg_image(filepath)
                event.acceptProposedAction()
                break
            elif ext in self.AUDIO_EXTS:
                self._set_ext_audio(filepath)
                event.acceptProposedAction()
                break

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "MIDIファイルを選択", "", "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        if path:
            self._load_midi_file(path)

    def _show_recent_files_menu(self):
        """最近開いたMIDIファイル履歴ポップアップメニュー"""
        menu = QMenu(self)
        recents = settings_manager.get_recent_files()
        if not recents:
            act = menu.addAction("（履歴はありません）")
            act.setEnabled(False)
        else:
            for path in recents:
                act = menu.addAction(f"📄 {os.path.basename(path)}")
                act.setToolTip(path)
                act.triggered.connect(lambda checked, p=path: self._load_midi_file(p))
            menu.addSeparator()
            act_clear = menu.addAction("🗑 履歴をクリア")
            def _clear():
                self.user_settings["recent_files"] = []
                settings_manager.save_settings(self.user_settings)
            act_clear.triggered.connect(_clear)
        menu.exec(self.btn_recent_menu.mapToGlobal(QPoint(0, self.btn_recent_menu.height())))

    def _save_current_song_profile(self):
        """現在開いている曲の設定を曲別プロファイル(JSON)へ保存"""
        if getattr(self, "_is_loading_midi", False):
            return
        if hasattr(self, "timeline") and self.timeline and self.timeline.filepath:
            extra = {
                "main_track_indices": getattr(self.timeline, "main_track_indices", [self.timeline.main_track_idx]),
                "accomp_track_indices": getattr(self.timeline, "accomp_track_indices", []),
                "monophonic_mode": getattr(self.timeline, "monophonic_mode", "すべて有効"),
                "hide_muted_notes": getattr(self.gl_widget, "hide_muted_notes", False),
                "transpose": self.spin_transpose.value(),
                "transpose_accomp": self.chk_transpose_accomp.isChecked(),
                "inst_type": self.inst_combo.currentText(),
                "ext_audio_path": self.ext_audio_path if (self.ext_audio_path and os.path.isfile(self.ext_audio_path)) else "",
                "ext_offset_ms": self.spin_ext_offset.value(),
                "loop_a": self.spin_loop_a.value(),
                "loop_b": self.spin_loop_b.value(),
            }
            harmonica_map.save_song_profile(self.timeline.filepath, extra)

    def _check_out_of_range_and_notify(self):
        """音域外ノーツの存在を検出してステータスバー等に通知 (A案スリム化＋詳細ツールチップ)"""
        if hasattr(self, "timeline") and self.timeline:
            cur_inst = self.inst_combo.currentText() if hasattr(self, "inst_combo") else None
            diag = self.timeline.diagnose_pitch_range(inst_type=cur_inst)
            status = diag.get("status")
            if status in ("out_of_range", "exceeds_instrument"):
                out_cnt = diag.get("out_count", 0)
                rec = diag.get("recommendation_text", "")
                r_min = diag.get("song_cur_min_name", "")
                r_max = diag.get("song_cur_max_name", "")
                rng_str = f"{r_min}〜{r_max}" if r_min and r_max else ""

                if status == "exceeds_instrument":
                    sub = "モデル音域超過"
                else:
                    targets = diag.get("target_transposes", [])
                    if targets:
                        best_t = targets[0]
                        sign_t = f"+{best_t}" if best_t > 0 else str(best_t)
                        sub = f"移調 {sign_t}stで解消可"
                    else:
                        sub = "移調で調整可"

                if rng_str:
                    short_msg = f"⚠ 音域外: {out_cnt}音 ({rng_str} / {sub})"
                else:
                    short_msg = f"⚠ 音域外: {out_cnt}音 ({sub})"

                self.lbl_status_msg.setText(short_msg)
                if rec:
                    self.lbl_status_msg.setToolTip(f"{short_msg}\n\n【詳細診断】\n{rec}")
            elif status == "ok":
                cur_text = self.lbl_status_msg.text()
                if "音域外" in cur_text:
                    self.lbl_status_msg.setText("✅ 全音域クリア (演奏可能)")
                    self.lbl_status_msg.setToolTip("全ノーツが選択中ハーモニカの音域内に収まっています。")

    def _on_check_pitch_range(self):
        """音域チェックボタン押下時の詳細診断ダイアログ表示"""
        if not hasattr(self, "timeline") or not self.timeline or not getattr(self.timeline, "main_notes", None):
            QMessageBox.information(self, "音域チェック", "MIDIファイルが読み込まれていません。")
            return

        cur_inst = self.inst_combo.currentText()
        diag = self.timeline.diagnose_pitch_range(inst_type=cur_inst)
        status = diag.get("status")

        if status == "empty":
            QMessageBox.information(self, "音域チェック", "有効な主旋律ノーツが見つかりませんでした。")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("🔍 ハーモニカ音域診断")

        info_lines = [
            "<b>【現在の設定】</b>",
            f"・モデル: <b>{self.inst_combo.currentText()}</b> (対応音域: {diag['inst_min_name']} 〜 {diag['inst_max_name']})",
            f"・曲の主旋律音域: <b>{diag['song_cur_min_name']} 〜 {diag['song_cur_max_name']}</b> (現在移調: {diag['current_transpose']:+d}st)",
        ]

        if status == "ok":
            msg.setIcon(QMessageBox.Icon.Information)
            info_lines.append("")
            info_lines.append("🎉 <b>判定: 全音域クリア</b>")
            info_lines.append("すべてのノーツが選択中ハーモニカの音域内に収まっており、無理なく演奏可能です！")
            msg.setText("<br>".join(info_lines))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            self.lbl_status_msg.setText("✅ 全音域クリア: 全ノーツ演奏可能です")
            return

        if status == "exceeds_instrument":
            msg.setIcon(QMessageBox.Icon.Warning)
            info_lines.append("")
            info_lines.append(f"⚠ <b>判定: 音域外ノーツ {diag['out_count']} 音 (高低差超過)</b>")
            info_lines.append(diag["recommendation_text"])
            msg.setText("<br>".join(info_lines))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            r_min = diag.get("song_cur_min_name", "")
            r_max = diag.get("song_cur_max_name", "")
            rng_str = f" ({r_min}〜{r_max} / モデル音域超過)" if r_min and r_max else " (モデル音域超過)"
            self.lbl_status_msg.setText(f"⚠ 音域外: {diag['out_count']}音{rng_str}")
            return

        # out_of_range (移調で解決可能)
        msg.setIcon(QMessageBox.Icon.Warning)
        info_lines.append("")
        info_lines.append(f"⚠ <b>判定: 音域外ノーツ {diag['out_count']} 音</b> (低音側: {diag['under_count']}音 / 高音側: {diag['over_count']}音)")
        info_lines.append("")
        info_lines.append(f"<b>{diag['recommendation_text']}</b>")
        msg.setText("<br>".join(info_lines))

        # 推奨ボタンの配置 (最大2件)
        target_transposes = diag.get("target_transposes", [])
        shifts = diag.get("recommended_shifts", [])
        buttons = []
        for i, target_t in enumerate(target_transposes[:2]):
            s = shifts[i]
            label = f"移調を {target_t:+d}st に設定 ({s:+d}半音)"
            btn = msg.addButton(label, QMessageBox.ButtonRole.ActionRole)
            buttons.append((btn, target_t))

        msg.addButton("閉じる", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        for btn, target_t in buttons:
            if clicked == btn:
                self.spin_transpose.setValue(target_t)
                self.lbl_status_msg.setText(f"🎯 移調を {target_t:+d}st に設定しました (全音域クリア)")
                break

    def _load_midi_file(self, filepath: str):
        try:
            if self.is_recording:
                self._on_record_toggle()
            self._is_loading_midi = True
            settings_manager.add_recent_file(filepath)
            prof = harmonica_map.load_song_profile(filepath)

            # 楽器復元 (プロファイル指定または現在のUI値)
            inst = prof.get("inst_type", self.inst_combo.currentText())
            self.inst_combo.blockSignals(True)
            self.inst_combo.setCurrentText(inst)
            self.inst_combo.blockSignals(False)

            self.timeline.load_file(filepath, inst_type=inst)

            # パート選択の復元
            if "main_track_indices" in prof and prof["main_track_indices"]:
                all_t_indices = {info["track_idx"] for info in getattr(self.timeline, "tracks_info", [])}
                valid_mains = [int(i) for i in prof["main_track_indices"] if int(i) in all_t_indices]
                if not valid_mains:
                    valid_mains = [self.timeline.main_track_idx]
                valid_accomps = [int(i) for i in prof.get("accomp_track_indices", []) if int(i) in all_t_indices] if "accomp_track_indices" in prof else None
                self.timeline.set_main_tracks(valid_mains, valid_accomps)
                self.audio_engine.set_main_tracks(valid_mains, valid_accomps)

            # 移調復元（プロファイル未設定なら 0 / True にリセット）
            trans_val = int(prof.get("transpose", 0))
            trans_acc = bool(prof.get("transpose_accomp", True))
            self.spin_transpose.blockSignals(True)
            self.spin_transpose.setValue(trans_val)
            self.spin_transpose.blockSignals(False)
            self.chk_transpose_accomp.blockSignals(True)
            self.chk_transpose_accomp.setChecked(trans_acc)
            self.chk_transpose_accomp.blockSignals(False)

            # 運指プリセットの復元
            if "preset" in prof and hasattr(self, "combo_fing_preset"):
                self.combo_fing_preset.blockSignals(True)
                self.combo_fing_preset.setCurrentText(harmonica_map.normalize_fingering_preset(prof["preset"]))
                self.combo_fing_preset.blockSignals(False)

            # 単音化 & 除外ノーツ非表示復元（未設定ならデフォルトにリセット）
            mono_mode = prof.get("monophonic_mode", "すべて有効")
            hide_muted = bool(prof.get("hide_muted_notes", False))
            harmonica_map.CURRENT_MONOPHONIC_MODE = mono_mode
            if hasattr(self, "combo_monophonic_mode"):
                self.combo_monophonic_mode.blockSignals(True)
                self.combo_monophonic_mode.setCurrentText(mono_mode)
                self.combo_monophonic_mode.blockSignals(False)
            self.timeline.set_monophonic_mode(mono_mode)

            if hasattr(self, "chk_hide_muted_notes"):
                self.chk_hide_muted_notes.blockSignals(True)
                self.chk_hide_muted_notes.setChecked(hide_muted)
                self.chk_hide_muted_notes.blockSignals(False)
            self.gl_widget.set_hide_muted_notes(hide_muted)

            # 移調を反映
            self.timeline.set_transpose(trans_val, trans_acc)

            self.gl_widget.set_timeline_data(self.timeline)
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.set_transpose(trans_val, trans_acc)

            try:
                cleaned = self.combo_count_in.currentText().replace("小節", "").strip().split()[0]
                ci_m = int(cleaned)
            except Exception:
                ci_m = 0
            self.audio_engine.set_count_in(ci_m)

            self.clock.set_total_duration(self.timeline.total_duration_sec)
            self.clock.set_anchor(0.0, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_STOPPED)
            self.clock.clear_active_notes()
            self.audio_engine.all_notes_off()
            self.audio_engine.seek(0.0)

            self.lbl_song_title.setMinimumWidth(140)
            self.lbl_song_title.setMaximumWidth(16777215)
            self.lbl_song_title.setText(self.timeline.filename)
            self.lbl_song_title.setToolTip(filepath)
            self._update_track_list()
            self._update_song_info_labels()
            self._reset_loop_ranges_to_song()

            # ループ範囲復元
            total_m = len(self.timeline.measures_timeline)
            if "loop_a" in prof:
                self.spin_loop_a.setValue(max(1, min(total_m, int(prof["loop_a"]))))
            if "loop_b" in prof:
                self.spin_loop_b.setValue(max(1, min(total_m, int(prof["loop_b"]))))

            start_sec = self.timeline.get_sec_for_measure(self.spin_loop_a.value()) if self.loop_playback else 0.0
            if start_sec > 0.0:
                self.clock.set_anchor(start_sec, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_STOPPED)
                self.audio_engine.seek(start_sec)
                self._update_time_label(start_sec)

            # 外部音源復元
            ext_path = prof.get("ext_audio_path", "")
            if ext_path and os.path.isfile(ext_path):
                self._set_ext_audio(ext_path)
            else:
                self._on_clear_ext_audio()

            if "ext_offset_ms" in prof:
                self.spin_ext_offset.setValue(int(prof["ext_offset_ms"]))

            if hasattr(self, "spin_exp_end"):
                self.spin_exp_end.setValue(round(self.timeline.total_duration_sec, 2))

            self.btn_play.setText("▶ 再生")
            self._sync_ext_audio_playback(False, 0.0)
            self._update_transpose_lock_state()
            self.lbl_status_msg.setText(f"📂 読込完了: {self.timeline.filename}")
            self._check_out_of_range_and_notify()
        except Exception as e:
            print(f"[Error] Failed to load MIDI: {e}")
            self.lbl_status_msg.setText(f"❌ 読込エラー: {e}")
        finally:
            self._is_loading_midi = False

    def _update_track_list(self):
        pass

    def _on_open_part_dialog(self):
        m_indices = getattr(self.timeline, "main_track_indices", [self.timeline.main_track_idx])
        a_indices = getattr(self.timeline, "accomp_track_indices", [])
        dlg = PartSelectDialog(
            self.timeline.tracks_info,
            self.timeline.main_track_idx,
            self,
            current_main_indices=m_indices,
            current_accomp_indices=a_indices
        )
        if dlg.exec():
            sel_mains = dlg.get_selected_track_indices()
            sel_accomps = dlg.get_selected_accomp_indices()
            self.timeline.set_main_tracks(sel_mains, sel_accomps)
            self.gl_widget.set_timeline_data(self.timeline)
            self.audio_engine.set_main_tracks(sel_mains, sel_accomps)
            self.audio_engine.load_timeline(self.timeline)
            cur_sec = self.clock.get_current_base_sec()
            self.audio_engine.seek(cur_sec)
            self._update_song_info_labels()
            self._save_current_song_profile()
            names = [f"Track {i+1}" for i in sel_mains]
            self.lbl_status_msg.setText(f"🎵 主旋律: {', '.join(names)} (複合 {len(sel_mains)} パート)")
            self._check_out_of_range_and_notify()

    def _on_monophonic_mode_changed(self, mode: str):
        import harmonica_map
        harmonica_map.CURRENT_MONOPHONIC_MODE = mode
        self.timeline.set_monophonic_mode(mode)
        self.gl_widget.set_timeline_data(self.timeline)
        self.audio_engine.load_timeline(self.timeline)
        self._save_current_song_profile()
        self.lbl_status_msg.setText(f"重なり音整理: {mode}")
        self._check_out_of_range_and_notify()

    def _on_hide_muted_notes_toggled(self, checked: bool):
        self.gl_widget.set_hide_muted_notes(checked)
        self._save_current_song_profile()
        self.lbl_status_msg.setText(f"除外ノーツ表示: {'非表示' if checked else 'グレーアウト表示 (編集可)'}")

    def _on_set_ab_range_to_export(self):
        a_sec = self.timeline.get_sec_for_measure(self.spin_loop_a.value()) if self.timeline else 0.0
        b_sec = self.timeline.get_measure_end_sec(self.spin_loop_b.value()) if self.timeline else getattr(self.timeline, "total_duration_sec", 60.0)
        if b_sec <= a_sec or b_sec > getattr(self.timeline, "total_duration_sec", 9999.0):
            b_sec = getattr(self.timeline, "total_duration_sec", 60.0)
        self.spin_exp_start.setValue(round(a_sec, 2))
        self.spin_exp_end.setValue(round(b_sec, 2))
        self.lbl_status_msg.setText(f"🔁 A-Bループ範囲 ({a_sec:.1f}s 〜 {b_sec:.1f}s) を出力範囲にセットしました")

    def _on_reset_export_range(self):
        """動画書き出し範囲を曲全体 (0.0s〜総尺) にリセット"""
        total = self.timeline.total_duration_sec if self.timeline else 60.0
        self.spin_exp_start.setValue(0.0)
        self.spin_exp_end.setValue(round(max(0.1, total), 2))
        self.lbl_status_msg.setText("↺ 動画出力範囲を全曲にリセットしました")

    # --- 音響制御 ---
    def _on_part_mode_changed(self, mode: str):
        self.audio_engine.set_part_mode(mode)
        self._save_current_settings()

    def _on_vol_changed(self, val: int):
        self.lbl_vol_val.setText(f"{val}%")
        self.audio_engine.set_volume(val / 100.0)
        self._save_current_settings()

    def closeEvent(self, event):
        if hasattr(self, "audio_engine"):
            self.audio_engine.close()
        self._save_current_settings()
        super().closeEvent(event)

    # =========================================================================
    # 再生トランスポート制御
    # =========================================================================
    def _on_play_toggle(self):
        st = self.clock.get_state()
        if st == SharedClockBridge.STATE_PLAYING:
            cur_sec = self.clock.get_current_base_sec()
            self.clock.set_anchor(cur_sec, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_PAUSED)
            self.btn_play.setText("▶ 再生")
            if hasattr(self, "btn_ext_audition"):
                self.btn_ext_audition.setText("▶ 試聴")
            self._sync_ext_audio_playback(False)
        else:
            cur_sec = self.clock.get_current_base_sec()
            if st == SharedClockBridge.STATE_STOPPED:
                if hasattr(self, "chk_stepup") and self.chk_stepup.isChecked():
                    if not getattr(self, "_stepup_running", False):
                        self._is_stepup_auto_adjusting = True
                        try:
                            self.speed_slider.setValue(self.spin_sp_start.value())
                        finally:
                            self._is_stepup_auto_adjusting = False
                        self._stepup_running = True
                if 0.0 <= cur_sec <= 0.05:
                    ci_dur = self._get_count_in_duration()
                    cur_sec = -ci_dur if ci_dur > 0 else 0.0
            elif 0.0 <= cur_sec <= 0.05 or cur_sec >= self.timeline.total_duration_sec:
                ci_dur = self._get_count_in_duration()
                cur_sec = -ci_dur if ci_dur > 0 else 0.0

            self.clock.set_anchor(cur_sec, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_PLAYING)
            self.audio_engine.seek(cur_sec)
            self.btn_play.setText("⏸ 一時停止")
            if hasattr(self, "btn_ext_audition"):
                self.btn_ext_audition.setText("⏸ 一時停止")
            if cur_sec >= 0.0:
                self._sync_ext_audio_playback(True, cur_sec)

    def _on_stop(self):
        start_sec = self.timeline.get_sec_for_measure(self.spin_loop_a.value()) if self.loop_playback else 0.0
        self.clock.set_anchor(start_sec, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_STOPPED)
        self.clock.clear_active_notes()
        self.audio_engine.all_notes_off()
        self.audio_engine.seek(start_sec)
        self.btn_play.setText("▶ 再生")
        if hasattr(self, "btn_ext_audition"):
            self.btn_ext_audition.setText("▶ 試聴")
        self._sync_ext_audio_playback(False, start_sec)
        if self.is_recording:
            self._on_record_toggle()
        self._update_time_label(start_sec)

    def _on_rewind(self):
        start_sec = self.timeline.get_sec_for_measure(self.spin_loop_a.value()) if self.loop_playback else 0.0
        st = self.clock.get_state()
        self.clock.set_anchor(start_sec, speed_ratio=self.speed_slider.value() / 100.0, state=st)
        self.audio_engine.seek(start_sec)
        self._sync_ext_audio_playback(st == SharedClockBridge.STATE_PLAYING, start_sec)
        self._update_time_label(start_sec)

    def _seek_relative(self, offset_sec: float):
        cur_sec = self.clock.get_current_base_sec()
        target = max(0.0, min(self.timeline.total_duration_sec, cur_sec + offset_sec))
        st = self.clock.get_state()
        self.clock.set_anchor(target, speed_ratio=self.speed_slider.value() / 100.0, state=st)
        self.audio_engine.seek(target)
        self._sync_ext_audio_playback(st == SharedClockBridge.STATE_PLAYING, target)

    def _on_seek_pressed(self):
        self.is_seeking = True

    def _on_seek_moved(self, val: int):
        total = self.timeline.total_duration_sec
        if total > 0:
            target_sec = (val / 1000.0) * total
            self._update_time_label(target_sec)

    def _on_seek_released(self):
        self.is_seeking = False
        total = self.timeline.total_duration_sec
        if total > 0:
            target_sec = (self.seek_slider.value() / 1000.0) * total
            st = self.clock.get_state()
            self.clock.set_anchor(target_sec, speed_ratio=self.speed_slider.value() / 100.0, state=st)
            self.audio_engine.seek(target_sec)
            self._sync_ext_audio_playback(st == SharedClockBridge.STATE_PLAYING, target_sec)

    def _on_loop_toggled(self, checked: bool):
        self.loop_playback = bool(checked)
        self._update_loop_range()
        self._save_current_settings()

    # --- 速度制御 ---
    def _on_speed_changed(self, val: int):
        spd = val / 100.0
        self.lbl_speed_val.setText(f"{val}%")
        self.clock.set_speed_ratio(spd)
        if hasattr(self, "chk_stepup") and self.chk_stepup.isChecked():
            if not getattr(self, "_is_stepup_auto_adjusting", False):
                self._stepup_running = False
                self.chk_stepup.blockSignals(True)
                self.chk_stepup.setChecked(False)
                self.chk_stepup.blockSignals(False)
                self.user_settings["stepup_enabled"] = False
                self.lbl_status_msg.setText(f"⏩ 速度: {val}% (ステップアップ練習を解除しました)")
        self._save_current_settings()

    def _adjust_speed(self, delta: int):
        new_val = max(10, min(300, self.speed_slider.value() + delta))
        self.speed_slider.setValue(new_val)

    def _on_fall_speed_changed(self, val: int):
        ratio = val / 100.0
        self.lbl_fall_val.setText(f"{val}%")
        self.gl_widget.set_note_speed_ratio(ratio)
        self._save_current_settings()

    # --- 表示モード切替 ---
    def _on_inst_changed(self, inst_type: str):
        self.timeline.rebind_fingerings(inst_type)
        self.gl_widget.set_timeline_data(self.timeline)
        self._save_current_song_profile()
        self._check_out_of_range_and_notify()
        self._save_current_settings()

    def _on_traj_changed(self, mode: str):
        self.gl_widget.set_trajectory_mode(mode)
        self._save_current_settings()

    def _on_lang_changed(self, lang: str):
        self.gl_widget.set_lang_mode(lang)
        self._save_current_settings()

    def _on_ratio_changed(self, ratio: str):
        self.gl_widget.set_aspect_ratio(ratio)
        self._save_current_settings()

    def _on_hole_num_style_changed(self, style: str):
        self.user_settings["hole_num_style"] = str(style)
        self.gl_widget.set_hole_num_style(str(style))
        self._save_current_settings()

    # =========================================================================
    # 定周期UI更新 (30Hz)
    # =========================================================================
    def _on_ui_tick(self):
        cur_sec = self.clock.get_current_base_sec()
        total_sec = self.timeline.total_duration_sec
        state = self.clock.get_state()

        # 前奏カウントダウンから本編への遷移検知、および外部音源の待機発音同期
        prev_s = getattr(self, "_prev_sec", 0.0)
        offset_sec = float(self.spin_ext_offset.value()) / 1000.0 if hasattr(self, "spin_ext_offset") else 0.0
        if state == SharedClockBridge.STATE_PLAYING:
            if getattr(self, "_ext_pending_start", False) and (cur_sec - offset_sec >= 0.0):
                self._sync_ext_audio_playback(True, cur_sec)
            elif prev_s < 0.0 <= cur_sec:
                self._sync_ext_audio_playback(True, 0.0)
            waiting_a = getattr(self, "_loop_waiting_for_a_sec", None)
            if waiting_a is not None and prev_s < waiting_a <= cur_sec:
                self._loop_waiting_for_a_sec = None
                self._sync_ext_audio_playback(True, waiting_a)
        self._prev_sec = cur_sec

        # シークバーと現在時刻の更新
        if not self.is_seeking:
            if total_sec > 0:
                pos = int(min(1000, (cur_sec / total_sec) * 1000))
                self.seek_slider.blockSignals(True)
                self.seek_slider.setValue(pos)
                self.seek_slider.blockSignals(False)
            self._update_time_label(cur_sec)

        # LCD 情報モニタの更新 (O(log M) 高速二分探索)
        if cur_sec < 0.0:
            bpm = getattr(self.timeline, "default_bpm", 120.0)
            den = getattr(self.timeline, "time_sig_den", 4)
            beat_dur = (60.0 / bpm) * (4.0 / den) if bpm > 0 else 0.5
            countdown_beat = int(abs(cur_sec) / beat_dur) + 1
            self.lbl_lcd_pos.setText(f"前奏: 残り {abs(cur_sec):0.1f}s")
            self.lbl_lcd_sig.setText("拍子: 前奏カウント")
            self.lbl_lcd_bpm.setText(f"テンポ: {int(bpm)}BPM({self.speed_slider.value()}%)")
            self.lbl_lcd_status.setText("前奏カウント")
            self.lbl_lcd_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        else:
            m_num, b_num, num, den, bpm = self.timeline.get_measure_and_beat(cur_sec)
            self.lbl_lcd_pos.setText(f"位置: {m_num:03d}小節 . {b_num:02d}拍")
            self.lbl_lcd_sig.setText(f"拍子: {num}/{den}")
            eff_bpm = bpm * (self.speed_slider.value() / 100.0)
            self.lbl_lcd_bpm.setText(f"テンポ: {int(round(eff_bpm)):03d}BPM({self.speed_slider.value()}%)")

            if state == SharedClockBridge.STATE_PLAYING:
                self.lbl_lcd_status.setText("再生中")
                self.lbl_lcd_status.setStyleSheet("color: #34D399; font-weight: bold;")
            elif state == SharedClockBridge.STATE_PAUSED:
                self.lbl_lcd_status.setText("一時停止")
                self.lbl_lcd_status.setStyleSheet("color: #FBBF24; font-weight: bold;")
            else:
                self.lbl_lcd_status.setText("停止中")
                self.lbl_lcd_status.setStyleSheet("color: #94A3B8; font-weight: bold;")

        # 録音中ステータス更新
        if self.is_recording:
            el = self.audio_recorder.get_elapsed_sec()
            self.lbl_rec_status.setText(f"🔴 録音中... [{int(el // 60):02d}:{int(el % 60):02d}]")
            self.btn_rec.setText(f"⏹ {int(el)}s")

        # 試聴ボタンの停止同期
        if hasattr(self, "audition_player") and hasattr(self, "btn_rec_listen"):
            if not self.audition_player.is_playing() and self.btn_rec_listen.text() == "⏹ 停止":
                self.btn_rec_listen.setText("▶ 試聴")

        # リアルタイムFPSバッジ更新
        fps = getattr(self.gl_widget, "get_fps", lambda: 0.0)()
        if fps > 0:
            self.lbl_fps.setText(f"● GPU {fps:.1f} FPS")

    def _update_time_label(self, sec: float):
        if sec < 0:
            m = int(abs(sec) // 60)
            s = abs(sec) % 60
            self.lbl_time_cur.setText(f"-{m:02d}:{s:04.1f}")
        else:
            m = int(sec // 60)
            s = sec % 60
            self.lbl_time_cur.setText(f"{m:02d}:{s:04.1f}")

    def _update_song_info_labels(self):
        total = self.timeline.total_duration_sec
        m = int(total // 60)
        s = total % 60
        self.lbl_time_total.setText(f"{m:02d}:{s:04.1f}")


    # =========================================================================
    # Step 6: 録音・音響・外部音源・リバーブ ハンドラ
    # =========================================================================
    def _refresh_audio_devices(self):
        """マイクデバイス一覧を再取得"""
        devs = AudioRecorder.get_input_devices()
        cur = self.combo_rec_dev.currentText() if hasattr(self, "combo_rec_dev") else ""
        self.combo_rec_dev.blockSignals(True)
        self.combo_rec_dev.clear()
        self.combo_rec_dev.addItem("既定の入力マイク (Windows標準)")
        for d in devs:
            self.combo_rec_dev.addItem(d)
        if cur and cur in [self.combo_rec_dev.itemText(i) for i in range(self.combo_rec_dev.count())]:
            self.combo_rec_dev.setCurrentText(cur)
        self.combo_rec_dev.blockSignals(False)

    def _on_record_toggle(self):
        """ワンクリック録音の開始/停止"""
        if not self.is_recording:
            dev_name = self.combo_rec_dev.currentText()
            ch_count = 1 if "モノラル" in self.combo_rec_ch.currentText() else 2

            rec_dir = get_portable_path("recordings")
            os.makedirs(rec_dir, exist_ok=True)
            song_base = os.path.splitext(self.timeline.filename)[0] if self.timeline.filename else "take"

            idx = 1
            while True:
                out_path = os.path.join(rec_dir, f"{song_base}_take_{idx:03d}.wav")
                if not os.path.exists(out_path):
                    break
                idx += 1

            self._cur_rec_output_path = out_path
            ok = self.audio_recorder.start_recording(device_name=dev_name, sample_rate=44100, channels=ch_count)
            if ok:
                self.is_recording = True
                self.btn_rec.setText("⏹ 停止")
                self.btn_rec.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; border-radius: 4px;")
                self.lbl_rec_status.setText("🔴 録音中... [00:00]")
                self.lbl_rec_status.setStyleSheet("color: #F87171; font-weight: bold;")
                self.lbl_status_msg.setText(f"🔴 演奏録音を開始しました: {os.path.basename(out_path)}")

                # MIDI再生が停止中なら同時に再生開始
                if self.clock.get_state() != SharedClockBridge.STATE_PLAYING:
                    self._on_play_toggle()

                # 録音開始時点のクロック秒数を記録 (前奏カウントイン自動カット用)
                self._rec_start_sec = self.clock.get_current_base_sec()
            else:
                QMessageBox.warning(self, "録音エラー", "マイク録音デバイスの初期化に失敗しました。\nマイクが接続されているか確認してください。")
        else:
            trim_sec = 0.0
            start_sec = getattr(self, "_rec_start_sec", 0.0)
            if start_sec < 0.0:
                trim_sec = abs(start_sec)

            saved_path, dur = self.audio_recorder.stop_recording(
                getattr(self, "_cur_rec_output_path", "recordings/take.wav"),
                trim_start_sec=trim_sec
            )
            self.is_recording = False
            self.btn_rec.setText("🔴 録音")
            self.btn_rec.setStyleSheet("")
            self.lbl_rec_status.setText("● 待機中 (上部 [🔴録音] で開始)")
            self.lbl_rec_status.setStyleSheet("color: #94A3B8; font-weight: bold;")

            if saved_path and dur > 0:
                self.last_recorded_path = saved_path
                trim_info = f" (前奏{trim_sec:.1f}秒自動カット済)" if trim_sec > 0.0 else ""
                self._set_elided_label_text(self.lbl_rec_take, f"録音テイク: {os.path.basename(saved_path)} ({dur:.1f}秒)", saved_path, max_width=300)
                self.lbl_rec_take.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
                self.btn_rec_listen.setEnabled(True)

                if self.chk_reverb.isChecked():
                    rev_type = self.combo_reverb_type.currentText()
                    wet = self.slider_reverb_wet.value()
                    rev_path = os.path.splitext(saved_path)[0] + "_reverb.wav"
                    apply_harmonica_reverb_numpy(saved_path, rev_path, rev_type, wet)
                    self.lbl_status_msg.setText(f"💾 録音完了＆リバーブ生成: {os.path.basename(saved_path)} ({dur:.1f}秒{trim_info})")
                else:
                    self.lbl_status_msg.setText(f"💾 録音完了: {os.path.basename(saved_path)} ({dur:.1f}秒{trim_info})")
            else:
                self.lbl_status_msg.setText("⚠️ 録音データが空のため破棄されました")

    def _on_rec_listen_toggle(self):
        """録音テイクの試聴再生/停止"""
        if self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("⏹ 試聴を停止しました")
        else:
            if not getattr(self, "last_recorded_path", None) or not os.path.exists(self.last_recorded_path):
                return
            target_path = self.last_recorded_path
            if self.chk_reverb.isChecked():
                rev_path = os.path.splitext(self.last_recorded_path)[0] + "_reverb.wav"
                apply_harmonica_reverb_numpy(self.last_recorded_path, rev_path, self.combo_reverb_type.currentText(), self.slider_reverb_wet.value())
                if os.path.exists(rev_path):
                    target_path = rev_path

            ok = self.audition_player.play(target_path, volume=self.vol_slider.value() / 100.0)
            if ok:
                self.btn_rec_listen.setText("⏹ 停止")
                self.lbl_status_msg.setText(f"▶ 試聴中: {os.path.basename(target_path)}")

    def _refresh_live_audition_reverb(self):
        """試聴停止し設定反映"""
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")

    def _on_select_rec_take(self):
        """過去に録音したテイクや任意の録音WAVファイルを選択して採用"""
        rec_dir = get_portable_path("recordings")
        os.makedirs(rec_dir, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "採用する録音テイク (WAV) を選択",
            rec_dir,
            "WAV Audio (*.wav);;Audio Files (*.wav *.mp3 *.flac *.m4a)"
        )
        if not file_path:
            return

        file_path = os.path.normpath(file_path).replace("\\", "/")
        self.last_recorded_path = file_path
        take_name = os.path.basename(file_path)
        self._set_elided_label_text(self.lbl_rec_take, f"採用テイク: {take_name}", file_path, max_width=310)
        self.lbl_rec_take.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        self.btn_rec_listen.setEnabled(True)
        if hasattr(self, "_update_mixer_summary_label"):
            self._update_mixer_summary_label()
        self.lbl_status_msg.setText(f"📂 録音テイクを採用しました: {take_name}")

    def _on_open_rec_folder(self):
        """録音フォルダを開く"""
        rec_dir = get_portable_path("recordings")
        os.makedirs(rec_dir, exist_ok=True)
        import subprocess
        subprocess.Popen(f'explorer "{rec_dir}"')

    def _on_reverb_toggled(self, checked: bool):
        self.reverb_enabled = bool(checked)
        self.user_settings["reverb_enabled"] = self.reverb_enabled
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("✨ リバーブ有効状態を変更しました ([▶ 試聴] で確認)")
        else:
            self.lbl_status_msg.setText(f"✨ リバーブ: {'有効' if checked else '無効'} ([▶ 試聴] で確認)")
        self._save_current_settings()

    def _on_reverb_type_changed(self, r_type: str):
        self.reverb_type = str(r_type)
        self.user_settings["reverb_type"] = self.reverb_type
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("✨ リバーブ空間タイプを変更しました ([▶ 試聴] で確認)")
        else:
            self.lbl_status_msg.setText(f"✨ リバーブタイプ: {r_type} ([▶ 試聴] で確認)")
        self._save_current_settings()

    def _on_reverb_slider_changed(self, val: int):
        self.reverb_wet_pct = int(val)
        self.lbl_reverb_wet.setText(f"深さ: {val}%")
        self.user_settings["reverb_wet_pct"] = self.reverb_wet_pct
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("✨ リバーブ深さを変更しました ([▶ 試聴] で確認)")
        self._save_current_settings()

    def _on_select_ext_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "伴奏・外部音源を選択", "",
            "オーディオファイル (*.mp3 *.wav *.m4a *.ogg *.flac *.aac);;全ファイル (*)"
        )
        if path:
            self._set_ext_audio(path)

    def _ensure_ext_pcm_loaded(self):
        """外部音源のPCMデータをメモリにキャッシュロード"""
        if getattr(self, "_ext_pcm", None) is not None:
            return self._ext_pcm
        if getattr(self, "ext_audio_path", "") and os.path.isfile(self.ext_audio_path):
            try:
                from audio_engine import load_external_audio_pcm
                self._ext_pcm = load_external_audio_pcm(self.ext_audio_path, sample_rate=44100)
                return self._ext_pcm
            except Exception as e:
                print(f"[ExtAudio Load Error] {e}")
                self._ext_pcm = None
        return None

    def _stop_ext_playback(self):
        """外部音源の再生を安全に停止"""
        try:
            if hasattr(self, "_ext_channel") and self._ext_channel is not None:
                self._ext_channel.stop()
            self._ext_pending_start = False
        except Exception:
            pass

    def _set_ext_audio(self, path: str):
        if not path or not os.path.isfile(path):
            return
        self.ext_audio_path = path
        self.user_settings["ext_audio_path"] = path
        self._ext_pcm = None
        self._ensure_ext_pcm_loaded()

        base_name = os.path.basename(path)
        self._set_elided_label_text(self.lbl_ext_audio, base_name, path, max_width=290)
        self.lbl_ext_audio.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px; background-color: #121218; border: 1px solid #22222E; border-radius: 3px; padding: 2px 6px;")
        if hasattr(self, "lbl_prac_ext_status"):
            self.lbl_prac_ext_status.setText(f"伴奏音源: {base_name}")
            self.lbl_prac_ext_status.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        self.btn_ext_audition.setEnabled(True)
        self.btn_ext_restart.setEnabled(True)
        self.btn_ext_stop.setEnabled(True)
        self._save_current_song_profile()
        self.lbl_status_msg.setText(f"🎵 伴奏音源を設定しました: {base_name}")
        self._save_current_settings()

    def _on_clear_ext_audio(self):
        self.ext_audio_path = ""
        self.user_settings["ext_audio_path"] = ""
        self._ext_pcm = None
        self._stop_ext_playback()
        self.lbl_ext_audio.setText("未選択 (MP3/WAV等をD&D可)")
        self.lbl_ext_audio.setToolTip("")
        self.lbl_ext_audio.setStyleSheet("color: #64748B; font-size: 11px; background-color: #121218; border: 1px solid #22222E; border-radius: 3px; padding: 2px 6px;")
        if hasattr(self, "lbl_prac_ext_status"):
            self.lbl_prac_ext_status.setText("伴奏音源: 未設定 (MIDIガイド再生)")
            self.lbl_prac_ext_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.btn_ext_audition.setEnabled(False)
        self.btn_ext_restart.setEnabled(False)
        self.btn_ext_stop.setEnabled(False)
        self._save_current_song_profile()
        self.lbl_status_msg.setText("伴奏音源を解除しました")
        self._save_current_settings()

    def _on_ext_mode_changed(self, mode: str):
        self.ext_audio_mode = str(mode)
        self.user_settings["ext_audio_mode"] = self.ext_audio_mode

        for combo_name in ("combo_ext_mode", "combo_prac_audio_mode"):
            combo = getattr(self, combo_name, None)
            if combo is not None and combo.currentText() != mode:
                combo.blockSignals(True)
                combo.setCurrentText(mode)
                combo.blockSignals(False)

        is_mute = ("ガイド音のみ" in mode or "伴奏ミュート" in mode or "外部音源オフ" in mode)
        if is_mute:
            self._stop_ext_playback()
        elif self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
            cur_sec = self.clock.get_current_base_sec()
            self._sync_ext_audio_playback(True, cur_sec)

        if "伴奏のみ" in mode or "外部音源のみ" in mode:
            self.audio_engine.set_midi_notes_muted(True)
        else:
            self.audio_engine.set_midi_notes_muted(False)
        self._save_current_settings()

    def _on_ext_vol_changed(self, val: int):
        self.ext_volume = int(val)
        self.lbl_ext_vol.setText(f"{val}%")
        self.user_settings["ext_audio_volume"] = val
        try:
            v = max(0.0, min(1.0, (val / 100.0) * (self.vol_slider.value() / 100.0)))
            if hasattr(self, "_ext_channel") and self._ext_channel is not None:
                self._ext_channel.set_volume(v)
        except Exception:
            pass
        self._save_current_settings()

    def _get_current_mixer_settings(self) -> dict:
        """現在のミキサー設定ディクショナリを取得 (常に最新のUI状態を同期反映)"""
        ext_path = getattr(self, "ext_audio_path", "")
        rec_path = getattr(self, "last_recorded_path", "")
        has_ext = bool(ext_path and os.path.isfile(ext_path))
        has_rec = bool(rec_path and os.path.isfile(rec_path))

        if not hasattr(self, "_mixer_settings") or not isinstance(self._mixer_settings, dict):
            self._mixer_settings = {
                "track_ext_enabled": has_ext,
                "track_ext_path": ext_path,
                "track_ext_vol": int(self.slider_ext_vol.value()) if hasattr(self, "slider_ext_vol") else 100,
                "track_ext_offset_ms": int(self.spin_ext_offset.value()) if hasattr(self, "spin_ext_offset") else 0,

                "track_rec_enabled": has_rec,
                "track_rec_path": rec_path,
                "track_rec_vol": 100,
                "track_rec_reverb": bool(self.chk_reverb.isChecked()) if hasattr(self, "chk_reverb") else False,
                "track_rec_offset_ms": int(self.spin_rec_offset.value()) if hasattr(self, "spin_rec_offset") else 0,

                "track_midi_enabled": not has_ext and not has_rec,
                "track_midi_mode": "全パート再生",
                "track_midi_vol": int(self.vol_slider.value()) if hasattr(self, "vol_slider") else 100,
            }
        else:
            if ext_path:
                self._mixer_settings["track_ext_path"] = ext_path
            if rec_path:
                self._mixer_settings["track_rec_path"] = rec_path
            if hasattr(self, "spin_ext_offset"):
                self._mixer_settings["track_ext_offset_ms"] = int(self.spin_ext_offset.value())
            if hasattr(self, "spin_rec_offset"):
                self._mixer_settings["track_rec_offset_ms"] = int(self.spin_rec_offset.value())
            if hasattr(self, "chk_reverb"):
                self._mixer_settings["track_rec_reverb"] = bool(self.chk_reverb.isChecked())

        return self._mixer_settings

    def _update_mixer_summary_label(self):
        """動画出力タブのミキサー概要テキストを更新"""
        if not hasattr(self, "lbl_mixer_summary"):
            return
        cfg = self._get_current_mixer_settings()
        parts = []
        if cfg.get("track_ext_enabled", False):
            parts.append(f"伴奏({cfg.get('track_ext_vol', 100)}%)")
        if cfg.get("track_rec_enabled", False):
            rev_str = "・Rev" if cfg.get("track_rec_reverb", False) else ""
            parts.append(f"録音({cfg.get('track_rec_vol', 100)}%{rev_str})")
        if cfg.get("track_midi_enabled", False):
            parts.append(f"MIDI({cfg.get('track_midi_vol', 100)}%)")
        if not parts:
            parts.append("無音")
        self.lbl_mixer_summary.setText("構成: " + " + ".join(parts))

    def _on_quick_audio_source_changed(self, choice: str):
        """クイック指定コンボが切り替えられた際にミキサー設定を追従"""
        cfg = self._get_current_mixer_settings()
        if "無音" in choice:
            cfg["track_ext_enabled"] = False
            cfg["track_rec_enabled"] = False
            cfg["track_midi_enabled"] = False
        elif "マイク録音" in choice:
            cfg["track_ext_enabled"] = False
            cfg["track_rec_enabled"] = True
            cfg["track_midi_enabled"] = False
        elif "伴奏音源" in choice:
            cfg["track_ext_enabled"] = True
            cfg["track_rec_enabled"] = False
            cfg["track_midi_enabled"] = False
        elif "MIDI" in choice:
            cfg["track_ext_enabled"] = False
            cfg["track_rec_enabled"] = False
            cfg["track_midi_enabled"] = True
        self._update_mixer_summary_label()

    def _on_open_audio_mixer_dialog(self):
        """音声トラック・ミキサーダイアログを開く"""
        cfg = self._get_current_mixer_settings()
        dlg = AudioTrackMixerDialog(cfg, timeline=self.timeline, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._mixer_settings = dlg.get_settings()
            self._update_mixer_summary_label()
            self.lbl_status_msg.setText("🎚️ 音声トラック・ミキサー設定を更新しました")
            self._save_current_settings()

    def _apply_youtube_volume_preset(self):
        """YouTube音声仕様（目標 -14.0 LUFS / True Peak -1.0 dBFS）に基づき、動画出力全体の音量を自動測定・最適化"""
        if (not hasattr(self, "timeline") or not self.timeline or self.timeline.total_duration_sec <= 0) and \
           (not getattr(self, "ext_audio_path", "") or not os.path.isfile(self.ext_audio_path)):
            QMessageBox.information(self, "音量解析", "解析対象の楽曲（MIDI）または外部音声ファイルが読み込まれていません。")
            return

        # 音声ソース判定
        audio_choice = self.combo_exp_audio.currentText() if hasattr(self, "combo_exp_audio") else "MIDIガイド音 (内部音源)"
        if "無音" in audio_choice:
            QMessageBox.information(self, "YouTube音量 自動解析", "動画の音声ソースが「無音」に設定されているため、音量解析は不要です。")
            return

        self.lbl_status_msg.setText("⏳ YouTube音量を解析中 (FFmpegラウドネス測定)...")
        QApplication.processEvents()

        temp_wav = get_portable_path(os.path.join("temp", f"yt_loudness_test_{int(time.time())}.wav"))
        os.makedirs(os.path.dirname(temp_wav), exist_ok=True)

        try:
            # 1. 出力範囲の特定 (動画出力設定の指定範囲と一致させる)
            start_sec = max(0.0, float(self.spin_exp_start.value())) if hasattr(self, "spin_exp_start") else 0.0
            end_sec = float(self.spin_exp_end.value()) if hasattr(self, "spin_exp_end") else (self.timeline.total_duration_sec if self.timeline else 60.0)
            if end_sec <= start_sec:
                end_sec = float(getattr(self.timeline, "total_duration_sec", start_sec + 60.0))
            duration_sec = max(0.5, end_sec - start_sec)

            # 2. 外部音声ソースの選定とPCM読み込み
            audio_path = ""
            if "伴奏音源" in audio_choice:
                if getattr(self, "ext_audio_path", "") and os.path.isfile(self.ext_audio_path):
                    audio_path = self.ext_audio_path
                elif getattr(self, "last_recorded_path", "") and os.path.isfile(self.last_recorded_path):
                    audio_path = self.last_recorded_path
            elif "マイク録音" in audio_choice:
                if getattr(self, "last_recorded_path", "") and os.path.isfile(self.last_recorded_path):
                    audio_path = self.last_recorded_path
                elif getattr(self, "ext_audio_path", "") and os.path.isfile(self.ext_audio_path):
                    audio_path = self.ext_audio_path

            ext_pcm = None
            if audio_path and os.path.isfile(audio_path):
                try:
                    from audio_engine import load_external_audio_pcm
                    ext_pcm = load_external_audio_pcm(audio_path, sample_rate=44100)
                except Exception as e:
                    print(f"[YouTube Preset] 外部音源読み込みエラー: {e}")

            ext_audio_mode = getattr(self, "ext_audio_mode", "頭出し確認 (再生:両方 / 動画:外部のみ)")
            if ("伴奏音源" in audio_choice or "マイク録音" in audio_choice) and ext_pcm is not None:
                ext_audio_mode = "動画:外部のみ"

            part_mode = self.part_combo.currentText() if hasattr(self, "part_combo") else "全パート再生"

            # 3. 音声トラック合成 (基準ボリューム100%かつリミッターなしで生特性を測定)
            from audio_engine import synthesize_midi_to_wav
            synthesize_midi_to_wav(
                midi_notes=self.timeline.main_notes if self.timeline else [],
                current_bpm=self.timeline.default_bpm if self.timeline else 120.0,
                max_duration=duration_sec,
                is_count_in=False,
                is_metro=False,
                output_wav_path=temp_wav,
                sample_rate=44100,
                accompaniment_notes=self.timeline.accomp_notes if self.timeline else [],
                part_play_mode=part_mode,
                ext_audio_pcm=ext_pcm,
                ext_audio_mode=ext_audio_mode,
                ext_audio_offset_ms=self.spin_ext_offset.value() if hasattr(self, "spin_ext_offset") else 0,
                ext_audio_vol_pct=float(self.slider_ext_vol.value()) if hasattr(self, "slider_ext_vol") else 100.0,
                sec_a_in_song=start_sec,
                yt_limiter=False,
                mixer_settings=self._get_current_mixer_settings()
            )

            # 4. FFmpeg loudnormフィルターによるITU-R BS.1770規格ラウドネス解析
            import subprocess, json, re
            cmd = [
                "ffmpeg", "-hide_banner",
                "-i", temp_wav,
                "-af", "loudnorm=I=-14.0:TP=-1.0:print_format=json",
                "-f", "null", "-"
            ]
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)
            match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', proc.stderr)
            if not match:
                raise RuntimeError("FFmpegによるラウドネス解析データの取得に失敗しました。")

            data = json.loads(match.group(0))
            input_i = float(data.get("input_i", -99.0))
            input_tp = float(data.get("input_tp", -99.0))

            if input_i <= -70.0:
                QMessageBox.warning(
                    self,
                    "YouTube音量 自動解析",
                    f"測定された音声が無音または極めて小さいレベルです ({input_i:.1f} LUFS)。\n"
                    f"現在の音量設定を変更せずに維持しました。"
                )
                self.lbl_status_msg.setText("準備完了")
                return

            gain_lufs_db = -14.0 - input_i
            max_peak_gain_db = -1.0 - input_tp
            diff_db = min(gain_lufs_db, max_peak_gain_db)
            gain_linear = 10.0 ** (diff_db / 20.0)
            opt_vol_pct = max(10, min(200, int(round(100.0 * gain_linear))))

            # 5. UIへの反映
            if hasattr(self, "slider_exp_audio_vol"):
                self.slider_exp_audio_vol.setValue(opt_vol_pct)
            if hasattr(self, "chk_yt_limiter"):
                self.chk_yt_limiter.setChecked(True)

            sign_str = f"+{diff_db:.1f}" if diff_db > 0 else f"{diff_db:.1f}"
            status_text = f"YouTube最適化完了: 測定 {input_i:.1f} LUFS ➔ 音量 {opt_vol_pct}% ({sign_str} dB)"
            self.lbl_status_msg.setText(status_text)
            self._save_current_settings()

            QMessageBox.information(
                self,
                "YouTube音量 自動解析・最適化",
                f"【YouTube音量 最適化完了】\n\n"
                f"・測定ラウドネス: {input_i:.1f} LUFS （YouTube目標: -14.0 LUFS）\n"
                f"・測定トゥルーピーク: {input_tp:.1f} dBFS （上限基準: -1.0 dBFS）\n\n"
                f"▶ 推奨音量補正: {sign_str} dB ➔ 「動画音声音量」を 【 {opt_vol_pct}% 】 に自動設定しました。\n"
                f"▶ 音割れ防止リミッター: 【 有効 (ON) 】 にセットしました。\n\n"
                f"※YouTubeの自動音量減衰を受けず、最高のダイナミクスと音質で再生されます。"
            )
        except Exception as e:
            print(f"[YouTube Audio Analyzer Error] {e}")
            self.lbl_status_msg.setText(f"YouTube音量解析エラー: {e}")
            QMessageBox.warning(self, "音量解析エラー", f"音量解析中にエラーが発生しました:\n{e}\n\n現在の音量設定を維持します。")
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

    def _on_ext_offset_changed(self, val: int):
        try:
            self.ext_offset_ms = int(val)
            self.user_settings["ext_audio_offset_ms"] = val

            # 再生中の場合、前奏カウントイン中(cur_sec < 0)でなければデバウンス同期を起動
            if self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
                cur_sec = self.clock.get_current_base_sec()
                if cur_sec >= 0.0:
                    self._ext_resync_timer.start()

            # 設定・プロファイルの保存をデバウンス (連打時のディスクI/O競合を抑制)
            self._ext_save_timer.start()
        except Exception as e:
            print(f"[ExtAudio Offset Error] {e}")

    def _do_ext_audio_resync(self):
        try:
            if self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
                cur_sec = self.clock.get_current_base_sec()
                self._sync_ext_audio_playback(True, cur_sec)
        except Exception as e:
            print(f"[ExtAudio Offset Resync Warning] {e}")

    def _do_ext_offset_save(self):
        try:
            self._save_current_song_profile()
            self._save_current_settings()
        except Exception as e:
            print(f"[ExtAudio Offset Save Error] {e}")

    def _on_ext_offset_adjust(self, delta_ms: int):
        try:
            new_val = self.spin_ext_offset.value() + int(delta_ms)
            self.spin_ext_offset.setValue(max(-5000, min(5000, new_val)))
        except Exception as e:
            print(f"[ExtAudio Offset Adjust Error] {e}")

    def _sync_ext_audio_playback(self, is_playing: bool, target_sec: float = None):
        """外部音源をタイムラインと完全同期再生/一時停止 (PCMスライス再生方式)"""
        pcm = self._ensure_ext_pcm_loaded()
        if pcm is None or len(pcm) == 0:
            return

        mode = getattr(self, "ext_audio_mode", "")
        if "外部音源オフ" in mode or "ガイド音のみ" in mode or "伴奏ミュート" in mode:
            self._stop_ext_playback()
            return

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

            if not hasattr(self, "_ext_channel") or self._ext_channel is None:
                self._ext_channel = pygame.mixer.Channel(1)

            cur_sec = self.clock.get_current_base_sec() if target_sec is None else target_sec
            offset_sec = float(self.spin_ext_offset.value()) / 1000.0
            # 共通計算式: src_sec = cur_sec - offset_sec (+offsetで遅らせる / -offsetで早める)
            src_sec = cur_sec - offset_sec
            vol = max(0.0, min(1.0, (self.slider_ext_vol.value() / 100.0) * (self.vol_slider.value() / 100.0)))

            if is_playing:
                if src_sec >= 0.0:
                    start_sample = int(round(src_sec * 44100))
                    if start_sample < len(pcm):
                        sound_slice = np.ascontiguousarray(pcm[start_sample:])
                        snd = pygame.sndarray.make_sound(sound_slice)
                        self._ext_channel.set_volume(vol)
                        self._ext_channel.play(snd)
                        self._ext_pending_start = False
                    else:
                        self._ext_channel.stop()
                        self._ext_pending_start = False
                else:
                    # まだ外部音源開始時刻に達していない (待機状態)
                    self._ext_channel.stop()
                    self._ext_pending_start = True
            else:
                self._ext_channel.stop()
                self._ext_pending_start = False
        except Exception as e:
            print(f"[ExtAudio Sync Error] {e}")

    def _on_ext_audition_play(self):
        """外部音源の頭出し試聴（メイン再生・画面描画・ガイド音と完全同期）"""
        self._on_play_toggle()

    def _on_ext_audition_restart(self):
        """外部音源を先頭から再生（巻き戻し＆再生同期キック）"""
        self._on_rewind()
        if self.clock.get_state() != SharedClockBridge.STATE_PLAYING:
            self._on_play_toggle()

    def _on_ext_audition_stop(self):
        """外部音源の試聴停止（メイン再生完全停止と同期）"""
        self._on_stop()
        if hasattr(self, "btn_ext_audition"):
            self.btn_ext_audition.setText("▶ 試聴")
            pass


    def _on_open_output_folder(self):
        """動画出力先フォルダ (output/) をエクスプローラーで開く"""
        out_dir = get_portable_path("output")
        os.makedirs(out_dir, exist_ok=True)
        try:
            import subprocess
            subprocess.Popen(f'explorer "{out_dir}"')
        except Exception as e:
            print(f"[Open Output Folder Error] {e}")

    def _on_preview_frame(self):
        """現在の再生位置のフレームを1枚オフスクリーンレンダリングしてポップアップ表示"""
        from video_exporter import OffscreenVisualizerRenderer, calc_export_resolution
        from dialogs import SingleFramePreviewDialog

        cur_sec = max(0.0, self.clock.get_current_base_sec())
        w, h = calc_export_resolution(self.combo_exp_res.currentText(), self.ratio_combo.currentText())

        render_settings = self._build_export_render_settings()

        title_overlay = {
            "enabled": self.chk_exp_title.isChecked() and ("クロマキー" not in self.combo_exp_style.currentText()) and ("完全背景透過" not in self.combo_exp_style.currentText()),
            "template": self.combo_title_template.currentText(),
            "title": self.txt_exp_title.text().strip() or (self.timeline.filename or ""),
            "credit": self.txt_exp_credit.text().strip(),
        }

        try:
            renderer = OffscreenVisualizerRenderer(
                self.timeline,
                width=w,
                height=h,
                aspect_ratio=self.ratio_combo.currentText(),
                settings=render_settings
            )
            qimage = renderer.render_single_frame_qimage(cur_sec, title_overlay=title_overlay)
            dlg = SingleFramePreviewDialog(qimage, f"再生位置: {cur_sec:.2f}s", parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "プレビューエラー", f"プレビュー描画に失敗しました:\n{e}")

    def _on_start_video_export(self):
        """動画書き出し処理の開始"""
        if not getattr(self.timeline, "main_notes", None):
            QMessageBox.information(self, "書き出しエラー", "MIDIファイルが読み込まれていません。\n先にMIDIファイルを開いてください。")
            return

        from video_exporter import check_ffmpeg_available, VideoExportThread, calc_export_resolution
        from dialogs import ExportProgressDialog

        if not check_ffmpeg_available():
            QMessageBox.warning(
                self,
                "FFmpegが見つかりません",
                "動画書き出しにはFFmpegが必要です。\nFFmpegがシステムにインストールされているか確認してください。"
            )
            return

        # 再生中なら停止
        if self.clock.get_state() != SharedClockBridge.STATE_STOPPED:
            self._on_stop()

        # 出力先パスの指定
        is_transparent = ("完全背景透過" in self.combo_exp_style.currentText())
        ext = ".mov" if is_transparent else ".mp4"
        filter_str = "QuickTime MOV Video (*.mov)" if is_transparent else "MP4 Video (*.mp4)"

        song_base = os.path.splitext(self.timeline.filename)[0] if self.timeline.filename else "harmonica_visualizer"
        out_dir = get_portable_path("output")
        os.makedirs(out_dir, exist_ok=True)
        default_file = os.path.join(out_dir, f"{song_base}{ext}")

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "動画の保存先を指定",
            default_file,
            filter_str
        )
        if not out_path:
            return

        if is_transparent and not out_path.lower().endswith(".mov"):
            out_path = os.path.splitext(out_path)[0] + ".mov"

        # 解像度設定 (アスペクト比連動の真の解像度)
        w, h = calc_export_resolution(self.combo_exp_res.currentText(), self.ratio_combo.currentText())

        # フレームレート
        fps = 30 if "30" in self.combo_exp_fps.currentText() else 60

        # エンコーダー
        codec = self.combo_exp_codec.currentText()

        # 前後余白秒数
        try:
            intro_sec = float(self.combo_exp_intro.currentText().replace("秒", "").strip())
        except Exception:
            intro_sec = 1.0
        try:
            outro_sec = float(self.combo_exp_outro.currentText().replace("秒", "").strip())
        except Exception:
            outro_sec = 2.0

        # 範囲
        start_sec = self.spin_exp_start.value()
        end_sec = self.spin_exp_end.value()
        if end_sec <= start_sec:
            end_sec = self.timeline.total_duration_sec

        # 音声トラック選定
        audio_choice = self.combo_exp_audio.currentText()
        audio_path = ""
        if "伴奏音源" in audio_choice:
            if self.ext_audio_path and os.path.isfile(self.ext_audio_path):
                audio_path = self.ext_audio_path
            elif self.last_recorded_path and os.path.isfile(self.last_recorded_path):
                audio_path = self.last_recorded_path
        elif "マイク録音" in audio_choice:
            if self.last_recorded_path and os.path.isfile(self.last_recorded_path):
                audio_path = self.last_recorded_path
            elif self.ext_audio_path and os.path.isfile(self.ext_audio_path):
                audio_path = self.ext_audio_path

        # レンダラー向け設定ディクト (v3.1.0 共通生成)
        render_settings = self._build_export_render_settings()

        # タイトルカード情報
        title_text = self.txt_exp_title.text().strip() or (self.timeline.filename or "")
        credit_text = self.txt_exp_credit.text().strip()
        title_overlay = {
            "enabled": self.chk_exp_title.isChecked() and ("クロマキー" not in self.combo_exp_style.currentText()) and ("完全背景透過" not in self.combo_exp_style.currentText()),
            "template": self.combo_title_template.currentText(),
            "title": title_text,
            "credit": credit_text,
        }

        # カウントイン小節数
        try:
            cleaned = self.combo_count_in.currentText().replace("小節", "").strip().split()[0]
            ci_m = int(cleaned)
        except Exception:
            ci_m = 0

        export_config = {
            "width": w,
            "height": h,
            "fps": fps,
            "aspect_ratio": self.ratio_combo.currentText(),
            "output_path": out_path,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "intro_sec": intro_sec,
            "outro_sec": outro_sec,
            "fade_in": self.chk_fade_in.isChecked(),
            "fade_out": self.chk_fade_out.isChecked(),
            "fade_in_sec": self.spin_fade_in.value(),
            "fade_out_sec": self.spin_fade_out.value(),
            "fade_title_mode": self.combo_fade_title.currentText(),
            "is_count_in": (ci_m > 0),
            "count_in_measures": ci_m,
            "is_metro": (self.combo_metro.currentText() != "なし"),
            "metronome_pattern": self.combo_metro.currentText(),
            "yt_limiter": self.chk_yt_limiter.isChecked() if hasattr(self, "chk_yt_limiter") else True,
            "export_audio_vol_pct": float(self.slider_exp_audio_vol.value()) if hasattr(self, "slider_exp_audio_vol") else 100.0,
            "ext_audio_offset_ms": self.spin_ext_offset.value(),
            "ext_audio_vol_pct": float(self.slider_ext_vol.value()),
            "mixer_settings": self._get_current_mixer_settings(),
            "ext_audio_mode": self.ext_audio_mode,
            "codec": codec,
            "audio_source": audio_choice,
            "audio_path": audio_path,
            "part_mode": self.part_combo.currentText(),
            "reverb_enabled": self.chk_exp_reverb.isChecked(),
            "reverb_type": self.user_settings.get("reverb_type", "ルーム (自然な部屋鳴り)"),
            "reverb_wet_pct": int(self.user_settings.get("reverb_wet_pct", 35)),
            "title_overlay": title_overlay,
            "settings": render_settings,
        }

        # 書き出しワーカースレッド生成＆ダイアログ表示
        try:
            export_thread = VideoExportThread(self.timeline, export_config, parent=self)
            dlg = ExportProgressDialog(export_thread, out_path, parent=self)
            export_thread.start()
            dlg.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "動画書き出しエラー", f"動画書き出し処理の開始中にエラーが発生しました:\n{e}")


def main():
    """アプリケーション起動エントリーポイント"""
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_DARK_STYLE)

    window = HarmonicaMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()



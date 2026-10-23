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
    QLineEdit, QColorDialog, QMessageBox
)

from ipc_state import SharedClockBridge
from midi_timeline import MidiTimelineData
from gl_visualizer import HarmonicaGLWidget
from audio_engine import AudioEngine, AudioRecorder, AuditionPlayer, apply_harmonica_reverb_numpy
from dialogs import PartSelectDialog
import settings_manager
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
QCheckBox {{
    spacing: 5px;
    color: #C0C0D0;
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


class HarmonicaMainWindow(QMainWindow):
    """v3.0 メインアプリケーションウィンドウ (クラシックL型レイアウト)"""

    sig_loop_wrapped = pyqtSignal()
    sig_playback_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harmonica Visualizer v3.0 [PyQt6 64-bit OpenGL Edition]")
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

        # 4. 定周期UI更新タイマー (30Hz)
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(33)
        self.ui_timer.timeout.connect(self._on_ui_tick)
        self.ui_timer.start()

        # 5. ユーザー設定の反映
        self._apply_user_settings()

        # 6. 組み込み高品位クロマチック音階デモを即座に展開・ロード
        self.timeline.load_demo(inst_type=self.inst_combo.currentText())
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
        import harmonica_map
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
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(int(round(float(self.user_settings.get("speed_ratio", 1.0)) * 100)))
        self.speed_slider.setFixedWidth(80)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        row1.addWidget(self.speed_slider)

        self.lbl_speed_val = QLabel(f"{self.speed_slider.value()}%", self)
        self.lbl_speed_val.setMinimumWidth(44)
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

        # ステータス即時メッセージ (大幅拡張 stretch=1)
        self.lbl_status_msg = QLabel("準備完了", self)
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
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 1. 🎷 ハーモニカモデル ＆ 運指設定グループ
        f_inst = QFrame()
        f_inst.setObjectName("groupFrame")
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
        r_fing.addWidget(self.combo_fing_preset, stretch=1)
        l_inst.addLayout(r_fing)

        r_mono = QHBoxLayout()
        r_mono.addWidget(QLabel("重なり音:"))
        self.combo_monophonic_mode = QComboBox(self)
        self.combo_monophonic_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_monophonic_mode.addItems(["すべて有効", "高音優先 (上パート)", "低音優先 (下パート)"])
        self.combo_monophonic_mode.setToolTip("和音やハモリが重なった際の単音化ルール (キャンバス上のShift+右クリックで個別変更可)")
        self.combo_monophonic_mode.currentTextChanged.connect(self._on_monophonic_mode_changed)
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
        self.spin_sp_start.setRange(30, 200)
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
        self.spin_sp_target.setRange(50, 250)
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
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 1. 軌道・比率・音名
        f_geom = QFrame()
        f_geom.setObjectName("groupFrame")
        l_geom = QVBoxLayout(f_geom)
        l_geom.setContentsMargins(6, 6, 6, 6)
        l_geom.setSpacing(6)

        r_traj = QHBoxLayout()
        r_traj.addWidget(QLabel("ノーツ軌道:"))
        self.traj_combo = QComboBox(self)
        self.traj_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.traj_combo.addItems(["3段階 (練習標準)", "2段階 (ビジュアル)", "垂直落下 (穴直上)"])
        self.traj_combo.setCurrentText(self.user_settings.get("trajectory_mode", "3段階 (練習標準)"))
        self.traj_combo.setToolTip("ノーツが画面上部からハーモニカ穴へ向かう軌道の形状")
        self.traj_combo.currentTextChanged.connect(self._on_traj_changed)
        r_traj.addWidget(self.traj_combo, stretch=1)
        l_geom.addLayout(r_traj)

        r_lang = QHBoxLayout()
        r_lang.addWidget(QLabel("音名表記:"))
        self.lang_combo = QComboBox(self)
        self.lang_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.lang_combo.setMinimumContentsLength(6)
        self.lang_combo.addItems(["ドレミ", "CDE", "なし"])
        self.lang_combo.setCurrentText(self.user_settings.get("lang_mode", "ドレミ"))
        self.lang_combo.setToolTip("画面上の音名表示（ドレミ / 英語音名 CDE / 非表示）")
        self.lang_combo.currentTextChanged.connect(self._on_lang_changed)
        r_lang.addWidget(self.lang_combo)

        r_lang.addWidget(QLabel("比率:"))
        self.ratio_combo = QComboBox(self)
        self.ratio_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.ratio_combo.setMinimumContentsLength(4)
        self.ratio_combo.addItems(["16:9", "4:3", "9:16"])
        self.ratio_combo.setCurrentText(self.user_settings.get("aspect_ratio", "16:9"))
        self.ratio_combo.setToolTip("ビジュアライザー描画のアスペクト比 (横長16:9 / 縦長9:16等)")
        self.ratio_combo.currentTextChanged.connect(self._on_ratio_changed)
        r_lang.addWidget(self.ratio_combo)
        l_geom.addLayout(r_lang)
        v_box.addWidget(f_geom)

        # 2. カラーテーマ & 吹吸カラー選択
        f_col = QFrame()
        f_col.setObjectName("groupFrame")
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
        self.chk_hole_num.setToolTip("ハーモニカ各ホールの穴番号(1〜16)を表示")
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
        self.combo_hole_num_style.addItems(["実機標準 (低音ドット付)", "通し番号 (1〜16)"])
        self.combo_hole_num_style.setCurrentText(self.user_settings.get("hole_num_style", "実機標準 (低音ドット付)"))
        self.combo_hole_num_style.setToolTip("実機同様に低音穴にドットを付与する表記（·1〜·4, 1〜12）か、通し番号（1〜16）かを選択")
        self.combo_hole_num_style.currentTextChanged.connect(self._on_hole_num_style_changed)
        r_hole_style.addWidget(self.combo_hole_num_style, stretch=1)
        l_chk.addLayout(r_hole_style)

        r_grid4 = QHBoxLayout()
        r_grid4.addWidget(QLabel("穴下ノート表示:"))
        self.combo_grid4 = QComboBox(self)
        self.combo_grid4.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_grid4.addItems(["4音グリッド表示", "1音表示 (従来)"])
        self.combo_grid4.setCurrentText(self.user_settings.get("grid4_mode", self.user_settings.get("show_grid4", "4音グリッド表示")))
        self.combo_grid4.setToolTip("穴の下に配置する音名（田の字4音グリッド / 単一吹音表示）")
        self.combo_grid4.currentTextChanged.connect(self._on_grid4_changed)
        r_grid4.addWidget(self.combo_grid4, stretch=1)
        l_chk.addLayout(r_grid4)
        v_box.addWidget(f_chk)

        # 4. 背景画像 & 減光 (コントラスト)
        f_bg = QFrame()
        f_bg.setObjectName("groupFrame")
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
        bg_name = os.path.basename(cur_bg) if cur_bg and os.path.exists(cur_bg) else "未設定 (ダーク背景)"
        self.lbl_bg_info = QLabel(f"画像: {bg_name}", self)
        self.lbl_bg_info.setStyleSheet("color: #94A3B8; font-size: 10px;")
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
            "画面に引き伸ばす"
        ])
        self.combo_bg_fit.setCurrentText(self.user_settings.get("bg_fit_mode", "中央トリミング (画面いっぱい)"))
        self.combo_bg_fit.setToolTip("背景画像の画面フィット方式")
        self.combo_bg_fit.currentTextChanged.connect(self._on_bg_fit_changed)
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
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 1. 音量制御
        f_vol = QFrame()
        f_vol.setObjectName("groupFrame")
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
            "Windows標準MIDI (WinMM / 推奨)",
            "内蔵軽量シンセ (遅延0ms・トラブルシューティング用)"
        ])
        self.combo_guide_audio.setCurrentText(self.user_settings.get("guide_audio_engine", "Windows標準MIDI (WinMM / 推奨)"))
        self.combo_guide_audio.setToolTip("再生に使用するMIDI音源エンジン")
        self.combo_guide_audio.currentTextChanged.connect(self._on_guide_audio_changed)
        r_gas.addWidget(self.combo_guide_audio, stretch=1)
        l_vol.addLayout(r_gas)

        self.chk_force_harmonica = QCheckBox("主旋律をハーモニカ音色に固定", self)
        self.chk_force_harmonica.setChecked(bool(self.user_settings.get("force_harmonica", True)))
        self.chk_force_harmonica.setToolTip("MIDIファイル内の楽器指定に関わらず主旋律パートをハーモニカ音色(GM 22)で再生")
        self.chk_force_harmonica.toggled.connect(lambda v: setattr(self.audio_engine, "force_main_harmonica", v))
        l_vol.addWidget(self.chk_force_harmonica)

        self.chk_yt_limiter = QCheckBox("音割れ防止リミッター (-1.0dB)", self)
        self.chk_yt_limiter.setChecked(bool(self.user_settings.get("yt_limiter", True)))
        self.chk_yt_limiter.setToolTip("動画音声やWAV合成時に音割れを防ぐためピークを-1.0dBFSに自動制限")
        self.chk_yt_limiter.toggled.connect(self._save_current_settings)
        l_vol.addWidget(self.chk_yt_limiter)
        v_box.addWidget(f_vol)

        # 2. 🎙️ マイク録音 (ワンクリック録音)
        f_rec = QFrame()
        f_rec.setObjectName("groupFrame")
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
        r_ch.addWidget(self.combo_rec_ch, stretch=1)
        l_rec.addLayout(r_ch)

        # テイク＆試聴
        r_take = QHBoxLayout()
        self.lbl_rec_take = QLabel("録音テイク: 未録音", self)
        self.lbl_rec_take.setStyleSheet("color: #64748B; font-size: 11px;")
        r_take.addWidget(self.lbl_rec_take, stretch=1)

        self.btn_rec_listen = QPushButton("▶ 試聴", self)
        self.btn_rec_listen.setFixedWidth(64)
        self.btn_rec_listen.setEnabled(False)
        self.btn_rec_listen.setToolTip("直前に録音したテイクを試聴再生")
        self.btn_rec_listen.clicked.connect(self._on_rec_listen_toggle)
        r_take.addWidget(self.btn_rec_listen)

        btn_open_rec = QPushButton("📂 フォルダ", self)
        btn_open_rec.setFixedWidth(74)
        btn_open_rec.setToolTip("録音されたWAVファイルが保存されるフォルダを開く")
        btn_open_rec.clicked.connect(self._on_open_rec_folder)
        r_take.addWidget(btn_open_rec)
        l_rec.addLayout(r_take)
        v_box.addWidget(f_rec)

        # 3. ✨ ハーモニカ用リバーブ (空間残響エフェクト)
        f_rev = QFrame()
        f_rev.setObjectName("groupFrame")
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
        l_ext = QVBoxLayout(f_ext)
        l_ext.setContentsMargins(6, 6, 6, 6)
        l_ext.setSpacing(6)
        l_ext.addWidget(QLabel("🎵 <b>伴奏・外部音源 (D&D対応):</b>"))

        r_ext1 = QHBoxLayout()
        btn_ext_open = QPushButton("📂 伴奏選択", self)
        btn_ext_open.setFixedWidth(84)
        btn_ext_open.setToolTip("外部の伴奏オーディオファイル (MP3/WAV/M4A/FLAC等) を選択 [ドラッグ＆ドロップ可]")
        btn_ext_open.clicked.connect(self._on_select_ext_audio)
        r_ext1.addWidget(btn_ext_open)

        btn_ext_clear = QPushButton("✕", self)
        btn_ext_clear.setFixedWidth(26)
        btn_ext_clear.setToolTip("音源を解除")
        btn_ext_clear.clicked.connect(self._on_clear_ext_audio)
        r_ext1.addWidget(btn_ext_clear)

        self.lbl_ext_audio = QLabel("未選択 (MP3/WAV等をD&D可)", self)
        self.lbl_ext_audio.setStyleSheet("color: #64748B; font-size: 11px;")
        if self.ext_audio_path and os.path.exists(self.ext_audio_path):
            self.lbl_ext_audio.setText(os.path.basename(self.ext_audio_path))
            self.lbl_ext_audio.setToolTip(self.ext_audio_path)
            self.lbl_ext_audio.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        r_ext1.addWidget(self.lbl_ext_audio, stretch=1)
        l_ext.addLayout(r_ext1)

        r_ext2 = QHBoxLayout()
        r_ext2.addWidget(QLabel("モード:"))
        self.combo_ext_mode = QComboBox(self)
        self.combo_ext_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_ext_mode.addItems([
            "頭出し確認 (再生:両方 / 動画:外部のみ)",
            "外部音源のみ (再生も動画も外部のみ)",
            "両方ミックス (再生も動画も両方)",
            "外部音源オフ (ガイド音のみ)"
        ])
        self.combo_ext_mode.setCurrentText(self.user_settings.get("ext_audio_mode", "頭出し確認 (再生:両方 / 動画:外部のみ)"))
        self.combo_ext_mode.setToolTip("外部伴奏と内部MIDI音源の再生・書き出し時のミックス動作")
        self.combo_ext_mode.currentTextChanged.connect(self._on_ext_mode_changed)
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
        self.spin_ext_offset.setFixedWidth(68)
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
            btn.setStyleSheet("font-size: 11px; padding: 2px 4px;")
            btn.setToolTip(f"同期オフセットを {label} 微調整")
            btn.clicked.connect(lambda _, d=val: self._on_ext_offset_adjust(d))
            r_fine.addWidget(btn)
        l_ext.addLayout(r_fine)

        # 試聴ボタン
        r_aud = QHBoxLayout()
        self.btn_ext_audition = QPushButton("▶ 試聴", self)
        self.btn_ext_audition.setStyleSheet("background-color: #1E3A5F; font-weight: bold;")
        self.btn_ext_audition.setToolTip("設定したオフセット位置から外部伴奏音源を試聴再生")
        self.btn_ext_audition.clicked.connect(self._on_ext_audition_play)
        r_aud.addWidget(self.btn_ext_audition)

        self.btn_ext_restart = QPushButton("⏮ 先頭", self)
        self.btn_ext_restart.setToolTip("外部伴奏音源を0秒(ファイル先頭)から試聴再生")
        self.btn_ext_restart.clicked.connect(self._on_ext_audition_restart)
        r_aud.addWidget(self.btn_ext_restart)

        self.btn_ext_stop = QPushButton("⏹ 停止", self)
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
        v_box = QVBoxLayout(content)
        v_box.setContentsMargins(2, 4, 6, 4)
        v_box.setSpacing(8)

        # 1. 動画レンダリング品質＆解像度
        f_exp = QFrame()
        f_exp.setObjectName("groupFrame")
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
        r_style.addWidget(self.combo_exp_style, stretch=1)
        l_exp.addLayout(r_style)

        self.r_bg_chroma = QHBoxLayout()
        self.r_bg_chroma.addWidget(QLabel("クロマキー背景色:"))
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
        r_enc.addWidget(self.combo_exp_codec, stretch=1)
        l_exp.addLayout(r_enc)

        r_rng = QHBoxLayout()
        r_rng.addWidget(QLabel("範囲:"))
        self.spin_exp_start = QDoubleSpinBox(self)
        self.spin_exp_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_exp_start.setRange(0.0, 9999.0)
        self.spin_exp_start.setValue(0.0)
        self.spin_exp_start.setSuffix("s")
        self.spin_exp_start.setFixedWidth(52)
        self.spin_exp_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_exp_start.setToolTip("動画書き出しの開始秒 [直接入力 / マウスホイールで変更]")
        r_rng.addWidget(self.spin_exp_start)

        r_rng.addWidget(QLabel("〜"))

        self.spin_exp_end = QDoubleSpinBox(self)
        self.spin_exp_end.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_exp_end.setRange(0.1, 9999.0)
        self.spin_exp_end.setValue(float(getattr(self.timeline, "total_duration_sec", 60.0)))
        self.spin_exp_end.setSuffix("s")
        self.spin_exp_end.setFixedWidth(52)
        self.spin_exp_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_exp_end.setToolTip("動画書き出しの終了秒 [直接入力 / マウスホイールで変更]")
        r_rng.addWidget(self.spin_exp_end)

        self.btn_set_ab_range = QPushButton("🔁 A-B反映", self)
        self.btn_set_ab_range.setFixedWidth(86)
        self.btn_set_ab_range.setToolTip("現在設定されているA-Bループの小節範囲（開始秒〜終了秒）を動画の出力範囲にコピーします")
        self.btn_set_ab_range.clicked.connect(self._on_set_ab_range_to_export)
        r_rng.addWidget(self.btn_set_ab_range)
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
        l_aud = QVBoxLayout(f_aud)
        l_aud.setContentsMargins(6, 6, 6, 6)
        l_aud.setSpacing(6)
        l_aud.addWidget(QLabel("🎵 <b>動画の音声トラック設定:</b>"))

        r_asrc = QHBoxLayout()
        r_asrc.addWidget(QLabel("音声ソース:"))
        self.combo_exp_audio = QComboBox(self)
        self.combo_exp_audio.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_exp_audio.addItems([
            "伴奏音源 (外部音源優先)",
            "マイク録音テイク (演奏収録)",
            "MIDIガイド音 (内部音源)",
            "無音 (映像のみ)"
        ])
        self.combo_exp_audio.setToolTip("動画に合成する音声ソースの優先順位")
        r_asrc.addWidget(self.combo_exp_audio, stretch=1)
        l_aud.addLayout(r_asrc)

        self.chk_exp_reverb = QCheckBox("音声にリバーブを適用", self)
        self.chk_exp_reverb.setChecked(bool(self.user_settings.get("reverb_enabled", False)))
        self.chk_exp_reverb.setToolTip("書き出す動画の音声トラックにハーモニカ用リバーブエフェクトを適用")
        l_aud.addWidget(self.chk_exp_reverb)
        v_box.addWidget(f_aud)

        # 3. タイトル・クレジット表示
        f_tit = QFrame()
        f_tit.setObjectName("groupFrame")
        l_tit = QVBoxLayout(f_tit)
        l_tit.setContentsMargins(6, 6, 6, 6)
        l_tit.setSpacing(6)
        l_tit.addWidget(QLabel("✨ <b>タイトル ＆ クレジット表示:</b>"))

        self.chk_exp_title = QCheckBox("タイトル・クレジットを表示", self)
        self.chk_exp_title.setChecked(True)
        self.chk_exp_title.setToolTip("動画内に曲名タイトルやクレジット文字列をオーバーレイ合成（透過MOV・クロマキー時は自動OFF）")
        l_tit.addWidget(self.chk_exp_title)

        r_tpl = QHBoxLayout()
        r_tpl.addWidget(QLabel("配置テンプレート:"))
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
        r_tpl.addWidget(self.combo_title_template, stretch=1)
        l_tit.addLayout(r_tpl)

        l_tit.addWidget(QLabel("曲名 (タイトル):"))
        self.txt_exp_title = QLineEdit(self)
        self.txt_exp_title.setPlaceholderText("曲名を入力")
        self.txt_exp_title.setText(self.timeline.filename or "")
        self.txt_exp_title.setToolTip("動画に表示する楽曲名")
        l_tit.addWidget(self.txt_exp_title)

        l_tit.addWidget(QLabel("演奏者・クレジット:"))
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
        r_ftitle.addWidget(QLabel("フェード対象:"))
        self.combo_fade_title = QComboBox(self)
        self.combo_fade_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.combo_fade_title.addItems(["フェード中もタイトル表示", "画面と一緒にフェードイン", "フェード中はタイトル非表示"])
        self.combo_fade_title.setCurrentText(str(self.user_settings.get("export_fade_title_mode", "フェード中もタイトル表示")))
        self.combo_fade_title.setToolTip("フェードイン/アウト時のタイトルカードの表示連動動作")
        r_ftitle.addWidget(self.combo_fade_title, stretch=1)
        l_tit.addLayout(r_ftitle)
        v_box.addWidget(f_tit)

        # 4. 出力実行
        f_btn = QFrame()
        f_btn.setObjectName("groupFrame")
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

    def _on_tab_changed(self, index: int):
        if index == 0:
            # 練習タブ: 常に全画面 16:9 で広々と表示
            self.gl_widget.set_aspect_ratio("16:9")
            self.gl_widget.set_canvas_bg_color("ノーマル（黒）", is_chromakey=False)
        elif index in (1, 3):
            # 画面作り / 動画出力タブ: 設定された出力アスペクト比で忠実にプレビュー
            self.gl_widget.set_aspect_ratio(self.ratio_combo.currentText())
            is_chroma = ("クロマキー" in self.combo_exp_style.currentText()) and (index == 3)
            self.gl_widget.set_canvas_bg_color(self.combo_exp_bg.currentText(), is_chromakey=is_chroma)

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
            self.combo_hole_num_style.blockSignals(True)
            self.combo_hole_num_style.setCurrentText(s.get("hole_num_style", "実機標準 (低音ドット付)"))
            self.combo_hole_num_style.blockSignals(False)
        self.gl_widget.set_use_ring(s.get("show_ring", s.get("use_ring", True)))
        self.gl_widget.set_show_glow(s.get("show_glow", True))
        self.gl_widget.set_show_legend(s.get("show_legend", True))
        g4_mode = s.get("grid4_mode", s.get("show_grid4", "4音グリッド表示"))
        self.gl_widget.set_show_grid4(g4_mode == "4音グリッド表示")

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

    def _save_current_settings(self):
        self.user_settings["inst_type"] = self.inst_combo.currentText()
        self.user_settings["trajectory_mode"] = self.traj_combo.currentText()
        self.user_settings["lang_mode"] = self.lang_combo.currentText()
        self.user_settings["aspect_ratio"] = self.ratio_combo.currentText()
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
        self.gl_widget.set_show_grid4(mode == "4音グリッド表示")
        self._save_current_settings()

    def _on_export_style_changed(self, style: str):
        is_chroma = ("クロマキー" in style)
        is_trans = ("完全背景透過" in style)
        self.combo_exp_bg.setEnabled(is_chroma)
        self.chk_exp_title.setEnabled(not is_chroma and not is_trans)
        self.combo_title_template.setEnabled(not is_chroma and not is_trans)
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
        self.lbl_bg_info.setText(f"画像: {os.path.basename(filepath)}")
        self.lbl_status_msg.setText(f"🖼️ 背景画像を設定しました: {os.path.basename(filepath)}")
        self._save_current_settings()

    def _on_clear_bg_image(self):
        self.gl_widget.clear_background_image()
        self.lbl_bg_info.setText("画像: 未設定 (ダーク背景)")
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
            import harmonica_map
            self.combo_fing_preset.blockSignals(True)
            self.combo_fing_preset.setCurrentText(harmonica_map.CURRENT_SONG_PRESET)
            self.combo_fing_preset.blockSignals(False)
            self._update_song_info_labels()
            self.lbl_status_msg.setText("💾 変え指設定を保存・適用しました")

    def _on_reset_song_fingering(self):
        ans = QMessageBox.question(
            self,
            "運指データの初期化確認",
            f"曲「{self.timeline.filename}」の個別運指データをすべて初期化（リセット）し、\n運指プリセットの初期状態へ戻しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            from harmonica_map import reset_song_fingering
            reset_song_fingering(self.timeline.filepath)
            self.timeline.rebind_fingerings(self.inst_combo.currentText())
            if self.audio_engine:
                self.audio_engine.load_timeline(self.timeline)
                self.audio_engine.seek(self.clock.get_current_base_sec())
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()
            self._check_out_of_range_and_notify()
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
        if val_a > val_b:
            self.spin_loop_b.setValue(val_a)
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
            self.speed_slider.setValue(self.spin_sp_start.value())
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
                self.speed_slider.setValue(new_pct)
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
            from harmonica_map import save_song_profile
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
            save_song_profile(self.timeline.filepath, extra)

    def _check_out_of_range_and_notify(self):
        """音域外ノーツの存在を検出してステータスバー等に通知"""
        if hasattr(self, "timeline") and self.timeline:
            diag = self.timeline.diagnose_pitch_range()
            status = diag.get("status")
            if status in ("out_of_range", "exceeds_instrument"):
                out_cnt = diag.get("out_count", 0)
                rec = diag.get("recommendation_text", "")
                self.lbl_status_msg.setText(f"⚠ 音域外: {out_cnt}音 | {rec}")
            elif status == "ok":
                cur_text = self.lbl_status_msg.text()
                if "音域外" in cur_text:
                    self.lbl_status_msg.setText("✅ 全音域クリア (演奏可能)")

    def _on_check_pitch_range(self):
        """音域チェックボタン押下時の詳細診断ダイアログ表示"""
        if not hasattr(self, "timeline") or not self.timeline or not getattr(self.timeline, "main_notes", None):
            QMessageBox.information(self, "音域チェック", "MIDIファイルが読み込まれていません。")
            return

        diag = self.timeline.diagnose_pitch_range()
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
            self.lbl_status_msg.setText(f"⚠ 音域外: {diag['out_count']}音 (曲の音域がモデルの上限/下限を超過)")
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
            from harmonica_map import load_song_profile
            prof = load_song_profile(filepath)

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

            # 単音化 & 除外ノーツ非表示復元（未設定ならデフォルトにリセット）
            mono_mode = prof.get("monophonic_mode", "すべて有効")
            hide_muted = bool(prof.get("hide_muted_notes", False))
            import harmonica_map
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
            self._sync_ext_audio_playback(False)
        else:
            cur_sec = self.clock.get_current_base_sec()
            if st == SharedClockBridge.STATE_STOPPED:
                if hasattr(self, "chk_stepup") and self.chk_stepup.isChecked():
                    if not getattr(self, "_stepup_running", False):
                        self.speed_slider.setValue(self.spin_sp_start.value())
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
            if cur_sec >= 0.0:
                self._sync_ext_audio_playback(True, cur_sec)

    def _on_stop(self):
        start_sec = self.timeline.get_sec_for_measure(self.spin_loop_a.value()) if self.loop_playback else 0.0
        self.clock.set_anchor(start_sec, speed_ratio=self.speed_slider.value() / 100.0, state=SharedClockBridge.STATE_STOPPED)
        self.clock.clear_active_notes()
        self.audio_engine.all_notes_off()
        self.audio_engine.seek(start_sec)
        self.btn_play.setText("▶ 再生")
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
            self._stepup_running = False
            self.chk_stepup.blockSignals(True)
            self.chk_stepup.setChecked(False)
            self.chk_stepup.blockSignals(False)
            self.user_settings["stepup_enabled"] = False
            self.lbl_status_msg.setText(f"⏩ 速度: {val}% (ステップアップ練習を解除しました)")
        self._save_current_settings()

    def _adjust_speed(self, delta: int):
        new_val = max(50, min(200, self.speed_slider.value() + delta))
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

        # 前奏カウントダウンから本編への遷移検知で外部音源を頭出し同期再生
        prev_s = getattr(self, "_prev_sec", 0.0)
        if prev_s < 0.0 <= cur_sec and state == SharedClockBridge.STATE_PLAYING:
            self._sync_ext_audio_playback(True, 0.0)
        waiting_a = getattr(self, "_loop_waiting_for_a_sec", None)
        if waiting_a is not None and prev_s < waiting_a <= cur_sec and state == SharedClockBridge.STATE_PLAYING:
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
            else:
                QMessageBox.warning(self, "録音エラー", "マイク録音デバイスの初期化に失敗しました。\nマイクが接続されているか確認してください。")
        else:
            saved_path, dur = self.audio_recorder.stop_recording(getattr(self, "_cur_rec_output_path", "recordings/take.wav"))
            self.is_recording = False
            self.btn_rec.setText("🔴 録音")
            self.btn_rec.setStyleSheet("")
            self.lbl_rec_status.setText("● 待機中 (上部 [🔴録音] で開始)")
            self.lbl_rec_status.setStyleSheet("color: #94A3B8; font-weight: bold;")

            if saved_path and dur > 0:
                self.last_recorded_path = saved_path
                self.lbl_rec_take.setText(f"録音テイク: {os.path.basename(saved_path)} ({dur:.1f}秒)")
                self.lbl_rec_take.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
                self.btn_rec_listen.setEnabled(True)

                if self.chk_reverb.isChecked():
                    rev_type = self.combo_reverb_type.currentText()
                    wet = self.slider_reverb_wet.value()
                    rev_path = os.path.splitext(saved_path)[0] + "_reverb.wav"
                    apply_harmonica_reverb_numpy(saved_path, rev_path, rev_type, wet)
                    self.lbl_status_msg.setText(f"💾 録音完了＆リバーブ生成: {os.path.basename(saved_path)} ({dur:.1f}秒)")
                else:
                    self.lbl_status_msg.setText(f"💾 録音完了: {os.path.basename(saved_path)} ({dur:.1f}秒)")
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
        """試聴再生中にリバーブ設定（ON/OFF、タイプ、深さ）が変更された際に即座に再生成・反映"""
        if getattr(self, "last_recorded_path", None) and os.path.exists(self.last_recorded_path):
            target_path = self.last_recorded_path
            if self.chk_reverb.isChecked():
                rev_path = os.path.splitext(self.last_recorded_path)[0] + "_reverb.wav"
                apply_harmonica_reverb_numpy(self.last_recorded_path, rev_path, self.combo_reverb_type.currentText(), self.slider_reverb_wet.value())
                if os.path.exists(rev_path):
                    target_path = rev_path
            if self.audition_player.is_playing():
                self.audition_player.play(target_path, volume=self.vol_slider.value() / 100.0)

    def _on_open_rec_folder(self):
        """録音フォルダを開く"""
        rec_dir = get_portable_path("recordings")
        os.makedirs(rec_dir, exist_ok=True)
        import subprocess
        subprocess.Popen(f'explorer "{rec_dir}"')

    def _on_reverb_toggled(self, checked: bool):
        self.reverb_enabled = bool(checked)
        self.user_settings["reverb_enabled"] = self.reverb_enabled
        self._refresh_live_audition_reverb()
        self._save_current_settings()
        self.lbl_status_msg.setText(f"✨ リバーブ: {'有効' if checked else '無効'}")

    def _on_reverb_type_changed(self, r_type: str):
        self.reverb_type = str(r_type)
        self.user_settings["reverb_type"] = self.reverb_type
        self._refresh_live_audition_reverb()
        self._save_current_settings()

    def _on_reverb_slider_changed(self, val: int):
        self.reverb_wet_pct = int(val)
        self.lbl_reverb_wet.setText(f"深さ: {val}%")
        self.user_settings["reverb_wet_pct"] = self.reverb_wet_pct
        self._refresh_live_audition_reverb()
        self._save_current_settings()

    def _on_select_ext_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "伴奏・外部音源を選択", "",
            "オーディオファイル (*.mp3 *.wav *.m4a *.ogg *.flac *.aac);;全ファイル (*)"
        )
        if path:
            self._set_ext_audio(path)

    def _set_ext_audio(self, path: str):
        if not path or not os.path.isfile(path):
            return
        self.ext_audio_path = path
        self.user_settings["ext_audio_path"] = path
        self.lbl_ext_audio.setText(os.path.basename(path))
        self.lbl_ext_audio.setToolTip(path)
        self.lbl_ext_audio.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        self.btn_ext_audition.setEnabled(True)
        self.btn_ext_restart.setEnabled(True)
        self.btn_ext_stop.setEnabled(True)
        self._save_current_song_profile()
        self.lbl_status_msg.setText(f"🎵 伴奏音源を設定しました: {os.path.basename(path)}")
        self._save_current_settings()

    def _on_clear_ext_audio(self):
        self.ext_audio_path = ""
        self.user_settings["ext_audio_path"] = ""
        self.lbl_ext_audio.setText("未選択 (MP3/WAV等をD&D可)")
        self.lbl_ext_audio.setToolTip("")
        self.lbl_ext_audio.setStyleSheet("color: #64748B; font-size: 11px;")
        self.btn_ext_audition.setEnabled(False)
        self.btn_ext_restart.setEnabled(False)
        self.btn_ext_stop.setEnabled(False)
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._save_current_song_profile()
        self.lbl_status_msg.setText("伴奏音源を解除しました")
        self._save_current_settings()

    def _on_ext_mode_changed(self, mode: str):
        self.ext_audio_mode = str(mode)
        self.user_settings["ext_audio_mode"] = self.ext_audio_mode
        if "外部音源のみ" in mode:
            self.audio_engine.set_muted(True)
        else:
            self.audio_engine.set_muted(False)
        self._save_current_settings()

    def _on_ext_vol_changed(self, val: int):
        self.ext_volume = int(val)
        self.lbl_ext_vol.setText(f"{val}%")
        self.user_settings["ext_audio_volume"] = val
        try:
            import pygame
            if pygame.mixer.get_init():
                v = (val / 100.0) * (self.vol_slider.value() / 100.0)
                pygame.mixer.music.set_volume(v)
        except Exception:
            pass
        self._save_current_settings()

    def _on_ext_offset_changed(self, val: int):
        self.ext_offset_ms = int(val)
        self.user_settings["ext_audio_offset_ms"] = val
        self._save_current_song_profile()
        self._save_current_settings()

    def _on_ext_offset_adjust(self, delta_ms: int):
        new_val = self.spin_ext_offset.value() + int(delta_ms)
        self.spin_ext_offset.setValue(max(-5000, min(5000, new_val)))

    def _sync_ext_audio_playback(self, is_playing: bool, target_sec: float = None):
        """外部音源をタイムラインと完全同期再生/一時停止"""
        if not getattr(self, "ext_audio_path", "") or not os.path.isfile(self.ext_audio_path):
            return
        if "外部音源オフ" in getattr(self, "ext_audio_mode", ""):
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass
            return

        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

            cur_sec = self.clock.get_current_base_sec() if target_sec is None else target_sec
            ext_time = max(0.0, cur_sec + self.spin_ext_offset.value() / 1000.0)
            vol = (self.slider_ext_vol.value() / 100.0) * (self.vol_slider.value() / 100.0)

            if is_playing and cur_sec >= 0.0:
                try:
                    pygame.mixer.music.load(self.ext_audio_path)
                    pygame.mixer.music.set_volume(vol)
                    pygame.mixer.music.play(start=ext_time)
                except Exception as e:
                    print(f"[ExtAudio Warning] play failed: {e}")
            else:
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
        except Exception as e:
            print(f"[ExtAudio Warning] sync failed: {e}")

    def _on_ext_audition_play(self):
        """外部音源の頭出し試聴"""
        if not getattr(self, "ext_audio_path", "") or not os.path.isfile(self.ext_audio_path):
            return
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
                self.btn_ext_audition.setText("▶ 試聴")
            else:
                ext_time = max(0.0, self.spin_ext_offset.value() / 1000.0)
                vol = (self.slider_ext_vol.value() / 100.0) * (self.vol_slider.value() / 100.0)
                pygame.mixer.music.load(self.ext_audio_path)
                pygame.mixer.music.set_volume(vol)
                pygame.mixer.music.play(start=ext_time)
                self.btn_ext_audition.setText("⏸ 一時停止")
        except Exception as e:
            print(f"[ExtAudio Audition Error] {e}")

    def _on_ext_audition_restart(self):
        """外部音源を先頭から再生"""
        if not getattr(self, "ext_audio_path", "") or not os.path.isfile(self.ext_audio_path):
            return
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            vol = (self.slider_ext_vol.value() / 100.0) * (self.vol_slider.value() / 100.0)
            pygame.mixer.music.load(self.ext_audio_path)
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(start=0.0)
            self.btn_ext_audition.setText("⏸ 一時停止")
        except Exception as e:
            print(f"[ExtAudio Restart Error] {e}")

    def _on_ext_audition_stop(self):
        """外部音源の試聴停止"""
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
            self.btn_ext_audition.setText("▶ 試聴")
        except Exception:
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
        from video_exporter import OffscreenVisualizerRenderer
        from dialogs import SingleFramePreviewDialog

        cur_sec = max(0.0, self.clock.get_current_base_sec())
        res_text = self.combo_exp_res.currentText()
        if "4K" in res_text:
            w, h = 3840, 2160
        elif "720p" in res_text:
            w, h = 1280, 720
        else:
            w, h = 1920, 1080

        render_settings = {
            "inst_type": self.inst_combo.currentText(),
            "trajectory_mode": self.traj_combo.currentText(),
            "lang_mode": self.lang_combo.currentText(),
            "lever_deco_mode": self.combo_lever.currentText(),
            "note_speed_ratio": self.gl_widget.note_speed_ratio,
            "default_bpm": getattr(self.timeline, "default_bpm", 120.0),
            "show_notes": self.gl_widget.show_notes,
            "show_grid": self.gl_widget.show_grid,
            "show_bar_lines": getattr(self.gl_widget, "show_bar_lines", True),
            "show_grid4": self.combo_grid4.currentText(),
            "show_hole_num": self.gl_widget.show_hole_num,
            "hole_num_style": getattr(self.gl_widget, "hole_num_style", "実機標準 (低音ドット付)"),
            "show_legend": self.gl_widget.show_legend,
            "show_lookahead": self.gl_widget.show_lookahead,
            "use_ring": self.gl_widget.use_ring,
            "show_glow": self.gl_widget.is_glow_on,
            "note_opacity": self.slider_op.value(),
            "color_blow": self.gl_widget.color_blow.name() if hasattr(self.gl_widget, "color_blow") else "#FF9900",
            "color_draw": self.gl_widget.color_draw.name() if hasattr(self.gl_widget, "color_draw") else "#00FFFF",
            "canvas_bg_color": self.combo_exp_bg.currentText() if "クロマキー" in self.combo_exp_style.currentText() else "#0d0d0d",
            "export_style": self.combo_exp_style.currentText(),
            "skin_enabled": self.chk_skin.isChecked(),
            "bg_image_path": self.user_settings.get("bg_image_path", ""),
            "bg_fit_mode": self.combo_bg_fit.currentText(),
            "bg_rotation": self.bg_rotation_deg,
            "bg_dim_ratio": self.slider_bg_dim.value(),
            "bg_image_enabled": self.chk_bg_enable.isChecked() if hasattr(self, "chk_bg_enable") else True,
        }

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

        from video_exporter import check_ffmpeg_available, VideoExportThread
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

        # 解像度設定
        res_text = self.combo_exp_res.currentText()
        if "4K" in res_text:
            w, h = 3840, 2160
        elif "720p" in res_text:
            w, h = 1280, 720
        else:
            w, h = 1920, 1080

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

        # レンダラー向け設定ディクト
        render_settings = {
            "inst_type": self.inst_combo.currentText(),
            "trajectory_mode": self.traj_combo.currentText(),
            "lang_mode": self.lang_combo.currentText(),
            "lever_deco_mode": self.combo_lever.currentText(),
            "note_speed_ratio": self.gl_widget.note_speed_ratio,
            "default_bpm": getattr(self.timeline, "default_bpm", 120.0),
            "show_notes": self.gl_widget.show_notes,
            "show_grid": self.gl_widget.show_grid,
            "show_bar_lines": getattr(self.gl_widget, "show_bar_lines", True),
            "show_grid4": self.combo_grid4.currentText(),
            "show_hole_num": self.gl_widget.show_hole_num,
            "hole_num_style": getattr(self.gl_widget, "hole_num_style", "実機標準 (低音ドット付)"),
            "show_legend": self.gl_widget.show_legend,
            "show_lookahead": self.gl_widget.show_lookahead,
            "use_ring": self.gl_widget.use_ring,
            "show_glow": self.gl_widget.is_glow_on,
            "note_opacity": self.slider_op.value(),
            "color_blow": self.gl_widget.color_blow.name() if hasattr(self.gl_widget, "color_blow") else "#FF9900",
            "color_draw": self.gl_widget.color_draw.name() if hasattr(self.gl_widget, "color_draw") else "#00FFFF",
            "canvas_bg_color": self.combo_exp_bg.currentText() if "クロマキー" in self.combo_exp_style.currentText() else "#0d0d0d",
            "export_style": self.combo_exp_style.currentText(),
            "skin_enabled": self.chk_skin.isChecked(),
            "bg_image_path": self.user_settings.get("bg_image_path", ""),
            "bg_fit_mode": self.combo_bg_fit.currentText(),
            "bg_rotation": self.bg_rotation_deg,
            "bg_dim_ratio": self.slider_bg_dim.value(),
            "bg_image_enabled": self.chk_bg_enable.isChecked() if hasattr(self, "chk_bg_enable") else True,
        }

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
            "ext_audio_offset_ms": self.spin_ext_offset.value(),
            "ext_audio_vol_pct": float(self.slider_ext_vol.value()),
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



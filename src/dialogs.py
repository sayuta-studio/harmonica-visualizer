# -*- coding: utf-8 -*-
"""
v3.0/dialogs.py
Chromatic Harmonica Visualizer v3.0 - モーダルダイアログ群
- HarmonicaSettingsDialog: 外観テーマ・装飾・練習・音響の総合設定
- PartSelectDialog: MIDI全トラック一覧・主旋律トラック選定
"""

import os
import sys
import time
import copy
import project_manager
from PyQt6.QtCore import Qt, QRectF, QUrl, QTimer
from PyQt6.QtGui import QColor, QPixmap, QImage, QPainter, QPen, QBrush, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QPushButton, QComboBox, QSlider, QSpinBox, QAbstractSpinBox, QCheckBox, QColorDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup,
    QFrame, QMessageBox, QLineEdit, QGroupBox, QScrollArea, QProgressBar, QAbstractItemView, QInputDialog, QFileDialog, QSizePolicy
)

from settings_manager import THEME_PRESETS, DEFAULT_SETTINGS, get_fresh_default_settings, get_fresh_default_practice_visual
from config import get_portable_path
from midi_timeline import get_gm_instrument_name
from audio_engine import AuditionPlayer, synthesize_midi_to_wav


def confirm_dialog(parent, title: str, text: str, default_yes: bool = False) -> bool:
    """日本語「はい」「いいえ」ボタン付きの統一確認ダイアログ"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle(title)
    msg.setText(text)
    btn_yes = msg.addButton("はい", QMessageBox.ButtonRole.YesRole)
    btn_no = msg.addButton("いいえ", QMessageBox.ButtonRole.NoRole)
    msg.setDefaultButton(btn_yes if default_yes else btn_no)
    msg.exec()
    return msg.clickedButton() == btn_yes


class HarmonicaSettingsDialog(QDialog):
    """システム環境設定ダイアログ (Ver.4.0)"""

    def __init__(self, current_settings: dict, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.setWindowTitle("システム環境設定 (System Preferences)")
        self.resize(740, 680)
        self.setModal(True)

        self.settings = copy.deepcopy(current_settings)
        self.initial_settings = copy.deepcopy(current_settings)

        self._init_ui()
        self._load_values()
        if 0 <= initial_tab < self.tabs.count():
            self.tabs.setCurrentIndex(initial_tab)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget(self)

        # -----------------------------------------------------------------
        # タブ 1: 🔊 音響・録音デバイス
        # -----------------------------------------------------------------
        tab_audio = QWidget()
        v_audio = QVBoxLayout(tab_audio)
        v_audio.setSpacing(10)

        v_audio.addWidget(QLabel("<b>【ガイドMIDI音源・同期】</b>"))
        row_synth = QHBoxLayout()
        row_synth.addWidget(QLabel("MIDI再生エンジン:"))
        self.combo_synth = QComboBox(self)
        self.combo_synth.addItems(["Windows標準MIDI (推奨)", "内蔵軽量シンセ (遅延0ms)"])
        row_synth.addWidget(self.combo_synth)
        row_synth.addStretch()
        v_audio.addLayout(row_synth)

        # 主旋律固定・メトロノーム設定は練習タブ・パートダイアログに一本化

        v_audio.addSpacing(10)
        v_audio.addWidget(QLabel("<b>【マイク録音・オーディオ設定】</b>"))

        row_ch = QHBoxLayout()
        row_ch.addWidget(QLabel("録音チャンネル数:"))
        self.combo_rec_channels = QComboBox(self)
        self.combo_rec_channels.addItems(["モノラル (1ch・DAW編集向き)", "ステレオ (2ch)"])
        row_ch.addWidget(self.combo_rec_channels)
        row_ch.addStretch()
        v_audio.addLayout(row_ch)

        row_offset = QHBoxLayout()
        row_offset.addWidget(QLabel("録音ズレ補正初期値:"))
        self.spin_rec_offset = QSpinBox(self)
        self.spin_rec_offset.setRange(-500, 500)
        self.spin_rec_offset.setSingleStep(10)
        self.spin_rec_offset.setSuffix(" ms")
        self.spin_rec_offset.setToolTip("録音開始時のレイテンシー補正デフォルト値 (通常0ms〜+80ms)")
        row_offset.addWidget(self.spin_rec_offset)
        row_offset.addStretch()
        v_audio.addLayout(row_offset)

        v_audio.addSpacing(10)
        gb_startup = QGroupBox("🚀 起動時の初期化設定（前回終了時の状態リセット）")
        v_startup = QVBoxLayout(gb_startup)
        v_startup.setSpacing(6)
        self.chk_reset_speed = QCheckBox("再生速度（テンポ）を毎回 100% にリセットして起動する", self)
        self.chk_reset_metro = QCheckBox("メトロノーム・拍子設定を毎回 標準（OFF・4/4拍子）にリセットして起動する", self)
        self.chk_reset_countin = QCheckBox("開始カウント（前奏）を毎回 1小節 にリセットして起動する", self)
        v_startup.addWidget(self.chk_reset_speed)
        v_startup.addWidget(self.chk_reset_metro)
        v_startup.addWidget(self.chk_reset_countin)
        v_audio.addWidget(gb_startup)

        v_audio.addStretch()
        self.tabs.addTab(tab_audio, "🔊 音響・録音デバイス")

        # -----------------------------------------------------------------
        # タブ 2: 🎨 練習画面・本体スキン設定 (フルビジュアル設定統合: 課題30)
        # -----------------------------------------------------------------
        tab_skin_practice = QWidget()
        v_sp_outer = QVBoxLayout(tab_skin_practice)
        v_sp_outer.setContentsMargins(4, 4, 4, 4)

        scroll_sp = QScrollArea()
        scroll_sp.setWidgetResizable(True)
        scroll_sp.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_sp = QWidget()
        v_sp = QVBoxLayout(content_sp)
        v_sp.setContentsMargins(8, 8, 8, 8)
        v_sp.setSpacing(10)

        # ① 🎵 演奏・ノーツ表示 (動画制作画面アコーディオンと完全統一)
        gb_notes = QGroupBox("🎵 1. 演奏・ノーツ表示")
        v_notes = QVBoxLayout(gb_notes)
        v_notes.setSpacing(6)

        r_traj = QHBoxLayout()
        r_traj.addWidget(QLabel("ノーツ軌道:"))
        self.pv_combo_traj = QComboBox(self)
        self.pv_combo_traj.addItems(["3段階 (練習標準)", "2段階 (ビジュアル)", "垂直落下 (クラシック)"])
        r_traj.addWidget(self.pv_combo_traj, stretch=1)

        r_traj.addSpacing(10)
        r_traj.addWidget(QLabel("音名表記:"))
        self.pv_combo_lang = QComboBox(self)
        self.pv_combo_lang.addItems(["ドレミ", "CDE"])
        r_traj.addWidget(self.pv_combo_lang, stretch=1)
        v_notes.addLayout(r_traj)
        v_sp.addWidget(gb_notes)

        # ② 🎨 カラーテーマ ＆ ノーツ装飾
        gb_color = QGroupBox("🎨 2. カラーテーマ ＆ ノーツ装飾")
        v_color = QVBoxLayout(gb_color)
        v_color.setSpacing(6)

        r_thm = QHBoxLayout()
        r_thm.addWidget(QLabel("配色テーマ:"))
        self.pv_combo_theme = QComboBox(self)
        self.pv_combo_theme.addItems(["ノーマル", "サクラ", "クールネオン", "モノクロ", "カスタム"])
        self.pv_combo_theme.currentTextChanged.connect(self._on_pv_theme_combo_changed)
        r_thm.addWidget(self.pv_combo_theme, stretch=1)

        r_thm.addSpacing(10)
        r_thm.addWidget(QLabel("吹音:"))
        self.btn_pv_blow_color = QPushButton("■ 吹", self)
        self.btn_pv_blow_color.setFixedWidth(64)
        self.btn_pv_blow_color.clicked.connect(self._pv_pick_blow_color)
        r_thm.addWidget(self.btn_pv_blow_color)

        r_thm.addWidget(QLabel("吸音:"))
        self.btn_pv_draw_color = QPushButton("■ 吸", self)
        self.btn_pv_draw_color.setFixedWidth(64)
        self.btn_pv_draw_color.clicked.connect(self._pv_pick_draw_color)
        r_thm.addWidget(self.btn_pv_draw_color)
        v_color.addLayout(r_thm)

        r_lev = QHBoxLayout()
        r_lev.addWidget(QLabel("レバーON装飾:"))
        self.pv_combo_lever = QComboBox(self)
        self.pv_combo_lever.addItems(["センターライン (芯線)", "センターライン2本 (ダブル芯線)", "センター半割 (スリット)", "サイドライン (明暗適応)", "装飾なし"])
        r_lev.addWidget(self.pv_combo_lever, stretch=1)

        r_lev.addSpacing(10)
        r_lev.addWidget(QLabel("ノーツ不透明度:"))
        self.pv_slider_opacity = QSlider(Qt.Orientation.Horizontal, self)
        self.pv_slider_opacity.setRange(20, 100)
        self.pv_lbl_opacity_val = QLabel("100%", self)
        self.pv_lbl_opacity_val.setMinimumWidth(36)
        self.pv_slider_opacity.valueChanged.connect(lambda v: self.pv_lbl_opacity_val.setText(f"{v}%"))
        r_lev.addWidget(self.pv_slider_opacity, stretch=1)
        r_lev.addWidget(self.pv_lbl_opacity_val)
        v_color.addLayout(r_lev)
        v_sp.addWidget(gb_color)

        # ③ ☑️ 表示要素 ON/OFF ＆ 穴番号 (動画側アコーディオンと同一のくくり)
        gb_elem = QGroupBox("☑️ 3. 表示要素 ON/OFF ＆ 穴番号")
        v_elem = QVBoxLayout(gb_elem)
        v_elem.setSpacing(6)

        r_el1 = QHBoxLayout()
        self.pv_chk_notes = QCheckBox("落下ノーツを表示", self)
        self.pv_chk_lookahead = QCheckBox("ノーツ直上音名を表示", self)
        self.pv_chk_grid = QCheckBox("レーンガイド線を表示", self)
        self.pv_chk_bar_lines = QCheckBox("小節線を表示", self)
        r_el1.addWidget(self.pv_chk_notes)
        r_el1.addWidget(self.pv_chk_lookahead)
        r_el1.addWidget(self.pv_chk_grid)
        r_el1.addWidget(self.pv_chk_bar_lines)
        v_elem.addLayout(r_el1)

        r_el2 = QHBoxLayout()
        self.pv_chk_hole_num = QCheckBox("穴番号を表示", self)
        self.pv_chk_hole_num.setVisible(False)
        self.pv_chk_ring = QCheckBox("判定リング (吹吸枠)", self)
        self.pv_chk_glow = QCheckBox("発光エフェクト (Glow)", self)
        self.pv_chk_legend = QCheckBox("吹吸凡例を表示", self)
        # 穴番号はスタイルコンボ（非表示）に一本化
        r_el2.addWidget(self.pv_chk_ring)
        r_el2.addWidget(self.pv_chk_glow)
        r_el2.addWidget(self.pv_chk_legend)
        v_elem.addLayout(r_el2)

        # 穴番号表記 ＆ 穴下ノート表示（動画側アコーディオンと同一のくくり・順序）
        r_sub = QHBoxLayout()
        r_sub.addWidget(QLabel("穴番号表記:"))
        self.pv_combo_hole_style = QComboBox(self)
        self.pv_combo_hole_style.addItems(["実機標準 (低音ドット付)", "通し番号 (1〜)", "非表示"])
        r_sub.addWidget(self.pv_combo_hole_style, stretch=1)

        r_sub.addSpacing(10)
        r_sub.addWidget(QLabel("穴下ノート表示:"))
        self.pv_combo_grid4 = QComboBox(self)
        self.pv_combo_grid4.addItems(["4音グリッド表示", "1音表示 (従来)", "非表示"])
        r_sub.addWidget(self.pv_combo_grid4, stretch=1)
        v_elem.addLayout(r_sub)

        v_sp.addWidget(gb_elem)

        # ④ 🖼️ 背景画像 ＆ 減光 (コントラスト) (動画側と完全統一)
        gb_bg = QGroupBox("🖼️ 4. 背景画像 ＆ 減光 (コントラスト)")
        v_bg = QVBoxLayout(gb_bg)
        v_bg.setSpacing(6)

        # 課題40: 「背景画像有効化」チェックボックスは廃止し、配置コンボの「非表示」へ一本化（内部互換用に非表示保持）
        self.pv_chk_bg_enable = QCheckBox("背景画像を有効化", self)
        self.pv_chk_bg_enable.setVisible(False)

        r_bg1 = QHBoxLayout()
        self.pv_lbl_bg_path = QLabel("未設定 (黒背景)", self)
        self.pv_lbl_bg_path.setStyleSheet("color: #888888; font-size: 11px;")
        r_bg1.addWidget(self.pv_lbl_bg_path, stretch=1)
        btn_pv_bg_browse = QPushButton("📁 画像選択...", self)
        btn_pv_bg_browse.clicked.connect(self._pv_choose_bg_image)
        r_bg1.addWidget(btn_pv_bg_browse)
        btn_pv_bg_clear = QPushButton("✕ 解除", self)
        btn_pv_bg_clear.clicked.connect(self._pv_clear_bg_image)
        r_bg1.addWidget(btn_pv_bg_clear)
        v_bg.addLayout(r_bg1)

        r_bg2 = QHBoxLayout()
        r_bg2.addWidget(QLabel("配置:"))
        self.pv_combo_bg_fit = QComboBox(self)
        self.pv_combo_bg_fit.addItems([
            "非表示 (背景画像オフ)",
            "中央トリミング (画面いっぱい)",
            "画面内に収める (全体表示)",
            "横幅に合わせる",
            "縦幅に合わせる",
            "画面に引き伸ばす (比率無視)"
        ])
        r_bg2.addWidget(self.pv_combo_bg_fit, stretch=1)

        r_bg2.addSpacing(10)
        r_bg2.addWidget(QLabel("回転:"))
        self.pv_combo_bg_rot = QComboBox(self)
        self.pv_combo_bg_rot.addItems(["0° (標準)", "90° (右回転)", "180° (上下反転)", "270° (左回転)"])
        r_bg2.addWidget(self.pv_combo_bg_rot)
        v_bg.addLayout(r_bg2)

        r_bg3 = QHBoxLayout()
        r_bg3.addWidget(QLabel("暗さ (減光):"))
        self.pv_slider_bg_dim = QSlider(Qt.Orientation.Horizontal, self)
        self.pv_slider_bg_dim.setRange(0, 100)
        self.pv_lbl_bg_dim_val = QLabel("60%", self)
        self.pv_lbl_bg_dim_val.setMinimumWidth(36)
        self.pv_slider_bg_dim.valueChanged.connect(lambda v: self.pv_lbl_bg_dim_val.setText(f"{v}%"))
        r_bg3.addWidget(self.pv_slider_bg_dim, stretch=1)
        r_bg3.addWidget(self.pv_lbl_bg_dim_val)
        v_bg.addLayout(r_bg3)

        v_sp.addWidget(gb_bg)

        # ⑤ 🎷 ハーモニカ本体スキン
        gb_skin = QGroupBox("🎷 5. ハーモニカ本体スキン")
        v_skin = QVBoxLayout(gb_skin)
        v_skin.setSpacing(6)

        self.chk_skin_enabled = QCheckBox("カスタム表示適用", self)
        self.chk_skin_enabled.setToolTip("ハーモニカ本体のマウスピース・カバープレート・スライドレバーのカスタムスキンを表示")
        self.chk_skin_enabled.toggled.connect(self._on_skin_toggled)
        v_skin.addWidget(self.chk_skin_enabled)

        row_skin_file = QHBoxLayout()
        self.lbl_skin_path = QLabel("スキン: 標準メタル / シルバー", self)
        self.lbl_skin_path.setStyleSheet("color: #888888; font-size: 11px;")
        row_skin_file.addWidget(self.lbl_skin_path, stretch=1)

        self.btn_select_skin = QPushButton("🎨 スキン選択...", self)
        self.btn_select_skin.clicked.connect(self._choose_skin_image)
        row_skin_file.addWidget(self.btn_select_skin)

        self.btn_clear_skin = QPushButton("↺ 初期化", self)
        self.btn_clear_skin.setToolTip("標準のメタルカバー・シルバーレバーに戻す")
        self.btn_clear_skin.clicked.connect(self._clear_skin_image)
        row_skin_file.addWidget(self.btn_clear_skin)
        v_skin.addLayout(row_skin_file)
        v_sp.addWidget(gb_skin)

        v_sp.addStretch()
        scroll_sp.setWidget(content_sp)
        v_sp_outer.addWidget(scroll_sp)
        self.tabs.addTab(tab_skin_practice, "🎨 練習画面・本体スキン設定")

        # -----------------------------------------------------------------
        # タブ 3: 📁 プロジェクト・保存先管理
        # -----------------------------------------------------------------
        tab_project = QWidget()
        v_proj = QVBoxLayout(tab_project)
        v_proj.setSpacing(10)

        v_proj.addWidget(QLabel("<b>【1. プロジェクトフォルダーの作成先 (親フォルダー)】</b>"))
        v_proj.addWidget(QLabel("読み込んだMIDI曲ごとに固有フォルダーが自動作成される親ディレクトリ："))
        self.edit_base_path = QLineEdit(self)
        self.edit_base_path.setReadOnly(True)
        self.edit_base_path.setText(os.path.abspath(get_portable_path("projects")))
        v_proj.addWidget(self.edit_base_path)

        btn_proj_dir = QPushButton("📂 プロジェクト一覧フォルダー (projects/) を直接開く", self)
        btn_proj_dir.clicked.connect(lambda: self._open_dir(get_portable_path("projects")))
        v_proj.addWidget(btn_proj_dir)

        v_proj.addSpacing(8)
        v_proj.addWidget(QLabel("<b>【2. プロジェクトフォルダー内の自動生成構造 (子フォルダー)】</b>"))
        tree_frame = QFrame(self)
        tree_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 8px; }")
        l_tree = QVBoxLayout(tree_frame)
        tree_label = QLabel(
            "📁 <b>projects / &lt;各MIDI曲名フォルダー&gt; /</b><br>"
            "&nbsp;&nbsp;├── 📂 <b>source/</b> &nbsp;&nbsp;<span style='color:#94A3B8;'>（読み込んだMIDI原本の自動バックアップ）</span><br>"
            "&nbsp;&nbsp;├── 📂 <b>takes/</b> &nbsp;&nbsp;&nbsp;<span style='color:#94A3B8;'>（マイク録音した演奏テイク WAV）</span><br>"
            "&nbsp;&nbsp;├── 📂 <b>audio/</b> &nbsp;&nbsp;&nbsp;<span style='color:#94A3B8;'>（外部伴奏音源 WAV/MP3）</span><br>"
            "&nbsp;&nbsp;├── 📂 <b>exports/</b> &nbsp;<span style='color:#94A3B8;'>（書き出した完成動画 MP4/MOV）</span><br>"
            "&nbsp;&nbsp;└── 📄 <b>project.json</b> <span style='color:#94A3B8;'>（曲別の運指パターン・移調・同期設定）</span>"
        )
        tree_label.setStyleSheet("font-size: 12px; line-height: 1.5;")
        l_tree.addWidget(tree_label)
        v_proj.addWidget(tree_frame)

        self.btn_cur_song_dir = QPushButton("📂 現在開いている楽曲の固有フォルダーを開く", self)
        self.btn_cur_song_dir.clicked.connect(self._on_open_current_song_dir)
        v_proj.addWidget(self.btn_cur_song_dir)

        v_proj.addStretch()
        self.tabs.addTab(tab_project, "📁 プロジェクト・保存先管理")

        # -----------------------------------------------------------------
        # タブ 4: 🎬 初期プリセット一覧
        # -----------------------------------------------------------------
        tab_presets = QWidget()
        v_presets = QVBoxLayout(tab_presets)
        v_presets.setSpacing(10)

        v_presets.addWidget(QLabel("<b>【公式5大動画プリセット比較マトリクス】</b>"))
        v_presets.addWidget(QLabel("各プリセットの主要パラメータ一覧です。制作用途に合わせて最適なプリセットを選択できます。"))

        self.table_presets = QTableWidget(5, 7, self)
        self.table_presets.setHorizontalHeaderLabels(["初期プリセット名", "画面比率", "ノーツ軌道", "音名表記", "穴下表示", "不透明度", "背景減光"])
        self.table_presets.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_presets.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_presets.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_presets.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v_presets.addWidget(self.table_presets)

        r_pre_btn = QHBoxLayout()
        self.btn_restore_factory_presets = QPushButton("↺ 公式初期プリセットを工場出荷時の設定に一括復元", self)
        self.btn_restore_factory_presets.setToolTip("5大プリセットの変更内容をリセットし、初期状態に復元します")
        self.btn_restore_factory_presets.clicked.connect(self._on_restore_factory_presets)
        r_pre_btn.addWidget(self.btn_restore_factory_presets)
        r_pre_btn.addStretch()
        v_presets.addLayout(r_pre_btn)

        self.tabs.addTab(tab_presets, "🎬 初期プリセット一覧")

        main_layout.addWidget(self.tabs)

        # -----------------------------------------------------------------
        # 最下部: ボタンバー
        # -----------------------------------------------------------------
        btn_layout = QHBoxLayout()
        self.btn_reset = QPushButton("初期設定に戻す", self)
        self.btn_reset.clicked.connect(self._on_reset_defaults)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch()

        self.btn_save = QPushButton("💾 保存して閉じる", self)
        self.btn_save.setObjectName("playBtn")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("キャンセル", self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _on_open_current_song_dir(self):
        p_dir = project_manager.get_active_project_dir()
        if not p_dir:
            from config import get_portable_path
            p_dir = get_portable_path("projects/_demo_chromatic")
        self._open_dir(p_dir)

    def _open_dir(self, path: str):
        if not path:
            from config import get_portable_path
            path = get_portable_path("projects/_demo_chromatic")
        try:
            os.makedirs(path, exist_ok=True)
            if os.name == "nt":
                os.startfile(os.path.abspath(path))
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path)))
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"フォルダを開けませんでした:\n{e}")

    def _update_skin_summary_label(self):
        mp = self.settings.get("skin_mouthpiece_path", "")
        lo = self.settings.get("skin_lever_off_path", "")
        if mp and os.path.exists(mp):
            mp_name = os.path.basename(mp).replace("マウスピース_", "").replace(".png", "")
            lo_name = os.path.basename(lo).replace("レバーオフ_", "").replace(".png", "") if lo else "標準"
            self.lbl_skin_path.setText(f"本体: {mp_name} / レバー: {lo_name}")
            self.lbl_skin_path.setToolTip(f"本体: {mp}\nレバー: {lo}")
        else:
            self.lbl_skin_path.setText("スキン: 標準メタル / シルバー")
            self.lbl_skin_path.setToolTip("内蔵標準スキン")

    def _update_pv_color_buttons(self):
        self.btn_pv_blow_color.setStyleSheet(
            f"background-color: {self._pv_blow_color}; color: #FFFFFF; font-weight: bold; border: 1px solid #FFFFFF;"
        )
        self.btn_pv_draw_color.setStyleSheet(
            f"background-color: {self._pv_draw_color}; color: #FFFFFF; font-weight: bold; border: 1px solid #FFFFFF;"
        )

    def _pv_pick_blow_color(self):
        c = QColorDialog.getColor(QColor(self._pv_blow_color), self, "吹音（ブロー）のカスタム色を選択")
        if c.isValid():
            self._pv_blow_color = c.name()
            self._update_pv_color_buttons()
            self.pv_combo_theme.blockSignals(True)
            self.pv_combo_theme.setCurrentText("カスタム")
            self.pv_combo_theme.blockSignals(False)

    def _pv_pick_draw_color(self):
        c = QColorDialog.getColor(QColor(self._pv_draw_color), self, "吸音（ドロー）のカスタム色を選択")
        if c.isValid():
            self._pv_draw_color = c.name()
            self._update_pv_color_buttons()
            self.pv_combo_theme.blockSignals(True)
            self.pv_combo_theme.setCurrentText("カスタム")
            self.pv_combo_theme.blockSignals(False)

    def _on_pv_theme_combo_changed(self, t_name: str):
        if t_name in THEME_PRESETS:
            b_col, d_col = THEME_PRESETS[t_name]
            self._pv_blow_color = b_col
            self._pv_draw_color = d_col
            self._update_pv_color_buttons()

    def _pv_choose_bg_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "練習画面の背景画像を選択", "", "画像 (*.png *.jpg *.jpeg *.bmp *.webp);;全ファイル (*)")
        if f:
            self._pv_bg_path = f
            self.pv_lbl_bg_path.setText(os.path.basename(f))
            self.pv_lbl_bg_path.setToolTip(f)
            self.pv_chk_bg_enable.setChecked(True)
            if self.pv_combo_bg_fit.currentText().startswith("非表示"):
                self.pv_combo_bg_fit.setCurrentText("中央トリミング (画面いっぱい)")

    def _pv_clear_bg_image(self):
        self._pv_bg_path = ""
        self.pv_lbl_bg_path.setText("未設定 (黒背景)")
        self.pv_lbl_bg_path.setToolTip("")
        self.pv_combo_bg_fit.setCurrentText("非表示 (背景画像オフ)")
        self.pv_chk_bg_enable.setChecked(False)

    def _choose_skin_image(self):
        dlg = SkinSelectDialog(self.settings, parent=self)
        if dlg.exec():
            res = dlg.get_selected_skins()
            self.settings["skin_mouthpiece_path"] = res["mouthpiece_path"]
            self.settings["skin_lever_off_path"] = res["lever_off_path"]
            self.settings["skin_lever_on_path"] = res["lever_on_path"]
            self.settings["skin_enabled"] = res["skin_enabled"]
            self.chk_skin_enabled.setChecked(res["skin_enabled"])
            self._update_skin_summary_label()

    def _clear_skin_image(self):
        skins_dir = get_portable_path("skins")
        self.settings["skin_mouthpiece_path"] = os.path.join(skins_dir, "マウスピース_メタル.png")
        self.settings["skin_lever_off_path"] = os.path.join(skins_dir, "レバーオフ_シルバー.png")
        self.settings["skin_lever_on_path"] = os.path.join(skins_dir, "レバーオン_シルバー.png")
        self.settings["skin_enabled"] = True
        self.chk_skin_enabled.setChecked(True)
        self._update_skin_summary_label()

    def _on_skin_toggled(self, checked: bool):
        self.btn_select_skin.setEnabled(checked)
        self.btn_clear_skin.setEnabled(checked)

    def _load_values(self):
        s = self.settings
        synth_val = s.get("synth_engine") or s.get("synth_mode") or s.get("guide_audio_engine", "Windows標準MIDI (推奨)")
        if "内蔵" in str(synth_val):
            self.combo_synth.setCurrentText("内蔵軽量シンセ (遅延0ms)")
        else:
            self.combo_synth.setCurrentText("Windows標準MIDI (推奨)")

        ch = int(s.get("rec_channels", 1))
        self.combo_rec_channels.setCurrentIndex(0 if ch == 1 else 1)
        self.spin_rec_offset.setValue(int(s.get("rec_offset_ms", 0)))

        self.chk_reset_speed.setChecked(bool(s.get("reset_speed_on_startup", True)))
        self.chk_reset_metro.setChecked(bool(s.get("reset_metro_on_startup", True)))
        self.chk_reset_countin.setChecked(bool(s.get("reset_countin_on_startup", False)))

        skin_en = bool(s.get("skin_enabled", True))
        self.chk_skin_enabled.setChecked(skin_en)
        self._update_skin_summary_label()
        self._on_skin_toggled(skin_en)

        # 練習用ビジュアル設定のロード
        pv = s.get("practice_visual", {})
        self.pv_combo_traj.setCurrentText(pv.get("trajectory_mode", "3段階 (練習標準)"))
        self.pv_combo_lang.setCurrentText(pv.get("lang_mode", "ドレミ"))
        self.pv_combo_grid4.setCurrentText(pv.get("grid4_mode", "4音グリッド表示"))
        hole_style = pv.get("hole_num_style", "実機標準 (低音ドット付)")
        if pv.get("show_hole_num") is False:
            hole_style = "非表示"
        self.pv_combo_hole_style.setCurrentText(hole_style)

        self.pv_combo_theme.blockSignals(True)
        self.pv_combo_theme.setCurrentText(pv.get("color_theme", "ノーマル"))
        self.pv_combo_theme.blockSignals(False)
        self._pv_blow_color = pv.get("color_blow", "#FF5500")
        self._pv_draw_color = pv.get("color_draw", "#00BFFF")
        self._update_pv_color_buttons()

        self.pv_combo_lever.setCurrentText(pv.get("lever_deco_mode", s.get("lever_deco_mode", "センターライン (芯線)")))
        op = int(pv.get("note_opacity", s.get("note_opacity", 100)))
        self.pv_slider_opacity.setValue(op)
        self.pv_lbl_opacity_val.setText(f"{op}%")

        self.pv_chk_notes.setChecked(bool(pv.get("show_notes", True)))
        self.pv_chk_lookahead.setChecked(bool(pv.get("show_lookahead", True)))
        self.pv_chk_grid.setChecked(bool(pv.get("show_grid", True)))
        self.pv_chk_bar_lines.setChecked(bool(pv.get("show_bar_lines", True)))
        self.pv_chk_hole_num.setChecked(bool(pv.get("show_hole_num", True)))
        self.pv_chk_ring.setChecked(bool(pv.get("show_ring", True)))
        self.pv_chk_glow.setChecked(bool(pv.get("show_glow", True)))
        self.pv_chk_legend.setChecked(bool(pv.get("show_legend", True)))

        bg_en = bool(pv.get("bg_image_enabled", True))
        cur_fit = pv.get("bg_fit_mode", "中央トリミング (画面いっぱい)")
        if not bg_en or str(cur_fit).startswith("非表示"):
            self.pv_combo_bg_fit.setCurrentText("非表示 (背景画像オフ)")
        elif "引き伸ば" in str(cur_fit) or "引き延ば" in str(cur_fit):
            self.pv_combo_bg_fit.setCurrentText("画面に引き伸ばす (比率無視)")
        elif "全体" in str(cur_fit) or "収める" in str(cur_fit):
            self.pv_combo_bg_fit.setCurrentText("画面内に収める (全体表示)")
        elif cur_fit in [self.pv_combo_bg_fit.itemText(i) for i in range(self.pv_combo_bg_fit.count())]:
            self.pv_combo_bg_fit.setCurrentText(cur_fit)
        else:
            self.pv_combo_bg_fit.setCurrentText("中央トリミング (画面いっぱい)")
        self.pv_chk_bg_enable.setChecked("非表示" not in self.pv_combo_bg_fit.currentText())

        self._pv_bg_path = pv.get("bg_image_path", "")
        self.pv_lbl_bg_path.setText(os.path.basename(self._pv_bg_path) if self._pv_bg_path else "未設定 (黒背景)")
        self.pv_lbl_bg_path.setToolTip(self._pv_bg_path)
        dim = int(pv.get("bg_dim_ratio", 60))
        self.pv_slider_bg_dim.setValue(dim)
        self.pv_lbl_bg_dim_val.setText(f"{dim}%")
        rot_deg = int(pv.get("bg_rotation", 0))
        rot_map = {0: "0° (標準)", 90: "90° (右回転)", 180: "180° (上下反転)", 270: "270° (左回転)"}
        self.pv_combo_bg_rot.setCurrentText(rot_map.get(rot_deg, "0° (標準)"))

        self._refresh_presets_table()

    def _on_reset_defaults(self):
        if confirm_dialog(self, "確認", "全設定を初期状態にリセットしますか？", default_yes=False):
            self.settings = get_fresh_default_settings()
            self._pv_bg_path = ""
            self._load_values()

    def _on_save_clicked(self):
        s = self.settings
        synth_choice = self.combo_synth.currentText()
        s["synth_engine"] = synth_choice
        s["synth_mode"] = synth_choice
        s["guide_audio_engine"] = synth_choice
        s["force_harmonica"] = bool(self.initial_settings.get("force_harmonica", True))
        s["metronome_mode"] = self.initial_settings.get("metronome_mode", "標準（頭拍強調）")

        s["rec_channels"] = 1 if self.combo_rec_channels.currentIndex() == 0 else 2
        s["rec_offset_ms"] = self.spin_rec_offset.value()

        s["reset_speed_on_startup"] = self.chk_reset_speed.isChecked()
        s["reset_metro_on_startup"] = self.chk_reset_metro.isChecked()
        s["reset_countin_on_startup"] = self.chk_reset_countin.isChecked()

        s["skin_enabled"] = self.chk_skin_enabled.isChecked()
        s["skin_mouthpiece_path"] = self.settings.get("skin_mouthpiece_path", "")
        s["skin_lever_off_path"] = self.settings.get("skin_lever_off_path", "")
        s["skin_lever_on_path"] = self.settings.get("skin_lever_on_path", "")

        s["stepup_enabled"] = bool(self.initial_settings.get("stepup_enabled", False))
        s["stepup_start_pct"] = int(self.initial_settings.get("stepup_start_pct", 70))
        s["stepup_target_pct"] = int(self.initial_settings.get("stepup_target_pct", 100))
        s["stepup_step_pct"] = int(self.initial_settings.get("stepup_step_pct", 5))

        # 練習画面フルビジュアル設定の保存
        pv = s.setdefault("practice_visual", {})
        pv["trajectory_mode"] = self.pv_combo_traj.currentText()
        pv["lang_mode"] = self.pv_combo_lang.currentText()
        pv["grid4_mode"] = self.pv_combo_grid4.currentText()
        hole_style = self.pv_combo_hole_style.currentText()
        pv["hole_num_style"] = hole_style
        pv["color_theme"] = self.pv_combo_theme.currentText()
        pv["color_blow"] = self._pv_blow_color
        pv["color_draw"] = self._pv_draw_color
        pv["lever_deco_mode"] = self.pv_combo_lever.currentText()
        pv["note_opacity"] = self.pv_slider_opacity.value()

        pv["show_notes"] = self.pv_chk_notes.isChecked()
        pv["show_lookahead"] = self.pv_chk_lookahead.isChecked()
        pv["show_grid"] = self.pv_chk_grid.isChecked()
        pv["show_bar_lines"] = self.pv_chk_bar_lines.isChecked()
        pv["show_hole_num"] = ("非表示" not in hole_style)
        self.pv_chk_hole_num.setChecked(pv["show_hole_num"])
        pv["show_ring"] = self.pv_chk_ring.isChecked()
        pv["show_glow"] = self.pv_chk_glow.isChecked()
        pv["show_legend"] = self.pv_chk_legend.isChecked()

        fit_choice = self.pv_combo_bg_fit.currentText()
        is_bg_on = ("非表示" not in fit_choice)
        pv["bg_image_enabled"] = is_bg_on
        self.pv_chk_bg_enable.setChecked(is_bg_on)
        pv["bg_image_path"] = self._pv_bg_path
        pv["bg_dim_ratio"] = self.pv_slider_bg_dim.value()
        pv["bg_fit_mode"] = fit_choice
        rot_rev = {"0° (標準)": 0, "90° (右回転)": 90, "180° (上下反転)": 180, "270° (左回転)": 270}
        pv["bg_rotation"] = rot_rev.get(self.pv_combo_bg_rot.currentText(), 0)

        pv["skin_enabled"] = self.chk_skin_enabled.isChecked()
        pv["skin_mouthpiece_path"] = self.settings.get("skin_mouthpiece_path", "")
        pv["skin_lever_off_path"] = self.settings.get("skin_lever_off_path", "")
        pv["skin_lever_on_path"] = self.settings.get("skin_lever_on_path", "")

        # 後方互換用トップレベル同期
        s["lever_deco_mode"] = pv["lever_deco_mode"]
        s["note_opacity"] = pv["note_opacity"]
        s["bg_image_path"] = self._pv_bg_path
        s["bg_image_enabled"] = pv["bg_image_enabled"]
        s["trajectory_mode"] = pv["trajectory_mode"]
        s["lang_mode"] = pv["lang_mode"]
        s["grid4_mode"] = pv["grid4_mode"]
        s["show_bar_lines"] = pv["show_bar_lines"]
        s["show_notes"] = pv["show_notes"]
        s["show_lookahead"] = pv["show_lookahead"]
        s["show_grid"] = pv["show_grid"]
        s["show_hole_num"] = pv["show_hole_num"]
        s["color_theme"] = pv["color_theme"]
        s["color_blow"] = pv["color_blow"]
        s["color_draw"] = pv["color_draw"]

        self.accept()

    def _refresh_presets_table(self):
        """公式5大プリセットの一覧テーブルを描画"""
        import settings_manager
        presets_dict = self.settings.get("video_presets", {})
        official_names = list(settings_manager.DEFAULT_VIDEO_PRESETS.keys())
        self.table_presets.setRowCount(len(official_names))

        for row, name in enumerate(official_names):
            p = presets_dict.get(name, settings_manager.DEFAULT_VIDEO_PRESETS[name])
            item_name = QTableWidgetItem(name)
            item_ratio = QTableWidgetItem(str(p.get("aspect_ratio", "16:9")))
            item_traj = QTableWidgetItem(str(p.get("trajectory_mode", "3段階 (練習標準)")))
            item_lang = QTableWidgetItem(str(p.get("lang_mode", "ドレミ")) if p.get("show_lookahead", True) else "非表示")
            item_g4 = QTableWidgetItem(str(p.get("grid4_mode", "非表示")))
            item_op = QTableWidgetItem(f"{p.get('note_opacity', 100)}%")
            item_bg = QTableWidgetItem(f"{p.get('bg_dim_ratio', 60)}%" if p.get("bg_image_enabled", True) else "なし")

            for item in (item_name, item_ratio, item_traj, item_lang, item_g4, item_op, item_bg):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            self.table_presets.setItem(row, 0, item_name)
            self.table_presets.setItem(row, 1, item_ratio)
            self.table_presets.setItem(row, 2, item_traj)
            self.table_presets.setItem(row, 3, item_lang)
            self.table_presets.setItem(row, 4, item_g4)
            self.table_presets.setItem(row, 5, item_op)
            self.table_presets.setItem(row, 6, item_bg)

    def _on_restore_factory_presets(self):
        """公式プリセットを初期値にリセット"""
        msg_text = "公式5大動画プリセットを工場出荷時の標準設定に戻しますか？\n（自作のプリセットはそのまま保持されます）"
        if not confirm_dialog(
            self,
            "初期プリセットの復元",
            msg_text,
            default_yes=False
        ):
            return
        import settings_manager
        if "video_presets" not in self.settings:
            self.settings["video_presets"] = {}
        for k, v in settings_manager.DEFAULT_VIDEO_PRESETS.items():
            self.settings["video_presets"][k] = copy.deepcopy(v)
        self._refresh_presets_table()
        QMessageBox.information(self, "復元完了", "公式初期プリセットを初期設定に戻しました。")

    def get_settings(self) -> dict:
        return self.settings


class PartSelectDialog(QDialog):
    """MIDI全トラック一覧表示 ＆ 主旋律ハーモニカ対象トラック選定ダイアログ (複数トラック複合対応)"""

    def __init__(self, tracks_info: list, current_main_idx: int = 0, parent=None,
                 current_main_indices: list = None, current_accomp_indices: list = None,
                 force_harmonica: bool = True):
        super().__init__(parent)
        self.setWindowTitle("MIDIパート詳細・主旋律トラック選定 (複数複合対応)")
        self.resize(780, 420)
        self.setModal(True)

        self.force_harmonica = force_harmonica
        self.tracks_info = tracks_info
        if current_main_indices:
            self.selected_main_indices = list(current_main_indices)
        else:
            self.selected_main_indices = [current_main_idx] if current_main_idx >= 0 else [0]

        if current_accomp_indices is not None:
            self.selected_accomp_indices = list(current_accomp_indices)
        else:
            self.selected_accomp_indices = [
                info["track_idx"] for info in tracks_info
                if info["track_idx"] not in self.selected_main_indices
            ]

        self.main_checkboxes = {}
        self.accomp_checkboxes = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(QLabel("ハーモニカで演奏・練習する主旋律トラックを選択してください (複数選択で複合可能):"))

        # テーブル作成 (7列: 主旋律チェック, 伴奏チェック, トラック名, 楽器音色, チャンネル, ノーツ数, 判定)
        self.table = QTableWidget(len(self.tracks_info), 7, self)
        self.table.setHorizontalHeaderLabels(["主旋律 (複数可)", "伴奏", "トラック名", "楽器音色 (GM)", "チャンネル", "総ノーツ数", "パート判定"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        for row, info in enumerate(self.tracks_info):
            t_idx = info["track_idx"]

            # Col 0: 主旋律チェックボックス
            chk_m = QCheckBox(self)
            chk_m.setChecked(t_idx in self.selected_main_indices)
            self.main_checkboxes[t_idx] = chk_m

            cell_m = QWidget()
            h_m = QHBoxLayout(cell_m)
            h_m.addWidget(chk_m)
            h_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_m.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, cell_m)

            # Col 1: 伴奏チェックボックス
            chk_a = QCheckBox(self)
            chk_a.setChecked(t_idx in self.selected_accomp_indices and t_idx not in self.selected_main_indices)
            self.accomp_checkboxes[t_idx] = chk_a

            cell_a = QWidget()
            h_a = QHBoxLayout(cell_a)
            h_a.addWidget(chk_a)
            h_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_a.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 1, cell_a)

            # 排他連動
            def make_handlers(target_idx, cm, ca):
                def on_main_toggled(checked):
                    if checked:
                        ca.blockSignals(True)
                        ca.setChecked(False)
                        ca.blockSignals(False)
                    else:
                        # 主旋律が0件にならないよう保護
                        checked_mains = [idx for idx, c in self.main_checkboxes.items() if c.isChecked()]
                        if not checked_mains:
                            cm.blockSignals(True)
                            cm.setChecked(True)
                            cm.blockSignals(False)
                            from PyQt6.QtWidgets import QMessageBox
                            QMessageBox.information(self, "主旋律選択", "主旋律トラックは最低1つ選択されている必要があります。")

                def on_accomp_toggled(checked):
                    if checked:
                        checked_mains = [idx for idx, c in self.main_checkboxes.items() if c.isChecked()]
                        if cm.isChecked() and len(checked_mains) <= 1:
                            ca.blockSignals(True)
                            ca.setChecked(False)
                            ca.blockSignals(False)
                            from PyQt6.QtWidgets import QMessageBox
                            QMessageBox.information(self, "主旋律選択", "このトラックは現在唯一の主旋律です。伴奏に変更する前に別の主旋律トラックを選択してください。")
                            return
                        cm.blockSignals(True)
                        cm.setChecked(False)
                        cm.blockSignals(False)

                cm.toggled.connect(on_main_toggled)
                ca.toggled.connect(on_accomp_toggled)

            make_handlers(t_idx, chk_m, chk_a)

            # トラック名
            item_name = QTableWidgetItem(info.get("name", f"Track {t_idx + 1}"))
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, 2, item_name)

            # 楽器音色 (GM)
            prog = info.get("program", 0)
            is_drum = info.get("is_drum", False)
            inst_str = info.get("instrument_name", get_gm_instrument_name(prog, is_drum=is_drum))
            item_inst = QTableWidgetItem(inst_str)
            item_inst.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            if prog == 22:
                item_inst.setForeground(QColor("#00E5FF"))
            self.table.setItem(row, 3, item_inst)

            # チャンネル
            item_ch = QTableWidgetItem(f"Ch. {info.get('channel', 0) + 1}")
            item_ch.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, item_ch)

            # ノーツ数
            item_count = QTableWidgetItem(f"{info.get('note_count', 0)} 音")
            item_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, item_count)

            # 判定
            if is_drum:
                kind = "ドラム / 打楽器"
            elif prog == 22 or any(k in info.get("name", "").lower() for k in ("harmonica", "melody", "vocal", "主旋律", "ハーモニカ")):
                kind = "★ 主旋律推奨"
            else:
                kind = "旋律 / 伴奏"
            item_kind = QTableWidgetItem(kind)
            item_kind.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "★" in kind:
                item_kind.setForeground(QColor("#34D399"))
            self.table.setItem(row, 6, item_kind)

        layout.addWidget(self.table)

        # ボタン
        btn_layout = QHBoxLayout()
        self.chk_force_harmonica = QCheckBox("主旋律パートをハーモニカ音色 (GM 22) に固定して再生", self)
        self.chk_force_harmonica.setChecked(bool(self.force_harmonica))
        btn_layout.addWidget(self.chk_force_harmonica)
        btn_layout.addStretch()

        btn_ok = QPushButton("決定", self)
        btn_ok.setObjectName("playBtn")
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("キャンセル", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _on_ok(self):
        mains = [idx for idx, c in self.main_checkboxes.items() if c.isChecked()]
        if not mains and self.tracks_info:
            mains = [self.tracks_info[0]["track_idx"]]
        self.selected_main_indices = mains
        self.selected_accomp_indices = [idx for idx, c in self.accomp_checkboxes.items() if c.isChecked()]
        self.selected_track_idx = mains[0]
        self.accept()

    def get_selected_track_idx(self) -> int:
        return self.selected_track_idx

    def get_selected_track_indices(self) -> list:
        return list(self.selected_main_indices)

    def get_selected_accomp_indices(self) -> list:
        return list(self.selected_accomp_indices)

    def is_force_harmonica(self) -> bool:
        return self.chk_force_harmonica.isChecked()




class FingeringEditorDialog(QDialog):
    """
    曲別変え指エディタ (Custom Fingering Editor) ダイアログ
    - 楽曲内の全旋律ノーツを小節順に一覧テーブル表示
    - 異名同音・重複運指を持つ候補ノーツ（C4/C5/C6, C#4/C#5/C#6, F3/F4/F5/F6等）を即座に絞り込み
    - 各行のプルダウンや「⟳ 循環切替」ボタンで、通常吹・隣の吹ド・シ#(吸ON)・ミ#(吹ON)をワンクリック選択
    - 行ダブルクリックまたは「▶ ジャンプ」で該当小節へ再生位置を即時シーク
    - ベース運指プリセット（スライド最小化 / スライド優先 / 標準）の一括切り替え
    - 曲別運指設定ファイル (*_fingering.txt) への即時セーブ＆リセット機能
    """

    def __init__(self, timeline, clock=None, audio_engine=None, gl_widget=None, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.clock = clock
        self.audio_engine = audio_engine
        self.gl_widget = gl_widget

        import harmonica_map
        self._initial_overrides = copy.deepcopy(harmonica_map.SONG_FINGERING_OVERRIDES)
        self._initial_muted = copy.deepcopy(harmonica_map.SONG_MUTED_NOTES)
        self._initial_preset = harmonica_map.CURRENT_SONG_PRESET
        self._initial_monophonic = harmonica_map.CURRENT_MONOPHONIC_MODE
        self._is_saved = False

        self._patterns = {}
        if self.timeline and self.timeline.filepath:
            prof = harmonica_map.load_song_profile(self.timeline.filepath)
            self._patterns = dict(prof.get("patterns", {}))
        self._initial_patterns = copy.deepcopy(self._patterns)

        self.setWindowTitle(f"🎼 変え指エディタ (Custom Fingering Editor) - {timeline.filename}")
        self.resize(980, 640)
        self.setMinimumSize(800, 500)
        self.setModal(True)

        self._row_note_map = []  # table_row -> note_data
        self._init_ui()
        self._populate_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # 1. ヘッダー情報バー
        hdr_frame = QFrame(self)
        hdr_frame.setObjectName("fingHdrFrame")
        hdr_frame.setStyleSheet("QFrame#fingHdrFrame { background-color: #161622; border: 1px solid #272738; border-radius: 6px; }")
        l_hdr = QHBoxLayout(hdr_frame)
        l_hdr.setContentsMargins(10, 6, 10, 6)

        v_hdr_text = QVBoxLayout()
        v_hdr_text.setSpacing(2)
        lbl_title = QLabel("🎼 <b style='font-size:14px; color:#38BDF8;'>曲別変え指エディタ (個別運指カスタマイズ)</b>", self)
        v_hdr_text.addWidget(lbl_title)

        lbl_desc = QLabel(f"対象曲: <b style='color:#E2E8F0;'>{self.timeline.filename}</b>　|　使用モデル: <b style='color:#FCD34D;'>{self.timeline.inst_type}</b>", self)
        v_hdr_text.addWidget(lbl_desc)
        l_hdr.addLayout(v_hdr_text, stretch=1)

        self.lbl_stats = QLabel(self)
        self.lbl_stats.setStyleSheet("font-size: 11px; color: #94A3B8; text-align: right;")
        l_hdr.addWidget(self.lbl_stats)

        layout.addWidget(hdr_frame)

        # 2. パターン＆プロファイル管理バー
        pat_frame = QFrame(self)
        pat_frame.setObjectName("fingPatFrame")
        pat_frame.setStyleSheet("QFrame#fingPatFrame { background-color: #151520; border: 1px solid #242436; border-radius: 4px; }")
        pat_layout = QHBoxLayout(pat_frame)
        pat_layout.setContentsMargins(8, 4, 8, 4)
        pat_layout.setSpacing(8)

        pat_layout.addWidget(QLabel("📂 <b>運指パターン:</b>"))
        self.combo_patterns = QComboBox(self)
        self.combo_patterns.setMinimumWidth(180)
        self.combo_patterns.setToolTip("曲ごとに保存されている複数の運指・除外パターンの切り替え")
        self._update_pattern_combo()
        self.combo_patterns.activated.connect(self._on_pattern_switched)
        pat_layout.addWidget(self.combo_patterns)

        self.btn_save_pattern = QPushButton("➕ パターン別名保存", self)
        self.btn_save_pattern.setStyleSheet("font-size: 11px; padding: 3px 8px; font-weight: bold;")
        self.btn_save_pattern.setToolTip("現在の運指・除外設定を新しいパターン名でプロファイルに保存")
        self.btn_save_pattern.clicked.connect(self._on_save_new_pattern)
        pat_layout.addWidget(self.btn_save_pattern)

        self.btn_rename_pattern = QPushButton("✏️ 名前変更...", self)
        self.btn_rename_pattern.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_rename_pattern.setToolTip("現在選択している運指パターンの名前を変更します")
        self.btn_rename_pattern.clicked.connect(self._on_rename_pattern)
        pat_layout.addWidget(self.btn_rename_pattern)

        self.btn_del_pattern = QPushButton("🗑 削除", self)
        self.btn_del_pattern.setStyleSheet("font-size: 11px; padding: 3px 8px; color: #FCA5A5;")
        self.btn_del_pattern.setToolTip("選択中の追加パターンを削除")
        self.btn_del_pattern.clicked.connect(self._on_delete_pattern)
        pat_layout.addWidget(self.btn_del_pattern)

        pat_layout.addStretch()
        layout.addWidget(pat_frame)

        # 3. フィルタ＆プリセット操作バー
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # 運指プリセット
        ctrl_layout.addWidget(QLabel("運指プリセット:"))
        self.combo_preset = QComboBox(self)
        self.combo_preset.addItems(["スライド最小化 (標準)", "スライド優先 (異名同音)"])
        from harmonica_map import CURRENT_SONG_PRESET, CURRENT_MONOPHONIC_MODE, normalize_fingering_preset
        self.combo_preset.setCurrentText(normalize_fingering_preset(CURRENT_SONG_PRESET))
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        ctrl_layout.addWidget(self.combo_preset)

        ctrl_layout.addSpacing(10)

        # 重なり音 (単音化モード)
        ctrl_layout.addWidget(QLabel("重なり音:"))
        self.combo_monophonic = QComboBox(self)
        self.combo_monophonic.addItems(["すべて有効", "高音優先 (上パート)", "低音優先 (下パート)"])
        self.combo_monophonic.setCurrentText(CURRENT_MONOPHONIC_MODE)
        self.combo_monophonic.currentTextChanged.connect(self._on_monophonic_mode_changed)
        ctrl_layout.addWidget(self.combo_monophonic)

        ctrl_layout.addSpacing(10)

        # 表示絞り込みフィルター
        ctrl_layout.addWidget(QLabel("表示絞り込み:"))
        self.combo_filter = QComboBox(self)
        self.combo_filter.addItems(["変更可能ノーツのみ (推奨)", "カスタム変更済みノーツのみ", "すべてのノーツ"])
        self.combo_filter.currentIndexChanged.connect(lambda _: self._populate_table())
        ctrl_layout.addWidget(self.combo_filter)

        ctrl_layout.addSpacing(10)

        # 検索ボックス (小節・音名)
        ctrl_layout.addWidget(QLabel("検索:"))
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("小節番号(例: 12) または 音名(例: ド4, C#)...")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(self._apply_text_filter)
        ctrl_layout.addWidget(self.txt_search, stretch=1)

        layout.addLayout(ctrl_layout)

        # 4. ノーツ一覧テーブル (9列: 発音/除外 状態を含む)
        self.table = QTableWidget(self)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "No.", "発音/除外", "小節 : 拍", "タイム", "音名", "現在の運指", "運指候補の選択", "循環切替", "状態"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 96)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #12121A;
                alternate-background-color: #171724;
                gridline-color: #232334;
                color: #E2E8F0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1B1B2A;
                color: #94A3B8;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #232334;
            }
            QTableWidget::item:selected {
                background-color: #1E3A5F;
                color: #FFFFFF;
            }
        """)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self.table, stretch=1)

        # 5. フッターボタンバー
        foot_layout = QHBoxLayout()
        foot_layout.setSpacing(10)

        btn_reset_mutes = QPushButton("🔔 除外ノーツを全復活", self)
        btn_reset_mutes.setStyleSheet("background-color: #1E2D3D; color: #93C5FD; border: 1px solid #1E40AF; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        btn_reset_mutes.setToolTip("除外（ミュート）されているすべてのノーツを有効（発音）状態に戻します（運指カスタムは維持）")
        btn_reset_mutes.clicked.connect(self._on_reset_muted_only)
        foot_layout.addWidget(btn_reset_mutes)

        btn_reset_fing = QPushButton("🎯 運指カスタムを全初期化", self)
        btn_reset_fing.setStyleSheet("background-color: #372B10; color: #FDE68A; border: 1px solid #92400E; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        btn_reset_fing.setToolTip("個別設定したすべての変え指を解除し、プリセット標準に戻します（除外ノーツは維持）")
        btn_reset_fing.clicked.connect(self._on_reset_custom_only)
        foot_layout.addWidget(btn_reset_fing)

        btn_jump = QPushButton("▶ 選択位置へジャンプ", self)
        btn_jump.setToolTip("選択されているノーツの再生位置へシークします (行のダブルクリックでもジャンプ可能)")
        btn_jump.clicked.connect(self._on_jump_clicked)
        foot_layout.addWidget(btn_jump)

        foot_layout.addStretch()

        btn_save = QPushButton("💾 保存して閉じる", self)
        btn_save.setObjectName("playBtn")
        btn_save.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        btn_save.clicked.connect(self._on_save_and_close)
        foot_layout.addWidget(btn_save)

        btn_close = QPushButton("閉じる", self)
        btn_close.clicked.connect(self.reject)
        foot_layout.addWidget(btn_close)

        layout.addLayout(foot_layout)

    def _populate_table(self):
        """現在のタイムライン主旋律ノーツを元にテーブルを構築"""
        from harmonica_map import (
            FINGERING_CANDIDATES,
            SONG_FINGERING_OVERRIDES,
            is_note_editable,
            get_candidate_label
        )

        self.table.setRowCount(0)
        self._row_note_map.clear()

        filter_mode = self.combo_filter.currentIndex()  # 0: editable only, 1: custom only, 2: all
        search_query = self.txt_search.text().strip().lower()

        notes = self.timeline.main_notes if self.timeline else []
        inst_type = self.timeline.inst_type if self.timeline else "16穴 (64音・C調)"

        editable_count = 0
        custom_count = 0

        visible_rows = []

        for idx, nd in enumerate(notes):
            pitch = nd["note"]
            start_tick = nd["start_tick"]
            start_sec = nd["start_sec"]
            lookup_note = pitch + 36 if "バス" in inst_type else pitch

            is_editable = is_note_editable(pitch, inst_type) and (lookup_note in FINGERING_CANDIDATES)
            if is_editable:
                editable_count += 1

            is_custom = (start_tick, lookup_note) in SONG_FINGERING_OVERRIDES
            if is_custom:
                custom_count += 1

            # フィルタ判定
            if filter_mode == 0 and not is_editable:
                continue
            elif filter_mode == 1 and not is_custom:
                continue

            # 小節・拍
            m, b, _, _, _ = self.timeline.get_measure_and_beat(start_sec) if self.timeline else (1, 1, 4, 4, 120)

            # 検索クエリ判定
            if search_query:
                m_str = str(m)
                jp_str = nd.get("name_jp", "").lower()
                cde_str = nd.get("name_cde", "").lower()
                h_str = f"{nd.get('hole', 1)}穴"
                if (search_query not in m_str and
                    search_query not in jp_str and
                    search_query not in cde_str and
                    search_query not in h_str):
                    continue

            visible_rows.append((idx, nd, m, b, lookup_note, is_editable, is_custom))

        # テーブル更新
        self.table.setRowCount(len(visible_rows))

        for r, (orig_idx, nd, m, b, lookup_note, is_editable, is_custom) in enumerate(visible_rows):
            self._row_note_map.append(nd)
            is_muted = nd.get("is_muted", False)
            dim_col = QColor("#64748B")

            # Col 0: No.
            it_no = QTableWidgetItem(f"{orig_idx + 1}")
            it_no.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_no.setFlags(it_no.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_muted:
                it_no.setForeground(dim_col)
            self.table.setItem(r, 0, it_no)

            # Col 1: 発音/除外状態トグルボタン
            btn_mute = QPushButton("🔇 除外" if is_muted else "🔔 有効", self)
            if is_muted:
                btn_mute.setStyleSheet("""
                    QPushButton {
                        background-color: #3B1C1C;
                        color: #F87171;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 2px 6px;
                        border: 1px solid #7F1D1D;
                        border-radius: 3px;
                    }
                    QPushButton:hover { background-color: #502424; }
                """)
                btn_mute.setToolTip("クリックでこのノーツを有効化（吹く）")
            else:
                btn_mute.setStyleSheet("""
                    QPushButton {
                        background-color: #143322;
                        color: #4ADE80;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 2px 6px;
                        border: 1px solid #166534;
                        border-radius: 3px;
                    }
                    QPushButton:hover { background-color: #1B452E; }
                """)
                btn_mute.setToolTip("クリックでこのノーツを除外（グレーアウト・吹かない）")

            btn_mute.clicked.connect(lambda _, n_data=nd: self._toggle_note_mute(n_data))
            cell_mute = QWidget()
            h_mute = QHBoxLayout(cell_mute)
            h_mute.addWidget(btn_mute)
            h_mute.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_mute.setContentsMargins(2, 2, 2, 2)
            self.table.setCellWidget(r, 1, cell_mute)

            # Col 2: 小節 : 拍
            it_mb = QTableWidgetItem(f"第 {m} 小節 {b} 拍")
            it_mb.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_mb.setFlags(it_mb.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_muted:
                it_mb.setForeground(dim_col)
            self.table.setItem(r, 2, it_mb)

            # Col 3: タイム
            sec = nd["start_sec"]
            it_time = QTableWidgetItem(f"{int(sec // 60):02d}:{sec % 60:05.2f}")
            it_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_time.setFlags(it_time.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_muted:
                it_time.setForeground(dim_col)
            self.table.setItem(r, 3, it_time)

            # Col 4: 音名
            it_name = QTableWidgetItem(f"{nd.get('name_jp', '')} ({nd.get('name_cde', '')})")
            it_name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_name.setFlags(it_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_muted:
                it_name.setForeground(dim_col)
            self.table.setItem(r, 4, it_name)

            # Col 5: 現在の運指バッジ
            fing = nd.get("fingering", {})
            f_hole = fing.get("hole", nd.get("hole", 1))
            f_act = fing.get("action", nd.get("action", "吹"))
            f_lev = fing.get("lever", nd.get("lever", "OFF"))
            f_str = f"{f_hole}穴 {f_act} {f_lev}"

            it_fing = QTableWidgetItem(f_str)
            it_fing.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_fing.setFlags(it_fing.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_muted:
                it_fing.setForeground(dim_col)
            elif f_act == "吹":
                it_fing.setForeground(QColor("#FF7A33"))
            else:
                it_fing.setForeground(QColor("#38BDF8"))
            self.table.setItem(r, 5, it_fing)

            # Col 6: 運指候補の選択 (QComboBox)
            if is_editable:
                candidates = FINGERING_CANDIDATES[lookup_note]
                combo = QComboBox(self)
                combo.setStyleSheet("QComboBox { font-size: 11px; padding: 2px 4px; }")
                for c_i, cand in enumerate(candidates):
                    lbl = get_candidate_label(cand, c_i)
                    combo.addItem(lbl)

                # 現在選択中のインデックス
                cur_override = SONG_FINGERING_OVERRIDES.get((nd["start_tick"], lookup_note))
                if cur_override is not None and 0 <= cur_override < len(candidates):
                    cur_idx = cur_override
                else:
                    cur_idx = 0
                    for c_i, cand in enumerate(candidates):
                        if cand["hole"] == f_hole and cand["action"] == f_act and cand["lever"] == f_lev:
                            cur_idx = c_i
                            break
                combo.setCurrentIndex(cur_idx)
                combo.currentIndexChanged.connect(
                    lambda new_idx, row_i=r, n_data=nd, l_note=lookup_note, cands=candidates:
                        self._on_candidate_changed(row_i, n_data, l_note, cands, new_idx)
                )
                self.table.setCellWidget(r, 6, combo)

                # Col 7: 循環切替ボタン
                btn_cyc = QPushButton("⟳ 切替", self)
                btn_cyc.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #26263A; border-radius: 3px;")
                btn_cyc.clicked.connect(
                    lambda _, row_i=r, cmb=combo, cands=candidates:
                        cmb.setCurrentIndex((cmb.currentIndex() + 1) % len(cands))
                )
                self.table.setCellWidget(r, 7, btn_cyc)
            else:
                it_fix = QTableWidgetItem("固定運指")
                it_fix.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_fix.setFlags(it_fix.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it_fix.setForeground(dim_col)
                self.table.setItem(r, 6, it_fix)

                it_dash = QTableWidgetItem("-")
                it_dash.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_dash.setFlags(it_dash.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it_dash.setForeground(dim_col)
                self.table.setItem(r, 7, it_dash)

            # Col 8: 状態 (カスタム時はボタン化して1クリックで標準へ復帰可能)
            if is_muted:
                it_stat = QTableWidgetItem("🔇 除外中")
                it_stat.setForeground(QColor("#F87171"))
                it_stat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_stat.setFlags(it_stat.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 8, it_stat)
            elif is_custom:
                btn_rev = QPushButton("★ カスタム", self)
                btn_rev.setFixedWidth(82)
                btn_rev.setStyleSheet("""
                    QPushButton {
                        background-color: #064E3B;
                        color: #6EE7B7;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 2px 4px;
                        border: 1px solid #059669;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #047857;
                        color: #FFFFFF;
                    }
                """)
                btn_rev.setToolTip("個別設定された変え指です。クリックすると標準の運指に戻します")
                btn_rev.clicked.connect(lambda _, n_data=nd, l_note=lookup_note: self._revert_single_note(n_data, l_note))
                cell_stat = QWidget()
                h_stat = QHBoxLayout(cell_stat)
                h_stat.addWidget(btn_rev)
                h_stat.setAlignment(Qt.AlignmentFlag.AlignCenter)
                h_stat.setContentsMargins(2, 2, 2, 2)
                self.table.setCellWidget(r, 8, cell_stat)
            else:
                it_stat = QTableWidgetItem("標準")
                it_stat.setForeground(dim_col)
                it_stat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_stat.setFlags(it_stat.flags() & ~Qt.ItemFlag.ItemIsEditable)
                it_stat.setToolTip("プリセット通りの標準運指です（運指候補を変更すると個別カスタムになります）")
                self.table.setItem(r, 8, it_stat)

        # 統計表示更新
        total_n = len(notes)
        muted_count = sum(1 for n in notes if n.get("is_muted", False))
        self.lbl_stats.setText(
            f"🎯 変更可能ノーツ: <b style='color:#38BDF8;'>{editable_count}</b> / {total_n} 音　"
            f"★ 個別運指カスタム: <b style='color:#34D399;'>{custom_count}</b> 音　"
            f"🔇 除外ノーツ: <b style='color:#F87171;'>{muted_count}</b> 音"
        )

    def _apply_text_filter(self):
        """検索ボックス入力時の軽量フィルタ"""
        self._populate_table()

    def _update_pattern_combo(self):
        """保存されている運指パターン一覧をコンボボックスへ更新"""
        cur = self.combo_patterns.currentText() if hasattr(self, "combo_patterns") else ""
        self.combo_patterns.blockSignals(True)
        self.combo_patterns.clear()
        self.combo_patterns.addItem("標準パターン (基本)")
        for p_name in sorted(self._patterns.keys()):
            self.combo_patterns.addItem(p_name)
        if cur in self._patterns:
            self.combo_patterns.setCurrentText(cur)
        else:
            self.combo_patterns.setCurrentIndex(0)
        self.combo_patterns.blockSignals(False)

    def _on_pattern_switched(self, idx: int):
        """運指パターンの切替"""
        import harmonica_map
        p_name = self.combo_patterns.currentText()
        harmonica_map.CURRENT_ACTIVE_PATTERN_NAME = p_name

        if p_name == "標準パターン (基本)":
            harmonica_map.SONG_FINGERING_OVERRIDES.clear()
            harmonica_map.SONG_FINGERING_OVERRIDES.update(self._initial_overrides)
            harmonica_map.SONG_MUTED_NOTES.clear()
            harmonica_map.SONG_MUTED_NOTES.update(self._initial_muted)
            harmonica_map.CURRENT_SONG_PRESET = self._initial_preset
            harmonica_map.CURRENT_MONOPHONIC_MODE = self._initial_monophonic
            pat_trans = getattr(self.timeline, "transpose_semitones", 0) if self.timeline else 0
            pat_trans_acc = getattr(self.timeline, "transpose_accomp", True) if self.timeline else True
        elif p_name in self._patterns:
            pat_data = self._patterns[p_name]
            pat_trans, pat_trans_acc = harmonica_map.apply_pattern_snapshot(pat_data)
        else:
            pat_trans = getattr(self.timeline, "transpose_semitones", 0) if self.timeline else 0
            pat_trans_acc = getattr(self.timeline, "transpose_accomp", True) if self.timeline else True

        if self.timeline:
            self.timeline.set_transpose(pat_trans, pat_trans_acc)
            self.timeline.monophonic_mode = harmonica_map.CURRENT_MONOPHONIC_MODE
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        self.combo_preset.blockSignals(True)
        self.combo_preset.setCurrentText(harmonica_map.normalize_fingering_preset(harmonica_map.CURRENT_SONG_PRESET))
        self.combo_preset.blockSignals(False)

        self.combo_monophonic.blockSignals(True)
        self.combo_monophonic.setCurrentText(harmonica_map.CURRENT_MONOPHONIC_MODE)
        self.combo_monophonic.blockSignals(False)

        harmonica_map.apply_fingering_preset(harmonica_map.CURRENT_SONG_PRESET)
        if self.audio_engine and self.timeline:
            self.audio_engine.set_transpose(pat_trans, pat_trans_acc)
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)
        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()
        self._populate_table()

    def _on_rename_pattern(self):
        """現在選択しているパターンの名前を変更 (課題29 / HIGH-5 / MEDIUM-4)"""
        old_name = self.combo_patterns.currentText()
        if not old_name or old_name == "標準パターン (基本)":
            QMessageBox.information(self, "名前変更不可", "「標準パターン (基本)」の名前は変更できません。")
            return
        new_name, ok = QInputDialog.getText(
            self, "パターン名の変更", "新しい運指パターン名を入力してください:", text=old_name
        )
        new_name = new_name.strip()
        if not ok or not new_name or new_name == old_name:
            return
        if new_name == "標準パターン (基本)":
            QMessageBox.warning(self, "名前エラー", "「標準パターン (基本)」と同名には変更できません。")
            return
        if new_name in self._patterns:
            QMessageBox.warning(self, "重複エラー", f"パターン「{new_name}」は既に存在します。")
            return

        import harmonica_map
        cur_trans = getattr(self.timeline, "transpose_semitones", 0) if self.timeline else 0
        cur_trans_acc = getattr(self.timeline, "transpose_accomp", True) if self.timeline else True
        cur_snapshot = harmonica_map.build_current_pattern_snapshot(
            transpose=cur_trans, transpose_accomp=cur_trans_acc
        )

        # 順序を保ってキーを置換し、最新スナップショットを反映
        new_patterns = {}
        for k, v in self._patterns.items():
            if k == old_name:
                new_patterns[new_name] = cur_snapshot
            else:
                new_patterns[k] = v
        self._patterns = new_patterns

        if old_name in self._initial_patterns:
            new_init = {}
            for k, v in self._initial_patterns.items():
                if k == old_name:
                    new_init[new_name] = copy.deepcopy(cur_snapshot)
                else:
                    new_init[k] = v
            self._initial_patterns = new_init

        harmonica_map.CURRENT_ACTIVE_PATTERN_NAME = new_name
        if self.timeline and self.timeline.filepath:
            harmonica_map.save_song_profile(self.timeline.filepath, {
                "patterns": self._patterns,
                "active_pattern_name": new_name,
                "transpose": cur_trans,
                "transpose_accomp": cur_trans_acc
            })
        self._update_pattern_combo()
        self.combo_patterns.setCurrentText(new_name)

    def _on_save_new_pattern(self):
        """現在の運指設定を別名パターンとして保存"""
        import harmonica_map
        cur_trans = getattr(self.timeline, "transpose_semitones", 0) if self.timeline else 0
        cur_trans_acc = getattr(self.timeline, "transpose_accomp", True) if self.timeline else True
        key_lbl = harmonica_map.format_transpose_key_label(cur_trans)
        default_name = f"{key_lbl} - パターン {len(self._patterns) + 1}"

        text, ok = QInputDialog.getText(
            self, "パターン別名保存",
            "新しい運指パターン名を入力してください:\n(例: Key+2 - ボーカル伴奏用 / スライド強化 / 簡易版)",
            text=default_name
        )
        if not ok or not text.strip():
            return
        p_name = text.strip()
        if p_name == "標準パターン (基本)":
            QMessageBox.warning(self, "保存不可", "「標準パターン (基本)」と同名では別名保存できません。別の名前を指定してください。")
            return

        snapshot = harmonica_map.build_current_pattern_snapshot(transpose=cur_trans, transpose_accomp=cur_trans_acc)
        self._patterns[p_name] = snapshot
        self._initial_patterns[p_name] = copy.deepcopy(snapshot)
        harmonica_map.CURRENT_ACTIVE_PATTERN_NAME = p_name
        if self.timeline and self.timeline.filepath:
            harmonica_map.save_song_profile(self.timeline.filepath, {
                "patterns": self._patterns,
                "active_pattern_name": p_name,
                "transpose": cur_trans,
                "transpose_accomp": cur_trans_acc
            })

        self._update_pattern_combo()
        self.combo_patterns.setCurrentText(p_name)
        QMessageBox.information(self, "パターン保存完了", f"パターン「{p_name}」をプロファイルに保存しました！")

    def _on_delete_pattern(self):
        """選択中パターンの削除"""
        p_name = self.combo_patterns.currentText()
        if p_name == "標準パターン (基本)":
            QMessageBox.information(self, "削除不可", "「標準パターン (基本)」は削除できません。")
            return
        if confirm_dialog(
            self, "パターンの削除確認",
            f"パターン「{p_name}」をプロファイルから完全に削除しますか？",
            default_yes=False
        ):
            if p_name in self._patterns:
                del self._patterns[p_name]
                import harmonica_map
                if self.timeline and self.timeline.filepath:
                    harmonica_map.save_song_profile(self.timeline.filepath, {"patterns": self._patterns})
            self._update_pattern_combo()
            self._on_pattern_switched(0)

    def _revert_single_note(self, nd: dict, lookup_note: int):
        """指定ノーツの個別変え指カスタムを解除し標準に戻す"""
        from harmonica_map import SONG_FINGERING_OVERRIDES
        start_tick = nd["start_tick"]
        key = (start_tick, lookup_note)
        if key in SONG_FINGERING_OVERRIDES:
            del SONG_FINGERING_OVERRIDES[key]

        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)
        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()
        if self.audio_engine:
            self.audio_engine.play_ui_click()

        self._populate_table()

    def _on_candidate_changed(self, row: int, nd: dict, lookup_note: int, candidates: list, new_idx: int):
        """候補コンボ変更時のリアルタイム反映 (メモリ上のみ更新・明示保存までファイル未保存)"""
        from harmonica_map import SONG_FINGERING_OVERRIDES

        start_tick = nd["start_tick"]
        SONG_FINGERING_OVERRIDES[(start_tick, lookup_note)] = new_idx

        # タイムライン再バインド
        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        # GLキャッシュ更新
        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()

        # 音響クリックフィードバック
        if self.audio_engine:
            self.audio_engine.play_ui_click()

        self._populate_table()

    def _toggle_note_mute(self, nd: dict):
        """ノーツの発音/除外 (Mute) 状態を反転 (メモリ上のみ更新・明示保存までファイル未保存)"""
        start_sec = nd["start_sec"]
        raw_pitch = nd.get("raw_note", nd["note"])
        key = f"{round(start_sec, 3)}_{raw_pitch}"
        new_muted = not nd.get("is_muted", False)
        from harmonica_map import SONG_MUTED_NOTES
        SONG_MUTED_NOTES[key] = new_muted

        mono_mode = getattr(self.timeline, "monophonic_mode", "すべて有効") if self.timeline else "すべて有効"
        if not new_muted and mono_mode != "すべて有効":
            for other_nd in (self.timeline.main_notes if self.timeline else []):
                if other_nd is not nd and not other_nd.get("is_muted", False):
                    overlap = min(nd["end_sec"], other_nd["end_sec"]) - max(nd["start_sec"], other_nd["start_sec"])
                    if overlap >= 0.03:
                        other_raw_pitch = other_nd.get("raw_note", other_nd["note"])
                        other_key = f"{round(other_nd['start_sec'], 3)}_{other_raw_pitch}"
                        SONG_MUTED_NOTES[other_key] = True

        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        if self.audio_engine:
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)
            self.audio_engine.play_ui_click()

        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()

        self._populate_table()

    def _on_monophonic_mode_changed(self, mode: str):
        """重なり音（単音化モード）変更"""
        import harmonica_map
        harmonica_map.CURRENT_MONOPHONIC_MODE = mode
        if self.timeline:
            self.timeline.set_monophonic_mode(mode)

        if self.audio_engine:
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)

        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()

        self._populate_table()

    def _on_cell_double_clicked(self, row: int, col: int):
        """セルダブルクリックで該当ノーツへシーク"""
        if 0 <= row < len(self._row_note_map):
            nd = self._row_note_map[row]
            sec = nd["start_sec"]
            if self.clock:
                self.clock.set_anchor(sec, speed_ratio=self.clock.get_speed_ratio(), state=self.clock.get_state())
            if self.audio_engine:
                self.audio_engine.seek(sec)
            if self.gl_widget:
                self.gl_widget.update()

    def _on_jump_clicked(self):
        """選択されている行のノーツへジャンプ"""
        sel_rows = self.table.selectedIndexes()
        if sel_rows:
            row = sel_rows[0].row()
            self._on_cell_double_clicked(row, 0)

    def _on_preset_changed(self, preset_name: str):
        """運指プリセット変更"""
        import harmonica_map
        harmonica_map.CURRENT_SONG_PRESET = preset_name
        harmonica_map.apply_fingering_preset(preset_name)

        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()

        self._populate_table()

    def _on_reset_custom_only(self):
        """個別変え指カスタムのみを全初期化（除外ノーツは維持）"""
        if confirm_dialog(
            self,
            "運指カスタム初期化確認",
            "個別設定したすべての変え指を解除し、プリセット標準の運指に戻しますか？\n（除外ノーツの状態はそのまま維持されます）",
            default_yes=False
        ):
            import harmonica_map
            harmonica_map.SONG_FINGERING_OVERRIDES.clear()
            if self.timeline:
                self.timeline.rebind_fingerings(self.timeline.inst_type)
            if self.audio_engine and self.timeline:
                self.audio_engine.load_timeline(self.timeline)
                self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)
            if self.gl_widget:
                self.gl_widget.invalidate_static_cache()
                self.gl_widget.update()
            self._populate_table()

    def _on_reset_muted_only(self):
        """除外ノーツのみを全復活（運指カスタムは維持）"""
        if confirm_dialog(
            self,
            "除外ノーツ全復活確認",
            "除外（ミュート）されているすべてのノーツを有効化し、\n通常通り発音・表示される状態に戻しますか？\n（運指カスタムはそのまま維持されます）",
            default_yes=False
        ):
            import harmonica_map
            harmonica_map.SONG_MUTED_NOTES.clear()
            if self.timeline:
                self.timeline.rebind_fingerings(self.timeline.inst_type)
            if self.audio_engine and self.timeline:
                self.audio_engine.load_timeline(self.timeline)
                self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)
            if self.gl_widget:
                self.gl_widget.invalidate_static_cache()
                self.gl_widget.update()
            self._populate_table()

    def _on_save_and_close(self):
        """明示的に設定をファイルへ保存して閉じる"""
        import harmonica_map
        if self.timeline and self.timeline.filepath:
            p_name = self.combo_patterns.currentText()
            harmonica_map.CURRENT_ACTIVE_PATTERN_NAME = p_name
            cur_trans = getattr(self.timeline, "transpose_semitones", 0) if self.timeline else 0
            cur_trans_acc = getattr(self.timeline, "transpose_accomp", True) if self.timeline else True
            if p_name != "標準パターン (基本)" and p_name in self._patterns:
                self._patterns[p_name] = harmonica_map.build_current_pattern_snapshot(
                    transpose=cur_trans, transpose_accomp=cur_trans_acc
                )
            extra = {
                "patterns": self._patterns,
                "active_pattern_name": p_name,
                "transpose": cur_trans,
                "transpose_accomp": cur_trans_acc
            }
            harmonica_map.save_song_profile(self.timeline.filepath, extra)
            harmonica_map.save_song_fingering(self.timeline.filepath)
        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)
        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()
        self._is_saved = True
        self.accept()

    def reject(self):
        """ダイアログキャンセル/閉じる時の未保存変更破棄およびロールバック処理"""
        if not self._is_saved:
            import harmonica_map
            has_changes = (
                harmonica_map.SONG_FINGERING_OVERRIDES != self._initial_overrides or
                harmonica_map.SONG_MUTED_NOTES != self._initial_muted or
                harmonica_map.CURRENT_SONG_PRESET != self._initial_preset or
                harmonica_map.CURRENT_MONOPHONIC_MODE != self._initial_monophonic or
                self._patterns != self._initial_patterns
            )
            if has_changes:
                if not confirm_dialog(
                    self,
                    "未保存の変更の確認",
                    "変え指または除外ノーツの変更が保存されていません。\n\n"
                    "変更を破棄して元の状態に戻しますか？\n"
                    "(「いいえ」を選ぶとエディタに戻ります)",
                    default_yes=False
                ):
                    return

            # 元の状態へ完全復元
            harmonica_map.SONG_FINGERING_OVERRIDES.clear()
            harmonica_map.SONG_FINGERING_OVERRIDES.update(self._initial_overrides)
            harmonica_map.SONG_MUTED_NOTES.clear()
            harmonica_map.SONG_MUTED_NOTES.update(self._initial_muted)
            harmonica_map.CURRENT_SONG_PRESET = self._initial_preset
            harmonica_map.CURRENT_MONOPHONIC_MODE = self._initial_monophonic
            harmonica_map.apply_fingering_preset(self._initial_preset)
            self._patterns = copy.deepcopy(self._initial_patterns)

            # ディスク上のプロファイルも初期状態へロールバック
            if self.timeline and self.timeline.filepath:
                harmonica_map.save_song_profile(self.timeline.filepath, {"patterns": self._initial_patterns})
                harmonica_map.save_song_fingering(self.timeline.filepath)

            if self.timeline:
                self.timeline.monophonic_mode = self._initial_monophonic
                self.timeline.rebind_fingerings(self.timeline.inst_type)
            if self.audio_engine and self.timeline:
                self.audio_engine.load_timeline(self.timeline)
                self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)
            if self.gl_widget:
                self.gl_widget.invalidate_static_cache()
                self.gl_widget.update()

        super().reject()



class ExportProgressDialog(QDialog):
    """MP4動画書き出し進捗ダイアログ"""

    def __init__(self, export_thread, output_path: str, parent=None):
        super().__init__(parent)
        self.export_thread = export_thread
        self.output_path = output_path
        self.is_done = False

        self.setWindowTitle("🎬 動画書き出し中 (MP4 Video Rendering)")
        self.resize(520, 240)
        self.setModal(True)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self.lbl_title = QLabel("🎬 <b>MP4動画レンダリングを実行中...</b>", self)
        self.lbl_title.setStyleSheet("font-size: 13px; color: #38BDF8;")
        layout.addWidget(self.lbl_title)

        self.lbl_filename = QLabel(f"保存先: {os.path.basename(self.output_path)}", self)
        self.lbl_filename.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.lbl_filename)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 4px;
                background-color: #1E293B;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #0284C7;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.lbl_frame_info = QLabel("準備中...", self)
        self.lbl_frame_info.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        layout.addWidget(self.lbl_frame_info)

        self.lbl_stats = QLabel("", self)
        self.lbl_stats.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(self.lbl_stats)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_open_folder = QPushButton("📂 保存フォルダを開く", self)
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_folder)
        btn_box.addWidget(self.btn_open_folder)

        self.btn_action = QPushButton("⏹ キャンセル", self)
        self.btn_action.clicked.connect(self._on_action_clicked)
        btn_box.addWidget(self.btn_action)

        layout.addLayout(btn_box)

    def _connect_signals(self):
        self.export_thread.sig_progress.connect(self._on_progress)
        self.export_thread.sig_finished.connect(self._on_finished)

    def _on_progress(self, frame_idx, total_frames, elapsed, fps, eta):
        pct = int(min(100, (frame_idx / total_frames) * 100)) if total_frames > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_frame_info.setText(f"フレーム: {frame_idx:,} / {total_frames:,} ({pct}%)")

        el_m, el_s = int(elapsed // 60), int(elapsed % 60)
        eta_m, eta_s = int(eta // 60), int(eta % 60)
        self.lbl_stats.setText(f"速度: {fps:.1f} FPS　|　経過: {el_m:02d}:{el_s:02d}　|　残り時間: {eta_m:02d}:{eta_s:02d}")

    def _on_finished(self, success, output_path, err_msg):
        self.is_done = True
        if success:
            self.progress_bar.setValue(100)
            self.lbl_title.setText("✅ <b>動画の書き出しが完了しました！</b>")
            self.lbl_title.setStyleSheet("font-size: 13px; color: #34D399;")
            msg = f"ファイル保存完了: {os.path.basename(output_path)}"
            if output_path.lower().endswith(".mov"):
                msg += "\n※完全透過MOVは編集ソフト（Premiere, DaVinci, AviUtl, OBS等）で重ねて使う合成用素材です"
            self.lbl_frame_info.setText(msg)
            self.btn_open_folder.setVisible(True)
            self.btn_action.setText("閉じる")
        else:
            self.lbl_title.setText("❌ <b>書き出しに失敗しました</b>")
            self.lbl_title.setStyleSheet("font-size: 13px; color: #F87171;")
            self.lbl_frame_info.setText(f"エラー: {err_msg[:120]}")
            self.btn_action.setText("閉じる")

    def _on_action_clicked(self):
        if not self.is_done:
            self.export_thread.cancel()
            self.reject()
        else:
            self.accept()

    def _open_folder(self):
        import subprocess
        norm_path = os.path.normpath(self.output_path)
        if os.path.isfile(norm_path):
            subprocess.Popen(f'explorer /select,"{norm_path}"')
        else:
            folder = os.path.dirname(norm_path)
            subprocess.Popen(f'explorer "{folder}"')

    def closeEvent(self, event):
        if not self.is_done:
            self.export_thread.cancel()
        super().closeEvent(event)


class SingleFramePreviewDialog(QDialog):
    """1フレーム静止画プレビュー確認ダイアログ (Full HD等の解像度確認用)"""

    def __init__(self, qimage: QImage, info_text: str = "", show_safe_zone: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📸 レンダリング静止画プレビュー")
        self.resize(1000, 620)
        self.setStyleSheet("""
            QDialog {
                background-color: #121214;
                color: #EDEDED;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_header = QLabel(f"<b>レンダリングプレビュー</b> — {info_text} ({qimage.width()}x{qimage.height()})", self)
        lbl_header.setStyleSheet("font-size: 13px; color: #38BDF8;")
        layout.addWidget(lbl_header)

        # プレビュー画像表示ラベル
        self.lbl_image = QLabel(self)
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("background-color: #0A0A0C; border: 1px solid #27272A; border-radius: 6px;")

        # セーフゾーン枠重畳描画 (案C)
        preview_img = qimage.copy()
        if show_safe_zone and preview_img.width() < preview_img.height():
            p = QPainter(preview_img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w, h = preview_img.width(), preview_img.height()
            scale = w / 960.0
            sz_top = int(h * 0.14)
            sz_bot = h - int(h * 0.22)
            sz_left = int(w * 0.05)
            sz_right = w - int(w * 0.14)

            p.fillRect(QRectF(0, 0, w, sz_top), QColor(239, 68, 68, 50))
            p.fillRect(QRectF(0, sz_bot, w, int(h * 0.22)), QColor(239, 68, 68, 50))
            p.fillRect(QRectF(sz_right, sz_top, int(w * 0.14), sz_bot - sz_top), QColor(239, 68, 68, 40))

            pen_sz = QPen(QColor("#F59E0B"), max(2.0, 3.0 * scale), Qt.PenStyle.DashLine)
            p.setPen(pen_sz)
            p.setBrush(QColor(245, 158, 11, 20))
            p.drawRect(QRectF(sz_left, sz_top, sz_right - sz_left, sz_bot - sz_top))

            font_sz = QFont("Meiryo UI", max(10, int(18.0 * scale)), QFont.Weight.Bold)
            p.setFont(font_sz)
            p.setPen(QColor("#F59E0B"))
            p.drawText(QRectF(sz_left + 12 * scale, sz_top + 8 * scale, sz_right - sz_left - 24 * scale, 36 * scale),
                       Qt.AlignmentFlag.AlignLeft, "🛡️ Shorts / TikTok 推奨セーフゾーン")
            p.setPen(QColor("#FCA5A5"))
            p.drawText(QRectF(12 * scale, 8 * scale, w - 24 * scale, 36 * scale),
                       Qt.AlignmentFlag.AlignCenter, "📱 上部UI・ノッチ被りエリア")
            p.drawText(QRectF(12 * scale, sz_bot + 8 * scale, w - 24 * scale, 36 * scale),
                       Qt.AlignmentFlag.AlignCenter, "📱 下部UI（タイトル・アカウント名）被りエリア")
            p.end()
            pixmap = QPixmap.fromImage(preview_img)
        else:
            pixmap = QPixmap.fromImage(qimage)

        scaled_pix = pixmap.scaled(960, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_image.setPixmap(scaled_pix)
        layout.addWidget(self.lbl_image, stretch=1)

        # 下部ボタン
        bottom_box = QHBoxLayout()
        bottom_box.addStretch()
        btn_close = QPushButton("閉じる", self)
        btn_close.setFixedHeight(32)
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        btn_close.clicked.connect(self.accept)
        bottom_box.addWidget(btn_close)
        layout.addLayout(bottom_box)


class SkinSelectDialog(QDialog):
    """
    ハーモニカ外観スキン選択・リアルタイムプレビューダイアログ
    - 本体スキン: メタル / ウッド / マットブラック / ゴールド / カスタムPNG
    - スライドレバー: シルバー / ゴールド / ウッド / カスタムPNG
    - リアルタイム合成プレビュー (本体 + 丸穴 + 穴番号 + レバー)
    """

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 ハーモニカスキン設定 (Custom Skins)")
        self.resize(760, 520)
        self.setMinimumSize(680, 480)
        self.setModal(True)

        from config import get_portable_path
        self.skins_dir = get_portable_path("skins")

        self.body_options = [
            ("スタンダードメタル (ステンレスシルバー)", "マウスピース_メタル.png"),
            ("ウッドカバー仕様 (高級木製ウォールナット調)", "マウスピース_ウッド.png"),
            ("マットブラック仕様 (艶消しブラック＆メタル口金)", "マウスピース_マットブラック.png"),
            ("ゴールド口金仕様 (真鍮ゴールド口金＆シルバー)", "マウスピース_ゴールド.png"),
            ("カスタム画像 (外部PNGファイル指定)", ""),
        ]

        self.lever_options = [
            ("スタンダードシルバー (ステンレス扁平ボタン)", ("レバーオフ_シルバー.png", "レバーオン_シルバー.png")),
            ("ブラスゴールド (真鍮金メッキボタン)", ("レバーオフ_ゴールド.png", "レバーオン_ゴールド.png")),
            ("ウッドボタン (高級木製カバーボタン)", ("レバーオフ_ウッド.png", "レバーオン_ウッド.png")),
            ("カスタム画像 (外部PNGファイル指定)", ("", "")),
        ]

        self.cur_mouthpiece_path = current_settings.get("skin_mouthpiece_path", "")
        self.cur_lever_off_path = current_settings.get("skin_lever_off_path", "")
        self.cur_lever_on_path = current_settings.get("skin_lever_on_path", "")
        self.skin_enabled = bool(current_settings.get("skin_enabled", True))

        self._init_ui()
        self._update_preview()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # ヘッダー
        lbl_hdr = QLabel("<b>ハーモニカ本体カバー＆スライドレバーの外観スキンカスタマイズ</b>", self)
        lbl_hdr.setStyleSheet("font-size: 13px; color: #38BDF8;")
        layout.addWidget(lbl_hdr)

        # プレビューボックス (中央表示)
        f_prev = QFrame(self)
        f_prev.setObjectName("skinPrevFrame")
        f_prev.setStyleSheet("QFrame#skinPrevFrame { background-color: #0E0E14; border: 1px solid #232334; border-radius: 6px; }")
        l_prev = QVBoxLayout(f_prev)
        l_prev.setContentsMargins(10, 8, 10, 8)
        l_prev.setSpacing(6)

        lbl_prev_title = QLabel("👁 <b>リアルタイム合成プレビュー (4穴＋レバー表示例):</b>", self)
        lbl_prev_title.setStyleSheet("font-size: 11px; color: #94A3B8;")
        l_prev.addWidget(lbl_prev_title)

        self.lbl_preview_canvas = QLabel(self)
        self.lbl_preview_canvas.setFixedHeight(120)
        self.lbl_preview_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_canvas.setStyleSheet("background-color: #08080C; border: 1px dashed #333346; border-radius: 4px;")
        l_prev.addWidget(self.lbl_preview_canvas)
        layout.addWidget(f_prev)

        # 選択グループ
        f_opts = QFrame(self)
        f_opts.setObjectName("skinOptsFrame")
        f_opts.setStyleSheet("QFrame#skinOptsFrame { background-color: #161622; border: 1px solid #272738; border-radius: 6px; }")
        l_opts = QVBoxLayout(f_opts)
        l_opts.setContentsMargins(14, 12, 14, 12)
        l_opts.setSpacing(10)

        # 1. 本体スキン
        l_opts.addWidget(QLabel("🎷 <b>ハーモニカ本体カバー＆口金スキン:</b>"))
        r_body = QHBoxLayout()
        self.combo_body = QComboBox(self)
        self.combo_body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for label, _ in self.body_options:
            self.combo_body.addItem(label)
        self._select_body_by_path(self.cur_mouthpiece_path)
        self.combo_body.currentIndexChanged.connect(self._on_body_combo_changed)
        r_body.addWidget(self.combo_body, stretch=1)

        self.btn_browse_body = QPushButton("📂 ファイル選択...", self)
        self.btn_browse_body.setToolTip("自作・カスタムのマウスピース/カバーPNG画像(推奨: 800x90px)を選択")
        self.btn_browse_body.clicked.connect(self._on_browse_body)
        r_body.addWidget(self.btn_browse_body)
        l_opts.addLayout(r_body)

        # 2. スライドレバースキン
        l_opts.addWidget(QLabel("🔘 <b>スライドレバーボタン (OFF / ON):</b>"))
        r_lever = QHBoxLayout()
        self.combo_lever = QComboBox(self)
        self.combo_lever.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for label, _ in self.lever_options:
            self.combo_lever.addItem(label)
        self._select_lever_by_path(self.cur_lever_off_path)
        self.combo_lever.currentIndexChanged.connect(self._on_lever_combo_changed)
        r_lever.addWidget(self.combo_lever, stretch=1)

        self.btn_browse_lever = QPushButton("📂 ファイル選択...", self)
        self.btn_browse_lever.setToolTip("自作・カスタムのスライドレバー通常時(OFF)画像(48x48px)を選択")
        self.btn_browse_lever.clicked.connect(self._on_browse_lever)
        r_lever.addWidget(self.btn_browse_lever)
        l_opts.addLayout(r_lever)

        # 有効チェックボックス
        self.chk_enable_skin = QCheckBox("カスタムスキンを有効にする (OFF時は標準プロシージャル描画)", self)
        self.chk_enable_skin.setChecked(self.skin_enabled)
        self.chk_enable_skin.toggled.connect(self._on_enable_toggled)
        l_opts.addWidget(self.chk_enable_skin)

        layout.addWidget(f_opts)

        layout.addStretch()

        # フッターボタン
        foot = QHBoxLayout()
        foot.addStretch()
        btn_apply = QPushButton("💾 適用して閉じる", self)
        btn_apply.setObjectName("playBtn")
        btn_apply.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        btn_apply.clicked.connect(self.accept)
        foot.addWidget(btn_apply)

        btn_cancel = QPushButton("キャンセル", self)
        btn_cancel.clicked.connect(self.reject)
        foot.addWidget(btn_cancel)
        layout.addLayout(foot)

    def _select_body_by_path(self, path: str):
        if not path:
            self.combo_body.setCurrentIndex(0)
            return
        base = os.path.basename(path)
        for idx, (label, fname) in enumerate(self.body_options[:-1]):
            if fname and (fname == base or (fname == "マウスピース_メタル.png" and base == "マウスピース.png")):
                self.combo_body.setCurrentIndex(idx)
                return
        self.combo_body.setCurrentIndex(len(self.body_options) - 1)

    def _select_lever_by_path(self, path: str):
        if not path:
            self.combo_lever.setCurrentIndex(0)
            return
        base = os.path.basename(path)
        for idx, (label, (foff, fon)) in enumerate(self.lever_options[:-1]):
            if foff and (foff == base or (foff == "レバーオフ_シルバー.png" and base == "レバーオフ.png")):
                self.combo_lever.setCurrentIndex(idx)
                return
        self.combo_lever.setCurrentIndex(len(self.lever_options) - 1)

    def _on_body_combo_changed(self, idx: int):
        if idx < len(self.body_options) - 1:
            fname = self.body_options[idx][1]
            self.cur_mouthpiece_path = os.path.join(self.skins_dir, fname)
        self._update_preview()

    def _on_lever_combo_changed(self, idx: int):
        if idx < len(self.lever_options) - 1:
            foff, fon = self.lever_options[idx][1]
            self.cur_lever_off_path = os.path.join(self.skins_dir, foff)
            self.cur_lever_on_path = os.path.join(self.skins_dir, fon)
        self._update_preview()

    def _on_browse_body(self):
        f, _ = QFileDialog.getOpenFileName(self, "本体マウスピース/カバー画像を選択", self.skins_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
        if f:
            self.cur_mouthpiece_path = f
            self.combo_body.blockSignals(True)
            self.combo_body.setCurrentIndex(len(self.body_options) - 1)
            self.combo_body.blockSignals(False)
            self._update_preview()

    def _on_browse_lever(self):
        f, _ = QFileDialog.getOpenFileName(self, "スライドレバー画像(OFF)を選択", self.skins_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
        if f:
            self.cur_lever_off_path = f
            dir_n = os.path.dirname(f)
            base_n = os.path.basename(f)
            on_n = base_n.replace("オフ", "オン").replace("off", "on")
            cand_on = os.path.join(dir_n, on_n)
            self.cur_lever_on_path = cand_on if os.path.exists(cand_on) else f
            self.combo_lever.blockSignals(True)
            self.combo_lever.setCurrentIndex(len(self.lever_options) - 1)
            self.combo_lever.blockSignals(False)
            self._update_preview()

    def _on_enable_toggled(self, checked: bool):
        self.skin_enabled = checked
        self._update_preview()

    def _update_preview(self):
        """プレビュー画像を描画合成"""
        w, h = 600, 110
        pix = QPixmap(w, h)
        pix.fill(QColor("#08080C"))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. 本体描画
        plate_w, plate_h = 480, 80
        px, py = 20, 15
        plate_rect = QRectF(px, py, plate_w, plate_h)

        target_mp = self.cur_mouthpiece_path or os.path.join(self.skins_dir, "マウスピース_メタル.png")
        if not os.path.exists(target_mp):
            target_mp = os.path.join(self.skins_dir, "マウスピース.png")

        if self.skin_enabled and os.path.exists(target_mp):
            mp_pix = QPixmap(target_mp)
            if not mp_pix.isNull():
                p.drawPixmap(plate_rect.toRect(), mp_pix)
            else:
                p.setPen(QPen(QColor("#777777"), 2))
                p.setBrush(QColor("#2d2f31"))
                p.drawRoundedRect(plate_rect, 12, 12)
        else:
            p.setPen(QPen(QColor("#777777"), 2))
            p.setBrush(QColor("#2d2f31"))
            p.drawRoundedRect(plate_rect, 12, 12)

        # 2. 5つの穴と穴番号サンプル
        hole_cnt = 5
        pitch = plate_w / (hole_cnt + 1)
        for i in range(hole_cnt):
            hx = px + (i + 1) * pitch
            hy = py + plate_h / 2.0
            hr = 15.0
            p.setPen(QPen(QColor("#999999"), 1.5))
            p.setBrush(QColor("#111116"))
            p.drawEllipse(QRectF(hx - hr, hy - hr, hr * 2, hr * 2))

            # 穴番号
            font = QFont("Arial", 9, QFont.Weight.Bold)
            p.setFont(font)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(hx - 20, hy - 9, 40, 18), Qt.AlignmentFlag.AlignCenter, f"{i + 1}")

        # 3. スライドレバー (通常時OFF)
        lever_x = px + plate_w + 4
        lever_y = py + (plate_h - 48) / 2.0
        lever_rect = QRectF(lever_x, lever_y, 48, 48)

        target_lo = self.cur_lever_off_path or os.path.join(self.skins_dir, "レバーオフ_シルバー.png")
        if not os.path.exists(target_lo):
            target_lo = os.path.join(self.skins_dir, "レバーオフ.png")

        if self.skin_enabled and os.path.exists(target_lo):
            lo_pix = QPixmap(target_lo)
            if not lo_pix.isNull():
                p.drawPixmap(lever_rect.toRect(), lo_pix)
            else:
                p.setPen(QPen(QColor("#888888"), 1.5))
                p.setBrush(QColor("#444444"))
                p.drawRoundedRect(QRectF(lever_x, lever_y + 16, 24, 16), 3, 3)
                p.setBrush(QColor("#CCCCCC"))
                p.drawEllipse(QRectF(lever_x + 20, lever_y + 6, 16, 36))
        else:
            p.setPen(QPen(QColor("#888888"), 1.5))
            p.setBrush(QColor("#444444"))
            p.drawRoundedRect(QRectF(lever_x, lever_y + 16, 24, 16), 3, 3)
            p.setBrush(QColor("#CCCCCC"))
            p.drawEllipse(QRectF(lever_x + 20, lever_y + 6, 16, 36))

        p.end()
        self.lbl_preview_canvas.setPixmap(pix)

    def get_selected_skins(self) -> dict:
        return {
            "mouthpiece_path": self.cur_mouthpiece_path,
            "lever_off_path": self.cur_lever_off_path,
            "lever_on_path": self.cur_lever_on_path,
            "skin_enabled": self.skin_enabled,
        }


def _add_offset_stepper_buttons(layout, spin: QSpinBox):
    """ズレ補正スピンボックス横に [-50] [-10] [0] [+10] [+50] ms のクリック調整ボタン群を配置"""
    for label, delta in [("-50", -50), ("-10", -10), ("0", None), ("+10", 10), ("+50", 50)]:
        btn = QPushButton(label)
        btn.setFixedWidth(36 if len(label) <= 3 else 40)
        btn.setFixedHeight(22)
        btn.setStyleSheet("QPushButton { font-size: 11px; padding: 1px 2px; }")
        if delta is None:
            btn.setToolTip("ズレ補正を 0ms にリセット")
            btn.clicked.connect(lambda _, s=spin: s.setValue(0))
        else:
            btn.setToolTip(f"{delta:+d}ms 調整")
            btn.clicked.connect(lambda _, s=spin, d=delta: s.setValue(s.value() + d))
        layout.addWidget(btn)


class AudioTrackMixerDialog(QDialog):
    """動画音声トラック・ミキサー (3系統マルチトラック合成ダイアログ)"""

    def __init__(self, mixer_settings: dict, timeline=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎚️ 動画音声トラック・ミキサー")
        self.resize(520, 640)
        self.setModal(True)
        self.timeline = timeline
        self.settings = dict(mixer_settings)
        self._audition_player = None
        self._temp_preview_wav = None

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._stop_preview)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        lbl_desc = QLabel("動画に合成する音声トラックを複数有効化し、各音量バランスやズレ補正を調整します。")
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        main_layout.addWidget(lbl_desc)

        # === Track 1: 外部伴奏音源 ===
        grp_ext = QFrame()
        grp_ext.setObjectName("groupFrame")
        grp_ext.setStyleSheet("QFrame#groupFrame { border: 1px solid #334155; border-radius: 6px; padding: 6px; background-color: #0F172A; }")
        l_ext = QVBoxLayout(grp_ext)
        l_ext.setSpacing(6)

        self.chk_ext = QCheckBox("🎵 Track 1: 伴奏・外部音源 (Audio File)", self)
        self.chk_ext.setChecked(bool(self.settings.get("track_ext_enabled", False)))
        self.chk_ext.setStyleSheet("font-weight: bold; color: #38BDF8;")
        l_ext.addWidget(self.chk_ext)

        r_ext_f = QHBoxLayout()
        ext_path = self.settings.get("track_ext_path", "")
        self.lbl_ext_path = QLabel("ファイル: " + (os.path.basename(ext_path) if ext_path else "未選択"))
        self.lbl_ext_path.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        r_ext_f.addWidget(self.lbl_ext_path, stretch=1)
        btn_browse_ext = QPushButton("📂 変更...", self)
        btn_browse_ext.setFixedWidth(70)
        btn_browse_ext.clicked.connect(self._on_browse_ext)
        r_ext_f.addWidget(btn_browse_ext)
        l_ext.addLayout(r_ext_f)

        r_ext_v = QHBoxLayout()
        r_ext_v.addWidget(QLabel("トラック音量:"))
        self.slider_ext_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_ext_vol.setRange(0, 200)
        self.slider_ext_vol.setValue(int(self.settings.get("track_ext_vol", 100)))
        r_ext_v.addWidget(self.slider_ext_vol)
        self.lbl_ext_vol = QLabel(f"{self.slider_ext_vol.value()}%", self)
        self.lbl_ext_vol.setFixedWidth(38)
        self.slider_ext_vol.valueChanged.connect(lambda v: self.lbl_ext_vol.setText(f"{v}%"))
        r_ext_v.addWidget(self.lbl_ext_vol)
        l_ext.addLayout(r_ext_v)

        r_ext_o = QHBoxLayout()
        r_ext_o.addWidget(QLabel("ズレ補正:"))
        self.spin_ext_off = QSpinBox(self)
        self.spin_ext_off.setRange(-5000, 5000)
        self.spin_ext_off.setSuffix(" ms")
        self.spin_ext_off.setSingleStep(10)
        self.spin_ext_off.setFixedWidth(90)
        self.spin_ext_off.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_ext_off.setValue(int(self.settings.get("track_ext_offset_ms", 0)))
        r_ext_o.addWidget(self.spin_ext_off)
        _add_offset_stepper_buttons(r_ext_o, self.spin_ext_off)
        r_ext_o.addStretch()
        l_ext.addLayout(r_ext_o)

        main_layout.addWidget(grp_ext)

        # === Track 2: マイク録音テイク ===
        grp_rec = QFrame()
        grp_rec.setObjectName("groupFrame")
        grp_rec.setStyleSheet("QFrame#groupFrame { border: 1px solid #7F1D1D; border-radius: 6px; padding: 6px; background-color: #1A0D0D; }")
        l_rec = QVBoxLayout(grp_rec)
        l_rec.setSpacing(6)

        self.chk_rec = QCheckBox("🎙️ Track 2: マイク演奏録音 (Recording Take)", self)
        self.chk_rec.setChecked(bool(self.settings.get("track_rec_enabled", False)))
        self.chk_rec.setStyleSheet("font-weight: bold; color: #FCA5A5;")
        l_rec.addWidget(self.chk_rec)

        r_rec_f = QHBoxLayout()
        rec_path = self.settings.get("track_rec_path", "")
        self.lbl_rec_path = QLabel("テイク: " + (os.path.basename(rec_path) if rec_path else "未録音/未選択"))
        self.lbl_rec_path.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        r_rec_f.addWidget(self.lbl_rec_path, stretch=1)
        btn_browse_rec = QPushButton("📂 選択...", self)
        btn_browse_rec.setFixedWidth(70)
        btn_browse_rec.clicked.connect(self._on_browse_rec)
        r_rec_f.addWidget(btn_browse_rec)
        l_rec.addLayout(r_rec_f)

        r_rec_v = QHBoxLayout()
        r_rec_v.addWidget(QLabel("トラック音量:"))
        self.slider_rec_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_rec_vol.setRange(0, 200)
        self.slider_rec_vol.setValue(int(self.settings.get("track_rec_vol", 100)))
        r_rec_v.addWidget(self.slider_rec_vol)
        self.lbl_rec_vol = QLabel(f"{self.slider_rec_vol.value()}%", self)
        self.lbl_rec_vol.setFixedWidth(38)
        self.slider_rec_vol.valueChanged.connect(lambda v: self.lbl_rec_vol.setText(f"{v}%"))
        r_rec_v.addWidget(self.lbl_rec_vol)
        l_rec.addLayout(r_rec_v)

        r_rec_opts = QHBoxLayout()
        self.chk_rec_rev = QCheckBox("リバーブ適用", self)
        self.chk_rec_rev.setChecked(bool(self.settings.get("track_rec_reverb", False)))
        r_rec_opts.addWidget(self.chk_rec_rev)

        r_rec_opts.addSpacing(15)
        r_rec_opts.addWidget(QLabel("録音ズレ補正:"))
        self.spin_rec_off = QSpinBox(self)
        self.spin_rec_off.setRange(-2000, 2000)
        self.spin_rec_off.setSuffix(" ms")
        self.spin_rec_off.setSingleStep(10)
        self.spin_rec_off.setFixedWidth(90)
        self.spin_rec_off.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_rec_off.setValue(int(self.settings.get("track_rec_offset_ms", 0)))
        r_rec_opts.addWidget(self.spin_rec_off)
        _add_offset_stepper_buttons(r_rec_opts, self.spin_rec_off)
        r_rec_opts.addStretch()
        l_rec.addLayout(r_rec_opts)

        main_layout.addWidget(grp_rec)

        # === Track 3: MIDI内部音源 ===
        grp_midi = QFrame()
        grp_midi.setObjectName("groupFrame")
        grp_midi.setStyleSheet("QFrame#groupFrame { border: 1px solid #1E293B; border-radius: 6px; padding: 6px; background-color: #0F172A; }")
        l_midi = QVBoxLayout(grp_midi)
        l_midi.setSpacing(6)

        self.chk_midi = QCheckBox("🎹 Track 3: MIDI内部音源 (Internal Synth)", self)
        self.chk_midi.setChecked(bool(self.settings.get("track_midi_enabled", False)))
        self.chk_midi.setStyleSheet("font-weight: bold; color: #A7F3D0;")
        l_midi.addWidget(self.chk_midi)

        r_midi_m = QHBoxLayout()
        r_midi_m.addWidget(QLabel("再生パート:"))
        self.combo_midi_mode = QComboBox(self)
        self.combo_midi_mode.addItems([
            "伴奏のみ (主旋律ミュート・カラオケ推奨)",
            "全パート再生 (主旋律＋伴奏)",
            "主旋律のみ (ガイドメロディ)"
        ])
        mode_str = str(self.settings.get("track_midi_mode", "伴奏のみ (主旋律ミュート・カラオケ推奨)"))
        for idx in range(self.combo_midi_mode.count()):
            if mode_str in self.combo_midi_mode.itemText(idx) or self.combo_midi_mode.itemText(idx).startswith(mode_str[:4]):
                self.combo_midi_mode.setCurrentIndex(idx)
                break
        r_midi_m.addWidget(self.combo_midi_mode, stretch=1)
        l_midi.addLayout(r_midi_m)

        r_midi_v = QHBoxLayout()
        r_midi_v.addWidget(QLabel("トラック音量:"))
        self.slider_midi_vol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_midi_vol.setRange(0, 200)
        self.slider_midi_vol.setValue(int(self.settings.get("track_midi_vol", 100)))
        r_midi_v.addWidget(self.slider_midi_vol)
        self.lbl_midi_vol = QLabel(f"{self.slider_midi_vol.value()}%", self)
        self.lbl_midi_vol.setFixedWidth(38)
        self.slider_midi_vol.valueChanged.connect(lambda v: self.lbl_midi_vol.setText(f"{v}%"))
        r_midi_v.addWidget(self.lbl_midi_vol)
        l_midi.addLayout(r_midi_v)

        r_midi_opts = QHBoxLayout()
        r_midi_opts.addWidget(QLabel("MIDIズレ補正:"))
        self.spin_midi_off = QSpinBox(self)
        self.spin_midi_off.setRange(-2000, 2000)
        self.spin_midi_off.setSuffix(" ms")
        self.spin_midi_off.setSingleStep(10)
        self.spin_midi_off.setFixedWidth(90)
        self.spin_midi_off.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_midi_off.setValue(int(self.settings.get("track_midi_offset_ms", 0)))
        r_midi_opts.addWidget(self.spin_midi_off)
        _add_offset_stepper_buttons(r_midi_opts, self.spin_midi_off)
        r_midi_opts.addStretch()
        l_midi.addLayout(r_midi_opts)

        main_layout.addWidget(grp_midi)

        # === プレビュー試聴 & ボタンバー ===
        r_prev = QHBoxLayout()
        self.combo_preview_pos = QComboBox(self)
        self.combo_preview_pos.addItems([
            "🎵 発音開始位置から5秒 (空白スキップ)",
            "🔥 曲の中間 (サビ付近) から5秒",
            "⏮ 曲の先頭 (0.0秒) から5秒"
        ])
        self.combo_preview_pos.setToolTip("5秒試聴を開始する位置")
        r_prev.addWidget(self.combo_preview_pos, stretch=1)

        self.btn_preview = QPushButton("▶ 5秒試聴 (ミックス確認)", self)
        self.btn_preview.setStyleSheet("font-weight: bold; padding: 6px;")
        self.btn_preview.clicked.connect(self._on_toggle_preview)
        r_prev.addWidget(self.btn_preview)
        main_layout.addLayout(r_prev)

        r_btns = QHBoxLayout()
        r_btns.addStretch()
        btn_cancel = QPushButton("キャンセル", self)
        btn_cancel.clicked.connect(self._on_cancel_and_reject)
        r_btns.addWidget(btn_cancel)

        btn_ok = QPushButton("OK (設定を適用)", self)
        btn_ok.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px;")
        btn_ok.clicked.connect(self._on_apply_and_accept)
        r_btns.addWidget(btn_ok)

        main_layout.addLayout(r_btns)

    def _on_browse_ext(self):
        p, _ = QFileDialog.getOpenFileName(self, "伴奏音源を選択", "", "オーディオ (*.mp3 *.wav *.m4a *.flac);;全ファイル (*)")
        if p:
            self.settings["track_ext_path"] = p
            self.lbl_ext_path.setText("ファイル: " + os.path.basename(p))
            self.chk_ext.setChecked(True)

    def _on_browse_rec(self):
        p, _ = QFileDialog.getOpenFileName(self, "マイク録音テイクを選択", "recordings", "WAVファイル (*.wav);;全ファイル (*)")
        if p:
            self.settings["track_rec_path"] = p
            self.lbl_rec_path.setText("テイク: " + os.path.basename(p))
            self.chk_rec.setChecked(True)

    def _stop_preview(self):
        if hasattr(self, "_preview_timer"):
            self._preview_timer.stop()
        if self._audition_player:
            self._audition_player.stop()
        self.btn_preview.setText("▶ 5秒試聴 (ミックス確認)")

    def _on_toggle_preview(self):
        if self._audition_player and self._audition_player.is_playing():
            self._stop_preview()
            return

        cfg = self.get_settings()
        if not cfg["track_ext_enabled"] and not cfg["track_rec_enabled"] and not cfg["track_midi_enabled"]:
            QMessageBox.information(self, "試聴", "有効な音声トラックが1つも選択されていません。")
            return

        self.btn_preview.setText("⏳ 合成中...")
        QApplication.processEvents()

        temp_dir = get_portable_path("temp")
        os.makedirs(temp_dir, exist_ok=True)
        self._temp_preview_wav = os.path.join(temp_dir, f"mixer_preview_{int(time.time())}.wav")

        try:
            midi_notes = self.timeline.main_notes if self.timeline else []
            acc_notes = self.timeline.accomp_notes if self.timeline else []
            measures = self.timeline.measures_timeline if self.timeline else []

            total_sec = float(getattr(self.timeline, "total_duration_sec", 60.0)) if self.timeline else 60.0
            pos_mode = self.combo_preview_pos.currentText() if hasattr(self, "combo_preview_pos") else ""
            if "先頭" in pos_mode:
                start_sec = 0.0
            elif "中間" in pos_mode:
                start_sec = max(0.0, total_sec * 0.45)
            else:  # 発音開始位置から5秒 (空白スキップ / HIGH-1)
                start_sec = 0.0
                earliest_notes = []
                if self.timeline and getattr(self.timeline, "main_notes", None):
                    earliest_notes.append(min(
                        float(n.get("start_sec", 0.0) if isinstance(n, dict) else getattr(n, "start_sec", 0.0))
                        for n in self.timeline.main_notes
                    ))
                if self.timeline and getattr(self.timeline, "accomp_notes", None):
                    earliest_notes.append(min(
                        float(n.get("start_sec", 0.0) if isinstance(n, dict) else getattr(n, "start_sec", 0.0))
                        for n in self.timeline.accomp_notes
                    ))
                if earliest_notes:
                    start_sec = max(0.0, min(earliest_notes) - 0.2)

            synth_eng = getattr(self.parent(), "user_settings", {}).get("synth_engine", "Windows標準MIDI (推奨)") if self.parent() else "Windows標準MIDI (推奨)"
            bpm_val = float(getattr(self.timeline, "default_bpm", 120.0)) if self.timeline else 120.0
            synthesize_midi_to_wav(
                midi_notes=midi_notes,
                current_bpm=bpm_val,
                max_duration=5.0,
                is_count_in=False,
                is_metro=False,
                output_wav_path=self._temp_preview_wav,
                measures_timeline=measures,
                sample_rate=44100,
                accompaniment_notes=acc_notes,
                sec_a_in_song=start_sec,
                mixer_settings=cfg,
                yt_limiter=True,
                synth_engine=synth_eng
            )

            if not self._audition_player:
                self._audition_player = AuditionPlayer()
            self._audition_player.play(self._temp_preview_wav, volume=1.0)
            self._preview_timer.start(5200)
            self.btn_preview.setText("⏹ 試聴停止")
        except Exception as e:
            QMessageBox.warning(self, "試聴エラー", f"ミキサー試聴合成に失敗しました:\n{e}")
            self._stop_preview()

    def _on_apply_and_accept(self):
        self._stop_preview()
        self.result_settings = self.get_settings()
        QTimer.singleShot(0, self.accept)

    def _on_cancel_and_reject(self):
        self._stop_preview()
        QTimer.singleShot(0, self.reject)

    def get_settings(self) -> dict:
        return {
            "track_ext_enabled": bool(self.chk_ext.isChecked()),
            "track_ext_path": self.settings.get("track_ext_path", ""),
            "track_ext_vol": int(self.slider_ext_vol.value()),
            "track_ext_offset_ms": int(self.spin_ext_off.value()),

            "track_rec_enabled": bool(self.chk_rec.isChecked()),
            "track_rec_path": self.settings.get("track_rec_path", ""),
            "track_rec_vol": int(self.slider_rec_vol.value()),
            "track_rec_reverb": bool(self.chk_rec_rev.isChecked()),
            "track_rec_offset_ms": int(self.spin_rec_off.value()),

            "track_midi_enabled": bool(self.chk_midi.isChecked()),
            "track_midi_mode": self.combo_midi_mode.currentText(),
            "track_midi_vol": int(self.slider_midi_vol.value()),
            "track_midi_offset_ms": int(self.spin_midi_off.value()) if hasattr(self, "spin_midi_off") else 0,
        }

    def closeEvent(self, event):
        self._stop_preview()
        super().closeEvent(event)
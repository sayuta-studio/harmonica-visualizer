# -*- coding: utf-8 -*-
"""
v3.0/dialogs.py
Chromatic Harmonica Visualizer v3.0 - モーダルダイアログ群
- HarmonicaSettingsDialog: 外観テーマ・装飾・練習・音響の総合設定
- PartSelectDialog: MIDI全トラック一覧・主旋律トラック選定
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QImage
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QPushButton, QComboBox, QSlider, QSpinBox, QAbstractSpinBox, QCheckBox, QColorDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup,
    QFrame, QMessageBox, QLineEdit, QProgressBar
)

from settings_manager import THEME_PRESETS, DEFAULT_SETTINGS
from midi_timeline import get_gm_instrument_name


class HarmonicaSettingsDialog(QDialog):
    """総合詳細設定ダイアログ"""

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("詳細環境設定 (Settings)")
        self.resize(540, 480)
        self.setModal(True)

        self.settings = dict(current_settings)

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # タブウィジェット
        self.tabs = QTabWidget(self)

        # --- タブ 1: 画面・テーマ設定 ---
        tab_view = QWidget()
        v_layout = QVBoxLayout(tab_view)
        v_layout.setSpacing(10)

        # テーマ選択行
        row_theme = QHBoxLayout()
        row_theme.addWidget(QLabel("カラーテーマ:"))
        self.combo_theme = QComboBox(self)
        self.combo_theme.addItems(["ノーマル", "サクラ", "クールネオン", "モノクロ", "カスタム"])
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed)
        row_theme.addWidget(self.combo_theme)
        row_theme.addStretch()
        v_layout.addLayout(row_theme)

        # 吹音・吸音カラーピッカー行
        row_colors = QHBoxLayout()
        row_colors.addWidget(QLabel("吹音色 (Blow):"))
        self.btn_color_blow = QPushButton("", self)
        self.btn_color_blow.setFixedSize(50, 24)
        self.btn_color_blow.clicked.connect(self._choose_color_blow)
        row_colors.addWidget(self.btn_color_blow)

        row_colors.addSpacing(20)
        row_colors.addWidget(QLabel("吸音色 (Draw):"))
        self.btn_color_draw = QPushButton("", self)
        self.btn_color_draw.setFixedSize(50, 24)
        self.btn_color_draw.clicked.connect(self._choose_color_draw)
        row_colors.addWidget(self.btn_color_draw)
        row_colors.addStretch()
        v_layout.addLayout(row_colors)

        # レバーON装飾行
        row_lever = QHBoxLayout()
        row_lever.addWidget(QLabel("レバーON装飾:"))
        self.combo_lever = QComboBox(self)
        self.combo_lever.addItems(["センターライン (芯線)", "スリット (2本線)", "なし"])
        row_lever.addWidget(self.combo_lever)
        row_lever.addStretch()
        v_layout.addLayout(row_lever)

        # ノーツ不透過度行
        row_opacity = QHBoxLayout()
        row_opacity.addWidget(QLabel("ノーツ不透過度:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_opacity.setRange(20, 100)
        self.slider_opacity.setValue(100)
        self.lbl_opacity_val = QLabel("100%", self)
        self.lbl_opacity_val.setMinimumWidth(38)
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        row_opacity.addWidget(self.slider_opacity)
        row_opacity.addWidget(self.lbl_opacity_val)
        v_layout.addLayout(row_opacity)

        # 描画オプションチェックボックス
        self.chk_notes = QCheckBox("落下ノーツを表示", self)
        self.chk_lookahead = QCheckBox("ノーツ直上に音名ラベルを表示", self)
        self.chk_grid = QCheckBox("レーンガイド線（オクターブ変形線）を表示", self)
        self.chk_bar_lines = QCheckBox("小節線を表示", self)
        self.chk_hole_num = QCheckBox("ハーモニカ穴番号を表示", self)
        self.chk_legend = QCheckBox("右下に吹吸凡例を表示", self)

        v_layout.addWidget(self.chk_notes)
        v_layout.addWidget(self.chk_lookahead)
        v_layout.addWidget(self.chk_grid)
        v_layout.addWidget(self.chk_bar_lines)
        v_layout.addWidget(self.chk_hole_num)
        v_layout.addWidget(self.chk_legend)
        v_layout.addStretch()

        self.tabs.addTab(tab_view, "🎨 画面・外観")

        # --- タブ 2: 練習・音響設定 ---
        tab_practice = QWidget()
        p_layout = QVBoxLayout(tab_practice)
        p_layout.setSpacing(10)

        # ステップアップ練習グループ
        p_layout.addWidget(QLabel("<b>【ステップアップ練習設定】</b>"))
        self.chk_stepup = QCheckBox("A-Bループ折り返し時に再生速度を自動アップ", self)
        p_layout.addWidget(self.chk_stepup)

        row_sp = QHBoxLayout()
        row_sp.addWidget(QLabel("開始速度:"))
        self.spin_sp_start = QSpinBox(self)
        self.spin_sp_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_sp_start.setRange(30, 200)
        self.spin_sp_start.setSuffix("%")
        self.spin_sp_start.setValue(70)
        self.spin_sp_start.setToolTip("練習開始時の再生速度% [直接入力 / マウスホイールで変更]")
        row_sp.addWidget(self.spin_sp_start)

        row_sp.addWidget(QLabel("目標速度:"))
        self.spin_sp_target = QSpinBox(self)
        self.spin_sp_target.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_sp_target.setRange(50, 250)
        self.spin_sp_target.setSuffix("%")
        self.spin_sp_target.setValue(100)
        self.spin_sp_target.setToolTip("到達目標の再生速度% [直接入力 / マウスホイールで変更]")
        row_sp.addWidget(self.spin_sp_target)

        row_sp.addWidget(QLabel("1周増分:"))
        self.combo_sp_step = QComboBox(self)
        self.combo_sp_step.addItems(["+1%", "+2%", "+5%", "+10%"])
        self.combo_sp_step.setCurrentText("+5%")
        row_sp.addWidget(self.combo_sp_step)
        row_sp.addStretch()
        p_layout.addLayout(row_sp)

        p_layout.addSpacing(10)

        # メトロノーム設定
        p_layout.addWidget(QLabel("<b>【メトロノーム設定】</b>"))
        row_metro = QHBoxLayout()
        row_metro.addWidget(QLabel("クリックパターン:"))
        self.combo_metro = QComboBox(self)
        self.combo_metro.addItems(["なし", "標準（頭拍強調）", "小節頭のみ", "全拍均一"])
        row_metro.addWidget(self.combo_metro)
        row_metro.addStretch()
        p_layout.addLayout(row_metro)

        p_layout.addSpacing(10)

        # 音響オプション
        p_layout.addWidget(QLabel("<b>【MIDI音響設定】</b>"))
        self.chk_force_harmonica = QCheckBox("主旋律をクロマチックハーモニカ音色 (GM Program 22) に強制ルーティング", self)
        p_layout.addWidget(self.chk_force_harmonica)
        p_layout.addStretch()

        self.tabs.addTab(tab_practice, "🎵 練習・音響")
        main_layout.addWidget(self.tabs)

        # --- 最下部: ボタンバー ---
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

    def _load_values(self):
        """現在の設定値を各UI要素に反映"""
        s = self.settings
        self.combo_theme.setCurrentText(s.get("color_theme", "ノーマル"))
        self._update_color_button(self.btn_color_blow, s.get("color_blow", "#FF5500"))
        self._update_color_button(self.btn_color_draw, s.get("color_draw", "#00BFFF"))
        self.combo_lever.setCurrentText(s.get("lever_deco_mode", "センターライン (芯線)"))
        op = int(s.get("note_opacity", 100))
        self.slider_opacity.setValue(op)
        self.lbl_opacity_val.setText(f"{op}%")

        self.chk_notes.setChecked(bool(s.get("show_notes", True)))
        self.chk_lookahead.setChecked(bool(s.get("show_lookahead", True)))
        self.chk_grid.setChecked(bool(s.get("show_grid", True)))
        self.chk_bar_lines.setChecked(bool(s.get("show_bar_lines", True)))
        self.chk_hole_num.setChecked(bool(s.get("show_hole_num", True)))
        self.chk_legend.setChecked(bool(s.get("show_legend", True)))

        self.chk_stepup.setChecked(bool(s.get("stepup_enabled", False)))
        self.spin_sp_start.setValue(int(s.get("stepup_start_pct", 70)))
        self.spin_sp_target.setValue(int(s.get("stepup_target_pct", 100)))
        inc = s.get("stepup_step_pct", 5)
        self.combo_sp_step.setCurrentText(f"+{inc}%")

        self.combo_metro.setCurrentText(s.get("metronome_mode", "標準（頭拍強調）"))
        self.chk_force_harmonica.setChecked(bool(s.get("force_harmonica", True)))

    def _update_color_button(self, btn: QPushButton, hex_code: str):
        btn.setStyleSheet(f"background-color: {hex_code}; border: 1px solid #FFFFFF; border-radius: 4px;")
        btn.setToolTip(hex_code)

    def _choose_color_blow(self):
        cur = QColor(self.settings.get("color_blow", "#FF5500"))
        col = QColorDialog.getColor(cur, self, "吹音色 (Blow) の選択")
        if col.isValid():
            hex_str = col.name().upper()
            self.settings["color_blow"] = hex_str
            self._update_color_button(self.btn_color_blow, hex_str)
            self.combo_theme.setCurrentText("カスタム")

    def _choose_color_draw(self):
        cur = QColor(self.settings.get("color_draw", "#00BFFF"))
        col = QColorDialog.getColor(cur, self, "吸音色 (Draw) の選択")
        if col.isValid():
            hex_str = col.name().upper()
            self.settings["color_draw"] = hex_str
            self._update_color_button(self.btn_color_draw, hex_str)
            self.combo_theme.setCurrentText("カスタム")

    def _on_theme_changed(self, theme_name: str):
        if theme_name in THEME_PRESETS:
            blow, draw = THEME_PRESETS[theme_name]
            self.settings["color_blow"] = blow
            self.settings["color_draw"] = draw
            self._update_color_button(self.btn_color_blow, blow)
            self._update_color_button(self.btn_color_draw, draw)

    def _on_reset_defaults(self):
        reply = QMessageBox.question(
            self, "確認", "全設定を初期状態にリセットしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.update(DEFAULT_SETTINGS)
            self._load_values()

    def _on_save_clicked(self):
        """全入力を辞書に反映してダイアログ受諾"""
        s = self.settings
        s["color_theme"] = self.combo_theme.currentText()
        s["lever_deco_mode"] = self.combo_lever.currentText()
        s["note_opacity"] = self.slider_opacity.value()

        s["show_notes"] = self.chk_notes.isChecked()
        s["show_lookahead"] = self.chk_lookahead.isChecked()
        s["show_grid"] = self.chk_grid.isChecked()
        s["show_bar_lines"] = self.chk_bar_lines.isChecked()
        s["show_hole_num"] = self.chk_hole_num.isChecked()
        s["show_legend"] = self.chk_legend.isChecked()

        s["stepup_enabled"] = self.chk_stepup.isChecked()
        s["stepup_start_pct"] = self.spin_sp_start.value()
        s["stepup_target_pct"] = self.spin_sp_target.value()
        try:
            s["stepup_step_pct"] = int(self.combo_sp_step.currentText().replace("+", "").replace("%", ""))
        except ValueError:
            s["stepup_step_pct"] = 5

        s["metronome_mode"] = self.combo_metro.currentText()
        s["force_harmonica"] = self.chk_force_harmonica.isChecked()

        self.accept()

    def get_settings(self) -> dict:
        return self.settings


class PartSelectDialog(QDialog):
    """MIDI全トラック一覧表示 ＆ 主旋律ハーモニカ対象トラック選定ダイアログ (複数トラック複合対応)"""

    def __init__(self, tracks_info: list, current_main_idx: int = 0, parent=None,
                 current_main_indices: list = None, current_accomp_indices: list = None):
        super().__init__(parent)
        self.setWindowTitle("MIDIパート詳細・主旋律トラック選定 (複数複合対応)")
        self.resize(780, 420)
        self.setModal(True)

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

        self.setWindowTitle(f"🎼 変え指エディタ (Custom Fingering Editor) - {timeline.filename}")
        self.resize(960, 620)
        self.setMinimumSize(780, 480)
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
        hdr_frame.setStyleSheet("background-color: #161622; border: 1px solid #272738; border-radius: 6px; padding: 6px;")
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

        # 2. フィルタ＆プリセット操作バー
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # 運指プリセット
        ctrl_layout.addWidget(QLabel("運指プリセット:"))
        self.combo_preset = QComboBox(self)
        self.combo_preset.addItems(["スライド最小化", "スライド優先", "標準"])
        from harmonica_map import CURRENT_SONG_PRESET, CURRENT_MONOPHONIC_MODE
        self.combo_preset.setCurrentText(CURRENT_SONG_PRESET)
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

        # 3. ノーツ一覧テーブル (9列: 発音/除外 状態を含む)
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
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
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

        # 4. フッターボタンバー
        foot_layout = QHBoxLayout()
        foot_layout.setSpacing(10)

        btn_reset = QPushButton("🔄 この曲の運指を初期化 (リセット)", self)
        btn_reset.setStyleSheet("background-color: #501F1F; color: #FECACA; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_reset.clicked.connect(self._on_reset_all)
        foot_layout.addWidget(btn_reset)

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
            if is_muted:
                it_mb.setForeground(dim_col)
            self.table.setItem(r, 2, it_mb)

            # Col 3: タイム
            sec = nd["start_sec"]
            it_time = QTableWidgetItem(f"{int(sec // 60):02d}:{sec % 60:05.2f}")
            it_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_muted:
                it_time.setForeground(dim_col)
            self.table.setItem(r, 3, it_time)

            # Col 4: 音名
            it_name = QTableWidgetItem(f"{nd.get('name_jp', '')} ({nd.get('name_cde', '')})")
            it_name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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
                it_fix.setForeground(dim_col)
                self.table.setItem(r, 6, it_fix)

                it_dash = QTableWidgetItem("-")
                it_dash.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_dash.setForeground(dim_col)
                self.table.setItem(r, 7, it_dash)

            # Col 8: 状態
            if is_muted:
                it_stat = QTableWidgetItem("除外中")
                it_stat.setForeground(QColor("#F87171"))
            elif is_custom:
                it_stat = QTableWidgetItem("★ カスタム")
                it_stat.setForeground(QColor("#34D399"))
            else:
                it_stat = QTableWidgetItem("標準")
                it_stat.setForeground(dim_col)
            it_stat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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

    def _on_candidate_changed(self, row: int, nd: dict, lookup_note: int, candidates: list, new_idx: int):
        """候補コンボ変更時のリアルタイム反映"""
        from harmonica_map import SONG_FINGERING_OVERRIDES, save_song_fingering

        start_tick = nd["start_tick"]
        SONG_FINGERING_OVERRIDES[(start_tick, lookup_note)] = new_idx

        # ファイル自動保存
        if self.timeline and self.timeline.filepath:
            save_song_fingering(self.timeline.filepath)

        # タイムライン再バインド
        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        # GLキャッシュ更新
        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()

        # 音響クリックフィードバック
        if self.audio_engine:
            self.audio_engine.play_ui_click()

        # テーブルのCol 5 (現在の運指) と Col 8 (状態) を更新
        new_cand = candidates[new_idx]
        f_str = f"{new_cand['hole']}穴 {new_cand['action']} {new_cand['lever']}"
        it_fing = self.table.item(row, 5)
        if it_fing:
            it_fing.setText(f_str)
            if new_cand["action"] == "吹":
                it_fing.setForeground(QColor("#FF7A33"))
            else:
                it_fing.setForeground(QColor("#38BDF8"))

        it_stat = self.table.item(row, 8)
        if it_stat:
            it_stat.setText("★ カスタム")
            it_stat.setForeground(QColor("#34D399"))

    def _toggle_note_mute(self, nd: dict):
        """ノーツの発音/除外 (Mute) 状態を反転"""
        start_sec = nd["start_sec"]
        raw_pitch = nd.get("raw_note", nd["note"])
        key = f"{round(start_sec, 3)}_{raw_pitch}"
        new_muted = not nd.get("is_muted", False)
        from harmonica_map import SONG_MUTED_NOTES, save_song_profile
        SONG_MUTED_NOTES[key] = new_muted

        # 単音化モード（高音優先/低音優先）設定時のみ、有効化した際に同タイミングの重複ノーツを自動除外 (シーソー動作)
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
            if self.timeline.filepath:
                save_song_profile(self.timeline.filepath)
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        if self.audio_engine:
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)
            self.audio_engine.play_ui_click()

        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()

        self._populate_table()

    def _on_monophonic_mode_changed(self, mode: str):
        """重なり音（単音化モード）変更"""
        import harmonica_map
        harmonica_map.CURRENT_MONOPHONIC_MODE = mode
        if self.timeline:
            self.timeline.set_monophonic_mode(mode)
            if self.timeline.filepath:
                harmonica_map.save_song_profile(self.timeline.filepath)

        if self.audio_engine:
            self.audio_engine.load_timeline(self.timeline)
            self.audio_engine.seek(self.clock.get_current_base_sec() if self.clock else 0.0)

        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()
            self.gl_widget.update()

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

        if self.timeline and self.timeline.filepath:
            harmonica_map.save_song_fingering(self.timeline.filepath)

        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)

        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()

        self._populate_table()

    def _on_reset_all(self):
        """この曲の個別カスタム運指を初期化"""
        ans = QMessageBox.question(
            self,
            "運指データの初期化確認",
            "この曲のすべての個別変え指設定を初期化し、\n初期状態に戻しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            from harmonica_map import reset_song_fingering
            reset_song_fingering(self.timeline.filepath)
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
        """保存して閉じる"""
        from harmonica_map import save_song_fingering
        if self.timeline and self.timeline.filepath:
            save_song_fingering(self.timeline.filepath)
        if self.timeline:
            self.timeline.rebind_fingerings(self.timeline.inst_type)
        if self.gl_widget:
            self.gl_widget.invalidate_static_cache()
        self.accept()



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
            self.lbl_frame_info.setText(f"ファイル保存完了: {os.path.basename(output_path)}")
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
        folder = os.path.dirname(self.output_path)
        subprocess.Popen(f'explorer "{folder}"')

    def closeEvent(self, event):
        if not self.is_done:
            self.export_thread.cancel()
        super().closeEvent(event)


class SingleFramePreviewDialog(QDialog):
    """1フレーム静止画プレビュー確認ダイアログ (Full HD等の解像度確認用)"""

    def __init__(self, qimage: QImage, info_text: str = "", parent=None):
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

        # アスペクト比を維持して最大表示
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

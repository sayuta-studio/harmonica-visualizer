# -*- coding: utf-8 -*-
# gui.py (Ver.2.10: スタイリッシュ＆スリム化・4タブ再編・録音ボタン配備版)
# - 🚀【上部操作バー刷新】：2段目「▶ 再生」の真下に「🔴 録音」ボタンを配備し、DAW準拠の直感レイアウトを実現。
# - 🚀【4タブ再編】：作業フロー順に「🎵 練習」「🎙️ 録音・音響」「🎨 画面作り」「🎬 動画出力」へ整理。
# - 🚀【画面作りの動線統合】：アスペクト比 ➔ 背景画像 ➔ タイトル ➔ ノーツ色・表示パーツが一連の流れで完結し、タブ間の行き来を根絶。
# - 🚀【スリム＆スタイリッシュ化】：余白をデトックスし、ダーク調で洗練されたコンパクトデザインを採用。
# - 🚀【スクロール対応】：全タブを CTkScrollableFrame 化し、解像度を問わず見切れを防止。

import tkinter as tk
import customtkinter as ctk

class HarmonicaAppGUI(ctk.CTkFrame):
    def __init__(self, parent, controller):
        """
        L字型UIウィジェットの物理的な配置・生成を担当。
        """
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.controller = controller

        self.canvas_bg_color = "#0d0d0d"
        self.pack(fill="both", expand=True)

        self.create_widgets()

    def create_widgets(self):
        # スタイリッシュで引き締まったタイポグラフィ
        self.f_bold = ("Segoe UI", 11, "bold")
        self.f_norm = ("Segoe UI", 11)
        self.f_jp_bold = ("Meiryo", 11, "bold") 
        self.f_jp_norm = ("Meiryo", 11)        

        # ==========================================
        # 1. 操作パネル (上部: 高さ150pxにスリム化)
        # ==========================================
        self.top_frame = ctk.CTkFrame(self, height=150, corner_radius=10, fg_color="#181818", border_width=1, border_color="#262626")
        self.top_frame.pack(side="top", fill="x", padx=10, pady=(8, 4))
        self.top_frame.pack_propagate(False)

        # 3段の操作ストリップ（高さ38px固定で無駄な余白を削減）
        self.row1 = ctk.CTkFrame(self.top_frame, fg_color="transparent", height=38)
        self.row1.pack(fill="x", padx=16, pady=(10, 2))
        self.row1.pack_propagate(False)

        self.row2 = ctk.CTkFrame(self.top_frame, fg_color="transparent", height=38)
        self.row2.pack(fill="x", padx=16, pady=2)
        self.row2.pack_propagate(False)

        self.row3 = ctk.CTkFrame(self.top_frame, fg_color="transparent", height=38)
        self.row3.pack(fill="x", padx=16, pady=(2, 6))  
        self.row3.pack_propagate(False)

        # セパレーター生成ヘルパー
        def create_sep(parent):
            return ctk.CTkLabel(parent, text="|", text_color="#333333", font=self.f_bold)

        # ----------------------------------------------------------------------
        # ■ 1行目：ファイル読込 ＋ パート選択 ＋ 小節ジャンプ ＋ 速度%
        # ----------------------------------------------------------------------
        self.file_btn = ctk.CTkButton(
            self.row1, text="📂 MIDIを開く", width=95, height=26, font=self.f_jp_bold,
            fg_color="#1f538d", hover_color="#143963",
            command=self.controller.on_open_file
        )
        self.file_btn.pack(side="left", padx=(0, 6))

        self.file_label_box = ctk.CTkFrame(self.row1, width=240, height=26, fg_color="#111111", corner_radius=6)
        self.file_label_box.pack(side="left", padx=(0, 6))
        self.file_label_box.pack_propagate(False)

        self.file_label = ctk.CTkLabel(self.file_label_box, text="demo.mid", text_color="#38bdf8", font=self.f_bold, anchor="w")
        self.file_label.pack(side="left", fill="both", expand=True, padx=8)

        # 右側コントロール群
        self.row1_right = ctk.CTkFrame(self.row1, fg_color="transparent")
        self.row1_right.pack(side="right", padx=(0, 4))

        # パート選択 ＆ 再生モード
        self.part_select_btn = ctk.CTkButton(
            self.row1_right, text="🎼 パート選択", width=95, height=26, font=self.f_jp_bold,
            fg_color="#2b5b84", hover_color="#1f4361",
            command=self.controller.open_part_select_dialog
        )
        self.part_select_btn.pack(side="left", padx=(0, 4))

        self.part_play_mode_menu = ctk.CTkOptionMenu(
            self.row1_right, values=["全パート再生", "主旋律ソロ", "伴奏のみ(カラオケ)"],
            width=145, height=26, font=self.f_jp_bold,
            command=self.controller.on_part_play_mode_changed
        )
        self.part_play_mode_menu.set("全パート再生")
        self.part_play_mode_menu.pack(side="left", padx=(0, 4))

        create_sep(self.row1_right).pack(side="left", padx=8)

        # 小節ジャンプ
        self.jump_title_lbl = ctk.CTkLabel(self.row1_right, text="小節:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.jump_title_lbl.pack(side="left", padx=(0, 2))

        self.jump_entry = ctk.CTkEntry(self.row1_right, width=38, height=26, font=self.f_norm, justify="center")
        self.jump_entry.insert(0, "1")
        self.jump_entry.pack(side="left", padx=2)
        self.jump_entry.bind("<Return>", lambda e: self.controller.on_jump_measure())

        self.jump_label = ctk.CTkLabel(self.row1_right, text=" / 1 小節", text_color="#aaaaaa", font=self.f_jp_bold)
        self.jump_label.pack(side="left", padx=2)

        self.jump_btn = ctk.CTkButton(self.row1_right, text="Go", width=32, height=26, font=self.f_bold, command=self.controller.on_jump_measure)
        self.jump_btn.pack(side="left", padx=(2, 4))

        create_sep(self.row1_right).pack(side="left", padx=8)

        # 再生速度(%)
        self.bpm_title_label = ctk.CTkLabel(self.row1_right, text="速度:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.bpm_title_label.pack(side="left", padx=(0, 2))

        self.bpm_minus_btn = ctk.CTkButton(self.row1_right, text="-5%", width=34, height=26, font=self.f_bold, fg_color="#333333", hover_color="#444444", command=lambda: self.controller.step_speed_percent(-5))
        self.bpm_minus_btn.pack(side="left", padx=1)

        self.bpm_entry = ctk.CTkEntry(self.row1_right, width=42, height=26, font=self.f_norm, justify="center")
        self.bpm_entry.insert(0, "100")
        self.bpm_entry.pack(side="left", padx=1)
        self.bpm_entry.bind("<Return>", lambda e: self.controller.apply_bpm())
        self.bpm_entry.bind("<FocusOut>", lambda e: self.controller.apply_bpm())

        self.bpm_plus_btn = ctk.CTkButton(self.row1_right, text="+5%", width=34, height=26, font=self.f_bold, fg_color="#333333", hover_color="#444444", command=lambda: self.controller.step_speed_percent(5))
        self.bpm_plus_btn.pack(side="left", padx=1)

        self.default_bpm_btn = ctk.CTkButton(self.row1_right, text="100%", width=42, height=26, font=self.f_norm, fg_color="#2b5b84", hover_color="#1f4361", command=self.controller.reset_bpm)
        self.default_bpm_btn.pack(side="left", padx=(2, 0))

        # ----------------------------------------------------------------------
        # ■ 2行目：トランスポート（再生・一時停止・停止） ➔ シーク ➔ LCD表示
        # ----------------------------------------------------------------------
        self.play_btn = ctk.CTkButton(self.row2, text="▶ 再生", width=75, height=26, font=self.f_jp_bold, fg_color="#2b8c54", hover_color="#1f6b3e", command=self.controller.on_play)
        self.play_btn.pack(side="left", padx=2)

        self.pause_btn = ctk.CTkButton(self.row2, text="⏸ 一時停止", width=75, height=26, font=self.f_jp_bold, fg_color="#d97706", hover_color="#b45309", command=self.controller.on_pause)
        self.pause_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(self.row2, text="■ 停止", width=75, height=26, font=self.f_jp_bold, fg_color="#dc2626", hover_color="#b91c1c", command=self.controller.on_stop)
        self.stop_btn.pack(side="left", padx=(2, 8))

        create_sep(self.row2).pack(side="left", padx=4)

        # シークスライダー
        self.seek_label = ctk.CTkLabel(self.row2, text="00:00 / 00:00", font=("Courier New", 11, "bold"))
        self.seek_label.pack(side="left", padx=(4, 6))

        self.seek_slider = ctk.CTkSlider(self.row2, from_=0, to=100, command=self.controller.on_seek_drag)
        self.seek_slider.set(0)
        self.seek_slider.pack(side="left", fill="x", expand=True, padx=(0, 12))

        create_sep(self.row2).pack(side="left", padx=4)

        # LCD風ステータス液晶
        self.lcd_frame = ctk.CTkFrame(self.row2, fg_color="#0a0a0a", border_width=1, border_color="#222222", width=540, height=28, corner_radius=4)
        self.lcd_frame.pack(side="right", padx=(0, 4))
        self.lcd_frame.pack_propagate(False)

        self.lbl_lcd_status = ctk.CTkLabel(self.lcd_frame, text="停止中", text_color="#00ffcc", font=("Courier New", 11, "bold"), width=90, anchor="w")
        self.lbl_lcd_status.pack(side="left", padx=(8, 2))

        self.lbl_lcd_split = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split.pack(side="left")

        self.lbl_lcd_pos = ctk.CTkLabel(self.lcd_frame, text="位置: 001小節 . 01拍", text_color="#00ffcc", font=("Courier New", 11, "bold"), width=160, anchor="w")
        self.lbl_lcd_pos.pack(side="left", padx=(8, 2))

        self.lbl_lcd_split2 = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split2.pack(side="left")

        self.lbl_lcd_sig = ctk.CTkLabel(self.lcd_frame, text="拍子: 4/4", text_color="#00ffcc", font=("Courier New", 11, "bold"), width=70, anchor="w")
        self.lbl_lcd_sig.pack(side="left", padx=(8, 2))

        self.lbl_lcd_split3 = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split3.pack(side="left")

        self.lbl_lcd_bpm = ctk.CTkLabel(self.lcd_frame, text="テンポ:120BPM(100%)", text_color="#00ffcc", font=("Courier New", 11, "bold"), width=140, anchor="w")
        self.lbl_lcd_bpm.pack(side="left", padx=(6, 2))

        # ----------------------------------------------------------------------
        # ■ 3行目：🔴 録音ボタン ＋ メトロノーム ＋ A-Bループ ＋ 落下速度
        # ----------------------------------------------------------------------
        # 🚀【新設】：再生ボタンの真下に配置されたワンクリック録音ボタン
        record_cmd = getattr(self.controller, "on_record_toggle", self.controller.on_play)
        self.record_btn = ctk.CTkButton(
            self.row3, text="🔴 録音", width=75, height=26, font=self.f_jp_bold,
            fg_color="#991b1b", hover_color="#dc2626",
            command=record_cmd
        )
        self.record_btn.pack(side="left", padx=2)

        create_sep(self.row3).pack(side="left", padx=6)

        self.metro_lbl_title = ctk.CTkLabel(self.row3, text="メトロノーム:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.metro_lbl_title.pack(side="left", padx=(0, 4))
        
        self.metro_menu = ctk.CTkOptionMenu(
            self.row3, 
            values=["標準（頭拍強調）", "小節頭のみ", "強調なし全拍", "なし"], 
            width=130, height=26,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm, 
            command=self.controller.on_metro_menu_changed
        )
        self.metro_menu.pack(side="left", padx=(0, 8))

        self.count_in_lbl_title = ctk.CTkLabel(self.row3, text="カウントイン:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.count_in_lbl_title.pack(side="left", padx=(0, 4))
        
        self.count_in_menu = ctk.CTkOptionMenu(
            self.row3, 
            values=["0 小節", "1 小節", "2 小節"], 
            width=80, height=26,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm, 
            command=self.controller.on_count_in_menu_changed
        )
        self.count_in_menu.set("1 小節")
        self.count_in_menu.pack(side="left", padx=(0, 8))

        create_sep(self.row3).pack(side="left", padx=8)

        # ABループ有効トグルスイッチ ＆ A点・B点小節指定
        self.cb_loop = ctk.CTkSwitch(self.row3, text="A-Bループ", font=self.f_jp_bold, command=self.controller.on_loop_toggle)
        self.cb_loop.pack(side="left", padx=(0, 6))

        self.btn_set_a = ctk.CTkButton(self.row3, text="A点", width=46, height=26, font=self.f_jp_bold, command=self.controller.set_loop_a_at_current)
        self.btn_set_a.pack(side="left", padx=1)
        
        self.loop_a_entry = ctk.CTkEntry(self.row3, width=36, height=26, font=self.f_norm, justify="center")
        self.loop_a_entry.insert(0, "1")
        self.loop_a_entry.pack(side="left", padx=1)
        self.loop_a_entry.bind("<Return>", lambda e: self.controller.on_loop_entry_changed())

        self.loop_a_lbl = ctk.CTkLabel(self.row3, text="小節頭", text_color="#00ffcc", font=self.f_jp_bold)
        self.loop_a_lbl.pack(side="left", padx=(2, 4))

        self.loop_tilde_lbl = ctk.CTkLabel(self.row3, text="〜", text_color="#aaaaaa", font=self.f_jp_bold)
        self.loop_tilde_lbl.pack(side="left", padx=2)

        self.btn_set_b = ctk.CTkButton(self.row3, text="B点", width=46, height=26, font=self.f_jp_bold, command=self.controller.set_loop_b_at_current)
        self.btn_set_b.pack(side="left", padx=1)

        self.loop_b_entry = ctk.CTkEntry(self.row3, width=36, height=26, font=self.f_norm, justify="center")
        self.loop_b_entry.insert(0, "12")
        self.loop_b_entry.pack(side="left", padx=1)
        self.loop_b_entry.bind("<Return>", lambda e: self.controller.on_loop_entry_changed())

        self.loop_b_lbl = ctk.CTkLabel(self.row3, text="小節末尾", text_color="#00ffcc", font=self.f_jp_bold)
        self.loop_b_lbl.pack(side="left", padx=(2, 6))

        self.btn_clear_loop = ctk.CTkButton(self.row3, text="解除", width=50, height=26, fg_color="#444444", hover_color="#555555", font=self.f_jp_bold, command=self.controller.reset_loop_points)
        self.btn_clear_loop.pack(side="left", padx=(2, 0))

        create_sep(self.row3).pack(side="left", padx=8)

        self.note_speed_lbl = ctk.CTkLabel(self.row3, text="落下速度:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.note_speed_lbl.pack(side="left", padx=(0, 4))

        self.note_speed_menu = ctk.CTkOptionMenu(
            self.row3,
            values=["0.5x", "0.75x", "1.0x (標準)", "1.25x", "1.5x", "2.0x"],
            width=100, height=26,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.note_speed_menu.set("1.0x (標準)")
        self.note_speed_menu.pack(side="left", padx=(0, 4))


        # ==========================================
        # 2. メインL字領域 (下部)
        # ==========================================
        self.main_lower_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_lower_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=(0, 8))

        # 左下：練習用Canvas (960x540基準、アスペクト可変アウターフレーム)
        self.canvas_frame = ctk.CTkFrame(self.main_lower_frame, width=1000, height=600, corner_radius=10, fg_color="#141414")
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.canvas_frame.pack_propagate(False)

        self.canvas = tk.Canvas(self.canvas_frame, width=960, height=540, bg=self.canvas_bg_color, highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")

        # 右下：4タブ切替サイドバー (幅360px固定：「🎵 練習」「🎙️ 録音・音響」「🎨 画面作り」「🎬 動画出力」)
        self.right_frame = ctk.CTkFrame(self.main_lower_frame, width=360, corner_radius=10, fg_color="#181818", border_width=1, border_color="#262626")
        self.right_frame.pack(side="right", fill="y", padx=(2, 0))
        self.right_frame.pack_propagate(False)

        # 最上部：モード切替セグメントボタン（新4タブ：練習 ➔ 画面作り ➔ 録音・音響 ➔ 動画出力）
        self.sidebar_mode_seg = ctk.CTkSegmentedButton(
            self.right_frame,
            values=["🎵 練習", "🎨 画面作り", "🎙️ 録音・音響", "🎬 動画出力"],
            font=ctk.CTkFont(family="Meiryo", size=10, weight="bold"),
            height=32,
            command=self.switch_sidebar_tab
        )
        self.sidebar_mode_seg.set("🎵 練習")
        self.sidebar_mode_seg.pack(fill="x", padx=10, pady=(10, 6))

        # 最下部：ステータスラベル（全タブ共通で常時表示）
        self.status_label = ctk.CTkLabel(self.right_frame, text="待機中...", font=self.f_jp_bold, text_color="#777777")
        self.status_label.pack(side="bottom", fill="x", pady=(4, 6))

        # 🚀【見切れ根絶】：全タブコンテナを CTkScrollableFrame 化し、解像度やウィンドウサイズに関係なく快適スクロール可能に
        self.tab_practice_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.tab_design_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.tab_audio_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.tab_export_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")

        # ======================================================================
        # 🟢 タブ1：【🎵 練習】（ステップアップ ➔ 楽器タイプ ➔ ガイド音源 ➔ 運指エディタ）
        # ======================================================================
        # 1. 📈 ステップアップ練習 (A-Bループ連動)
        self.stepup_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.stepup_group.pack(fill="x", padx=6, pady=(2, 4))

        ctk.CTkLabel(self.stepup_group, text="📈 ステップアップ練習 (A-Bループ連動):", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        stepup_row1 = ctk.CTkFrame(self.stepup_group, fg_color="transparent")
        stepup_row1.pack(fill="x", padx=12, pady=2)
        self.stepup_switch = ctk.CTkSwitch(
            stepup_row1, text="ステップアップ有効", font=self.f_jp_bold,
            command=self.controller.on_stepup_toggle
        )
        self.stepup_switch.deselect()
        self.stepup_switch.pack(side="left")

        self.stepup_step_menu = ctk.CTkOptionMenu(
            stepup_row1, values=["+1%", "+2%", "+5%", "+10%"],
            width=70, height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm,
            command=self.controller.on_stepup_param_changed
        )
        self.stepup_step_menu.set("+5%")
        self.stepup_step_menu.pack(side="right")
        ctk.CTkLabel(stepup_row1, text="1周増分:", font=self.f_jp_bold, text_color="#aaaaaa").pack(side="right", padx=(0, 4))

        stepup_row2 = ctk.CTkFrame(self.stepup_group, fg_color="transparent")
        stepup_row2.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(stepup_row2, text="開始:", font=self.f_jp_bold, text_color="#aaaaaa").pack(side="left", padx=(0, 2))
        self.stepup_start_entry = ctk.CTkEntry(stepup_row2, width=44, height=24, font=self.f_norm, justify="center")
        self.stepup_start_entry.insert(0, "70")
        self.stepup_start_entry.pack(side="left", padx=2)
        self.stepup_start_entry.bind("<Return>", lambda e: self.controller.on_stepup_param_changed())
        self.stepup_start_entry.bind("<FocusOut>", lambda e: self.controller.on_stepup_param_changed())
        ctk.CTkLabel(stepup_row2, text="%", font=self.f_jp_bold, text_color="#00ffcc").pack(side="left", padx=(1, 8))

        ctk.CTkLabel(stepup_row2, text="➔ 目標:", font=self.f_jp_bold, text_color="#aaaaaa").pack(side="left", padx=(4, 2))
        self.stepup_goal_entry = ctk.CTkEntry(stepup_row2, width=44, height=24, font=self.f_norm, justify="center")
        self.stepup_goal_entry.insert(0, "100")
        self.stepup_goal_entry.pack(side="left", padx=2)
        self.stepup_goal_entry.bind("<Return>", lambda e: self.controller.on_stepup_param_changed())
        self.stepup_goal_entry.bind("<FocusOut>", lambda e: self.controller.on_stepup_param_changed())
        ctk.CTkLabel(stepup_row2, text="%", font=self.f_jp_bold, text_color="#00ffcc").pack(side="left", padx=(1, 0))

        # 2. 🎛️ 楽器タイプ ＆ 音名表記設定
        self.inst_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.inst_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.inst_group, text="🎛️ 楽器タイプ ＆ 音名表示:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        inst_row = ctk.CTkFrame(self.inst_group, fg_color="transparent")
        inst_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(inst_row, text="ハーモニカ:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.inst_menu = ctk.CTkOptionMenu(
            inst_row, values=["16穴 (C3-D7)", "12穴 標準 (C4-D7)", "12穴 バス (C1-D4)"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.inst_menu.pack(side="right", fill="x", expand=True)

        grid4_row = ctk.CTkFrame(self.inst_group, fg_color="transparent")
        grid4_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(grid4_row, text="穴下の音名:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.grid4_menu = ctk.CTkOptionMenu(
            grid4_row, values=["4音グリッド表示", "1音表示 (従来)"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.grid4_menu.set("4音グリッド表示")
        self.grid4_menu.pack(side="right", fill="x", expand=True)

        lang_row = ctk.CTkFrame(self.inst_group, fg_color="transparent")
        lang_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(lang_row, text="音名表記:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.lang_menu = ctk.CTkOptionMenu(
            lang_row, values=["CDE", "ドレミ", "なし"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.lang_menu.set("CDE")
        self.lang_menu.pack(side="right", fill="x", expand=True)

        # 3. 🔊 ガイド音源・音量設定
        self.audio_metro_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.audio_metro_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.audio_metro_group, text="🔊 ガイド音源・音量設定:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        audio_row = ctk.CTkFrame(self.audio_metro_group, fg_color="transparent")
        audio_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(audio_row, text="再生音源:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.audio_mode_menu = ctk.CTkOptionMenu(
            audio_row, values=["MIDI再生 (Windows標準音源)", "簡易再生 (内蔵軽量シンセ)", "ミュート"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_audio_mode_changed
        )
        self.audio_mode_menu.pack(side="right", fill="x", expand=True)

        vol_row = ctk.CTkFrame(self.audio_metro_group, fg_color="transparent")
        vol_row.pack(fill="x", padx=12, pady=(2, 8))
        self.volume_label = ctk.CTkLabel(vol_row, text="音量 (簡易再生): 80%", text_color="#aaaaaa", font=self.f_jp_bold, anchor="w")
        self.volume_label.pack(side="left")
        self.volume_slider = ctk.CTkSlider(vol_row, from_=0.0, to=1.0, width=110, command=self.controller.on_volume_change)
        self.volume_slider.set(0.8)
        self.volume_slider.pack(side="right")

        # 4. 🎯 運指エディタ (変え指設定)
        self.editor_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.editor_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.editor_group, text="🎯 運指エディタ (変え指設定):", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        preset_row = ctk.CTkFrame(self.editor_group, fg_color="transparent")
        preset_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(preset_row, text="運指プリセット:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.alt_fingering_menu = ctk.CTkOptionMenu(
            preset_row, values=["スライド最小化", "スライド優先"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm,
            command=self.controller.on_fingering_preset_changed
        )
        self.alt_fingering_menu.pack(side="right", fill="x", expand=True)

        self.switch_frame_edit = ctk.CTkFrame(self.editor_group, fg_color="transparent")
        self.switch_frame_edit.pack(fill="x", padx=12, pady=(3, 3))
        self.fingering_edit_switch = ctk.CTkSwitch(
            self.switch_frame_edit, text="運指変更モード (クリック循環)",
            font=self.f_jp_bold, command=self.controller.on_fingering_edit_toggle
        )
        self.fingering_edit_switch.deselect()
        self.fingering_edit_switch.pack(side="left", expand=True, anchor="w")

        self.reset_fingering_btn = ctk.CTkButton(
            self.editor_group, text="🔄 曲別の運指データを初期化 (リセット)",
            font=self.f_jp_bold, height=26, fg_color="#6b3030", hover_color="#8a3d3d",
            command=self.controller.on_reset_song_fingering
        )
        self.reset_fingering_btn.pack(fill="x", padx=12, pady=(2, 8))

        # ======================================================================
        # 🔴 タブ2：【🎙️ 録音・音響】（新設！マイク録音・リバーブ・伴奏・頭出し）
        # ======================================================================
        # 1. 🎙️ マイク録音コントロール
        self.rec_group = ctk.CTkFrame(self.tab_audio_frame, corner_radius=8, border_width=1, border_color="#991b1b", fg_color="#201414")
        self.rec_group.pack(fill="x", padx=6, pady=(2, 4))

        ctk.CTkLabel(self.rec_group, text="🎙️ マイク録音 (ワンクリック録音):", font=self.f_jp_bold, text_color="#f87171").pack(anchor="w", padx=12, pady=(6, 2))

        rec_stat_row = ctk.CTkFrame(self.rec_group, fg_color="transparent")
        rec_stat_row.pack(fill="x", padx=12, pady=2)
        self.rec_status_lbl = ctk.CTkLabel(rec_stat_row, text="● 待機中 (上部の🔴録音ボタンで開始)", font=self.f_jp_bold, text_color="#aaaaaa", anchor="w")
        self.rec_status_lbl.pack(side="left", fill="x", expand=True)

        rec_dev_row = ctk.CTkFrame(self.rec_group, fg_color="transparent")
        rec_dev_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(rec_dev_row, text="マイク:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.rec_device_menu = ctk.CTkOptionMenu(
            rec_dev_row, values=["既定の入力マイク (Windows標準)"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm
        )
        self.rec_device_menu.pack(side="right", fill="x", expand=True)

        rec_take_row = ctk.CTkFrame(self.rec_group, fg_color="transparent")
        rec_take_row.pack(fill="x", padx=12, pady=(2, 8))
        self.rec_file_lbl = ctk.CTkLabel(rec_take_row, text="録音テイク: 未録音", font=self.f_jp_norm, text_color="#888888", anchor="w")
        self.rec_file_lbl.pack(side="left", fill="x", expand=True)
        self.rec_listen_btn = ctk.CTkButton(
            rec_take_row, text="▶ 試聴", width=58, height=24, font=self.f_jp_bold,
            fg_color="#3a3a3a", hover_color="#505050"
        )
        self.rec_listen_btn.pack(side="right")

        # 2. ✨ ハーモニカ用リバーブ (空間残響エフェクト)
        self.reverb_group = ctk.CTkFrame(self.tab_audio_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.reverb_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.reverb_group, text="✨ ハーモニカ用リバーブ (空間エフェクト):", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        rev_sw_row = ctk.CTkFrame(self.reverb_group, fg_color="transparent")
        rev_sw_row.pack(fill="x", padx=12, pady=2)
        self.reverb_switch = ctk.CTkSwitch(
            rev_sw_row, text="リバーブを適用", font=self.f_jp_bold,
            command=self.controller.on_setting_changed
        )
        self.reverb_switch.deselect()
        self.reverb_switch.pack(side="left")

        self.reverb_type_menu = ctk.CTkOptionMenu(
            rev_sw_row, values=["ルーム (自然な部屋鳴り)", "ホール (豊かな広がり)", "プレート (透明感のある響き)"],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.reverb_type_menu.set("ルーム (自然な部屋鳴り)")
        self.reverb_type_menu.pack(side="right", fill="x", expand=True, padx=(8, 0))

        rev_slider_row = ctk.CTkFrame(self.reverb_group, fg_color="transparent")
        rev_slider_row.pack(fill="x", padx=12, pady=(2, 8))
        self.reverb_wet_lbl = ctk.CTkLabel(rev_slider_row, text="深さ: 35%", text_color="#aaaaaa", font=self.f_jp_bold, width=70, anchor="w")
        self.reverb_wet_lbl.pack(side="left")
        self.reverb_wet_slider = ctk.CTkSlider(rev_slider_row, from_=0, to=100, number_of_steps=100)
        self.reverb_wet_slider.set(35)
        self.reverb_wet_slider.pack(side="left", fill="x", expand=True, padx=4)

        # 3. 🎵 外部音源・伴奏 (BGM) 設定
        self.ext_audio_group = ctk.CTkFrame(self.tab_audio_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.ext_audio_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.ext_audio_group, text="🎵 伴奏・外部音源 (D&D対応):", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        ext_file_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        ext_file_row.pack(fill="x", padx=12, pady=2)
        self.ext_audio_btn = ctk.CTkButton(
            ext_file_row, text="📂 音源選択", width=84, height=25, font=self.f_jp_bold,
            fg_color="#1f538d", hover_color="#143963", command=self.controller.on_select_ext_audio
        )
        self.ext_audio_btn.pack(side="left", padx=(0, 4))
        self.ext_audio_clear_btn = ctk.CTkButton(
            ext_file_row, text="✕", width=26, height=25, font=self.f_jp_bold,
            fg_color="#444444", hover_color="#773333", command=self.controller.on_clear_ext_audio
        )
        self.ext_audio_clear_btn.pack(side="right", padx=(4, 0))
        self.ext_audio_label = ctk.CTkLabel(
            ext_file_row, text="未選択 (ここに音源D&D可)", font=self.f_jp_norm, text_color="#888888", anchor="w"
        )
        self.ext_audio_label.pack(side="left", fill="x", expand=True)

        ext_mode_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        ext_mode_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(ext_mode_row, text="モード:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.ext_audio_mode_menu = ctk.CTkOptionMenu(
            ext_mode_row,
            values=[
                "頭出し確認 (再生:両方 / 動画:外部のみ)",
                "外部音源のみ (再生も動画も外部のみ)",
                "両方ミックス (再生も動画も両方)",
                "外部音源オフ (ガイド音のみ)"
            ],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm,
            command=self.controller.on_ext_audio_mode_changed
        )
        self.ext_audio_mode_menu.set("頭出し確認 (再生:両方 / 動画:外部のみ)")
        self.ext_audio_mode_menu.pack(side="right", fill="x", expand=True)

        # 4. ⏱️ 頭出し同期 ＆ 音量設定 (YouTube対応)
        self.ext_sync_group = ctk.CTkFrame(self.tab_audio_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.ext_sync_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.ext_sync_group, text="⏱️ 頭出し同期 ＆ 音量 (YouTube対応):", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        # 試聴コントロール
        ext_audition_row = ctk.CTkFrame(self.ext_sync_group, fg_color="transparent")
        ext_audition_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ext_audition_row, text="試聴:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.ext_audition_play_btn = ctk.CTkButton(
            ext_audition_row, text="▶ 頭出し試聴", width=98, height=25, font=self.f_jp_bold,
            fg_color="#2b8c54", hover_color="#1f6b3e", command=self.controller.on_ext_audition_play_pause
        )
        self.ext_audition_play_btn.pack(side="left", padx=(0, 2))
        self.ext_audition_restart_btn = ctk.CTkButton(
            ext_audition_row, text="⏮ 先頭から", width=86, height=25, font=self.f_jp_bold,
            fg_color="#1f538d", hover_color="#143963", command=self.controller.on_ext_audition_restart
        )
        self.ext_audition_restart_btn.pack(side="left", padx=2)
        self.ext_audition_stop_btn = ctk.CTkButton(
            ext_audition_row, text="⏹ 停止", width=52, height=25, font=self.f_jp_bold,
            fg_color="#dc2626", hover_color="#b91c1c", command=self.controller.on_stop
        )
        self.ext_audition_stop_btn.pack(side="right")

        # 頭出しオフセット微調整
        ext_off_row = ctk.CTkFrame(self.ext_sync_group, fg_color="transparent")
        ext_off_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ext_off_row, text="頭出し:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.ext_offset_m10_btn = ctk.CTkButton(
            ext_off_row, text="-10", width=30, height=24, font=self.f_jp_bold,
            fg_color="#333333", hover_color="#444444", command=lambda: self.controller.step_ext_audio_offset(-10)
        )
        self.ext_offset_m10_btn.pack(side="left", padx=1)
        self.ext_offset_m1_btn = ctk.CTkButton(
            ext_off_row, text="-1", width=25, height=24, font=self.f_jp_bold,
            fg_color="#333333", hover_color="#444444", command=lambda: self.controller.step_ext_audio_offset(-1)
        )
        self.ext_offset_m1_btn.pack(side="left", padx=1)

        self.ext_audio_offset_entry = ctk.CTkEntry(ext_off_row, width=50, height=24, justify="center", font=self.f_bold)
        self.ext_audio_offset_entry.insert(0, "0")
        self.ext_audio_offset_entry.pack(side="left", padx=2)
        self.ext_audio_offset_entry.bind("<Return>", lambda e: self.controller.on_ext_audio_offset_changed())
        self.ext_audio_offset_entry.bind("<FocusOut>", lambda e: self.controller.on_ext_audio_offset_changed())

        ctk.CTkLabel(ext_off_row, text="ms", font=self.f_jp_norm, text_color="#aaaaaa").pack(side="left", padx=(0, 2))
        self.ext_offset_p1_btn = ctk.CTkButton(
            ext_off_row, text="+1", width=25, height=24, font=self.f_jp_bold,
            fg_color="#333333", hover_color="#444444", command=lambda: self.controller.step_ext_audio_offset(1)
        )
        self.ext_offset_p1_btn.pack(side="left", padx=1)
        self.ext_offset_p10_btn = ctk.CTkButton(
            ext_off_row, text="+10", width=30, height=24, font=self.f_jp_bold,
            fg_color="#333333", hover_color="#444444", command=lambda: self.controller.step_ext_audio_offset(10)
        )
        self.ext_offset_p10_btn.pack(side="left", padx=1)

        # 音量
        ext_vol_row = ctk.CTkFrame(self.ext_sync_group, fg_color="transparent")
        ext_vol_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ext_vol_row, text="音量%:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.ext_audio_vol_entry = ctk.CTkEntry(ext_vol_row, width=42, height=24, justify="center", font=self.f_bold)
        self.ext_audio_vol_entry.insert(0, "100")
        self.ext_audio_vol_entry.pack(side="right", padx=(2, 0))
        self.ext_audio_vol_entry.bind("<Return>", lambda e: self.controller.on_ext_audio_vol_entry_changed())
        self.ext_audio_vol_entry.bind("<FocusOut>", lambda e: self.controller.on_ext_audio_vol_entry_changed())
        self.ext_audio_vol_slider = ctk.CTkSlider(
            ext_vol_row, from_=0, to=200, number_of_steps=200, height=16,
            command=self.controller.on_ext_audio_vol_slider
        )
        self.ext_audio_vol_slider.set(100)
        self.ext_audio_vol_slider.pack(side="left", fill="x", expand=True, padx=2)

        # YouTubeリミッター
        yt_lim_row = ctk.CTkFrame(self.ext_sync_group, fg_color="transparent")
        yt_lim_row.pack(fill="x", padx=12, pady=(2, 8))
        self.yt_limiter_switch = ctk.CTkSwitch(
            yt_lim_row, text="YouTube上限リミッター (-1.0dB自動保護)", font=self.f_jp_bold,
            command=self.controller.on_setting_changed
        )
        self.yt_limiter_switch.select()
        self.yt_limiter_switch.pack(side="left", anchor="w")

        # ======================================================================
        # 🎨 タブ3：【🎨 画面作り】（比率 ➔ 背景 ➔ タイトル ➔ ノーツ色 ➔ パーツ）
        # ======================================================================
        # 1. 📐 画面アスペクト比 ＆ 🖼️ 背景画像設定
        self.bg_canvas_group = ctk.CTkFrame(self.tab_design_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.bg_canvas_group.pack(fill="x", padx=6, pady=(2, 4))

        ctk.CTkLabel(self.bg_canvas_group, text="📐 画面比率 ＆ 背景画像:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        # アスペクト比選択
        ratio_row = ctk.CTkFrame(self.bg_canvas_group, fg_color="transparent")
        ratio_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ratio_row, text="アスペクト比:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.ratio_menu = ctk.CTkOptionMenu(
            ratio_row, values=["16:9", "9:16", "4:3"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_ratio_changed
        )
        self.ratio_menu.set("16:9")
        self.ratio_menu.pack(side="right", fill="x", expand=True)

        # 背景画像ファイル選択 ＆ 表示ON/OFFスイッチ
        bg_img_file_row = ctk.CTkFrame(self.bg_canvas_group, fg_color="transparent")
        bg_img_file_row.pack(fill="x", padx=12, pady=2)
        self.bg_image_btn = ctk.CTkButton(
            bg_img_file_row, text="📂 画像選択", width=84, height=24, font=self.f_jp_bold,
            fg_color="#1f538d", hover_color="#143963", command=self.controller.on_select_bg_image
        )
        self.bg_image_btn.pack(side="left", padx=(0, 4))
        self.bg_image_enable_switch = ctk.CTkSwitch(
            bg_img_file_row, text="表示", width=52, font=self.f_jp_bold, command=self.controller.on_setting_changed
        )
        self.bg_image_enable_switch.select()
        self.bg_image_enable_switch.pack(side="right", padx=(4, 0))
        self.bg_image_clear_btn = ctk.CTkButton(
            bg_img_file_row, text="✕", width=26, height=24, font=self.f_jp_bold,
            fg_color="#444444", hover_color="#773333", command=self.controller.on_clear_bg_image
        )
        self.bg_image_clear_btn.pack(side="right", padx=(2, 0))
        self.bg_image_label = ctk.CTkLabel(
            bg_img_file_row, text="未選択 (ここに画像D&D可)", font=self.f_jp_norm, text_color="#888888", anchor="w"
        )
        self.bg_image_label.pack(side="left", fill="x", expand=True)

        # 配置モード
        bg_img_fit_row = ctk.CTkFrame(self.bg_canvas_group, fg_color="transparent")
        bg_img_fit_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(bg_img_fit_row, text="配置:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.bg_image_fit_menu = ctk.CTkOptionMenu(
            bg_img_fit_row,
            values=[
                "中央トリミング (画面いっぱい)",
                "画面内に収める (全体表示)",
                "横幅に合わせる",
                "縦幅に合わせる",
                "画面に引き伸ばす"
            ],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.bg_image_fit_menu.set("中央トリミング (画面いっぱい)")
        self.bg_image_fit_menu.pack(side="right", fill="x", expand=True)

        # 回転 ＆ 明るさ
        bg_img_rot_row = ctk.CTkFrame(self.bg_canvas_group, fg_color="transparent")
        bg_img_rot_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(bg_img_rot_row, text="回転:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.bg_image_rot_btn = ctk.CTkButton(
            bg_img_rot_row, text="↻ 90°回転", width=74, height=24, font=self.f_jp_bold,
            fg_color="#333333", hover_color="#444444", command=self.controller.on_rotate_bg_image_90
        )
        self.bg_image_rot_btn.pack(side="right", padx=(4, 0))
        self.bg_image_rot_menu = ctk.CTkOptionMenu(
            bg_img_rot_row, values=["0° (自動補正)", "右へ90°", "180°", "左へ90°"],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.bg_image_rot_menu.set("0° (自動補正)")
        self.bg_image_rot_menu.pack(side="left", fill="x", expand=True)

        bg_img_dim_row = ctk.CTkFrame(self.bg_canvas_group, fg_color="transparent")
        bg_img_dim_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(bg_img_dim_row, text="明るさ:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.bg_image_dim_menu = ctk.CTkOptionMenu(
            bg_img_dim_row,
            values=[
                "少し暗め (70%・ノーツ強調)",
                "そのまま (100%)",
                "半分 (50%・くっきり)",
                "かなり暗め (30%)"
            ],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.bg_image_dim_menu.set("少し暗め (70%・ノーツ強調)")
        self.bg_image_dim_menu.pack(side="right", fill="x", expand=True)

        # 2. 🎨 ノーツカラー ＆ 軌道設定
        self.design_color_group = ctk.CTkFrame(self.tab_design_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.design_color_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.design_color_group, text="🎨 ノーツカラー ＆ 軌道設定:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        traj_row = ctk.CTkFrame(self.design_color_group, fg_color="transparent")
        traj_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(traj_row, text="ノーツ軌道:", font=self.f_jp_bold, text_color="#aaaaaa", width=80, anchor="w").pack(side="left")
        self.trajectory_menu = ctk.CTkOptionMenu(
            traj_row, values=["3段階 (練習標準)", "垂直落下 (穴直上)", "2段階 (ビジュアル)"],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.trajectory_menu.set("3段階 (練習標準)")
        self.trajectory_menu.pack(side="right", fill="x", expand=True)

        self.theme_color_frame = ctk.CTkFrame(self.design_color_group, fg_color="transparent")
        self.theme_color_frame.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.theme_color_frame, text="カラー:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.theme_menu = ctk.CTkOptionMenu(
            self.theme_color_frame, values=["ノーマル", "サクラ", "クールネオン", "モノクロ", "カスタム"],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, width=105, command=self.controller.on_theme_changed
        )
        self.theme_menu.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.btn_color_blow = ctk.CTkButton(
            self.theme_color_frame, text="吹色..", width=58, height=24, font=self.f_jp_bold, command=self.controller.choose_color_blow
        )
        self.btn_color_blow.pack(side="left", padx=2)
        self.btn_color_draw = ctk.CTkButton(
            self.theme_color_frame, text="吸色..", width=58, height=24, font=self.f_jp_bold, command=self.controller.choose_color_draw
        )
        self.btn_color_draw.pack(side="right", padx=(2, 0))

        op_row = ctk.CTkFrame(self.design_color_group, fg_color="transparent")
        op_row.pack(fill="x", padx=12, pady=(2, 8))
        self.opacity_lbl = ctk.CTkLabel(op_row, text="不透過度% (動画用):", font=self.f_jp_bold, text_color="#aaaaaa")
        self.opacity_lbl.pack(side="left")
        self.opacity_entry = ctk.CTkEntry(op_row, width=44, height=24, font=self.f_norm, justify="center")
        self.opacity_entry.insert(0, "50")
        self.opacity_entry.pack(side="right")
        self.opacity_entry.bind("<Return>", lambda e: self.controller.on_setting_changed())
        self.opacity_entry.bind("<FocusOut>", lambda e: self.controller.on_setting_changed())
        self.opacity_entry.bind("<KeyRelease>", lambda e: self.controller.save_user_settings_txt())

        # 4. 👁️ 表示パーツ切替（コンパクト2列グリッド）
        self.design_parts_group = ctk.CTkFrame(self.tab_design_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.design_parts_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.design_parts_group, text="👁️ 表示パーツ切替:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        sw_row1 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        sw_row1.pack(fill="x", padx=12, pady=2)
        self.hole_num_switch = ctk.CTkSwitch(sw_row1, text="穴番号", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.hole_num_switch.select()
        self.hole_num_switch.pack(side="left", expand=True, anchor="w")
        self.show_legend_switch = ctk.CTkSwitch(sw_row1, text="凡例", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_legend_switch.select()
        self.show_legend_switch.pack(side="right", expand=True, anchor="w")

        sw_row2 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        sw_row2.pack(fill="x", padx=12, pady=2)
        self.show_notes_switch = ctk.CTkSwitch(sw_row2, text="ノーツ表示", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_notes_switch.select()
        self.show_notes_switch.pack(side="left", expand=True, anchor="w")
        self.show_grid_switch = ctk.CTkSwitch(sw_row2, text="ガイド線", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_grid_switch.select()
        self.show_grid_switch.pack(side="right", expand=True, anchor="w")

        sw_row3 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        sw_row3.pack(fill="x", padx=12, pady=2)
        self.show_ring_switch = ctk.CTkSwitch(sw_row3, text="レバーリング", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_ring_switch.select()
        self.show_ring_switch.pack(side="left", expand=True, anchor="w")
        self.show_glow_switch = ctk.CTkSwitch(sw_row3, text="着地発光", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_glow_switch.pack(side="right", expand=True, anchor="w")

        sw_row4 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        sw_row4.pack(fill="x", padx=12, pady=(2, 8))
        self.show_lookahead_switch = ctk.CTkSwitch(sw_row4, text="ノーツ音名", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_lookahead_switch.select()
        self.show_lookahead_switch.pack(side="left", expand=True, anchor="w")
        self.use_skin_switch = ctk.CTkSwitch(sw_row4, text="外部スキン", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.use_skin_switch.select()
        self.use_skin_switch.pack(side="right", expand=True, anchor="w")

        # ======================================================================
        # 🎬 タブ4：【🎬 動画出力】（解像度・余白・フェード・書き出し）
        # ======================================================================
        # レンダリング・出力アクション (下部に最優先固定)
        self.export_action_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.export_action_group.pack(side="bottom", fill="x", padx=6, pady=(4, 6))

        self.export_edit_summary_lbl = ctk.CTkLabel(
            self.export_action_group,
            text="✨ 出力スタイル: 完成動画（背景画像・タイトル・音源合成）",
            font=self.f_jp_bold, text_color="#00ffcc", anchor="w"
        )
        self.export_edit_summary_lbl.pack(fill="x", padx=12, pady=(6, 2))

        self.action_btn_frame = ctk.CTkFrame(self.export_action_group, fg_color="transparent")
        self.action_btn_frame.pack(fill="x", padx=8, pady=(4, 8))

        self.preview_btn = ctk.CTkButton(
            self.action_btn_frame, text="📸 プレビュー", fg_color="#1f538d", hover_color="#143963",
            font=self.f_jp_bold, width=84, height=32, command=self.controller.execute_single_frame_preview
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.export_btn = ctk.CTkButton(
            self.action_btn_frame, text="🎬 書き出し", fg_color="#2b8c54", hover_color="#1f6b3e",
            font=self.f_jp_bold, width=92, height=32, command=self.controller.execute_video_export
        )
        self.export_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.open_output_btn = ctk.CTkButton(
            self.action_btn_frame, text="📂 保存先", fg_color="#444444", hover_color="#666666",
            font=self.f_jp_bold, width=70, height=32, command=self.controller.on_open_output_dir
        )
        self.open_output_btn.pack(side="right", padx=(2, 0))

        # 1. 🎬 出力スタイル (完成動画 vs クロマキー素材)
        self.export_mode_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#1f538d", fg_color="#142332")
        self.export_mode_group.pack(fill="x", padx=6, pady=(2, 4))

        mode_hdr_row = ctk.CTkFrame(self.export_mode_group, fg_color="transparent")
        mode_hdr_row.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(mode_hdr_row, text="🎬 出力スタイル:", font=self.f_jp_bold).pack(side="left")

        mode_row = ctk.CTkFrame(self.export_mode_group, fg_color="transparent")
        mode_row.pack(fill="x", padx=12, pady=(2, 6))
        self.export_mode_menu = ctk.CTkOptionMenu(
            mode_row,
            values=["完成動画 (背景・タイトル合成)", "クロマキー素材 (背景・タイトルなし)"],
            height=26, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_export_mode_changed
        )
        self.export_mode_menu.set("完成動画 (背景・タイトル合成)")
        self.export_mode_menu.pack(fill="x", expand=True)

        # 2. 🏷️ タイトル・クレジット表示 (動画出力用)
        self.title_overlay_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.title_overlay_group.pack(fill="x", padx=6, pady=4)

        title_hdr_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        title_hdr_row.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(title_hdr_row, text="🏷️ タイトル・クレジット表示:", font=self.f_jp_bold).pack(side="left")
        self.edit_preview_btn = ctk.CTkButton(
            title_hdr_row, text="📸 画面確認", width=74, height=22, font=self.f_jp_bold,
            fg_color="#1f538d", hover_color="#143963", command=self.controller.execute_single_frame_preview
        )
        self.edit_preview_btn.pack(side="right")

        tpl_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        tpl_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(tpl_row, text="配置:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.title_template_menu = ctk.CTkOptionMenu(
            tpl_row,
            values=["なし", "イントロ中央のみ", "左上常時", "右上常時", "イントロ中央＋左上常時", "イントロ中央＋右上常時"],
            height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.title_template_menu.set("なし")
        self.title_template_menu.pack(side="right", fill="x", expand=True)

        title_txt_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        title_txt_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(title_txt_row, text="曲名:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.video_title_entry = ctk.CTkEntry(title_txt_row, placeholder_text="曲名を入力 (空欄時は非表示)", height=24, font=self.f_jp_norm)
        self.video_title_entry.pack(side="right", fill="x", expand=True)
        self.video_title_entry.bind("<Return>", lambda e: self.controller.save_user_settings_txt())
        self.video_title_entry.bind("<FocusOut>", lambda e: self.controller.save_user_settings_txt())

        credit_txt_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        credit_txt_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(credit_txt_row, text="サブ:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.video_credit_entry = ctk.CTkEntry(credit_txt_row, placeholder_text="演奏者・クレジット等 (任意)", height=24, font=self.f_jp_norm)
        self.video_credit_entry.pack(side="right", fill="x", expand=True)
        self.video_credit_entry.bind("<Return>", lambda e: self.controller.save_user_settings_txt())
        self.video_credit_entry.bind("<FocusOut>", lambda e: self.controller.save_user_settings_txt())

        # 3. 映像フォーマット・画質設定
        self.export_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.export_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.export_group, text="📐 映像フォーマット・画質設定:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        bg_row = ctk.CTkFrame(self.export_group, fg_color="transparent")
        bg_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(bg_row, text="動画背景色:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.bg_menu = ctk.CTkOptionMenu(
            bg_row, values=["ノーマル（黒）", "グリーンバック", "ブルーバック", "マゼンタ（ピンク）"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_bg_change
        )
        self.bg_menu.pack(side="right", fill="x", expand=True)

        res_row = ctk.CTkFrame(self.export_group, fg_color="transparent")
        res_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(res_row, text="出力解像度:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.res_menu = ctk.CTkOptionMenu(
            res_row, values=["4K (3840x2160)", "Full HD (1920x1080)", "HD (1280x720)", "SD (960x540)"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.res_menu.set("Full HD (1920x1080)")
        self.res_menu.pack(side="right", fill="x", expand=True)

        fps_row = ctk.CTkFrame(self.export_group, fg_color="transparent")
        fps_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(fps_row, text="フレームレート:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.fps_menu = ctk.CTkOptionMenu(
            fps_row, values=["60 FPS", "30 FPS", "15 FPS"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.fps_menu.set("60 FPS")
        self.fps_menu.pack(side="right", fill="x", expand=True)

        # 4. 出力範囲・余白・フェード演出
        self.export_range_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b", fg_color="#1e1e1e")
        self.export_range_group.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(self.export_range_group, text="✂️ 出力範囲・余白・フェード演出:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        range_row = ctk.CTkFrame(self.export_range_group, fg_color="transparent")
        range_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(range_row, text="書き出し範囲:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.export_range_menu = ctk.CTkOptionMenu(
            range_row, values=["全曲", "A〜B小節のみ"],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.export_range_menu.set("全曲")
        self.export_range_menu.pack(side="right", fill="x", expand=True)

        in_out_row = ctk.CTkFrame(self.export_range_group, fg_color="transparent")
        in_out_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(in_out_row, text="前後の余白:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        ctk.CTkLabel(in_out_row, text="前", font=self.f_jp_norm, text_color="#cccccc").pack(side="left", padx=(0, 2))
        self.intro_sec_menu = ctk.CTkOptionMenu(
            in_out_row, values=["0秒", "1秒", "2秒", "3秒", "5秒"],
            width=70, height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.intro_sec_menu.set("0秒")
        self.intro_sec_menu.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(in_out_row, text="後", font=self.f_jp_norm, text_color="#cccccc").pack(side="left", padx=(0, 2))
        self.outro_sec_menu = ctk.CTkOptionMenu(
            in_out_row, values=["0秒", "1秒", "2秒", "3秒", "5秒"],
            width=70, height=24, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.outro_sec_menu.set("2秒")
        self.outro_sec_menu.pack(side="left")

        fade_row = ctk.CTkFrame(self.export_range_group, fg_color="transparent")
        fade_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(fade_row, text="フェード演出:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.fade_in_switch = ctk.CTkSwitch(
            fade_row, text="開始", width=75, font=self.f_jp_bold, command=self.controller.on_setting_changed
        )
        self.fade_in_switch.deselect()
        self.fade_in_switch.pack(side="left", padx=(0, 8))

        self.fade_out_switch = ctk.CTkSwitch(
            fade_row, text="終了", width=75, font=self.f_jp_bold, command=self.controller.on_setting_changed
        )
        self.fade_out_switch.deselect()
        self.fade_out_switch.pack(side="left")

        fade_title_row = ctk.CTkFrame(self.export_range_group, fg_color="transparent")
        fade_title_row.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(fade_title_row, text="フェード時題名:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.fade_in_title_menu = ctk.CTkOptionMenu(
            fade_title_row,
            values=[
                "フェード中もタイトル表示",
                "フェード中はタイトル非表示",
                "画面と一緒にフェードイン"
            ],
            height=25, font=self.f_jp_bold, dropdown_font=self.f_jp_norm, command=self.controller.on_setting_changed
        )
        self.fade_in_title_menu.set("フェード中もタイトル表示")
        self.fade_in_title_menu.pack(side="right", fill="x", expand=True)

        # 初期表示タブを「🎵 練習」に設定
        self.tab_practice_frame.pack(fill="both", expand=True)

    def switch_sidebar_tab(self, tab_name):
        """右サイドバーの表示タブを切り替えます（新4タブ対応）。"""
        self.tab_practice_frame.pack_forget()
        self.tab_design_frame.pack_forget()
        self.tab_audio_frame.pack_forget()
        self.tab_export_frame.pack_forget()

        if tab_name == "🎵 練習":
            self.tab_practice_frame.pack(fill="both", expand=True)
        elif tab_name == "🎨 画面作り":
            self.tab_design_frame.pack(fill="both", expand=True)
        elif tab_name == "🎙️ 録音・音響":
            self.tab_audio_frame.pack(fill="both", expand=True)
        elif tab_name == "🎬 動画出力":
            self.tab_export_frame.pack(fill="both", expand=True)

        if hasattr(self.controller, "gui") and hasattr(self.controller, "on_sidebar_tab_changed"):
            self.controller.on_sidebar_tab_changed(tab_name)

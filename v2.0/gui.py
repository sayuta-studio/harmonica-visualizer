# -*- coding: utf-8 -*-
# gui.py (STEP 4-B: 右サイドバーUI完全デトックス ＆ ABループ小節頭・小節末尾表記対応版)
# - 【小節頭・末尾表示】：手入力のエントリーの右横にあるラベルテキストを、ご指定いただいた親切な「小節頭」「小節末尾」にそれぞれスリム修正しました。
# - 🚀【マルチアスペクト＆スキンUI配備】：動画解像度セクションに「アスペクト比選択（16:9/9:16/4:3）」と「外部スキン適用トグル」をシームレスに追加。
# - 🚀【下端不動吸着】：縦長アスペクト時に幾何学がはみ出さないよう、Canvasの配置位置を「下端吸着（anchor="s", rely=1.0）」へ物理修正。
# - 🚀【STEP 4.5 3大グループ枠へ極限デトックス】：右サイドバーの設定群を「練習設定 / 運指エディタ / 動画出力設定」の角丸フレームへ完全に収束・整頓！
# - 🚀【マゼンタ追加】：クロマキー動画背景色プルダウンメニューへ「マゼンタ（ピンク）」を追加配備。
# - 🚀【UX改善 ＆ レバーリング追加】：不透過度を「ノーツ不透過度」「不透過度%」に変更。「アスペクト比」「カラーテーマ」に見出しラベルを追加。「レバーリング」ON/OFFトグルを新設。

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
        # すべてのフォントを一律「Meiryo / Segoe UI 12px」に滑らか統一
        self.f_bold = ("Segoe UI", 12, "bold")
        self.f_norm = ("Segoe UI", 12)
        self.f_jp_bold = ("Meiryo", 12, "bold") 
        self.f_jp_norm = ("Meiryo", 12)        

        # ==========================================
        # 1. 操作パネル (上部: ctk.CTkFrame - 高さ165pxにスリム縮小・余白デトックス)
        # ==========================================
        self.top_frame = ctk.CTkFrame(self, height=165, corner_radius=10)
        self.top_frame.pack(side="top", fill="x", padx=10, pady=(10, 5))
        self.top_frame.pack_propagate(False)

        # UI潰れを防ぐ高さ45px固定 of 3段ストリップ
        self.row1 = ctk.CTkFrame(self.top_frame, fg_color="transparent", height=45)
        self.row1.pack(fill="x", padx=20, pady=(15, 2))
        self.row1.pack_propagate(False)

        self.row2 = ctk.CTkFrame(self.top_frame, fg_color="transparent", height=45)
        self.row2.pack(fill="x", padx=20, pady=2)
        self.row2.pack_propagate(False)

        self.row3 = ctk.CTkFrame(self.top_frame, fg_color="transparent", height=45)
        self.row3.pack(fill="x", padx=20, pady=(2, 5))  
        self.row3.pack_propagate(False)

        # セパレーター
        def create_sep(parent):
            return ctk.CTkLabel(parent, text="|", text_color="#3d3d3d", font=self.f_bold)

        self.row1.grid_columnconfigure(2, weight=1) 
        
        # --- ■ 1行目：左側グループ（左詰め） ---
        self.file_btn = ctk.CTkButton(self.row1, text="MIDIを開く", width=95, font=self.f_jp_bold, command=self.controller.on_open_file)
        self.file_btn.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # ファイル名表示
        self.file_label = ctk.CTkLabel(self.row1, text="demo.mid", text_color="#1f538d", font=self.f_bold, anchor="w")
        self.file_label.grid(row=0, column=1, padx=(0, 15), sticky="w")

        # --- ■ 1行目：右側グループ ---
        self.audio_mode_menu = ctk.CTkOptionMenu(self.row1, values=["MIDI再生 (Windows標準音源)", "簡易再生 (内蔵軽量シンセ)", "ミュート"], width=200, font=self.f_jp_bold, command=self.controller.on_audio_mode_changed)
        self.audio_mode_menu.grid(row=0, column=3, padx=2, sticky="e")

        self.sep_r1_1 = create_sep(self.row1)
        self.sep_r1_1.grid(row=0, column=4, padx=12, sticky="e")

        # 小節ジャンプ
        self.jump_btn = ctk.CTkButton(self.row1, text="Go", width=30, font=self.f_bold, command=self.controller.on_jump_measure)
        self.jump_btn.grid(row=0, column=8, padx=2, sticky="e")

        self.jump_label = ctk.CTkLabel(self.row1, text=" / 1 小節", text_color="#aaaaaa", font=self.f_jp_bold)
        self.jump_label.grid(row=0, column=7, padx=2, sticky="e")

        self.jump_entry = ctk.CTkEntry(self.row1, width=38, font=self.f_norm)
        self.jump_entry.insert(0, "1")
        self.jump_entry.grid(row=0, column=6, padx=2, sticky="e")
        self.jump_entry.bind("<Return>", lambda e: self.controller.on_jump_measure())

        self.jump_title_lbl = ctk.CTkLabel(self.row1, text="小節ジャンプ:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.jump_title_lbl.grid(row=0, column=5, padx=0, sticky="e")

        self.sep_r1_2 = create_sep(self.row1)
        self.sep_r1_2.grid(row=0, column=9, padx=12, sticky="e")

        # BPM設定
        self.bpm_title_label = ctk.CTkLabel(self.row1, text="BPM設定:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.bpm_title_label.grid(row=0, column=10, padx=2, sticky="e")

        self.bpm_entry = ctk.CTkEntry(self.row1, width=45, font=self.f_norm)
        self.bpm_entry.insert(0, "120")
        self.bpm_entry.grid(row=0, column=11, padx=2, sticky="e")

        self.apply_bpm_btn = ctk.CTkButton(self.row1, text="適用", width=35, font=self.f_jp_bold, command=self.controller.apply_bpm)
        self.apply_bpm_btn.grid(row=0, column=12, padx=2, sticky="e")

        self.default_bpm_btn = ctk.CTkButton(self.row1, text="Default", width=50, font=self.f_norm, command=self.controller.reset_bpm)
        self.default_bpm_btn.grid(row=0, column=13, padx=(5, 0), sticky="e")


        # --- ■ 2行目 (中段：トランスポート ➔ シークタイムライン ➔ LCDステータス液晶) ---
        self.play_btn = ctk.CTkButton(self.row2, text="▶ 再生", width=75, height=24, font=self.f_jp_bold, fg_color="#2b8c54", hover_color="#1f6b3e", command=self.controller.on_play)
        self.play_btn.pack(side="left", padx=2)

        self.pause_btn = ctk.CTkButton(self.row2, text="⏸ 一時停止", width=75, height=24, font=self.f_jp_bold, fg_color="#e0a300", hover_color="#b88400", command=self.controller.on_pause)
        self.pause_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(self.row2, text="■ 停止", width=75, height=24, font=self.f_jp_bold, fg_color="#c0392b", hover_color="#962d22", command=self.controller.on_stop)
        self.stop_btn.pack(side="left", padx=(2, 10))

        create_sep(self.row2).pack(side="left", padx=5)

        # シークスライダー
        self.seek_label = ctk.CTkLabel(self.row2, text="00:00 / 00:00", font=("Courier New", 11, "bold"))
        self.seek_label.pack(side="left", padx=(5, 5))

        self.seek_slider = ctk.CTkSlider(self.row2, from_=0, to=100, command=self.controller.on_seek_drag)
        self.seek_slider.set(0)
        self.seek_slider.pack(side="left", fill="x", expand=True, padx=(0, 15))

        create_sep(self.row2).pack(side="left", padx=5)

        # LCD風液晶表示パネル
        self.lcd_frame = ctk.CTkFrame(self.row2, fg_color="#111111", border_width=1, border_color="#333333", width=520, height=34)
        self.lcd_frame.pack(side="right", padx=(0, 10))
        self.lcd_frame.pack_propagate(False)

        # 状態表示
        self.lbl_lcd_status = ctk.CTkLabel(self.lcd_frame, text="停止中", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=100, anchor="w")
        self.lbl_lcd_status.pack(side="left", padx=(10, 2))

        self.lbl_lcd_split = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split.pack(side="left")

        # 小節 ＆ 拍位置表示
        self.lbl_lcd_pos = ctk.CTkLabel(self.lcd_frame, text="位置: 001小節 . 01拍", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=170, anchor="w")
        self.lbl_lcd_pos.pack(side="left", padx=(10, 2))

        self.lbl_lcd_split2 = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split2.pack(side="left")

        # 拍子表示
        self.lbl_lcd_sig = ctk.CTkLabel(self.lcd_frame, text="拍子: 4/4", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=75, anchor="w")
        self.lbl_lcd_sig.pack(side="left", padx=(10, 2))

        self.lbl_lcd_split3 = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split3.pack(side="left")

        # テンポ表示
        self.lbl_lcd_bpm = ctk.CTkLabel(self.lcd_frame, text="テンポ: 120 BPM", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=110, anchor="w")
        self.lbl_lcd_bpm.pack(side="left", padx=(10, 2))


        # --- ■ 3行目 (下段：演奏設定 ➔ 高機能ABループ数値) ---
        self.row3.grid_columnconfigure(14, weight=1)

        self.metro_lbl_title = ctk.CTkLabel(self.row3, text="メトロノーム:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.metro_lbl_title.grid(row=0, column=0, padx=(0, 5), sticky="w")
        
        self.metro_menu = ctk.CTkOptionMenu(
            self.row3, 
            values=["標準（頭拍強調）", "小節頭のみ", "強調なし全拍", "なし"], 
            width=135, 
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm, 
            command=self.controller.on_metro_menu_changed
        )
        self.metro_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")

        self.count_in_lbl_title = ctk.CTkLabel(self.row3, text="カウントイン:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.count_in_lbl_title.grid(row=0, column=2, padx=(0, 5), sticky="w")
        
        self.count_in_menu = ctk.CTkOptionMenu(
            self.row3, 
            values=["0 小節", "1 小節", "2 小節"], 
            width=80, 
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm, 
            command=self.controller.on_count_in_menu_changed
        )
        self.count_in_menu.set("1 小節")
        self.count_in_menu.grid(row=0, column=3, padx=(0, 10), sticky="w")

        self.sep_r3_1 = create_sep(self.row3)
        self.sep_r3_1.grid(row=0, column=4, padx=10)

        # ABループ有効トグルスイッチ
        self.cb_loop = ctk.CTkSwitch(self.row3, text="A-Bループ", font=self.f_jp_bold, command=self.controller.on_loop_toggle)
        self.cb_loop.grid(row=0, column=5, padx=(0, 8), sticky="w")

        # ABループの直接小節数値指定Entry
        self.btn_set_a = ctk.CTkButton(self.row3, text="A点設定", width=55, font=self.f_jp_bold, command=self.controller.set_loop_a_at_current)
        self.btn_set_a.grid(row=0, column=6, padx=2, sticky="w")
        
        self.loop_a_entry = ctk.CTkEntry(self.row3, width=32, font=self.f_norm)
        self.loop_a_entry.insert(0, "1")
        self.loop_a_entry.grid(row=0, column=7, padx=2, sticky="w")
        self.loop_a_entry.bind("<Return>", lambda e: self.controller.on_loop_entry_changed())

        # A点手入力Entryの横ラベル
        self.loop_a_lbl = ctk.CTkLabel(self.row3, text="小節頭", text_color="#00ffcc", font=self.f_jp_bold)
        self.loop_a_lbl.grid(row=0, column=8, padx=(2, 8), sticky="w")

        self.btn_set_b = ctk.CTkButton(self.row3, text="B点設定", width=55, font=self.f_jp_bold, command=self.controller.set_loop_b_at_current)
        self.btn_set_b.grid(row=0, column=9, padx=2, sticky="w")

        self.loop_b_entry = ctk.CTkEntry(self.row3, width=32, font=self.f_norm)
        self.loop_b_entry.insert(0, "12")
        self.loop_b_entry.grid(row=0, column=10, padx=2, sticky="w")
        self.loop_b_entry.bind("<Return>", lambda e: self.controller.on_loop_entry_changed())

        # B点手入力Entryの横ラベル
        self.loop_b_lbl = ctk.CTkLabel(self.row3, text="小節末尾", text_color="#00ffcc", font=self.f_jp_bold)
        self.loop_b_lbl.grid(row=0, column=11, padx=(2, 8), sticky="w")

        self.btn_clear_loop = ctk.CTkButton(self.row3, text="ループ解除", width=65, fg_color="#555555", hover_color="#444444", font=self.f_jp_bold, command=self.controller.reset_loop_points)
        self.btn_clear_loop.grid(row=0, column=12, padx=(0, 15), sticky="w")

        self.sep_r3_2 = create_sep(self.row3)
        self.sep_r3_2.grid(row=0, column=13, padx=10)

        # 音量スライダー
        self.volume_label = ctk.CTkLabel(self.row3, text="音量 (簡易再生時のみ): 80%", text_color="#aaaaaa", font=self.f_jp_bold)
        self.volume_label.grid(row=0, column=15, padx=(0, 5), sticky="e")

        self.volume_slider = ctk.CTkSlider(self.row3, from_=0.0, to=1.0, width=100, command=self.controller.on_volume_change)
        self.volume_slider.set(0.8)
        self.volume_slider.grid(row=0, column=16, padx=(0, 10), sticky="e")


        # ==========================================
        # 2. メインL字領域 (下部: ctk.CTkFrame)
        # ==========================================
        self.main_lower_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_lower_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=(0, 10))

        # 左下：練習用Canvas (960x540基準、アスペクト可変アウターフレーム)
        self.canvas_frame = ctk.CTkFrame(self.main_lower_frame, width=1000, height=600, corner_radius=10, fg_color="#1a1a1a")
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.canvas_frame.pack_propagate(False)

        self.canvas = tk.Canvas(self.canvas_frame, width=960, height=540, bg=self.canvas_bg_color, highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")

        # 右下：3タブ切替サイドバー (幅360px固定：「🎵 練習」「🎨 デザイン」「🎬 動画出力」)
        self.right_frame = ctk.CTkFrame(self.main_lower_frame, width=360, corner_radius=10)
        self.right_frame.pack(side="right", fill="y", padx=(5, 0))
        self.right_frame.pack_propagate(False)

        # 最上部：モード切替セグメントボタン
        self.sidebar_mode_seg = ctk.CTkSegmentedButton(
            self.right_frame,
            values=["🎵 練習", "🎨 デザイン", "🎬 動画出力"],
            font=self.f_jp_bold,
            height=34,
            command=self.switch_sidebar_tab
        )
        self.sidebar_mode_seg.set("🎵 練習")
        self.sidebar_mode_seg.pack(fill="x", padx=12, pady=(12, 6))

        # 最下部：ステータスラベル（全タブ共通で常時表示）
        self.status_label = ctk.CTkLabel(self.right_frame, text="待機中...", font=self.f_jp_bold, text_color="#777777")
        self.status_label.pack(side="bottom", fill="x", pady=(4, 8))

        # 各タブ用のコンテナフレーム
        self.tab_practice_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.tab_design_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.tab_export_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")

        # ======================================================================
        # 🟢 タブ1：【🎵 練習】 (楽器・パート・練習ガイド・運指エディタ)
        # ======================================================================
        self.practice_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.practice_group.pack(fill="x", padx=12, pady=(6, 8))

        inst_menu_label = ctk.CTkLabel(self.practice_group, text="🎛️ 楽器・音名表記設定:", font=self.f_jp_bold)
        inst_menu_label.pack(anchor="w", padx=15, pady=(10, 4))

        inst_sub_lbl = ctk.CTkLabel(self.practice_group, text="使用ハーモニカ:", font=self.f_jp_bold, text_color="#aaaaaa")
        inst_sub_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.inst_menu = ctk.CTkOptionMenu(
            self.practice_group,
            values=["16穴 (C3-D7)", "12穴 標準 (C4-D7)", "12穴 バス (C1-D4)"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.inst_menu.pack(fill="x", padx=15, pady=(0, 8))

        lang_sub_lbl = ctk.CTkLabel(self.practice_group, text="音名表記スタイル:", font=self.f_jp_bold, text_color="#aaaaaa")
        lang_sub_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.lang_menu = ctk.CTkOptionMenu(
            self.practice_group,
            values=["CDE", "ドレミ", "なし"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.lang_menu.set("CDE")
        self.lang_menu.pack(fill="x", padx=15, pady=(0, 12))

        # --- 🎯 運指エディタ ---
        self.editor_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.editor_group.pack(fill="x", padx=12, pady=6)

        editor_lbl_title = ctk.CTkLabel(self.editor_group, text="🎯 運指エディタ (変え指設定):", font=self.f_jp_bold)
        editor_lbl_title.pack(anchor="w", padx=15, pady=(10, 4))

        preset_sub_lbl = ctk.CTkLabel(self.editor_group, text="曲別ベース運指プリセット:", font=self.f_jp_bold, text_color="#aaaaaa")
        preset_sub_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.alt_fingering_menu = ctk.CTkOptionMenu(
            self.editor_group,
            values=["スライド最小化", "スライド優先"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_fingering_preset_changed
        )
        self.alt_fingering_menu.pack(fill="x", padx=15, pady=(0, 8))

        self.switch_frame_edit = ctk.CTkFrame(self.editor_group, fg_color="transparent")
        self.switch_frame_edit.pack(fill="x", padx=15, pady=(4, 12))

        self.fingering_edit_switch = ctk.CTkSwitch(
            self.switch_frame_edit,
            text="運指変更モード (クリック循環)",
            font=self.f_jp_bold,
            command=self.controller.on_fingering_edit_toggle
        )
        self.fingering_edit_switch.deselect()
        self.fingering_edit_switch.pack(side="left", expand=True, anchor="w")

        # ======================================================================
        # 🎨 タブ2：【🎨 デザイン】 (カラーテーマ・外部スキン・表示パーツON/OFF)
        # ======================================================================
        self.design_color_group = ctk.CTkFrame(self.tab_design_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.design_color_group.pack(fill="x", padx=12, pady=(6, 8))

        design_title_lbl = ctk.CTkLabel(self.design_color_group, text="🎨 カラー・スキン設定:", font=self.f_jp_bold)
        design_title_lbl.pack(anchor="w", padx=15, pady=(10, 4))

        theme_title_lbl = ctk.CTkLabel(self.design_color_group, text="ノーツカラーテーマ:", font=self.f_jp_bold, text_color="#aaaaaa")
        theme_title_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.theme_color_frame = ctk.CTkFrame(self.design_color_group, fg_color="transparent")
        self.theme_color_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.theme_menu = ctk.CTkOptionMenu(
            self.theme_color_frame,
            values=["ノーマル", "サクラ", "クールネオン", "モノクロ", "カスタム"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            width=115,
            command=self.controller.on_theme_changed
        )
        self.theme_menu.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.btn_color_blow = ctk.CTkButton(
            self.theme_color_frame,
            text="吹色..",
            width=65,
            font=self.f_jp_bold,
            command=self.controller.choose_color_blow
        )
        self.btn_color_blow.pack(side="left", padx=2)

        self.btn_color_draw = ctk.CTkButton(
            self.theme_color_frame,
            text="吸色..",
            width=65,
            font=self.f_jp_bold,
            command=self.controller.choose_color_draw
        )
        self.btn_color_draw.pack(side="right", padx=(2, 0))

        self.skin_opacity_frame = ctk.CTkFrame(self.design_color_group, fg_color="transparent")
        self.skin_opacity_frame.pack(fill="x", padx=15, pady=(4, 12))

        self.use_skin_switch = ctk.CTkSwitch(
            self.skin_opacity_frame,
            text="外部スキン",
            font=self.f_jp_bold,
            command=self.controller.on_setting_changed
        )
        self.use_skin_switch.select()
        self.use_skin_switch.pack(side="left", expand=True, anchor="w")

        self.opacity_entry = ctk.CTkEntry(self.skin_opacity_frame, width=42, font=self.f_norm)
        self.opacity_entry.insert(0, "50")
        self.opacity_entry.pack(side="right", padx=1)

        self.opacity_btn = ctk.CTkButton(
            self.skin_opacity_frame,
            text="ノーツ不透過度%",
            width=80,
            font=self.f_jp_bold,
            command=self.controller.on_setting_changed
        )
        self.opacity_btn.pack(side="right", padx=(0, 3))

        # --- 👁️ 表示パーツ・エフェクト切替 ---
        self.design_parts_group = ctk.CTkFrame(self.tab_design_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.design_parts_group.pack(fill="x", padx=12, pady=6)

        parts_title_lbl = ctk.CTkLabel(self.design_parts_group, text="👁️ 表示パーツ・エフェクト切替:", font=self.f_jp_bold)
        parts_title_lbl.pack(anchor="w", padx=15, pady=(10, 6))

        self.switch_frame_1 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_1.pack(fill="x", padx=15, pady=4)

        self.hole_num_switch = ctk.CTkSwitch(self.switch_frame_1, text="穴番号", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.hole_num_switch.select()
        self.hole_num_switch.pack(side="left", expand=True, anchor="w")

        self.show_legend_switch = ctk.CTkSwitch(self.switch_frame_1, text="凡例", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_legend_switch.select()
        self.show_legend_switch.pack(side="right", expand=True, anchor="w")

        self.switch_frame_2 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_2.pack(fill="x", padx=15, pady=4)

        self.show_notes_switch = ctk.CTkSwitch(self.switch_frame_2, text="ノーツ表示", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_notes_switch.select()
        self.show_notes_switch.pack(side="left", expand=True, anchor="w")

        self.show_grid_switch = ctk.CTkSwitch(self.switch_frame_2, text="ガイド線", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_grid_switch.select()
        self.show_grid_switch.pack(side="right", expand=True, anchor="w")

        self.switch_frame_ring = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_ring.pack(fill="x", padx=15, pady=(4, 12))

        self.show_ring_switch = ctk.CTkSwitch(self.switch_frame_ring, text="レバーリング連動", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_ring_switch.select()
        self.show_ring_switch.pack(side="left", expand=True, anchor="w")

        self.show_glow_switch = ctk.CTkSwitch(self.switch_frame_ring, text="着地発光", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_glow_switch.pack(side="right", expand=True, anchor="w")

        # ======================================================================
        # 🎬 タブ3：【🎬 動画出力】 (アスペクト比・背景色・解像度・FPS・出力ボタン)
        # ======================================================================
        self.export_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.export_group.pack(fill="x", padx=12, pady=(6, 8))

        bg_label = ctk.CTkLabel(self.export_group, text="🎬 動画フォーマット・背景設定:", font=self.f_jp_bold)
        bg_label.pack(anchor="w", padx=15, pady=(10, 4))

        ratio_title_lbl = ctk.CTkLabel(self.export_group, text="出力アスペクト比:", font=self.f_jp_bold, text_color="#aaaaaa")
        ratio_title_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.ratio_menu = ctk.CTkOptionMenu(
            self.export_group,
            values=["16:9", "9:16", "4:3"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_ratio_changed
        )
        self.ratio_menu.set("16:9")
        self.ratio_menu.pack(fill="x", padx=15, pady=(0, 8))

        bg_sub_lbl = ctk.CTkLabel(self.export_group, text="動画背景色 (クロマキー対応):", font=self.f_jp_bold, text_color="#aaaaaa")
        bg_sub_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.bg_menu = ctk.CTkOptionMenu(
            self.export_group,
            values=["ノーマル（黒）", "グリーンバック", "ブルーバック", "マゼンタ（ピンク）"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_bg_change
        )
        self.bg_menu.pack(fill="x", padx=15, pady=(0, 8))

        res_sub_lbl = ctk.CTkLabel(self.export_group, text="解像度 ＆ フレームレート:", font=self.f_jp_bold, text_color="#aaaaaa")
        res_sub_lbl.pack(anchor="w", padx=15, pady=(2, 1))

        self.res_fps_frame = ctk.CTkFrame(self.export_group, fg_color="transparent")
        self.res_fps_frame.pack(fill="x", padx=15, pady=(0, 12))

        self.res_menu = ctk.CTkOptionMenu(
            self.res_fps_frame,
            values=["4K (3840x2160)", "Full HD (1920x1080)", "HD (1280x720)", "SD (960x540)"],
            width=135,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.res_menu.set("Full HD (1920x1080)")
        self.res_menu.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.fps_menu = ctk.CTkOptionMenu(
            self.res_fps_frame,
            values=["60 FPS", "30 FPS", "15 FPS"],
            width=90,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.fps_menu.set("60 FPS")
        self.fps_menu.pack(side="right", padx=(3, 0))

        # --- 🚀 レンダリング・出力アクション ---
        self.export_action_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.export_action_group.pack(fill="x", padx=12, pady=6)

        act_lbl = ctk.CTkLabel(self.export_action_group, text="🚀 レンダリング・出力:", font=self.f_jp_bold)
        act_lbl.pack(anchor="w", padx=15, pady=(10, 4))

        self.action_btn_frame = ctk.CTkFrame(self.export_action_group, fg_color="transparent")
        self.action_btn_frame.pack(fill="x", padx=15, pady=(2, 12))

        self.preview_btn = ctk.CTkButton(
            self.action_btn_frame,
            text="📸 プレビュー",
            fg_color="#1f538d",
            hover_color="#143963",
            font=self.f_jp_bold,
            height=34,
            command=self.controller.execute_single_frame_preview
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.export_btn = ctk.CTkButton(
            self.action_btn_frame,
            text="🎬 書き出し",
            fg_color="#2b8c54",
            hover_color="#1f6b3e",
            font=self.f_jp_bold,
            height=34,
            command=self.controller.execute_video_export
        )
        self.export_btn.pack(side="right", fill="x", expand=True, padx=(3, 0))

        # 初期表示タブを「🎵 練習」に設定
        self.tab_practice_frame.pack(fill="both", expand=True)

    def switch_sidebar_tab(self, tab_name):
        """右サイドバーの表示タブを切り替えます。"""
        self.tab_practice_frame.pack_forget()
        self.tab_design_frame.pack_forget()
        self.tab_export_frame.pack_forget()

        if tab_name == "🎵 練習":
            self.tab_practice_frame.pack(fill="both", expand=True)
        elif tab_name == "🎨 デザイン":
            self.tab_design_frame.pack(fill="both", expand=True)
        elif tab_name == "🎬 動画出力":
            self.tab_export_frame.pack(fill="both", expand=True)

        if hasattr(self.controller, "gui") and hasattr(self.controller, "on_sidebar_tab_changed"):
            self.controller.on_sidebar_tab_changed(tab_name)


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

        # --- ■ 1行目：左側グループ（MIDIを開く ＋ 固定幅曲名ラベル） ---
        self.file_btn = ctk.CTkButton(self.row1, text="MIDIを開く", width=95, font=self.f_jp_bold, command=self.controller.on_open_file)
        self.file_btn.pack(side="left", padx=(0, 8))

        # 曲名表示ボックス（幅260px完全固定：長い曲名でも右側のボタン群が1ピクセルも動かない構造）
        self.file_label_box = ctk.CTkFrame(self.row1, width=260, height=32, fg_color="transparent")
        self.file_label_box.pack(side="left", padx=(0, 6))
        self.file_label_box.pack_propagate(False)

        self.file_label = ctk.CTkLabel(self.file_label_box, text="demo.mid", text_color="#1f538d", font=self.f_bold, anchor="w")
        self.file_label.pack(side="left", fill="both", expand=True)

        # --- ■ 1行目：右側グループ（右端完全固定：パート選択・再生モード ｜ 小節ジャンプ ｜ 再生速度%） ---
        self.row1_right = ctk.CTkFrame(self.row1, fg_color="transparent")
        self.row1_right.pack(side="right", padx=(0, 10))

        # 1. マルチパートMIDI：主旋律パート選択 ＆ パート再生モード
        self.part_select_btn = ctk.CTkButton(
            self.row1_right, text="🎼 パート選択", width=110, font=self.f_jp_bold,
            fg_color="#2b5b84", hover_color="#1f4361",
            command=self.controller.open_part_select_dialog
        )
        self.part_select_btn.pack(side="left", padx=(0, 6))

        self.part_play_mode_menu = ctk.CTkOptionMenu(
            self.row1_right, values=["全パート再生", "主旋律ソロ", "伴奏のみ(カラオケ)"],
            width=155, font=self.f_jp_bold,
            command=self.controller.on_part_play_mode_changed
        )
        self.part_play_mode_menu.set("全パート再生")
        self.part_play_mode_menu.pack(side="left", padx=(0, 4))

        self.sep_r1_1 = create_sep(self.row1_right)
        self.sep_r1_1.pack(side="left", padx=10)

        # 2. 小節ジャンプ（2段目LCDの「位置: 001小節」の真上に配置）
        self.jump_title_lbl = ctk.CTkLabel(self.row1_right, text="小節ジャンプ:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.jump_title_lbl.pack(side="left", padx=(0, 2))

        self.jump_entry = ctk.CTkEntry(self.row1_right, width=40, font=self.f_norm, justify="center")
        self.jump_entry.insert(0, "1")
        self.jump_entry.pack(side="left", padx=2)
        self.jump_entry.bind("<Return>", lambda e: self.controller.on_jump_measure())

        self.jump_label = ctk.CTkLabel(self.row1_right, text=" / 1 小節", text_color="#aaaaaa", font=self.f_jp_bold)
        self.jump_label.pack(side="left", padx=2)

        self.jump_btn = ctk.CTkButton(self.row1_right, text="Go", width=34, font=self.f_bold, command=self.controller.on_jump_measure)
        self.jump_btn.pack(side="left", padx=(2, 4))

        self.sep_r1_2 = create_sep(self.row1_right)
        self.sep_r1_2.pack(side="left", padx=10)

        # 3. 再生速度(%)設定（2段目LCDの「テンポ:120BPM(100%)」の真上に配置）
        self.bpm_title_label = ctk.CTkLabel(self.row1_right, text="再生速度(%):", text_color="#aaaaaa", font=self.f_jp_bold)
        self.bpm_title_label.pack(side="left", padx=(0, 4))

        self.bpm_minus_btn = ctk.CTkButton(self.row1_right, text="-5%", width=36, font=self.f_bold, fg_color="#3a3a3a", hover_color="#505050", command=lambda: self.controller.step_speed_percent(-5))
        self.bpm_minus_btn.pack(side="left", padx=1)

        self.bpm_entry = ctk.CTkEntry(self.row1_right, width=46, font=self.f_norm, justify="center")
        self.bpm_entry.insert(0, "100")
        self.bpm_entry.pack(side="left", padx=1)
        self.bpm_entry.bind("<Return>", lambda e: self.controller.apply_bpm())
        self.bpm_entry.bind("<FocusOut>", lambda e: self.controller.apply_bpm())

        self.bpm_plus_btn = ctk.CTkButton(self.row1_right, text="+5%", width=36, font=self.f_bold, fg_color="#3a3a3a", hover_color="#505050", command=lambda: self.controller.step_speed_percent(5))
        self.bpm_plus_btn.pack(side="left", padx=1)

        self.default_bpm_btn = ctk.CTkButton(self.row1_right, text="100%", width=46, font=self.f_norm, command=self.controller.reset_bpm)
        self.default_bpm_btn.pack(side="left", padx=(4, 0))


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
        self.lcd_frame = ctk.CTkFrame(self.row2, fg_color="#111111", border_width=1, border_color="#333333", width=560, height=34)
        self.lcd_frame.pack(side="right", padx=(0, 10))
        self.lcd_frame.pack_propagate(False)

        # 状態表示
        self.lbl_lcd_status = ctk.CTkLabel(self.lcd_frame, text="停止中", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=100, anchor="w")
        self.lbl_lcd_status.pack(side="left", padx=(10, 2))

        self.lbl_lcd_split = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split.pack(side="left")

        # 小節 ＆ 拍位置表示
        self.lbl_lcd_pos = ctk.CTkLabel(self.lcd_frame, text="位置: 001小節 . 01拍", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=165, anchor="w")
        self.lbl_lcd_pos.pack(side="left", padx=(10, 2))

        self.lbl_lcd_split2 = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split2.pack(side="left")

        # 拍子表示
        self.lbl_lcd_sig = ctk.CTkLabel(self.lcd_frame, text="拍子: 4/4", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=75, anchor="w")
        self.lbl_lcd_sig.pack(side="left", padx=(10, 2))

        self.lbl_lcd_split3 = ctk.CTkLabel(self.lcd_frame, text="|", text_color="#333333")
        self.lbl_lcd_split3.pack(side="left")

        # テンポ表示
        self.lbl_lcd_bpm = ctk.CTkLabel(self.lcd_frame, text="テンポ:120BPM(100%)", text_color="#00ffcc", font=("Courier New", 12, "bold"), width=145, anchor="w")
        self.lbl_lcd_bpm.pack(side="left", padx=(8, 2))


        # --- ■ 3行目 (下段：メトロノーム ＆ カウントイン ➔ 高機能A-Bループ) ---
        self.metro_lbl_title = ctk.CTkLabel(self.row3, text="メトロノーム:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.metro_lbl_title.pack(side="left", padx=(0, 5))
        
        self.metro_menu = ctk.CTkOptionMenu(
            self.row3, 
            values=["標準（頭拍強調）", "小節頭のみ", "強調なし全拍", "なし"], 
            width=140, 
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm, 
            command=self.controller.on_metro_menu_changed
        )
        self.metro_menu.pack(side="left", padx=(0, 12))

        self.count_in_lbl_title = ctk.CTkLabel(self.row3, text="カウントイン:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.count_in_lbl_title.pack(side="left", padx=(0, 5))
        
        self.count_in_menu = ctk.CTkOptionMenu(
            self.row3, 
            values=["0 小節", "1 小節", "2 小節"], 
            width=85, 
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm, 
            command=self.controller.on_count_in_menu_changed
        )
        self.count_in_menu.set("1 小節")
        self.count_in_menu.pack(side="left", padx=(0, 10))

        self.sep_r3_1 = create_sep(self.row3)
        self.sep_r3_1.pack(side="left", padx=12)

        # ABループ有効トグルスイッチ ＆ A点・B点小節指定
        self.cb_loop = ctk.CTkSwitch(self.row3, text="A-Bループ", font=self.f_jp_bold, command=self.controller.on_loop_toggle)
        self.cb_loop.pack(side="left", padx=(0, 10))

        self.btn_set_a = ctk.CTkButton(self.row3, text="A点設定", width=60, font=self.f_jp_bold, command=self.controller.set_loop_a_at_current)
        self.btn_set_a.pack(side="left", padx=2)
        
        self.loop_a_entry = ctk.CTkEntry(self.row3, width=38, font=self.f_norm, justify="center")
        self.loop_a_entry.insert(0, "1")
        self.loop_a_entry.pack(side="left", padx=2)
        self.loop_a_entry.bind("<Return>", lambda e: self.controller.on_loop_entry_changed())

        self.loop_a_lbl = ctk.CTkLabel(self.row3, text="小節頭", text_color="#00ffcc", font=self.f_jp_bold)
        self.loop_a_lbl.pack(side="left", padx=(2, 6))

        self.loop_tilde_lbl = ctk.CTkLabel(self.row3, text="〜", text_color="#aaaaaa", font=self.f_jp_bold)
        self.loop_tilde_lbl.pack(side="left", padx=4)

        self.btn_set_b = ctk.CTkButton(self.row3, text="B点設定", width=60, font=self.f_jp_bold, command=self.controller.set_loop_b_at_current)
        self.btn_set_b.pack(side="left", padx=2)

        self.loop_b_entry = ctk.CTkEntry(self.row3, width=38, font=self.f_norm, justify="center")
        self.loop_b_entry.insert(0, "12")
        self.loop_b_entry.pack(side="left", padx=2)
        self.loop_b_entry.bind("<Return>", lambda e: self.controller.on_loop_entry_changed())

        self.loop_b_lbl = ctk.CTkLabel(self.row3, text="小節末尾", text_color="#00ffcc", font=self.f_jp_bold)
        self.loop_b_lbl.pack(side="left", padx=(2, 10))

        self.btn_clear_loop = ctk.CTkButton(self.row3, text="ループ解除", width=70, fg_color="#555555", hover_color="#444444", font=self.f_jp_bold, command=self.controller.reset_loop_points)
        self.btn_clear_loop.pack(side="left", padx=(2, 0))

        self.sep_r3_2 = create_sep(self.row3)
        self.sep_r3_2.pack(side="left", padx=12)

        self.note_speed_lbl = ctk.CTkLabel(self.row3, text="ノーツ落下速度:", text_color="#aaaaaa", font=self.f_jp_bold)
        self.note_speed_lbl.pack(side="left", padx=(0, 5))

        self.note_speed_menu = ctk.CTkOptionMenu(
            self.row3,
            values=["0.5x", "0.75x", "1.0x (標準)", "1.25x", "1.5x", "2.0x"],
            width=110,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.note_speed_menu.set("1.0x (標準)")
        self.note_speed_menu.pack(side="left", padx=(0, 6))


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
        # 🟢 タブ1：【🎵 練習】 (楽器・音源設定・運指エディタ)
        # ======================================================================
        self.practice_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.practice_group.pack(fill="x", padx=12, pady=(4, 5))

        inst_menu_label = ctk.CTkLabel(self.practice_group, text="🎛️ 楽器・ノーツ軌道設定:", font=self.f_jp_bold)
        inst_menu_label.pack(anchor="w", padx=15, pady=(8, 3))

        inst_row = ctk.CTkFrame(self.practice_group, fg_color="transparent")
        inst_row.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(inst_row, text="ハーモニカ:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.inst_menu = ctk.CTkOptionMenu(
            inst_row,
            values=["16穴 (C3-D7)", "12穴 標準 (C4-D7)", "12穴 バス (C1-D4)"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.inst_menu.pack(side="right", fill="x", expand=True)

        traj_row = ctk.CTkFrame(self.practice_group, fg_color="transparent")
        traj_row.pack(fill="x", padx=15, pady=(2, 8))
        ctk.CTkLabel(traj_row, text="ノーツ軌道:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.trajectory_menu = ctk.CTkOptionMenu(
            traj_row,
            values=["3段階 (練習標準)", "垂直落下 (穴直上)", "2段階 (ビジュアル)"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.trajectory_menu.set("3段階 (練習標準)")
        self.trajectory_menu.pack(side="right", fill="x", expand=True)

        # --- 🔊 音源・音量設定 ---
        self.audio_metro_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.audio_metro_group.pack(fill="x", padx=12, pady=5)

        audio_metro_title = ctk.CTkLabel(self.audio_metro_group, text="🔊 音源・音量設定:", font=self.f_jp_bold)
        audio_metro_title.pack(anchor="w", padx=15, pady=(8, 3))

        audio_row = ctk.CTkFrame(self.audio_metro_group, fg_color="transparent")
        audio_row.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(audio_row, text="再生音源:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.audio_mode_menu = ctk.CTkOptionMenu(
            audio_row,
            values=["MIDI再生 (Windows標準音源)", "簡易再生 (内蔵軽量シンセ)", "ミュート"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_audio_mode_changed
        )
        self.audio_mode_menu.pack(side="right", fill="x", expand=True)

        vol_row = ctk.CTkFrame(self.audio_metro_group, fg_color="transparent")
        vol_row.pack(fill="x", padx=15, pady=(3, 8))
        self.volume_label = ctk.CTkLabel(vol_row, text="音量 (簡易再生時のみ): 80%", text_color="#aaaaaa", font=self.f_jp_bold, anchor="w")
        self.volume_label.pack(side="left")
        self.volume_slider = ctk.CTkSlider(vol_row, from_=0.0, to=1.0, width=115, command=self.controller.on_volume_change)
        self.volume_slider.set(0.8)
        self.volume_slider.pack(side="right")

        # --- 🎯 運指エディタ ---
        self.editor_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.editor_group.pack(fill="x", padx=12, pady=5)

        editor_lbl_title = ctk.CTkLabel(self.editor_group, text="🎯 運指エディタ (変え指設定):", font=self.f_jp_bold)
        editor_lbl_title.pack(anchor="w", padx=15, pady=(8, 3))

        preset_row = ctk.CTkFrame(self.editor_group, fg_color="transparent")
        preset_row.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(preset_row, text="運指プリセット:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.alt_fingering_menu = ctk.CTkOptionMenu(
            preset_row,
            values=["スライド最小化", "スライド優先"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_fingering_preset_changed
        )
        self.alt_fingering_menu.pack(side="right", fill="x", expand=True)

        self.switch_frame_edit = ctk.CTkFrame(self.editor_group, fg_color="transparent")
        self.switch_frame_edit.pack(fill="x", padx=15, pady=(4, 4))

        self.fingering_edit_switch = ctk.CTkSwitch(
            self.switch_frame_edit,
            text="運指変更モード (クリック循環)",
            font=self.f_jp_bold,
            command=self.controller.on_fingering_edit_toggle
        )
        self.fingering_edit_switch.deselect()
        self.fingering_edit_switch.pack(side="left", expand=True, anchor="w")

        self.reset_fingering_btn = ctk.CTkButton(
            self.editor_group,
            text="🔄 曲別の運指データを初期化 (リセット)",
            font=self.f_jp_bold,
            height=28,
            fg_color="#6b3030",
            hover_color="#8a3d3d",
            command=self.controller.on_reset_song_fingering
        )
        self.reset_fingering_btn.pack(fill="x", padx=15, pady=(2, 10))

        # --- 📈 ステップアップ練習 (A-Bループ連動) ---
        self.stepup_group = ctk.CTkFrame(self.tab_practice_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.stepup_group.pack(fill="x", padx=12, pady=5)

        stepup_title = ctk.CTkLabel(self.stepup_group, text="📈 ステップアップ練習 (A-Bループ連動):", font=self.f_jp_bold)
        stepup_title.pack(anchor="w", padx=15, pady=(8, 3))

        stepup_row1 = ctk.CTkFrame(self.stepup_group, fg_color="transparent")
        stepup_row1.pack(fill="x", padx=15, pady=2)

        self.stepup_switch = ctk.CTkSwitch(
            stepup_row1,
            text="ステップアップ有効",
            font=self.f_jp_bold,
            command=self.controller.on_stepup_toggle
        )
        self.stepup_switch.deselect()
        self.stepup_switch.pack(side="left")

        self.stepup_step_menu = ctk.CTkOptionMenu(
            stepup_row1,
            values=["+1%", "+2%", "+5%", "+10%"],
            width=72,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_stepup_param_changed
        )
        self.stepup_step_menu.set("+5%")
        self.stepup_step_menu.pack(side="right")

        ctk.CTkLabel(stepup_row1, text="1周増分:", font=self.f_jp_bold, text_color="#aaaaaa").pack(side="right", padx=(0, 4))

        stepup_row2 = ctk.CTkFrame(self.stepup_group, fg_color="transparent")
        stepup_row2.pack(fill="x", padx=15, pady=(3, 10))

        ctk.CTkLabel(stepup_row2, text="開始:", font=self.f_jp_bold, text_color="#aaaaaa").pack(side="left", padx=(0, 4))
        self.stepup_start_entry = ctk.CTkEntry(stepup_row2, width=48, font=self.f_norm, justify="center")
        self.stepup_start_entry.insert(0, "70")
        self.stepup_start_entry.pack(side="left", padx=2)
        self.stepup_start_entry.bind("<Return>", lambda e: self.controller.on_stepup_param_changed())
        self.stepup_start_entry.bind("<FocusOut>", lambda e: self.controller.on_stepup_param_changed())
        ctk.CTkLabel(stepup_row2, text="%", font=self.f_jp_bold, text_color="#00ffcc").pack(side="left", padx=(2, 10))

        ctk.CTkLabel(stepup_row2, text="➔   目標:", font=self.f_jp_bold, text_color="#aaaaaa").pack(side="left", padx=(4, 4))
        self.stepup_goal_entry = ctk.CTkEntry(stepup_row2, width=48, font=self.f_norm, justify="center")
        self.stepup_goal_entry.insert(0, "100")
        self.stepup_goal_entry.pack(side="left", padx=2)
        self.stepup_goal_entry.bind("<Return>", lambda e: self.controller.on_stepup_param_changed())
        self.stepup_goal_entry.bind("<FocusOut>", lambda e: self.controller.on_stepup_param_changed())
        ctk.CTkLabel(stepup_row2, text="%", font=self.f_jp_bold, text_color="#00ffcc").pack(side="left", padx=(2, 0))

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

        self.opacity_entry = ctk.CTkEntry(self.skin_opacity_frame, width=46, font=self.f_norm, justify="center")
        self.opacity_entry.insert(0, "50")
        self.opacity_entry.pack(side="right", padx=1)
        self.opacity_entry.bind("<Return>", lambda e: self.controller.on_setting_changed())
        self.opacity_entry.bind("<FocusOut>", lambda e: self.controller.on_setting_changed())
        self.opacity_entry.bind("<KeyRelease>", lambda e: self.controller.save_user_settings_txt())

        self.opacity_lbl = ctk.CTkLabel(
            self.skin_opacity_frame,
            text="ノーツ不透過度(動画用%):",
            font=self.f_jp_bold,
            text_color="#cccccc"
        )
        self.opacity_lbl.pack(side="right", padx=(0, 4))

        # --- 👁️ 音名・表示パーツ・エフェクト切替 ---
        self.design_parts_group = ctk.CTkFrame(self.tab_design_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.design_parts_group.pack(fill="x", padx=12, pady=6)

        parts_title_lbl = ctk.CTkLabel(self.design_parts_group, text="👁️ 音名・表示パーツ切替:", font=self.f_jp_bold)
        parts_title_lbl.pack(anchor="w", padx=15, pady=(10, 4))

        lang_row = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        lang_row.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(lang_row, text="音名表記:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.lang_menu = ctk.CTkOptionMenu(
            lang_row,
            values=["CDE", "ドレミ", "なし"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.lang_menu.set("CDE")
        self.lang_menu.pack(side="right", fill="x", expand=True)

        grid4_row = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        grid4_row.pack(fill="x", padx=15, pady=(2, 6))
        ctk.CTkLabel(grid4_row, text="穴下の音名:", font=self.f_jp_bold, text_color="#aaaaaa", width=95, anchor="w").pack(side="left")
        self.grid4_menu = ctk.CTkOptionMenu(
            grid4_row,
            values=["4音グリッド表示", "1音表示 (従来)"],
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.grid4_menu.set("4音グリッド表示")
        self.grid4_menu.pack(side="right", fill="x", expand=True)

        self.switch_frame_1 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_1.pack(fill="x", padx=15, pady=3)

        self.hole_num_switch = ctk.CTkSwitch(self.switch_frame_1, text="穴番号", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.hole_num_switch.select()
        self.hole_num_switch.pack(side="left", expand=True, anchor="w")

        self.show_legend_switch = ctk.CTkSwitch(self.switch_frame_1, text="凡例", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_legend_switch.select()
        self.show_legend_switch.pack(side="right", expand=True, anchor="w")

        self.switch_frame_2 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_2.pack(fill="x", padx=15, pady=3)

        self.show_notes_switch = ctk.CTkSwitch(self.switch_frame_2, text="ノーツ表示", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_notes_switch.select()
        self.show_notes_switch.pack(side="left", expand=True, anchor="w")

        self.show_grid_switch = ctk.CTkSwitch(self.switch_frame_2, text="ガイド線", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_grid_switch.select()
        self.show_grid_switch.pack(side="right", expand=True, anchor="w")

        self.switch_frame_ring = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_ring.pack(fill="x", padx=15, pady=3)

        self.show_ring_switch = ctk.CTkSwitch(self.switch_frame_ring, text="レバーリング連動", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_ring_switch.select()
        self.show_ring_switch.pack(side="left", expand=True, anchor="w")

        self.show_glow_switch = ctk.CTkSwitch(self.switch_frame_ring, text="着地発光", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_glow_switch.pack(side="right", expand=True, anchor="w")

        self.switch_frame_step5 = ctk.CTkFrame(self.design_parts_group, fg_color="transparent")
        self.switch_frame_step5.pack(fill="x", padx=15, pady=(3, 10))

        self.show_lookahead_switch = ctk.CTkSwitch(self.switch_frame_step5, text="ノーツ音名表示", font=self.f_jp_bold, command=self.controller.on_setting_changed)
        self.show_lookahead_switch.select()
        self.show_lookahead_switch.pack(side="left", expand=True, anchor="w")

        # ======================================================================
        # 🎬 タブ3：【🎬 動画出力】 (フォーマット・範囲・タイトル・外部音源・出力)
        # ======================================================================
        self.export_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.export_group.pack(fill="x", padx=12, pady=(4, 4))

        bg_label = ctk.CTkLabel(self.export_group, text="🎬 フォーマット・範囲・尺設定:", font=self.f_jp_bold)
        bg_label.pack(anchor="w", padx=12, pady=(6, 2))

        ratio_bg_row = ctk.CTkFrame(self.export_group, fg_color="transparent")
        ratio_bg_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ratio_bg_row, text="比率/背景:", font=self.f_jp_bold, text_color="#aaaaaa", width=72, anchor="w").pack(side="left")
        self.ratio_menu = ctk.CTkOptionMenu(
            ratio_bg_row,
            values=["16:9", "9:16", "4:3"],
            width=68,
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_ratio_changed
        )
        self.ratio_menu.set("16:9")
        self.ratio_menu.pack(side="left", padx=(0, 4))

        self.bg_menu = ctk.CTkOptionMenu(
            ratio_bg_row,
            values=["ノーマル（黒）", "グリーンバック", "ブルーバック", "マゼンタ（ピンク）"],
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_bg_change
        )
        self.bg_menu.pack(side="right", fill="x", expand=True)

        self.res_fps_frame = ctk.CTkFrame(self.export_group, fg_color="transparent")
        self.res_fps_frame.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(self.res_fps_frame, text="画質/FPS:", font=self.f_jp_bold, text_color="#aaaaaa", width=72, anchor="w").pack(side="left")

        self.res_menu = ctk.CTkOptionMenu(
            self.res_fps_frame,
            values=["4K (3840x2160)", "Full HD (1920x1080)", "HD (1280x720)", "SD (960x540)"],
            width=120,
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.res_menu.set("Full HD (1920x1080)")
        self.res_menu.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.fps_menu = ctk.CTkOptionMenu(
            self.res_fps_frame,
            values=["60 FPS", "30 FPS", "15 FPS"],
            width=74,
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.fps_menu.set("60 FPS")
        self.fps_menu.pack(side="right")

        range_row = ctk.CTkFrame(self.export_group, fg_color="transparent")
        range_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(range_row, text="出力範囲:", font=self.f_jp_bold, text_color="#aaaaaa", width=72, anchor="w").pack(side="left")
        self.export_range_menu = ctk.CTkOptionMenu(
            range_row,
            values=["全曲", "A〜B小節のみ"],
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.export_range_menu.set("全曲")
        self.export_range_menu.pack(side="right", fill="x", expand=True)

        in_out_row = ctk.CTkFrame(self.export_group, fg_color="transparent")
        in_out_row.pack(fill="x", padx=12, pady=(2, 6))
        ctk.CTkLabel(in_out_row, text="前後の余白:", font=self.f_jp_bold, text_color="#aaaaaa", width=72, anchor="w").pack(side="left")
        ctk.CTkLabel(in_out_row, text="前", font=self.f_jp_norm, text_color="#cccccc").pack(side="left", padx=(0, 2))
        self.intro_sec_menu = ctk.CTkOptionMenu(
            in_out_row,
            values=["0秒", "1秒", "2秒", "3秒", "5秒"],
            width=66,
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.intro_sec_menu.set("0秒")
        self.intro_sec_menu.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(in_out_row, text="後", font=self.f_jp_norm, text_color="#cccccc").pack(side="left", padx=(0, 2))
        self.outro_sec_menu = ctk.CTkOptionMenu(
            in_out_row,
            values=["0秒", "1秒", "2秒", "3秒", "5秒"],
            width=66,
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.outro_sec_menu.set("2秒")
        self.outro_sec_menu.pack(side="left")

        # --- 🏷️ タイトル・クレジット表示設定 ---
        self.title_overlay_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.title_overlay_group.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(self.title_overlay_group, text="🏷️ タイトル・クレジット表示:", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        tpl_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        tpl_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(tpl_row, text="配置:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.title_template_menu = ctk.CTkOptionMenu(
            tpl_row,
            values=["なし", "イントロ中央のみ", "左上常時", "右上常時", "イントロ中央＋左上常時", "イントロ中央＋右上常時"],
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_setting_changed
        )
        self.title_template_menu.set("なし")
        self.title_template_menu.pack(side="right", fill="x", expand=True)

        title_txt_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        title_txt_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(title_txt_row, text="曲名:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.video_title_entry = ctk.CTkEntry(
            title_txt_row,
            placeholder_text="曲名を入力 (空欄時は非表示)",
            height=24,
            font=self.f_jp_norm
        )
        self.video_title_entry.pack(side="right", fill="x", expand=True)
        self.video_title_entry.bind("<Return>", lambda e: self.controller.save_user_settings_txt())
        self.video_title_entry.bind("<FocusOut>", lambda e: self.controller.save_user_settings_txt())

        credit_txt_row = ctk.CTkFrame(self.title_overlay_group, fg_color="transparent")
        credit_txt_row.pack(fill="x", padx=12, pady=(2, 6))
        ctk.CTkLabel(credit_txt_row, text="サブ:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.video_credit_entry = ctk.CTkEntry(
            credit_txt_row,
            placeholder_text="演奏者・クレジット等 (任意)",
            height=24,
            font=self.f_jp_norm
        )
        self.video_credit_entry.pack(side="right", fill="x", expand=True)
        self.video_credit_entry.bind("<Return>", lambda e: self.controller.save_user_settings_txt())
        self.video_credit_entry.bind("<FocusOut>", lambda e: self.controller.save_user_settings_txt())

        # --- 🎵 外部音源・頭出し同期・音量設定 (YouTube対応) ---
        self.ext_audio_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.ext_audio_group.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(self.ext_audio_group, text="🎵 外部音源・頭出し・音量 (YouTube対応):", font=self.f_jp_bold).pack(anchor="w", padx=12, pady=(6, 2))

        ext_file_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        ext_file_row.pack(fill="x", padx=12, pady=2)
        self.ext_audio_btn = ctk.CTkButton(
            ext_file_row,
            text="📂 音源選択",
            width=86,
            height=24,
            font=self.f_jp_bold,
            fg_color="#1f538d",
            hover_color="#143963",
            command=self.controller.on_select_ext_audio
        )
        self.ext_audio_btn.pack(side="left", padx=(0, 4))

        self.ext_audio_clear_btn = ctk.CTkButton(
            ext_file_row,
            text="✕",
            width=26,
            height=24,
            font=self.f_jp_bold,
            fg_color="#555555",
            hover_color="#773333",
            command=self.controller.on_clear_ext_audio
        )
        self.ext_audio_clear_btn.pack(side="right", padx=(4, 0))

        self.ext_audio_label = ctk.CTkLabel(
            ext_file_row,
            text="未選択 (内蔵シンセ合成)",
            font=self.f_jp_norm,
            text_color="#888888",
            anchor="w"
        )
        self.ext_audio_label.pack(side="left", fill="x", expand=True)

        ext_mode_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        ext_mode_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ext_mode_row, text="モード:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.ext_audio_mode_menu = ctk.CTkOptionMenu(
            ext_mode_row,
            values=[
                "頭出し確認 (再生:両方 / 動画:外部のみ)",
                "外部音源のみ (再生も動画も外部のみ)",
                "両方ミックス (再生も動画も両方)",
                "外部音源オフ (ガイド音のみ)"
            ],
            height=24,
            font=self.f_jp_bold,
            dropdown_font=self.f_jp_norm,
            command=self.controller.on_ext_audio_mode_changed
        )
        self.ext_audio_mode_menu.set("頭出し確認 (再生:両方 / 動画:外部のみ)")
        self.ext_audio_mode_menu.pack(side="right", fill="x", expand=True)

        ext_off_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        ext_off_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ext_off_row, text="頭出し:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")

        self.ext_offset_m10_btn = ctk.CTkButton(
            ext_off_row, text="-10", width=32, height=22, font=self.f_jp_bold,
            fg_color="#3a3a3a", hover_color="#555555",
            command=lambda: self.controller.step_ext_audio_offset(-10)
        )
        self.ext_offset_m10_btn.pack(side="left", padx=1)

        self.ext_offset_m1_btn = ctk.CTkButton(
            ext_off_row, text="-1", width=26, height=22, font=self.f_jp_bold,
            fg_color="#3a3a3a", hover_color="#555555",
            command=lambda: self.controller.step_ext_audio_offset(-1)
        )
        self.ext_offset_m1_btn.pack(side="left", padx=1)

        self.ext_audio_offset_entry = ctk.CTkEntry(ext_off_row, width=54, height=22, justify="center", font=self.f_bold)
        self.ext_audio_offset_entry.insert(0, "0")
        self.ext_audio_offset_entry.pack(side="left", padx=2)
        self.ext_audio_offset_entry.bind("<Return>", lambda e: self.controller.on_ext_audio_offset_changed())
        self.ext_audio_offset_entry.bind("<FocusOut>", lambda e: self.controller.on_ext_audio_offset_changed())

        ctk.CTkLabel(ext_off_row, text="ms", font=self.f_jp_norm, text_color="#aaaaaa").pack(side="left", padx=(0, 2))

        self.ext_offset_p1_btn = ctk.CTkButton(
            ext_off_row, text="+1", width=26, height=22, font=self.f_jp_bold,
            fg_color="#3a3a3a", hover_color="#555555",
            command=lambda: self.controller.step_ext_audio_offset(1)
        )
        self.ext_offset_p1_btn.pack(side="left", padx=1)

        self.ext_offset_p10_btn = ctk.CTkButton(
            ext_off_row, text="+10", width=32, height=22, font=self.f_jp_bold,
            fg_color="#3a3a3a", hover_color="#555555",
            command=lambda: self.controller.step_ext_audio_offset(10)
        )
        self.ext_offset_p10_btn.pack(side="left", padx=1)

        ext_vol_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        ext_vol_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(ext_vol_row, text="音量%:", font=self.f_jp_bold, text_color="#aaaaaa", width=52, anchor="w").pack(side="left")
        self.ext_audio_vol_entry = ctk.CTkEntry(ext_vol_row, width=44, height=22, justify="center", font=self.f_bold)
        self.ext_audio_vol_entry.insert(0, "100")
        self.ext_audio_vol_entry.pack(side="right", padx=(4, 0))
        self.ext_audio_vol_entry.bind("<Return>", lambda e: self.controller.on_ext_audio_vol_entry_changed())
        self.ext_audio_vol_entry.bind("<FocusOut>", lambda e: self.controller.on_ext_audio_vol_entry_changed())

        self.ext_audio_vol_slider = ctk.CTkSlider(
            ext_vol_row,
            from_=0,
            to=200,
            number_of_steps=200,
            height=16,
            command=self.controller.on_ext_audio_vol_slider
        )
        self.ext_audio_vol_slider.set(100)
        self.ext_audio_vol_slider.pack(side="left", fill="x", expand=True, padx=2)

        yt_lim_row = ctk.CTkFrame(self.ext_audio_group, fg_color="transparent")
        yt_lim_row.pack(fill="x", padx=12, pady=(2, 6))
        self.yt_limiter_switch = ctk.CTkSwitch(
            yt_lim_row,
            text="YouTube上限リミッター (-1.0dB自動保護)",
            font=self.f_jp_bold,
            command=self.controller.on_setting_changed
        )
        self.yt_limiter_switch.select()
        self.yt_limiter_switch.pack(side="left", anchor="w")

        # --- 🚀 レンダリング・出力アクション ---
        self.export_action_group = ctk.CTkFrame(self.tab_export_frame, corner_radius=8, border_width=1, border_color="#2b2b2b")
        self.export_action_group.pack(fill="x", padx=12, pady=(4, 6))

        self.action_btn_frame = ctk.CTkFrame(self.export_action_group, fg_color="transparent")
        self.action_btn_frame.pack(fill="x", padx=10, pady=8)

        self.preview_btn = ctk.CTkButton(
            self.action_btn_frame,
            text="📸 プレビュー",
            fg_color="#1f538d",
            hover_color="#143963",
            font=self.f_jp_bold,
            width=88,
            height=32,
            command=self.controller.execute_single_frame_preview
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.export_btn = ctk.CTkButton(
            self.action_btn_frame,
            text="🎬 書き出し",
            fg_color="#2b8c54",
            hover_color="#1f6b3e",
            font=self.f_jp_bold,
            width=96,
            height=32,
            command=self.controller.execute_video_export
        )
        self.export_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.open_output_btn = ctk.CTkButton(
            self.action_btn_frame,
            text="📂 保存先",
            fg_color="#444444",
            hover_color="#666666",
            font=self.f_jp_bold,
            width=74,
            height=32,
            command=self.controller.on_open_output_dir
        )
        self.open_output_btn.pack(side="right", padx=(2, 0))

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


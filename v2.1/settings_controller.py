# -*- coding: utf-8 -*-
# settings_controller.py (STEP 4-B: 環境設定 ＆ 運指・書き出しボタンロック連動 Mixin)
# - 【バグ修正】：変え指プリセット（プルダウン）が変更されたその瞬間、即座にメモリ上の楽譜ノーツ全体の `"fingering"` キャッシュを再バインド更新（self.rebind_all_notes_fingerings）させる処理を搭載。プリセット切り替え時における演奏LEDの不追従バグも完全に解消しました。
# - 🚀【アスペクト＆スキン対応】：settings.txt からのアスペクト比・外部スキン設定の自動復元・保存処理、およびアスペクト比切り替え時のCanvas動的サイズ変更・下端不動吸着トリガー on_ratio_changed を搭載。
# - 🚀【練習Canvas自動縮小フィット解決】：比率変更時、親フレーム内にアスペクト比を完璧に維持したままフィット縮小（レターボックス化）させて中央へ綺麗に配置。
# - 🚀【トグル連動バグ根治 ＆ マゼンタ追加】：ガイド線やノーツ表示切り替え時の静的キャッシュ強制破棄を新設。第3のクロマキー色マゼンタを追加。
# - 🚀【レバーリング同期】：レバーリングトグルの保存・ロード同期に対応。

import os
import tkinter as tk
from tkinter import colorchooser
import numpy as np
import pygame
import settings_manager
import harmonica_map
from harmonica_map import (
    is_note_editable, FINGERING_CANDIDATES, SONG_FINGERING_OVERRIDES,
    save_song_fingering, get_note_name
)
from config import get_portable_path, get_visualizer_layout_params, get_note_dest_x

class SettingsController:
    # Mixinのため self は app_controller.HarmonicaAppIntegrator インスタンスを指します

    def load_user_settings(self):
        """settings_managerを介した設定自動復元"""
        loaded = settings_manager.load_settings()
        self.gui.inst_menu.set(loaded.get("ハーモニカ", "16穴 (C3-D7)"))
        self.gui.lang_menu.set(loaded.get("音名表記", "CDE"))
        
        if loaded.get("穴番号", "ON") == "ON": self.gui.hole_num_switch.select()
        else: self.gui.hole_num_switch.deselect()
        
        if loaded.get("凡例", "ON") == "ON": self.gui.show_legend_switch.select()
        else: self.gui.show_legend_switch.deselect()
        
        if loaded.get("ノーツ表示", "ON") == "ON": self.gui.show_notes_switch.select()
        else: self.gui.show_notes_switch.deselect()
        
        if loaded.get("ガイド線", "ON") == "ON": self.gui.show_grid_switch.select()
        else: self.gui.show_grid_switch.deselect()
        
        if loaded.get("着地発光", "OFF") == "ON": self.gui.show_glow_switch.select()
        else: self.gui.show_glow_switch.deselect()
            
        self.gui.opacity_entry.delete(0, tk.END)
        self.gui.opacity_entry.insert(0, loaded.get("ノーツ不透過度", "50"))
        
        val = loaded.get("動画背景色", "ノーマル（黒）")
        self.gui.bg_menu.set(val)
        # 第3のクロマキー背景マゼンタの復元ロード
        if val == "グリーンバック": self.gui.canvas_bg_color = "#00FF00"
        elif val == "ブルーバック": self.gui.canvas_bg_color = "#0000FF"
        elif val == "マゼンタ（ピンク）": self.gui.canvas_bg_color = "#FF00FF"
        else: self.gui.canvas_bg_color = "#0d0d0d"
        
        self.gui.res_menu.set(loaded.get("出力解像度", "Full HD (1920x1080)"))
        
        # カラー環境設定、および動画出力フレームレート設定のサイレント自動復元
        self.gui.theme_menu.set(loaded.get("ノーツカラーテーマ", "ノーマル"))
        self.color_blow_hex = loaded.get("吹音色", "#FF9900")
        self.color_draw_hex = loaded.get("吸音色", "#00FFFF")
        self.gui.fps_menu.set(loaded.get("フレームレート", "60 FPS"))

        # 再生音源の復元同期
        audio_mode = loaded.get("再生音源", "MIDI再生 (Windows標準音源)")
        self.gui.audio_mode_menu.set(audio_mode)
        self.sync_audio_mode_internals(audio_mode)

        # アスペクト比 ＆ 外部スキン設定の自動復元
        self.gui.ratio_menu.set(loaded.get("アスペクト比", "16:9"))
        if loaded.get("外部スキン", "ON") == "ON":
            self.gui.use_skin_switch.select()
        else:
            self.gui.use_skin_switch.deselect()

        # レバーリング連動の自動復元
        if loaded.get("レバーリング連動", "ON") == "ON":
            self.gui.show_ring_switch.select()
        else:
            self.gui.show_ring_switch.deselect()

        # ABループ状態（スイッチ、Entry、終了ティック）は settings.txt からは復元させず、
        # MIDIロード時の自動初期同期フロー（1小節〜最終小節）にすべてを安全委ねます。
        self.gui.loop_a_entry.delete(0, tk.END)
        self.gui.loop_a_entry.insert(0, "1")
        self.gui.cb_loop.deselect()
        self.midi_engine.loop_enabled = False

        # 運指プリセットの初期ロード復元
        fingering_preset = loaded.get("運指プリセット", "スライド最小化")
        if fingering_preset == "標準運指":
            fingering_preset = "スライド最小化" 
        self.gui.alt_fingering_menu.set(fingering_preset)
        harmonica_map.apply_fingering_preset(fingering_preset)

        # ノーツ軌道の復元
        traj_mode = loaded.get("ノーツ軌道", "3段階 (練習標準)")
        if traj_mode == "3段階収束 (標準)":
            traj_mode = "3段階 (練習標準)"
        if traj_mode not in ["3段階 (練習標準)", "垂直落下 (穴直上)", "2段階 (ビジュアル)"]:
            traj_mode = "3段階 (練習標準)"
        if hasattr(self.gui, "trajectory_menu"):
            self.gui.trajectory_menu.set(traj_mode)

        # ノーツ音名表示・穴下の音名（4音グリッド表示）の復元
        if hasattr(self.gui, "show_lookahead_switch"):
            if loaded.get("ノーツ音名表示", "ON") == "ON":
                self.gui.show_lookahead_switch.select()
            else:
                self.gui.show_lookahead_switch.deselect()

        if hasattr(self.gui, "grid4_menu"):
            grid4_val = loaded.get("穴下の音名", "4音グリッド表示")
            if grid4_val in ("OFF", "1音表示 (従来)"):
                self.gui.grid4_menu.set("1音表示 (従来)")
            else:
                self.gui.grid4_menu.set("4音グリッド表示")

        # ノーツ落下速度・ステップアップ設定の復元
        if hasattr(self.gui, "note_speed_menu"):
            ns_val = loaded.get("ノーツ落下速度", "1.0x (標準)")
            if ns_val not in ["0.5x", "0.75x", "1.0x (標準)", "1.25x", "1.5x", "2.0x"]:
                ns_val = "1.0x (標準)"
            self.gui.note_speed_menu.set(ns_val)

        if hasattr(self.gui, "stepup_step_menu"):
            st_step = loaded.get("ステップアップ1周増分", "+5%")
            if st_step not in ["+1%", "+2%", "+5%", "+10%"]:
                st_step = "+5%"
            self.gui.stepup_step_menu.set(st_step)

        if hasattr(self.gui, "stepup_start_entry"):
            self.gui.stepup_start_entry.delete(0, tk.END)
            self.gui.stepup_start_entry.insert(0, str(loaded.get("ステップアップ開始", "70")))

        if hasattr(self.gui, "stepup_goal_entry"):
            self.gui.stepup_goal_entry.delete(0, tk.END)
            self.gui.stepup_goal_entry.insert(0, str(loaded.get("ステップアップ目標", "100")))

        if hasattr(self.gui, "stepup_switch"):
            self.gui.stepup_switch.deselect()

        # 書き出し範囲・前後の余白・タイトル・外部音源設定の復元
        if hasattr(self.gui, "export_range_menu"):
            rng_val = loaded.get("書き出し範囲", "全曲")
            if rng_val not in ["全曲", "A〜B小節のみ"]:
                rng_val = "全曲"
            self.gui.export_range_menu.set(rng_val)

        if hasattr(self.gui, "intro_sec_menu"):
            in_val = loaded.get("前の余白", "0秒")
            if in_val not in ["0秒", "1秒", "2秒", "3秒", "5秒"]:
                in_val = "0秒"
            self.gui.intro_sec_menu.set(in_val)

        if hasattr(self.gui, "outro_sec_menu"):
            out_val = loaded.get("後の余白", "2秒")
            if out_val not in ["0秒", "1秒", "2秒", "3秒", "5秒"]:
                out_val = "2秒"
            self.gui.outro_sec_menu.set(out_val)

        if hasattr(self.gui, "fade_in_switch"):
            if loaded.get("開始フェードイン", "OFF") == "ON":
                self.gui.fade_in_switch.select()
            else:
                self.gui.fade_in_switch.deselect()

        if hasattr(self.gui, "fade_out_switch"):
            if loaded.get("終了フェードアウト", "OFF") == "ON":
                self.gui.fade_out_switch.select()
            else:
                self.gui.fade_out_switch.deselect()

        if hasattr(self.gui, "fade_in_title_menu"):
            ft_val = loaded.get("フェード時題名", "フェード中もタイトル表示")
            valid_fts = [
                "フェード中もタイトル表示",
                "フェード中はタイトル非表示",
                "画面と一緒にフェードイン"
            ]
            if ft_val not in valid_fts:
                ft_val = "フェード中もタイトル表示"
            self.gui.fade_in_title_menu.set(ft_val)

        if hasattr(self.gui, "title_template_menu"):
            tpl_val = loaded.get("タイトル配置", "なし")
            valid_tpls = ["なし", "イントロ中央のみ", "左上常時", "右上常時", "イントロ中央＋左上常時", "イントロ中央＋右上常時"]
            if tpl_val not in valid_tpls:
                tpl_val = "なし"
            self.gui.title_template_menu.set(tpl_val)

        if hasattr(self.gui, "video_title_entry"):
            self.gui.video_title_entry.delete(0, tk.END)
            self.gui.video_title_entry.insert(0, str(loaded.get("タイトル曲名", "")))

        if hasattr(self.gui, "video_credit_entry"):
            self.gui.video_credit_entry.delete(0, tk.END)
            self.gui.video_credit_entry.insert(0, str(loaded.get("タイトルサブ", "")))

        if hasattr(self.gui, "bg_image_fit_menu"):
            bg_fit_val = loaded.get("背景画像の配置", "中央トリミング (画面いっぱい)")
            valid_fits = [
                "中央トリミング (画面いっぱい)",
                "画面内に収める (全体表示)",
                "横幅に合わせる",
                "縦幅に合わせる",
                "画面に引き伸ばす"
            ]
            if bg_fit_val not in valid_fits:
                bg_fit_val = "中央トリミング (画面いっぱい)"
            self.gui.bg_image_fit_menu.set(bg_fit_val)

        if hasattr(self.gui, "bg_image_rot_menu"):
            bg_rot_val = loaded.get("背景画像の回転", "0° (自動補正)")
            valid_rots = ["0° (自動補正)", "右へ90°", "180°", "左へ90°"]
            if bg_rot_val not in valid_rots:
                bg_rot_val = "0° (自動補正)"
            self.gui.bg_image_rot_menu.set(bg_rot_val)

        if hasattr(self.gui, "bg_image_dim_menu"):
            bg_dim_val = loaded.get("背景画像の明るさ", "少し暗め (70%・ノーツ強調)")
            valid_dims = ["少し暗め (70%・ノーツ強調)", "そのまま (100%)", "半分 (50%・くっきり)", "かなり暗め (30%)"]
            if bg_dim_val not in valid_dims:
                bg_dim_val = "少し暗め (70%・ノーツ強調)"
            self.gui.bg_image_dim_menu.set(bg_dim_val)

        saved_bg_path = str(loaded.get("背景画像パス", "")).strip()
        if saved_bg_path and os.path.exists(saved_bg_path):
            self.bg_image_path = saved_bg_path
            if hasattr(self.gui, "bg_image_label"):
                fname = os.path.basename(saved_bg_path)
                disp = self._truncate_by_visual_width(fname, max_width=20) if hasattr(self, "_truncate_by_visual_width") else fname[:18]
                self.gui.bg_image_label.configure(text=disp, text_color="#00ffcc")
        else:
            self.bg_image_path = None
            if hasattr(self.gui, "bg_image_label"):
                self.gui.bg_image_label.configure(text="未選択 (ここに画像D&D可)", text_color="#888888")

        if hasattr(self.gui, "ext_audio_mode_menu"):
            em_val = loaded.get("外部音源モード", "頭出し確認 (再生:両方 / 動画:外部のみ)")
            valid_ems = [
                "頭出し確認 (再生:両方 / 動画:外部のみ)",
                "外部音源のみ (再生も動画も外部のみ)",
                "両方ミックス (再生も動画も両方)",
                "外部音源オフ (ガイド音のみ)"
            ]
            if em_val not in valid_ems:
                em_val = "頭出し確認 (再生:両方 / 動画:外部のみ)"
            self.gui.ext_audio_mode_menu.set(em_val)

        if hasattr(self.gui, "ext_audio_offset_entry"):
            self.gui.ext_audio_offset_entry.delete(0, tk.END)
            self.gui.ext_audio_offset_entry.insert(0, str(loaded.get("外部音源頭出しms", "0")))

        if hasattr(self.gui, "ext_audio_vol_entry") and hasattr(self.gui, "ext_audio_vol_slider"):
            try:
                v_pct = int(max(0, min(200, float(loaded.get("外部音源音量%", "100")))))
            except ValueError:
                v_pct = 100
            self.gui.ext_audio_vol_entry.delete(0, tk.END)
            self.gui.ext_audio_vol_entry.insert(0, str(v_pct))
            self.gui.ext_audio_vol_slider.set(v_pct)

        if hasattr(self.gui, "yt_limiter_switch"):
            if loaded.get("YouTube上限リミッター", "ON") == "ON":
                self.gui.yt_limiter_switch.select()
            else:
                self.gui.yt_limiter_switch.deselect()

        if hasattr(self.gui, "video_edit_enabled_switch"):
            if loaded.get("動画編集を動画出力に適用", "ON") == "ON":
                self.gui.video_edit_enabled_switch.select()
            else:
                self.gui.video_edit_enabled_switch.deselect()
        self.update_export_edit_summary_label()

    def is_video_edit_enabled(self):
        """🎞️ 動画編集タブの一括適用スイッチがONかどうかを返します。"""
        if hasattr(self, "gui") and hasattr(self.gui, "video_edit_enabled_switch"):
            return bool(self.gui.video_edit_enabled_switch.get())
        return True

    def get_bg_image_brightness_ratio(self):
        """背景画像の明るさ設定から 0.30〜1.00 の輝度倍率を返します。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "bg_image_dim_menu"):
            return 0.70
        val = str(self.gui.bg_image_dim_menu.get())
        if "100%" in val:
            return 1.00
        if "50%" in val:
            return 0.50
        if "30%" in val:
            return 0.30
        return 0.70

    def get_effective_bg_image_info(self):
        """動画編集スイッチがONかつ背景画像が有効な場合に (bg_image_path, brightness_ratio, fit_mode, rotation_mode) を返します。"""
        fit_mode = self.gui.bg_image_fit_menu.get() if (hasattr(self, "gui") and hasattr(self.gui, "bg_image_fit_menu")) else "中央トリミング (画面いっぱい)"
        rot_mode = self.gui.bg_image_rot_menu.get() if (hasattr(self, "gui") and hasattr(self.gui, "bg_image_rot_menu")) else "0° (自動補正)"
        if not self.is_video_edit_enabled():
            return None, 1.0, fit_mode, rot_mode
        bg_path = getattr(self, "bg_image_path", None)
        if bg_path and os.path.exists(bg_path):
            return bg_path, self.get_bg_image_brightness_ratio(), fit_mode, rot_mode
        return None, 1.0, fit_mode, rot_mode

    def on_rotate_bg_image_90(self):
        """↻ 90°回転ボタンで背景画像の回転角度を時計回りに90度ずつ順送りします。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "bg_image_rot_menu"):
            return
        order = ["0° (自動補正)", "右へ90°", "180°", "左へ90°"]
        cur = self.gui.bg_image_rot_menu.get()
        idx = (order.index(cur) + 1) % len(order) if cur in order else 1
        next_rot = order[idx]
        self.gui.bg_image_rot_menu.set(next_rot)
        self.on_setting_changed()
        self.gui.status_label.configure(text=f"🖼️ 背景画像の回転: {next_rot}", text_color="#00ffcc")

    def load_bg_image_file(self, file_path):
        """指定パスの画像ファイルを検証し、背景画像としてセット・即時描画します（D&D・ダイアログ共通）。"""
        from PIL import Image
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            with Image.open(file_path) as img:
                img.verify()
            self.bg_image_path = file_path
            fname = os.path.basename(file_path)
            disp = self._truncate_by_visual_width(fname, max_width=20) if hasattr(self, "_truncate_by_visual_width") else fname[:18]
            if hasattr(self.gui, "bg_image_label"):
                self.gui.bg_image_label.configure(text=disp, text_color="#00ffcc")
            if hasattr(self.gui, "video_edit_enabled_switch") and not self.gui.video_edit_enabled_switch.get():
                self.gui.video_edit_enabled_switch.select()
                self.update_export_edit_summary_label()
            self.on_setting_changed()
            self.gui.status_label.configure(
                text=f"🖼️ 背景画像をセットしました: {disp}（配置・回転・明るさを調整可能）",
                text_color="#2b8c54"
            )
            return True
        except Exception as e:
            self.gui.status_label.configure(text=f"❌ 背景画像の読み込み失敗: {e}", text_color="#ff5555")
            return False

    def on_select_bg_image(self):
        """🖼️ 背景画像ファイル（PNG/JPG/WebP等）を選択し、プレビューと動画出力へ反映します。"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="背景に合成する画像ファイルを選択してください",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        self.load_bg_image_file(file_path)

    def on_clear_bg_image(self):
        """選択中の背景画像を解除し、通常の背景色（黒やグリーンバック等）へ戻します。"""
        self.bg_image_path = None
        if hasattr(self.gui, "bg_image_label"):
            self.gui.bg_image_label.configure(text="未選択 (ここに画像D&D可)", text_color="#888888")
        self.on_setting_changed()
        self.gui.status_label.configure(text="背景画像を解除しました（通常の背景色を使用）", text_color="#aaaaaa")

    def update_export_edit_summary_label(self):
        """🎬 動画出力タブの下部にある動画編集反映ステータスバッジを更新します。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "export_edit_summary_lbl"):
            return
        if self.is_video_edit_enabled():
            self.gui.export_edit_summary_lbl.configure(
                text="✨ 動画編集の適用: ON（🎞️動画編集タブの設定を反映）",
                text_color="#00ffcc"
            )
        else:
            self.gui.export_edit_summary_lbl.configure(
                text="⚪ 動画編集の適用: OFF（純粋なビジュアライザー動画を出力）",
                text_color="#aaaaaa"
            )

    def on_video_edit_master_toggle(self):
        """🎞️ 動画編集タブ最上部のマスタースイッチ切替時のハンドラ"""
        is_on = self.is_video_edit_enabled()
        self.update_export_edit_summary_label()
        if hasattr(self, "gui") and self.gui.canvas:
            self.gui.canvas._static_state_key = None
            self.gui.canvas.delete("static_plate")
        if getattr(self, "play_state", "stopped") == "playing":
            if hasattr(self, "_apply_effective_guide_audio_mode"):
                self._apply_effective_guide_audio_mode()
            if hasattr(self, "sync_ext_audio_playback"):
                self.sync_ext_audio_playback()
        else:
            self.draw_harmonica_static()
        if is_on:
            self.gui.status_label.configure(
                text="✨ 動画編集の適用: ON（タイトル・背景画像・外部音源を動画出力および試聴に反映します）",
                text_color="#00ffcc"
            )
        else:
            self.gui.status_label.configure(
                text="⚪ 動画編集の適用: OFF（入力内容を保持したまま、純粋なビジュアライザーとして出力します）",
                text_color="#aaaaaa"
            )
        self.save_user_settings_txt()

    def get_intro_outro_seconds(self):
        """イントロ秒数・アウトロ秒数を float タプル (intro_sec, outro_sec) として返します。"""
        in_sec = 0.0
        out_sec = 2.0
        if hasattr(self, "gui"):
            if hasattr(self.gui, "intro_sec_menu"):
                try:
                    in_sec = float(str(self.gui.intro_sec_menu.get()).replace("秒", "").strip())
                except ValueError:
                    in_sec = 0.0
            if hasattr(self.gui, "outro_sec_menu"):
                try:
                    out_sec = float(str(self.gui.outro_sec_menu.get()).replace("秒", "").strip())
                except ValueError:
                    out_sec = 2.0
        return max(0.0, in_sec), max(0.0, out_sec)

    def on_open_output_dir(self):
        """動画の出力先フォルダ（output）をOSのエクスプローラーで開きます。"""
        out_dir = get_portable_path("output")
        os.makedirs(out_dir, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(out_dir)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", out_dir])
            self.gui.status_label.configure(text=f"📂 保存先フォルダを開きました: {out_dir}", text_color="#00ffcc")
        except Exception as e:
            self.gui.status_label.configure(text=f"フォルダを開けませんでした: {e}", text_color="#ff5555")

    def get_note_speed_ratio(self):
        """ノーツ落下速度メニュー（0.5x〜2.0x）から数値倍率を返します。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "note_speed_menu"):
            return 1.0
        raw = str(self.gui.note_speed_menu.get()).split("x")[0].strip()
        try:
            return max(0.25, min(4.0, float(raw)))
        except ValueError:
            return 1.0

    def get_stepup_params(self):
        """ステップアップ設定（開始%・目標%・1周増分%）を安全に検証して返します。"""
        start_pct = 70.0
        goal_pct = 100.0
        step_pct = 5.0
        if hasattr(self, "gui"):
            if hasattr(self.gui, "stepup_start_entry"):
                try:
                    start_pct = float(str(self.gui.stepup_start_entry.get()).replace("%", "").strip())
                except ValueError:
                    start_pct = 70.0
            if hasattr(self.gui, "stepup_goal_entry"):
                try:
                    goal_pct = float(str(self.gui.stepup_goal_entry.get()).replace("%", "").strip())
                except ValueError:
                    goal_pct = 100.0
            if hasattr(self.gui, "stepup_step_menu"):
                try:
                    step_pct = float(str(self.gui.stepup_step_menu.get()).replace("+", "").replace("%", "").strip())
                except ValueError:
                    step_pct = 5.0
        start_pct = max(10.0, min(400.0, start_pct))
        goal_pct = max(10.0, min(400.0, goal_pct))
        if goal_pct < start_pct:
            goal_pct = start_pct
        return int(round(start_pct)), int(round(goal_pct)), int(round(step_pct))

    def on_stepup_toggle(self):
        """ステップアップ練習スイッチ切替時のハンドラ（ON時はA-Bループも自動でONに連動）"""
        is_on = bool(self.gui.stepup_switch.get())
        start_pct, goal_pct, step_pct = self.get_stepup_params()
        if is_on:
            if not self.gui.cb_loop.get():
                self.gui.cb_loop.select()
                self.on_loop_toggle()
            if getattr(self, "play_state", "stopped") == "stopped":
                self.gui.bpm_entry.delete(0, tk.END)
                self.gui.bpm_entry.insert(0, str(start_pct))
                self.apply_bpm()
            self.gui.status_label.configure(
                text=f"📈 ステップアップ有効: {start_pct}% ➔ {goal_pct}% (+{step_pct}%/周)",
                text_color="#00ffcc"
            )
        else:
            self.gui.status_label.configure(text="ステップアップ練習をOFFにしました", text_color="#aaaaaa")
        self.save_user_settings_txt()

    def on_stepup_param_changed(self, value=None):
        """ステップアップの開始%・目標%・増分%変更時の正規化と保存"""
        start_pct, goal_pct, step_pct = self.get_stepup_params()
        if hasattr(self.gui, "stepup_start_entry"):
            self.gui.stepup_start_entry.delete(0, tk.END)
            self.gui.stepup_start_entry.insert(0, str(start_pct))
        if hasattr(self.gui, "stepup_goal_entry"):
            self.gui.stepup_goal_entry.delete(0, tk.END)
            self.gui.stepup_goal_entry.insert(0, str(goal_pct))
        if hasattr(self.gui, "stepup_switch") and self.gui.stepup_switch.get():
            if getattr(self, "play_state", "stopped") == "stopped":
                self.gui.bpm_entry.delete(0, tk.END)
                self.gui.bpm_entry.insert(0, str(start_pct))
                self.apply_bpm()
            self.gui.status_label.configure(
                text=f"📈 ステップアップ設定: {start_pct}% ➔ {goal_pct}% (+{step_pct}%/周)",
                text_color="#00ffcc"
            )
        self.save_user_settings_txt()

    def save_user_settings_txt(self):
        """settings_managerへの設定自動保存（現在の4タブUI表示名と完全一致）"""
        settings_manager.save_settings(
            inst=self.gui.inst_menu.get(), 
            lang=self.gui.lang_menu.get(),  
            hole="ON" if self.gui.hole_num_switch.get() else "OFF",
            legend="ON" if self.gui.show_legend_switch.get() else "OFF",
            notes="ON" if self.gui.show_notes_switch.get() else "OFF",
            grid="ON" if self.gui.show_grid_switch.get() else "OFF",
            glow="ON" if self.gui.show_glow_switch.get() else "OFF",
            opacity=self.gui.opacity_entry.get(), 
            bg=self.gui.bg_menu.get(), 
            res=self.gui.res_menu.get(),
            theme=self.gui.theme_menu.get(),       
            blow=self.color_blow_hex,              
            draw=self.color_draw_hex,
            fps=self.gui.fps_menu.get(),
            audio_mode=self.gui.audio_mode_menu.get(),
            fingering_preset=self.gui.alt_fingering_menu.get(),
            ratio=self.gui.ratio_menu.get(),
            use_skin="ON" if self.gui.use_skin_switch.get() else "OFF",
            ring="ON" if self.gui.show_ring_switch.get() else "OFF",
            trajectory=self.gui.trajectory_menu.get() if hasattr(self.gui, "trajectory_menu") else "3段階 (練習標準)",
            lookahead=("ON" if self.gui.show_lookahead_switch.get() else "OFF") if hasattr(self.gui, "show_lookahead_switch") else "ON",
            grid4=self.gui.grid4_menu.get() if hasattr(self.gui, "grid4_menu") else "4音グリッド表示",
            **{
                "ノーツ落下速度": self.gui.note_speed_menu.get() if hasattr(self.gui, "note_speed_menu") else "1.0x (標準)",
                "ステップアップ1周増分": self.gui.stepup_step_menu.get() if hasattr(self.gui, "stepup_step_menu") else "+5%",
                "ステップアップ開始": self.gui.stepup_start_entry.get() if hasattr(self.gui, "stepup_start_entry") else "70",
                "ステップアップ目標": self.gui.stepup_goal_entry.get() if hasattr(self.gui, "stepup_goal_entry") else "100",
                "書き出し範囲": self.gui.export_range_menu.get() if hasattr(self.gui, "export_range_menu") else "全曲",
                "前の余白": self.gui.intro_sec_menu.get() if hasattr(self.gui, "intro_sec_menu") else "0秒",
                "後の余白": self.gui.outro_sec_menu.get() if hasattr(self.gui, "outro_sec_menu") else "2秒",
                "開始フェードイン": ("ON" if self.gui.fade_in_switch.get() else "OFF") if hasattr(self.gui, "fade_in_switch") else "OFF",
                "終了フェードアウト": ("ON" if self.gui.fade_out_switch.get() else "OFF") if hasattr(self.gui, "fade_out_switch") else "OFF",
                "フェード時題名": self.gui.fade_in_title_menu.get() if hasattr(self.gui, "fade_in_title_menu") else "フェード中もタイトル表示",
                "タイトル配置": self.gui.title_template_menu.get() if hasattr(self.gui, "title_template_menu") else "なし",
                "タイトル曲名": self.gui.video_title_entry.get() if hasattr(self.gui, "video_title_entry") else "",
                "タイトルサブ": self.gui.video_credit_entry.get() if hasattr(self.gui, "video_credit_entry") else "",
                "外部音源モード": self.gui.ext_audio_mode_menu.get() if hasattr(self.gui, "ext_audio_mode_menu") else "頭出し確認 (再生:両方 / 動画:外部のみ)",
                "外部音源頭出しms": self.gui.ext_audio_offset_entry.get() if hasattr(self.gui, "ext_audio_offset_entry") else "0",
                "外部音源音量%": self.gui.ext_audio_vol_entry.get() if hasattr(self.gui, "ext_audio_vol_entry") else "100",
                "YouTube上限リミッター": ("ON" if self.gui.yt_limiter_switch.get() else "OFF") if hasattr(self.gui, "yt_limiter_switch") else "ON",
                "動画編集を動画出力に適用": ("ON" if self.gui.video_edit_enabled_switch.get() else "OFF") if hasattr(self.gui, "video_edit_enabled_switch") else "ON",
                "背景画像パス": getattr(self, "bg_image_path", "") or "",
                "背景画像の配置": self.gui.bg_image_fit_menu.get() if hasattr(self.gui, "bg_image_fit_menu") else "中央トリミング (画面いっぱい)",
                "背景画像の回転": self.gui.bg_image_rot_menu.get() if hasattr(self.gui, "bg_image_rot_menu") else "0° (自動補正)",
                "背景画像の明るさ": self.gui.bg_image_dim_menu.get() if hasattr(self.gui, "bg_image_dim_menu") else "少し暗め (70%・ノーツ強調)",
            }
        )
        self.update_export_edit_summary_label()

    def on_setting_changed(self, value=None):
        # トグル表示（ガイド線/ノーツ表示/落下軌道など）切り替え時に
        # Canvas内の静的状態キャッシュを無効化し、再生中・一時停止中にかかわらず即座に再構築反映。
        if hasattr(self, "gui") and self.gui.canvas:
            self.gui.canvas._static_state_key = None
            self.gui.canvas.delete("static_plate")
            if hasattr(self.gui.canvas, "note_pool"):
                for pool_item in self.gui.canvas.note_pool.values():
                    for k_id, cid in pool_item.items():
                        if k_id != "style_key" and cid is not None:
                            self.gui.canvas.delete(cid)
                self.gui.canvas.note_pool.clear()
            if hasattr(self.gui.canvas, "measure_pool"):
                for lid, tid in self.gui.canvas.measure_pool.values():
                    if lid is not None:
                        self.gui.canvas.delete(lid)
                    if tid is not None:
                        self.gui.canvas.delete(tid)
                self.gui.canvas.measure_pool.clear()

        if self.midi_notes and self.midi_notes[0].get("_bound_inst") != self.gui.inst_menu.get():
            self.rebind_all_notes_fingerings()

        self.apply_bpm()
        if getattr(self, "play_state", "stopped") != "playing":
            self.draw_harmonica_static()
        self.save_user_settings_txt()

    def sync_audio_mode_internals(self, mode_str):
        if "MIDI再生" in mode_str:
            self.midi_engine.device_muted = False
            self.midi_engine.internal_synth_enabled = False
        elif "簡易再生" in mode_str:
            self.midi_engine.device_muted = True
            self.midi_engine.internal_synth_enabled = True
        else:
            self.midi_engine.device_muted = True
            self.midi_engine.internal_synth_enabled = False

    def on_audio_mode_changed(self, value):
        self.on_stop()
        self.sync_audio_mode_internals(value)
        self.save_user_settings_txt()

    def on_bg_change(self, value):
        # 第3のクロマキーマゼンタの検出反映イベントを完備
        if value == "グリーンバック": 
            self.gui.canvas_bg_color = "#00FF00"
        elif value == "ブルーバック": 
            self.gui.canvas_bg_color = "#0000FF"
        elif value == "マゼンタ（ピンク）":
            self.gui.canvas_bg_color = "#FF00FF"
        else: 
            self.gui.canvas_bg_color = "#0d0d0d"
        self.draw_harmonica_static()
        self.save_user_settings_txt()

    def on_theme_changed(self, value):
        themes = {
            "ノーマル": ("#FF9900", "#00FFFF"),       
            "サクラ": ("#FFB7C5", "#3CB371"),         
            "クールネオン": ("#FF007F", "#1E90FF"),   
            "モノクロ": ("#FFFFFF", "#7F7F7F")        
        }
        
        if value in themes:
            self.color_blow_hex, self.color_draw_hex = themes[value]
        
        self.draw_harmonica_static()
        self.save_user_settings_txt()

    def choose_color_blow(self):
        self.gui.theme_menu.set("カスタム")
        color_code = colorchooser.askcolor(initialcolor=self.color_blow_hex, title="吹音(Blow)のカラーテーマ色を選択")
        if color_code and color_code[1]:
            self.color_blow_hex = color_code[1]
            self.draw_harmonica_static()
            self.save_user_settings_txt()

    def choose_color_draw(self):
        self.gui.theme_menu.set("カスタム")
        color_code = colorchooser.askcolor(initialcolor=self.color_draw_hex, title="吸音(Draw)のカラーテーマ色を選択")
        if color_code and color_code[1]:
            self.color_draw_hex = color_code[1]
            self.draw_harmonica_static()
            self.save_user_settings_txt()

    # 曲別のプリセット選択状態を変更した際
    def on_fingering_preset_changed(self, value):
        """曲別のプリセット選択状態を更新し、プロパティファイルへ同期セーブ、かつメモリ上の運指キャッシュも即座に再解決更新します。"""
        harmonica_map.CURRENT_SONG_PRESET = value
        harmonica_map.apply_fingering_preset(value)
        harmonica_map.save_song_fingering(self.current_midi_path)
        
        # プリセット選択プルダウンが切り替わった瞬間に、メモリ上の全ノーツ運指キャッシュを即座に再評価・更新！
        # これにより、再生中のLED点滅やレバー変形が瞬時かつ完全に連動追従するようになります。
        self.rebind_all_notes_fingerings()
        
        self.draw_harmonica_static()
        self.save_user_settings_txt()

    def on_fingering_edit_toggle(self):
        """運指変更モード中の「🎬 書き出し」ボタンのロック制御を完璧に行います。"""
        self.fingering_edit_mode = bool(self.gui.fingering_edit_switch.get())
        
        if self.fingering_edit_mode:
            self.gui.export_btn.configure(state="disabled")
            self.gui.status_label.configure(
                text="🎯 運指変更モード：有効（赤色ノーツをクリックで循環）", 
                text_color="#ff3333"
            )
        else:
            self.gui.export_btn.configure(state="normal")
            self.gui.status_label.configure(
                text="待機中...", 
                text_color="#777777"
            )
            
        self.draw_harmonica_static()

    def on_reset_song_fingering(self):
        """現在の曲でクリック変更した個別運指データをすべて初期化（リセット）します。"""
        from tkinter import messagebox
        ans = messagebox.askyesno(
            "運指データの初期化確認",
            "現在の曲で変更した運指設定ファイルを初期化（リセット）し、\nベース運指プリセットの初期状態へ戻しますか？",
            parent=self
        )
        if not ans:
            return

        harmonica_map.reset_song_fingering(self.current_midi_path)
        self.last_edited_note_name = None
        self.last_edited_fingering = None

        self.rebind_all_notes_fingerings()
        self.draw_harmonica_static()

        self.gui.status_label.configure(
            text="🔄 曲別の運指データを初期状態にリセットしました",
            text_color="#2ecc71"
        )

    def on_canvas_click(self, event):
        """Canvasクリック時にEntry等からフォーカスを外し、運指変更モード時は対象ノーツの運指設定を循環させます。"""
        try:
            self.gui.canvas.focus_set()
        except Exception:
            pass
        if not self.fingering_edit_mode:
            return
            
        items = self.gui.canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        for item in items:
            tags = self.gui.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("note_edit_"):
                    parts = tag.split("_")
                    if len(parts) == 4:
                        start_tick = int(parts[2])
                        note_val = int(parts[3])
                        self.cycle_note_fingering(start_tick, note_val)
                        return

    def cycle_note_fingering(self, start_tick, note_val):
        """対象ノーツのオーバーライドインデックスを循環させ、右上に常時描画させるための状態を更新します。"""
        if not is_note_editable(note_val, self.gui.inst_menu.get()):
            return

        lookup_note = note_val
        if "バス" in self.gui.inst_menu.get():
            lookup_note = note_val + 36
            
        if lookup_note not in FINGERING_CANDIDATES:
            return
            
        candidates = FINGERING_CANDIDATES[lookup_note]
        current_idx = SONG_FINGERING_OVERRIDES.get((start_tick, lookup_note), 0)
        
        next_idx = (current_idx + 1) % len(candidates)
        SONG_FINGERING_OVERRIDES[(start_tick, lookup_note)] = next_idx
        
        new_f = candidates[next_idx]
        new_str = f"{new_f['hole']}穴 {new_f['action']} {new_f['lever']}"
        
        save_song_fingering(self.current_midi_path)
        self.rebind_all_notes_fingerings()
        self.play_edit_click_sound()
        
        note_name_str = get_note_name(note_val, is_japanese=("ドレミ" in self.gui.lang_menu.get()))
        self.last_edited_note_name = note_name_str
        self.last_edited_fingering = new_str
        
        self.gui.status_label.configure(
            text=f"切替: {note_name_str} ({new_str})", 
            text_color="#ffcc00"
        )
        self.draw_harmonica_static()

    def play_edit_click_sound(self):
        try:
            sample_rate = 44100
            duration = 0.05  
            t = np.arange(0, duration, 1.0 / sample_rate)
            wave_data = np.sin(2.0 * np.pi * 1600.0 * t)
            
            fade_len = int(sample_rate * 0.01)
            wave_data[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
            
            pcm_data = (wave_data * 12000).astype(np.int16)
            sound = pygame.mixer.Sound(buffer=pcm_data)
            sound.set_volume(self.midi_engine.volume_factor * 0.4)
            sound.play()
        except Exception as e:
            print(f"[警告] 効果音生成失敗: {e}")

    def rebind_all_notes_fingerings(self):
        """すべての楽譜ノーツに対して、解決済み運指・音域内外・落下先X座標・音名を事前計算して埋め込みます。"""
        if not self.midi_notes:
            return
        inst_type = self.gui.inst_menu.get()
        for note_data in self.midi_notes:
            start_tick = note_data.get("start_tick", 0)
            note_val = note_data["note"]
            note_data["fingering"] = harmonica_map.get_note_fingering_for_song(start_tick, note_val, inst_type)
            note_data["in_range"] = harmonica_map.is_note_in_range(note_val, inst_type)
            note_data["is_editable"] = harmonica_map.is_note_editable(note_val, inst_type)
            note_data["name_cde"] = harmonica_map.get_note_name(note_val, is_japanese=False)
            note_data["name_jp"] = harmonica_map.get_note_name(note_val, is_japanese=True)
            note_data["dest_x_base"] = get_note_dest_x(note_val, inst_type, scale=1.0, start_tick=start_tick)
            note_data["_bound_inst"] = inst_type
        print("[システム] すべての音符オブジェクトへの運指・座標プリ・バインドが完了しました。")

    def get_effective_canvas_ratio(self):
        """
        練習タブ（🎵 練習）選択時は常に最大横幅の 16:9 で見やすく表示し、
        デザイン・動画出力タブ選択時は設定された出力アスペクト比をプレビュー反映します。
        """
        if not hasattr(self, "gui"):
            return "16:9"
        if hasattr(self.gui, "sidebar_mode_seg") and self.gui.sidebar_mode_seg.get() == "🎵 練習":
            return "16:9"
        return self.gui.ratio_menu.get()

    def get_current_canvas_layout(self):
        """現在の canvas_frame の実寸と実効アスペクト比から、表示用Canvasの (width, height, scale) を返します。"""
        effective_ratio = self.get_effective_canvas_ratio()
        max_w, max_h = 960, 540
        if hasattr(self, "gui") and hasattr(self.gui, "canvas_frame"):
            fw = self.gui.canvas_frame.winfo_width()
            fh = self.gui.canvas_frame.winfo_height()
            if fw > 200 and fh > 200:
                max_w = max(320, fw - 20)
                max_h = max(240, fh - 20)
        return get_visualizer_layout_params(effective_ratio, max_w=max_w, max_h=max_h)

    def sync_canvas_size_to_active_ratio(self):
        """現在の実効アスペクト比およびウィンドウサイズに合わせて表示用Canvasのサイズとキャッシュを同期します。"""
        if not hasattr(self, "gui") or not self.gui.canvas:
            return
        effective_ratio = self.get_effective_canvas_ratio()
        if hasattr(self.gui, "canvas_frame"):
            fw = self.gui.canvas_frame.winfo_width()
            fh = self.gui.canvas_frame.winfo_height()
            if fw > 200 and fh > 200:
                self._synced_frame_wh = (fw, fh, effective_ratio)
        w, h, scale = self.get_current_canvas_layout()
        self._current_canvas_scale = scale
        cur_w = int(self.gui.canvas.cget("width"))
        cur_h = int(self.gui.canvas.cget("height"))
        if cur_w != w or cur_h != h:
            self.gui.canvas.configure(width=w, height=h)
            self.gui.canvas.place(relx=0.5, rely=0.5, anchor="center")

        if hasattr(self.gui.canvas, "skin_cache"):
            self.gui.canvas.skin_cache.clear()
        self.gui.canvas.delete("static_plate")

    def on_canvas_frame_configure(self, event=None):
        """ウィンドウ最大化・リサイズ時にアスペクト比を維持したままCanvasを自動追従フィットさせます。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "canvas_frame"):
            return
        try:
            if not self.gui.canvas_frame.winfo_exists():
                return
            fw = self.gui.canvas_frame.winfo_width()
            fh = self.gui.canvas_frame.winfo_height()
        except Exception:
            return
        if fw <= 200 or fh <= 200:
            return
        new_size = (fw, fh)
        if new_size == getattr(self, "_last_canvas_frame_size", (0, 0)):
            return
        self._last_canvas_frame_size = new_size
        pending = getattr(self, "_resize_after_id", None)
        if pending is not None:
            try:
                self.after_cancel(pending)
            except Exception:
                pass
        self._resize_after_id = self.after(20, self._apply_canvas_frame_resize)

    def _apply_canvas_frame_resize(self):
        self._resize_after_id = None
        self.sync_canvas_size_to_active_ratio()
        if getattr(self, "play_state", "stopped") != "playing":
            self.draw_harmonica_static()

    def on_sidebar_tab_changed(self, tab_name):
        """右サイドバーのタブ切替時にCanvasの表示比率・描画を即時同期します。"""
        self.sync_canvas_size_to_active_ratio()
        self.draw_harmonica_static()

    # アスペクト比変更イベントフック
    def on_ratio_changed(self, value):
        """
        アスペクト比プルダウン（16:9/9:16/4:3）の変更を検知した瞬間、
        表示用Canvasの物理サイズを拡大縮小し、親枠内の中央に綺麗にフィット（レターボックス）配置します。
        """
        self.sync_canvas_size_to_active_ratio()
        self.apply_bpm()
        self.draw_harmonica_static()
        self.save_user_settings_txt()

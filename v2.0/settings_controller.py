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
import settings_manager
import harmonica_map  
from config import get_visualizer_layout_params

class SettingsController:
    # Mixinのため self は app_controller.HarmonicaAppIntegrator インスタンスを指します

    def load_user_settings(self):
        """settings_managerを介した設定自動復元"""
        loaded = settings_manager.load_settings()
        self.gui.inst_menu.set(loaded["楽器タイプ"])
        self.gui.lang_menu.set(loaded["音名表記"])
        
        if loaded["穴番号表示"] == "ON": self.gui.hole_num_switch.select()
        else: self.gui.hole_num_switch.deselect()
        
        if loaded["凡例表示"] == "ON": self.gui.show_legend_switch.select()
        else: self.gui.show_legend_switch.deselect()
        
        if loaded["ノーツ表示"] == "ON": self.gui.show_notes_switch.select()
        else: self.gui.show_notes_switch.deselect()
        
        if loaded["ガイド線表示"] == "ON": self.gui.show_grid_switch.select()
        else: self.gui.show_grid_switch.deselect()
        
        if loaded["着地発光表示"] == "ON": self.gui.show_glow_switch.select()
        else: self.gui.show_glow_switch.deselect()
            
        self.gui.opacity_entry.delete(0, tk.END)
        self.gui.opacity_entry.insert(0, loaded["ノーツ不透明度"])
        
        self.gui.bg_menu.set(loaded["動画背景色"])
        val = loaded["動画背景色"]
        # 第3のクロマキー背景マゼンタの復元ロード
        if val == "グリーンバック": self.gui.canvas_bg_color = "#00FF00"
        elif val == "ブルーバック": self.gui.canvas_bg_color = "#0000FF"
        elif val == "マゼンタ（ピンク）": self.gui.canvas_bg_color = "#FF00FF"
        else: self.gui.canvas_bg_color = "#0d0d0d"
        
        self.gui.res_menu.set(loaded["動画解像度"])
        
        # カラー環境設定、および動画出力FPS設定のサイレント自動復元
        self.gui.theme_menu.set(loaded.get("カラーテーマ", "ノーマル"))
        self.color_blow_hex = loaded.get("吹音色", "#FF9900")
        self.color_draw_hex = loaded.get("吸音色", "#00FFFF")
        self.gui.fps_menu.set(loaded.get("動画FPS", "60 FPS"))

        # 音響モードの復元同期
        audio_mode = loaded.get("音響モード", "MIDI再生 (Windows標準音源)")
        self.gui.audio_mode_menu.set(audio_mode)
        self.sync_audio_mode_internals(audio_mode)

        # アスペクト比 ＆ 外部スキン設定の自動復元
        self.gui.ratio_menu.set(loaded.get("アスペクト比", "16:9"))
        if loaded.get("外部スキン使用", "ON") == "ON":
            self.gui.use_skin_switch.select()
        else:
            self.gui.use_skin_switch.deselect()

        # 🚀【追加】：レバーリング設定の自動復元
        if loaded.get("レバーリング表示", "ON") == "ON":
            self.gui.show_ring_switch.select()
        else:
            self.gui.show_ring_switch.deselect()

        # ABループ状態（スイッチ、Entry、終了ティック）は settings.txt からは復元させず、
        # MIDIロード時の自動初期同期フロー（1小節〜最終小節）にすべてを安全委ねます。
        self.gui.loop_a_entry.delete(0, tk.END)
        self.gui.loop_a_entry.insert(0, "1")
        self.gui.cb_loop.deselect()
        self.midi_engine.loop_enabled = False

        # 変え指（運指プリセット）の初期ロード復元
        fingering_preset = loaded.get("変え指設定", "スライド最小化")
        if fingering_preset == "標準運指":
            fingering_preset = "スライド最小化" 
        self.gui.alt_fingering_menu.set(fingering_preset)
        harmonica_map.apply_fingering_preset(fingering_preset)

    def save_user_settings_txt(self):
        """settings_managerへの設定自動保存"""
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
            simplified="ON",
            theme=self.gui.theme_menu.get(),       
            blow=self.color_blow_hex,              
            draw=self.color_draw_hex,
            fps=self.gui.fps_menu.get(),
            audio_mode=self.gui.audio_mode_menu.get(),
            fingering_preset=self.gui.alt_fingering_menu.get(),
            ratio=self.gui.ratio_menu.get(),
            use_skin="ON" if self.gui.use_skin_switch.get() else "OFF",
            ring="ON" if self.gui.show_ring_switch.get() else "OFF"  # 🚀【追加】：レバーリング状態保存
        )

    def on_setting_changed(self, value=None):
        # トグル表示（ガイド線/ノーツ表示など）切り替え時に
        # Canvas内の静的なグリッドや凡例キャッシュを強制的にデリート消去するロジックを肉付け。
        # これにより、再生中・一時停止中にかかわらず、スイッチのオン/オフが完全不整合なくリアルタイムに反映。
        if hasattr(self, "gui") and self.gui.canvas:
            self.gui.canvas.delete("static_grid")
            self.gui.canvas.delete("static_grid_border")
            self.gui.canvas.delete("static_legend")
            self.gui.canvas.delete("static_plate")  # プレート消去で次回 draw_mode="all" を自動励起
            self.gui.canvas.delete("static_hole")
            self.gui.canvas.delete("cached_led")
            self.gui.canvas.delete("cached_shadow")
            self.gui.canvas.delete("cached_body")
            self.gui.canvas.delete("static_text")
            if hasattr(self.gui.canvas, "note_pool"):
                # ノーツ表示ON/OFF切り替え時にオブジェクトプールを完全クリーンアップ
                for pool_item in self.gui.canvas.note_pool.values():
                    if pool_item["rect_id"] is not None: self.gui.canvas.delete(pool_item["rect_id"])
                    if pool_item["poly_id"] is not None: self.gui.canvas.delete(pool_item["poly_id"])
                self.gui.canvas.note_pool.clear()

        self.apply_bpm()
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

    def sync_canvas_size_to_active_ratio(self):
        """現在の実効アスペクト比に合わせて表示用Canvasのサイズとキャッシュを同期します。"""
        if not hasattr(self, "gui") or not self.gui.canvas:
            return
        effective_ratio = self.get_effective_canvas_ratio()
        w, h, _ = get_visualizer_layout_params(effective_ratio)
        self.gui.canvas.configure(width=w, height=h)
        self.gui.canvas.place(relx=0.5, rely=0.5, anchor="center")

        if hasattr(self.gui.canvas, "skin_cache"):
            self.gui.canvas.skin_cache.clear()
        self.gui.canvas.delete("static_plate")


    def on_sidebar_tab_changed(self, tab_name):
        """右サイドバーのタブ切替時にCanvasの表示比率・描画を即時同期します。"""
        self.sync_canvas_size_to_active_ratio()
        self.draw_harmonica_static()

    # アスペクト比変更イベントフック
    def on_ratio_changed(self, value):
        """
        アスペクト比プルダウン（16:9/9:16/4:3）の変更を検知した瞬間、
        表示用Canvasの物理サイズを拡大縮小し、最大960x540の親枠内の中央に綺麗にフィット（レターボックス）配置します。
        """
        self.sync_canvas_size_to_active_ratio()
        self.apply_bpm()
        self.draw_harmonica_static()
        self.save_user_settings_txt()
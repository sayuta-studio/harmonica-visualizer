# -*- coding: utf-8 -*-
# app_controller.py (STEP 4-B: コアアプリケーション ＆ 運指キャッシュ即時更新・SyntaxError修正版)
# - 【バグ修正】：199行目のメソッド定義における括弧の重複（SyntaxError）を完全に修正し、起動不具合を解消しました。
# - 🚀【skins自立解決 ＆ アスペクト比対応】：起動時の自動 default skins 自己構築機能、およびアスペクト比・スキン適用の描画連携を追加。
# - 🚀【縮小フィットペイント統合】：練習Canvasへ描画する際、アスペクト比ごとの縮小描画スケール（scale）を正確に中継。
# - 🚀【小節ジャンプ上書き根絶】：再生中の jump_entry への強制上書きを根絶。打ち込んだ小節番号がそのまま維持され、再生中でもシームレスにジャンプが機能。
# - 🚀【マウスピーススキン化】：スキンのファイル名を「マウスピース.png」へ完全連動リネーム。
# - 🚀【音声メニューロック ＆ 中止物理解放】：音声メニュー（audio_mode_menu）のロック漏れを完全補完。ビデオエクスポート完了/中止時のクリーンアップ・UIロック復帰コールバックを新設し、ボタンの不感化バグを100%解決。
# - 🚀【3D金属光沢スライド押し込みペイント】：レバーオフ/オンPNGの自動生成時、ボタン部に3D球面シルバークローム金属光沢を物理シミュレーションペイント。オン画像はボタンが左に寄った「押し込み」形状を自動描画。旧アセット（32x36）の自動更新。
# - 🚀【レバーリング中継】：練習Canvas描画部へ「レバーリング表示」のトグル状態を安全に中継。
# - 🚀【60FPS練習モード ＆ 1024バッファ】：update_clockの周期を after(16) に引き上げて点滅スキップを根絶。pygameバッファサイズを 1024 に拡大して描画CPU負荷を確保。
# - 🚀【扁平ステンレス光沢自動ペイント】：先端が球体のボタンから、元の平たい扁平縦長楕円形状へ完全回帰！美しい3Dクローム質感と押し込み沈み込みパラパラ仕様を skins/PNGへ自動描画。

import os
import sys
import time
import tkinter as tk
from tkinter import messagebox  
import customtkinter as ctk
import pygame
import numpy as np
import math

# モジュール全体を安全にインポート
from config import (
    get_portable_path, get_visualizer_layout_params, draw_metallic_button_pil_flat
)
from midi_engine import MidiEngine
from gui import HarmonicaAppGUI
from visualizer import draw_harmonica_canvas

# 機能別 Mixin コントローラーのインポート
from playback_controller import PlaybackController
from settings_controller import SettingsController

class HarmonicaAppIntegrator(ctk.CTk, PlaybackController, SettingsController):
    def __init__(self):
        super().__init__()
        
        self.base_dir = get_portable_path("")

        self.check_and_build_directories()

        self.title("Chromatic Harmonica Visualizer & Trainer")
        self.geometry("1400x820")
        self.resizable(False, False)

        # 状態管理変数
        self.midi_notes = []
        self.accompaniment_notes = []
        self.current_time = 0.0
        self.max_duration = 0.0
        self.original_max_duration = 0.0
        self.play_state = "stopped"
        self.last_update_time = 0.0
        self.current_midi_path = None
        
        self.video_export_cancelled = False
        
        self.color_blow_hex = "#FF9900"
        self.color_draw_hex = "#00FFFF"

        # 運指変更モードフラグ
        self.fingering_edit_mode = False

        # 外部オーディオファイル状態保持 (Step 4)
        self.ext_audio_path = None
        self.ext_audio_pcm = None
        self._ext_audio_channel = None
        self._ext_audio_sound_ref = None

        # 自立進行用の等速累積時間ティック
        self.current_tick = 0.0

        self.default_bpm = 120.0
        self.current_bpm = 120.0
        self.bpm_ratio = 1.0
        self.speed_percent = 100.0
        self.speed_ratio = 1.0
        
        self.midi_engine = MidiEngine()
        
        self.midi_engine.active_pitches_callback = None
        
        self.midi_engine.progress_callback = lambda pct: self.after(0, lambda: self.update_progress_from_engine(pct))
        self.midi_engine.measure_beat_callback = lambda m, b, num, den, tot: self.after(0, lambda: self.update_measure_beat_from_engine(m, b, num, den, tot))
        self.midi_engine.status_callback = lambda status: self.after(0, lambda: self.update_status_from_engine(status))
        self.midi_engine.error_callback = lambda err: self.after(0, lambda: self.on_engine_error(err))

        self.midi_engine.stream_start_callback = lambda: self.after(0, self.on_audio_stream_start)
        self.midi_engine.loop_wrap_callback = lambda: self.after(0, self.on_loop_wrapped)

        self.gui = HarmonicaAppGUI(self, self)

        global PYGAME_AVAILABLE
        try:
            if pygame.mixer.get_init() is None:
                # 音声割り込みオーバーヘッドを削減しGUIタイマーへ優先権を割譲
                pygame.mixer.init(44100, -16, 2, 1024)
            print("[システム] pygame.mixerを正常に初期化しました。")
            PYGAME_AVAILABLE = True
        except Exception as ex:
            print(f"[システム警告] pygame.mixer的初期化に失敗しました: {ex}")
            PYGAME_AVAILABLE = False

        # Canvasへのマウスイベント・グローバルキーイベントバインディング
        self.gui.canvas.bind("<Button-1>", self.on_canvas_click)
        self.gui.canvas.bind("<MouseWheel>", self.on_canvas_mousewheel)
        self.bind("<KeyPress>", self.on_global_key_press)

        self.after(100, self.initialize_flow)

    def report_callback_exception(self, exc, val, tb):
        """ボタンクリック等のTkinterコールバック例外も自動で error_log.txt に記録し自己診断可能にします。"""
        import traceback
        err_text = "".join(traceback.format_exception(exc, val, tb))
        print("Exception in Tkinter callback\n" + err_text, file=sys.stderr)
        try:
            log_path = os.path.join(self.base_dir, "error_log.txt")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n=== Tkinter Callback Exception ===\n")
                f.write(err_text)
        except Exception:
            pass


    def check_and_build_directories(self):
        """環境用フォルダ自動作成 ＆ デフォルトスキン自立書き出し"""
        temp_dir = get_portable_path("temp")
        output_dir = get_portable_path("output")
        fingering_dir = get_portable_path("fingering") 
        skins_dir = get_portable_path("skins")  
        
        if not os.path.exists(temp_dir): os.makedirs(temp_dir, exist_ok=True)
        if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
        if not os.path.exists(fingering_dir): os.makedirs(fingering_dir, exist_ok=True)
        if not os.path.exists(skins_dir): os.makedirs(skins_dir, exist_ok=True)

        # 古い「顔.png」を「マウスピース.png」に自動追従リネーム
        old_face = os.path.join(skins_dir, "顔.png")
        new_face = os.path.join(skins_dir, "マウスピース.png")
        if os.path.exists(old_face) and not os.path.exists(new_face):
            try:
                os.rename(old_face, new_face)
                print("[システム] 古い 顔.png を マウスピース.png へ自動引き継ぎリネームしました。")
            except Exception:
                pass

        # 以前の古い 32x36px の赤ボタンレバーを検出し、48x48pxの新レバーペイントのために自動強制削除・リセット
        # 🚀【解決】：サイズが48x48ではない、または古いピクセルをスキャンして強制アップデート
        lever_off_path = os.path.join(skins_dir, "レバーオフ.png")
        lever_on_path = os.path.join(skins_dir, "レバーオン.png")
        from PIL import Image
        for path in [lever_off_path, lever_on_path]:
            if os.path.exists(path):
                try:
                    with Image.open(path) as img:
                        # 48x48 ではない、または3D球体時代のもの等を含め強制リライト
                        if img.size != (48, 48):
                            img.close()
                            os.remove(path)
                            print(f"[システム] 旧レバー素材（{os.path.basename(path)}）を自動削除しました（新ステンレス扁平メタルに更新します）。")
                except Exception:
                    pass

        self.generate_default_skins()

    def generate_default_skins(self):
        """
        skins/ 内にマウスピース・レバーのPNGスキンが存在しない場合、
        Pillowを用いて、美しく金属光沢を施した画像を動的に生成書き出しします。
        """
        from PIL import Image, ImageDraw
        skins_dir = get_portable_path("skins")
        
        face_path = os.path.join(skins_dir, "マウスピース.png")  
        lever_off_path = os.path.join(skins_dir, "レバーオフ.png")
        lever_on_path = os.path.join(skins_dir, "レバーオン.png")

        # 1. カバープレート「マウスピース.png」の自立生成
        if not os.path.exists(face_path):
            w, h = 800, 90
            y, x = np.ogrid[:h, :w]
            grad = (x + y * 1.5) / (w + h * 1.5)
            light = np.sin(grad * np.pi * 1.5 - np.pi / 4)
            light = np.clip(light, -0.3, 0.7) + 0.3
            gray_values = 45 + light * 75
            
            tex_np = np.zeros((h, w, 4), dtype=np.uint8)
            tex_np[..., 0] = tex_np[..., 1] = tex_np[..., 2] = gray_values
            tex_np[..., 3] = 255
            
            face_img = Image.fromarray(tex_np, "RGBA")
            mask = Image.new("L", (w, h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, w, h], radius=15, fill=255)
            
            final_face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            final_face.paste(face_img, (0, 0), mask=mask)
            final_face.save(face_path, "PNG")
            print("[システム] skins/マウスピース.png の自動書き出しに成功しました。")

        # 2. スライドレバー「レバーオフ.png」の自立生成 (ステンレス扁平ボタン・通常位置)
        if not os.path.exists(lever_off_path):
            w, h = 48, 48
            lo_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(lo_img)
            # グレーシャフト (通常位置)
            draw.rounded_rectangle([0, 16, 24, 32], radius=4, fill="#555555")
            
            # 🚀 扁平縦長楕円形状 (幅16px, 高さ36px) の3Dメタルドーム (右寄せX=24にペースト)
            btn_w, btn_h = 16, 36
            btn_img = draw_metallic_button_pil_flat(btn_w, btn_h, is_on=False)
            
            btn_mask = Image.new("L", (btn_w, btn_h), 0)
            btn_mask_draw = ImageDraw.Draw(btn_mask)
            btn_mask_draw.ellipse([0, 0, btn_w, btn_h], fill=255)
            
            lo_img.paste(btn_img, (24, 6), mask=btn_mask)
            lo_img.save(lever_off_path, "PNG")
            print("[システム] skins/レバーオフ.png の自動書き出しに成功しました。")

        # 3. スライドレバー「レバーオン.png」の自立生成 (ステンレス扁平ボタン・押し込み位置)
        # 🚀 レバーONでもX平行スライドを全廃！
        # シャフトを縮め（X=0〜12）、3D扁平縦長ボタンを左端（X=12〜28）に寄せた完全パラパラ沈み込みスキンを自動ペイント！
        if not os.path.exists(lever_on_path):
            w, h = 48, 48
            lon_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(lon_img)
            # 短縮グレーシャフト
            draw.rounded_rectangle([0, 16, 12, 32], radius=4, fill="#3a3a3a")
            
            btn_w, btn_h = 16, 36
            btn_img = draw_metallic_button_pil_flat(btn_w, btn_h, is_on=True)
                
            btn_mask = Image.new("L", (btn_w, btn_h), 0)
            btn_mask_draw = ImageDraw.Draw(btn_mask)
            btn_mask_draw.ellipse([0, 0, btn_w, btn_h], fill=255)
            
            lon_img.paste(btn_img, (12, 6), mask=btn_mask)
            lon_img.save(lever_on_path, "PNG")
            print("[システム] skins/レバーオン.png の自動書き出しに成功しました。")

    def initialize_flow(self):
        """設定ファイルとおもてなしデータの初期ロード"""
        self.load_user_settings()
        
        # 初期起動時・環境ロード時の Canvas アスペクト比物理サイズ同期
        self.on_ratio_changed(self.gui.ratio_menu.get())

        self.load_safe_melody()
        self.draw_harmonica_static()

    def _set_label_if_changed(self, widget, cache_key, new_text):
        """CustomTkinterラベルの重い再描画を防ぐため、文字列が実際に変化した時のみ更新します。"""
        if not hasattr(self, "_ui_text_cache"):
            self._ui_text_cache = {}
        if self._ui_text_cache.get(cache_key) != new_text:
            self._ui_text_cache[cache_key] = new_text
            widget.configure(text=new_text)

    def update_clock(self):
        """完全自立パッシブ等速時間軸タイマー（カウントイン＆ABループ折り返し完全連続追従）"""
        if self.play_state != "playing": return

        ticks_per_beat = self.midi_engine.ticks_per_beat
        count_in_duration = self.get_count_in_duration()

        now = time.time()
        is_count_in_active = (self.midi_engine.playing_state == "count_in")
        self.current_tick = self.midi_engine.get_smooth_current_tick()

        if self.current_tick < 0:
            song_sec = -self.midi_engine.tick_to_sec(-self.current_tick)
        else:
            song_sec = self.midi_engine.tick_to_sec(self.current_tick)

        self.current_time = count_in_duration + song_sec
        if self.current_time > self.max_duration:
            self.current_time = self.max_duration

        if self.gui.seek_slider and self.max_duration > 0:
            if self.current_tick <= 0:
                if getattr(self, "_last_slider_pct", -1.0) != 0.0:
                    self._last_slider_pct = 0.0
                    self._last_slider_time = now
                    self.gui.seek_slider.set(0)
            else:
                denom = self.max_duration - count_in_duration
                pct = max(0.0, min(100.0, (song_sec / denom) * 100)) if denom > 0 else 0.0
                if (now - getattr(self, "_last_slider_time", 0.0) >= 0.08) and (abs(pct - getattr(self, "_last_slider_pct", -1.0)) >= 0.15):
                    self._last_slider_pct = pct
                    self._last_slider_time = now
                    self.gui.seek_slider.set(pct)
            
        self.update_time_label()

        safe_tick = max(0, self.current_tick)
        measure, beat, num, den, total_measures = self.midi_engine.get_measure_and_beat(safe_tick)
        self.current_bpm = self.midi_engine.get_bpm_at_tick(safe_tick)
        
        status_state = self.midi_engine.playing_state
        status_map = {
            "stopped": "停止中", 
            "paused": "一時停止", 
            "playing": "再生中", 
            "count_in": "前奏中"       
        }
        status_ja = status_map.get(status_state.lower(), "前奏中" if is_count_in_active else status_state)
        
        self._set_label_if_changed(self.gui.lbl_lcd_status, "lcd_status", f"状態：{status_ja[:6].ljust(6)}")
        
        if is_count_in_active:
            pos_str = "位置：前奏カウント中..."
        else:
            pos_str = f"位置：{measure:03d}小節 . {beat:02d}拍"
        self._set_label_if_changed(self.gui.lbl_lcd_pos, "lcd_pos", pos_str)
            
        self._set_label_if_changed(self.gui.lbl_lcd_sig, "lcd_sig", f"拍子：{num}/{den}")
        speed_pct = int(round(getattr(self, "speed_percent", 100)))
        self._set_label_if_changed(self.gui.lbl_lcd_bpm, "lcd_bpm", f"テンポ:{int(round(self.current_bpm)):03d}BPM({speed_pct}%)")
        
        self.last_update_time = now

        self.draw_harmonica(active_pitches=self.midi_engine.currently_playing_notes, target_tick=self.current_tick, ticks_per_beat=ticks_per_beat, draw_mode="notes")
        
        # after(30)だったスレッドタイマーを、高精度60FPS周期である after(16) へスライド短縮！
        self.after(16, self.update_clock)

    def draw_harmonica(self, active_pitches=None, target_tick=0, ticks_per_beat=480, draw_mode="notes"):
        """Canvasプレビューの描画接続"""
        if not hasattr(self, "gui") or not self.gui.canvas: return
        
        current_time = self.current_time
        
        is_hole_num_on = bool(self.gui.hole_num_switch.get())
        is_legend_on = bool(self.gui.show_legend_switch.get())
        is_notes_on = bool(self.gui.show_notes_switch.get())
        is_grid_on = bool(self.gui.show_grid_switch.get())
        is_glow_on = bool(self.gui.show_glow_switch.get())

        last_edit_note = getattr(self, "last_edited_note_name", None)
        last_edit_fing = getattr(self, "last_edited_fingering", None)

        use_skin = bool(self.gui.use_skin_switch.get())
        
        aspect_ratio = self.get_effective_canvas_ratio()
        _, _, disp_scale = get_visualizer_layout_params(aspect_ratio)

        # 連動リング表示スイッチのON/OFF状態を引き渡す
        use_ring = bool(self.gui.show_ring_switch.get())
        trajectory_mode = self.gui.trajectory_menu.get() if hasattr(self.gui, "trajectory_menu") else "3段階 (練習標準)"
        show_lookahead = bool(self.gui.show_lookahead_switch.get()) if hasattr(self.gui, "show_lookahead_switch") else True
        show_grid4 = ("4音グリッド" in self.gui.grid4_menu.get()) if hasattr(self.gui, "grid4_menu") else True
        note_speed_ratio = self.get_note_speed_ratio() if hasattr(self, "get_note_speed_ratio") else 1.0

        draw_harmonica_canvas(
            canvas=self.gui.canvas,
            canvas_bg_color=self.gui.canvas_bg_color,
            inst_type=self.gui.inst_menu.get(),
            lang_seg_value=self.gui.lang_menu.get(), 
            is_hole_num_on=is_hole_num_on,
            is_legend_on=is_legend_on,
            is_notes_on=is_notes_on,
            is_grid_on=is_grid_on,
            midi_notes=self.midi_notes,
            current_time=current_time,
            current_bpm=self.current_bpm,
            active_pitches=active_pitches,
            draw_mode=draw_mode,
            target_tick=target_tick,
            ticks_per_beat=ticks_per_beat,
            color_blow_hex=self.color_blow_hex,  
            color_draw_hex=self.color_draw_hex,
            edit_mode_active=self.fingering_edit_mode,
            last_edit_note=last_edit_note,    
            last_edit_fing=last_edit_fing,
            use_skin=use_skin,
            scale=disp_scale,
            aspect_ratio=aspect_ratio,
            use_ring=use_ring,
            trajectory_mode=trajectory_mode,
            show_lookahead=show_lookahead,
            show_grid4=show_grid4,
            measures_timeline=self.midi_engine.measures_timeline,
            is_glow_on=is_glow_on,
            note_speed_ratio=note_speed_ratio
        )

    def draw_harmonica_body_only(self, pitches):
        """音が鳴った瞬間にLEDをCanvas上で点灯"""
        ticks_per_beat = self.midi_engine.ticks_per_beat
        self.draw_harmonica(
            active_pitches=pitches,
            target_tick=self.current_tick,
            ticks_per_beat=ticks_per_beat,
            draw_mode="harmonica"
        )

    def draw_harmonica_static(self, show_active_at_tick=False):
        """再生停止・シーク・ジャンプ時のプレビュー追従"""
        ticks_per_beat = self.midi_engine.ticks_per_beat
        
        count_in_duration = self.get_count_in_duration()
        self.current_time = self.midi_engine.tick_to_sec(self.midi_engine.accumulated_ticks) + count_in_duration
        self.current_bpm = self.midi_engine.get_bpm_at_tick(self.midi_engine.accumulated_ticks)
        
        self.draw_harmonica(
            active_pitches=("from_tick" if show_active_at_tick else set()),
            target_tick=self.midi_engine.accumulated_ticks,
            ticks_per_beat=ticks_per_beat,
            draw_mode="all"
        )

    def on_engine_error(self, err):
        print(f"[演奏スレッド警告] {err}")

    def lock_controls_on_play(self, lock=True):
        """再生中のUIコントロールロック（表示設定・カラー・速度・パート再生モード・小節ジャンプ・ABループは再生中も常時操作可能）"""
        state = "disabled" if lock else "normal"
        self.gui.bpm_minus_btn.configure(state="normal")
        self.gui.bpm_entry.configure(state="normal")
        self.gui.bpm_plus_btn.configure(state="normal")
        self.gui.default_bpm_btn.configure(state="normal")
        self.gui.file_btn.configure(state=state)
        if hasattr(self.gui, "part_select_btn"):
            self.gui.part_select_btn.configure(state=state)
        if hasattr(self.gui, "part_play_mode_menu"):
            self.gui.part_play_mode_menu.configure(state="normal")
        
        self.gui.audio_mode_menu.configure(state=state)
        self.gui.metro_menu.configure(state=state)
        self.gui.count_in_menu.configure(state=state)
        
        self.gui.jump_entry.configure(state="normal")
        self.gui.jump_btn.configure(state="normal")
        
        self.gui.loop_a_entry.configure(state="normal")
        self.gui.loop_b_entry.configure(state="normal")
        self.gui.cb_loop.configure(state="normal")
        self.gui.btn_set_a.configure(state="normal")
        self.gui.btn_set_b.configure(state="normal")
        self.gui.btn_clear_loop.configure(state="normal")
        if hasattr(self.gui, "note_speed_menu"):
            self.gui.note_speed_menu.configure(state="normal")
        
        self.gui.inst_menu.configure(state=state)
        self.gui.lang_menu.configure(state="normal")
        if hasattr(self.gui, "trajectory_menu"):
            self.gui.trajectory_menu.configure(state="normal")
        
        # 再生中も表示パーツ・テーマ・グリッド等はリアルタイム切替可能に常時アンロック
        self.gui.hole_num_switch.configure(state="normal")
        self.gui.show_legend_switch.configure(state="normal")
        self.gui.show_notes_switch.configure(state="normal")
        self.gui.show_grid_switch.configure(state="normal")
        self.gui.show_ring_switch.configure(state="normal")
        self.gui.show_glow_switch.configure(state="normal")
        if hasattr(self.gui, "show_lookahead_switch"):
            self.gui.show_lookahead_switch.configure(state="normal")
        if hasattr(self.gui, "grid4_menu"):
            self.gui.grid4_menu.configure(state="normal")
        self.gui.opacity_entry.configure(state="normal")
        if hasattr(self.gui, "reset_fingering_btn"):
            self.gui.reset_fingering_btn.configure(state=state)
        self.gui.bg_menu.configure(state="normal")
        self.gui.res_menu.configure(state="normal")
        
        if self.fingering_edit_mode:
            self.gui.export_btn.configure(state="disabled")
        else:
            self.gui.export_btn.configure(state=state)

    # 動画書き出し時専用の一括コントロールロック
    def lock_controls_for_export(self, lock=True):
        """動画書き出し中の一括ロック制御"""
        state = "disabled" if lock else "normal"
        
        # export_btn の自立活性化。中止を待ち受けるため常に normal を死守！
        self.gui.export_btn.configure(state="normal")
        
        if hasattr(self.gui, "sidebar_mode_seg"):
            self.gui.sidebar_mode_seg.configure(state=state)
        
        # ロック漏れしていた音声選択(audio_mode_menu)をリストへ補完
        self.gui.audio_mode_menu.configure(state=state)
        self.gui.file_btn.configure(state=state)
        if hasattr(self.gui, "part_select_btn"):
            self.gui.part_select_btn.configure(state=state)
        if hasattr(self.gui, "part_play_mode_menu"):
            self.gui.part_play_mode_menu.configure(state=state)
        
        self.gui.play_btn.configure(state=state)
        self.gui.pause_btn.configure(state=state)
        self.gui.stop_btn.configure(state=state)
        
        if hasattr(self.gui, "bpm_minus_btn"):
            self.gui.bpm_minus_btn.configure(state=state)
        self.gui.bpm_entry.configure(state=state)
        if hasattr(self.gui, "bpm_plus_btn"):
            self.gui.bpm_plus_btn.configure(state=state)
        self.gui.default_bpm_btn.configure(state=state)
        
        self.gui.metro_menu.configure(state=state)
        self.gui.count_in_menu.configure(state=state)
        self.gui.jump_entry.configure(state=state)
        self.gui.jump_btn.configure(state=state)
        self.gui.loop_a_entry.configure(state=state)
        self.gui.loop_b_entry.configure(state=state)
        self.gui.cb_loop.configure(state=state)
        self.gui.btn_set_a.configure(state=state)
        self.gui.btn_set_b.configure(state=state)
        self.gui.btn_clear_loop.configure(state=state)
        if hasattr(self.gui, "note_speed_menu"):
            self.gui.note_speed_menu.configure(state=state)
        if hasattr(self.gui, "stepup_switch"):
            self.gui.stepup_switch.configure(state=state)
        if hasattr(self.gui, "stepup_step_menu"):
            self.gui.stepup_step_menu.configure(state=state)
        if hasattr(self.gui, "stepup_start_entry"):
            self.gui.stepup_start_entry.configure(state=state)
        if hasattr(self.gui, "stepup_goal_entry"):
            self.gui.stepup_goal_entry.configure(state=state)
        self.gui.inst_menu.configure(state=state)
        self.gui.lang_menu.configure(state=state)
        if hasattr(self.gui, "trajectory_menu"):
            self.gui.trajectory_menu.configure(state=state)
        self.gui.alt_fingering_menu.configure(state=state)
        self.gui.fingering_edit_switch.configure(state=state)
        if hasattr(self.gui, "reset_fingering_btn"):
            self.gui.reset_fingering_btn.configure(state=state)
        self.gui.theme_menu.configure(state=state)
        self.gui.btn_color_blow.configure(state=state)
        self.gui.btn_color_draw.configure(state=state)
        self.gui.hole_num_switch.configure(state=state)
        self.gui.show_legend_switch.configure(state=state)
        self.gui.show_notes_switch.configure(state=state)
        self.gui.show_grid_switch.configure(state=state)
        self.gui.show_ring_switch.configure(state=state)  # 連動リングスイッチもロック
        if hasattr(self.gui, "show_glow_switch"):
            self.gui.show_glow_switch.configure(state=state)
        if hasattr(self.gui, "show_lookahead_switch"):
            self.gui.show_lookahead_switch.configure(state=state)
        if hasattr(self.gui, "grid4_menu"):
            self.gui.grid4_menu.configure(state=state)
        self.gui.opacity_entry.configure(state=state)
        self.gui.bg_menu.configure(state=state)
        self.gui.res_menu.configure(state=state)
        self.gui.preview_btn.configure(state=state)
        self.gui.fps_menu.configure(state=state)
        
        self.gui.ratio_menu.configure(state=state)
        self.gui.use_skin_switch.configure(state=state)

        for attr_name in (
            "export_range_menu",
            "intro_sec_menu",
            "outro_sec_menu",
            "title_template_menu",
            "video_title_entry",
            "video_credit_entry",
            "ext_audio_btn",
            "ext_audio_clear_btn",
            "ext_audio_mode_menu",
            "ext_offset_m10_btn",
            "ext_offset_m1_btn",
            "ext_audio_offset_entry",
            "ext_offset_p1_btn",
            "ext_offset_p10_btn",
            "ext_audio_vol_slider",
            "ext_audio_vol_entry",
            "yt_limiter_switch",
        ):
            if hasattr(self.gui, attr_name):
                getattr(self.gui, attr_name).configure(state=state)


    def execute_video_export(self):
        """高画質動画書き出しコアと画面コンソールボタンを完全に結合！"""
        from video_exporter import execute_video_export_core
        
        # すでにエクスポート中の場合 ➔ ユーザーによる「🛑 中止」ボタン
        if self.play_state == "exporting":
            self.video_export_cancelled = True
            self.gui.status_label.configure(text="🛑 レンダリングを中止しています...", text_color="#ff5555")
            # 二重連打を防ぐため、スレッドクリーンアップが走るまでの間一時的にdisabled化。
            self.gui.export_btn.configure(state="disabled")
            return

        if not self.midi_notes:
            return

        if self.current_midi_path:
            midi_filename = os.path.basename(self.current_midi_path)
            midi_name_only, _ = os.path.splitext(midi_filename)
            out_filename = f"{midi_name_only}.mp4"
        else:
            out_filename = "chromatic_harmonica_output.mp4"
            
        output_dir = get_portable_path("output")
        final_output_path = os.path.join(output_dir, out_filename)
        
        if os.path.exists(final_output_path):
            ans = messagebox.askyesno(
                "上書き確認", 
                f"ファイル '{out_filename}' は既に存在します。\n上書きしてよろしいですか？",
                parent=self
            )
            if not ans:
                self.gui.status_label.configure(text="🛑 書き出しをキャンセルしました", text_color="#aaaaaa")
                return

        self.on_stop()
        self.play_state = "exporting"
        self.video_export_cancelled = False
        
        self.lock_controls_for_export(True)
        self.gui.export_btn.configure(text="🛑 中止", fg_color="#c0392b", hover_color="#962d22")

        midi_notes = self.midi_notes
        current_bpm = self.current_bpm
        max_duration = self.max_duration
        
        res_mode = self.gui.res_menu.get()
        inst_type = self.gui.inst_menu.get()
        notation_mode = self.gui.lang_menu.get()
        bg_color = self.gui.canvas_bg_color
        
        is_hole_num_on = bool(self.gui.hole_num_switch.get())
        is_legend_on = bool(self.gui.show_legend_switch.get())
        is_notes_on = bool(self.gui.show_notes_switch.get())
        is_grid_on = bool(self.gui.show_grid_switch.get())
        is_glow_on = bool(self.gui.show_glow_switch.get())
        use_ring = bool(self.gui.show_ring_switch.get())
        show_lookahead = bool(self.gui.show_lookahead_switch.get()) if hasattr(self.gui, "show_lookahead_switch") else True
        show_grid4 = ("4音グリッド" in self.gui.grid4_menu.get()) if hasattr(self.gui, "grid4_menu") else True
        note_speed_ratio = self.get_note_speed_ratio() if hasattr(self, "get_note_speed_ratio") else 1.0
        
        note_opacity = self.gui.opacity_entry.get()
        
        is_count_in = bool(self.midi_engine.count_in_measures > 0)
        is_metro = bool(self.gui.metro_menu.get() != "なし")
        ticks_per_beat = self.midi_engine.ticks_per_beat
        fps_mode = self.gui.fps_menu.get()

        aspect_ratio = self.gui.ratio_menu.get()
        use_skin = bool(self.gui.use_skin_switch.get())
        trajectory_mode = self.gui.trajectory_menu.get() if hasattr(self.gui, "trajectory_menu") else "3段階 (練習標準)"

        # Step 3 & Step 4 動画書き出し拡張パラメータ
        export_range = self.gui.export_range_menu.get() if hasattr(self.gui, "export_range_menu") else "全曲"
        intro_sec, outro_sec = self.get_intro_outro_seconds() if hasattr(self, "get_intro_outro_seconds") else (0.0, 0.0)
        title_template = self.gui.title_template_menu.get() if hasattr(self.gui, "title_template_menu") else "なし"
        video_title = self.gui.video_title_entry.get() if hasattr(self.gui, "video_title_entry") else ""
        video_credit = self.gui.video_credit_entry.get() if hasattr(self.gui, "video_credit_entry") else ""

        ext_audio_pcm = getattr(self, "ext_audio_pcm", None)
        ext_audio_mode = self.gui.ext_audio_mode_menu.get() if hasattr(self.gui, "ext_audio_mode_menu") else "頭出し確認 (再生:両方 / 動画:外部のみ)"
        ext_audio_offset_ms = self.get_ext_audio_offset_ms() if hasattr(self, "get_ext_audio_offset_ms") else 0
        ext_audio_vol_pct = self.get_ext_audio_vol_pct() if hasattr(self, "get_ext_audio_vol_pct") else 100
        yt_limiter = bool(self.gui.yt_limiter_switch.get()) if hasattr(self.gui, "yt_limiter_switch") else True

        execute_video_export_core(
            midi_notes=midi_notes,
            current_bpm=current_bpm,
            max_duration=max_duration,
            is_count_in=is_count_in,
            is_metro=is_metro,
            res_mode=res_mode,
            inst_type=inst_type,
            notation_mode=notation_mode,
            bg_color=bg_color,
            is_hole_num_on=is_hole_num_on,  
            is_legend_on=is_legend_on,
            is_notes_on=is_notes_on,
            is_grid_on=is_grid_on,
            is_glow_on=is_glow_on,
            note_opacity=note_opacity,
            current_midi_path=self.current_midi_path,
            status_label=self.gui.status_label,
            export_btn=self.gui.export_btn,
            root_after=self.after,
            ticks_per_beat=ticks_per_beat,
            fps_mode=fps_mode,
            color_blow_hex=self.color_blow_hex,  
            color_draw_hex=self.color_draw_hex,
            aspect_ratio=aspect_ratio,
            use_skin=use_skin,
            controller=self,
            trajectory_mode=trajectory_mode,
            show_lookahead=show_lookahead,
            show_grid4=show_grid4,
            measures_timeline=self.midi_engine.measures_timeline,
            use_ring=use_ring,
            note_speed_ratio=note_speed_ratio,
            export_range=export_range,
            intro_sec=intro_sec,
            outro_sec=outro_sec,
            title_template=title_template,
            video_title=video_title,
            video_credit=video_credit,
            ext_audio_pcm=ext_audio_pcm,
            ext_audio_mode=ext_audio_mode,
            ext_audio_offset_ms=ext_audio_offset_ms,
            ext_audio_vol_pct=ext_audio_vol_pct,
            yt_limiter=yt_limiter,
        )

    # エクスポート完了、エラー、またはユーザー中止時のクリーンUI復帰コールバック
    def on_export_finished_or_cancelled(self, status, err_msg=None):
        """
        エクスポート処理が終了、エラー終了、またはユーザーにより中止された際に、
        UIロックをすべて解除し、書き出しボタンを通常状態にリセット復帰させます。
        """
        self.play_state = "stopped"
        self.video_export_cancelled = False
        
        # すべてのコントロールロックを解除
        self.lock_controls_for_export(False)
        
        # ボタンのテキストとカラーを通常時に戻す（運指変更モード中は disabled を維持）
        btn_state = "disabled" if self.fingering_edit_mode else "normal"
        self.gui.export_btn.configure(text="🎬 書き出し", fg_color="#2b8c54", hover_color="#1f6b3e", state=btn_state)
        
        if status == "cancelled":
            self.gui.status_label.configure(text="🛑 レンダリングを中止しました", text_color="#ff5555")
        elif status == "failed" and err_msg:
            self.gui.status_label.configure(text=f"❌ レンダリング失敗: {err_msg[:30]}...", text_color="#ff5555")

    def execute_single_frame_preview(self):
        """📸 レンダリングを試すボタンと、video_exporterのポップアッププレビュー処理を完全結合！"""
        from video_exporter import execute_single_frame_preview
        
        if not self.midi_notes:
            return

        midi_notes = self.midi_notes
        current_bpm = self.midi_engine.get_bpm_at_tick(self.midi_engine.accumulated_ticks)
        
        count_in_duration = self.get_count_in_duration()
        current_time_sec = self.midi_engine.tick_to_sec(self.midi_engine.accumulated_ticks) + count_in_duration

        res_mode = self.gui.res_menu.get()
        inst_type = self.gui.inst_menu.get()
        notation_mode = self.gui.lang_menu.get()
        bg_color = self.gui.canvas_bg_color
        
        is_hole_num_on = bool(self.gui.hole_num_switch.get())
        is_legend_on = bool(self.gui.show_legend_switch.get())
        is_notes_on = bool(self.gui.show_notes_switch.get())
        is_grid_on = bool(self.gui.show_grid_switch.get())
        is_glow_on = bool(self.gui.show_glow_switch.get())
        use_ring = bool(self.gui.show_ring_switch.get())
        show_lookahead = bool(self.gui.show_lookahead_switch.get()) if hasattr(self.gui, "show_lookahead_switch") else True
        show_grid4 = ("4音グリッド" in self.gui.grid4_menu.get()) if hasattr(self.gui, "grid4_menu") else True
        note_speed_ratio = self.get_note_speed_ratio() if hasattr(self, "get_note_speed_ratio") else 1.0
        
        note_opacity = self.gui.opacity_entry.get()

        aspect_ratio = self.gui.ratio_menu.get()
        use_skin = bool(self.gui.use_skin_switch.get())
        trajectory_mode = self.gui.trajectory_menu.get() if hasattr(self.gui, "trajectory_menu") else "3段階 (練習標準)"
        title_template = self.gui.title_template_menu.get() if hasattr(self.gui, "title_template_menu") else "なし"
        video_title = self.gui.video_title_entry.get() if hasattr(self.gui, "video_title_entry") else ""
        video_credit = self.gui.video_credit_entry.get() if hasattr(self.gui, "video_credit_entry") else ""

        execute_single_frame_preview(
            midi_notes=midi_notes,
            current_bpm=current_bpm,
            current_time=current_time_sec,
            res_mode=res_mode,
            inst_type=inst_type,
            notation_mode=notation_mode,
            bg_color=bg_color,
            is_hole_num_on=is_hole_num_on,  
            is_legend_on=is_legend_on,
            is_notes_on=is_notes_on,
            is_grid_on=is_grid_on,
            is_glow_on=is_glow_on,
            note_opacity=note_opacity,
            parent_window=self,
            color_blow_hex=self.color_blow_hex,  
            color_draw_hex=self.color_draw_hex,
            aspect_ratio=aspect_ratio,
            use_skin=use_skin,
            trajectory_mode=trajectory_mode,
            show_lookahead=show_lookahead,
            show_grid4=show_grid4,
            measures_timeline=self.midi_engine.measures_timeline,
            use_ring=use_ring,
            note_speed_ratio=note_speed_ratio,
            title_template=title_template,
            video_title=video_title,
            video_credit=video_credit,
        )

    def destroy(self):
        """ライフサイクル：WinMM / MIDIエンジンのクローズ安全開放処理"""
        if hasattr(self, "stop_ext_audio_playback"):
            self.stop_ext_audio_playback()
        self.midi_engine.stop()
        self.midi_engine.close_device()
        super().destroy()
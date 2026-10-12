# -*- coding: utf-8 -*-
# playback_controller.py (STEP 4-B: 演奏トランスポート ＆ 小節ジャンプ常時アンロック版)
# - 【常時アンロック】：小節ジャンプEntryおよびGoボタンを、再生中もコントロールロック対象から完全に除外しました。再生を維持したまま、滑らかにいつでも任意の小節へワープジャンプ可能です。
# - 🚀【音声選択ロック連動】：演奏ロック(lock_controls_on_play)のリストへ、漏れていた音声モード選択（audio_mode_menu）を同期追加。
# - 🚀【解決：1小節ループ解放】：A点 ≦ B点（同一小節でのループ指定）を完全に解放するため、Entry入力競合およびA点/B点ボタン選択競合の境界条件を ≦ ≧ に緩和。

import os
import time
import tkinter as tk
from tkinter import filedialog
import traceback
import numpy as np
import harmonica_map

class PlaybackController:
    # Mixinのため self は app_controller.HarmonicaAppIntegrator インスタンスを指します

    def get_count_in_duration(self):
        """現在の再生速度倍率・開始テンポ・拍子に基づき、カウントイン期間の秒数を正確に算出"""
        count_in_measures_val = int(self.gui.count_in_menu.get().split()[0])
        if count_in_measures_val > 0:
            time_sig_num = self.midi_engine.time_sig_num
            time_sig_den = self.midi_engine.time_sig_den
            total_beats = count_in_measures_val * time_sig_num
            start_bpm = max(1.0, self.midi_engine.get_bpm_at_tick(0))
            return total_beats * ((60.0 / start_bpm) * (4.0 / time_sig_den))
        return 0.0

    def extract_notes_from_midi(self):
        """
        現在選択されている主旋律パート（main_track_index）からビジュアル描画・練習用ノーツ(self.midi_notes)を抽出し、
        それ以外の非ドラム伴奏パートから伴奏用ノーツ(self.accompaniment_notes)を抽出します。
        """
        active_notes = {}
        parsed_main_notes = []
        parsed_accomp_notes = []
        main_idx = self.midi_engine.main_track_index

        for event in self.midi_engine.merged_messages:
            if event.is_metronome:
                continue
            msg = event.msg
            if msg.is_meta or not hasattr(msg, "channel"):
                continue

            abs_tick = event.abs_tick
            abs_sec = self.midi_engine.tick_to_sec(abs_tick, speed_ratio=1.0)
            key = (event.track_idx, msg.channel, getattr(msg, "note", -1))

            if msg.type == "note_on" and msg.velocity > 0:
                active_notes[key] = (abs_sec, abs_tick, msg.velocity)
            elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                if key in active_notes:
                    start_time, start_tick, velocity = active_notes.pop(key)
                    duration = max(0.01, abs_sec - start_time)
                    duration_ticks = max(1, abs_tick - start_tick)
                    note_obj = {
                        "note": msg.note,
                        "original_start_time": start_time,
                        "original_duration": duration,
                        "start_tick": start_tick,
                        "duration_ticks": duration_ticks,
                        "velocity": velocity,
                        "track_idx": event.track_idx,
                    }
                    if event.track_idx == main_idx:
                        parsed_main_notes.append(note_obj)
                    elif msg.channel != 9:
                        parsed_accomp_notes.append(note_obj)

        # 未終了ノーツの安全クローズ
        end_tick = self.midi_engine.total_ticks
        end_sec = self.midi_engine.tick_to_sec(end_tick, speed_ratio=1.0)
        for (t_idx, ch, note_num), (start_time, start_tick, velocity) in list(active_notes.items()):
            duration = max(0.05, end_sec - start_time)
            duration_ticks = max(1, end_tick - start_tick)
            note_obj = {
                "note": note_num,
                "original_start_time": start_time,
                "original_duration": duration,
                "start_tick": start_tick,
                "duration_ticks": duration_ticks,
                "velocity": velocity,
                "track_idx": t_idx,
            }
            if t_idx == main_idx:
                parsed_main_notes.append(note_obj)
            elif ch != 9:
                parsed_accomp_notes.append(note_obj)

        self.midi_notes = [n for n in parsed_main_notes if 24 <= n["note"] <= 98]
        self.midi_notes.sort(key=lambda x: x["start_tick"])

        self.accompaniment_notes = [n for n in parsed_accomp_notes if 12 <= n["note"] <= 108]
        self.accompaniment_notes.sort(key=lambda x: x["start_tick"])

        # ロード・パート切替完了後に、主旋律ノーツへ解決済み運指データをキャッシュ埋め込み
        self.rebind_all_notes_fingerings()

        max_main_end = max((n["original_start_time"] + n["original_duration"] for n in self.midi_notes), default=0.0)
        max_acc_end = max((n["original_start_time"] + n["original_duration"] for n in self.accompaniment_notes), default=0.0)
        self.original_max_duration = max(max_main_end, max_acc_end)

        if self.midi_notes:
            self.apply_bpm()

    def load_safe_melody(self):
        """ユーザー様ご提供の自作高品位MIDIデータ（16進数ハッシュ）から物理展開・自動ロード"""
        hex_data = "4d546864000000060001000101e04d54726b0000023f00ff031d31362d486f6c652043204368726f6d61746963204861726d6f6e69636100ff58040402180800ff5902000000ff510307a12000b0790000640000650000060c00647f00657f00c01600b00764000a40005b00005d0000ff21010000903c5000b002508267903c00013d5000b0025077903d00013e5000b002508267903e00013f5000b0025077903f0001405000b00250826790400001415000b002507790410001425000b00250826790420001435000b002507790430001445000b00250826790440001455000b002507790450001465000b00250826790460001475000b002507790470001485000b00250835f9048008361485000b00250826790480001495000b0025077904900014a5000b002508267904a00014b5000b0025077904b00014c5000b002508267904c00014d5000b0025077904d00014e5000b002508267904e00014f5000b0025077904f0001505000b00250826790500001515000b002507790510001525000b00250826790520001535000b002507790530001545000b00250835f9054008361545000b00250826790540001555000b002507790550001565000b00250826790560001575000b002507790570001585000b00250826790580001595000b0025077905900015a5000b002508267905a00015b5000b0025077905b00015c5000b002508267905c00015d5000b0025077905d00015e5000b002508267905e00015f5000b0025077905f0001605000b00250835f9060008361625000b002508b1f90620001305000b002507790300001ff2f00"
        
        self.current_midi_path = os.path.join(self.base_dir, "temp", "test_harmonica_input.mid")
        try:
            midi_bytes = bytes.fromhex(hex_data)
            with open(self.current_midi_path, "wb") as f:
                f.write(midi_bytes)
                
            self.midi_engine.load_file(self.current_midi_path)
            self.default_bpm = self.midi_engine.default_bpm
            self.speed_percent = 100.0
            self.speed_ratio = 1.0
            self.midi_engine.speed_ratio = 1.0
            self.current_bpm = self.default_bpm
            self.bpm_ratio = 1.0
            
            if self.gui.bpm_entry:
                self.gui.bpm_entry.delete(0, tk.END)
                self.gui.bpm_entry.insert(0, "100")
                
            total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 1
            self.gui.jump_label.configure(text=f" / {total_measures} 小節")

            # MIDI初期解決時に、B点Entryに総小節数を自動同期代入！
            self.gui.loop_b_entry.delete(0, tk.END)
            self.gui.loop_b_entry.insert(0, str(total_measures))
            self.midi_engine.set_loop_point_by_measure('B', total_measures)

            harmonica_map.load_song_fingering(self.current_midi_path)
            self.gui.alt_fingering_menu.set(harmonica_map.CURRENT_SONG_PRESET)
            harmonica_map.apply_fingering_preset(harmonica_map.CURRENT_SONG_PRESET)

            self.extract_notes_from_midi()
            
        except Exception as e:
            print(f"[警告] デモ曲MIDI物理展開・ロード失敗: {e}")
            traceback.print_exc()

    def update_time_label(self):
        """前奏マイナス時間軸カウント対応時間表記（秒が変わった瞬間のみ更新）"""
        count_in_duration = self.get_count_in_duration()
        display_sec = self.current_time - count_in_duration
        
        is_negative = (display_sec < 0)
        abs_time = abs(display_sec)
        
        cur_min = int(abs_time) // 60
        cur_sec = int(abs_time) % 60
        max_min = int(self.max_duration - count_in_duration) // 60
        max_sec = int(self.max_duration - count_in_duration) % 60
        
        sign = "-" if is_negative else ""
        new_text = f"{sign}{cur_min:02d}:{cur_sec:02d} / {max_min:02d}:{max_sec:02d}"
        self._set_label_if_changed(self.gui.seek_label, "seek_label", new_text)

    def _truncate_by_visual_width(self, text, max_width=24):
        """全角文字=2・半角文字=1として見た目幅を計算し、固定幅ボックスに収まるよう省略します。"""
        import unicodedata
        def char_w(c):
            return 2 if unicodedata.east_asian_width(c) in ("F", "W", "A") else 1
        total_w = sum(char_w(c) for c in text)
        if total_w <= max_width:
            return text
        head = []
        w = 0
        for c in text:
            cw = char_w(c)
            if w + cw > max_width - 7:
                break
            head.append(c)
            w += cw
        return "".join(head) + "..." + text[-4:]

    def on_open_file(self):
        """MIDIファイルのパース読み込み ＆ 固定幅トリミング表示"""
        self.on_stop()
        file_path = filedialog.askopenfilename(title="MIDIファイルを選択してください", filetypes=[("MIDI Files", "*.mid")])
        if not file_path: return

        filename = os.path.basename(file_path)
        display_name = self._truncate_by_visual_width(filename, max_width=24)
            
        self.gui.file_label.configure(text=display_name, text_color="#1f538d")
        self.current_midi_path = file_path
        
        try:
            self.midi_engine.load_file(file_path)
            self.default_bpm = self.midi_engine.default_bpm
            self.speed_percent = 100.0
            self.speed_ratio = 1.0
            self.midi_engine.speed_ratio = 1.0
            self.current_bpm = self.default_bpm
            self.bpm_ratio = 1.0
            
            if self.gui.bpm_entry:
                self.gui.bpm_entry.delete(0, tk.END)
                self.gui.bpm_entry.insert(0, "100")

            total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 1
            self.gui.loop_b_entry.delete(0, tk.END)
            self.gui.loop_b_entry.insert(0, str(total_measures))
            self.midi_engine.set_loop_point_by_measure('B', total_measures)

            self.gui.jump_label.configure(text=f" / {total_measures} 小節")

            harmonica_map.load_song_fingering(self.current_midi_path)
            self.gui.alt_fingering_menu.set(harmonica_map.CURRENT_SONG_PRESET)
            harmonica_map.apply_fingering_preset(harmonica_map.CURRENT_SONG_PRESET)

            self.extract_notes_from_midi()

            main_info = self.midi_engine.get_main_track_info()
            part_name = main_info["name"] if main_info else "Track 1"
            num_parts = len(self.midi_engine.tracks_info)

            if self.midi_notes:
                self.gui.status_label.configure(
                    text=f"MIDIロード成功！ (主旋律: {part_name} [全{num_parts}パート] / 基準: {int(self.default_bpm)} BPM)",
                    text_color="#2b8c54"
                )
            else:
                self.gui.status_label.configure(
                    text=f"警告: 選択パート({part_name})に有効な音符がありません。「🎼 パート選択」から別パートを選んでください。",
                    text_color="#ffcc00"
                )
        except Exception as e:
            self.gui.status_label.configure(text=f"MIDI解析失敗: {e}", text_color="#ff5555")
            traceback.print_exc()

    def on_part_play_mode_changed(self, value):
        """トップバーのパート再生モード（全パート再生 / 主旋律ソロ / 伴奏のみ(カラオケ)）切替ハンドラ"""
        self.midi_engine.part_play_mode = value
        if self.midi_engine.playing_state in ["playing", "count_in"]:
            self.midi_engine.all_notes_off()
            self.midi_engine.sync_midi_channel_states(self.midi_engine.current_msg_index)
        if hasattr(self, "gui") and hasattr(self.gui, "status_label"):
            self.gui.status_label.configure(text=f"🎼 パート再生モードを「{value}」に切り替えました", text_color="#00ffcc")

    def select_main_track(self, track_idx, dialog=None):
        """パート選択ウィンドウから主旋律パートを切り替えます。"""
        self.on_stop()
        self.midi_engine.set_main_track(track_idx)
        self.extract_notes_from_midi()
        main_info = self.midi_engine.get_main_track_info()
        part_name = main_info["name"] if main_info else f"Track {track_idx + 1}"
        if self.midi_notes:
            self.gui.status_label.configure(
                text=f"🎼 主旋律パートを「{part_name}」に設定しました ({len(self.midi_notes)}音)",
                text_color="#00ffcc"
            )
        else:
            self.gui.status_label.configure(
                text=f"⚠ パート「{part_name}」にはハーモニカ音域内の音符がありません",
                text_color="#ffcc00"
            )
        self.draw_harmonica_static()
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def on_toggle_force_harmonica(self, sw_var):
        """主旋律パートのハーモニカ音色強制スイッチ切替"""
        self.midi_engine.force_main_harmonica = bool(sw_var.get())
        self.midi_engine.sync_midi_channel_states(self.midi_engine.current_msg_index)

    def open_part_select_dialog(self):
        """マルチパートMIDIの主旋律パート選択ポップアップウィンドウを表示します。"""
        import customtkinter as ctk

        if hasattr(self, "_part_dialog") and self._part_dialog is not None and self._part_dialog.winfo_exists():
            self._part_dialog.focus()
            return

        dlg = ctk.CTkToplevel(self)
        self._part_dialog = dlg
        dlg.title("🎼 主旋律パート選択 (マルチパートMIDI)")
        dlg.geometry("680x440")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        header_frame = ctk.CTkFrame(dlg, fg_color="#1a1a1a", corner_radius=8)
        header_frame.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(
            header_frame,
            text="🎼 ハーモニカで演奏・表示する「主旋律パート」を選択してください",
            font=("Meiryo", 13, "bold"),
            text_color="#00ffcc",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            header_frame,
            text="※ 選択したパートのノーツと穴LEDが画面に表示され、伴奏パートはバックグラウンドで再生されます。",
            font=("Meiryo", 11),
            text_color="#bbbbbb",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 8))

        sw_var = tk.BooleanVar(value=self.midi_engine.force_main_harmonica)
        harm_sw = ctk.CTkSwitch(
            header_frame,
            text="主旋律パートのMIDI音色を常に「ハーモニカ (GM #23)」に固定する",
            variable=sw_var,
            font=("Meiryo", 11, "bold"),
            command=lambda: self.on_toggle_force_harmonica(sw_var)
        )
        harm_sw.pack(anchor="w", padx=12, pady=(2, 10))

        scroll_frame = ctk.CTkScrollableFrame(dlg, fg_color="#141414", corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        tracks = self.midi_engine.tracks_info
        current_main = self.midi_engine.main_track_index

        for i, info in enumerate(tracks):
            t_idx = info["track_idx"]
            is_selected = (t_idx == current_main)
            row_bg = "#1e3a2f" if is_selected else "#222222"

            row_card = ctk.CTkFrame(scroll_frame, fg_color=row_bg, corner_radius=6)
            row_card.pack(fill="x", padx=6, pady=4)

            left_box = ctk.CTkFrame(row_card, fg_color="transparent")
            left_box.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            badge = "★ 主旋律" if is_selected else f"パート #{i + 1}"
            title_text = f"[{badge}]  {info['name']}   (Ch.{info['channel'] + 1})"
            ctk.CTkLabel(
                left_box,
                text=title_text,
                font=("Meiryo", 12, "bold"),
                text_color="#00ffcc" if is_selected else "#ffffff",
                anchor="w"
            ).pack(fill="x")

            sub_text = f"元の音色: {info['instrument_name']}  |  総ノーツ数: {info['note_count']}音 (ハーモニカ音域内: {info['in_range_count']}音)"
            ctk.CTkLabel(
                left_box,
                text=sub_text,
                font=("Meiryo", 11),
                text_color="#aaaaaa",
                anchor="w"
            ).pack(fill="x", pady=(2, 0))

            btn_text = "✓ 選択中" if is_selected else "主旋律に設定"
            btn_fg = "#2b8c54" if is_selected else "#1f538d"
            btn_hover = "#1f6b3e" if is_selected else "#163c66"

            ctk.CTkButton(
                row_card,
                text=btn_text,
                width=115,
                height=32,
                font=("Meiryo", 11, "bold"),
                fg_color=btn_fg,
                hover_color=btn_hover,
                command=lambda idx=t_idx: self.select_main_track(idx, dialog=dlg)
            ).pack(side="right", padx=12, pady=8)

        close_btn = ctk.CTkButton(
            dlg, text="閉じる", width=120, font=("Meiryo", 11, "bold"),
            fg_color="#444444", hover_color="#666666", command=dlg.destroy
        )
        close_btn.pack(pady=(0, 12))

    def apply_bpm(self):
        """再生速度(%)倍率と曲中テンポ変化タイムラインの同期適用"""
        if not self.midi_notes and not getattr(self, "accompaniment_notes", []):
            return
        try:
            speed_pct = 100.0
            if self.gui.bpm_entry:
                raw_str = str(self.gui.bpm_entry.get()).replace("%", "").strip()
                try:
                    speed_pct = float(raw_str)
                except ValueError:
                    pass

            if speed_pct < 10 or speed_pct > 400:
                self.gui.status_label.configure(text="再生速度は 10% 〜 400% の間で設定してください", text_color="#ff5555")
                return

            self.speed_percent = speed_pct
            self.speed_ratio = speed_pct / 100.0
            self.midi_engine.speed_ratio = self.speed_ratio

            self.current_bpm = self.midi_engine.get_bpm_at_tick(self.midi_engine.accumulated_ticks, self.speed_ratio)
            self.bpm_ratio = 1.0 / self.speed_ratio
            self.midi_engine.bpm = round(self.current_bpm)

            count_in_duration = self.get_count_in_duration()

            count_in_measures_val = int(self.gui.count_in_menu.get().split()[0])
            self.midi_engine.count_in_measures = count_in_measures_val

            ticks_per_beat = self.midi_engine.ticks_per_beat
            ticks_per_sec = (self.current_bpm * ticks_per_beat) / 60.0

            for note in self.midi_notes:
                note["start_time"] = (note["original_start_time"] * self.bpm_ratio) + count_in_duration
                note["duration"] = note["original_duration"] * self.bpm_ratio
                if "start_tick" not in note:
                    note["start_tick"] = int((note["start_time"] - count_in_duration) * ticks_per_sec)
                if "duration_ticks" not in note:
                    note["duration_ticks"] = int(note["duration"] * ticks_per_sec)

            for acc_note in getattr(self, "accompaniment_notes", []):
                acc_note["start_time"] = (acc_note["original_start_time"] * self.bpm_ratio) + count_in_duration
                acc_note["duration"] = acc_note["original_duration"] * self.bpm_ratio

            for m in getattr(self.midi_engine, "measures_timeline", []):
                m["start_time"] = self.midi_engine.tick_to_sec(m["start_tick"]) + count_in_duration

            self.max_duration = (self.original_max_duration * self.bpm_ratio) + count_in_duration
            self.current_time = self.midi_engine.tick_to_sec(self.midi_engine.accumulated_ticks) + count_in_duration
            self.update_time_label()
            
            if hasattr(self, "gui") and hasattr(self.gui, "lbl_lcd_bpm"):
                self._set_label_if_changed(
                    self.gui.lbl_lcd_bpm, "lcd_bpm",
                    f"テンポ:{int(round(self.current_bpm)):03d}BPM({int(round(self.speed_percent))}%)"
                )

            if hasattr(self, "gui") and self.gui.canvas and self.play_state != "playing":
                self.draw_harmonica_static() 
            self.save_user_settings_txt()
        except Exception as ex:
            print(f"[警告] 再生速度適用中に例外が発生しました: {ex}")

    def step_speed_percent(self, delta):
        """-5% / +5% ボタンで再生速度をワンクリック増減します（再生中もリアルタイム反映）。"""
        if not self.midi_notes: return
        cur_pct = getattr(self, "speed_percent", 100.0)
        if self.gui.bpm_entry:
            raw_str = str(self.gui.bpm_entry.get()).replace("%", "").strip()
            try:
                cur_pct = float(raw_str)
            except ValueError:
                pass
        new_pct = max(10, min(400, int(round(cur_pct + delta))))
        if self.gui.bpm_entry:
            self.gui.bpm_entry.delete(0, tk.END)
            self.gui.bpm_entry.insert(0, str(new_pct))
        self.apply_bpm()

    def reset_bpm(self):
        if not self.midi_notes: return
        self.gui.bpm_entry.delete(0, tk.END)
        self.gui.bpm_entry.insert(0, "100")
        self.apply_bpm()

    def on_play(self):
        if not self.midi_notes: return
        was_stopped = (self.play_state == "stopped")

        # ステップアップ練習がONかつ停止状態からの新規再生時は、開始速度(%)へ自動セット＆A-Bループ連動ON
        if was_stopped and hasattr(self.gui, "stepup_switch") and self.gui.stepup_switch.get():
            if not self.gui.cb_loop.get():
                self.gui.cb_loop.select()
            start_pct, goal_pct, step_pct = self.get_stepup_params()
            self.gui.bpm_entry.delete(0, tk.END)
            self.gui.bpm_entry.insert(0, str(start_pct))
            self.gui.status_label.configure(
                text=f"📈 ステップアップ開始: {start_pct}% ➔ 目標 {goal_pct}% (+{step_pct}%/周)",
                text_color="#00ffcc"
            )

        self.midi_engine.loop_enabled = bool(self.gui.cb_loop.get())
        self.on_loop_entry_changed()
        self.apply_bpm()

        if self.play_state != "playing":
            self.play_state = "playing"
            self.lock_controls_on_play(True)
            
            self.gui.export_btn.configure(state="disabled")
            if hasattr(self.gui, "ext_audition_play_btn"):
                self.gui.ext_audition_play_btn.configure(
                    text="⏸ 一時停止", fg_color="#e67e22", hover_color="#d35400"
                )

            self._apply_effective_guide_audio_mode()
            self._refresh_ext_audio_config_cache()
            self.stop_ext_audio_playback()

            now = time.time()
            self.last_update_time = now
            self.midi_engine.play()
            self.update_clock()

    def _apply_effective_guide_audio_mode(self):
        """外部音源設定と通常音源設定を統合し、外部音源との重ね再生時は遅延ゼロの内蔵シンセへ自動ルーティングして動画出力との音ズレを解消します。"""
        edit_on = self.is_video_edit_enabled() if hasattr(self, "is_video_edit_enabled") else True
        has_ext = (getattr(self, "ext_audio_pcm", None) is not None and len(getattr(self, "ext_audio_pcm", [])) > 0)
        ext_mode = self.gui.ext_audio_mode_menu.get() if hasattr(self.gui, "ext_audio_mode_menu") else ""
        audio_mode = self.gui.audio_mode_menu.get()

        if edit_on and has_ext and "外部音源オフ" not in ext_mode:
            if "外部音源のみ" in ext_mode:
                self.midi_engine.device_muted = True
                self.midi_engine.internal_synth_enabled = False
                self.midi_engine.all_notes_off()
                return
            # 頭出し確認・両方ミックス時は、Windows GS音源の約50ms発音遅延を排除し動画出力と完全一致させるため内蔵シンセを使用
            if "消音" not in audio_mode or "頭出し確認" in ext_mode:
                self.midi_engine.device_muted = True
                self.midi_engine.internal_synth_enabled = True
                self.midi_engine.metronome_pattern = self.gui.metro_menu.get()
                self.midi_engine.all_notes_off()
                return

        if "MIDI再生" in audio_mode:
            self.midi_engine.device_muted = False
            self.midi_engine.internal_synth_enabled = False
            self.midi_engine.metronome_pattern = self.gui.metro_menu.get()
        elif "簡易再生" in audio_mode:
            self.midi_engine.device_muted = True
            self.midi_engine.internal_synth_enabled = True
            self.midi_engine.metronome_pattern = self.gui.metro_menu.get()
        else:
            self.midi_engine.device_muted = True
            self.midi_engine.internal_synth_enabled = False

    def on_pause(self):
        self.play_state = "paused"
        self.midi_engine.pause()
        self.stop_ext_audio_playback()
        try:
            import pygame
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.pause()
        except Exception:
            pass
        self.lock_controls_on_play(False)
        if hasattr(self.gui, "ext_audition_play_btn"):
            self.gui.ext_audition_play_btn.configure(
                text="▶ 頭出し試聴", fg_color="#2b8c54", hover_color="#1f6b3e"
            )
        if not self.fingering_edit_mode:
            self.gui.export_btn.configure(state="normal")

    def on_stop(self):
        self.play_state = "stopped"
        self.midi_engine.stop()
        self.stop_ext_audio_playback()
        try:
            import pygame
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass
        self.lock_controls_on_play(False)
        if hasattr(self.gui, "ext_audition_play_btn"):
            self.gui.ext_audition_play_btn.configure(
                text="▶ 頭出し試聴", fg_color="#2b8c54", hover_color="#1f6b3e"
            )
        if not self.fingering_edit_mode:
            self.gui.export_btn.configure(state="normal")
        self.draw_harmonica_static()

    def on_seek_drag(self, value):
        pct = float(value)
        self.midi_engine.seek(pct)
        
        self.current_tick = self.midi_engine.accumulated_ticks
        count_in_duration = self.get_count_in_duration()
        elapsed_sec = self.midi_engine.ticks_to_ms(self.current_tick) / 1000.0
        
        self.current_time = elapsed_sec + count_in_duration
        self.update_time_label()
        if self.play_state == "playing":
            self.sync_ext_audio_playback()
        self.draw_harmonica_static()

    def on_volume_change(self, value):
        self.midi_engine.volume_factor = float(value)
        try:
            import pygame
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.set_volume(float(value))
        except Exception:
            pass
        self.gui.volume_label.configure(text=f"音量 (簡易再生時のみ): {int(float(value) * 100)}%")

    def on_loop_toggle(self):
        self.midi_engine.loop_enabled = bool(self.gui.cb_loop.get())
        self.on_loop_entry_changed()
        if self.play_state == "stopped":
            self.midi_engine.reset_playback_state()
            self.draw_harmonica_static()

    def set_loop_a_at_current(self):
        if not self.midi_notes: return
        measure, _, _, _, _ = self.midi_engine.get_measure_and_beat(max(0, self.midi_engine.accumulated_ticks))
        total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 1
        
        try:
            val_b = int(self.gui.loop_b_entry.get())
        except ValueError:
            val_b = total_measures
            
        # 🚀【解決】：A点設定時、B点と同じ数値（A点＝B点による1小節無限ループ）を完全に許容するため
        # これまで val_a >= val_b としていた厳密な等号境界条件を、安全に val_a > val_b へと緩和！
        if measure > val_b:
            measure = 1
            self.gui.loop_b_entry.delete(0, tk.END)
            self.gui.loop_b_entry.insert(0, str(total_measures))
            self.midi_engine.set_loop_point_by_measure('B', total_measures)

        self.midi_engine.set_loop_point_by_measure('A', measure)
        self.gui.loop_a_entry.delete(0, tk.END)
        self.gui.loop_a_entry.insert(0, str(measure))

    def set_loop_b_at_current(self):
        if not self.midi_notes: return
        measure, _, _, _, _ = self.midi_engine.get_measure_and_beat(max(0, self.midi_engine.accumulated_ticks))
        total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 1
        
        try:
            val_a = int(self.gui.loop_a_entry.get())
        except ValueError:
            val_a = 1
            
        # 🚀【解決】：B点設定時も、A点と同じ数値（1小節無限ループ）を完全に許容するため、
        # 旧 measure <= val_a だった不当境界判定を、安全に measure < val_a へと緩和！
        if measure < val_a:
            measure = total_measures
            self.gui.loop_a_entry.delete(0, tk.END)
            self.gui.loop_a_entry.insert(0, "1")
            self.midi_engine.set_loop_point_by_measure('A', 1)

        self.midi_engine.set_loop_point_by_measure('B', measure)
        self.gui.loop_b_entry.delete(0, tk.END)
        self.gui.loop_b_entry.insert(0, str(measure))

    def reset_loop_points(self):
        """ループ点の全解除"""
        total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 12
        self.midi_engine.loop_a_index = None
        self.midi_engine.loop_b_index = None
        self.midi_engine.loop_b_target_tick = None 
        self.gui.loop_a_entry.delete(0, tk.END)
        self.gui.loop_a_entry.insert(0, "1")
        self.gui.loop_b_entry.delete(0, tk.END)
        self.gui.loop_b_entry.insert(0, str(total_measures))
        self.midi_engine.set_loop_point_by_measure('A', 1)
        self.midi_engine.set_loop_point_by_measure('B', total_measures)

    def on_metro_menu_changed(self, value):
        self.midi_engine.metronome_pattern = value

    def on_count_in_menu_changed(self, value):
        self.apply_bpm()

    def on_jump_measure(self):
        """再生中であっても滑らかに指定小節にジャンプする処理"""
        if not self.midi_notes: return
        try:
            val = int(self.gui.jump_entry.get())
            self.midi_engine.seek_to_measure(val)
            
            self.current_tick = self.midi_engine.accumulated_ticks
            count_in_duration = self.get_count_in_duration()
            elapsed_sec = self.midi_engine.ticks_to_ms(self.current_tick) / 1000.0
            
            self.current_time = elapsed_sec + count_in_duration
            self.update_time_label()
            if self.play_state == "playing":
                self.sync_ext_audio_playback()
            self.draw_harmonica_static()
        except ValueError:
            pass

    def on_loop_entry_changed(self):
        if not self.midi_notes: return
        total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 1
        
        try:
            val_a = int(self.gui.loop_a_entry.get())
            if val_a < 1 or val_a > total_measures:
                raise ValueError
        except ValueError:
            val_a = 1
            self.gui.loop_a_entry.delete(0, tk.END)
            self.gui.loop_a_entry.insert(0, "1")
            
        try:
            val_b = int(self.gui.loop_b_entry.get())
            if val_b < 1 or val_b > total_measures:
                raise ValueError
        except ValueError:
            val_b = total_measures
            self.gui.loop_b_entry.delete(0, tk.END)
            self.gui.loop_b_entry.insert(0, str(total_measures))

        # 🚀【解決】：手入力Entryの決定時でも、同一小節ループ指定を許容するため
        # val_a >= val_b だった不当境界判定を val_a > val_b へ安全に緩和。
        if val_a > val_b:
            val_a = 1
            val_b = total_measures
            self.gui.loop_a_entry.delete(0, tk.END)
            self.gui.loop_a_entry.insert(0, "1")
            self.gui.loop_b_entry.delete(0, tk.END)
            self.gui.loop_b_entry.insert(0, str(total_measures))

        self.midi_engine.set_loop_point_by_measure('A', val_a)
        self.midi_engine.set_loop_point_by_measure('B', val_b)
        if self.play_state == "stopped" and self.midi_engine.loop_enabled:
            self.midi_engine.reset_playback_state()
            self.draw_harmonica_static()

    def update_progress_from_engine(self, pct):
        if self.play_state == "playing":
            return
        if self.gui.seek_slider:
            self._last_slider_pct = pct
            self.gui.seek_slider.set(pct)
        self.current_time = (pct / 100.0) * self.max_duration
        self.update_time_label()

    def update_measure_beat_from_engine(self, measure, beat, num, den, total_measures):
        if self.play_state == "playing":
            return
        self._set_label_if_changed(self.gui.lbl_lcd_pos, "lcd_pos", f"位置：{measure:03d}小節 . {beat:02d}拍")
        self._set_label_if_changed(self.gui.lbl_lcd_sig, "lcd_sig", f"拍子：{num}/{den}")
        cur_bpm = int(round(self.midi_engine.get_bpm_at_tick(self.midi_engine.accumulated_ticks)))
        speed_pct = int(round(getattr(self, "speed_percent", 100)))
        self._set_label_if_changed(self.gui.lbl_lcd_bpm, "lcd_bpm", f"テンポ:{cur_bpm:03d}BPM({speed_pct}%)")
        
        self.gui.jump_entry.delete(0, tk.END)
        self.gui.jump_entry.insert(0, str(measure))

    def update_status_from_engine(self, status):
        status_map = {
            "stopped": "停止中", 
            "paused": "一時停止", 
            "playing": "再生中", 
            "count_in": "前奏カウント"
        }
        status_ja = status_map.get(status.lower(), status)
        
        self._set_label_if_changed(self.gui.lbl_lcd_status, "lcd_status", f"状態：{status_ja[:6].ljust(6)}")
        
        if status == "Finished":
            self.on_stop()

    def on_audio_stream_start(self):
        if self.play_state == "playing" and self.last_update_time == 0.0:
            self.last_update_time = time.time()
            self.current_tick = self.midi_engine.accumulated_ticks
            self.update_clock()
            print("[System] 再生ストリームの物理発音を検知 ➔ UIタイマーループ点火")

    def on_loop_wrapped(self):
        """A-BループでB点末尾からA点頭へ折り返した瞬間のコールバック（ステップアップ練習の速度更新）"""
        if hasattr(self, "gui") and hasattr(self.gui, "stepup_switch") and self.gui.stepup_switch.get():
            start_pct, goal_pct, step_pct = self.get_stepup_params()
            cur_pct = int(round(getattr(self, "speed_percent", start_pct)))
            if cur_pct < goal_pct:
                new_pct = min(goal_pct, cur_pct + step_pct)
                self.gui.bpm_entry.delete(0, tk.END)
                self.gui.bpm_entry.insert(0, str(new_pct))
                self.apply_bpm()
                if new_pct >= goal_pct:
                    self.gui.status_label.configure(
                        text=f"🎯 目標速度 {goal_pct}% に到達しました！（この速度を維持してループ）",
                        text_color="#00ffcc"
                    )
                else:
                    self.gui.status_label.configure(
                        text=f"📈 ステップアップ: {cur_pct}% ➔ {new_pct}% (目標 {goal_pct}%)",
                        text_color="#ffcc00"
                    )
            else:
                self.gui.status_label.configure(
                    text=f"🎯 目標速度 {goal_pct}% でループ練習中",
                    text_color="#00ffcc"
                )

    def on_main_playback_start(self):
        """カウントイン終了または本編再生開始の瞬間にワーカースレッドから直結呼び出しされ、1音目と外部音源を誤差0.0msで同時点火します。"""
        if self.play_state == "playing":
            self.sync_ext_audio_playback(from_worker=True, anchor_tick=self.midi_engine.accumulated_ticks)

    # ==============================================================================
    # 外部音源（伴奏・実演録音）の読み込み・リアルタイム頭出し同期・音量制御
    # ==============================================================================
    def _refresh_ext_audio_config_cache(self):
        """ワーカースレッドからTkinterウィジェットに触れずに外部音源設定を参照できるようキャッシュを更新します。"""
        self._ext_cfg_edit_on = self.is_video_edit_enabled() if hasattr(self, "is_video_edit_enabled") else True
        self._ext_cfg_mode = self.gui.ext_audio_mode_menu.get() if hasattr(self.gui, "ext_audio_mode_menu") else ""
        self._ext_cfg_offset_ms = self.get_ext_audio_offset_ms()
        self._ext_cfg_vol_pct = self.get_ext_audio_vol_pct()
        self._ext_cfg_yt_lim = bool(self.gui.yt_limiter_switch.get()) if hasattr(self.gui, "yt_limiter_switch") else True

    def get_ext_audio_offset_ms(self):
        """外部音源の開始オフセット(ms)を整数として返します（正値＝外部音源を遅らせる、負値＝外部音源の頭を削って早める）。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "ext_audio_offset_entry"):
            return 0
        raw = str(self.gui.ext_audio_offset_entry.get()).replace("ms", "").strip()
        try:
            return max(-60000, min(60000, int(round(float(raw)))))
        except ValueError:
            return 0

    def get_ext_audio_vol_pct(self):
        """外部音源の音量(%)を 0.0〜200.0 の範囲で返します。"""
        if not hasattr(self, "gui") or not hasattr(self.gui, "ext_audio_vol_entry"):
            return 100.0
        raw = str(self.gui.ext_audio_vol_entry.get()).replace("%", "").strip()
        try:
            return max(0.0, min(200.0, float(raw)))
        except ValueError:
            return 100.0

    def on_select_ext_audio(self):
        """外部音源ファイル（WAV/MP3/M4A等）を選択し、44.1kHzステレオPCMとしてメモリにロードします。"""
        from audio_engine import load_external_audio_pcm
        self.on_stop()
        file_path = filedialog.askopenfilename(
            title="外部音源ファイル（伴奏・演奏録音）を選択してください",
            filetypes=[("Audio/Video Files", "*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.mp4"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        self.gui.status_label.configure(text="🎵 外部音源を読み込み中...", text_color="#ffcc00")
        self.update_idletasks()
        try:
            pcm = load_external_audio_pcm(file_path, sample_rate=44100)
            self.ext_audio_path = file_path
            self.ext_audio_pcm = pcm
            fname = os.path.basename(file_path)
            disp = self._truncate_by_visual_width(fname, max_width=20)
            if hasattr(self.gui, "ext_audio_label"):
                self.gui.ext_audio_label.configure(text=disp, text_color="#00ffcc")
            dur_sec = len(pcm) / 44100.0
            self.gui.status_label.configure(
                text=f"🎵 外部音源ロード完了: {disp} ({dur_sec:.1f}秒) — 再生中に [ / ] キーで頭出し調整可能",
                text_color="#2b8c54"
            )
        except Exception as e:
            self.ext_audio_path = None
            self.ext_audio_pcm = None
            self.gui.status_label.configure(text=f"❌ 外部音源の読み込み失敗: {e}", text_color="#ff5555")

    def on_clear_ext_audio(self):
        """読み込んだ外部音源を解除します。"""
        self.stop_ext_audio_playback()
        self.ext_audio_path = None
        self.ext_audio_pcm = None
        if hasattr(self.gui, "ext_audio_label"):
            self.gui.ext_audio_label.configure(text="未選択 (内蔵シンセ合成)", text_color="#888888")
        if self.play_state == "playing":
            self._apply_effective_guide_audio_mode()
        self.gui.status_label.configure(text="外部音源を解除しました（内蔵シンセ合成モード）", text_color="#aaaaaa")

    def stop_ext_audio_playback(self):
        """再生中の外部音源チャンネルを即座に停止します。"""
        ch = getattr(self, "_ext_audio_channel", None)
        if ch is not None:
            try:
                ch.stop()
            except Exception:
                pass
        self._ext_audio_channel = None
        self._ext_audio_sound_ref = None

    def sync_ext_audio_playback(self, from_worker=False, anchor_tick=None):
        """現在の再生ティック位置・ミリ秒オフセット・音量%に合わせて外部音源をサンプル精度で同期再生し、発音直後にマスタークロックを再ロックします。"""
        if not from_worker:
            self._refresh_ext_audio_config_cache()

        self.stop_ext_audio_playback()
        if self.play_state != "playing":
            return
        # カウントイン中は外部音源を鳴らさず、本編突入の瞬間（on_main_playback_start）に誤差0msで点火する
        if self.midi_engine.playing_state != "playing":
            return
        if not getattr(self, "_ext_cfg_edit_on", True):
            return
        pcm = getattr(self, "ext_audio_pcm", None)
        if pcm is None or len(pcm) == 0:
            return
        ext_mode = getattr(self, "_ext_cfg_mode", "")
        if "外部音源オフ" in ext_mode:
            return

        try:
            import pygame
            if pygame.mixer.get_init() is None:
                return
        except Exception:
            return

        cur_tick = float(self.midi_engine.accumulated_ticks if anchor_tick is not None else self.midi_engine.get_smooth_current_tick())
        song_sec = self.midi_engine.tick_to_sec(max(0.0, cur_tick))

        offset_sec = float(getattr(self, "_ext_cfg_offset_ms", 0)) / 1000.0
        ext_pos_sec = song_sec - offset_sec
        sample_rate = 44100
        start_sample = int(round(ext_pos_sec * sample_rate))

        if start_sample >= len(pcm):
            return

        if start_sample >= 0:
            play_pcm = pcm[start_sample:]
        else:
            pad_samples = min(-start_sample, sample_rate * 20)
            pad = np.zeros((pad_samples, 2), dtype=np.int16)
            play_pcm = np.vstack((pad, pcm))

        vol_pct = float(getattr(self, "_ext_cfg_vol_pct", 100.0))
        yt_lim = bool(getattr(self, "_ext_cfg_yt_lim", True))

        if vol_pct > 100.0:
            gain = vol_pct / 100.0
            scaled = play_pcm.astype(np.float32) * gain
            max_amp = 29200.0 if yt_lim else 32767.0
            play_pcm = np.clip(scaled, -max_amp, max_amp).astype(np.int16)
            hw_vol = 1.0
            self._ext_audio_boosted = True
        else:
            play_pcm = np.ascontiguousarray(play_pcm, dtype=np.int16)
            hw_vol = max(0.0, min(1.0, vol_pct / 100.0))
            self._ext_audio_boosted = False

        try:
            snd = pygame.mixer.Sound(buffer=play_pcm)
            ch = snd.play()
            # 🚀【解決】：バッファ切り出し・Sound生成に要した数十msのラグを完全に打ち消すため、
            # 外部音源が物理発音を開始したこの瞬間にマスタークロックの時刻アンカーを再ロック！
            self.midi_engine.resync_master_clock(anchor_tick=cur_tick)
            if ch is not None:
                ch.set_volume(hw_vol)
            self._ext_audio_sound_ref = snd
            self._ext_audio_channel = ch
        except Exception as e:
            print(f"[警告] 外部音源の再生開始失敗: {e}")

    def on_ext_audition_play_pause(self):
        """🎞️ 動画編集タブの手元『▶ 頭出し試聴 / ⏸ 一時停止』ボタンハンドラ"""
        if self.play_state == "playing":
            self.on_pause()
            return
        if hasattr(self.gui, "video_edit_enabled_switch") and not self.gui.video_edit_enabled_switch.get():
            self.gui.video_edit_enabled_switch.select()
            if hasattr(self, "update_export_edit_summary_label"):
                self.update_export_edit_summary_label()
            self.save_user_settings_txt()
        self.on_play()

    def on_ext_audition_restart(self):
        """🎞️ 動画編集タブの手元『⏮ 頭から再生』ボタンハンドラ（曲頭またはループA点から即座に再生し、1音目の頭出しを確認）"""
        if not self.midi_notes:
            return
        if hasattr(self.gui, "video_edit_enabled_switch") and not self.gui.video_edit_enabled_switch.get():
            self.gui.video_edit_enabled_switch.select()
            if hasattr(self, "update_export_edit_summary_label"):
                self.update_export_edit_summary_label()
            self.save_user_settings_txt()
        self.on_stop()
        if hasattr(self.gui, "cb_loop") and self.gui.cb_loop.get():
            try:
                val_a = max(1, int(self.gui.loop_a_entry.get()))
            except ValueError:
                val_a = 1
            self.midi_engine.seek_to_measure(val_a)
        else:
            self.midi_engine.seek(0.0)
        self.on_play()

    def on_ext_audio_mode_changed(self, value=None):
        """外部音源モード変更時にガイド音のミュート状態と外部音源再生を即時同期します。"""
        if self.play_state == "playing":
            self._apply_effective_guide_audio_mode()
            self.sync_ext_audio_playback()
        self.save_user_settings_txt()

    def step_ext_audio_offset(self, delta_ms):
        """外部音源の開始オフセットを ±delta_ms だけ増減し、再生中なら即座に再同期します。"""
        cur_ms = self.get_ext_audio_offset_ms()
        new_ms = max(-60000, min(60000, cur_ms + int(delta_ms)))
        if hasattr(self.gui, "ext_audio_offset_entry"):
            self.gui.ext_audio_offset_entry.delete(0, tk.END)
            self.gui.ext_audio_offset_entry.insert(0, str(new_ms))
        self.on_ext_audio_offset_changed()

    def on_ext_audio_offset_changed(self):
        """外部音源オフセットEntry確定時の正規化・即時再同期・保存"""
        ms = self.get_ext_audio_offset_ms()
        if hasattr(self.gui, "ext_audio_offset_entry"):
            self.gui.ext_audio_offset_entry.delete(0, tk.END)
            self.gui.ext_audio_offset_entry.insert(0, str(ms))
        if self.play_state == "playing":
            self.sync_ext_audio_playback()
        sign = "+" if ms > 0 else ""
        self.gui.status_label.configure(
            text=f"⏱️ 外部音源 頭出しオフセット: {sign}{ms} ms",
            text_color="#00ffcc"
        )
        self.save_user_settings_txt()

    def on_ext_audio_vol_slider(self, value):
        """外部音源音量スライダー操作時のリアルタイム反映"""
        v_int = int(round(float(value)))
        if hasattr(self.gui, "ext_audio_vol_entry"):
            self.gui.ext_audio_vol_entry.delete(0, tk.END)
            self.gui.ext_audio_vol_entry.insert(0, str(v_int))
        self._apply_ext_audio_live_volume(v_int)
        self.save_user_settings_txt()

    def on_ext_audio_vol_entry_changed(self):
        """外部音源音量Entry手入力確定時の反映"""
        v_int = int(round(self.get_ext_audio_vol_pct()))
        if hasattr(self.gui, "ext_audio_vol_entry"):
            self.gui.ext_audio_vol_entry.delete(0, tk.END)
            self.gui.ext_audio_vol_entry.insert(0, str(v_int))
        if hasattr(self.gui, "ext_audio_vol_slider"):
            self.gui.ext_audio_vol_slider.set(v_int)
        self._apply_ext_audio_live_volume(v_int)
        self.save_user_settings_txt()

    def _apply_ext_audio_live_volume(self, vol_pct):
        if self.play_state != "playing":
            return
        ch = getattr(self, "_ext_audio_channel", None)
        if ch is not None and vol_pct <= 100 and not getattr(self, "_ext_audio_boosted", False):
            try:
                ch.set_volume(max(0.0, min(1.0, vol_pct / 100.0)))
                return
            except Exception:
                pass
        self.sync_ext_audio_playback()

    def on_canvas_mousewheel(self, event):
        """停止中・一時停止中にCanvas上でマウスホイールを回すと、1拍単位（Shiftで1/4拍、Ctrlで1小節単位）で前後スクラブ確認"""
        if self.play_state not in ("stopped", "paused") or not self.midi_notes:
            return
        delta = getattr(event, "delta", 0)
        if not delta:
            return
        notches = int(delta / 120) if abs(delta) >= 120 else (1 if delta > 0 else -1)
        # ホイール手前回転(notches < 0)で時間を前へ進め、奥回転(notches > 0)で巻き戻す
        steps = -notches
        tpb = max(1, self.midi_engine.ticks_per_beat)
        state_flags = getattr(event, "state", 0)
        if state_flags & 0x0001:  # Shift押下: 1/4拍単位の微細コマ送り
            step_ticks = max(1, tpb // 4)
        elif state_flags & 0x0004:  # Ctrl押下: 1小節単位
            step_ticks = tpb * max(1, self.midi_engine.time_sig_num)
        else:  # 通常: 1拍単位
            step_ticks = tpb

        target_tick = max(0, min(self.midi_engine.total_ticks, int(self.midi_engine.accumulated_ticks + steps * step_ticks)))
        self.midi_engine.seek_to_tick(target_tick, exact_tick=True)

        self.current_tick = self.midi_engine.accumulated_ticks
        count_in_duration = self.get_count_in_duration()
        elapsed_sec = self.midi_engine.ticks_to_ms(self.current_tick) / 1000.0
        self.current_time = elapsed_sec + count_in_duration
        self.update_time_label()
        self.draw_harmonica_static(show_active_at_tick=True)

    def on_global_key_press(self, event):
        """ハンズフリー練習＆外部音源ミリ秒頭出し用キーボードショートカット（入力欄フォーカス時・動画書き出し中は無効）"""
        if self.play_state == "exporting":
            return
        focus_w = self.focus_get()
        if focus_w is not None and (isinstance(focus_w, tk.Entry) or "entry" in str(focus_w).lower()):
            if event.keysym == "Escape" and hasattr(self, "gui") and self.gui.canvas:
                self.gui.canvas.focus_set()
            return

        ks = event.keysym
        state_flags = getattr(event, "state", 0)
        is_shift = bool(state_flags & 0x0001)
        is_ctrl = bool(state_flags & 0x0004)

        if ks == "space":
            if self.play_state == "playing":
                self.on_pause()
            else:
                self.on_play()
        elif ks in ("BackSpace", "Escape", "Return"):
            self.on_stop()
        elif ks in ("bracketleft", "comma", "less", "braceleft"):
            step = -1 if is_shift else (-100 if is_ctrl else -10)
            self.step_ext_audio_offset(step)
        elif ks in ("bracketright", "period", "greater", "braceright"):
            step = 1 if is_shift else (100 if is_ctrl else 10)
            self.step_ext_audio_offset(step)
        elif ks in ("Left", "Right"):
            if not self.midi_notes:
                return
            cur_m, _, _, _, total_m = self.midi_engine.get_measure_and_beat(max(0, self.midi_engine.accumulated_ticks))
            target_m = max(1, min(total_m, cur_m + (-1 if ks == "Left" else 1)))
            self.gui.jump_entry.delete(0, tk.END)
            self.gui.jump_entry.insert(0, str(target_m))
            self.on_jump_measure()
            if self.play_state in ("stopped", "paused"):
                self.draw_harmonica_static(show_active_at_tick=True)
        elif ks == "Up":
            self.step_speed_percent(5)
        elif ks == "Down":
            self.step_speed_percent(-5)
        elif ks in ("a", "A"):
            self.set_loop_a_at_current()
        elif ks in ("b", "B"):
            self.set_loop_b_at_current()
        elif ks in ("l", "L"):
            if self.gui.cb_loop.get():
                self.gui.cb_loop.deselect()
            else:
                self.gui.cb_loop.select()
            self.on_loop_toggle()


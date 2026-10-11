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
from audio_engine import synthesize_midi_to_wav
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

            # 自作高品位MIDIメッセージから、正確な再生用 absolute ティックをパース構築
            ticks_per_beat = self.midi_engine.ticks_per_beat
            current_tempo = int(60000000 / self.default_bpm)

            absolute_time_seconds = 0.0
            absolute_ticks = 0
            active_notes = {}
            parsed_notes = []

            for event in self.midi_engine.merged_messages:
                msg = event.msg
                if msg.is_meta and msg.type == "set_tempo":
                    current_tempo = msg.tempo

                seconds_per_tick = (current_tempo / 1000000.0) / ticks_per_beat
                delta_seconds = event.time * seconds_per_tick
                absolute_time_seconds += delta_seconds
                absolute_ticks += event.time

                if event.is_metronome:
                    continue  

                if msg.type == "note_on" and msg.velocity > 0:
                    active_notes[msg.note] = (absolute_time_seconds, absolute_ticks, msg.velocity)
                elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                    if msg.note in active_notes:
                        start_time, start_tick, velocity = active_notes.pop(msg.note)
                        duration = absolute_time_seconds - start_time
                        duration_ticks = absolute_ticks - start_tick
                        parsed_notes.append({
                            "note": msg.note, 
                            "original_start_time": start_time, 
                            "original_duration": duration,
                            "start_tick": start_tick,            
                            "duration_ticks": duration_ticks,    
                            "velocity": velocity,
                        })

            self.midi_notes = [n for n in parsed_notes if 24 <= n["note"] <= 98]
            self.midi_notes.sort(key=lambda x: x["start_tick"])
            
            # ロード完了後に、全ノーツへ解決済み運指データをキャッシュ埋め込み！
            self.rebind_all_notes_fingerings()

            if self.midi_notes:
                last_note = self.midi_notes[-1]
                self.original_max_duration = last_note["original_start_time"] + last_note["original_duration"]
                self.apply_bpm()
            
        except Exception as e:
            print(f"[警告] デモ曲MIDI物理展開・ロード失敗: {e}")
            traceback.print_exc()

    def update_time_label(self):
        """前奏マイナス時間軸カウント対応時間表記"""
        count_in_duration = self.get_count_in_duration()
        display_sec = self.current_time - count_in_duration
        
        is_negative = (display_sec < 0)
        abs_time = abs(display_sec)
        
        cur_min = int(abs_time) // 60
        cur_sec = int(abs_time) % 60
        max_min = int(self.max_duration - count_in_duration) // 60
        max_sec = int(self.max_duration - count_in_duration) % 60
        
        sign = "-" if is_negative else ""
        self.gui.seek_label.configure(text=f"{sign}{cur_min:02d}:{cur_sec:02d} / {max_min:02d}:{max_sec:02d}")

    def on_open_file(self):
        """MIDIファイルのパース読み込み ＆ 30文字トリミング表示"""
        self.on_stop()
        file_path = filedialog.askopenfilename(title="MIDIファイルを選択してください", filetypes=[("MIDI Files", "*.mid")])
        if not file_path: return

        filename = os.path.basename(file_path)
        
        if len(filename) > 30:
            display_name = filename[:20] + "..." + filename[-6:]
        else:
            display_name = filename
            
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

            total_measures = len(self.midi_engine.measures_timeline) if self.midi_engine.measures_timeline else 1
            self.gui.jump_label.configure(text=f" / {total_measures} 小節")

            harmonica_map.load_song_fingering(self.current_midi_path)
            self.gui.alt_fingering_menu.set(harmonica_map.CURRENT_SONG_PRESET)
            harmonica_map.apply_fingering_preset(harmonica_map.CURRENT_SONG_PRESET)

            ticks_per_beat = self.midi_engine.ticks_per_beat
            current_tempo = int(60000000 / self.default_bpm)

            absolute_time_seconds = 0.0
            absolute_ticks = 0
            active_notes = {}
            parsed_notes = []

            for event in self.midi_engine.merged_messages:
                msg = event.msg
                if msg.is_meta and msg.type == "set_tempo":
                    current_tempo = msg.tempo

                seconds_per_tick = (current_tempo / 1000000.0) / ticks_per_beat
                delta_seconds = event.time * seconds_per_tick
                absolute_time_seconds += delta_seconds
                absolute_ticks += event.time

                if event.is_metronome:
                    continue  

                if msg.type == "note_on" and msg.velocity > 0:
                    active_notes[msg.note] = (absolute_time_seconds, absolute_ticks, msg.velocity)
                elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                    if msg.note in active_notes:
                        start_time, start_tick, velocity = active_notes.pop(msg.note)
                        duration = absolute_time_seconds - start_time
                        duration_ticks = absolute_ticks - start_tick
                        parsed_notes.append({
                            "note": msg.note, 
                            "original_start_time": start_time, 
                            "original_duration": duration,
                            "start_tick": start_tick,            
                            "duration_ticks": duration_ticks,    
                            "velocity": velocity,
                        })

            self.midi_notes = [n for n in parsed_notes if 24 <= n["note"] <= 98]
            self.midi_notes.sort(key=lambda x: x["start_tick"])
            
            # ロード完了後に、全ノーツへ解決済み運指データをキャッシュ埋め込み！
            self.rebind_all_notes_fingerings()

            if self.midi_notes:
                last_note = self.midi_notes[-1]
                self.original_max_duration = last_note["original_start_time"] + last_note["original_duration"]
                self.apply_bpm()
                self.gui.status_label.configure(text=f"MIDIロード成功！ (基準テンポ: {int(self.default_bpm)} BPM / 再生速度: 100%)", text_color="#2b8c54")
            else:
                self.gui.status_label.configure(text="エラー: 有効な半音階の音符が見つかりません。", text_color="#ff5555")
        except Exception as e:
            self.gui.status_label.configure(text=f"MIDI解析失敗: {e}", text_color="#ff5555")
            traceback.print_exc()

    def apply_bpm(self):
        """再生速度(%)倍率と曲中テンポ変化タイムラインの同期適用"""
        if not self.midi_notes: return
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

            self.max_duration = (self.original_max_duration * self.bpm_ratio) + count_in_duration
            self.current_time = self.midi_engine.tick_to_sec(self.midi_engine.accumulated_ticks) + count_in_duration
            if self.play_state == "playing":
                self.play_start_time = time.time() - self.current_time
            self.update_time_label()
            
            if hasattr(self, "gui") and hasattr(self.gui, "lbl_lcd_bpm"):
                self.gui.lbl_lcd_bpm.configure(
                    text=f"テンポ:{int(round(self.current_bpm)):03d}BPM({int(round(self.speed_percent))}%)")

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

    def lock_controls_on_play(self, lock=True):
        """再生中のUIコントロールロック（再生速度%・小節ジャンプ・ABループは再生中も常時操作可能）"""
        state = "disabled" if lock else "normal"
        self.gui.bpm_minus_btn.configure(state="normal")
        self.gui.bpm_entry.configure(state="normal")
        self.gui.bpm_plus_btn.configure(state="normal")
        self.gui.default_bpm_btn.configure(state="normal")
        self.gui.file_btn.configure(state=state)
        
        # 音声選択メニュー(audio_mode_menu)のロックを追加補完
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
        
        self.gui.inst_menu.configure(state=state)
        self.gui.lang_menu.configure(state=state)
        
        self.gui.hole_num_switch.configure(state=state)
        self.gui.show_legend_switch.configure(state=state)
        self.gui.show_notes_switch.configure(state=state)
        self.gui.show_grid_switch.configure(state=state)
        self.gui.show_ring_switch.configure(state=state)
        self.gui.show_glow_switch.configure(state=state)
        self.gui.opacity_entry.configure(state=state)
        if hasattr(self.gui, "reset_fingering_btn"):
            self.gui.reset_fingering_btn.configure(state=state)
        self.gui.bg_menu.configure(state=state)
        self.gui.res_menu.configure(state=state)
        
        if self.fingering_edit_mode:
            self.gui.export_btn.configure(state="disabled")
        else:
            self.gui.export_btn.configure(state=state)

    def on_play(self):
        if not self.midi_notes: return
        self.apply_bpm()

        if self.play_state != "playing":
            self.play_state = "playing"
            self.lock_controls_on_play(True)
            
            self.gui.export_btn.configure(state="disabled")

            audio_mode = self.gui.audio_mode_menu.get()
            
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

            ticks_per_beat = self.midi_engine.ticks_per_beat
            count_in_duration = self.get_count_in_duration()
            
            now = time.time()
            if self.midi_engine.accumulated_ticks <= 0 and count_in_duration > 0:
                self.play_start_time = now
            else:
                elapsed_sec = self.midi_engine.ticks_to_ms(self.midi_engine.accumulated_ticks) / 1000.0
                self.play_start_time = now - (elapsed_sec + count_in_duration)

            self.last_update_time = now
            self.update_clock()
            self.midi_engine.play()

    def on_pause(self):
        self.play_state = "paused"
        self.midi_engine.pause()
        try:
            import pygame
            if pygame.mixer.get_init() is None:
                pygame.mixer.music.pause()
        except Exception:
            pass
        self.lock_controls_on_play(False)
        if not self.fingering_edit_mode:
            self.gui.export_btn.configure(state="normal")

    def on_stop(self):
        self.play_state = "stopped"
        self.midi_engine.stop()
        try:
            import pygame
            if pygame.mixer.get_init() is None:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass
        self.lock_controls_on_play(False)
        if not self.fingering_edit_mode:
            self.gui.export_btn.configure(state="normal")
        self.draw_harmonica_static()

    def on_seek_drag(self, value):
        pct = float(value)
        self.midi_engine.seek(pct)
        
        self.current_tick = self.midi_engine.accumulated_ticks
        count_in_duration = self.get_count_in_duration()
        
        now = time.time()
        elapsed_sec = self.midi_engine.ticks_to_ms(self.current_tick) / 1000.0
        self.play_start_time = now - (elapsed_sec + count_in_duration)
        
        self.current_time = elapsed_sec + count_in_duration
        self.update_time_label()
        self.draw_harmonica_static()

    def on_volume_change(self, value):
        self.midi_engine.volume_factor = float(value)
        try:
            import pygame
            if pygame.mixer.get_init() is None:
                pygame.mixer.music.set_volume(float(value))
        except Exception:
            pass
        self.gui.volume_label.configure(text=f"音量 (簡易再生時のみ): {int(float(value) * 100)}%")

    def on_loop_toggle(self):
        self.midi_engine.loop_enabled = self.gui.cb_loop.get()

    def set_loop_a_at_current(self):
        if not self.midi_notes: return
        measure, _, _, _, _ = self.midi_engine.get_measure_and_beat(self.midi_engine.accumulated_ticks)
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
        measure, _, _, _, _ = self.midi_engine.get_measure_and_beat(self.midi_engine.accumulated_ticks)
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
            
            now = time.time()
            elapsed_sec = self.midi_engine.ticks_to_ms(self.current_tick) / 1000.0
            self.play_start_time = now - (elapsed_sec + count_in_duration)
            
            self.current_time = elapsed_sec + count_in_duration
            self.update_time_label()
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

    def update_progress_from_engine(self, pct):
        if self.play_state == "playing":
            return
        if self.gui.seek_slider:
            self.gui.seek_slider.set(pct)
        self.current_time = (pct / 100.0) * self.max_duration
        self.update_time_label()

    def update_measure_beat_from_engine(self, measure, beat, num, den, total_measures):
        if self.play_state == "playing":
            return
        self.gui.lbl_lcd_pos.configure(text=f"位置：{measure:03d}小節 . {beat:02d}拍")
        self.gui.lbl_lcd_sig.configure(text=f"拍子：{num}/{den}")
        cur_bpm = int(round(self.midi_engine.get_bpm_at_tick(self.midi_engine.accumulated_ticks)))
        speed_pct = int(round(getattr(self, "speed_percent", 100)))
        self.gui.lbl_lcd_bpm.configure(text=f"テンポ:{cur_bpm:03d}BPM({speed_pct}%)")
        
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
        
        self.gui.lbl_lcd_status.configure(text=f"状態：{status_ja[:6].ljust(6)}")
        
        if status == "Finished":
            self.on_stop()

    def on_audio_stream_start(self):
        if self.play_state == "playing" and self.last_update_time == 0.0:
            self.last_update_time = time.time()
            self.current_tick = self.midi_engine.accumulated_ticks
            self.update_clock()
            print("[System] 再生ストリームの物理発音を検知 ➔ UIタイマーループ点火")
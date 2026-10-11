# -*- coding: utf-8 -*-
# midi_engine.py (STEP 4-B: 絶対ティックシーケンサー ＆ B小節末尾完全演奏ループ対応版)
# - 【小節末尾ループ】：A点は小節の頭（start_tick）、B点は指定小節の完全な終わり（end_tick）を終了閾値として解決。B点に指定した小節が最後まで完全に演奏されたのちに折り返す、美しいループバックを実現しました。
# - 🚀【音声バッファ最適化】：pygame-ce内蔵シンセの初期化バッファサイズを 512 から 1024 へと拡大し、高FPS動作時におけるCPU発音割り込み処理負荷を半減させ、GUIタイマーの安定に寄与。

import os
import sys
import time
import threading
import ctypes
from ctypes import wintypes

try:
    import mido
    import pygame
    import numpy as np
except ImportError as e:
    print(f"[エラー] 必要な外部ライブラリが見つかりません: {e}")
    sys.exit(1)

HMIDIOUT = ctypes.c_void_p
PHMIDIOUT = ctypes.POINTER(HMIDIOUT)

if os.name == 'nt':
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 2) 
    except Exception:
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
    try:
        winmm = ctypes.windll.winmm
        winmm.midiOutOpen.argtypes = [PHMIDIOUT, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
        winmm.midiOutOpen.restype = wintypes.UINT
        winmm.midiOutClose.argtypes = [HMIDIOUT]
        winmm.midiOutClose.restype = wintypes.UINT
        winmm.midiOutShortMsg.argtypes = [HMIDIOUT, wintypes.DWORD]
        winmm.midiOutShortMsg.restype = wintypes.UINT
        winmm.midiOutGetNumDevs.argtypes = []
        winmm.midiOutGetNumDevs.restype = wintypes.UINT
    except Exception as e:
        print(f"[警告] WinMM.dllのバインドに失敗しました: {e}")
        winmm = None
else:
    winmm = None


class PlayableEvent:
    def __init__(self, mido_msg, is_metronome=False, beat_in_measure=0, abs_tick=0):
        self.msg = mido_msg
        self.is_metronome = is_metronome
        self.beat_in_measure = beat_in_measure
        self.abs_tick = abs_tick
        self.time = 0
        self.time_sig_num = 4
        self.time_sig_den = 4


class MidiEngine:
    def __init__(self):
        self.h_midi_out = HMIDIOUT(0)
        self.device_opened = False
        self.open_device()
        
        self.mido_file = None
        self.merged_messages = []
        self.ticks_per_beat = 480
        
        self.playing_state = 'stopped'
        self.current_msg_index = 0
        self.accumulated_ticks = 0
        self.total_ticks = 0
        
        self.play_thread = None
        
        # 演奏属性
        self.default_bpm = 120.0
        self.bpm = 120
        self.speed_ratio = 1.0
        self.tempo_timeline = [{"tick": 0, "tempo": 500000, "bpm": 120.0, "base_sec": 0.0}]
        self.time_sig_num = 4
        self.time_sig_den = 4
        self.count_in_measures = 1
        
        self.metronome_pattern = "標準（頭拍強調）"
        self.device_muted = False
        
        self.loop_enabled = False
        self.loop_a_index = None
        self.loop_b_index = None
        
        self.loop_b_target_tick = None 
        
        self.measures_timeline = []
        self.currently_playing_notes = set()
        
        # コールバック
        self.status_callback = None
        self.progress_callback = None
        self.measure_beat_callback = None
        self.active_pitches_callback = None
        self.error_callback = None
        self.stream_start_callback = None

        # 内蔵軽量ポータブルシンセ
        self.synth_voices = {}          
        self.active_channels = {}       
        self.volume_factor = 0.8        
        self.internal_synth_enabled = False  
        
        self.metro_sound_strong = None  
        self.metro_sound_weak = None    
        self.synth_initialized = False
        self.init_internal_synth()

    def open_device(self):
        if winmm and not self.device_opened:
            res = winmm.midiOutOpen(ctypes.byref(self.h_midi_out), 0, 0, 0, 0)
            if res != 0:
                res = winmm.midiOutOpen(ctypes.byref(self.h_midi_out), 0xFFFFFFFF, 0, 0, 0)
            if res == 0:
                self.device_opened = True

    def close_device(self):
        if self.device_opened:
            self.all_notes_off()
            winmm.midiOutClose(self.h_midi_out)
            self.device_opened = False

    def init_internal_synth(self):
        try:
            if pygame.mixer.get_init() is None:
                # 🚀【解決】：音声割り込み負荷低減のためバッファサイズを 512 から 1024 へ最適化拡大！
                pygame.mixer.init(44100, -16, 2, 1024)
            
            pygame.mixer.set_num_channels(16)
            sample_rate = 44100
            
            self.metro_sound_strong = self._generate_click_wave(1200.0, sample_rate, 0.05)
            self.metro_sound_weak = self._generate_click_wave(800.0, sample_rate, 0.05)
            
            for note in range(24, 99):
                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                self.synth_voices[note] = self._generate_triangle_wave(freq, sample_rate, 0.6)
                
            self.synth_initialized = True
            print("[MidiEngine] 内蔵ポータブルPCMシンセサイザーの起動に成功しました。")
        except Exception as ex:
            print(f"[警告] 内蔵シンセサイザーの初期化に失敗しました: {ex}")
            self.synth_initialized = False

    def _generate_click_wave(self, freq, sample_rate, duration):
        t = np.arange(0, duration, 1.0 / sample_rate)
        envelope = np.exp(-35.0 * t / duration) 
        wave = np.sin(2.0 * np.pi * freq * t) * envelope
        pcm_data = (wave * 32767).astype(np.int16)
        return pygame.mixer.Sound(buffer=pcm_data)

    def _generate_triangle_wave(self, freq, sample_rate, duration):
        t = np.arange(0, duration, 1.0 / sample_rate)
        wave = 2.0 * np.abs(2.0 * (t * freq - np.floor(t * freq + 0.5))) - 1.0
        
        fade_len = int(sample_rate * 0.01)
        fade_in = np.linspace(0.0, 1.0, fade_len)
        fade_out = np.linspace(1.0, 0.0, fade_len)
        wave[:fade_len] *= fade_in
        wave[-fade_len:] *= fade_out
        
        pcm_data = (wave * 32767).astype(np.int16)
        return pygame.mixer.Sound(buffer=pcm_data)

    def synth_note_on(self, note, velocity):
        if not self.synth_initialized or note not in self.synth_voices:
            return
        try:
            self.synth_note_off(note)
            
            sound = self.synth_voices[note]
            channel = sound.play(loops=-1)
            if channel:
                vol = (velocity / 127.0) * self.volume_factor * 0.4
                channel.set_volume(vol)
                self.active_channels[note] = channel
        except Exception:
            pass

    def synth_note_off(self, note):
        if not self.synth_initialized or note not in self.active_channels:
            return
        try:
            channel = self.active_channels.pop(note, None)
            if channel and channel.get_busy():
                channel.fadeout(50) 
        except Exception:
            pass

    def all_notes_off(self):
        if self.device_opened and winmm:
            for ch in range(16):
                msg = (0xB0 | ch) | (123 << 8) | (0 << 16)
                winmm.midiOutShortMsg(self.h_midi_out, msg)
                
        if self.synth_initialized:
            for note, channel in list(self.active_channels.items()):
                try:
                    if channel and channel.get_busy():
                        channel.fadeout(50)
                except Exception:
                    pass
            self.active_channels.clear()
            
        self.currently_playing_notes.clear()

    # ==============================================================================
    # リアルタイム再生・進行管理ロジック
    # ==============================================================================
    def load_file(self, filepath):
        self.stop()
        self.mido_file = mido.MidiFile(filepath)
        self.ticks_per_beat = self.mido_file.ticks_per_beat
        
        raw_merged = list(mido.merge_tracks(self.mido_file.tracks))
        self.total_ticks = sum(msg.time for msg in raw_merged)
        
        self.compute_tempo_timeline(raw_merged)
        self.default_bpm = round(self.tempo_timeline[0]["bpm"]) if self.tempo_timeline else 120
        self.bpm = round(self.default_bpm * self.speed_ratio)
        
        self.compute_measure_timeline()
        
        if self.measures_timeline:
            self.time_sig_num = self.measures_timeline[0]['num']
            self.time_sig_den = self.measures_timeline[0]['den']
        else:
            self.time_sig_num = 4
            self.time_sig_den = 4
            
        self.generate_merged_messages_with_metronome(raw_merged)
        
        self.loop_a_index = None
        self.loop_b_index = None
        self.loop_b_target_tick = None 
        self.reset_playback_state()
        self.sync_midi_channel_states(0)

    def compute_tempo_timeline(self, raw_merged):
        """曲中のすべての set_tempo メタイベントを走査し、ティックと100%基準秒数のテンポタイムラインを構築します。"""
        tempo_changes = [(0, 500000)]
        current_tick = 0
        for msg in raw_merged:
            current_tick += msg.time
            if msg.is_meta and msg.type == 'set_tempo':
                tempo_changes.append((current_tick, msg.tempo))

        tempo_changes.sort(key=lambda x: x[0])
        filtered_tempos = []
        for change in tempo_changes:
            if not filtered_tempos or filtered_tempos[-1][0] != change[0]:
                filtered_tempos.append(change)
            else:
                filtered_tempos[-1] = change

        self.tempo_timeline = []
        cum_sec = 0.0
        for i, (t_tick, tempo_us) in enumerate(filtered_tempos):
            bpm_val = 60000000.0 / max(1, tempo_us)
            if i > 0:
                prev_seg = self.tempo_timeline[-1]
                dt = max(0, t_tick - prev_seg["tick"])
                cum_sec += dt * (60.0 / (prev_seg["bpm"] * self.ticks_per_beat))
            self.tempo_timeline.append({
                "tick": t_tick,
                "tempo": tempo_us,
                "bpm": bpm_val,
                "base_sec": cum_sec
            })

    def get_base_bpm_at_tick(self, tick):
        """指定ティック時点での原曲BPM（100%速度時）を返します。"""
        if not self.tempo_timeline:
            return float(self.default_bpm)
        t = max(0.0, float(tick))
        active_bpm = self.tempo_timeline[0]["bpm"]
        for seg in self.tempo_timeline:
            if seg["tick"] <= t:
                active_bpm = seg["bpm"]
            else:
                break
        return active_bpm

    def get_bpm_at_tick(self, tick, speed_ratio=None):
        """指定ティック時点での実効BPM（原曲BPM × 再生速度倍率）を返します。"""
        sr = self.speed_ratio if speed_ratio is None else speed_ratio
        return self.get_base_bpm_at_tick(tick) * max(0.05, sr)

    def tick_to_sec(self, tick, speed_ratio=None):
        """指定ティックを、曲中テンポ変化と再生速度倍率を考慮した実経過秒数（カウントイン除く）へ変換します。"""
        sr = max(0.05, self.speed_ratio if speed_ratio is None else speed_ratio)
        if not self.tempo_timeline:
            base_sec = float(tick) * (60.0 / (max(1.0, self.default_bpm) * self.ticks_per_beat))
            return base_sec / sr

        if tick <= 0:
            first_bpm = max(1.0, self.tempo_timeline[0]["bpm"])
            base_sec = float(tick) * (60.0 / (first_bpm * self.ticks_per_beat))
            return base_sec / sr

        active_seg = self.tempo_timeline[0]
        for seg in self.tempo_timeline:
            if seg["tick"] <= tick:
                active_seg = seg
            else:
                break

        dt = float(tick) - active_seg["tick"]
        base_sec = active_seg["base_sec"] + dt * (60.0 / (max(1.0, active_seg["bpm"]) * self.ticks_per_beat))
        return base_sec / sr

    def sec_to_tick(self, sec, speed_ratio=None):
        """実経過秒数（カウントイン除く）を、曲中テンポ変化と再生速度倍率を考慮したティックへ変換します。"""
        sr = max(0.05, self.speed_ratio if speed_ratio is None else speed_ratio)
        target_base_sec = float(sec) * sr
        if not self.tempo_timeline:
            return target_base_sec * (max(1.0, self.default_bpm) * self.ticks_per_beat / 60.0)

        if target_base_sec <= 0:
            first_bpm = max(1.0, self.tempo_timeline[0]["bpm"])
            return target_base_sec * (first_bpm * self.ticks_per_beat / 60.0)

        active_seg = self.tempo_timeline[0]
        for seg in self.tempo_timeline:
            if seg["base_sec"] <= target_base_sec:
                active_seg = seg
            else:
                break

        delta_base_sec = target_base_sec - active_seg["base_sec"]
        return active_seg["tick"] + delta_base_sec * (max(1.0, active_seg["bpm"]) * self.ticks_per_beat / 60.0)

    def compute_measure_timeline(self):
        sig_changes = [(0, 4, 4)]
        
        for track in self.mido_file.tracks:
            current_tick = 0
            for msg in track:
                current_tick += msg.time
                if msg.type == 'time_signature':
                    sig_changes.append((current_tick, msg.numerator, msg.denominator))
                    
        sig_changes.sort(key=lambda x: x[0])
        filtered_changes = []
        for change in sig_changes:
            if not filtered_changes or filtered_changes[-1][0] != change[0]:
                filtered_changes.append(change)
            else:
                filtered_changes[-1] = change
                
        self.measures_timeline = []
        tick = 0
        sig_idx = 0
        measure_num = 1
        
        while tick < self.total_ticks:
            while (sig_idx + 1 < len(filtered_changes) and 
                   filtered_changes[sig_idx + 1][0] <= tick):
                sig_idx += 1
                
            num = filtered_changes[sig_idx][1]
            def_den = filtered_changes[sig_idx][2]
            
            measure_len_ticks = int(self.ticks_per_beat * num * (4 / def_den))
            
            self.measures_timeline.append({
                'measure_num': measure_num,
                'start_tick': tick,
                'end_tick': tick + measure_len_ticks,
                'num': num,
                'den': def_den
            })
            
            tick += measure_len_ticks
            measure_num += 1

    def get_measure_and_beat(self, tick):
        if tick < 0:
            return 1, 1, self.time_sig_num, self.time_sig_den, len(self.measures_timeline) if self.measures_timeline else 1
            
        if not self.measures_timeline:
            return 1, 1, 4, 4, 1
            
        for m in self.measures_timeline:
            if m['start_tick'] <= tick < m['end_tick']:
                elapsed = tick - m['start_tick']
                beat_len = int(self.ticks_per_beat * (4 / m['den']))
                beat = int(elapsed // beat_len) + 1
                beat = min(beat, m['num'])
                return m['measure_num'], beat, m['num'], m['den'], len(self.measures_timeline)
                
        m = self.measures_timeline[-1]
        return m['measure_num'], m['num'], m['num'], m['den'], len(self.measures_timeline)

    def generate_merged_messages_with_metronome(self, raw_merged):
        absolute_events = []
        current_tick = 0
        for msg in raw_merged:
            current_tick += msg.time
            absolute_events.append((current_tick, PlayableEvent(msg, is_metronome=False, abs_tick=current_tick)))
            
        metronome_events = []
        for m in self.measures_timeline:
            num = m['num']
            den = m['den']
            beat_len = int(self.ticks_per_beat * (4 / den))
            
            for b in range(num):
                beat_tick = m['start_tick'] + b * beat_len
                if beat_tick > self.total_ticks:
                    break
                note = 76 if b == 0 else 77
                velocity = 110 if b == 0 else 80
                
                m_msg = mido.Message('note_on', channel=9, note=note, velocity=velocity, time=0)
                event = PlayableEvent(m_msg, is_metronome=True, beat_in_measure=b, abs_tick=beat_tick)
                event.time_sig_num = num
                event.time_sig_den = den
                
                metronome_events.append((beat_tick, event))
                
        combined = absolute_events + metronome_events
        combined.sort(key=lambda x: x[0])
        
        self.merged_messages = []
        prev_tick = 0
        for abs_tick, event in combined:
            delta = abs_tick - prev_tick
            event.time = delta
            self.merged_messages.append(event)
            prev_tick = abs_tick

    def reset_playback_state(self):
        self.current_msg_index = self.loop_a_index if (self.loop_enabled and self.loop_a_index is not None) else 0
        if self.current_msg_index < len(self.merged_messages):
            self.accumulated_ticks = self.merged_messages[self.current_msg_index].abs_tick
        else:
            self.accumulated_ticks = 0
        self.currently_playing_notes.clear()

    def seek(self, pct):
        if not self.merged_messages:
            return
        target_tick = (pct / 100.0) * self.total_ticks
        self.seek_to_tick(target_tick)

    def seek_to_measure(self, measure_number):
        if not self.measures_timeline:
            return
        measure_number = max(1, min(measure_number, len(self.measures_timeline)))
        m_info = self.measures_timeline[measure_number - 1]
        self.seek_to_tick(m_info['start_tick'])

    def seek_to_tick(self, target_tick):
        was_playing = self.playing_state in ['playing', 'count_in']
        if was_playing:
            self.playing_state = 'paused'
            self.all_notes_off()
            time.sleep(0.05)
            
        closest_index = 0
        min_diff = float('inf')
        for idx, event in enumerate(self.merged_messages):
            diff = abs(event.abs_tick - target_tick)
            if diff < min_diff:
                min_diff = diff
                closest_index = idx
                
        self.current_msg_index = closest_index
        if self.current_msg_index < len(self.merged_messages):
            self.accumulated_ticks = self.merged_messages[self.current_msg_index].abs_tick
        else:
            self.accumulated_ticks = int(target_tick)
            
        self.sync_midi_channel_states(self.current_msg_index)
            
        if was_playing:
            self.playing_state = 'playing'
            self.play_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.play_thread.start()
        else:
            if self.progress_callback and self.total_ticks > 0:
                pct = (self.accumulated_ticks / self.total_ticks) * 100
                self.progress_callback(pct)
            
            measure, beat, num, den, total_measures = self.get_measure_and_beat(self.accumulated_ticks)
            if self.measure_beat_callback:
                self.measure_beat_callback(measure, beat, num, den, total_measures)
            
            if self.status_callback:
                self.status_callback(f"Paused (M: {measure} | B: {beat} / {num} | {num}/{den}拍子)")

    def sync_midi_channel_states(self, up_to_index=None):
        """
        小節ジャンプ・シーク・ループ折り返し等で途中から再生した際にも、
        その時点までに設定されているべき楽器音色(program_change)と主要コントロール(音量・パン・表現等)を
        漏れなくMIDIデバイスへ先行送信し、ピアノ音色へ戻ってしまう現象を防止します。
        """
        if not self.merged_messages or not self.device_opened or not winmm:
            return

        if up_to_index is None:
            up_to_index = self.current_msg_index

        target_tick = 0
        if 0 <= up_to_index < len(self.merged_messages):
            target_tick = self.merged_messages[up_to_index].abs_tick
        elif self.merged_messages:
            target_tick = self.merged_messages[-1].abs_tick

        latest_programs = {}
        latest_ccs = {}
        tracked_cc_nums = {0, 2, 7, 10, 11, 32}

        for idx, event in enumerate(self.merged_messages):
            if event.abs_tick > target_tick:
                break
            if event.is_metronome:
                continue
            msg = event.msg
            if msg.is_meta:
                continue
            if msg.type == "program_change":
                latest_programs[msg.channel] = msg
            elif msg.type == "control_change" and msg.control in tracked_cc_nums:
                latest_ccs[(msg.channel, msg.control)] = msg

        for (_, _), cc_msg in sorted(latest_ccs.items()):
            b = cc_msg.bytes()
            if len(b) >= 3:
                dw_msg = b[0] | (b[1] << 8) | (b[2] << 16)
                winmm.midiOutShortMsg(self.h_midi_out, dw_msg)

        for ch, pc_msg in sorted(latest_programs.items()):
            b = pc_msg.bytes()
            if len(b) >= 2:
                dw_msg = b[0] | (b[1] << 8)
                winmm.midiOutShortMsg(self.h_midi_out, dw_msg)

    def set_loop_point_by_measure(self, point_type, measure_number):
        """A小節の頭から、B小節の末尾（end_tick）までをループ範囲に解決します。"""
        if not self.measures_timeline:
            return
        measure_number = max(1, min(measure_number, len(self.measures_timeline)))
        m_info = self.measures_timeline[measure_number - 1]
        
        if point_type == 'A':
            target_tick = m_info['start_tick']
            closest_index = 0
            min_diff = float('inf')
            for idx, event in enumerate(self.merged_messages):
                diff = abs(event.abs_tick - target_tick)
                if diff < min_diff:
                    min_diff = diff
                    closest_index = idx
            self.loop_a_index = closest_index
            
        elif point_type == 'B':
            self.loop_b_target_tick = m_info['end_tick']
            
            target_tick = m_info['end_tick']
            closest_index = 0
            min_diff = float('inf')
            for idx, event in enumerate(self.merged_messages):
                diff = abs(event.abs_tick - target_tick)
                if diff < min_diff:
                    min_diff = diff
                    closest_index = idx
            self.loop_b_index = closest_index
            
        if self.loop_a_index is not None and self.loop_b_index is not None:
            # 🚀【解決】： A点 ≦ B点 (同一小節での1小節ループ対応) に緩和するため、より未来の場合のみスワップ
            if self.loop_a_index > self.loop_b_index:
                self.loop_a_index, self.loop_b_index = self.loop_b_index, self.loop_a_index

    def send_midi_msg(self, msg):
        if not self.device_muted and not self.internal_synth_enabled and self.device_opened and winmm:
            b = msg.bytes()
            if len(b) > 0:
                dw_msg = b[0]
                if len(b) > 1: dw_msg |= (b[1] << 8)
                if len(b) > 2: dw_msg |= (b[2] << 16)
                winmm.midiOutShortMsg(self.h_midi_out, dw_msg)
                
        if self.synth_initialized and self.internal_synth_enabled:
            if msg.type == "note_on" and msg.velocity > 0:
                self.synth_note_on(msg.note, msg.velocity)
            elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                self.synth_note_off(msg.note)

    def play_metronome_tick(self, beat_in_measure, force_standard=False):
        pattern = "標準（頭拍強調）" if force_standard else self.metronome_pattern
        if pattern == "なし":
            return

        if not self.device_muted and not self.internal_synth_enabled and self.device_opened and winmm:
            if pattern == "小節頭のみ" and beat_in_measure != 0:
                pass
            elif pattern == "強調なし全拍":
                winmm.midiOutShortMsg(self.h_midi_out, 0x99 | (77 << 8) | (80 << 16))
            else: 
                note = 76 if beat_in_measure == 0 else 77
                vel = 110 if beat_in_measure == 0 else 80
                winmm.midiOutShortMsg(self.h_midi_out, 0x99 | (note << 8) | (vel << 16))
                    
        if self.synth_initialized and self.internal_synth_enabled:
            is_strong = (beat_in_measure == 0)
            is_playable = True
            
            if pattern == "小節頭のみ" and beat_in_measure != 0:
                is_playable = False
            elif pattern == "強調なし全拍":
                is_strong = False
                
            if is_playable:
                try:
                    vol = self.volume_factor
                    if is_strong:
                        self.metro_sound_strong.set_volume(vol)
                        self.metro_sound_strong.play()
                    else:
                        self.metro_sound_weak.set_volume(vol * 0.6)
                        self.metro_sound_weak.play()
                except Exception:
                    pass

    def play(self):
        if not self.mido_file:
            return
        if self.playing_state in ['playing', 'count_in']:
            return
            
        self.playing_state = 'playing' if self.current_msg_index > 0 else 'count_in'
        self.play_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.play_thread.start()

    def pause(self):
        if self.playing_state in ['playing', 'count_in']:
            self.playing_state = 'paused'
            self.all_notes_off()
            if self.status_callback:
                measure, beat, num, den, total_measures = self.get_measure_and_beat(self.accumulated_ticks)
                self.status_callback(f"Paused (M: {measure} | B: {beat} / {num} | {num}/{den}拍子)")

    def stop(self):
        self.playing_state = 'stopped'
        self.reset_playback_state()
        self.all_notes_off()
        if self.status_callback:
            self.status_callback("Stopped")
        if self.progress_callback:
            pct = (self.accumulated_ticks / self.total_ticks) * 100 if self.total_ticks > 0 else 0.0
            self.progress_callback(pct)
            
        measure, beat, num, den, total_measures = self.get_measure_and_beat(self.accumulated_ticks)
        if self.measure_beat_callback:
            self.measure_beat_callback(measure, beat, num, den, total_measures)

    def ticks_to_ms(self, ticks):
        return self.tick_to_sec(ticks) * 1000.0

    def ms_to_ticks(self, ms):
        return int(self.sec_to_tick(ms / 1000.0))

    def sync_with_wav_ms(self, ms):
        target_tick = self.ms_to_ticks(ms)
        self.accumulated_ticks = max(0, min(target_tick, self.total_ticks))
        
        closest_index = 0
        min_diff = float('inf')
        for idx, event in enumerate(self.merged_messages):
            diff = abs(event.abs_tick - self.accumulated_ticks)
            if diff < min_diff:
                min_diff = diff
                closest_index = idx
        self.current_msg_index = closest_index

    def _playback_worker(self):
        try:
            last_sent_measure = -1
            last_sent_beat = -1
            has_triggered_stream_start = False
            
            while self.playing_state in ['playing', 'count_in']:
                self.sync_midi_channel_states(self.current_msg_index)
                
                if self.current_msg_index < len(self.merged_messages):
                    start_tick = self.merged_messages[self.current_msg_index].abs_tick
                    _, _, active_num, active_den, _ = self.get_measure_and_beat(start_tick)
                else:
                    start_tick = 0
                    active_num = self.time_sig_num
                    active_den = self.time_sig_den
                
                # 1. カウントイン
                if self.playing_state == 'count_in' and self.count_in_measures > 0:
                    total_beats = self.count_in_measures * active_num
                    total_count_in_ticks = self.count_in_measures * active_num * int(self.ticks_per_beat * (4.0 / active_den))
                    
                    for beat in range(total_beats):
                        if self.playing_state != 'count_in':
                            break
                        
                        beat_in_measure = beat % active_num
                        if self.status_callback:
                            self.status_callback(f"Count-in: {beat_in_measure + 1} / {active_num}")
                        
                        if not has_triggered_stream_start:
                            has_triggered_stream_start = True
                            if self.stream_start_callback:
                                self.stream_start_callback()
                        
                        self.play_metronome_tick(beat_in_measure, force_standard=True)
                        
                        active_bpm = max(1.0, self.get_bpm_at_tick(start_tick))
                        self.bpm = round(active_bpm)
                        beat_dur = (60.0 / active_bpm) * (4.0 / active_den)
                        start_wait = time.perf_counter()
                        
                        ticks_per_beat_val = int(self.ticks_per_beat * (4.0 / active_den))
                        beat_start_tick = -total_count_in_ticks + (beat * ticks_per_beat_val)
                        
                        while True:
                            if self.playing_state != 'count_in':
                                break
                            
                            elapsed = time.perf_counter() - start_wait
                            
                            ticks_per_sec = (active_bpm * self.ticks_per_beat) / 60.0
                            self.accumulated_ticks = beat_start_tick + int(elapsed * ticks_per_sec)
                            if self.accumulated_ticks > 0:
                                self.accumulated_ticks = 0
                            
                            remaining = beat_dur - elapsed
                            if remaining <= 0:
                                break
                            
                            if remaining > 0.015:
                                time.sleep(0.005)
                            elif remaining > 0.001:
                                time.sleep(0)
                            else:
                                pass
                    self.accumulated_ticks = 0
                    
                if self.playing_state == 'stopped':
                    break
                    
                # 2. 本編メイン再生
                self.playing_state = 'playing'
                reached_b_or_end = False
                
                while self.playing_state == 'playing' and self.current_msg_index < len(self.merged_messages):
                    if self.loop_enabled and self.loop_b_target_tick is not None:
                        if self.accumulated_ticks >= self.loop_b_target_tick:
                            reached_b_or_end = True
                            break
                    
                    event = self.merged_messages[self.current_msg_index]
                    ticks = event.time
                    
                    if not has_triggered_stream_start:
                        has_triggered_stream_start = True
                        if self.stream_start_callback:
                            self.stream_start_callback()
                    
                    if ticks > 0:
                        if self.active_pitches_callback:
                            self.active_pitches_callback(self.currently_playing_notes)
                            
                        start_wait = time.perf_counter()
                        start_tick_base = event.abs_tick - ticks
                        base_delta_sec = max(0.0, self.tick_to_sec(event.abs_tick, speed_ratio=1.0) - self.tick_to_sec(start_tick_base, speed_ratio=1.0))
                        
                        while True:
                            if self.playing_state != 'playing':
                                break
                            
                            speed_r = max(0.05, self.speed_ratio)
                            dynamic_delay = base_delta_sec / speed_r
                            
                            elapsed = time.perf_counter() - start_wait
                            
                            cur_bpm = max(1.0, self.get_bpm_at_tick(start_tick_base, speed_r))
                            self.bpm = round(cur_bpm)
                            ticks_per_sec = (cur_bpm * self.ticks_per_beat) / 60.0
                            self.accumulated_ticks = min(event.abs_tick, start_tick_base + int(elapsed * ticks_per_sec))
                            
                            if self.loop_enabled and self.loop_b_target_tick is not None:
                                if self.accumulated_ticks >= self.loop_b_target_tick:
                                    reached_b_or_end = True
                                    break
                            
                            remaining = dynamic_delay - elapsed
                            if remaining <= 0:
                                break
                            
                            if remaining > 0.015:
                                time.sleep(0.005)
                            elif remaining > 0.001:
                                time.sleep(0)
                            else:
                                pass
                                
                        if reached_b_or_end:
                            break
                    
                    if self.playing_state != 'playing':
                        break
                    
                    self.accumulated_ticks = event.abs_tick
                    self.bpm = round(self.get_bpm_at_tick(self.accumulated_ticks))
                    measure, beat, num, den, total_measures = self.get_measure_and_beat(self.accumulated_ticks)
                    
                    if measure != last_sent_measure or beat != last_sent_beat:
                        if self.measure_beat_callback:
                            self.measure_beat_callback(measure, beat, num, den, total_measures)
                        last_sent_measure = measure
                        last_sent_beat = beat
                    
                    if event.is_metronome:
                        self.play_metronome_tick(event.beat_in_measure)
                    else:
                        msg = event.msg
                        if not msg.is_meta and msg.type != 'sysex':
                            self.send_midi_msg(msg)
                            
                            if msg.type == "note_on" and msg.velocity > 0:
                                self.currently_playing_notes.add(msg.note)
                            elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                                if msg.note in self.currently_playing_notes:
                                    self.currently_playing_notes.remove(msg.note)
                    
                    self.current_msg_index += 1
                    
                if self.playing_state != 'playing':
                    break
                
                # 3. ABループ折り返し
                if self.loop_enabled and (reached_b_or_end or self.current_msg_index >= len(self.merged_messages)):
                    self.all_notes_off()
                    self.current_msg_index = self.loop_a_index if self.loop_a_index is not None else 0
                    if self.current_msg_index < len(self.merged_messages):
                        self.accumulated_ticks = self.merged_messages[self.current_msg_index].abs_tick
                    else:
                        self.accumulated_ticks = 0
                        
                    if self.progress_callback and self.total_ticks > 0:
                        pct = (self.accumulated_ticks / self.total_ticks) * 100
                        self.progress_callback(pct)
                        
                    time.sleep(0.1)
                    has_triggered_stream_start = False
                    self.playing_state = 'count_in'
                else:
                    if self.current_msg_index >= len(self.merged_messages):
                        self.playing_state = 'stopped'
                        self.reset_playback_state()
                        self.all_notes_off()
                        if self.status_callback:
                            self.status_callback("Finished")
                        if self.progress_callback:
                            self.progress_callback(100.0)
                        
                        measure, beat, num, den, total_measures = self.get_measure_and_beat(self.accumulated_ticks)
                        if self.measure_beat_callback:
                            self.measure_beat_callback(measure, beat, num, den, total_measures)
                        break
                        
        except Exception as e:
            self.playing_state = 'stopped'
            self.all_notes_off()
            if self.error_callback:
                self.error_callback(e)
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


GM_INSTRUMENT_NAMES = {
    0: "Acoustic Grand Piano (ピアノ)",
    1: "Bright Acoustic Piano (ピアノ)",
    4: "Electric Piano 1 (エレピ)",
    5: "Electric Piano 2 (エレピ)",
    11: "Vibraphone (ヴィブラフォン)",
    16: "Drawbar Organ (オルガン)",
    19: "Church Organ (チャーチオルガン)",
    21: "Accordion (アコーディオン)",
    22: "Harmonica (ハーモニカ)",
    23: "Tango Accordion (バンドネオン)",
    24: "Acoustic Guitar Nylon (アコギ)",
    25: "Acoustic Guitar Steel (アコギ)",
    26: "Electric Guitar Jazz (ジャズギター)",
    27: "Electric Guitar Clean (エレキギター)",
    32: "Acoustic Bass (ウッドベース)",
    33: "Electric Bass Finger (エレキベース)",
    35: "Fretless Bass (フレットレスベース)",
    40: "Violin (バイオリン)",
    41: "Viola (ビオラ)",
    42: "Cello (チェロ)",
    48: "String Ensemble 1 (ストリングス)",
    49: "String Ensemble 2 (ストリングス)",
    52: "Choir Aahs (コーラス)",
    56: "Trumpet (トランペット)",
    57: "Trombone (トロンボーン)",
    60: "French Horn (ホルン)",
    61: "Brass Section (ブラス)",
    64: "Soprano Sax (ソプラノサックス)",
    65: "Alto Sax (アルトサックス)",
    66: "Tenor Sax (テナーサックス)",
    68: "Oboe (オーボエ)",
    71: "Clarinet (クラリネット)",
    73: "Flute (フルート)",
    75: "Pan Flute (パンフルート)",
    79: "Ocarina (オカリナ)",
    80: "Lead 1 Square (シンセリード)",
    81: "Lead 2 Sawtooth (シンセリード)",
    88: "Pad 1 New Age (シンセパッド)",
}


def get_gm_instrument_name(program, is_drum=False):
    if is_drum:
        return "Percussion / Drums (ドラム)"
    if program in GM_INSTRUMENT_NAMES:
        return GM_INSTRUMENT_NAMES[program]
    return f"GM Program #{program + 1}"


class PlayableEvent:
    def __init__(self, mido_msg, is_metronome=False, beat_in_measure=0, abs_tick=0, track_idx=-1):
        self.msg = mido_msg
        self.is_metronome = is_metronome
        self.beat_in_measure = beat_in_measure
        self.abs_tick = abs_tick
        self.track_idx = track_idx
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
        
        # マルチパート・主旋律トラック管理
        self.tracks_info = []
        self.main_track_index = 0
        self.main_midi_channel = 0
        self.force_main_harmonica = True
        self.part_play_mode = "全パート再生"  # "全パート再生" / "主旋律ソロ" / "伴奏のみ(カラオケ)"
        
        self.playing_state = 'stopped'
        self.current_msg_index = 0
        self.accumulated_ticks = 0
        self.total_ticks = 0
        self._interp_base_tick = 0.0
        self._interp_max_tick = 0.0
        self._interp_start_perf = 0.0
        self._interp_ticks_per_sec = 0.0
        
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
        
        raw_merged_with_track = self.analyze_tracks_and_merge()
        raw_merged_msgs = [item[2] for item in raw_merged_with_track]
        self.total_ticks = raw_merged_with_track[-1][0] if raw_merged_with_track else 0
        
        self.compute_tempo_timeline(raw_merged_msgs)
        self.default_bpm = round(self.tempo_timeline[0]["bpm"]) if self.tempo_timeline else 120
        self.bpm = round(self.default_bpm * self.speed_ratio)
        
        self.compute_measure_timeline()
        
        if self.measures_timeline:
            self.time_sig_num = self.measures_timeline[0]['num']
            self.time_sig_den = self.measures_timeline[0]['den']
        else:
            self.time_sig_num = 4
            self.time_sig_den = 4
            
        self.generate_merged_messages_with_metronome(raw_merged_with_track)
        
        self.loop_a_index = None
        self.loop_b_index = None
        self.loop_b_target_tick = None 
        self.reset_playback_state()
        self.sync_midi_channel_states(0)

    def analyze_tracks_and_merge(self):
        """
        全トラック（またはFormat 0の複数チャンネル）を解析して self.tracks_info を構築し、
        主旋律パートの初期自動選択とイベントマージを行います。
        """
        playable_tracks = []
        all_channels_in_single_track = set()

        for t_idx, track in enumerate(self.mido_file.tracks):
            t_name = ""
            note_count = 0
            in_range_count = 0
            ch_counts = {}
            prog_by_ch = {}
            first_prog = None

            for msg in track:
                if msg.is_meta and msg.type == "track_name" and not t_name:
                    t_name = msg.name.strip()
                elif not msg.is_meta:
                    if msg.type == "program_change":
                        prog_by_ch[msg.channel] = msg.program
                        if first_prog is None:
                            first_prog = msg.program
                    elif msg.type == "note_on" and msg.velocity > 0:
                        note_count += 1
                        ch_counts[msg.channel] = ch_counts.get(msg.channel, 0) + 1
                        if msg.channel != 9 and 24 <= msg.note <= 98:
                            in_range_count += 1

            if note_count > 0:
                primary_ch = max(ch_counts.items(), key=lambda x: x[1])[0]
                primary_prog = prog_by_ch.get(primary_ch, first_prog if first_prog is not None else 0)
                is_drum = (primary_ch == 9)
                inst_name = get_gm_instrument_name(primary_prog, is_drum=is_drum)
                playable_tracks.append({
                    "track_idx": t_idx,
                    "name": t_name if t_name else f"Track {t_idx + 1}",
                    "channel": primary_ch,
                    "program": primary_prog,
                    "instrument_name": inst_name,
                    "note_count": note_count,
                    "in_range_count": in_range_count,
                    "is_drum": is_drum,
                    "channels_used": set(ch_counts.keys())
                })
                if len(ch_counts) > 1:
                    all_channels_in_single_track = set(ch_counts.keys())

        # Format 0 等で1つのトラック内に複数チャンネルが混在している場合はチャンネル単位でパート分割
        split_by_channel = (len(playable_tracks) == 1 and len(all_channels_in_single_track) > 1)
        if split_by_channel:
            base_track = self.mido_file.tracks[playable_tracks[0]["track_idx"]]
            ch_info_map = {}
            prog_by_ch = {}
            for msg in base_track:
                if not msg.is_meta:
                    if msg.type == "program_change":
                        prog_by_ch[msg.channel] = msg.program
                    elif msg.type == "note_on" and msg.velocity > 0:
                        ch = msg.channel
                        if ch not in ch_info_map:
                            ch_info_map[ch] = {"note_count": 0, "in_range_count": 0}
                        ch_info_map[ch]["note_count"] += 1
                        if ch != 9 and 24 <= msg.note <= 98:
                            ch_info_map[ch]["in_range_count"] += 1

            self.tracks_info = []
            for ch in sorted(ch_info_map.keys()):
                prog = prog_by_ch.get(ch, 0)
                is_drum = (ch == 9)
                inst_name = get_gm_instrument_name(prog, is_drum=is_drum)
                self.tracks_info.append({
                    "track_idx": ch,
                    "name": f"Channel {ch + 1}",
                    "channel": ch,
                    "program": prog,
                    "instrument_name": inst_name,
                    "note_count": ch_info_map[ch]["note_count"],
                    "in_range_count": ch_info_map[ch]["in_range_count"],
                    "is_drum": is_drum
                })
        else:
            self.tracks_info = [
                {k: v for k, v in info.items() if k != "channels_used"}
                for info in playable_tracks
            ]

        if not self.tracks_info:
            self.tracks_info = [{
                "track_idx": 0,
                "name": "Track 1",
                "channel": 0,
                "program": 22,
                "instrument_name": get_gm_instrument_name(22),
                "note_count": 0,
                "in_range_count": 0,
                "is_drum": False
            }]

        # 主旋律パートの自動推論（ハーモニカ音色・トラック名・音域内ノーツ数から最適パートを選択）
        best_track_idx = self.tracks_info[0]["track_idx"]
        best_score = -1
        for order_i, info in enumerate(self.tracks_info):
            if info["is_drum"] or info["in_range_count"] == 0:
                score = 0
            else:
                score = 100
                if info["program"] == 22:
                    score += 500
                elif info["program"] in (21, 23, 64, 65, 66, 68, 71, 73, 79, 80, 81):
                    score += 150
                low_name = info["name"].lower()
                if any(k in low_name for k in ("harmonica", "melody", "vocal", "main", "lead", "solo", "メロディ", "主旋律", "ハーモニカ")):
                    score += 400
                # トラック順が若い非ドラムパートを優先
                score += max(0, 50 - order_i * 5)
            if score > best_score:
                best_score = score
                best_track_idx = info["track_idx"]

        self.set_main_track(best_track_idx)

        # 全トラックのイベントを絶対ティック＋パート識別子付きでマージ
        collected = []
        order_counter = 0
        for t_idx, track in enumerate(self.mido_file.tracks):
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                part_id = getattr(msg, "channel", t_idx) if split_by_channel else t_idx
                collected.append((abs_tick, order_counter, part_id, msg))
                order_counter += 1

        collected.sort(key=lambda x: (x[0], x[1]))

        raw_merged_with_track = []
        prev_tick = 0
        for abs_tick, _, part_id, msg in collected:
            delta = abs_tick - prev_tick
            cloned_msg = msg.copy(time=delta)
            raw_merged_with_track.append((abs_tick, part_id, cloned_msg))
            prev_tick = abs_tick

        return raw_merged_with_track

    def set_main_track(self, track_idx):
        """主旋律パートを切り替え、伴奏とチャンネルが競合しないよう専用チャンネルルーティングを更新します。"""
        self.main_track_index = track_idx
        main_info = None
        other_channels = set()
        for info in self.tracks_info:
            if info["track_idx"] == track_idx:
                main_info = info
            else:
                other_channels.add(info["channel"])

        orig_ch = main_info["channel"] if main_info else 0
        if orig_ch == 9 or orig_ch in other_channels:
            # 他の伴奏トラックとチャンネルが重なる（またはCh.10ドラム）場合は空きチャンネルを割り当て
            chosen_ch = orig_ch
            for candidate_ch in range(16):
                if candidate_ch != 9 and candidate_ch not in other_channels:
                    chosen_ch = candidate_ch
                    break
            self.main_midi_channel = chosen_ch
        else:
            self.main_midi_channel = orig_ch

        if self.merged_messages:
            self.all_notes_off()
            self.sync_midi_channel_states(self.current_msg_index)

    def get_main_track_info(self):
        for info in self.tracks_info:
            if info["track_idx"] == self.main_track_index:
                return info
        return self.tracks_info[0] if self.tracks_info else None

    def is_track_audible(self, track_idx):
        """現在のパート再生モードに応じて、指定トラックを発音させるべきか判定します。"""
        if track_idx < 0:
            return True
        if self.part_play_mode == "主旋律ソロ":
            return track_idx == self.main_track_index
        elif self.part_play_mode == "伴奏のみ(カラオケ)":
            return track_idx != self.main_track_index
        return True

    def transform_msg_for_routing(self, msg, track_idx):
        """主旋律パートのチャンネル分離およびGMハーモニカ音色(Program 22)強制変換を行います。"""
        if track_idx == self.main_track_index and hasattr(msg, "channel"):
            if msg.type == "program_change" and self.force_main_harmonica:
                return msg.copy(channel=self.main_midi_channel, program=22)
            elif msg.channel != self.main_midi_channel:
                return msg.copy(channel=self.main_midi_channel)
        return msg

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

    def generate_merged_messages_with_metronome(self, raw_merged_with_track):
        absolute_events = []
        current_tick = 0
        for item in raw_merged_with_track:
            if isinstance(item, tuple) and len(item) == 3:
                abs_tick, t_idx, msg = item
                current_tick = abs_tick
            else:
                msg = item
                t_idx = 0
                current_tick += msg.time
            absolute_events.append((current_tick, PlayableEvent(msg, is_metronome=False, abs_tick=current_tick, track_idx=t_idx)))
            
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
                event = PlayableEvent(m_msg, is_metronome=True, beat_in_measure=b, abs_tick=beat_tick, track_idx=-1)
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
        self._interp_base_tick = float(self.accumulated_ticks)
        self._interp_max_tick = float(self.accumulated_ticks)
        self._interp_start_perf = 0.0
        self._interp_ticks_per_sec = 0.0
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
        self._interp_base_tick = float(self.accumulated_ticks)
        self._interp_max_tick = float(self.accumulated_ticks)
        self._interp_start_perf = time.perf_counter()
            
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
        小節ジャンプ・シーク・ループ折り返し・パート切替時にも、
        その時点までに設定されているべき楽器音色(program_change)と主要コントロール(音量・パン・表現等)を
        漏れなくMIDIデバイスへ先行送信し、主旋律パートのGMハーモニカ音色(Program 22)を確実に維持します。
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
            raw_msg = event.msg
            if raw_msg.is_meta:
                continue
            msg = self.transform_msg_for_routing(raw_msg, event.track_idx)
            if msg.type == "program_change":
                latest_programs[msg.channel] = msg
            elif msg.type == "control_change" and msg.control in tracked_cc_nums:
                latest_ccs[(msg.channel, msg.control)] = msg

        # 主旋律パートのハーモニカ音色強制がONの場合は、MIDI内にprogram_changeが無い場合も確実にProgram 22(Harmonica)を設定
        if self.force_main_harmonica:
            latest_programs[self.main_midi_channel] = mido.Message(
                'program_change', channel=self.main_midi_channel, program=22
            )

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

    def send_midi_msg(self, msg, track_idx=-1):
        if not self.is_track_audible(track_idx):
            return
        msg = self.transform_msg_for_routing(msg, track_idx)
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

    def _get_count_in_origin_tick(self, start_tick):
        if self.count_in_measures <= 0:
            return start_tick
        _, _, active_num, active_den, _ = self.get_measure_and_beat(max(0, start_tick))
        ticks_per_beat_val = int(self.ticks_per_beat * (4.0 / active_den))
        return start_tick - (self.count_in_measures * active_num * ticks_per_beat_val)

    def get_smooth_current_tick(self):
        """60FPS描画タイマー向けに、現在再生中（カウントイン含む）の連続ティック位置を高精度補間して返します。"""
        if self.playing_state not in ('playing', 'count_in'):
            return float(self.accumulated_ticks)
        if self._interp_ticks_per_sec <= 0.0 or self._interp_start_perf <= 0.0:
            return float(self.accumulated_ticks)
        elapsed = time.perf_counter() - self._interp_start_perf
        if elapsed <= 0.0:
            return float(self._interp_base_tick)
        tick = self._interp_base_tick + elapsed * self._interp_ticks_per_sec
        return float(min(self._interp_max_tick, tick))

    def play(self):
        if not self.mido_file:
            return
        if self.playing_state in ['playing', 'count_in']:
            return

        was_stopped = (self.playing_state == 'stopped')
        if self.loop_enabled and self.loop_a_index is not None:
            a_tick = self.merged_messages[self.loop_a_index].abs_tick if self.loop_a_index < len(self.merged_messages) else 0
            b_tick = self.loop_b_target_tick if self.loop_b_target_tick is not None else self.total_ticks
            if was_stopped or self.accumulated_ticks < a_tick or self.accumulated_ticks >= b_tick:
                self.current_msg_index = self.loop_a_index
                self.accumulated_ticks = a_tick

        start_tick = self.merged_messages[self.current_msg_index].abs_tick if self.current_msg_index < len(self.merged_messages) else 0
        if self.count_in_measures > 0:
            self.playing_state = 'count_in'
            init_tick = self._get_count_in_origin_tick(start_tick)
        else:
            self.playing_state = 'playing'
            init_tick = start_tick

        self.accumulated_ticks = init_tick
        self._interp_base_tick = float(init_tick)
        self._interp_max_tick = float(init_tick)
        self._interp_start_perf = time.perf_counter()
        self.play_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.play_thread.start()

    def pause(self):
        if self.playing_state in ['playing', 'count_in']:
            self.playing_state = 'paused'
            self.all_notes_off()
            if self.status_callback:
                measure, beat, num, den, total_measures = self.get_measure_and_beat(max(0, self.accumulated_ticks))
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
            
        measure, beat, num, den, total_measures = self.get_measure_and_beat(max(0, self.accumulated_ticks))
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
                
                # 1. カウントイン（A地点・開始小節の start_tick からカウントイン分だけ手前を起点に等速進行）
                if self.playing_state == 'count_in' and self.count_in_measures > 0:
                    ticks_per_beat_val = int(self.ticks_per_beat * (4.0 / active_den))
                    total_beats = self.count_in_measures * active_num
                    total_count_in_ticks = total_beats * ticks_per_beat_val
                    count_in_origin_tick = start_tick - total_count_in_ticks
                    self.accumulated_ticks = count_in_origin_tick
                    self._interp_base_tick = float(count_in_origin_tick)
                    self._interp_max_tick = float(count_in_origin_tick)
                    self._interp_start_perf = time.perf_counter()
                    
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
                        
                        start_wait = time.perf_counter()
                        beat_start_tick = count_in_origin_tick + (beat * ticks_per_beat_val)
                        beat_end_tick = beat_start_tick + ticks_per_beat_val
                        self._interp_base_tick = float(beat_start_tick)
                        self._interp_max_tick = float(beat_end_tick)
                        self._interp_start_perf = start_wait
                        
                        while True:
                            if self.playing_state != 'count_in':
                                break
                            
                            active_bpm = max(1.0, self.get_bpm_at_tick(max(0, start_tick)))
                            self.bpm = round(active_bpm)
                            beat_dur = (60.0 / active_bpm) * (4.0 / active_den)
                            ticks_per_sec = (active_bpm * self.ticks_per_beat) / 60.0
                            self._interp_ticks_per_sec = ticks_per_sec
                            
                            elapsed = time.perf_counter() - start_wait
                            self.accumulated_ticks = min(beat_end_tick, beat_start_tick + int(elapsed * ticks_per_sec))
                            
                            remaining = beat_dur - elapsed
                            if remaining <= 0:
                                break
                            
                            if remaining > 0.015:
                                time.sleep(0.005)
                            elif remaining > 0.001:
                                time.sleep(0)
                            else:
                                pass
                    self.accumulated_ticks = start_tick
                    self._interp_base_tick = float(start_tick)
                    self._interp_max_tick = float(start_tick)
                    self._interp_start_perf = time.perf_counter()
                    
                if self.playing_state == 'stopped':
                    break
                    
                # 2. 本編メイン再生（開始位置 start_tick を基準に差分ティックを待機し、A地点開始時の逆戻りワープを完全防止）
                self.playing_state = 'playing'
                reached_b_or_end = False
                current_play_tick = start_tick
                self.accumulated_ticks = start_tick
                self._interp_base_tick = float(start_tick)
                self._interp_max_tick = float(start_tick)
                self._interp_start_perf = time.perf_counter()
                
                while self.playing_state == 'playing' and self.current_msg_index < len(self.merged_messages):
                    if self.loop_enabled and self.loop_b_target_tick is not None:
                        if self.accumulated_ticks >= self.loop_b_target_tick:
                            reached_b_or_end = True
                            break
                    
                    event = self.merged_messages[self.current_msg_index]
                    ticks = max(0, event.abs_tick - current_play_tick)
                    
                    if not has_triggered_stream_start:
                        has_triggered_stream_start = True
                        if self.stream_start_callback:
                            self.stream_start_callback()
                    
                    if ticks > 0:
                        if self.active_pitches_callback:
                            self.active_pitches_callback(self.currently_playing_notes)
                            
                        start_wait = time.perf_counter()
                        start_tick_base = current_play_tick
                        base_delta_sec = max(0.0, self.tick_to_sec(event.abs_tick, speed_ratio=1.0) - self.tick_to_sec(start_tick_base, speed_ratio=1.0))
                        self._interp_base_tick = float(start_tick_base)
                        self._interp_max_tick = float(event.abs_tick)
                        self._interp_start_perf = start_wait
                        
                        while True:
                            if self.playing_state != 'playing':
                                break
                            
                            speed_r = max(0.05, self.speed_ratio)
                            dynamic_delay = base_delta_sec / speed_r
                            
                            elapsed = time.perf_counter() - start_wait
                            
                            cur_bpm = max(1.0, self.get_bpm_at_tick(start_tick_base, speed_r))
                            self.bpm = round(cur_bpm)
                            ticks_per_sec = (cur_bpm * self.ticks_per_beat) / 60.0
                            self._interp_ticks_per_sec = ticks_per_sec
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
                    
                    current_play_tick = event.abs_tick
                    self.accumulated_ticks = event.abs_tick
                    self._interp_base_tick = float(event.abs_tick)
                    self._interp_max_tick = float(event.abs_tick)
                    self._interp_start_perf = time.perf_counter()
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
                            self.send_midi_msg(msg, track_idx=event.track_idx)
                            
                            # 穴のLED発光(currently_playing_notes)は、常に選択中の主旋律パートのノーツのみに連動させる
                            if event.track_idx < 0 or event.track_idx == self.main_track_index:
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
                    next_a_tick = self.merged_messages[self.current_msg_index].abs_tick if self.current_msg_index < len(self.merged_messages) else 0
                    if self.count_in_measures > 0:
                        self.playing_state = 'count_in'
                        loop_init_tick = self._get_count_in_origin_tick(next_a_tick)
                    else:
                        self.playing_state = 'playing'
                        loop_init_tick = next_a_tick
                    self.accumulated_ticks = loop_init_tick
                    self._interp_base_tick = float(loop_init_tick)
                    self._interp_max_tick = float(loop_init_tick)
                    self._interp_start_perf = time.perf_counter()
                        
                    if self.progress_callback and self.total_ticks > 0:
                        pct = (max(0, self.accumulated_ticks) / self.total_ticks) * 100
                        self.progress_callback(pct)
                        
                    has_triggered_stream_start = False
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
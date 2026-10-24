# -*- coding: utf-8 -*-
"""
v3.0/audio_engine.py
Windows Multimedia API (WinMM) を用いた低レイテンシ・ジッターフリーMIDI音響再生エンジン。
- timeBeginPeriod(1) によるOS高分解能1msタイマー駆動
- SharedClockBridge (ナノ秒OSカウンタ) と完全非同期同期
- GM音色 (Program 22: Harmonica) 強制ルーティング
- 全パート再生 / 主旋律ソロ / 伴奏カラオケ切替対応
- オールノートオフ・オールサウンドオフによる残響・音残り完全防止
"""

import os
import sys
import time
import bisect
import threading
import ctypes
from ctypes import wintypes

from ipc_state import SharedClockBridge

# WinMM API 型定義
HMIDIOUT = wintypes.HANDLE
PHMIDIOUT = ctypes.POINTER(HMIDIOUT)

try:
    if sys.platform == "win32":
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        winmm = ctypes.windll.winmm
        winmm.midiOutOpen.argtypes = [PHMIDIOUT, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
        winmm.midiOutOpen.restype = wintypes.UINT
        winmm.midiOutClose.argtypes = [HMIDIOUT]
        winmm.midiOutClose.restype = wintypes.UINT
        winmm.midiOutShortMsg.argtypes = [HMIDIOUT, wintypes.DWORD]
        winmm.midiOutShortMsg.restype = wintypes.UINT
        winmm.midiOutSetVolume.argtypes = [HMIDIOUT, wintypes.DWORD]
        winmm.midiOutSetVolume.restype = wintypes.UINT
        winmm.timeBeginPeriod.argtypes = [wintypes.UINT]
        winmm.timeBeginPeriod.restype = wintypes.UINT
        winmm.timeEndPeriod.argtypes = [wintypes.UINT]
        winmm.timeEndPeriod.restype = wintypes.UINT
    else:
        winmm = None
except Exception as e:
    print(f"[AudioEngine Warning] WinMM initialization failed: {e}")
    winmm = None


class AudioEngine:
    """高精度・低レイテンシMIDI音響エンジン"""

    PART_ALL = "全パート再生"
    PART_SOLO = "主旋律ソロ"
    PART_ACCOMP = "伴奏のみ(カラオケ)"

    def __init__(self, clock_bridge: SharedClockBridge):
        self.clock = clock_bridge
        self.h_midi_out = HMIDIOUT(0)
        self.device_opened = False
        self._timer_period_active = False

        # 再生パラメータ
        self.part_mode = self.PART_ALL
        self.force_main_harmonica = True
        self.volume_ratio = 1.0  # 0.0 〜 1.0
        self.is_muted = False
        self.is_midi_notes_muted = False
        self.transpose_semitones = 0
        self.timeline = None

        # メトロノームパラメータ
        self.metronome_mode = "標準（頭拍強調）"
        self.count_in_measures = 1
        self.metro_events = []
        self.metro_secs = []
        self._next_metro_idx = 0

        # A-Bループパラメータ
        self.loop_enabled = False
        self.loop_a_sec = 0.0
        self.loop_b_sec = None
        self.on_loop_wrapped_callback = None
        self._suppress_notes_until_sec = None
        self._loop_ci_events = []

        # コンパイル済イベントキュー
        self._lock = threading.RLock()
        self.events = []
        self.event_secs = []
        self.main_track_idx = 0
        self.main_track_indices = [0]
        self.accomp_track_indices = None
        self.main_channel = 0
        self.split_by_channel = False
        self.total_duration_sec = 0.0

        # 再生音源モード (B案) & 内蔵シンセフォールバック
        self.guide_audio_engine = "Windows標準MIDI (WinMM / 推奨)"
        self.synth_fallback = False
        self.synth_voices = {}
        self.active_synth_channels = {}
        self._ui_beep_sound = None
        self.on_synth_fallback_callback = None
        self.on_playback_finished_callback = None

        # 再生ワーカースレッド制御
        self.is_running = True
        self._last_cur_sec = -1.0
        self._next_ev_idx = 0

        # WinMM デバイス初期化
        self._init_device()

        # バックグラウンド音響ワーカースレッド起動
        self._worker_thread = threading.Thread(target=self._audio_worker_loop, daemon=True)
        self._worker_thread.start()

    def _init_device(self):
        """WinMMデバイスオープン (Microsoft GS Wavetable優先) & 1msタイマー分解能設定"""
        if not winmm:
            self.synth_fallback = True
            self.init_internal_synth()
            return
        try:
            winmm.timeBeginPeriod(1)
            self._timer_period_active = True
        except Exception:
            pass

        try:
            # 接続デバイスをスキャンし、Microsoft GS Wavetable Synth を優先オープン
            target_dev = 0
            try:
                class MIDIOUTCAPSW(ctypes.Structure):
                    _fields_ = [
                        ("wMid", wintypes.WORD),
                        ("wPid", wintypes.WORD),
                        ("vDriverVersion", wintypes.UINT),
                        ("szPname", wintypes.WCHAR * 32),
                        ("wTechnology", wintypes.WORD),
                        ("wVoices", wintypes.WORD),
                        ("wNotes", wintypes.WORD),
                        ("wChannelMask", wintypes.WORD),
                        ("dwSupport", wintypes.DWORD),
                    ]
                num_devs = winmm.midiOutGetNumDevs()
                for dev_id in range(num_devs):
                    caps = MIDIOUTCAPSW()
                    if winmm.midiOutGetDevCapsW(dev_id, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
                        name = str(caps.szPname).lower()
                        if "microsoft gs" in name or "wavetable" in name:
                            target_dev = dev_id
                            break
            except Exception:
                target_dev = 0

            res = winmm.midiOutOpen(ctypes.byref(self.h_midi_out), target_dev, 0, 0, 0)
            if res != 0:
                res = winmm.midiOutOpen(ctypes.byref(self.h_midi_out), 0xFFFFFFFF, 0, 0, 0)
            if res == 0:
                self.device_opened = True
                self.set_volume(self.volume_ratio)
            else:
                self.device_opened = False
                self.synth_fallback = True
                self.init_internal_synth()
        except Exception as ex:
            print(f"[AudioEngine Error] Failed to open MIDI device: {ex}")
            self.device_opened = False
            self.synth_fallback = True
            self.init_internal_synth()

    def set_guide_audio_engine(self, engine_mode: str):
        """ガイド再生音源切替 (B案: Windows標準MIDI / 内蔵軽量シンセ)"""
        with self._lock:
            self.guide_audio_engine = str(engine_mode)
            self.all_notes_off()
            if "内蔵" in self.guide_audio_engine or "シンセ" in self.guide_audio_engine:
                self.init_internal_synth()

    def init_internal_synth(self):
        """内蔵軽量シンセの波形バッファ事前生成 (pygame.mixer)"""
        if self.synth_voices:
            return
        try:
            import pygame
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            # ハーモニカ演奏音域 (24〜98) の倍音波形を事前キャッシュ
            sr = 44100
            for note in range(24, 99):
                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                # 0.8秒の自然減衰波形
                wave_data = generate_harmonica_tone(freq, int(0.8 * sr), sr)
                pcm = (np.clip(wave_data, -1.0, 1.0) * 32767.0).astype(np.int16)
                stereo = np.column_stack((pcm, pcm))
                self.synth_voices[note] = pygame.mixer.Sound(buffer=stereo)

            # メトロノーム・カウントイン・UIクリック音 (強拍1200Hz, 弱拍800Hz)
            click_hi = generate_metronome_click(1200.0, sr, duration=0.05)
            pcm_hi = (np.clip(click_hi, -1.0, 1.0) * 32767.0).astype(np.int16)
            self.synth_click_hi = pygame.mixer.Sound(buffer=np.column_stack((pcm_hi, pcm_hi)))

            click_lo = generate_metronome_click(800.0, sr, duration=0.05)
            pcm_lo = (np.clip(click_lo, -1.0, 1.0) * 32767.0).astype(np.int16)
            self.synth_click_lo = pygame.mixer.Sound(buffer=np.column_stack((pcm_lo, pcm_lo)))

            print("[AudioEngine] 内蔵軽量シンセの音色キャッシュを生成しました (24〜98音 & メトロノーム)")
        except Exception as e:
            print(f"[AudioEngine Warning] 内蔵シンセ初期化失敗: {e}")

    def synth_note_on(self, note: int, velocity: int = 80):
        if not self.synth_voices:
            self.init_internal_synth()
        snd = self.synth_voices.get(note)
        if snd:
            try:
                import pygame
                ch = pygame.mixer.find_channel()
                if ch:
                    vol = (max(0, min(127, velocity)) / 127.0) * self.volume_ratio if not self.is_muted else 0.0
                    ch.set_volume(vol)
                    ch.play(snd)
                    self.active_synth_channels[note] = ch
            except Exception:
                pass

    def synth_note_off(self, note: int):
        ch = self.active_synth_channels.pop(note, None)
        if ch:
            try:
                ch.fadeout(40)
            except Exception:
                pass

    def close(self):
        """エンジン終了処理"""
        self.is_running = False
        self.all_notes_off()
        if self.device_opened and winmm:
            try:
                winmm.midiOutClose(self.h_midi_out)
            except Exception:
                pass
            self.device_opened = False
        if self._timer_period_active and winmm:
            try:
                winmm.timeEndPeriod(1)
            except Exception:
                pass
            self._timer_period_active = False

    def set_volume(self, ratio: float):
        """音量設定 (0.0 〜 1.0)"""
        self.volume_ratio = max(0.0, min(1.0, float(ratio)))
        if self.device_opened and winmm:
            val = int(self.volume_ratio * 65535) if not self.is_muted else 0
            dw_vol = (val & 0xFFFF) | ((val & 0xFFFF) << 16)
            try:
                winmm.midiOutSetVolume(self.h_midi_out, dw_vol)
            except Exception:
                pass

    def set_muted(self, muted: bool):
        self.is_muted = bool(muted)
        self.set_volume(self.volume_ratio)

    def set_midi_notes_muted(self, muted: bool):
        """メトロノーム/カウントイン拍は生かしたまま、楽曲MIDIノーツのみを消音/復帰 (伴奏のみモード等)"""
        self.is_midi_notes_muted = bool(muted)
        if self.is_midi_notes_muted:
            self.all_notes_off()

    def set_part_mode(self, mode: str):
        """全パート再生 / 主旋律ソロ / 伴奏カラオケ切替"""
        self.part_mode = str(mode)
        self.all_notes_off()

    def is_track_audible(self, track_idx: int) -> bool:
        """現在のパートモードに基づき指定トラックを発音すべきか判定 (複数主旋律対応)"""
        main_indices = getattr(self, "main_track_indices", [self.main_track_idx])
        is_main = track_idx in main_indices
        if is_main:
            return self.part_mode != self.PART_ACCOMP
        if self.part_mode == self.PART_SOLO:
            return False
        return (self.accomp_track_indices is None or track_idx in self.accomp_track_indices)

    def all_notes_off(self):
        """全チャンネルの残響・持続音を完全遮断"""
        if self.device_opened and winmm:
            for ch in range(16):
                try:
                    # CC 64: Sustain Pedal OFF (0)
                    winmm.midiOutShortMsg(self.h_midi_out, (0xB0 | ch) | (64 << 8) | (0 << 16))
                    # CC 120: All Sound Off (0)
                    winmm.midiOutShortMsg(self.h_midi_out, (0xB0 | ch) | (120 << 8) | (0 << 16))
                    # CC 123: All Notes Off (0)
                    winmm.midiOutShortMsg(self.h_midi_out, (0xB0 | ch) | (123 << 8) | (0 << 16))
                except Exception:
                    pass
        for ch in list(self.active_synth_channels.values()):
            try:
                ch.stop()
            except Exception:
                pass
        self.active_synth_channels.clear()

    def _determine_main_channel(self, timeline):
        """主旋律のMIDIチャンネルを決定 (伴奏との衝突回避)"""
        other_channels = set()
        main_orig_ch = 0
        main_indices = set(self.main_track_indices) if getattr(self, "main_track_indices", None) else {self.main_track_idx}
        for info in getattr(timeline, "tracks_info", []):
            if info["track_idx"] in main_indices:
                main_orig_ch = info.get("channel", 0)
            else:
                other_channels.add(info.get("channel", 0))

        if main_orig_ch == 9 or main_orig_ch in other_channels:
            chosen = main_orig_ch
            for candidate in range(16):
                if candidate != 9 and candidate not in other_channels:
                    chosen = candidate
                    break
            self.main_channel = chosen
        else:
            self.main_channel = main_orig_ch

    def load_timeline(self, timeline):
        """MidiTimelineData から再生用MIDIイベントキューを高速事前コンパイル"""
        self.all_notes_off()
        self.timeline = timeline
        self.main_track_idx = timeline.main_track_idx
        self.main_track_indices = getattr(timeline, "main_track_indices", [timeline.main_track_idx])
        self.accomp_track_indices = getattr(timeline, "accomp_track_indices", None)
        self.transpose_accomp = getattr(timeline, "transpose_accomp", True)
        self.total_duration_sec = timeline.total_duration_sec
        self.split_by_channel = getattr(timeline, "split_by_channel", False)
        self._determine_main_channel(timeline)

        muted_tick_notes = {(nd["start_tick"], nd.get("raw_note", nd["note"])) for nd in getattr(timeline, "main_notes", []) if nd.get("is_muted", False)}
        muted_sec_notes = {f"{round(nd['start_sec'], 3)}_{nd.get('raw_note', nd['note'])}" for nd in getattr(timeline, "main_notes", []) if nd.get("is_muted", False)}

        raw_events = getattr(timeline, "raw_events", [])
        if not raw_events:
            self.events = []
            self.event_secs = []
            return

        compiled = []
        # 主旋律パートのプログラムチェンジ (Program 22: Harmonica) を先頭に事前注入
        if self.force_main_harmonica:
            compiled.append({
                "sec": 0.0,
                "dw_msg": (0xC0 | self.main_channel) | (22 << 8),
                "is_note_on": False,
                "is_note_off": False,
                "raw_note": 0,
                "velocity": 0,
                "pitch": 0,
                "track_idx": self.main_track_idx,
                "channel": self.main_channel,
                "type": "program_change",
                "is_main": True,
                "is_muted_note": False,
            })

        for cur_tick, t_idx, msg in raw_events:
            if msg.is_meta or msg.type == "sysex":
                continue

            sec = timeline.tick_to_sec(cur_tick)
            raw_ch = getattr(msg, "channel", 0) & 0x0F
            is_main = (raw_ch in self.main_track_indices) if self.split_by_channel else (t_idx in self.main_track_indices)
            ch = self.main_channel if is_main else raw_ch
            part_id = raw_ch if self.split_by_channel else t_idx

            dw_msg = None
            is_note_on = False
            is_note_off = False
            pitch = 0
            is_muted_note = False

            vel = getattr(msg, "velocity", 64)
            should_transpose = is_main or (self.transpose_accomp and ch != 9)
            if msg.type == "note_on" and vel > 0:
                is_note_on = True
                pitch = msg.note
                p_eff = min(127, max(0, pitch + (self.transpose_semitones if should_transpose else 0)))
                dw_msg = (0x90 | ch) | (p_eff << 8) | ((vel & 0x7F) << 16)
                if is_main:
                    if (cur_tick, pitch) in muted_tick_notes or f"{round(sec, 3)}_{pitch}" in muted_sec_notes:
                        is_muted_note = True
            elif (msg.type == "note_off") or (msg.type == "note_on" and vel == 0):
                is_note_off = True
                pitch = msg.note
                p_eff = min(127, max(0, pitch + (self.transpose_semitones if should_transpose else 0)))
                dw_msg = (0x80 | ch) | (p_eff << 8) | (0 << 16)
            elif msg.type == "program_change":
                prog = 22 if (is_main and self.force_main_harmonica) else (msg.program & 0x7F)
                dw_msg = (0xC0 | ch) | (prog << 8)
            elif msg.type == "control_change":
                dw_msg = (0xB0 | ch) | ((msg.control & 0x7F) << 8) | ((msg.value & 0x7F) << 16)
            elif msg.type == "pitchwheel":
                val = max(-8192, min(8191, msg.pitch)) + 8192
                lsb = val & 0x7F
                msb = (val >> 7) & 0x7F
                dw_msg = (0xE0 | ch) | (lsb << 8) | (msb << 16)

            if dw_msg is not None:
                compiled.append({
                    "sec": sec,
                    "dw_msg": dw_msg,
                    "is_note_on": is_note_on,
                    "is_note_off": is_note_off,
                    "raw_note": pitch,
                    "velocity": vel,
                    "pitch": pitch,
                    "track_idx": part_id,
                    "channel": ch,
                    "type": msg.type,
                    "is_main": is_main,
                    "is_muted_note": is_muted_note,
                })

        compiled.sort(key=lambda x: x["sec"])
        self.events = compiled
        self.event_secs = [e["sec"] for e in compiled]
        self._next_ev_idx = 0
        self._last_cur_sec = -1.0

        # メトロノーム・カウントインイベント展開
        self._rebuild_metro_events()

        # ★ ロード直後に全チャンネルの音色 (Program Change) と初期コントロールを先行同期
        self.sync_midi_channel_states(0.0)

    def sync_midi_channel_states(self, target_sec: float = 0.0):
        """
        ファイル読込・シーク・ループ折り返し・パート切替時にも、
        その時点までに設定されているべき楽器音色 (Program Change) と主要コントロール (CC: 音量・パン・表現等) を
        漏れなく WinMM MIDI デバイスへ先行送信し、主旋律パートの GM ハーモニカ音色 (Program 22) を確実に維持します。
        """
        if not self.device_opened or not winmm:
            return

        latest_programs = {}
        latest_ccs = {}
        tracked_cc_nums = {0, 1, 2, 7, 10, 11, 32, 64}

        # 1. 全トラック・チャンネルの初期音色 (timeline.tracks_info およびイベント全体の先頭PC) を事前同期
        if hasattr(self, "timeline") and self.timeline:
            for info in getattr(self.timeline, "tracks_info", []):
                t_idx = info.get("track_idx", 0)
                if not self.is_track_audible(t_idx):
                    continue
                ch = info.get("channel", 0) & 0x0F
                prog = info.get("program")
                if prog is not None:
                    latest_programs[ch] = prog & 0x7F

        for ev in self.events:
            if ev.get("type") == "program_change":
                ch = ev.get("channel", 0) & 0x0F
                t_idx = ev.get("track_idx", 0)
                if not self.is_track_audible(t_idx):
                    continue
                if ch not in latest_programs:
                    latest_programs[ch] = (ev.get("dw_msg", 0) >> 8) & 0x7F

        target = max(0.0, float(target_sec))

        for ev in self.events:
            if ev["sec"] > target:
                break
            t_idx = ev.get("track_idx", 0)
            if not self.is_track_audible(t_idx):
                continue

            t_type = ev.get("type")
            ch = ev.get("channel", 0) & 0x0F
            dw = ev.get("dw_msg", 0)

            if t_type == "program_change":
                prog = (dw >> 8) & 0x7F
                latest_programs[ch] = prog
            elif t_type == "control_change":
                cc_num = (dw >> 8) & 0x7F
                cc_val = (dw >> 16) & 0x7F
                if cc_num in tracked_cc_nums:
                    latest_ccs[(ch, cc_num)] = cc_val

        # 主旋律パートのハーモニカ音色強制 (Program 22) を確実に設定
        if self.force_main_harmonica:
            latest_programs[self.main_channel] = 22

        # 主要コントロール (CC) 送信
        for (ch, cc_num), cc_val in sorted(latest_ccs.items()):
            try:
                dw = (0xB0 | ch) | (cc_num << 8) | (cc_val << 16)
                winmm.midiOutShortMsg(self.h_midi_out, dw)
            except Exception:
                pass

        # プログラムチェンジ (楽器音色) 送信
        for ch, prog in sorted(latest_programs.items()):
            try:
                dw = (0xC0 | ch) | (prog << 8)
                winmm.midiOutShortMsg(self.h_midi_out, dw)
            except Exception:
                pass

    def set_main_tracks(self, main_indices: list, accomp_indices: list = None):
        """主旋律対象トラック群（複数可）変更"""
        self.main_track_indices = [int(i) for i in main_indices] if main_indices else [0]
        self.main_track_idx = self.main_track_indices[0]
        if accomp_indices is not None:
            self.accomp_track_indices = [int(i) for i in accomp_indices]
        self.all_notes_off()
        if hasattr(self, "timeline") and self.timeline:
            self.load_timeline(self.timeline)
        self.sync_midi_channel_states(self._last_cur_sec if self._last_cur_sec >= 0 else 0.0)

    def set_main_track(self, track_idx: int):
        """主旋律対象トラック変更 (単一・後方互換)"""
        self.set_main_tracks([int(track_idx)])

    def set_transpose(self, semitones: int, transpose_accomp: bool = None):
        """移調 (半音 -24 〜 +24) 設定 & 待機イベントのdw_msg高速再コンパイル"""
        self.transpose_semitones = int(semitones)
        if transpose_accomp is not None:
            self.transpose_accomp = bool(transpose_accomp)
        self.all_notes_off()
        for ev in self.events:
            raw = ev.get("raw_note")
            if raw is not None:
                ch = ev["channel"]
                vel = ev.get("velocity", 64)
                t_type = ev["type"]
                is_main = ev.get("is_main", False)
                should_transpose = is_main or (getattr(self, "transpose_accomp", True) and ch != 9)
                p_eff = min(127, max(0, raw + (self.transpose_semitones if should_transpose else 0)))
                ev["pitch"] = p_eff
                if t_type == "note_on":
                    ev["dw_msg"] = (0x90 | ch) | (p_eff << 8) | ((vel & 0x7F) << 16)
                elif t_type == "note_off":
                    ev["dw_msg"] = (0x80 | ch) | (p_eff << 8) | (0 << 16)

    def set_metronome_mode(self, mode: str):
        """メトロノームパターン変更 ('なし', '標準（頭拍強調）', '小節頭のみ', '全拍均一')"""
        self.metronome_mode = str(mode)

    def set_count_in(self, measures: int):
        """前奏カウント小節数 (0, 1, 2) の設定とイベント再構築"""
        self.count_in_measures = max(0, int(measures))
        self._rebuild_metro_events()

    def _rebuild_metro_events(self):
        """カウントイン拍と本編メトロノームイベントを合算構築"""
        base_events = self.timeline.get_metronome_ticks() if (hasattr(self, "timeline") and self.timeline and hasattr(self.timeline, "get_metronome_ticks")) else []
        if self.count_in_measures > 0 and hasattr(self, "timeline") and self.timeline:
            num = getattr(self.timeline, "time_sig_num", 4)
            den = getattr(self.timeline, "time_sig_den", 4)
            bpm = getattr(self.timeline, "default_bpm", 120.0)
            beat_dur = (60.0 / bpm) * (4.0 / den)
            total_beats = self.count_in_measures * num
            total_dur = total_beats * beat_dur
            ci_events = []
            for b in range(total_beats):
                t = -total_dur + b * beat_dur
                ci_events.append({
                    "sec": t,
                    "is_accent": (b % num == 0),
                    "measure": -(self.count_in_measures - (b // num)),
                    "beat": (b % num) + 1,
                    "is_count_in": True,
                })
            self.metro_events = ci_events + base_events
        else:
            self.metro_events = base_events
        self.metro_secs = [m["sec"] for m in self.metro_events]
        self._next_metro_idx = 0

    def set_loop_range(self, a_sec: float = 0.0, b_sec: float = None, enabled: bool = True):
        """A-Bループ範囲設定"""
        self.loop_a_sec = max(0.0, float(a_sec)) if a_sec is not None else 0.0
        self.loop_b_sec = float(b_sec) if b_sec is not None else None
        self.loop_enabled = bool(enabled)

    def seek(self, target_sec: float = 0.0, is_loop_ci: bool = False):
        """シーク・曲頭戻し・ループ折り返し時に直接再生位置を再同期"""
        self.all_notes_off()
        sec = float(target_sec)
        self._last_cur_sec = sec
        if not is_loop_ci:
            self._suppress_notes_until_sec = None
            self._loop_ci_events = []
            target_note_sec = max(0.0, sec)
            target_metro_sec = sec - 0.04
        else:
            # ループ周回カウントイン中は、A点（_suppress_notes_until_sec）以前のノーツ発音を抑制
            suppress_sec = self._suppress_notes_until_sec if self._suppress_notes_until_sec is not None else sec
            target_note_sec = max(0.0, suppress_sec)
            target_metro_sec = suppress_sec - 0.04

        self._next_ev_idx = bisect.bisect_left(self.event_secs, target_note_sec)
        # 1拍目落ち防止: sec 直上にあるイベント（境界イベント）を取りこぼさないよう、0.04秒の先行マージンでbisect
        self._next_metro_idx = bisect.bisect_left(self.metro_secs, target_metro_sec)
        self.sync_midi_channel_states(target_note_sec)

    def _get_ui_beep_sound(self):
        """v2.1仕様の1600Hz電子音「ピッ」効果音オブジェクトを生成・返却"""
        if getattr(self, "_ui_beep_sound", None) is None:
            try:
                import numpy as np
                import pygame
                if pygame.mixer.get_init() is None:
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
                sr = 44100
                duration = 0.045
                t = np.arange(0, duration, 1.0 / sr)
                # 1600Hzの純音（v2.1踏襲の電子音「ピッ」）
                wave_data = np.sin(2.0 * np.pi * 1600.0 * t)

                # 先頭3ms、末尾12msのフェードでクリックノイズ防止
                att_len = int(sr * 0.003)
                wave_data[:att_len] *= np.linspace(0.0, 1.0, att_len)
                fade_len = int(sr * 0.012)
                wave_data[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)

                pcm = (wave_data * 12000).astype(np.int16)
                stereo = np.column_stack((pcm, pcm))
                self._ui_beep_sound = pygame.mixer.Sound(buffer=stereo)
            except Exception as e:
                print(f"[AudioEngine Warning] UI切り替え電子音生成失敗: {e}")
                self._ui_beep_sound = None
        return self._ui_beep_sound

    def play_ui_click(self):
        """運指変更・UIクリック時の即応フィードバック音 (v2.1仕様の1600Hz電子音「ピッ」)"""
        try:
            snd = self._get_ui_beep_sound()
            if snd:
                vol = max(0.1, min(1.0, getattr(self, "volume_ratio", 1.0) * 0.45))
                snd.set_volume(vol)
                snd.play()
                return
        except Exception:
            pass

        # pygameフォールバック (万一pygameが利用できない場合)
        if self.device_opened and winmm and self.h_midi_out:
            try:
                winmm.midiOutShortMsg(self.h_midi_out, 0x99 | (76 << 8) | (85 << 16))
            except Exception:
                pass

    # =========================================================================
    # 高精度バックグラウンド再生ループ
    # =========================================================================
    def _audio_worker_loop(self):
        """OS高分解能1msタイマーによる発音ジッターゼロのバックグラウンドループ"""
        was_playing = False

        while self.is_running:
            state = self.clock.get_state()
            is_playing = (state == SharedClockBridge.STATE_PLAYING)

            if not is_playing:
                if was_playing:
                    self.all_notes_off()
                    was_playing = False
                time.sleep(0.015)
                continue

            # 現在時刻取得 (OSナノ秒カウンタ)
            cur_sec = self.clock.get_current_base_sec(lookahead_sec=0.0)

            if not was_playing:
                was_playing = True
                self.all_notes_off()
                self.sync_midi_channel_states(max(0.0, cur_sec))
                self._next_ev_idx = bisect.bisect_left(self.event_secs, max(0.0, cur_sec))
                self._next_metro_idx = bisect.bisect_left(self.metro_secs, cur_sec - 0.04)
                self._last_cur_sec = cur_sec

            # シーク・ジャンプ・ループ折り返しの検知 (時刻が戻った、または0.08秒以上急激に飛んだ場合)
            if cur_sec < self._last_cur_sec or abs(cur_sec - self._last_cur_sec) > 0.08:
                self.all_notes_off()
                self._next_ev_idx = bisect.bisect_left(self.event_secs, max(0.0, cur_sec))
                self._next_metro_idx = bisect.bisect_left(self.metro_secs, cur_sec - 0.04)
                self.sync_midi_channel_states(max(0.0, cur_sec))

            self._last_cur_sec = cur_sec

            # A-Bループ自動折り返し判定 (1ms高分解能タイマーによる音響・描画の完全同時ラップ)
            end_sec = self.loop_b_sec if (self.loop_b_sec is not None and self.loop_b_sec > 0) else self.total_duration_sec
            if self.loop_enabled and end_sec > 0 and cur_sec >= end_sec:
                wrap_to = self.loop_a_sec if self.loop_a_sec is not None else 0.0
                speed = self.clock.get_speed_ratio()
                self.all_notes_off()

                # カウントイン小節数が設定されている場合、A点直前に予備拍（カウントイン）を実行
                num = getattr(self.timeline, "time_sig_num", 4) if (hasattr(self, "timeline") and self.timeline) else 4
                den = getattr(self.timeline, "time_sig_den", 4) if (hasattr(self, "timeline") and self.timeline) else 4
                bpm = getattr(self.timeline, "default_bpm", 120.0) if (hasattr(self, "timeline") and self.timeline) else 120.0
                beat_dur = (60.0 / bpm) * (4.0 / den)
                ci_beats = self.count_in_measures * num if self.count_in_measures > 0 else 0
                ci_dur = ci_beats * beat_dur

                if ci_dur > 0:
                    start_sec = wrap_to - ci_dur
                    self._suppress_notes_until_sec = wrap_to
                    self._loop_ci_events = []
                    for b in range(ci_beats):
                        t = start_sec + b * beat_dur
                        self._loop_ci_events.append({
                            "sec": t,
                            "is_accent": (b % num == 0),
                            "measure": -(self.count_in_measures - (b // num)),
                            "beat": (b % num) + 1,
                            "is_count_in": True,
                        })
                    self.clock.set_anchor(start_sec, speed_ratio=speed, state=SharedClockBridge.STATE_PLAYING)
                    self.seek(start_sec, is_loop_ci=True)
                else:
                    self._suppress_notes_until_sec = None
                    self._loop_ci_events = []
                    self.clock.set_anchor(wrap_to, speed_ratio=speed, state=SharedClockBridge.STATE_PLAYING)
                    self.seek(wrap_to)

                if callable(self.on_loop_wrapped_callback):
                    try:
                        self.on_loop_wrapped_callback()
                    except Exception:
                        pass
                continue

            # 非ループ時の曲末尾自動停止
            if not self.loop_enabled and self.total_duration_sec > 0 and cur_sec >= self.total_duration_sec + 0.25:
                self.all_notes_off()
                self.clock.stop()
                if callable(self.on_playback_finished_callback):
                    try:
                        self.on_playback_finished_callback()
                    except Exception:
                        pass
                time.sleep(0.015)
                continue

            use_synth = ("内蔵" in self.guide_audio_engine or "シンセ" in self.guide_audio_engine or not self.device_opened)

            # メトロノーム・カウントイン発音処理 (WinMM Ch.10 / 内蔵シンセ対応)
            if not self.is_muted:
                # 1. ループ周回時カウントイン拍の処理
                if self._loop_ci_events:
                    while self._loop_ci_events and self._loop_ci_events[0]["sec"] <= cur_sec:
                        m_ev = self._loop_ci_events.pop(0)
                        is_accent = m_ev.get("is_accent", False)
                        if use_synth:
                            if not hasattr(self, "synth_click_hi") or self.synth_click_hi is None:
                                self.init_internal_synth()
                            snd = self.synth_click_hi if is_accent else self.synth_click_lo
                            if snd:
                                try:
                                    snd.play()
                                except Exception:
                                    pass
                        elif self.device_opened and winmm:
                            note = 76 if is_accent else 77
                            vel = 110 if is_accent else 85
                            try:
                                winmm.midiOutShortMsg(self.h_midi_out, 0x99 | (note << 8) | (vel << 16))
                            except Exception:
                                pass

                # 2. 通常のメトロノーム・曲頭カウントインの処理 (周回カウントイン中は抑制)
                if not self._loop_ci_events and self._suppress_notes_until_sec is None:
                    while self._next_metro_idx < len(self.metro_events):
                        m_ev = self.metro_events[self._next_metro_idx]
                        if m_ev["sec"] <= cur_sec:
                            is_ci = m_ev.get("is_count_in", False)
                            if is_ci or self.metronome_mode != "なし":
                                is_accent = m_ev.get("is_accent", False)
                                play_metro = True
                                if not is_ci:
                                    if self.metronome_mode == "小節頭のみ" and not is_accent:
                                        play_metro = False
                                    elif self.metronome_mode == "全拍均一":
                                        is_accent = False

                                if play_metro:
                                    if use_synth:
                                        if not hasattr(self, "synth_click_hi") or self.synth_click_hi is None:
                                            self.init_internal_synth()
                                        snd = self.synth_click_hi if is_accent else self.synth_click_lo
                                        if snd:
                                            try:
                                                snd.play()
                                            except Exception:
                                                pass
                                    elif self.device_opened and winmm:
                                        note = 76 if is_accent else 77
                                        vel = 110 if is_accent else 85
                                        try:
                                            winmm.midiOutShortMsg(self.h_midi_out, 0x99 | (note << 8) | (vel << 16))
                                        except Exception:
                                            pass
                            self._next_metro_idx += 1
                        else:
                            break

            with self._lock:
                if not self.events or self._next_ev_idx >= len(self.events):
                    time.sleep(0.005)
                    continue

                # 現在時刻に達したイベントを一括送信
                if self._suppress_notes_until_sec is not None:
                    if cur_sec < self._suppress_notes_until_sec:
                        time.sleep(0.005)
                        continue
                    else:
                        # A点到達：抑止期間中の過去イベントを一斉発音しないようA点インデックスへ同期
                        self._next_ev_idx = bisect.bisect_left(self.event_secs, max(0.0, self._suppress_notes_until_sec))
                        self._suppress_notes_until_sec = None

                while self._next_ev_idx < len(self.events):
                    ev = self.events[self._next_ev_idx]
                    if ev["sec"] <= cur_sec:
                        if not self.is_muted and not getattr(self, "is_midi_notes_muted", False) and self.is_track_audible(ev["track_idx"]):
                            if ev.get("is_muted_note", False):
                                # 除外されたノーツは主旋律としては発音しない
                                self._next_ev_idx += 1
                                continue
                            if use_synth:
                                t_type = ev.get("type")
                                pitch = ev.get("pitch")
                                if t_type == "note_on" and ev.get("velocity", 0) > 0:
                                    self.synth_note_on(pitch, ev.get("velocity", 80))
                                elif t_type in ("note_off", "note_on"):
                                    self.synth_note_off(pitch)
                            elif self.device_opened and winmm:
                                try:
                                    winmm.midiOutShortMsg(self.h_midi_out, ev["dw_msg"])
                                except Exception:
                                    pass
                        self._next_ev_idx += 1
                    else:
                        break

                # 次のイベントまでの待機時間計算
                if self._next_ev_idx < len(self.events):
                    next_sec = self.events[self._next_ev_idx]["sec"]
                    speed = self.clock.get_speed_ratio()
                    remaining_sec = (next_sec - cur_sec) / speed if speed > 0 else 0.001

                    if remaining_sec > 0.006:
                        time.sleep(0.002)
                    elif remaining_sec > 0.0015:
                        time.sleep(0.0005)
                    else:
                        # 1.5ms以内は極小スピンで超高精度同期
                        pass
                else:
                    time.sleep(0.005)




# =============================================================================
# Step 6: マイク録音 (AudioRecorder) ＆ ハーモニカ用リバーブエフェクト
# =============================================================================

class AudioRecorder:
    """pygame._sdl2.audio を用いた低遅延・高音質マイク録音クラス"""

    def __init__(self):
        self.device = None
        self.buffer = bytearray()
        self.is_recording = False
        self.sample_rate = 44100
        self.channels = 1
        self.start_time = 0.0
        self.last_recorded_path = None
        self.last_recorded_dur = 0.0

    @staticmethod
    def get_input_devices():
        """接続されているマイク・オーディオインターフェースの一覧を取得"""
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            import pygame._sdl2.audio as sdl2_audio
            names = sdl2_audio.get_audio_device_names(True)
            return list(names) if names else []
        except Exception as e:
            print(f"[AudioRecorder] デバイス一覧取得失敗: {e}")
            return []

    def start_recording(self, device_name=None, sample_rate=44100, channels=1):
        """マイク録音を開始 (PCM16 バッファ蓄積)"""
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            import pygame._sdl2.audio as sdl2_audio

            self.buffer = bytearray()
            self.sample_rate = int(sample_rate)
            self.channels = 1 if channels == 1 else 2

            dev_target = None
            if device_name and "既定" not in device_name and "標準" not in device_name:
                dev_target = device_name

            def _callback(audiodevice, memoryview_obj):
                if self.is_recording:
                    self.buffer.extend(memoryview_obj)

            self.device = sdl2_audio.AudioDevice(
                dev_target,
                True,  # iscapture
                self.sample_rate,
                sdl2_audio.AUDIO_S16,
                self.channels,
                1024,  # chunksize
                0,     # allowed_changes
                _callback
            )
            self.is_recording = True
            self.start_time = time.time()
            self.device.pause(0)
            return True
        except Exception as e:
            print(f"[AudioRecorder] 録音開始失敗: {e}")
            self.is_recording = False
            self.device = None
            return False

    def stop_recording(self, output_wav_path, trim_start_sec: float = 0.0):
        """録音を停止し、WAVファイルとして保存（trim_start_sec > 0 の場合は前奏カウントイン分を自動トリム）"""
        self.is_recording = False
        if self.device:
            try:
                self.device.pause(1)
                self.device.close()
            except Exception:
                pass
            self.device = None

        if len(self.buffer) == 0:
            return None, 0.0

        try:
            import wave
            out_abs = os.path.abspath(output_wav_path)
            os.makedirs(os.path.dirname(out_abs), exist_ok=True)

            bytes_per_sample = self.channels * 2
            trim_bytes = int(round(max(0.0, float(trim_start_sec)) * self.sample_rate)) * bytes_per_sample
            trim_bytes = (trim_bytes // bytes_per_sample) * bytes_per_sample

            raw_bytes = bytes(self.buffer)
            if 0 < trim_bytes < len(raw_bytes):
                save_data = raw_bytes[trim_bytes:]
            elif trim_bytes >= len(raw_bytes):
                save_data = b""
            else:
                save_data = raw_bytes

            if len(save_data) == 0:
                return None, 0.0

            with wave.open(out_abs, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(save_data)

            dur = len(save_data) / float(self.sample_rate * self.channels * 2)
            self.last_recorded_path = out_abs
            self.last_recorded_dur = dur
            return out_abs, dur
        except Exception as e:
            print(f"[AudioRecorder] WAV保存失敗: {e}")
            return None, 0.0

    def get_elapsed_sec(self):
        """録音中の経過秒数を取得"""
        if self.is_recording:
            return time.time() - self.start_time
        return 0.0


def get_reverb_filter_arg(reverb_type="ルーム (自然な部屋鳴り)", wet_pct=35):
    """FFmpeg aecho フィルター文字列を生成 (動画書き出し用)"""
    w = max(0.0, min(100.0, float(wet_pct))) / 100.0
    in_gain = max(0.2, 1.0 - 0.25 * w)
    out_gain = min(0.95, max(0.1, 0.35 + 0.55 * w))

    if "ホール" in reverb_type:
        delays = "80|140|210|320"
        decays = f"{max(0.01, 0.50*w):.2f}|{max(0.01, 0.40*w):.2f}|{max(0.01, 0.30*w):.2f}|{max(0.01, 0.20*w):.2f}"
    elif "プレート" in reverb_type:
        delays = "25|45|75|110|160"
        decays = f"{max(0.01, 0.55*w):.2f}|{max(0.01, 0.45*w):.2f}|{max(0.01, 0.35*w):.2f}|{max(0.01, 0.25*w):.2f}|{max(0.01, 0.15*w):.2f}"
    else:  # ルーム
        delays = "35|55|80"
        decays = f"{max(0.01, 0.35*w):.2f}|{max(0.01, 0.25*w):.2f}|{max(0.01, 0.15*w):.2f}"

    return f"aecho={in_gain:.2f}:{out_gain:.2f}:{delays}:{decays}"


def apply_harmonica_reverb_numpy(input_wav_path, output_wav_path, reverb_type="ルーム (自然な部屋鳴り)", wet_pct=35):
    """
    Python/NumPy による高速かつ高品質なリバーブ付加（試聴・即時プレビュー用）。
    FFmpeg未導入や非同期呼び出しを必要とせず、10msオーダーで残響付きWAVを生成します。
    """
    import wave
    import numpy as np

    if not input_wav_path or not os.path.exists(input_wav_path):
        return None

    try:
        with wave.open(input_wav_path, 'rb') as wf:
            n_ch = wf.getnchannels()
            sw = wf.getsampwidth()
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if sw == 2:
            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

        w = max(0.0, min(100.0, float(wet_pct))) / 100.0
        if w < 0.01:
            out_int = (np.clip(data, -0.99, 0.99) * 32767.0).astype(np.int16)
        else:
            if "ホール" in reverb_type:
                delays = [80, 140, 210, 320]
                decays = [0.50 * w, 0.40 * w, 0.30 * w, 0.20 * w]
            elif "プレート" in reverb_type:
                delays = [25, 45, 75, 110, 160]
                decays = [0.55 * w, 0.45 * w, 0.35 * w, 0.25 * w, 0.15 * w]
            else:  # ルーム
                delays = [35, 55, 80]
                decays = [0.35 * w, 0.25 * w, 0.15 * w]

            dry_gain = max(0.2, 1.0 - 0.25 * w)
            max_d_samp = int(max(delays) * sr / 1000.0)

            if n_ch == 1:
                out_len = len(data) + max_d_samp
                out_buf = np.zeros(out_len, dtype=np.float32)
                out_buf[:len(data)] += data * dry_gain
                for d_ms, dec in zip(delays, decays):
                    d_samp = int(d_ms * sr / 1000.0)
                    out_buf[d_samp:d_samp + len(data)] += data * dec
            else:
                samples = len(data) // n_ch
                data_stereo = data.reshape((samples, n_ch))
                out_len = samples + max_d_samp
                out_stereo = np.zeros((out_len, n_ch), dtype=np.float32)
                out_stereo[:samples] += data_stereo * dry_gain
                for d_ms, dec in zip(delays, decays):
                    d_samp = int(d_ms * sr / 1000.0)
                    out_stereo[d_samp:d_samp + samples] += data_stereo * dec
                out_buf = out_stereo.reshape(-1)

            out_buf = np.clip(out_buf, -0.98, 0.98)
            out_int = (out_buf * 32767.0).astype(np.int16)

        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
        with wave.open(output_wav_path, 'wb') as wf:
            wf.setnchannels(n_ch)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(out_int.tobytes())

        return output_wav_path
    except Exception as e:
        print(f"[apply_harmonica_reverb_numpy] エフェクト適用失敗: {e}")
        return None


class AuditionPlayer:
    """pygame.mixer を用いた録音テイク・外部音源の即時試聴管理クラス"""

    def __init__(self):
        self._current_sound = None
        self._current_channel = None
        self._init_mixer()

    def _init_mixer(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        except Exception as e:
            print(f"[AuditionPlayer] mixer初期化失敗: {e}")

    def play(self, file_path: str, volume: float = 1.0, start_sec: float = 0.0):
        self.stop()
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            import pygame
            import wave
            self._init_mixer()
            start_sec = max(0.0, float(start_sec))
            sound_created = False
            if start_sec > 0.05:
                try:
                    with wave.open(file_path, "rb") as wf:
                        sr = wf.getframerate()
                        n_frames = wf.getnframes()
                        start_frame = int(start_sec * sr)
                        if start_frame < n_frames:
                            wf.setpos(start_frame)
                            raw_data = wf.readframes(n_frames - start_frame)
                            self._current_sound = pygame.mixer.Sound(buffer=raw_data)
                            sound_created = True
                except Exception as e:
                    print(f"[AuditionPlayer] シーク再生バッファ抽出失敗: {e}")

            if not sound_created:
                self._current_sound = pygame.mixer.Sound(file_path)
                start_sec = 0.0

            self._current_sound.set_volume(max(0.0, min(1.0, float(volume))))
            self._current_channel = self._current_sound.play()
            self._play_start_time = time.time()
            self._start_offset_sec = start_sec
            return True
        except Exception as e:
            print(f"[AuditionPlayer] 再生失敗: {e}")
            return False

    def get_position_sec(self) -> float:
        """現在の試聴再生位置（秒）を取得"""
        if self.is_playing() and hasattr(self, "_play_start_time"):
            return (time.time() - self._play_start_time) + getattr(self, "_start_offset_sec", 0.0)
        return 0.0

    def stop(self):
        try:
            if self._current_channel:
                self._current_channel.stop()
                self._current_channel = None
            if self._current_sound:
                self._current_sound.stop()
                self._current_sound = None
        except Exception:
            pass

    def is_playing(self) -> bool:
        try:
            if self._current_channel:
                return bool(self._current_channel.get_busy())
        except Exception:
            pass
        return False


# ==============================================================================
# 高音質MIDI物理合成 ＆ 外部音源ロード・ノーマライズ (動画書き出し用)
# ==============================================================================
import wave
import numpy as np


def generate_harmonica_tone(freq, num_samples, sample_rate):
    """倍音ブレンド＋指数エンベロープ＋フェードによる高品位ハーモニカ音波形生成"""
    t = np.arange(num_samples) / sample_rate
    if len(t) == 0:
        return np.array([], dtype=np.float32)

    f0 = np.sin(2.0 * np.pi * freq * t)
    f1 = np.sin(2.0 * np.pi * (2.0 * freq) * t) * 0.35
    f2 = np.sin(2.0 * np.pi * (3.0 * freq) * t) * 0.15
    f3 = np.sin(2.0 * np.pi * (4.0 * freq) * t) * 0.05
    wave_data = f0 + f1 + f2 + f3

    dur = max(0.01, num_samples / sample_rate)
    envelope = np.exp(-1.5 * t / dur)
    wave_data *= envelope

    fade_in_len = min(int(0.015 * sample_rate), len(wave_data))
    fade_out_len = min(int(0.035 * sample_rate), len(wave_data))
    if fade_in_len > 0:
        wave_data[:fade_in_len] *= np.linspace(0.0, 1.0, fade_in_len)
    if fade_out_len > 0:
        wave_data[-fade_out_len:] *= np.linspace(1.0, 0.0, fade_out_len)
    return wave_data


def generate_metronome_click(freq, sample_rate, duration=0.05):
    """疑似ウッドブロック調の高精度パルスクリック音波形を生成"""
    t = np.arange(int(duration * sample_rate)) / sample_rate
    envelope = np.exp(-35.0 * t / duration)
    return np.sin(2.0 * np.pi * freq * t) * envelope * 0.3


def generate_accompaniment_tone(freq, num_samples, sample_rate):
    """伴奏パート用の温かみのあるソフトなエレピ／アコースティック調トーンを生成"""
    t = np.arange(num_samples) / sample_rate
    if len(t) == 0:
        return np.array([], dtype=np.float32)

    f0 = np.sin(2.0 * np.pi * freq * t)
    f1 = np.sin(2.0 * np.pi * (2.0 * freq) * t) * 0.18
    wave_data = (f0 + f1) * 0.45

    dur = max(0.01, num_samples / sample_rate)
    envelope = np.exp(-2.2 * t / dur)
    wave_data *= envelope

    fade_in_len = min(int(0.012 * sample_rate), len(wave_data))
    fade_out_len = min(int(0.030 * sample_rate), len(wave_data))
    if fade_in_len > 0:
        wave_data[:fade_in_len] *= np.linspace(0.0, 1.0, fade_in_len)
    if fade_out_len > 0:
        wave_data[-fade_out_len:] *= np.linspace(1.0, 0.0, fade_out_len)
    return wave_data


def load_external_audio_pcm(filepath, sample_rate=44100):
    """外部オーディオファイルを44.1kHz 16-bit 2chステレオのNumPy配列として読み込み"""
    import subprocess
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f"音源ファイルが見つかりません: {filepath}")

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        cmd = [
            "ffmpeg", "-v", "error",
            "-i", filepath,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "2",
            "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, timeout=30)
        if res.returncode == 0 and len(res.stdout) >= 4:
            n_frames = len(res.stdout) // 4
            pcm = np.frombuffer(res.stdout[:n_frames * 4], dtype=np.int16).reshape(-1, 2).copy()
            return np.ascontiguousarray(pcm, dtype=np.int16)
    except Exception as e:
        print(f"[AudioEngine] FFmpegデコードフォールバック試行: {e}")

    try:
        import pygame
        if pygame.mixer.get_init() is not None:
            snd = pygame.mixer.Sound(filepath)
            arr = pygame.sndarray.array(snd)
            if arr.ndim == 1:
                arr = np.column_stack((arr, arr))
            elif arr.shape[1] > 2:
                arr = arr[:, :2]
            return np.ascontiguousarray(arr, dtype=np.int16)
    except Exception:
        pass

    with wave.open(filepath, 'rb') as wf:
        n_ch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        fr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
        if sampwidth == 2:
            data = np.frombuffer(raw, dtype=np.int16)
        elif sampwidth == 1:
            data = ((np.frombuffer(raw, dtype=np.uint8).astype(np.int16) - 128) << 8)
        else:
            raise ValueError(f"未対応のサンプル幅です: {sampwidth} bytes")
        if n_ch == 1:
            stereo = np.column_stack((data, data))
        else:
            stereo = data.reshape(-1, n_ch)[:, :2]
        if fr != sample_rate and len(stereo) > 0:
            new_len = int(round(len(stereo) * sample_rate / float(fr)))
            x_old = np.linspace(0.0, 1.0, len(stereo))
            x_new = np.linspace(0.0, 1.0, new_len)
            left = np.interp(x_new, x_old, stereo[:, 0]).astype(np.int16)
            right = np.interp(x_new, x_old, stereo[:, 1]).astype(np.int16)
            stereo = np.column_stack((left, right))
        return np.ascontiguousarray(stereo, dtype=np.int16)


def _add_audio_track_to_mix(out_stereo, pcm_data, vol_gain, offset_ms, video_song_start_sec, sec_a_in_song, max_duration, num_samples, sample_rate):
    """任意のPCMステレオ配列をオフセット・ゲイン・端点フェード付きでマスター波形に加算合成"""
    if pcm_data is None or len(pcm_data) == 0 or vol_gain <= 0.0:
        return
    offset_sec = float(offset_ms) / 1000.0
    ext_zero_in_video_sec = video_song_start_sec - sec_a_in_song + offset_sec
    video_song_end_sec = video_song_start_sec + max_duration

    dst_min_sample = int(round(video_song_start_sec * sample_rate))
    dst_max_sample = int(round(min(num_samples, video_song_end_sec * sample_rate)))
    dst_start = max(dst_min_sample, int(round(ext_zero_in_video_sec * sample_rate)))
    src_start = max(0, int(round((dst_start / float(sample_rate) - ext_zero_in_video_sec) * sample_rate)))

    if dst_start >= dst_max_sample:
        return
    avail_src = max(0, len(pcm_data) - src_start)
    avail_dst = max(0, dst_max_sample - dst_start)
    copy_len = min(avail_src, avail_dst)
    if copy_len <= 0:
        return

    ext_slice = (pcm_data[src_start:src_start + copy_len].astype(np.float32) / 32768.0) * vol_gain
    fi = min(int(0.015 * sample_rate), copy_len)
    fo = min(int(0.025 * sample_rate), copy_len)
    if fi > 0:
        ext_slice[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, np.newaxis]
    if fo > 0:
        ext_slice[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)[:, np.newaxis]
    out_stereo[dst_start:dst_start + copy_len] += ext_slice


def synthesize_midi_to_wav(midi_notes, current_bpm, max_duration, is_count_in, is_metro, output_wav_path,
                           time_sig_num=4, time_sig_den=4, count_in_measures=1, measures_timeline=None,
                           metronome_pattern="標準（頭拍強調）", ticks_per_beat=480, sample_rate=44100,
                           tick_to_sec_fn=None, accompaniment_notes=None, part_play_mode="全パート再生",
                           intro_sec=0.0, outro_sec=0.0, ext_audio_pcm=None, ext_audio_mode="頭出し確認 (再生:両方 / 動画:外部のみ)",
                           ext_audio_offset_ms=0, ext_audio_vol_pct=100.0, sec_a_in_song=0.0, yt_limiter=True,
                           mixer_settings: dict = None):
    """
    MIDI演奏情報および外部オーディオ（ミリ秒オフセット・音量%・YouTube上限リミッター対応）から
    高音質PCM WAVファイルを物理合成して出力。
    """
    extended_duration = max(0.5, float(max_duration)) + float(intro_sec) + float(outro_sec) + 0.5
    num_samples = int(extended_duration * sample_rate)
    samples = np.zeros(num_samples, dtype=np.float32)

    has_ext_audio = (ext_audio_pcm is not None and len(ext_audio_pcm) > 0 and "外部音源オフ" not in str(ext_audio_mode) and "ガイド音のみ" not in str(ext_audio_mode))
    include_guide_synth = True
    if has_ext_audio and ("動画:外部のみ" in str(ext_audio_mode) or "外部音源のみ" in str(ext_audio_mode) or "外部伴奏音源" in str(ext_audio_mode) or "伴奏のみ" in str(ext_audio_mode)):
        include_guide_synth = False

    first_time_sig_num = 4
    first_time_sig_den = 4
    if measures_timeline:
        first_time_sig_num = measures_timeline[0].get('num', 4)
        first_time_sig_den = measures_timeline[0].get('den', 4)

    count_in_beats = (count_in_measures * first_time_sig_num) if is_count_in else 0
    count_in_beat_duration = (60.0 / max(1.0, current_bpm)) * (4.0 / max(1.0, first_time_sig_den))
    count_in_duration = count_in_beats * count_in_beat_duration if count_in_beats > 0 else 0.0

    if include_guide_synth:
        # A. カウントイン部分のクリック音合成
        if count_in_beats > 0:
            for beat in range(count_in_beats):
                beat_time = intro_sec + beat * count_in_beat_duration
                is_strong = (beat % first_time_sig_num == 0)
                freq = 1200.0 if is_strong else 800.0
                click_wave = generate_metronome_click(freq, sample_rate, duration=0.05)
                start_sample = int(beat_time * sample_rate)
                end_sample = min(start_sample + len(click_wave), num_samples)
                if 0 <= start_sample < num_samples and end_sample > start_sample:
                    samples[start_sample:end_sample] += click_wave[:end_sample - start_sample]

        # B. 本編メトロノーム部分のクリック音合成
        if is_metro and measures_timeline:
            for m in measures_timeline:
                num = m.get('num', 4)
                den = m.get('den', 4)
                beat_len_ticks = ticks_per_beat * (4.0 / den)
                m_base_time = m.get('start_sec', m.get('start_time', None))

                for b in range(num):
                    if tick_to_sec_fn is not None:
                        beat_tick = m.get('start_tick', 0) + b * beat_len_ticks
                        beat_time_in_midi = tick_to_sec_fn(beat_tick) - sec_a_in_song
                    elif m_base_time is not None:
                        sec_per_tick = 60.0 / (max(1.0, current_bpm) * ticks_per_beat)
                        beat_time_in_midi = (m_base_time - sec_a_in_song) + (b * beat_len_ticks) * sec_per_tick
                    else:
                        beat_tick = m.get('start_tick', 0) + b * beat_len_ticks
                        sec_per_tick = 60.0 / (max(1.0, current_bpm) * ticks_per_beat)
                        beat_time_in_midi = beat_tick * sec_per_tick - sec_a_in_song
                    beat_time = intro_sec + count_in_duration + beat_time_in_midi

                    # 本編メトロノームは曲の開始〜max_duration の間のみ鳴らす（前奏余白や後余白outro_secでは鳴らさない）
                    if beat_time < (intro_sec + count_in_duration) or beat_time >= (intro_sec + count_in_duration + max_duration):
                        continue

                    is_click_playable = True
                    is_strong = (b == 0)
                    if metronome_pattern == "なし":
                        is_click_playable = False
                    elif metronome_pattern == "小節頭のみ":
                        if b != 0:
                            is_click_playable = False
                    elif metronome_pattern == "強調なし全拍":
                        is_strong = False

                    if is_click_playable:
                        freq = 1200.0 if is_strong else 800.0
                        click_wave = generate_metronome_click(freq, sample_rate, duration=0.05)
                        start_sample = int(beat_time * sample_rate)
                        end_sample = min(start_sample + len(click_wave), num_samples)
                        if 0 <= start_sample < num_samples and end_sample > start_sample:
                            samples[start_sample:end_sample] += click_wave[:end_sample - start_sample]

        # C-1. 主旋律ハーモニカ音符の合成
        max_music_sec = intro_sec + count_in_duration + max_duration
        max_music_sample = int(max_music_sec * sample_rate)

        if part_play_mode in ("全パート再生", "主旋律ソロ", "主旋律のみ") and midi_notes:
            for note_data in midi_notes:
                if note_data.get("is_muted", False):
                    continue
                note = note_data.get('note', 60)
                start = note_data.get('start_sec', note_data.get('start_time', 0.0))
                dur = note_data.get('dur_sec', note_data.get('duration', 0.5))

                if (start - sec_a_in_song) >= max_duration:
                    continue

                start_in_video = intro_sec + count_in_duration + (start - sec_a_in_song)
                if start_in_video < 0:
                    continue
                start_sample = max(0, int(start_in_video * sample_rate))
                end_sample = min(int((start_in_video + dur) * sample_rate), max_music_sample, num_samples)
                if start_sample >= max_music_sample or start_sample >= num_samples:
                    continue

                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                target_length = end_sample - start_sample
                if target_length > 0:
                    wave_data = generate_harmonica_tone(freq, target_length, sample_rate)
                    samples[start_sample:end_sample] += wave_data

        # C-2. 伴奏パート音符の合成
        if part_play_mode in ("全パート再生", "伴奏のみ(カラオケ)") and accompaniment_notes:
            for acc_data in accompaniment_notes:
                note = acc_data.get('note', 60)
                start = acc_data.get('start_sec', acc_data.get('start_time', 0.0))
                dur = acc_data.get('dur_sec', acc_data.get('duration', 0.5))
                vel_scale = max(0.2, min(1.0, acc_data.get('velocity', 80) / 100.0))

                if (start - sec_a_in_song) >= max_duration:
                    continue

                start_in_video = intro_sec + count_in_duration + (start - sec_a_in_song)
                if start_in_video < 0:
                    continue
                start_sample = max(0, int(start_in_video * sample_rate))
                end_sample = min(int((start_in_video + dur) * sample_rate), max_music_sample, num_samples)
                if start_sample >= max_music_sample or start_sample >= num_samples:
                    continue

                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                target_length = end_sample - start_sample
                if target_length > 0:
                    acc_wave = generate_accompaniment_tone(freq, target_length, sample_rate) * vel_scale
                    samples[start_sample:end_sample] += acc_wave

        # ガイド音のノーマライズ（最大振幅80%）
        max_val = np.max(np.abs(samples))
        if max_val > 0.0:
            samples = (samples / max_val) * 0.8

    # D. マルチトラック合成または単一トラック出力（ステレオ出力）
    video_song_start_sec = intro_sec + count_in_duration
    out_stereo = np.zeros((num_samples, 2), dtype=np.float32)

    if mixer_settings is not None and isinstance(mixer_settings, dict):
        # 1. Track 3: MIDI内部音源
        if mixer_settings.get("track_midi_enabled", False):
            midi_vol = max(0.0, min(2.5, float(mixer_settings.get("track_midi_vol", 100)) / 100.0))
            out_stereo[:, 0] += samples * midi_vol
            out_stereo[:, 1] += samples * midi_vol

        # 2. Track 1: 外部伴奏音源
        if mixer_settings.get("track_ext_enabled", False):
            ext_path = mixer_settings.get("track_ext_path", "")
            if ext_path and os.path.isfile(ext_path):
                pcm_1 = load_external_audio_pcm(ext_path, sample_rate=sample_rate)
                vol_1 = max(0.0, min(2.5, float(mixer_settings.get("track_ext_vol", 100)) / 100.0))
                off_1 = int(mixer_settings.get("track_ext_offset_ms", 0))
                _add_audio_track_to_mix(out_stereo, pcm_1, vol_1, off_1, video_song_start_sec, sec_a_in_song, max_duration, num_samples, sample_rate)

        # 3. Track 2: マイク録音テイク
        if mixer_settings.get("track_rec_enabled", False):
            rec_path = mixer_settings.get("track_rec_path", "")
            if rec_path and os.path.isfile(rec_path):
                target_rec = rec_path
                if mixer_settings.get("track_rec_reverb", False):
                    rev_p = os.path.splitext(rec_path)[0] + "_reverb.wav"
                    if not os.path.exists(rev_p):
                        apply_harmonica_reverb_numpy(rec_path, rev_p, "ホール (豊かな広がり)", 35)
                    if os.path.exists(rev_p):
                        target_rec = rev_p
                pcm_2 = load_external_audio_pcm(target_rec, sample_rate=sample_rate)
                vol_2 = max(0.0, min(2.5, float(mixer_settings.get("track_rec_vol", 100)) / 100.0))
                off_2 = int(mixer_settings.get("track_rec_offset_ms", 0))
                _add_audio_track_to_mix(out_stereo, pcm_2, vol_2, off_2, video_song_start_sec, sec_a_in_song, max_duration, num_samples, sample_rate)
    elif has_ext_audio:
        if include_guide_synth:
            out_stereo[:, 0] = samples * 0.85
            out_stereo[:, 1] = samples * 0.85
        vol_legacy = max(0.0, min(2.5, float(ext_audio_vol_pct) / 100.0))
        _add_audio_track_to_mix(out_stereo, ext_audio_pcm, vol_legacy, ext_audio_offset_ms, video_song_start_sec, sec_a_in_song, max_duration, num_samples, sample_rate)
    else:
        out_stereo[:, 0] = samples
        out_stereo[:, 1] = samples

    # E. True Peak リミッター & WAV保存
    peak = float(np.max(np.abs(out_stereo)))
    if yt_limiter:
        yt_ceiling = 0.89125  # -1.0 dBFS
        if peak > yt_ceiling:
            out_stereo *= (yt_ceiling / peak)
    else:
        if peak > 1.0:
            out_stereo = np.clip(out_stereo, -1.0, 1.0)

    samples_16 = (out_stereo * 32767.0).astype(np.int16)
    with wave.open(output_wav_path, 'wb') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples_16.tobytes())

    return output_wav_path

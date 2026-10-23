# -*- coding: utf-8 -*-
"""
v3.0/ipc_state.py
GUIプロセスと音響プロセス間でロック・通信遅延ゼロで時刻と発音状態を共有するブリッジ。
WindowsのOSハードウェアカウンタ (QueryPerformanceCounter / time.perf_counter_ns) を基準に
共有メモリ (ctypes Structure / multiprocessing.RawValue) を用いてナノ秒同期します。
"""

import time
import ctypes
from multiprocessing import RawValue, Queue


class _ClockStruct(ctypes.Structure):
    _fields_ = [
        ("playing_state", ctypes.c_int32),     # 0:stopped, 1:playing, 2:paused, 3:count_in
        ("anchor_perf_ns", ctypes.c_int64),    # time.perf_counter_ns() 基準値
        ("anchor_base_sec", ctypes.c_double),  # 基準時点の楽曲経過秒数 (1.0倍速換算)
        ("speed_ratio", ctypes.c_double),      # 再生速度倍率 (例: 1.0)
        ("current_bpm", ctypes.c_double),      # 現在実効BPM
        ("total_duration", ctypes.c_double),   # 楽曲総秒数
        ("active_notes_lo", ctypes.c_uint64),  # Pitch 0〜63 の発音ビットマスク
        ("active_notes_hi", ctypes.c_uint64),  # Pitch 64〜127 の発音ビットマスク
    ]


class SharedClockBridge:
    """GUI描画とリアルタイム音響の完全非同期0ms同期ブリッジ"""
    STATE_STOPPED = 0
    STATE_PLAYING = 1
    STATE_PAUSED = 2
    STATE_COUNT_IN = 3

    def __init__(self):
        self.raw = RawValue(_ClockStruct, 0, time.perf_counter_ns(), 0.0, 1.0, 120.0, 0.0, 0, 0)
        self.cmd_queue = Queue()

    def set_anchor(self, base_sec: float, speed_ratio: float = 1.0, state: int = 1):
        self.raw.anchor_base_sec = float(base_sec)
        self.raw.speed_ratio = max(0.05, float(speed_ratio))
        self.raw.anchor_perf_ns = time.perf_counter_ns()
        self.raw.playing_state = int(state)

    def set_state(self, state: int):
        self.raw.playing_state = int(state)

    def get_state(self) -> int:
        return self.raw.playing_state

    def set_speed_ratio(self, speed_ratio: float):
        # 現在時刻を新アンカーとして速度切り替え時の段差ジャンプを防止
        cur_sec = self.get_current_base_sec(lookahead_sec=0.0)
        self.set_anchor(cur_sec, speed_ratio=speed_ratio, state=self.raw.playing_state)

    def get_speed_ratio(self) -> float:
        return max(0.05, float(self.raw.speed_ratio))

    def set_total_duration(self, duration_sec: float):
        self.raw.total_duration = max(0.0, float(duration_sec))

    def get_total_duration(self) -> float:
        return float(self.raw.total_duration)

    def get_current_base_sec(self, lookahead_sec: float = 0.008) -> float:
        """
        現在の原曲経過秒数を取得（lookahead_sec: 画面提示レイテンシ先読み補正）。
        OSハードウェアカウンタ直接参照により、プロセス間通信遅延 0.0ms で即座に返却。
        """
        state = self.raw.playing_state
        if state in (self.STATE_PLAYING, self.STATE_COUNT_IN):
            elapsed_sec = (time.perf_counter_ns() - self.raw.anchor_perf_ns) * 1e-9
            return self.raw.anchor_base_sec + (elapsed_sec + lookahead_sec) * self.raw.speed_ratio
        return self.raw.anchor_base_sec

    def stop(self):
        """再生停止状態へのリセット"""
        self.set_anchor(0.0, state=self.STATE_STOPPED)
        self.clear_active_notes()

    def set_note_active(self, pitch: int, active: bool):
        if 0 <= pitch < 64:
            mask = ctypes.c_uint64(1 << pitch).value
            if active:
                self.raw.active_notes_lo |= mask
            else:
                self.raw.active_notes_lo &= ~mask
        elif 64 <= pitch < 128:
            mask = ctypes.c_uint64(1 << (pitch - 64)).value
            if active:
                self.raw.active_notes_hi |= mask
            else:
                self.raw.active_notes_hi &= ~mask

    def clear_active_notes(self):
        self.raw.active_notes_lo = 0
        self.raw.active_notes_hi = 0

    def is_pitch_active(self, pitch: int) -> bool:
        if 0 <= pitch < 64:
            return bool(self.raw.active_notes_lo & (1 << pitch))
        elif 64 <= pitch < 128:
            return bool(self.raw.active_notes_hi & (1 << (pitch - 64)))
        return False


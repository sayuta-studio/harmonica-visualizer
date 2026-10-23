# -*- coding: utf-8 -*-
"""
v3.0/midi_timeline.py
MIDIパース・テンポマップ二分探索・小節線生成・クロマチックハーモニカ運指解決データクラス。
描画ループ内での動的計算を排除するため、全ノーツの秒数・X座標・運指情報を事前バインドします。
"""

import os
import bisect
import mido

from harmonica_map import (
    load_song_fingering,
    load_song_profile,
    apply_monophonic_filter,
    SONG_MUTED_NOTES,
    get_note_fingering_for_song,
    is_note_in_range,
    is_note_editable,
    get_note_name,
)
from config import get_note_dest_x, get_portable_path

# デフォルト組み込み高品位クロマチックハーモニカ音階デモ（16進数バイト列）
DEMO_MIDI_HEX = (
    "4d546864000000060001000101e04d54726b0000023f00ff031d31362d486f6c652043204368726f6d61746963204861726d6f6e69636100"
    "ff58040402180800ff5902000000ff510307a12000b0790000640000650000060c00647f00657f00c01600b00764000a40005b00005d0000"
    "ff21010000903c5000b002508267903c00013d5000b0025077903d00013e5000b002508267903e00013f5000b0025077903f0001405000b0"
    "0250826790400001415000b002507790410001425000b00250826790420001435000b002507790430001445000b002508267904400014550"
    "00b002507790450001465000b00250826790460001475000b002507790470001485000b00250835f9048008361485000b002508267904800"
    "01495000b0025077904900014a5000b002508267904a00014b5000b0025077904b00014c5000b002508267904c00014d5000b0025077904d"
    "00014e5000b002508267904e00014f5000b0025077904f0001505000b00250826790500001515000b002507790510001525000b002508267"
    "90520001535000b002507790530001545000b00250835f9054008361545000b00250826790540001555000b002507790550001565000b002"
    "50826790560001575000b002507790570001585000b00250826790580001595000b0025077905900015a5000b002508267905a00015b5000"
    "b0025077905b00015c5000b002508267905c00015d5000b0025077905d00015e5000b002508267905e00015f5000b0025077905f00016050"
    "00b00250835f9060008361625000b002508b1f90620001305000b002507790300001ff2f00"
)

GM_INSTRUMENT_NAMES = {
    0: "Acoustic Grand Piano (ピアノ)",
    1: "Bright Acoustic Piano (ブライトピアノ)",
    2: "Electric Grand Piano (エレピグランド)",
    3: "Honky-tonk Piano (ホンキートンクピアノ)",
    4: "Electric Piano 1 (エレピ1)",
    5: "Electric Piano 2 (エレピ2)",
    6: "Harpsichord (ハープシコード)",
    7: "Clavinet (クラビネット)",
    8: "Celesta (チェレスタ)",
    9: "Glockenspiel (グロッケン)",
    10: "Music Box (オルゴール)",
    11: "Vibraphone (ヴィブラフォン)",
    12: "Marimba (マリンバ)",
    13: "Xylophone (木琴)",
    14: "Tubular Bells (チューブラーベル)",
    15: "Dulcimer (ダルシマー)",
    16: "Drawbar Organ (オルガン)",
    17: "Percussive Organ (パーカッシブオルガン)",
    18: "Rock Organ (ロックオルガン)",
    19: "Church Organ (チャーチオルガン)",
    20: "Reed Organ (リードオルガン)",
    21: "Accordion (アコーディオン)",
    22: "Harmonica (ハーモニカ)",
    23: "Tango Accordion (バンドネオン)",
    24: "Acoustic Guitar Nylon (クラシックギター)",
    25: "Acoustic Guitar Steel (アコギ)",
    26: "Electric Guitar Jazz (ジャズギター)",
    27: "Electric Guitar Clean (エレキギター)",
    28: "Electric Guitar Muted (ミュートギター)",
    29: "Overdriven Guitar (オーバードライブギター)",
    30: "Distortion Guitar (ディストーションギター)",
    31: "Guitar Harmonics (ギターハーモニクス)",
    32: "Acoustic Bass (ウッドベース)",
    33: "Electric Bass Finger (エレキベース)",
    34: "Electric Bass Pick (ピックベース)",
    35: "Fretless Bass (フレットレスベース)",
    36: "Slap Bass 1 (スラップベース1)",
    37: "Slap Bass 2 (スラップベース2)",
    38: "Synth Bass 1 (シンセベース1)",
    39: "Synth Bass 2 (シンセベース2)",
    40: "Violin (バイオリン)",
    41: "Viola (ビオラ)",
    42: "Cello (チェロ)",
    43: "Contrabass (コントラバス)",
    44: "Tremolo Strings (トレモロストリングス)",
    45: "Pizzicato Strings (ピチカート)",
    46: "Orchestral Harp (ハープ)",
    47: "Timpani (ティンパニ)",
    48: "String Ensemble 1 (ストリングス1)",
    49: "String Ensemble 2 (ストリングス2)",
    50: "Synth Strings 1 (シンセストリングス1)",
    51: "Synth Strings 2 (シンセストリングス2)",
    52: "Choir Aahs (コーラス)",
    53: "Voice Oohs (ボイス)",
    54: "Synth Choir (シンセボイス)",
    55: "Orchestra Hit (オーケストラヒット)",
    56: "Trumpet (トランペット)",
    57: "Trombone (トロンボーン)",
    58: "Tuba (チューバ)",
    59: "Muted Trumpet (ミュートトランペット)",
    60: "French Horn (ホルン)",
    61: "Brass Section (ブラスセクション)",
    62: "Synth Brass 1 (シンセブラス1)",
    63: "Synth Brass 2 (シンセブラス2)",
    64: "Soprano Sax (ソプラノサックス)",
    65: "Alto Sax (アルトサックス)",
    66: "Tenor Sax (テナーサックス)",
    67: "Baritone Sax (バリトンサックス)",
    68: "Oboe (オーボエ)",
    69: "English Horn (イングリッシュホルン)",
    70: "Bassoon (ファゴット)",
    71: "Clarinet (クラリネット)",
    72: "Piccolo (ピッコロ)",
    73: "Flute (フルート)",
    74: "Recorder (リコーダー)",
    75: "Pan Flute (パンフルート)",
    76: "Blown Bottle (ボトル)",
    77: "Shakuhachi (尺八)",
    78: "Whistle (口笛/ホイッスル)",
    79: "Ocarina (オカリナ)",
    80: "Lead 1 Square (シンセリード・矩形波)",
    81: "Lead 2 Sawtooth (シンセリード・ノコギリ波)",
    88: "Pad 1 New Age (シンセパッド)",
}

def get_gm_instrument_name(program: int, is_drum: bool = False) -> str:
    if is_drum:
        return "Percussion / Drums (ドラム)"
    if program in GM_INSTRUMENT_NAMES:
        return GM_INSTRUMENT_NAMES[program]
    return f"GM Program #{program + 1}"


class MidiTimelineData:
    """MIDIデータの高速再生・描画用タイムラインコンパイル管理クラス"""

    def __init__(self):
        self.filename = ""
        self.filepath = ""
        self.ticks_per_beat = 480
        self.total_ticks = 0
        self.total_duration_sec = 0.0
        self.default_bpm = 120.0
        self.time_sig_num = 4
        self.time_sig_den = 4

        # テンポマップ
        self.tempo_timeline = []
        self.tempo_start_ticks = []
        self.tempo_base_secs = []

        # 小節マップ
        self.measures_timeline = []

        # ノーツ配列
        self.main_notes = []
        self.accomp_notes = []
        self.tracks_info = []
        self.main_track_idx = 0
        self.main_track_indices = [0]
        self.accomp_track_indices = None

        # 単音化・除外ノーツ表示
        self.monophonic_mode = "すべて有効"
        self.hide_muted_notes = False

        # 現在の楽器・移調
        self.inst_type = "16穴 (64音・C調)"
        self.transpose_semitones = 0
        self.transpose_accomp = True
        self.split_by_channel = False

    def load_demo(self, inst_type="16穴 (64音・C調)"):
        """組み込みデモMIDIを展開してロード"""
        self.inst_type = inst_type
        temp_dir = get_portable_path("temp")
        os.makedirs(temp_dir, exist_ok=True)
        demo_path = os.path.join(temp_dir, "demo_chromatic.mid")
        with open(demo_path, "wb") as f:
            f.write(bytes.fromhex(DEMO_MIDI_HEX))
        self.load_file(demo_path, inst_type=inst_type, display_name="Demo (Chromatic Scale).mid")

    def load_file(self, filepath: str, inst_type="16穴 (64音・C調)", display_name=""):
        self.filepath = filepath
        self.filename = display_name or os.path.basename(filepath)
        self.inst_type = inst_type

        # 曲別プロファイル（運指・除外ノーツ・各種設定）の自動ロード
        prof = {}
        try:
            prof = load_song_profile(filepath)
            if "monophonic_mode" in prof:
                self.monophonic_mode = prof["monophonic_mode"]
            if "hide_muted_notes" in prof:
                self.hide_muted_notes = bool(prof["hide_muted_notes"])
            if "transpose" in prof:
                self.transpose_semitones = int(prof["transpose"])
            if "transpose_accomp" in prof:
                self.transpose_accomp = bool(prof["transpose_accomp"])
            if "inst_type" in prof:
                self.inst_type = prof["inst_type"]
        except Exception as e:
            print(f"[MidiTimeline] load_song_profile warning: {e}")

        mid = mido.MidiFile(filepath)
        self.ticks_per_beat = mid.ticks_per_beat

        # 1. 全トラックのメッセージを絶対Tick付きで収集
        raw_events = []
        for t_idx, track in enumerate(mid.tracks):
            cur_tick = 0
            for msg in track:
                cur_tick += msg.time
                raw_events.append((cur_tick, t_idx, msg))

        raw_events.sort(key=lambda x: x[0])
        self.raw_events = raw_events
        self.total_ticks = raw_events[-1][0] if raw_events else 0

        # 2. テンポタイムライン算出
        tempo_changes = [(0, 500000)]
        for cur_tick, _, msg in raw_events:
            if msg.is_meta and msg.type == 'set_tempo':
                tempo_changes.append((cur_tick, msg.tempo))

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
        self.tempo_start_ticks = [seg["tick"] for seg in self.tempo_timeline]
        self.tempo_base_secs = [seg["base_sec"] for seg in self.tempo_timeline]
        self.default_bpm = round(self.tempo_timeline[0]["bpm"]) if self.tempo_timeline else 120.0
        self.total_duration_sec = self.tick_to_sec(self.total_ticks)

        # 3. 小節タイムライン算出
        sig_changes = [(0, 4, 4)]
        for cur_tick, _, msg in raw_events:
            if msg.is_meta and msg.type == 'time_signature':
                sig_changes.append((cur_tick, msg.numerator, msg.denominator))
        sig_changes.sort(key=lambda x: x[0])
        filtered_sigs = []
        for change in sig_changes:
            if not filtered_sigs or filtered_sigs[-1][0] != change[0]:
                filtered_sigs.append(change)
            else:
                filtered_sigs[-1] = change

        self.time_sig_num = filtered_sigs[0][1] if filtered_sigs else 4
        self.time_sig_den = filtered_sigs[0][2] if filtered_sigs else 4

        self.measures_timeline = []
        m_tick = 0
        sig_idx = 0
        m_num = 1
        while m_tick < max(1, self.total_ticks):
            while (sig_idx + 1 < len(filtered_sigs) and filtered_sigs[sig_idx + 1][0] <= m_tick):
                sig_idx += 1
            num = filtered_sigs[sig_idx][1]
            den = filtered_sigs[sig_idx][2]
            beat_len = int(self.ticks_per_beat * (4.0 / den))
            m_len = beat_len * num
            m_sec = self.tick_to_sec(m_tick)
            self.measures_timeline.append({
                "measure_num": m_num,
                "start_tick": m_tick,
                "end_tick": m_tick + m_len,
                "start_sec": m_sec,
                "num": num,
                "den": den,
            })
            m_tick += m_len
            m_num += 1

        # 4. トラック解析 & 主旋律トラック推論
        playable_tracks = []
        all_channels_in_single_track = set()

        for t_idx, track in enumerate(mid.tracks):
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
                    all_channels_in_single_track.update(ch_counts.keys())

        # Format 0 等で1つのトラック内に複数チャンネルが混在している場合はチャンネル単位でパート分割
        split_by_channel = (len(playable_tracks) == 1 and len(all_channels_in_single_track) > 1)
        if split_by_channel and mid.tracks:
            base_track = mid.tracks[playable_tracks[0]["track_idx"]]
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
                    "is_drum": is_drum,
                    "channels_used": {ch}
                })
        else:
            self.tracks_info = playable_tracks

        self.split_by_channel = split_by_channel

        if not self.tracks_info:
            self.tracks_info = [{
                "track_idx": 0,
                "name": "Track 1",
                "channel": 0,
                "program": 22,
                "instrument_name": get_gm_instrument_name(22),
                "note_count": 0,
                "in_range_count": 0,
                "is_drum": False,
                "channels_used": {0}
            }]

        # 主旋律パートの自動推論（プロファイルに未指定の場合のみ）
        if "main_track_indices" in prof and prof["main_track_indices"]:
            self.main_track_indices = [int(i) for i in prof["main_track_indices"]]
            self.main_track_idx = self.main_track_indices[0]
            if "accomp_track_indices" in prof:
                self.accomp_track_indices = [int(i) for i in prof["accomp_track_indices"]]
        else:
            best_track_idx = self.tracks_info[0]["track_idx"]
            best_score = -1
            for order_i, info in enumerate(self.tracks_info):
                if info["is_drum"] or info["in_range_count"] == 0:
                    score = 0
                else:
                    score = 100
                    if info.get("program") == 22:
                        score += 500  # ハーモニカ音色
                    elif info.get("program") in (21, 23, 64, 65, 66, 68, 71, 73, 79, 80, 81):
                        score += 150  # 旋律系ソロ楽器
                    low_name = info.get("name", "").lower()
                    if any(k in low_name for k in ("harmonica", "melody", "vocal", "main", "lead", "solo", "メロディ", "主旋律", "ハーモニカ")):
                        score += 400
                    score += max(0, 50 - order_i * 5)
                if score > best_score:
                    best_score = score
                    best_track_idx = info["track_idx"]

            self.main_track_idx = best_track_idx
            self.main_track_indices = [best_track_idx]
            self.accomp_track_indices = [
                info["track_idx"] for info in self.tracks_info
                if info["track_idx"] != best_track_idx and not info["is_drum"]
            ]

        # 5. ノーツペアリング (NoteOn <-> NoteOff)
        self._rebuild_notes()

        # 6. 運指・音名・X座標の事前解決バインド
        self.rebind_fingerings(self.inst_type)

    def _rebuild_notes(self):
        """主旋律トラックまたはイベント変更時にノーツを高速ペアリング"""
        if not hasattr(self, "raw_events") or not self.raw_events:
            self.main_notes = []
            self.accomp_notes = []
            return

        active_notes = {}
        parsed_main = []
        parsed_accomp = []

        for cur_tick, t_idx, msg in self.raw_events:
            if msg.is_meta:
                continue
            cur_sec = self.tick_to_sec(cur_tick)
            if msg.type == "note_on" and msg.velocity > 0:
                key = (t_idx, msg.channel, msg.note)
                active_notes[key] = (cur_sec, cur_tick, msg.velocity)
            elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                key = (t_idx, msg.channel, msg.note)
                if key in active_notes:
                    start_s, start_t, vel = active_notes.pop(key)
                    dur_s = max(0.01, cur_sec - start_s)
                    dur_t = max(1, cur_tick - start_t)
                    n_obj = {
                        "raw_note": msg.note,
                        "note": msg.note,
                        "start_sec": start_s,
                        "dur_sec": dur_s,
                        "end_sec": start_s + dur_s,
                        "start_tick": start_t,
                        "dur_tick": dur_t,
                        "velocity": vel,
                        "track_idx": t_idx,
                        "channel": msg.channel,
                    }
                    is_main = (msg.channel in self.main_track_indices) if getattr(self, "split_by_channel", False) else (t_idx in self.main_track_indices)
                    if is_main and 24 <= msg.note <= 98:
                        parsed_main.append(n_obj)
                    elif msg.channel != 9:
                        if self.accomp_track_indices is None or (t_idx in self.accomp_track_indices):
                            parsed_accomp.append(n_obj)

        # 終了しなかったノーツのクローズ
        for (t_idx, ch, note_num), (start_s, start_t, vel) in list(active_notes.items()):
            dur_s = max(0.05, self.total_duration_sec - start_s)
            dur_t = max(1, self.total_ticks - start_t)
            n_obj = {
                "raw_note": note_num,
                "note": note_num,
                "start_sec": start_s,
                "dur_sec": dur_s,
                "end_sec": start_s + dur_s,
                "start_tick": start_t,
                "dur_tick": dur_t,
                "velocity": vel,
                "track_idx": t_idx,
                "channel": ch,
            }
            is_main = (ch in self.main_track_indices) if getattr(self, "split_by_channel", False) else (t_idx in self.main_track_indices)
            if is_main and 24 <= note_num <= 98:
                parsed_main.append(n_obj)
            elif ch != 9:
                if self.accomp_track_indices is None or (t_idx in self.accomp_track_indices):
                    parsed_accomp.append(n_obj)

        self.main_notes = sorted(parsed_main, key=lambda x: (x["start_sec"], x["note"]))
        self.accomp_notes = sorted(parsed_accomp, key=lambda x: (x["start_sec"], x["note"]))

    def set_main_tracks(self, track_indices: list, accomp_indices: list = None):
        """主旋律対象トラック群（複数可）変更＆運指高速再解決"""
        self.main_track_indices = [int(i) for i in track_indices] if track_indices else [0]
        self.main_track_idx = self.main_track_indices[0]
        if accomp_indices is not None:
            self.accomp_track_indices = [int(i) for i in accomp_indices]
        self._rebuild_notes()
        self.rebind_fingerings(self.inst_type)

    def set_main_track(self, track_idx: int):
        """主旋律対象トラック変更＆運指高速再解決 (後方互換)"""
        self.set_main_tracks([int(track_idx)])

    def set_monophonic_mode(self, mode: str):
        """単音化モード（すべて有効／高音優先／低音優先）設定＆再解決"""
        self.monophonic_mode = mode
        self.rebind_fingerings(self.inst_type)

    def set_hide_muted_notes(self, hide: bool):
        """除外ノーツ非表示フラグ設定"""
        self.hide_muted_notes = bool(hide)

    def set_transpose(self, semitones: int, transpose_accomp: bool = None):
        """移調 (半音 -24 〜 +24) 設定＆全ノーツ運指高速再解決"""
        self.transpose_semitones = int(semitones)
        if transpose_accomp is not None:
            self.transpose_accomp = bool(transpose_accomp)
        self.rebind_fingerings(self.inst_type)

    def diagnose_pitch_range(self, inst_type: str = None) -> dict:
        """主旋律ノーツの音域と選択中モデルの音域適合性を診断し、最適な推奨移調量を計算"""
        active_notes = [nd for nd in self.main_notes if not nd.get("is_muted", False)]
        if not active_notes:
            return {"status": "empty", "message": "主旋律ノーツが存在しません"}

        from harmonica_map import get_instrument_range, get_note_name
        target_inst = inst_type or self.inst_type
        inst_min, inst_max = get_instrument_range(target_inst)

        # 現在の移調適用後の実ノート番号
        current_pitches = [nd["note"] for nd in active_notes]
        song_cur_min = min(current_pitches)
        song_cur_max = max(current_pitches)
        song_span = song_cur_max - song_cur_min
        inst_span = inst_max - inst_min

        # 音域外のノーツ
        under_notes = [p for p in current_pitches if p < inst_min]
        over_notes = [p for p in current_pitches if p > inst_max]
        out_cnt = len(under_notes) + len(over_notes)

        res = {
            "status": "ok" if out_cnt == 0 else "out_of_range",
            "out_count": out_cnt,
            "under_count": len(under_notes),
            "over_count": len(over_notes),
            "song_cur_min": song_cur_min,
            "song_cur_max": song_cur_max,
            "song_cur_min_name": get_note_name(song_cur_min),
            "song_cur_max_name": get_note_name(song_cur_max),
            "inst_min": inst_min,
            "inst_max": inst_max,
            "inst_min_name": get_note_name(inst_min),
            "inst_max_name": get_note_name(inst_max),
            "current_transpose": self.transpose_semitones,
            "recommended_shifts": [],
            "target_transposes": [],
            "recommendation_text": "",
        }

        if out_cnt == 0:
            res["recommendation_text"] = "全ノーツが選択中モデルの音域内に収まっています。"
            return res

        # 収まるための追加シフト Δ (current_pitch + Δ ∈ [inst_min, inst_max])
        delta_min = inst_min - song_cur_min
        delta_max = inst_max - song_cur_max

        if delta_min > delta_max:
            res["status"] = "exceeds_instrument"
            res["recommendation_text"] = (
                f"曲の音域（{song_span + 1}半音: {res['song_cur_min_name']}〜{res['song_cur_max_name']}）が"
                f"ハーモニカの対応音域（{inst_span + 1}半音: {res['inst_min_name']}〜{res['inst_max_name']}）を"
                f"超えているため、移調のみでは全音収まりません（16穴モデル等の利用を推奨）。"
            )
            return res

        # 全ノーツが収まる追加シフト
        shifts = []
        if delta_min <= 0 <= delta_max:
            min_abs_shift = 0
        elif delta_min > 0:
            min_abs_shift = delta_min
        else:
            min_abs_shift = delta_max

        if min_abs_shift != 0:
            shifts.append(min_abs_shift)

        # 原曲(0st)からのオクターブ移動 (+12, -12, 0, +24, -24) に対応するシフト
        for target_oct in [12, -12, 0, 24, -24]:
            needed_shift = target_oct - self.transpose_semitones
            if delta_min <= needed_shift <= delta_max and needed_shift not in shifts:
                shifts.append(needed_shift)

        res["recommended_shifts"] = shifts
        res["target_transposes"] = [self.transpose_semitones + s for s in shifts]

        recs = []
        for s in shifts:
            target_t = self.transpose_semitones + s
            sign_s = f"+{s}" if s > 0 else str(s)
            sign_t = f"+{target_t}" if target_t > 0 else str(target_t)
            if abs(target_t) == 12 or target_t == 0:
                oct_label = " (原曲キー)" if target_t == 0 else (" (+1Oct)" if target_t == 12 else " (-1Oct)")
                recs.append(f"{sign_s}半音{oct_label} [移調:{sign_t}st]")
            else:
                recs.append(f"{sign_s}半音 [移調:{sign_t}st]")

        res["recommendation_text"] = f"💡 推奨: {' または '.join(recs)} で全ノーツ演奏可能"
        return res

    def get_out_of_range_count(self) -> int:
        """現在有効な主旋律ノーツの中で音域外となっているノーツ数を取得"""
        cnt = 0
        for nd in self.main_notes:
            if not nd.get("is_muted", False) and not nd.get("in_range", True):
                cnt += 1
        return cnt

    def rebind_fingerings(self, inst_type: str = None):
        """楽器タイプ切替・移調時に全ノーツの運指テーブルおよび事前計算X座標を一括更新"""
        if inst_type is not None:
            self.inst_type = inst_type

        # 1. 主旋律ノーツの移調
        for nd in self.main_notes:
            raw_pitch = nd.get("raw_note", nd["note"])
            pitch = min(127, max(0, raw_pitch + self.transpose_semitones))
            nd["note"] = pitch

        # 2. 伴奏ノーツの移調（transpose_accomp 有効時のみ）
        for nd in self.accomp_notes:
            raw_pitch = nd.get("raw_note", nd["note"])
            if self.transpose_accomp:
                nd["note"] = min(127, max(0, raw_pitch + self.transpose_semitones))
            else:
                nd["note"] = raw_pitch

        # 3. 単音化フィルターおよび個別除外オーバーライドの適用
        apply_monophonic_filter(self.main_notes, self.monophonic_mode, SONG_MUTED_NOTES)

        # 4. 運指・音名・X座標バインド
        for nd in self.main_notes:
            pitch = nd["note"]
            s_tick = nd["start_tick"]
            fing = get_note_fingering_for_song(s_tick, pitch, self.inst_type)
            if not fing:
                fing = {"hole": 1, "action": "吹", "lever": "OFF", "note_name": "C4"}
            nd["fingering"] = fing
            nd["hole"] = fing["hole"]
            nd["action"] = fing["action"]
            nd["lever"] = fing["lever"]
            nd["dest_x_base"] = get_note_dest_x(pitch, self.inst_type, scale=1.0, start_tick=s_tick)
            nd["name_jp"] = get_note_name(pitch, is_japanese=True)
            nd["name_cde"] = get_note_name(pitch, is_japanese=False)
            nd["is_editable"] = is_note_editable(pitch, self.inst_type)
            nd["in_range"] = is_note_in_range(pitch, self.inst_type)

    def tick_to_sec(self, tick: float) -> float:
        """指定Tickをテンポマップに基づき原曲経過秒数へ高速二分探索変換"""
        if not self.tempo_timeline or not self.tempo_start_ticks:
            return float(tick) * (60.0 / (120.0 * self.ticks_per_beat))
        if tick <= 0:
            bpm = max(1.0, self.tempo_timeline[0]["bpm"])
            return float(tick) * (60.0 / (bpm * self.ticks_per_beat))

        idx = bisect.bisect_right(self.tempo_start_ticks, tick) - 1
        if idx < 0:
            idx = 0
        seg = self.tempo_timeline[idx]
        dt = float(tick) - seg["tick"]
        return seg["base_sec"] + dt * (60.0 / (max(1.0, seg["bpm"]) * self.ticks_per_beat))

    def sec_to_tick(self, sec: float) -> float:
        """指定秒数をテンポマップに基づきTickへ高速二分探索変換"""
        if not self.tempo_timeline or not self.tempo_base_secs:
            return float(sec) * (120.0 * self.ticks_per_beat / 60.0)
        if sec <= 0:
            bpm = max(1.0, self.tempo_timeline[0]["bpm"])
            return float(sec) * (bpm * self.ticks_per_beat / 60.0)

        idx = bisect.bisect_right(self.tempo_base_secs, sec) - 1
        if idx < 0:
            idx = 0
        seg = self.tempo_timeline[idx]
        ds = float(sec) - seg["base_sec"]
        return seg["tick"] + ds * (max(1.0, seg["bpm"]) * self.ticks_per_beat / 60.0)

    def get_bpm_at_sec(self, sec: float) -> float:
        """指定秒数における原曲実効BPMを取得"""
        if not self.tempo_timeline or not self.tempo_base_secs:
            return self.default_bpm
        idx = bisect.bisect_right(self.tempo_base_secs, sec) - 1
        if idx < 0:
            idx = 0
        return self.tempo_timeline[idx]["bpm"]

    def get_measure_and_beat(self, cur_sec: float) -> tuple:
        """指定秒数における (小節番号, 拍番号, 拍子分子, 拍子分母, BPM) をO(log M)で高速取得"""
        if not self.measures_timeline:
            return 1, 1, 4, 4, self.default_bpm
        cur_tick = self.sec_to_tick(cur_sec)
        m_start_ticks = [m["start_tick"] for m in self.measures_timeline]
        idx = bisect.bisect_right(m_start_ticks, cur_tick) - 1
        if idx < 0:
            idx = 0
        elif idx >= len(self.measures_timeline):
            idx = len(self.measures_timeline) - 1

        m = self.measures_timeline[idx]
        beat_len = max(1, int(self.ticks_per_beat * (4.0 / m["den"])))
        beat_num = int((cur_tick - m["start_tick"]) / beat_len) + 1
        beat_num = max(1, min(m["num"], beat_num))
        bpm = self.get_bpm_at_sec(cur_sec)
        return m["measure_num"], beat_num, m["num"], m["den"], bpm

    def get_sec_for_measure(self, measure_num: int) -> float:
        """指定小節 (1始まり) の開始秒数を取得"""
        if not self.measures_timeline:
            return 0.0
        idx = max(0, min(len(self.measures_timeline) - 1, measure_num - 1))
        return self.measures_timeline[idx]["start_sec"]

    def get_measure_end_sec(self, measure_num: int) -> float:
        """指定小節 (1始まり) の末尾秒数を取得"""
        if not self.measures_timeline:
            return self.total_duration_sec
        idx = max(0, min(len(self.measures_timeline) - 1, measure_num - 1))
        end_tick = self.measures_timeline[idx]["end_tick"]
        return self.tick_to_sec(end_tick)

    def get_metronome_ticks(self) -> list:
        """全小節・拍ごとのメトロノーム発音秒数リストを事前生成"""
        ticks = []
        if not self.measures_timeline:
            return ticks
        for m in self.measures_timeline:
            num = m["num"]
            den = m["den"]
            beat_len = int(self.ticks_per_beat * (4.0 / den))
            for b in range(num):
                b_tick = m["start_tick"] + b * beat_len
                b_sec = self.tick_to_sec(b_tick)
                ticks.append({
                    "sec": b_sec,
                    "is_accent": (b == 0),
                    "measure": m["measure_num"],
                    "beat": b + 1,
                })
        ticks.sort(key=lambda x: x["sec"])
        return ticks


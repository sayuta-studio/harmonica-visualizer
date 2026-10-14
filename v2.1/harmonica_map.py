# -*- coding: utf-8 -*-
# harmonica_map.py (STEP 4-B: 運指マッピング隔離 ＆ インタラクティブ曲別変え指エディタコア・シ(B3)定義バグ修復版)
# - 【データバグ修復】：「スライド最小化」プリセット内に混入していたシ(B3/59)の誤定義を完全に撤廃・削除。これにより4番穴のシが8番・12番穴と同様に、一貫して左端(吸OFF)へ正しく落ち、美しく整列するよう解決しました。

import os

# デフォルトのメーカー標準運指マッピング (C3〜D7)
DEFAULT_HARMONICA_MAP = {
    48: {"hole": 1, "action": "吹", "lever": "OFF", "note_name": "C3"},
    49: {"hole": 1, "action": "吹", "lever": "ON",  "note_name": "C#3"},
    50: {"hole": 1, "action": "吸", "lever": "OFF", "note_name": "D3"},
    51: {"hole": 1, "action": "吸", "lever": "ON",  "note_name": "D#3"},
    52: {"hole": 2, "action": "吹", "lever": "OFF", "note_name": "E3"},
    53: {"hole": 2, "action": "吸", "lever": "OFF", "note_name": "F3"},
    54: {"hole": 2, "action": "吸", "lever": "ON",  "note_name": "F#3"},
    55: {"hole": 3, "action": "吹", "lever": "OFF", "note_name": "G3"},
    56: {"hole": 3, "action": "吹", "lever": "ON",  "note_name": "G#3"},
    57: {"hole": 3, "action": "吸", "lever": "OFF", "note_name": "A3"},
    58: {"hole": 3, "action": "吸", "lever": "ON",  "note_name": "A#3"},
    59: {"hole": 4, "action": "吸", "lever": "OFF", "note_name": "B3"},
    
    60: {"hole": 5, "action": "吹", "lever": "OFF", "note_name": "C4"},
    61: {"hole": 5, "action": "吹", "lever": "ON",  "note_name": "C#4"},
    62: {"hole": 5, "action": "吸", "lever": "OFF", "note_name": "D4"},
    63: {"hole": 5, "action": "吸", "lever": "ON",  "note_name": "D#4"},
    64: {"hole": 6, "action": "吹", "lever": "OFF", "note_name": "E4"},
    65: {"hole": 6, "action": "吸", "lever": "OFF", "note_name": "F4"},
    66: {"hole": 6, "action": "吸", "lever": "ON",  "note_name": "F#4"},
    67: {"hole": 7, "action": "吹", "lever": "OFF", "note_name": "G4"},
    68: {"hole": 7, "action": "吹", "lever": "ON",  "note_name": "G#4"},
    69: {"hole": 7, "action": "吸", "lever": "OFF", "note_name": "A4"},
    70: {"hole": 7, "action": "吸", "lever": "ON",  "note_name": "A#4"},
    71: {"hole": 8, "action": "吸", "lever": "OFF", "note_name": "B4"},
    
    72: {"hole": 9, "action": "吹", "lever": "OFF", "note_name": "C5"},
    73: {"hole": 9, "action": "吹", "lever": "ON",  "note_name": "C#5"},
    74: {"hole": 9, "action": "吸", "lever": "OFF", "note_name": "D5"},
    75: {"hole": 9, "action": "吸", "lever": "ON",  "note_name": "D#5"},
    76: {"hole": 10, "action": "吹", "lever": "OFF", "note_name": "E5"},
    77: {"hole": 10, "action": "吸", "lever": "OFF", "note_name": "F5"},
    78: {"hole": 10, "action": "吸", "lever": "ON",  "note_name": "F#5"},
    79: {"hole": 11, "action": "吹", "lever": "OFF", "note_name": "G5"},
    80: {"hole": 11, "action": "吹", "lever": "ON",  "note_name": "G#5"},
    81: {"hole": 11, "action": "吸", "lever": "OFF", "note_name": "A5"},
    82: {"hole": 11, "action": "吸", "lever": "ON",  "note_name": "A#5"},
    83: {"hole": 12, "action": "吸", "lever": "OFF", "note_name": "B5"},
    
    84: {"hole": 13, "action": "吹", "lever": "OFF", "note_name": "C6"},
    85: {"hole": 13, "action": "吹", "lever": "ON",  "note_name": "C#6"},
    86: {"hole": 13, "action": "吸", "lever": "OFF", "note_name": "D6"},
    87: {"hole": 13, "action": "吸", "lever": "ON",  "note_name": "D#6"},
    88: {"hole": 14, "action": "吹", "lever": "OFF", "note_name": "E6"},
    89: {"hole": 14, "action": "吸", "lever": "OFF", "note_name": "F6"},
    90: {"hole": 14, "action": "吸", "lever": "ON",  "note_name": "F#6"},
    91: {"hole": 15, "action": "吹", "lever": "OFF", "note_name": "G6"},
    92: {"hole": 15, "action": "吹", "lever": "ON",  "note_name": "G#6"},
    93: {"hole": 15, "action": "吸", "lever": "OFF", "note_name": "A6"},
    94: {"hole": 15, "action": "吸", "lever": "ON",  "note_name": "A#6"},
    95: {"hole": 16, "action": "吸", "lever": "OFF", "note_name": "B6"},
    96: {"hole": 16, "action": "吹", "lever": "OFF", "note_name": "C7"},
    97: {"hole": 16, "action": "吹", "lever": "ON",  "note_name": "C#7"},
    98: {"hole": 16, "action": "吸", "lever": "ON",  "note_name": "D7"},
}

# 異名同音・重複運指に対応する「変え指(Alternative)」マップテーブル
# 🚀【解決】：シ(B3/59)の「吹ON」誤定義を完全に削除しました
ALTERNATIVE_PRESETS = {
    "スライド最小化": {
        53: {"hole": 2, "action": "吸", "lever": "OFF", "note_name": "F3"},  
        65: {"hole": 6, "action": "吸", "lever": "OFF", "note_name": "F4"},  
        77: {"hole": 10, "action": "吸", "lever": "OFF", "note_name": "F5"}, 
        89: {"hole": 14, "action": "吸", "lever": "OFF", "note_name": "F6"}, 
    },
    "スライド優先": {
        60: {"hole": 4, "action": "吸", "lever": "ON",  "note_name": "C4"},   
        72: {"hole": 8, "action": "吸", "lever": "ON",  "note_name": "C5"},   
        84: {"hole": 12, "action": "吸", "lever": "ON",  "note_name": "C6"},  
        64: {"hole": 5, "action": "吸", "lever": "ON",  "note_name": "E4"},   
        76: {"hole": 9, "action": "吸", "lever": "ON",  "note_name": "E5"},
        88: {"hole": 13, "action": "吸", "lever": "ON",  "note_name": "E6"},
    }
}

# インタラクティブ切り替え可能な循環候補パターン定義
FINGERING_CANDIDATES = {
    # --- 中音域・高音域のド（C）の3種循環設定 ---
    60: [ # C4 (5吹OFF / 4吹OFF[隣の吹ド] / 4吸ON[シ#])
        {"hole": 5, "action": "吹", "lever": "OFF", "note_name": "C4"}, # 通常
        {"hole": 4, "action": "吹", "lever": "OFF", "note_name": "C4"}, # 隣の吹ド
        {"hole": 4, "action": "吸", "lever": "ON",  "note_name": "B3"}  # 隣の吸ON
    ],
    72: [ # C5 (9吹OFF / 8吹OFF[隣の吹ド] / 8吸ON[シ#])
        {"hole": 9, "action": "吹", "lever": "OFF", "note_name": "C5"}, # 通常
        {"hole": 8, "action": "吹", "lever": "OFF", "note_name": "C5"}, # 隣の吹ド
        {"hole": 8, "action": "吸", "lever": "ON",  "note_name": "B4"}  # 隣の吸ON
    ],
    84: [ # C6 (13吹OFF / 12吹OFF[隣の吹ド] / 12吸ON[シ#])
        {"hole": 13, "action": "吹", "lever": "OFF", "note_name": "C6"}, # 通常
        {"hole": 12, "action": "吹", "lever": "OFF", "note_name": "C6"}, # 隣の吹ド
        {"hole": 12, "action": "吸", "lever": "ON",  "note_name": "B5"}  # 隣の吸ON
    ],

    # ドのシャープ(C#)の2種循環設定
    61: [ # C#4
        {"hole": 5, "action": "吹", "lever": "ON", "note_name": "C#4"}, # 通常
        {"hole": 4, "action": "吹", "lever": "ON", "note_name": "C#4"}  # 隣の吹ON
    ],
    73: [ # C#5
        {"hole": 9, "action": "吹", "lever": "ON", "note_name": "C#5"}, # 通常
        {"hole": 8, "action": "吹", "lever": "ON", "note_name": "C#5"}  # 隣の吹ON
    ],
    85: [ # C#6
        {"hole": 13, "action": "吹", "lever": "ON", "note_name": "C#6"}, # 通常
        {"hole": 12, "action": "吹", "lever": "ON", "note_name": "C#6"}  # 隣の吹ON
    ],

    # --- ファの異名同音群 ---
    53: [ 
        {"hole": 2, "action": "吸", "lever": "OFF", "note_name": "F3"},
        {"hole": 2, "action": "吹", "lever": "ON",  "note_name": "E3"}
    ],
    65: [ 
        {"hole": 6, "action": "吸", "lever": "OFF", "note_name": "F4"},
        {"hole": 6, "action": "吹", "lever": "ON",  "note_name": "E4"}
    ],
    77: [ 
        {"hole": 10, "action": "吸", "lever": "OFF", "note_name": "F5"},
        {"hole": 10, "action": "吹", "lever": "ON",  "note_name": "E5"}
    ],
    89: [ 
        {"hole": 14, "action": "吸", "lever": "OFF", "note_name": "F6"},
        {"hole": 14, "action": "吹", "lever": "ON",  "note_name": "E6"}
    ]
}

ACTIVE_HARMONICA_MAP = DEFAULT_HARMONICA_MAP.copy()

# 曲ごとの個別カスタム運指ストレージ辞書
SONG_FINGERING_OVERRIDES = {}

# 曲ごとの全体プリセット設定値
CURRENT_SONG_PRESET = "スライド最小化"


def get_song_fingering_path(midi_path):
    if not midi_path:
        return None
    filename = os.path.basename(midi_path)
    name_only, _ = os.path.splitext(filename)
    
    from config import get_portable_path
    fingering_dir = get_portable_path("fingering")
    return os.path.join(fingering_dir, f"{name_only}_fingering.txt")


def load_song_fingering(midi_path):
    global SONG_FINGERING_OVERRIDES, CURRENT_SONG_PRESET
    SONG_FINGERING_OVERRIDES.clear()
    CURRENT_SONG_PRESET = "スライド最小化" 
    
    path = get_song_fingering_path(midi_path)
    if not path or not os.path.exists(path):
        return
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("PRESET:"):
                    CURRENT_SONG_PRESET = line.split(":", 1)[1].strip()
                    continue
                    
                parts = line.split(":")
                if len(parts) == 2:
                    key_parts = parts[0].strip().split("_")
                    if len(key_parts) == 2:
                        tick = int(key_parts[0])
                        note = int(key_parts[1])
                        idx = int(parts[1].strip())
                        SONG_FINGERING_OVERRIDES[(tick, note)] = idx
        print(f"[システム] 曲別運指プロパティを解決しました: {os.path.basename(path)} (Preset: {CURRENT_SONG_PRESET})")
    except Exception as e:
        print(f"[警告] 曲別運指ファイルの解決に失敗しました: {e}")


def save_song_fingering(midi_path):
    path = get_song_fingering_path(midi_path)
    if not path:
        return
        
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# chromatic_harmonica_fingering_config\n")
            f.write(f"PRESET: {CURRENT_SONG_PRESET}\n\n") 
            f.write("# FORMAT -> start_tick_note_val: candidate_index\n")
            for (tick, note), idx in sorted(SONG_FINGERING_OVERRIDES.items()):
                f.write(f"{tick}_{note}: {idx}\n")
        print(f"[システム] 曲別運指プロパティを自動セーブしました: {os.path.basename(path)}")
    except Exception as e:
        print(f"[警告] 曲別運指ファイルの自動セーブに失敗しました: {e}")


def reset_song_fingering(midi_path):
    """現在の曲の個別カスタム運指データ（オーバーライド）をすべてクリアし、設定ファイルも初期状態へリセットします。"""
    global SONG_FINGERING_OVERRIDES
    SONG_FINGERING_OVERRIDES.clear()
    path = get_song_fingering_path(midi_path)
    if path and os.path.exists(path):
        try:
            os.remove(path)
            print(f"[システム] 曲別運指ファイルを削除・初期化しました: {os.path.basename(path)}")
        except Exception as e:
            print(f"[警告] 曲別運指ファイルの初期化に失敗しました: {e}")
            save_song_fingering(midi_path)



def apply_fingering_preset(preset_name, user_custom_overrides=None):
    global ACTIVE_HARMONICA_MAP
    temp_map = DEFAULT_HARMONICA_MAP.copy()
    
    preset_overrides = ALTERNATIVE_PRESETS.get(preset_name, {})
    for note, details in preset_overrides.items():
        temp_map[note] = details
        
    if user_custom_overrides:
        for note, details in user_custom_overrides.items():
            temp_map[note] = details
            
    ACTIVE_HARMONICA_MAP = temp_map


def is_note_in_range(note, inst_type):
    if "バス" in inst_type:
        return 24 <= note <= 62
    elif "標準" in inst_type:
        return 60 <= note <= 98
    else:
        return 48 <= note <= 98


def get_note_fingering(note, inst_type):
    lookup_note = note
    if "バス" in inst_type:
        lookup_note = note + 36
    return ACTIVE_HARMONICA_MAP.get(lookup_note)


def get_note_fingering_for_song(start_tick, note, inst_type):
    lookup_note = note
    if "バス" in inst_type:
        lookup_note = note + 36
        
    # A. 個別クリックの優先解決
    override_idx = SONG_FINGERING_OVERRIDES.get((start_tick, lookup_note))
    if override_idx is not None and lookup_note in FINGERING_CANDIDATES:
        candidates = FINGERING_CANDIDATES[lookup_note]
        if 0 <= override_idx < len(candidates):
            return candidates[override_idx]
            
    # B. 曲ごとの選択プリセットによる自動解決
    preset_overrides = ALTERNATIVE_PRESETS.get(CURRENT_SONG_PRESET, {})
    if lookup_note in preset_overrides:
        return preset_overrides[lookup_note]
        
    # C. 標準
    return DEFAULT_HARMONICA_MAP.get(lookup_note)


def is_note_editable(note, inst_type):
    """
    指定されたnote（MIDI番号）が変更可能（二重枠表示）ノーツであるかを判定します。
    """
    lookup_note = note
    if "バス" in inst_type:
        lookup_note = note + 36
        
    # ファ(F)はオクターブを問わず変更可能
    if lookup_note in [53, 65, 77, 89]:
        return True
        
    # ド(C)およびドのシャープ(C#)の編集判定 (最低・最高音のオクターブ端は保護し固定)
    if "16穴" in inst_type:
        if lookup_note in [60, 72, 84, 61, 73, 85]: 
            return True
    else:
        if lookup_note in [72, 84, 73, 85]: 
            return True
            
    return False


def get_note_name(note, is_japanese=False):
    octave = (note // 12) - 1
    names_eng = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    names_jap = ["ド", "ド#", "レ", "レ#", "ミ", "ファ", "ファ#", "ソ", "ソ#", "ラ", "ラ#", "シ"]
    pitch_class = note % 12
    if is_japanese:
        return names_jap[pitch_class]
    else:
        return f"{names_eng[pitch_class]}{octave}"


def get_hole_4_notes(hole_abs, inst_type):
    """
    指定された絶対穴番号 (1〜16) と楽器タイプに対して、
    教則本準拠の「田の字」4音（左上:吹OFF, 右上:吸OFF, 左下:吹ON, 右下:吸ON）の
    MIDIノート番号辞書を返します。
    """
    oct_idx = (hole_abs - 1) // 4
    rel = (hole_abs - 1) % 4
    base_c = 48 + oct_idx * 12
    if "バス" in str(inst_type):
        base_c -= 36

    if rel == 0:
        return {
            ("吹", "OFF"): base_c + 0,
            ("吸", "OFF"): base_c + 2,
            ("吹", "ON"):  base_c + 1,
            ("吸", "ON"):  base_c + 3,
        }
    elif rel == 1:
        return {
            ("吹", "OFF"): base_c + 4,
            ("吸", "OFF"): base_c + 5,
            ("吹", "ON"):  base_c + 5,
            ("吸", "ON"):  base_c + 6,
        }
    elif rel == 2:
        return {
            ("吹", "OFF"): base_c + 7,
            ("吸", "OFF"): base_c + 9,
            ("吹", "ON"):  base_c + 8,
            ("吸", "ON"):  base_c + 10,
        }
    elif hole_abs == 16:
        return {
            ("吹", "OFF"): base_c + 12,
            ("吸", "OFF"): base_c + 11,
            ("吹", "ON"):  base_c + 13,
            ("吸", "ON"):  base_c + 14,
        }
    else:
        return {
            ("吹", "OFF"): base_c + 12,
            ("吸", "OFF"): base_c + 11,
            ("吹", "ON"):  base_c + 13,
            ("吸", "ON"):  base_c + 12,
        }


# 1音表示モード時の各穴のデフォルト基準吹音MIDIノート番号テーブル（練習画面・動画出力で共通利用）
BLOW_NOTES_MIDI = {
    "16穴": [48, 52, 55, 60, 60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
    "12穴 標準": [60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
    "12穴 バス": [24, 28, 31, 35, 36, 40, 43, 47, 48, 52, 55, 59],
}

# -*- coding: utf-8 -*-
# harmonica_map.py (STEP 4-B: 運指マッピング隔離 ＆ インタラクティブ曲別変え指エディタコア・シ(B3)定義バグ修復版)
# - 【データバグ修復】：「スライド最小化」プリセット内に混入していたシ(B3/59)の誤定義を完全に撤廃・削除。これにより4番穴のシが8番・12番穴と同様に、一貫して左端(吸OFF)へ正しく落ち、美しく整列するよう解決しました。

import os
import json
from config import get_portable_path
import project_manager

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
# エイリアス登録（新名称および旧名称の後方互換）
ALTERNATIVE_PRESETS["スライド最小化 (標準)"] = ALTERNATIVE_PRESETS["スライド最小化"]
ALTERNATIVE_PRESETS["スライド優先 (異名同音)"] = ALTERNATIVE_PRESETS["スライド優先"]
ALTERNATIVE_PRESETS["標準"] = ALTERNATIVE_PRESETS["スライド最小化"]

def normalize_fingering_preset(preset_name: str) -> str:
    """プリセット名を標準表示名へ正規化"""
    if not preset_name:
        return "スライド最小化 (標準)"
    if "優先" in preset_name:
        return "スライド優先 (異名同音)"
    return "スライド最小化 (標準)"

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

def get_candidate_label(cand: dict, idx: int) -> str:
    """運指候補オブジェクトから人間向けの分かりやすいラベル文字列を生成"""
    hole = cand.get("hole", 1)
    act = cand.get("action", "吹")
    lev = cand.get("lever", "OFF")
    note_name = cand.get("note_name", "")

    if idx == 0:
        desc = "標準 / 通常"
    elif "ON" in lev and act == "吸":
        desc = "シ# (異名同音)"
    elif "ON" in lev and act == "吹":
        desc = "ミ# (異名同音)" if ("E" in note_name or "F" in note_name) else "隣の吹ON"
    elif act == "吹":
        desc = "隣の吹ド"
    else:
        desc = "変え指"
    return f"{hole}穴 {act} {lev} [{desc}]"


# 曲ごとの個別カスタム運指ストレージ辞書: (start_tick, note) -> candidate_idx
SONG_FINGERING_OVERRIDES = {}

# 曲ごとの個別ノーツ除外 (Mute/Grayout) オーバーライド辞書: f"{round(start_sec, 3)}_{note}" -> bool (True=除外, False=有効)
SONG_MUTED_NOTES = {}

# 曲ごとの全体プリセット設定値
CURRENT_SONG_PRESET = "スライド最小化"

# 曲ごとの単音化モード: "すべて有効" / "高音優先 (上パート)" / "低音優先 (下パート)"
CURRENT_MONOPHONIC_MODE = "すべて有効"

# 除外ノーツを非表示にするか (True=非表示 / False=半透明グレーアウト表示)
HIDE_MUTED_NOTES = False

# 現在選択中の運指パターン名
CURRENT_ACTIVE_PATTERN_NAME = "標準パターン (基本)"

# 曲ごとの付帯プロファイル（トラック選択、移調、外部音源、ABループ）
CURRENT_SONG_PROFILE_EXTRA = {}


def format_transpose_key_label(transpose_val: int) -> str:
    """移調値を判読しやすいラベルに変換 (例: 0 -> '原曲キー', 2 -> 'Key +2', -3 -> 'Key -3')"""
    try:
        val = int(transpose_val)
    except Exception:
        val = 0
    if val == 0:
        return "原曲キー"
    elif val > 0:
        return f"Key +{val}"
    else:
        return f"Key {val}"


def build_current_pattern_snapshot(transpose: int = 0, transpose_accomp: bool = True) -> dict:
    """現在の運指・除外・移調状態をスナップショット辞書として構築"""
    custom_fg_dict = {f"{tick}_{note}": idx for (tick, note), idx in SONG_FINGERING_OVERRIDES.items()}
    return {
        "preset": CURRENT_SONG_PRESET,
        "monophonic_mode": CURRENT_MONOPHONIC_MODE,
        "hide_muted_notes": HIDE_MUTED_NOTES,
        "custom_fingering": custom_fg_dict,
        "muted_notes": dict(SONG_MUTED_NOTES),
        "transpose": int(transpose),
        "transpose_accomp": bool(transpose_accomp),
    }


def apply_pattern_snapshot(pat_data: dict) -> tuple[int, bool]:
    """運指パターン辞書を展開・適用し、(transpose, transpose_accomp) を返す"""
    global CURRENT_SONG_PRESET, CURRENT_MONOPHONIC_MODE, HIDE_MUTED_NOTES
    global SONG_FINGERING_OVERRIDES, SONG_MUTED_NOTES

    SONG_FINGERING_OVERRIDES.clear()
    for k, v in pat_data.get("custom_fingering", {}).items():
        try:
            t, n = k.split("_", 1)
            SONG_FINGERING_OVERRIDES[(int(t), int(n))] = int(v)
        except Exception:
            pass

    SONG_MUTED_NOTES.clear()
    SONG_MUTED_NOTES.update(pat_data.get("muted_notes", {}))

    if "preset" in pat_data:
        CURRENT_SONG_PRESET = pat_data["preset"]
    if "monophonic_mode" in pat_data:
        CURRENT_MONOPHONIC_MODE = pat_data["monophonic_mode"]
    if "hide_muted_notes" in pat_data:
        HIDE_MUTED_NOTES = bool(pat_data["hide_muted_notes"])

    apply_fingering_preset(CURRENT_SONG_PRESET)

    transpose = int(pat_data.get("transpose", CURRENT_SONG_PROFILE_EXTRA.get("transpose", 0)))
    transpose_accomp = bool(pat_data.get("transpose_accomp", CURRENT_SONG_PROFILE_EXTRA.get("transpose_accomp", True)))
    return transpose, transpose_accomp


def get_song_profile_path(midi_path):
    if not midi_path:
        return None
    return project_manager.get_project_profile_path(midi_path)


def get_song_fingering_path(midi_path):
    if not midi_path:
        return None
    return project_manager.get_project_fingering_txt_path(midi_path)


def load_song_profile(midi_path) -> dict:
    """曲別プロファイル (JSON) をロードし、運指・除外ノーツ・各種設定を復元 (MEDIUM-1)"""
    global SONG_FINGERING_OVERRIDES, SONG_MUTED_NOTES, CURRENT_SONG_PRESET
    global CURRENT_MONOPHONIC_MODE, HIDE_MUTED_NOTES, CURRENT_SONG_PROFILE_EXTRA
    global CURRENT_ACTIVE_PATTERN_NAME

    SONG_FINGERING_OVERRIDES.clear()
    SONG_MUTED_NOTES.clear()
    CURRENT_SONG_PRESET = "スライド最小化"
    CURRENT_MONOPHONIC_MODE = "すべて有効"
    HIDE_MUTED_NOTES = False
    CURRENT_ACTIVE_PATTERN_NAME = "標準パターン (基本)"
    CURRENT_SONG_PROFILE_EXTRA.clear()

    json_path = get_song_profile_path(midi_path)
    # プロジェクト内に無ければ旧 fingering/ の候補も探す
    if not json_path or not os.path.isfile(json_path):
        if midi_path:
            filename = os.path.basename(midi_path)
            name_only, _ = os.path.splitext(filename)
            for old_dir in (get_portable_path("fingering"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "fingering")):
                candidate = os.path.join(old_dir, f"{name_only}_profile.json")
                if os.path.isfile(candidate):
                    json_path = candidate
                    break

    if json_path and os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            CURRENT_SONG_PRESET = data.get("preset", "スライド最小化")
            CURRENT_MONOPHONIC_MODE = data.get("monophonic_mode", "すべて有効")
            HIDE_MUTED_NOTES = bool(data.get("hide_muted_notes", False))

            # 運指オーバーライドの復元
            for k, v in data.get("custom_fingering", {}).items():
                parts = k.split("_")
                if len(parts) == 2:
                    try:
                        SONG_FINGERING_OVERRIDES[(int(parts[0]), int(parts[1]))] = int(v)
                    except ValueError:
                        pass

            # 除外ノーツの復元
            for k, v in data.get("muted_notes", {}).items():
                SONG_MUTED_NOTES[k] = bool(v)

            # 付帯設定の保持
            for key in ("main_track_indices", "accomp_track_indices", "transpose",
                        "transpose_accomp", "inst_type", "ext_audio_path",
                        "ext_offset_ms", "loop_a", "loop_b", "active_take_path",
                        "active_pattern_name", "patterns"):
                if key in data:
                    val = data[key]
                    if key in ("ext_audio_path", "active_take_path") and isinstance(val, str) and val:
                        val = project_manager.from_project_rel_path(val)
                    CURRENT_SONG_PROFILE_EXTRA[key] = val

            if "active_pattern_name" in data and data["active_pattern_name"]:
                CURRENT_ACTIVE_PATTERN_NAME = str(data["active_pattern_name"])
            else:
                CURRENT_ACTIVE_PATTERN_NAME = "標準パターン (基本)"

            print(f"[システム] 曲別プロファイル(JSON)を解決しました: {os.path.basename(json_path)} (Preset: {CURRENT_SONG_PRESET})")
            return data
        except Exception as e:
            print(f"[警告] 曲別プロファイル(JSON)読込エラー: {e}")

    # JSONが存在しない場合はレガシーtxtをロード
    load_song_fingering(midi_path)
    return {}


def _write_song_fingering_txt(midi_path):
    """レガシー互換 _fingering.txt への書き出し内部ヘルパー"""
    path = get_song_fingering_path(midi_path)
    if not path:
        return

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# chromatic_harmonica_fingering_config\n")
            f.write(f"PRESET: {CURRENT_SONG_PRESET}\n\n")
            f.write("# FORMAT -> start_tick_note_val: candidate_index\n")
            for (tick, note), idx in sorted(SONG_FINGERING_OVERRIDES.items()):
                f.write(f"{tick}_{note}: {idx}\n")
    except Exception as e:
        print(f"[警告] 曲別運指ファイルの自動セーブに失敗しました: {e}")


def save_song_profile(midi_path, extra_data: dict = None):
    """曲別プロファイルをJSON形式で保存し、互換txtも出力"""
    global CURRENT_SONG_PROFILE_EXTRA
    if extra_data:
        CURRENT_SONG_PROFILE_EXTRA.update(extra_data)

    json_path = get_song_profile_path(midi_path)
    if json_path:
        try:
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            custom_fg_dict = {f"{tick}_{note}": idx for (tick, note), idx in SONG_FINGERING_OVERRIDES.items()}
            payload = {
                "preset": CURRENT_SONG_PRESET,
                "monophonic_mode": CURRENT_MONOPHONIC_MODE,
                "hide_muted_notes": HIDE_MUTED_NOTES,
                "custom_fingering": custom_fg_dict,
                "muted_notes": dict(SONG_MUTED_NOTES),
                "active_pattern_name": CURRENT_ACTIVE_PATTERN_NAME,
            }
            extra_copy = dict(CURRENT_SONG_PROFILE_EXTRA)
            for k in ("ext_audio_path", "active_take_path"):
                if k in extra_copy and isinstance(extra_copy[k], str) and extra_copy[k]:
                    extra_copy[k] = project_manager.to_project_rel_path(extra_copy[k])
            payload.update(extra_copy)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"[システム] 曲別プロファイル(JSON)を自動保存しました: {os.path.basename(json_path)}")
        except Exception as e:
            print(f"[警告] 曲別プロファイル(JSON)保存エラー: {e}")

    # レガシー互換の _fingering.txt も更新
    _write_song_fingering_txt(midi_path)


def load_song_fingering(midi_path):
    """レガシー _fingering.txt からの読込"""
    global SONG_FINGERING_OVERRIDES, CURRENT_SONG_PRESET
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
        print(f"[システム] レガシー曲別運指プロパティを解決しました: {os.path.basename(path)}")
    except Exception as e:
        print(f"[警告] レガシー曲別運指ファイルの解決に失敗しました: {e}")


def save_song_fingering(midi_path):
    """カスタム運指の保存（JSONプロファイルと互換txtの双方を同期保存）"""
    save_song_profile(midi_path)


def reset_song_fingering(midi_path):
    """現在の曲の個別カスタム運指および除外データをクリア"""
    global SONG_FINGERING_OVERRIDES, SONG_MUTED_NOTES
    SONG_FINGERING_OVERRIDES.clear()
    SONG_MUTED_NOTES.clear()
    if not midi_path:
        return
    txt_path = get_song_fingering_path(midi_path)
    if txt_path and os.path.exists(txt_path):
        try:
            os.remove(txt_path)
        except Exception as e:
            print(f"[警告] 運指ファイル削除エラー: {e}")
    prof_path = get_song_profile_path(midi_path)
    if prof_path and os.path.exists(prof_path):
        try:
            with open(prof_path, "r", encoding="utf-8") as f:
                prof = json.load(f)
            prof["custom_fingering"] = {}
            prof["muted_notes"] = {}
            with open(prof_path, "w", encoding="utf-8") as f:
                json.dump(prof, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] プロファイル更新エラー: {e}")


def apply_monophonic_filter(main_notes: list, mode: str = "すべて有効", custom_muted_dict: dict = None):
    """
    主旋律ノーツリストに対して単音化ルール（高音優先／低音優先）および個別例外オーバーライドを適用し、
    各ノート辞書の 'is_muted' (bool) を設定する。
    """
    if custom_muted_dict is None:
        custom_muted_dict = SONG_MUTED_NOTES

    if not main_notes:
        return

    # 1. 基本ルールによる初期化
    if mode == "すべて有効":
        for nd in main_notes:
            nd["is_muted"] = False
    elif mode in ("高音優先 (上パート)", "低音優先 (下パート)"):
        for nd in main_notes:
            nd["is_muted"] = False

        n_len = len(main_notes)
        for i in range(n_len):
            n1 = main_notes[i]
            s1, e1 = n1["start_sec"], n1["end_sec"]
            p1 = n1["note"]

            for j in range(i + 1, n_len):
                n2 = main_notes[j]
                s2, e2 = n2["start_sec"], n2["end_sec"]
                if s2 >= e1:
                    break

                # 0.03秒以上の重複がある場合のみ重なり音と判定
                overlap = min(e1, e2) - max(s1, s2)
                if overlap >= 0.03:
                    p2 = n2["note"]
                    if p1 == p2:
                        continue
                    if mode == "高音優先 (上パート)":
                        # 低い方をグレーアウト (is_muted = True)
                        if p1 < p2:
                            n1["is_muted"] = True
                        else:
                            n2["is_muted"] = True
                    elif mode == "低音優先 (下パート)":
                        # 高い方をグレーアウト (is_muted = True)
                        if p1 > p2:
                            n1["is_muted"] = True
                        else:
                            n2["is_muted"] = True

    # 2. 個別ノーツの例外オーバーライドの適用 (移調に不変な原曲ノート番号 raw_note をキーとする)
    for nd in main_notes:
        raw_pitch = nd.get("raw_note", nd["note"])
        key = f"{round(nd['start_sec'], 3)}_{raw_pitch}"
        if key in custom_muted_dict:
            nd["is_muted"] = bool(custom_muted_dict[key])




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


def get_instrument_range(inst_type: str) -> tuple:
    """ハーモニカモデルの対応MIDIノート番号範囲 (min_note, max_note) を返却"""
    if not inst_type:
        return (48, 98)
    if "バス" in inst_type:
        return (24, 62)  # C1 (24) 〜 D4 (62)
    elif "14穴" in inst_type:
        return (55, 98)  # G3 (55) 〜 D7 (98)
    elif "12穴" in inst_type or "標準" in inst_type or "48音" in inst_type:
        return (60, 98)  # C4 (60) 〜 D7 (98)
    else:
        return (48, 98)  # C3 (48) 〜 D7 (98) (16穴)


def is_note_in_range(note, inst_type):
    low, high = get_instrument_range(inst_type)
    return low <= note <= high


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
    if "16穴" in inst_type or "14穴" in inst_type:
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
    "14穴": [55, 60, 60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
    "12穴 標準": [60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
    "12穴 バス": [24, 28, 31, 35, 36, 40, 43, 47, 48, 52, 55, 59],
}


def has_custom_fingering() -> bool:
    """現在の曲に個別カスタム運指（変え指オーバーライド）が1件以上設定されているか判定"""
    return len(SONG_FINGERING_OVERRIDES) > 0


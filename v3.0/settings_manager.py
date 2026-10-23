# -*- coding: utf-8 -*-
"""
v3.0/settings_manager.py
Chromatic Harmonica Visualizer v3.0 - ユーザー環境設定マネージャー
- JSON形式による高速・安全な設定保存と読込
- 設定ファイル未存在時の自動デフォルト値補完
"""

import os
import sys
import json
from config import get_portable_path

SETTINGS_FILE = get_portable_path("settings.json")

DEFAULT_SETTINGS = {
    # 楽器・表示
    "inst_type": "16穴 (64音・C調)",
    "trajectory_mode": "3段階 (練習標準)",
    "lang_mode": "ドレミ",
    "aspect_ratio": "16:9",
    "show_grid": True,
    "show_bar_lines": True,
    "show_legend": True,
    "show_hole_num": True,
    "show_notes": True,
    "show_lookahead": True,
    "grid4_mode": "4音グリッド表示",
    "show_grid4": "4音グリッド表示",
    "show_ring": True,
    "show_glow": True,
    "note_opacity": 100,
    "fingering_preset": "スライド最小化",

    # テーマ・カラー
    "color_theme": "ノーマル",
    "color_blow": "#FF5500",
    "color_draw": "#00BFFF",
    "lever_deco_mode": "センターライン (芯線)",

    # 練習・再生
    "speed_ratio": 1.0,
    "fall_speed_ratio": 1.0,
    "volume": 100,
    "part_mode": "全パート再生",
    "force_harmonica": True,
    "loop_enabled": False,
    "transpose": 0,
    "transpose_accomp": True,
    "guide_audio_engine": "Windows標準MIDI (WinMM / 推奨)",

    # メトロノーム・カウントイン
    "metronome_mode": "標準（頭拍強調）",
    "count_in_mode": "1小節",

    # ステップアップ練習
    "stepup_enabled": False,
    "stepup_start_pct": 70,
    "stepup_target_pct": 100,
    "stepup_step_pct": 5,

    # 背景画像 & スキン
    "bg_image_enabled": True,
    "bg_image_path": "",
    "bg_dim_ratio": 60,
    "bg_fit_mode": "中央トリミング (画面いっぱい)",
    "bg_rotation": 0,
    "skin_enabled": True,
    "skin_mouthpiece_path": "",
    "skin_lever_off_path": "",
    "skin_lever_on_path": "",

    # 録音・外部音源・リバーブ (Step 6)
    "rec_device": "",
    "rec_channels": 1,
    "reverb_enabled": False,
    "reverb_type": "ルーム (自然な部屋鳴り)",
    "reverb_wet_pct": 35,
    "ext_audio_path": "",
    "ext_audio_mode": "頭出し確認 (再生:両方 / 動画:外部のみ)",
    "ext_audio_offset_ms": 0,
    "ext_audio_volume": 100,
    "yt_limiter": True,

    # 動画出力設定 (Tab 4)
    "export_range": "全曲",
    "export_resolution": "Full HD (1920x1080)",
    "export_fps": "60 FPS",
    "export_bg_color": "ノーマル (黒)",
    "export_style": "完成動画 (背景・タイトル合成)",
    "export_intro_sec": "0秒",
    "export_outro_sec": "2秒",
    "export_fade_in": True,
    "export_fade_out": True,
    "export_fade_in_sec": 1.5,
    "export_fade_out_sec": 1.5,
    "export_fade_title_mode": "フェード中もタイトル表示",
    "export_title_template": "なし",
    "export_title_text": "",
    "export_credit_text": "",

    # 履歴
    "recent_files": [],
}

# カラーテーマ定義 (吹音, 吸音)
THEME_PRESETS = {
    "ノーマル": ("#FF5500", "#00BFFF"),
    "サクラ": ("#FFB7C5", "#3CB371"),
    "クールネオン": ("#FF007F", "#1E90FF"),
    "モノクロ": ("#FFFFFF", "#7F7F7F"),
}


def load_settings() -> dict:
    """設定ファイルから辞書を読込。存在しない項目はデフォルト値で自動補完"""
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    settings.update(saved)
        except Exception as e:
            print(f"[SettingsManager Warning] Failed to load settings: {e}")
    return settings


def save_settings(settings: dict) -> bool:
    """設定辞書をJSONファイルへ永続化"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[SettingsManager Error] Failed to save settings: {e}")
        return False


def get_recent_files() -> list:
    """最近開いたMIDIファイル履歴リスト (最大10件) を取得"""
    s = load_settings()
    files = s.get("recent_files", [])
    return [p for p in files if os.path.isfile(p)]


def add_recent_file(file_path: str):
    """最近開いたMIDIファイルを履歴の先頭に追加して保存 (最大10件)"""
    if not file_path or not os.path.isfile(file_path):
        return
    norm_path = os.path.normpath(file_path)
    s = load_settings()
    files = s.get("recent_files", [])
    # 既存の同一パスを削除
    files = [p for p in files if os.path.normpath(p) != norm_path]
    files.insert(0, norm_path)
    s["recent_files"] = files[:10]
    save_settings(s)



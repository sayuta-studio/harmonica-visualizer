# -*- coding: utf-8 -*-
"""
v3.0/settings_manager.py
Chromatic Harmonica Visualizer v3.0 - ユーザー環境設定マネージャー
- JSON形式による高速・安全な設定保存と読込
- 設定ファイル未存在時の自動デフォルト値補完
- 練習画面スタイル (practice_visual) と動画出力プリセット (video_presets) の完全分離 (v3.1.0)
"""

import os
import sys
import json
import copy
from config import get_portable_path

SETTINGS_FILE = get_portable_path("settings.json")

# ビジュアル関連の統一キー定義
VISUAL_KEYS = (
    "trajectory_mode", "lang_mode", "color_theme", "color_blow", "color_draw",
    "lever_deco_mode", "note_opacity", "show_notes", "show_lookahead",
    "show_grid", "show_bar_lines", "show_hole_num", "hole_num_style",
    "grid4_mode", "show_ring", "show_glow", "show_legend",
    "bg_image_enabled", "bg_image_path", "bg_dim_ratio", "bg_fit_mode", "bg_rotation",
    "skin_enabled", "skin_mouthpiece_path", "skin_lever_off_path", "skin_lever_on_path",
)

# 練習用標準ビジュアル設定（日常の見やすさ優先）
DEFAULT_PRACTICE_VISUAL = {
    "trajectory_mode": "3段階 (練習標準)",
    "lang_mode": "ドレミ",
    "color_theme": "ノーマル",
    "color_blow": "#FF5500",
    "color_draw": "#00BFFF",
    "lever_deco_mode": "センターライン (芯線)",
    "note_opacity": 100,
    "show_notes": True,
    "show_lookahead": True,
    "show_grid": True,
    "show_bar_lines": True,
    "show_hole_num": True,
    "hole_num_style": "実機標準 (低音ドット付)",
    "grid4_mode": "4音グリッド表示",
    "show_ring": True,
    "show_glow": True,
    "show_legend": True,
    "bg_image_enabled": True,
    "bg_image_path": "",
    "bg_dim_ratio": 60,
    "bg_fit_mode": "中央トリミング (画面いっぱい)",
    "bg_rotation": 0,
    "skin_enabled": True,
    "skin_mouthpiece_path": "",
    "skin_lever_off_path": "",
    "skin_lever_on_path": "",
}

# 公式動画出力プリセット（用途別パッケージ）
DEFAULT_VIDEO_PRESETS = {
    "📱 YouTube Shorts (縦型・解説)": {
        "aspect_ratio": "9:16",
        "export_resolution": "Full HD (1920x1080・推奨)",
        "export_fps": "60 FPS (滑らか・推奨)",
        "export_style": "完成動画 (背景・タイトル合成)",
        "export_bg_color": "ノーマル（黒）",
        "export_intro_sec": "1秒",
        "export_outro_sec": "2秒",
        "export_fade_in": True,
        "export_fade_out": True,
        "export_fade_in_sec": 1.0,
        "export_fade_out_sec": 1.5,
        "export_fade_title_mode": "フェード中もタイトル表示",
        "export_title_template": "イントロ中央＋左上常時",
        "export_title_enabled": True,
        "export_title_duration": 3.5,
        "export_title_exit_mode": "フェードアウトで消える",
        "vertical_layout_mode": "全画面フル展開 (標準Shorts)",
        "audio_quick_mode": "伴奏音源 (外部音源優先)",
        "reverb_enabled": True,
        "yt_limiter": True,
        "export_audio_volume": 100,
        # ビジュアル
        "trajectory_mode": "垂直落下 (穴直上)",
        "lang_mode": "ドレミ",
        "color_theme": "ノーマル",
        "color_blow": "#FF5500",
        "color_draw": "#00BFFF",
        "lever_deco_mode": "センターライン (芯線)",
        "note_opacity": 100,
        "show_notes": True,
        "show_lookahead": True,
        "show_grid": True,
        "show_bar_lines": True,
        "show_hole_num": True,
        "hole_num_style": "実機標準 (低音ドット付)",
        "grid4_mode": "4音グリッド表示",
        "show_ring": True,
        "show_glow": True,
        "show_legend": False,  # 縦長構図のため凡例はOFF
        "bg_image_enabled": True,
        "bg_image_path": "",
        "bg_dim_ratio": 60,
        "bg_fit_mode": "中央トリミング (画面いっぱい)",
        "bg_rotation": 0,
        "skin_enabled": True,
        "skin_mouthpiece_path": "",
        "skin_lever_off_path": "",
        "skin_lever_on_path": "",
    },
    "🎥 演奏解説・レッスン (16:9)": {
        "aspect_ratio": "16:9",
        "export_resolution": "Full HD (1920x1080・推奨)",
        "export_fps": "60 FPS (滑らか・推奨)",
        "export_style": "完成動画 (背景・タイトル合成)",
        "export_bg_color": "ノーマル（黒）",
        "export_intro_sec": "1秒",
        "export_outro_sec": "2秒",
        "export_fade_in": True,
        "export_fade_out": True,
        "export_fade_in_sec": 1.5,
        "export_fade_out_sec": 1.5,
        "export_fade_title_mode": "フェード中もタイトル表示",
        "export_title_template": "イントロ中央＋右上常時",
        "export_title_enabled": True,
        "export_title_duration": 3.5,
        "export_title_exit_mode": "フェードアウトで消える",
        "vertical_layout_mode": "全画面フル展開 (標準Shorts)",
        "audio_quick_mode": "伴奏音源 (外部音源優先)",
        "reverb_enabled": True,
        "yt_limiter": True,
        "export_audio_volume": 100,
        # ビジュアル
        "trajectory_mode": "垂直落下 (穴直上)",
        "lang_mode": "ドレミ",
        "color_theme": "ノーマル",
        "color_blow": "#FF5500",
        "color_draw": "#00BFFF",
        "lever_deco_mode": "センターライン (芯線)",
        "note_opacity": 100,
        "show_notes": True,
        "show_lookahead": True,
        "show_grid": True,
        "show_bar_lines": True,
        "show_hole_num": True,
        "hole_num_style": "実機標準 (低音ドット付)",
        "grid4_mode": "4音グリッド表示",
        "show_ring": True,
        "show_glow": True,
        "show_legend": True,
        "bg_image_enabled": True,
        "bg_image_path": "",
        "bg_dim_ratio": 60,
        "bg_fit_mode": "中央トリミング (画面いっぱい)",
        "bg_rotation": 0,
        "skin_enabled": True,
        "skin_mouthpiece_path": "",
        "skin_lever_off_path": "",
        "skin_lever_on_path": "",
    },
    "🎨 演奏作品・MV (16:9・背景画像)": {
        "aspect_ratio": "16:9",
        "export_resolution": "Full HD (1920x1080・推奨)",
        "export_fps": "60 FPS (滑らか・推奨)",
        "export_style": "完成動画 (背景・タイトル合成)",
        "export_bg_color": "ノーマル（黒）",
        "export_intro_sec": "2秒",
        "export_outro_sec": "2秒",
        "export_fade_in": True,
        "export_fade_out": True,
        "export_fade_in_sec": 1.5,
        "export_fade_out_sec": 1.5,
        "export_fade_title_mode": "フェード中もタイトル表示",
        "export_title_template": "イントロ中央＋右上常時",
        "export_title_enabled": True,
        "export_title_duration": 3.5,
        "export_title_exit_mode": "フェードアウトで消える",
        "vertical_layout_mode": "全画面フル展開 (標準Shorts)",
        "audio_quick_mode": "伴奏音源 (外部音源優先)",
        "reverb_enabled": True,
        "yt_limiter": True,
        "export_audio_volume": 100,
        # ビジュアル (MV向け・背景引き立て＆ノーツ透過)
        "trajectory_mode": "3段階 (練習標準)",
        "lang_mode": "ドレミ",
        "color_theme": "ノーマル",
        "color_blow": "#FF5500",
        "color_draw": "#00BFFF",
        "lever_deco_mode": "センターライン (芯線)",
        "note_opacity": 85,
        "show_notes": True,
        "show_lookahead": False,
        "show_grid": False,
        "show_bar_lines": False,
        "show_hole_num": True,
        "hole_num_style": "実機標準 (低音ドット付)",
        "grid4_mode": "非表示",
        "show_ring": True,
        "show_glow": True,
        "show_legend": False,
        "bg_image_enabled": True,
        "bg_image_path": "",
        "bg_dim_ratio": 40,
        "bg_fit_mode": "中央トリミング (画面いっぱい)",
        "bg_rotation": 0,
        "skin_enabled": True,
        "skin_mouthpiece_path": "",
        "skin_lever_off_path": "",
        "skin_lever_on_path": "",
    },
    "✨ ミニマル・シネマティック (16:9)": {
        "aspect_ratio": "16:9",
        "export_resolution": "Full HD (1920x1080・推奨)",
        "export_fps": "60 FPS (滑らか・推奨)",
        "export_style": "完成動画 (背景・タイトル合成)",
        "export_bg_color": "ノーマル（黒）",
        "export_intro_sec": "3秒",
        "export_outro_sec": "3秒",
        "export_fade_in": True,
        "export_fade_out": True,
        "export_fade_in_sec": 2.0,
        "export_fade_out_sec": 2.0,
        "export_fade_title_mode": "フェード中もタイトル表示",
        "export_title_template": "イントロ中央のみ",
        "export_title_enabled": True,
        "export_title_duration": 3.5,
        "export_title_exit_mode": "フェードアウトで消える",
        "vertical_layout_mode": "全画面フル展開 (標準Shorts)",
        "audio_quick_mode": "伴奏音源 (外部音源優先)",
        "reverb_enabled": True,
        "yt_limiter": True,
        "export_audio_volume": 100,
        # ビジュアル (映像美重視・文字/線なし)
        "trajectory_mode": "2段階 (ビジュアル)",
        "lang_mode": "ドレミ",
        "color_theme": "ノーマル",
        "color_blow": "#FF5500",
        "color_draw": "#00BFFF",
        "lever_deco_mode": "センターライン (芯線)",
        "note_opacity": 95,
        "show_notes": True,
        "show_lookahead": False,  # 音名OFF
        "show_grid": False,        # レーンガイドOFF
        "show_bar_lines": False,   # 小節線OFF
        "show_hole_num": False,    # 穴番号OFF
        "hole_num_style": "実機標準 (低音ドット付)",
        "grid4_mode": "非表示",
        "show_ring": True,
        "show_glow": True,
        "show_legend": False,     # 凡例OFF
        "bg_image_enabled": True,
        "bg_image_path": "",
        "bg_dim_ratio": 60,
        "bg_fit_mode": "中央トリミング (画面いっぱい)",
        "bg_rotation": 0,
        "skin_enabled": True,
        "skin_mouthpiece_path": "",
        "skin_lever_off_path": "",
        "skin_lever_on_path": "",
    },
    "🟩 クロマキー透過素材 (外部編集用)": {
        "aspect_ratio": "16:9",
        "export_resolution": "Full HD (1920x1080・推奨)",
        "export_fps": "60 FPS (滑らか・推奨)",
        "export_style": "クロマキー素材 (背景・タイトルなし)",
        "export_bg_color": "グリーンバック",
        "export_intro_sec": "0秒",
        "export_outro_sec": "1秒",
        "export_fade_in": False,
        "export_fade_out": False,
        "export_fade_in_sec": 0.0,
        "export_fade_out_sec": 0.0,
        "export_fade_title_mode": "フェード中もタイトル表示",
        "export_title_template": "なし",
        "export_title_enabled": False,
        "export_title_duration": 3.5,
        "export_title_exit_mode": "フェードアウトで消える",
        "vertical_layout_mode": "全画面フル展開 (標準Shorts)",
        "audio_quick_mode": "無音 (映像のみ)",
        "reverb_enabled": False,
        "yt_limiter": True,
        "export_audio_volume": 100,
        # ビジュアル (合成用・垂直落下)
        "trajectory_mode": "垂直落下 (穴直上)",
        "lang_mode": "ドレミ",
        "color_theme": "ノーマル",
        "color_blow": "#FF5500",
        "color_draw": "#00BFFF",
        "lever_deco_mode": "センターライン (芯線)",
        "note_opacity": 100,
        "show_notes": True,
        "show_lookahead": True,
        "show_grid": False,
        "show_bar_lines": False,
        "show_hole_num": True,
        "hole_num_style": "実機標準 (低音ドット付)",
        "grid4_mode": "4音グリッド表示",
        "show_ring": True,
        "show_glow": True,
        "show_legend": False,
        "bg_image_enabled": False,
        "bg_image_path": "",
        "bg_dim_ratio": 0,
        "bg_fit_mode": "中央トリミング (画面いっぱい)",
        "bg_rotation": 0,
        "skin_enabled": True,
        "skin_mouthpiece_path": "",
        "skin_lever_off_path": "",
        "skin_lever_on_path": "",
    },
}

DEFAULT_SETTINGS = {
    # 楽器・基本
    "inst_type": "16穴 (64音・C調)",
    "fingering_preset": "スライド最小化",

    # 起動時の状態初期化設定 (v4.2.0: 課題27)
    "reset_speed_on_startup": True,
    "reset_metro_on_startup": True,
    "reset_countin_on_startup": False,

    # 音声合成エンジン (v4.2.0: 課題35)
    "synth_engine": "Windows標準MIDI (推奨)",

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

    # 録音・外部音源・リバーブ
    "rec_device": "",
    "rec_channels": 1,
    "rec_offset_ms": 0,
    "reverb_enabled": False,
    "reverb_type": "ルーム (自然な部屋鳴り)",
    "reverb_wet_pct": 35,
    "ext_audio_path": "",
    "ext_audio_mode": "頭出し確認 (再生:両方 / 動画:外部のみ)",
    "ext_audio_offset_ms": 0,
    "ext_audio_volume": 100,
    "yt_limiter": True,

    # 🌟 練習用ビジュアル設定 (v3.1.0)
    "practice_visual": copy.deepcopy(DEFAULT_PRACTICE_VISUAL),

    # 🌟 動画出力プリセット管理 (v3.1.0)
    "active_video_preset": "📱 YouTube Shorts (縦型・解説)",
    "video_presets": copy.deepcopy(DEFAULT_VIDEO_PRESETS),

    # 履歴
    "recent_files": [],

    # レガシー互換キー (旧バージョンからの読み込み・フォールバック用)
    "aspect_ratio": "16:9",
    "trajectory_mode": "3段階 (練習標準)",
    "lang_mode": "ドレミ",
    "show_grid": True,
    "show_bar_lines": True,
    "show_legend": True,
    "show_hole_num": True,
    "hole_num_style": "実機標準 (低音ドット付)",
    "show_notes": True,
    "show_lookahead": True,
    "grid4_mode": "4音グリッド表示",
    "show_ring": True,
    "show_glow": True,
    "note_opacity": 100,
    "color_theme": "ノーマル",
    "color_blow": "#FF5500",
    "color_draw": "#00BFFF",
    "lever_deco_mode": "センターライン (芯線)",
    "bg_image_enabled": True,
    "bg_image_path": "",
    "bg_dim_ratio": 60,
    "bg_fit_mode": "中央トリミング (画面いっぱい)",
    "bg_rotation": 0,
    "skin_enabled": True,
    "skin_mouthpiece_path": "",
    "skin_lever_off_path": "",
    "skin_lever_on_path": "",
    "export_range": "全曲",
    "export_resolution": "Full HD (1920x1080)",
    "export_fps": "60 FPS",
    "export_bg_color": "ノーマル (黒)",
    "export_style": "完成動画 (背景・タイトル合成)",
    "export_intro_sec": "1秒",
    "export_outro_sec": "2秒",
    "export_fade_in": True,
    "export_fade_out": True,
    "export_fade_in_sec": 1.5,
    "export_fade_out_sec": 1.5,
    "export_fade_title_mode": "フェード中もタイトル表示",
    "export_title_template": "なし",
    "export_title_text": "",
    "export_credit_text": "",
    "export_audio_volume": 100,
}

# カラーテーマ定義 (吹音, 吸音)
THEME_PRESETS = {
    "ノーマル": ("#FF5500", "#00BFFF"),
    "サクラ": ("#FFB7C5", "#3CB371"),
    "クールネオン": ("#FF007F", "#1E90FF"),
    "モノクロ": ("#FFFFFF", "#7F7F7F"),
}


def get_fresh_default_settings() -> dict:
    """初期デフォルト設定の完全な独立ディープコピーを返却（グローバル定数汚染の防止）"""
    s = copy.deepcopy(DEFAULT_SETTINGS)
    s["practice_visual"] = copy.deepcopy(DEFAULT_PRACTICE_VISUAL)
    s["video_presets"] = copy.deepcopy(DEFAULT_VIDEO_PRESETS)
    return s


def get_fresh_default_practice_visual() -> dict:
    """練習画面用初期ビジュアル設定の完全な独立ディープコピーを返却"""
    return copy.deepcopy(DEFAULT_PRACTICE_VISUAL)


def load_settings() -> dict:
    """設定ファイルから辞書を読込。存在しない項目はデフォルト値で自動補完し、v3.1.0形式へ自動マイグレーション"""
    settings = get_fresh_default_settings()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    settings.update(saved)
        except Exception as e:
            print(f"[SettingsManager Warning] Failed to load settings: {e}")

    # --- v3.1.0 マイグレーション処理 ---
    # 1. practice_visual が未定義または不完全な場合、フラットな既存設定から構築
    if "practice_visual" not in settings or not isinstance(settings["practice_visual"], dict):
        settings["practice_visual"] = copy.deepcopy(DEFAULT_PRACTICE_VISUAL)
        for k in VISUAL_KEYS:
            if k in settings:
                settings["practice_visual"][k] = settings[k]
    else:
        # 欠けているキーをデフォルト値で補完
        for k, v in DEFAULT_PRACTICE_VISUAL.items():
            if k not in settings["practice_visual"]:
                settings["practice_visual"][k] = copy.deepcopy(v)

    # 2. video_presets が未定義または空の場合、公式デフォルトを補完
    if "video_presets" not in settings or not isinstance(settings["video_presets"], dict) or not settings["video_presets"]:
        settings["video_presets"] = copy.deepcopy(DEFAULT_VIDEO_PRESETS)
    else:
        # 旧プリセット名からの自動マイグレーション
        old_to_new = {
            "🎥 演奏解説・練習用 (横型・標準)": "🎥 演奏解説・レッスン (16:9)",
            "✨ シネマティックMV (横型・演出重視)": "✨ ミニマル・シネマティック (16:9)",
            "🟩 クロマキー合成素材 (透過用)": "🟩 クロマキー透過素材 (外部編集用)",
        }
        for old_k, new_k in old_to_new.items():
            if old_k in settings["video_presets"] and new_k not in settings["video_presets"]:
                settings["video_presets"][new_k] = settings["video_presets"].pop(old_k)

        # 公式5大プリセットの補完および自己修復
        for def_name, def_preset in DEFAULT_VIDEO_PRESETS.items():
            if def_name not in settings["video_presets"]:
                settings["video_presets"][def_name] = copy.deepcopy(def_preset)
            else:
                p_item = settings["video_presets"][def_name]
                if isinstance(p_item, dict):
                    # 各プリセットの最新共通キーを補完
                    for dk, dv in def_preset.items():
                        p_item.setdefault(dk, copy.deepcopy(dv))
                    # Shortsプリセット等の公式比率修復
                    if "Shorts" in def_name or "縦型" in def_name:
                        p_item["aspect_ratio"] = "9:16"
                    elif "16:9" in def_name or "MV" in def_name or "クロマキー" in def_name:
                        p_item["aspect_ratio"] = "16:9"

    # 3. active_video_preset の整合性
    if settings.get("active_video_preset") not in settings["video_presets"]:
        settings["active_video_preset"] = "📱 YouTube Shorts (縦型・解説)"

    # 4. v3.2.0 マイグレーション: lang_mode "なし" の撤廃と grid4_mode / show_lookahead の完全直交化
    def _migrate_lang_mode(target_dict: dict):
        if target_dict.get("lang_mode") == "なし":
            target_dict["lang_mode"] = "ドレミ"
            target_dict["show_lookahead"] = False
            target_dict["grid4_mode"] = "非表示"

    _migrate_lang_mode(settings)
    if "practice_visual" in settings and isinstance(settings["practice_visual"], dict):
        _migrate_lang_mode(settings["practice_visual"])
    if "video_presets" in settings and isinstance(settings["video_presets"], dict):
        for p_dict in settings["video_presets"].values():
            if isinstance(p_dict, dict):
                _migrate_lang_mode(p_dict)

    # 5. v4.2.0 マイグレーション: MIDI音源エンジン設定キーの統一同期 (HIGH-3)
    raw_eng = settings.get("synth_engine") or settings.get("synth_mode") or settings.get("guide_audio_engine", "Windows標準MIDI (推奨)")
    if "内蔵" in str(raw_eng):
        norm_eng = "内蔵軽量シンセ (遅延0ms)"
    else:
        norm_eng = "Windows標準MIDI (推奨)"
    settings["synth_engine"] = norm_eng
    settings["synth_mode"] = norm_eng
    settings["guide_audio_engine"] = norm_eng

    # 6. video_working_state の初期化補完 (HIGH-2)
    active_p_name = settings.get("active_video_preset", "📱 YouTube Shorts (縦型・解説)")
    active_p_orig = copy.deepcopy(settings["video_presets"].get(active_p_name, DEFAULT_VIDEO_PRESETS["📱 YouTube Shorts (縦型・解説)"]))
    if "video_working_state" not in settings or not isinstance(settings.get("video_working_state"), dict):
        settings["video_working_state"] = copy.deepcopy(active_p_orig)
    else:
        for dk, dv in active_p_orig.items():
            settings["video_working_state"].setdefault(dk, copy.deepcopy(dv))

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
    files = [p for p in files if os.path.normpath(p) != norm_path]
    files.insert(0, norm_path)
    s["recent_files"] = files[:10]
    save_settings(s)


def extract_visual_from_settings(s: dict) -> dict:
    """設定辞書からビジュアル関連キーのみを安全に抽出した辞書を返却"""
    pv = s.get("practice_visual", {})
    res = {}
    for k in VISUAL_KEYS:
        if k in pv:
            res[k] = pv[k]
        elif k in s:
            res[k] = s[k]
        else:
            res[k] = DEFAULT_PRACTICE_VISUAL.get(k)
    return res


def get_active_preset_dict(s: dict) -> dict:
    """現在アクティブな動画出力プリセットの辞書を返却"""
    presets = s.get("video_presets", DEFAULT_VIDEO_PRESETS)
    active_name = s.get("active_video_preset", "📱 YouTube Shorts (縦型・解説)")
    if active_name in presets:
        return copy.deepcopy(presets[active_name])
    return copy.deepcopy(DEFAULT_VIDEO_PRESETS.get("📱 YouTube Shorts (縦型・解説)"))


def get_working_video_state(s: dict) -> dict:
    """現在の動画制作セッションの作業状態 (video_working_state) を返却（未設定時はアクティブプリセット原本のコピー）"""
    base = get_active_preset_dict(s)
    ws = s.get("video_working_state")
    if isinstance(ws, dict) and ws:
        merged = copy.deepcopy(base)
        merged.update(copy.deepcopy(ws))
        return merged
    return base


def get_video_presets() -> dict:
    """保存されている全動画出力プリセット辞書を取得"""
    s = load_settings()
    return s.get("video_presets", copy.deepcopy(DEFAULT_VIDEO_PRESETS))


def save_video_preset(preset_name: str, preset_dict: dict):
    """動画出力プリセットを新規保存または上書き更新"""
    s = load_settings()
    if "video_presets" not in s:
        s["video_presets"] = copy.deepcopy(DEFAULT_VIDEO_PRESETS)
    s["video_presets"][preset_name] = copy.deepcopy(preset_dict)
    s["active_video_preset"] = preset_name
    save_settings(s)


def delete_video_preset(preset_name: str) -> bool:
    """ユーザー定義プリセットを削除（公式プリセットは保護）"""
    if preset_name in DEFAULT_VIDEO_PRESETS:
        return False
    s = load_settings()
    presets = s.get("video_presets", {})
    if preset_name in presets:
        del presets[preset_name]
        s["active_video_preset"] = "📱 YouTube Shorts (縦型・解説)"
        save_settings(s)
        return True
    return False


def reset_default_preset(preset_name: str) -> bool:
    """公式プリセットを初期状態値へリセット"""
    if preset_name not in DEFAULT_VIDEO_PRESETS:
        return False
    s = load_settings()
    presets = s.get("video_presets", {})
    presets[preset_name] = copy.deepcopy(DEFAULT_VIDEO_PRESETS[preset_name])
    save_settings(s)
    return True

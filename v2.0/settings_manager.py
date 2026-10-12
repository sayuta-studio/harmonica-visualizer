# -*- coding: utf-8 -*-
# settings_manager.py (STEP 4-B: ユーザー設定自動ロード・セーブ・ABループ保存除外版)
# - 【安全設計】：PermissionErrorおよび一時フォルダ消去トラップを完全回避するポータブル仕様。
# - 【ABループ保存除外】：曲ごとに小節数が異なって表示崩れやエラーを誘発するのを防ぐため、ABループ設定（トグル・A点・B点）を共通設定保存対象から完全に除外しました。
# - 🚀【新機能対応】：アスペクト比設定と外部スキン使用状態の永続保存ロジックを追加。
# - 🚀【STEP 4.5】：新設「レバーリング表示」の設定ロード・セーブを追加同期。

import os
from config import get_portable_path

def get_portable_base_dir():
    """
    PyInstallerでワンファイル化されてアセットが一時フォルダに展開されている際も、
    ユーザーが実際にダブルクリックして起動した「実行ファイル（.exe）が存在している物理フォルダ」
    の絶対パスを正確に取得します。
    """
    return get_portable_path("")


DEFAULT_SETTINGS = {
    "楽器タイプ": "16穴 (C3-D7)",
    "音名表記": "CDE",
    "穴番号表示": "ON",
    "凡例表示": "ON",
    "ノーツ表示": "ON",
    "ガイド線表示": "ON",
    "着地発光表示": "OFF",
    "ノーツ不透明度": "50",
    "動画背景色": "ノーマル（黒）",
    "動画解像度": "Full HD (1920x1080)",
    "軽量プレビュー": "ON",
    "カラーテーマ": "ノーマル",
    "吹音色": "#FF9900",
    "吸音色": "#00FFFF",
    "動画FPS": "60 FPS",
    "音響モード": "MIDI再生 (Windows標準音源)",
    "変え指設定": "スライド最小化",
    "アスペクト比": "16:9",
    "外部スキン使用": "ON",
    "レバーリング表示": "ON",
    "ノーツ落下軌道": "3段階 (練習標準)",
    "直上音名予告": "ON",
    "田の字4音表示": "ON",
    "ノーツ落下速度": "1.0x (標準)",
    "ステップアップ増加": "+5%",
    "ステップアップ開始": "70",
    "ステップアップ目標": "100",
    "動画出力範囲": "全曲",
    "動画イントロ秒": "0秒",
    "動画アウトロ秒": "2秒",
    "動画タイトル配置": "なし",
    "動画タイトル文字列": "",
    "動画クレジット文字列": "",
    "外部音源モード": "頭出し確認 (再生:両方 / 動画:外部のみ)",
    "外部音源オフセットms": "0",
    "外部音源音量": "100",
    "YouTube上限リミッター": "ON"
}


def load_settings():
    base_dir = get_portable_base_dir()
    settings_path = os.path.join(base_dir, "settings.txt")
    loaded = DEFAULT_SETTINGS.copy()
    if not os.path.exists(settings_path):
        return loaded

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                val = parts[1].strip()
                if key in loaded:
                    loaded[key] = val
        return loaded
    except Exception as e:
        print(f"[警告] settings.txt のパースに失敗しました: {e}")
        return loaded


def save_settings_dict(settings_dict):
    """辞書形式で受け取った設定を settings.txt へ安全に永続化保存します。"""
    base_dir = get_portable_base_dir()
    settings_path = os.path.join(base_dir, "settings.txt")
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings_dict)
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("# ======================================================\n")
            f.write("#  Chromatic Harmonica Trainer - ユーザー環境設定\n")
            f.write("#  (このファイルをメモ帳等で直接書き換えて保存することができます)\n")
            f.write("#  全角・半角のコロンどちらにも対応しています。\n")
            f.write("# ======================================================\n\n")
            for k, v in merged.items():
                f.write(f"{k}: {v}\n")
    except Exception as e:
        print(f"[警告] settings.txt へのセーブに失敗しました: {e}")


def save_settings(inst, lang, hole, legend, notes, grid, glow, opacity, bg, res,
                  simplified="ON", theme="ノーマル", blow="#FF9900", draw="#00FFFF", fps="60 FPS",
                  audio_mode="MIDI再生 (Windows標準音源)", fingering_preset="スライド最小化",
                  ratio="16:9", use_skin="ON", ring="ON", trajectory="3段階 (練習標準)",
                  lookahead="ON", grid4="ON", **extra):
    """後方互換ラッパー：個別引数を辞書にまとめて save_settings_dict へ委譲します。"""
    data = {
        "楽器タイプ": inst,
        "音名表記": lang,
        "穴番号表示": hole,
        "凡例表示": legend,
        "ノーツ表示": notes,
        "ガイド線表示": grid,
        "着地発光表示": glow,
        "ノーツ不透明度": opacity,
        "動画背景色": bg,
        "動画解像度": res,
        "軽量プレビュー": simplified,
        "カラーテーマ": theme,
        "吹音色": blow,
        "吸音色": draw,
        "動画FPS": fps,
        "音響モード": audio_mode,
        "変え指設定": fingering_preset,
        "アスペクト比": ratio,
        "外部スキン使用": use_skin,
        "レバーリング表示": ring,
        "ノーツ落下軌道": trajectory,
        "直上音名予告": lookahead,
        "田の字4音表示": grid4,
    }
    data.update(extra)
    save_settings_dict(data)

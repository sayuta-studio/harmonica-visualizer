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
    # --- 🎵 練習タブ ＆ 上部バー ---
    "ハーモニカ": "16穴 (C3-D7)",
    "穴下の音名": "4音グリッド表示",
    "音名表記": "CDE",
    "ノーツ落下速度": "1.0x (標準)",
    "ステップアップ開始": "70",
    "ステップアップ目標": "100",
    "ステップアップ1周増分": "+5%",
    "再生音源": "MIDI再生 (Windows標準音源)",
    "運指プリセット": "スライド最小化",

    # --- 🎙️ 録音・音響タブ ---
    "マイクデバイス": "既定の入力マイク (システム標準)",
    "録音チャンネル": "モノラル (1ch・DAW編集向き)",
    "リバーブ適用": "OFF",
    "リバーブ種類": "ルーム (自然な部屋鳴り)",
    "リバーブ深さ%": "35",
    "外部音源モード": "頭出し確認 (再生:両方 / 動画:外部のみ)",
    "外部音源頭出しms": "0",
    "外部音源音量%": "100",
    "YouTube上限リミッター": "ON",

    # --- 🎨 画面作りタブ ---
    "背景画像の表示": "ON",
    "動画編集を動画出力に適用": "ON",
    "アスペクト比": "16:9",
    "背景画像パス": "",
    "背景画像の配置": "中央トリミング (画面いっぱい)",
    "背景画像の回転": "0° (自動補正)",
    "背景画像の明るさ": "少し暗め (70%・ノーツ強調)",
    "タイトル配置": "なし",
    "タイトル曲名": "",
    "タイトルサブ": "",
    "ノーツ軌道": "垂直落下 (穴直上)",
    "ノーツカラーテーマ": "ノーマル",
    "吹音色": "#FF9900",
    "吸音色": "#00FFFF",
    "レバーON装飾": "センターライン (芯線)",
    "外部スキン": "ON",
    "ノーツ不透過度": "50",
    "穴番号": "ON",
    "凡例": "ON",
    "ノーツ表示": "ON",
    "ガイド線": "ON",
    "レバーリング連動": "ON",
    "着地発光": "OFF",
    "ノーツ音名表示": "ON",

    # --- 🎬 動画出力タブ ---
    "出力スタイル": "完成動画 (背景・タイトル合成)",
    "動画背景色": "ノーマル（黒）",
    "出力解像度": "Full HD (1920x1080)",
    "フレームレート": "60 FPS",
    "書き出し範囲": "全曲",
    "前の余白": "0秒",
    "後の余白": "2秒",
    "開始フェードイン": "OFF",
    "終了フェードアウト": "OFF",
    "フェード時題名": "フェード中もタイトル表示",
}

# 旧バージョンの settings.txt キー名を現在のUI表示名へ自動引き継ぎ変換するマップ
LEGACY_KEY_MAP = {
    "楽器タイプ": "ハーモニカ",
    "ノーツ落下軌道": "ノーツ軌道",
    "ステップアップ増加": "ステップアップ1周増分",
    "音響モード": "再生音源",
    "変え指設定": "運指プリセット",
    "カラーテーマ": "ノーツカラーテーマ",
    "外部スキン使用": "外部スキン",
    "ノーツ不透明度": "ノーツ不透過度",
    "田の字4音表示": "穴下の音名",
    "穴番号表示": "穴番号",
    "凡例表示": "凡例",
    "ガイド線表示": "ガイド線",
    "レバーリング表示": "レバーリング連動",
    "着地発光表示": "着地発光",
    "直上音名予告": "ノーツ音名表示",
    "動画編集適用": "出力スタイル",
    "動画編集を動画出力に適用": "出力スタイル",
    "リバーブ有効": "リバーブ適用",
    "リバーブタイプ": "リバーブ種類",
    "リバーブ深さ": "リバーブ深さ%",
    "動画タイトル配置": "タイトル配置",
    "動画タイトル文字列": "タイトル曲名",
    "動画クレジット文字列": "タイトルサブ",
    "外部音源オフセットms": "外部音源頭出しms",
    "外部音源音量": "外部音源音量%",
    "動画解像度": "出力解像度",
    "動画FPS": "フレームレート",
    "動画出力範囲": "書き出し範囲",
    "動画イントロ秒": "前の余白",
    "動画アウトロ秒": "後の余白",
}

SETTINGS_SECTIONS = [
    ("🎵 練習タブ ＆ 上部バー", [
        "ステップアップ開始",
        "ステップアップ目標",
        "ステップアップ1周増分",
        "ハーモニカ",
        "穴下の音名",
        "音名表記",
        "再生音源",
        "運指プリセット",
        "ノーツ落下速度",
    ]),
    ("🎨 画面作りタブ", [
        "背景画像の表示",
        "アスペクト比",
        "背景画像パス",
        "背景画像の配置",
        "背景画像の回転",
        "背景画像の明るさ",
        "ノーツ軌道",
        "ノーツカラーテーマ",
        "吹音色",
        "吸音色",
        "レバーON装飾",
        "外部スキン",
        "ノーツ不透過度",
        "穴番号",
        "凡例",
        "ノーツ表示",
        "ガイド線",
        "レバーリング連動",
        "着地発光",
        "ノーツ音名表示",
    ]),
    ("🎙️ 録音・音響タブ", [
        "マイクデバイス",
        "録音チャンネル",
        "リバーブ適用",
        "リバーブ種類",
        "リバーブ深さ%",
        "外部音源モード",
        "外部音源頭出しms",
        "外部音源音量%",
        "YouTube上限リミッター",
    ]),
    ("🎬 動画出力タブ", [
        "出力スタイル",
        "タイトル配置",
        "タイトル曲名",
        "タイトルサブ",
        "動画背景色",
        "出力解像度",
        "フレームレート",
        "書き出し範囲",
        "前の余白",
        "後の余白",
        "開始フェードイン",
        "終了フェードアウト",
        "フェード時題名",
    ]),
]


def _normalize_loaded_value(key, val):
    """旧表記の設定値を現在のUI選択肢表記へ正規化します。"""
    if key == "穴下の音名":
        if val in ("ON", "4音グリッド表示"):
            return "4音グリッド表示"
        if val in ("OFF", "1音表示 (従来)"):
            return "1音表示 (従来)"
    elif key == "ノーツ軌道":
        if val == "3段階収束 (標準)":
            return "3段階 (練習標準)"
    elif key == "運指プリセット":
        if val == "標準運指":
            return "スライド最小化"
    elif key == "出力スタイル":
        if val in ("ON", "True", "true"):
            return "完成動画 (背景・タイトル合成)"
        if val in ("OFF", "False", "false"):
            return "クロマキー素材 (背景・タイトルなし)"
    elif key == "録音チャンネル":
        if val in ("1", "1ch", "モノラル", "mono", "Mono"):
            return "モノラル (1ch・DAW編集向き)"
        if val in ("2", "2ch", "ステレオ", "stereo", "Stereo"):
            return "ステレオ (2ch)"
    return val


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
                raw_key = parts[0].strip()
                val = parts[1].strip()
                key = LEGACY_KEY_MAP.get(raw_key, raw_key)
                if key in loaded:
                    loaded[key] = _normalize_loaded_value(key, val)
        return loaded
    except Exception as e:
        print(f"[警告] settings.txt のパースに失敗しました: {e}")
        return loaded


def save_settings_dict(settings_dict):
    """辞書形式で受け取った設定を、現在の4タブUI構成に揃えて settings.txt へ永続化保存します。"""
    base_dir = get_portable_base_dir()
    settings_path = os.path.join(base_dir, "settings.txt")
    merged = DEFAULT_SETTINGS.copy()
    for raw_k, v in settings_dict.items():
        k = LEGACY_KEY_MAP.get(raw_k, raw_k)
        if k in merged:
            merged[k] = _normalize_loaded_value(k, v)

    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("# ======================================================\n")
            f.write("#  Chromatic Harmonica Visualizer - ユーザー環境設定\n")
            f.write("#  (このファイルをメモ帳等で直接書き換えて保存することができます)\n")
            f.write("#  項目名・選択肢は画面上の表示名と一致しています。\n")
            f.write("#  全角・半角のコロンどちらにも対応しています。\n")
            f.write("# ======================================================\n")
            for sec_title, keys in SETTINGS_SECTIONS:
                f.write(f"\n# --- [{sec_title}] ---\n")
                for k in keys:
                    f.write(f"{k}: {merged.get(k, DEFAULT_SETTINGS[k])}\n")
    except Exception as e:
        print(f"[警告] settings.txt へのセーブに失敗しました: {e}")


def save_settings(inst, lang, hole, legend, notes, grid, glow, opacity, bg, res,
                  theme="ノーマル", blow="#FF9900", draw="#00FFFF", fps="60 FPS",
                  audio_mode="MIDI再生 (Windows標準音源)", fingering_preset="スライド最小化",
                  ratio="16:9", use_skin="ON", ring="ON", trajectory="垂直落下 (穴直上)",
                  lookahead="ON", grid4="4音グリッド表示", lever_deco="センターライン (芯線)", **extra):
    """個別引数を辞書にまとめて save_settings_dict へ委譲します。"""
    data = {
        "ハーモニカ": inst,
        "音名表記": lang,
        "穴番号": hole,
        "凡例": legend,
        "ノーツ表示": notes,
        "ガイド線": grid,
        "着地発光": glow,
        "ノーツ不透過度": opacity,
        "動画背景色": bg,
        "出力解像度": res,
        "ノーツカラーテーマ": theme,
        "吹音色": blow,
        "吸音色": draw,
        "レバーON装飾": lever_deco,
        "フレームレート": fps,
        "再生音源": audio_mode,
        "運指プリセット": fingering_preset,
        "アスペクト比": ratio,
        "外部スキン": use_skin,
        "レバーリング連動": ring,
        "ノーツ軌道": trajectory,
        "ノーツ音名表示": lookahead,
        "穴下の音名": grid4,
    }
    data.update(extra)
    save_settings_dict(data)

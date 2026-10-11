# -*- coding: utf-8 -*-
# settings_manager.py (STEP 4-B: ユーザー設定自動ロード・セーブ・ABループ保存除外版)
# - 【安全設計】：PermissionErrorおよび一時フォルダ消去トラップを完全回避するポータブル仕様。
# - 【ABループ保存除外】：曲ごとに小節数が異なって表示崩れやエラーを誘発するのを防ぐため、ABループ設定（トグル・A点・B点）を共通設定保存対象から完全に除外しました。
# - 🚀【新機能対応】：アスペクト比設定と外部スキン使用状態の永続保存ロジックを追加。
# - 🚀【STEP 4.5】：新設「レバーリング表示」の設定ロード・セーブを追加同期。

import os
import sys

def get_portable_base_dir():
    """
    PyInstallerでワンファイル化されてアセットが一時フォルダに展開されている際も、
    ユーザーが実際にダブルクリックして起動した「実行ファイル（.exe）が存在している物理フォルダ」
    の絶対パスを正確に取得します。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def load_settings():
    default_settings = {
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
        "レバーリング表示": "ON"  # 🚀【追加】：レバーリング状態
    }
    
    base_dir = get_portable_base_dir()
    settings_path = os.path.join(base_dir, "settings.txt")
    if not os.path.exists(settings_path):
        return default_settings
        
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        loaded = default_settings.copy()
        for line in lines:
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
        return default_settings


def save_settings(inst, lang, hole, legend, notes, grid, glow, opacity, bg, res, 
                  simplified="ON", theme="ノーマル", blow="#FF9900", draw="#00FFFF", fps="60 FPS",
                  audio_mode="MIDI再生 (Windows標準音源)", fingering_preset="スライド最小化",
                  ratio="16:9", use_skin="ON", ring="ON"):  # 🚀【追加】：ring引数
    """
    ユーザー環境設定を物理領域へ安全に永続化保存します。(ABループ設定は除外)
    """
    base_dir = get_portable_base_dir()
    settings_path = os.path.join(base_dir, "settings.txt")
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write("# ======================================================\n")
            f.write("#  Chromatic Harmonica Trainer - ユーザー環境設定\n")
            f.write("#  (このファイルをメモ帳等で直接書き換えて保存することができます)\n")
            f.write("#  全角・半角のコロンどちらにも対応しています。\n")
            f.write("# ======================================================\n\n")
            f.write(f"楽器タイプ: {inst}\n")
            f.write(f"音名表記: {lang}\n")
            f.write(f"穴番号表示: {hole}\n")
            f.write(f"凡例表示: {legend}\n")
            f.write(f"ノーツ表示: {notes}\n")
            f.write(f"ガイド線表示: {grid}\n")
            f.write(f"着地発光表示: {glow}\n")
            f.write(f"ノーツ不透明度: {opacity}\n")
            f.write(f"動画背景色: {bg}\n")
            f.write(f"動画解像度: {res}\n")
            f.write(f"軽量プレビュー: {simplified}\n")
            f.write(f"カラーテーマ: {theme}\n")
            f.write(f"吹音色: {blow}\n")
            f.write(f"吸音色: {draw}\n")
            f.write(f"動画FPS: {fps}\n")
            f.write(f"音響モード: {audio_mode}\n")
            f.write(f"変え指設定: {fingering_preset}\n")
            f.write(f"アスペクト比: {ratio}\n")
            f.write(f"外部スキン使用: {use_skin}\n")
            f.write(f"レバーリング表示: {ring}\n")  # 🚀【追加】：レバーリング状態
    except Exception as e:
        print(f"[警告] settings.txt へのセーブに失敗しました: {e}")
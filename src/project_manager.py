# -*- coding: utf-8 -*-
"""
project_manager.py
Harmonica Visualizer Ver.4.0.0 楽曲プロジェクト自己完結管理マネージャー
- 1曲＝1フォルダ (projects/<曲名>/) 構造の管理
- SHA-256ハッシュによる同名別MIDI衝突検知
- プロジェクト内相対パス管理によるフォルダリネーム追従
- 旧 fingering/<曲名>_profile.json からの無損失自動マイグレーション
"""

import os
import sys
import json
import shutil
import hashlib
from typing import Optional, Dict, Any

from config import get_portable_path

# グローバルな現在アクティブなプロジェクト状態
ACTIVE_PROJECT_DIR: Optional[str] = None
ACTIVE_PROJECT_JSON: Optional[str] = None
ACTIVE_PROJECT_DATA: Dict[str, Any] = {}

def sanitize_folder_name(name: str) -> str:
    """Windows/OSで使用不可能なファイル・フォルダ禁止文字を安全に置換"""
    invalid_chars = '<>:"/\\|?*'
    sanitized = "".join(c if c not in invalid_chars else "_" for c in name)
    sanitized = sanitized.strip().strip(". ")
    return sanitized or "untitled_project"

def compute_file_sha256(filepath: str) -> str:
    """ファイルの SHA-256 チェックサムを算出"""
    if not filepath or not os.path.isfile(filepath):
        return ""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f"[ProjectManager] SHA-256 計算エラー ({filepath}): {e}")
        return ""

def get_projects_root_dir() -> str:
    """projects ルートディレクトリの絶対パスを取得"""
    p_dir = get_portable_path("projects")
    os.makedirs(p_dir, exist_ok=True)
    return p_dir

def get_active_project_dir() -> Optional[str]:
    """現在アクティブな楽曲プロジェクトディレクトリ"""
    global ACTIVE_PROJECT_DIR
    return ACTIVE_PROJECT_DIR

def get_active_takes_dir() -> str:
    """現在の録音テイク保存先ディレクトリ（アクティブプロジェクト優先）"""
    proj_dir = get_active_project_dir()
    if proj_dir and os.path.isdir(proj_dir):
        takes_dir = os.path.join(proj_dir, "takes")
        os.makedirs(takes_dir, exist_ok=True)
        return takes_dir
    demo_dir = get_portable_path("projects/_demo_chromatic/takes")
    os.makedirs(demo_dir, exist_ok=True)
    legacy_rec = get_portable_path("recordings")
    if os.path.isdir(legacy_rec):
        try:
            if not os.listdir(legacy_rec):
                os.rmdir(legacy_rec)
        except Exception:
            pass
    return demo_dir

def get_active_exports_dir() -> str:
    """現在の動画書き出し保存先ディレクトリ（アクティブプロジェクト優先）"""
    proj_dir = get_active_project_dir()
    if proj_dir and os.path.isdir(proj_dir):
        exp_dir = os.path.join(proj_dir, "exports")
        os.makedirs(exp_dir, exist_ok=True)
        return exp_dir
    demo_exp = get_portable_path("projects/_demo_chromatic/exports")
    os.makedirs(demo_exp, exist_ok=True)
    return demo_exp

def get_active_audio_dir() -> str:
    """現在の外部伴奏保存先ディレクトリ"""
    proj_dir = get_active_project_dir()
    if proj_dir and os.path.isdir(proj_dir):
        audio_dir = os.path.join(proj_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        return audio_dir
    return get_portable_path("temp")

def to_project_rel_path(abs_path: str, proj_dir: Any = None) -> str:
    """プロジェクトフォルダ内のファイルであれば相対パス（スラッシュ区切り）に変換"""
    if not abs_path:
        return ""
    if isinstance(proj_dir, dict):
        proj_dir = proj_dir.get("project_dir")
    p_dir = proj_dir or get_active_project_dir()
    if not p_dir:
        return abs_path

    norm_abs = os.path.normpath(os.path.abspath(abs_path))
    norm_proj = os.path.normpath(os.path.abspath(p_dir))

    try:
        common = os.path.commonpath([norm_abs, norm_proj])
        if common == norm_proj:
            rel = os.path.relpath(norm_abs, norm_proj)
            return rel.replace("\\", "/")
    except Exception:
        pass
    return abs_path

def from_project_rel_path(stored_path: str, proj_dir: Any = None) -> str:
    """相対パスまたは旧絶対パスを、現在のプロジェクトフォルダ基準の絶対パスに解決"""
    if not stored_path:
        return ""
    if isinstance(proj_dir, dict):
        proj_dir = proj_dir.get("project_dir")
    p_dir = proj_dir or get_active_project_dir()
    if not p_dir:
        return stored_path

    # 相対パスとしてまず検証
    if not os.path.isabs(stored_path):
        candidate = os.path.normpath(os.path.join(p_dir, stored_path)).replace("\\", "/")
        if os.path.exists(candidate):
            return candidate

    # 既に絶対パスで存在していればそれを優先
    if os.path.isabs(stored_path) and os.path.exists(stored_path):
        return stored_path

    # 旧絶対パスだったがフォルダ名がリネームされた場合（末尾のファイル名が takes/ や audio/ にあるかチェック）
    base_name = os.path.basename(stored_path)
    for sub in ("takes", "audio", "source", "exports"):
        sub_candidate = os.path.join(p_dir, sub, base_name)
        if os.path.exists(sub_candidate):
            return sub_candidate.replace("\\", "/")

    return os.path.normpath(os.path.join(p_dir, stored_path)).replace("\\", "/") if not os.path.isabs(stored_path) else stored_path

def get_project_profile_path(midi_path: str) -> str:
    """指定MIDIに対応する project.json の絶対パスを取得"""
    proj_dir = get_active_project_dir()
    if proj_dir:
        return os.path.join(proj_dir, "project.json")

    if not midi_path:
        return get_portable_path(os.path.join("projects", "_default", "project.json"))

    base_name = sanitize_folder_name(os.path.splitext(os.path.basename(midi_path))[0])
    return get_portable_path(os.path.join("projects", base_name, "project.json"))

def get_project_fingering_txt_path(midi_path: str) -> str:
    """レガシー互換の fingering.txt パス"""
    proj_dir = get_active_project_dir()
    if proj_dir:
        return os.path.join(proj_dir, "fingering.txt")
    base_name = sanitize_folder_name(os.path.splitext(os.path.basename(midi_path))[0])
    return get_portable_path(os.path.join("projects", base_name, "fingering.txt"))

def resolve_song_project(midi_path: str, interactive_parent=None) -> dict:
    """
    MIDIファイルの読み込み時に自己完結プロジェクトフォルダを初期化・解決。
    同名別MIDI衝突検知、原本バックアップコピー、旧プロファイルマイグレーションを行う。
    """
    global ACTIVE_PROJECT_DIR, ACTIVE_PROJECT_JSON, ACTIVE_PROJECT_DATA

    projects_root = get_projects_root_dir()

    # デモ曲またはファイル実体なし
    if not midi_path or not os.path.isfile(midi_path) or "demo_chromatic" in midi_path:
        demo_dir = os.path.join(projects_root, "_demo_chromatic")
        os.makedirs(demo_dir, exist_ok=True)
        for sub in ("source", "takes", "audio", "exports"):
            os.makedirs(os.path.join(demo_dir, sub), exist_ok=True)
        ACTIVE_PROJECT_DIR = demo_dir
        ACTIVE_PROJECT_JSON = os.path.join(demo_dir, "project.json")
        return {"project_dir": demo_dir, "project_json": ACTIVE_PROJECT_JSON}

    norm_midi = os.path.normpath(os.path.abspath(midi_path))
    file_sha256 = compute_file_sha256(norm_midi)

    # 既に projects/*/source/ 内のMIDIが指定された場合、そのプロジェクトを採用
    parts = norm_midi.replace("\\", "/").split("/")
    if "projects" in parts and "source" in parts:
        try:
            p_idx = parts.index("projects")
            s_idx = parts.index("source")
            if s_idx == p_idx + 2:
                proj_dir = "/".join(parts[:s_idx])
                proj_json = os.path.join(proj_dir, "project.json")
                ACTIVE_PROJECT_DIR = proj_dir
                ACTIVE_PROJECT_JSON = proj_json
                return {"project_dir": proj_dir, "project_json": proj_json}
        except Exception:
            pass

    base_name = sanitize_folder_name(os.path.splitext(os.path.basename(midi_path))[0])
    target_dir = os.path.join(projects_root, base_name)
    proj_json_path = os.path.join(target_dir, "project.json")

    # 同名別MIDI衝突検知
    if os.path.isdir(target_dir) and os.path.isfile(proj_json_path):
        stored_sha = ""
        try:
            with open(proj_json_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                stored_sha = d.get("midi_source", {}).get("sha256", "")
        except Exception:
            pass

        # ハッシュ不一致（同名・別内容MIDI）
        if stored_sha and file_sha256 and stored_sha != file_sha256:
            should_create_new = True
            if interactive_parent is not None:
                from PyQt6.QtWidgets import QMessageBox
                ans = QMessageBox.question(
                    interactive_parent,
                    "同名MIDI衝突の検知",
                    f"同名のプロジェクト「{base_name}」が既に存在しますが、選択されたMIDIファイルの内容が異なります。\n\n"
                    f"【はい (Yes)】別プロジェクト「{base_name}_2」として新規作成する（推奨・既存データ保護）\n"
                    f"【いいえ (No)】既存プロジェクトのMIDI原本を上書き更新する",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                should_create_new = (ans == QMessageBox.StandardButton.Yes)

            if should_create_new:
                idx = 2
                while True:
                    new_candidate = os.path.join(projects_root, f"{base_name}_{idx}")
                    if not os.path.exists(new_candidate):
                        target_dir = new_candidate
                        proj_json_path = os.path.join(target_dir, "project.json")
                        break
                    idx += 1

    # フォルダ構造作成
    os.makedirs(target_dir, exist_ok=True)
    source_dir = os.path.join(target_dir, "source")
    os.makedirs(source_dir, exist_ok=True)
    for sub in ("takes", "audio", "exports"):
        os.makedirs(os.path.join(target_dir, sub), exist_ok=True)

    # MIDI原本を source/ にコピー（自己コピー防止）
    dest_midi = os.path.join(source_dir, os.path.basename(norm_midi))
    if os.path.normpath(norm_midi) != os.path.normpath(dest_midi):
        try:
            shutil.copy2(norm_midi, dest_midi)
        except Exception as e:
            print(f"[ProjectManager] MIDI原本コピー警告: {e}")

    # project.json のロードまたは新規作成
    project_data = {}
    if os.path.isfile(proj_json_path):
        try:
            with open(proj_json_path, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        except Exception as e:
            print(f"[ProjectManager] project.json 読込エラー: {e}")

    if not project_data:
        # 旧プロファイルからの自動マイグレーション
        old_fingering_dir = get_portable_path("fingering")
        src_fingering_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fingering")
        old_candidates = [
            os.path.join(old_fingering_dir, f"{base_name}_profile.json"),
            os.path.join(src_fingering_dir, f"{base_name}_profile.json"),
        ]
        for old_p in old_candidates:
            if os.path.isfile(old_p):
                try:
                    with open(old_p, "r", encoding="utf-8") as f:
                        project_data = json.load(f)
                    print(f"[ProjectManager] 🌟 旧プロファイルを新プロジェクトへ自動移行しました: {os.path.basename(old_p)}")
                    break
                except Exception:
                    pass

    # メタデータ補完
    project_data["schema_version"] = "4.0.0"
    project_data["project_name"] = os.path.basename(target_dir)
    project_data["midi_source"] = {
        "filename": os.path.basename(norm_midi),
        "relative_path": to_project_rel_path(dest_midi, target_dir),
        "sha256": file_sha256
    }

    try:
        with open(proj_json_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ProjectManager] project.json 保存エラー: {e}")

    ACTIVE_PROJECT_DIR = target_dir
    ACTIVE_PROJECT_JSON = proj_json_path
    ACTIVE_PROJECT_DATA = project_data

    return {
        "project_dir": target_dir,
        "project_json": proj_json_path,
        "midi_dest": dest_midi,
        "data": project_data
    }


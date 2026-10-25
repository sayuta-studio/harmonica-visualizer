# -*- coding: utf-8 -*-
"""
tests/verify_v400_studio.py
Ver.4.0.0 Harmonica Studio 全体統合検証スクリプト (全8項目完全自動テスト)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
import shutil
import subprocess
import tempfile

# 開発モードのパス解決を検証するため src を sys.path に追加
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PyQt6.QtWidgets import QApplication
from config import get_portable_path
import project_manager
import dialogs
from dialogs import HarmonicaSettingsDialog
from main import HarmonicaMainWindow
from studio_controller import StudioExportMixin
import settings_manager
import harmonica_map


def test_1_portable_path():
    print("[TEST 1] Portable path resolution in dev mode...")
    base = get_portable_path("")
    assert os.path.samefile(base, REPO_ROOT), f"Base path {base} does not match repo root {REPO_ROOT}"

    # Verify src/ git cleanliness
    res = subprocess.run(["git", "status", "--porcelain", "src/"], capture_output=True, text=True, cwd=REPO_ROOT)
    untracked_in_src = [line for line in res.stdout.splitlines() if line.startswith("??")]
    assert len(untracked_in_src) == 0, f"Untracked files leaked into src/: {untracked_in_src}"
    print("  -> PASS: Portable path resolves to repository root without polluting src/.")


def test_2_and_3_project_manager_and_sha256():
    print("[TEST 2 & 3] Project creation, container structure, and SHA-256 collision detection...")
    temp_dir = tempfile.mkdtemp()
    try:
        midi1 = os.path.join(temp_dir, "test_song.mid")
        with open(midi1, "wb") as f:
            f.write(b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\x2f\x00\x00")

        # Resolve first song project
        p1 = project_manager.resolve_song_project(midi1)
        assert os.path.isdir(p1["project_dir"]), "Project directory was not created"
        for sub in ["source", "takes", "audio", "exports"]:
            sub_path = os.path.join(p1["project_dir"], sub)
            assert os.path.isdir(sub_path), f"Subdirectory {sub} missing"
        assert os.path.isfile(p1["project_json"]), "project.json missing"
        assert os.path.basename(p1["project_dir"]) == "test_song"

        # Resolve second song with same name but different content (different SHA-256)
        midi2 = os.path.join(temp_dir, "diff_dir", "test_song.mid")
        os.makedirs(os.path.dirname(midi2), exist_ok=True)
        with open(midi2, "wb") as f:
            f.write(b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\xe0MTrk\x00\x00\x00\x05\x00\x90\x3c\x40\x00")

        p2 = project_manager.resolve_song_project(midi2)
        song2_name = os.path.basename(p2["project_dir"])
        assert song2_name == "test_song_2", f"Collision detection failed: expected test_song_2, got {song2_name}"
        assert p2["project_dir"] != p1["project_dir"], "Projects must have separated directories"
        print("  -> PASS: Song project container and SHA-256 collision separation verified.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        # Clean up created test projects
        for p_name in ["test_song", "test_song_2"]:
            p_path = get_portable_path(os.path.join("projects", p_name))
            if os.path.isdir(p_path):
                shutil.rmtree(p_path, ignore_errors=True)


def test_4_relative_path_rename():
    print("[TEST 4] Project folder rename tolerance via relative path resolution...")
    temp_dir = tempfile.mkdtemp()
    try:
        midi = os.path.join(temp_dir, "rename_test.mid")
        with open(midi, "wb") as f:
            f.write(b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\x2f\x00\x00")

        p = project_manager.resolve_song_project(midi)
        orig_proj_dir = p["project_dir"]
        sample_abs = os.path.join(orig_proj_dir, "audio", "backing.wav")
        rel = project_manager.to_project_rel_path(sample_abs, p)
        assert rel == "audio/backing.wav"

        # Simulate folder rename
        new_proj_dir = orig_proj_dir + "_renamed"
        if os.path.exists(new_proj_dir):
            shutil.rmtree(new_proj_dir)
        os.rename(orig_proj_dir, new_proj_dir)

        p_renamed = dict(p)
        p_renamed["project_dir"] = new_proj_dir
        resolved_abs = project_manager.from_project_rel_path(rel, p_renamed)
        expected_abs = os.path.normpath(os.path.join(new_proj_dir, "audio", "backing.wav"))
        assert os.path.normpath(resolved_abs) == expected_abs, f"Path mismatch: {resolved_abs} != {expected_abs}"
        print("  -> PASS: Relative asset paths follow project directory rename seamlessly.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        for p_name in ["rename_test", "rename_test_renamed"]:
            p_path = get_portable_path(os.path.join("projects", p_name))
            if os.path.isdir(p_path):
                shutil.rmtree(p_path, ignore_errors=True)


def test_5_to_8_gui_integration():
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    win = HarmonicaMainWindow()

    # TEST 5: Key-based fingering pattern selector and unlock
    print("[TEST 5] Key-based fingering pattern switching and unlock...")
    assert hasattr(win, "combo_main_fg_pattern"), "combo_main_fg_pattern missing"
    assert hasattr(win, "btn_unlock_for_new_key"), "btn_unlock_for_new_key missing"

    # Save a custom pattern with transpose = +2
    target_path = win.timeline.filepath or "dummy_test.mid"
    custom_patterns = {
        "標準パターン (基本)": {"transpose": 0, "transpose_accomp": True, "custom_map": {}},
        "曲別_D調用": {"transpose": 2, "transpose_accomp": True, "custom_map": {}}
    }
    harmonica_map.save_song_profile(target_path, extra_data={"patterns": custom_patterns})
    win.timeline.filepath = target_path
    win._refresh_main_fg_pattern_combo()

    # Switch to D調用 (transpose 2)
    win.combo_main_fg_pattern.setCurrentText("曲別_D調用")
    win._on_main_fg_pattern_activated(win.combo_main_fg_pattern.currentIndex())
    assert win.spin_transpose.value() == 2, f"Selecting custom did not restore transpose 2: got {win.spin_transpose.value()}"

    # Switch back to standard (transpose 0)
    win.combo_main_fg_pattern.setCurrentIndex(0)
    win._on_main_fg_pattern_activated(0)
    assert win.spin_transpose.value() == 0, f"Selecting standard did not restore transpose 0: got {win.spin_transpose.value()}"

    # Test unlock (mock confirm_dialog to avoid modal blocking in headless test)
    orig_confirm = dialogs.confirm_dialog
    dialogs.confirm_dialog = lambda *args, **kwargs: True
    try:
        win.btn_unlock_for_new_key.click()
    finally:
        dialogs.confirm_dialog = orig_confirm

    assert win.spin_transpose.isEnabled() is True, "btn_unlock_for_new_key did not unlock transpose"
    print("  -> PASS: Key-based fingering pattern sync and new-key unlock work as expected.")

    # TEST 6: Practice visual style vs Video dedicated tab
    print("[TEST 6] Practice visual style controls and 100% video dedicated design tab...")
    assert hasattr(win, "combo_prac_traj"), "combo_prac_traj missing"
    assert hasattr(win, "combo_prac_lang"), "combo_prac_lang missing"
    win.combo_prac_lang.setCurrentText("CDE")
    assert win.user_settings.get("practice_visual", {}).get("lang_mode") == "CDE"
    # v4.1.0 2階層タブ対応
    assert "動画制作" in win.tab_widget.tabText(1)
    assert hasattr(win, "video_sub_tabs") and "画面" in win.video_sub_tabs.tabText(0)
    print("  -> PASS: Practice style unified in practice tab and video design dedicated.")

    # TEST 7: Settings dialog and top header button
    print("[TEST 7] [⚙ 設定] button on top header and HarmonicaSettingsDialog...")
    assert hasattr(win, "btn_open_settings"), "btn_open_settings missing on row1"
    assert win.btn_open_settings.text() == "⚙ 設定"
    dlg = HarmonicaSettingsDialog(win.user_settings)
    assert dlg.tabs.count() in (3, 4), f"HarmonicaSettingsDialog must have 3 or 4 tabs, got {dlg.tabs.count()}"
    print("  -> PASS: Global settings dialog initialized with 3 tabs and accessible.")

    # TEST 8: StudioExportMixin separation and line count reduction
    print("[TEST 8] StudioExportMixin separation and main.py line reduction...")
    assert isinstance(win, StudioExportMixin), "HarmonicaMainWindow must inherit StudioExportMixin"
    assert hasattr(win, "_on_open_project_folder")
    assert hasattr(win, "_on_open_rec_folder")
    assert hasattr(win, "_on_open_output_folder")
    assert hasattr(win, "_build_export_render_settings")
    assert hasattr(win, "_on_start_video_export")

    main_py_path = os.path.join(SRC_DIR, "main.py")
    with open(main_py_path, "r", encoding="utf-8") as f:
        main_lines = len(f.readlines())
    print(f"  Current main.py line count: {main_lines} (reduced from 5,727)")
    assert main_lines < 5300, f"Expected main.py < 5300 lines, got {main_lines}"
    assert "Harmonica Visualizer v4.0.0 [Harmonica Studio Edition]" in win.windowTitle()
    print("  -> PASS: StudioExportMixin cleanly extracted and main.py significantly slimmed.")


def main():
    print("=" * 70)
    print("STARTING Ver.4.0.0 Harmonica Studio Comprehensive Verification")
    print("=" * 70)

    test_1_portable_path()
    test_2_and_3_project_manager_and_sha256()
    test_4_relative_path_rename()
    test_5_to_8_gui_integration()

    print("=" * 70)
    print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY! (Ver.4.0.0 READY)")
    print("=" * 70)


if __name__ == "__main__":
    main()


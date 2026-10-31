# -*- coding: utf-8 -*-
"""
studio_controller.py - Harmonica Visualizer v4.0 Harmonica Studio
録音制御、外部伴奏同期、オーディオミキサー、動画エクスポート、
および楽曲プロジェクトフォルダ（takes / exports / audio）直結制御を提供する Mixin クラス。
"""

import os
import sys
import time
import json
import re
import traceback
import subprocess
import numpy as np
import pygame
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog

import settings_manager
import project_manager
from config import get_portable_path
from ipc_state import SharedClockBridge
from audio_engine import load_external_audio_pcm, synthesize_midi_to_wav, apply_harmonica_reverb_numpy, resolve_clean_recording_path, get_reverb_cache_path
from video_exporter import (
    check_ffmpeg_available,
    VideoExportThread,
    OffscreenVisualizerRenderer,
    calc_export_resolution,
)
from dialogs import AudioTrackMixerDialog, ExportProgressDialog, SingleFramePreviewDialog


class StudioExportMixin:
    """メインウィンドウに多重継承してスタジオ録音・伴奏・動画エクスポート機能を提供する Mixin"""

    # -------------------------------------------------------------------------
    # フォルダ操作・プロジェクト直結
    # -------------------------------------------------------------------------
    def _on_open_project_folder(self):
        """現在アクティブな楽曲プロジェクトフォルダを開く"""
        p_dir = project_manager.get_active_project_dir() or get_portable_path("projects")
        os.makedirs(p_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(p_dir)))

    def _on_open_rec_folder(self):
        """録音フォルダ（プロジェクト takes/ または recordings/）を開く"""
        rec_dir = project_manager.get_active_takes_dir() or get_portable_path("recordings")
        os.makedirs(rec_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(rec_dir)))

    def _on_open_output_folder(self):
        """動画出力先フォルダ（プロジェクト exports/ または exports/）を開く"""
        out_dir = project_manager.get_active_exports_dir() or get_portable_path("exports")
        os.makedirs(out_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(out_dir)))

    def _build_export_render_settings(self, preset: dict = None) -> dict:
        """動画制作の現在作業状態（または引数指定プリセット）から動画レンダラー向け設定辞書を統一生成 (HIGH-2)"""
        if preset is None:
            preset = settings_manager.get_working_video_state(self.user_settings)

        exp_style = preset.get("export_style", self.combo_exp_style.currentText() if hasattr(self, "combo_exp_style") else "完成動画 (背景・タイトル合成)")
        bg_col = preset.get("export_bg_color", self.combo_exp_bg.currentText() if hasattr(self, "combo_exp_bg") else "ノーマル（黒）")
        reverb_on = self.chk_reverb.isChecked() if hasattr(self, "chk_reverb") else False

        return {
            "inst_type": self.inst_combo.currentText(),
            "trajectory_mode": preset.get("trajectory_mode", "3段階 (練習標準)"),
            "lang_mode": preset.get("lang_mode", "ドレミ"),
            "lever_deco_mode": preset.get("lever_deco_mode", "センターライン (芯線)"),
            "note_speed_ratio": self.gl_widget.note_speed_ratio,
            "default_bpm": getattr(self.timeline, "default_bpm", 120.0),
            "show_notes": preset.get("show_notes", True),
            "show_grid": preset.get("show_grid", True),
            "show_bar_lines": preset.get("show_bar_lines", True),
            "show_grid4": preset.get("grid4_mode", "4音グリッド表示"),
            "show_hole_num": preset.get("show_hole_num", True),
            "hole_num_style": preset.get("hole_num_style", "実機標準 (低音ドット付)"),
            "show_legend": preset.get("show_legend", False),
            "show_lookahead": preset.get("show_lookahead", True),
            "use_ring": preset.get("show_ring", True),
            "show_glow": preset.get("show_glow", True),
            "note_opacity": preset.get("note_opacity", 100),
            "color_blow": preset.get("color_blow", "#FF5500"),
            "color_draw": preset.get("color_draw", "#00BFFF"),
            "canvas_bg_color": bg_col if "クロマキー" in exp_style else "#0d0d0d",
            "export_style": exp_style,
            "skin_enabled": preset.get("skin_enabled", True),
            "skin_mouthpiece_path": preset.get("skin_mouthpiece_path", "") or getattr(self.gl_widget, "skin_mouthpiece_path", ""),
            "skin_lever_off_path": preset.get("skin_lever_off_path", "") or getattr(self.gl_widget, "skin_lever_off_path", ""),
            "skin_lever_on_path": preset.get("skin_lever_on_path", "") or getattr(self.gl_widget, "skin_lever_on_path", ""),
            "bg_image_path": preset.get("bg_image_path", ""),
            "bg_fit_mode": preset.get("bg_fit_mode", "中央トリミング (画面いっぱい)"),
            "bg_rotation": preset.get("bg_rotation", 0),
            "bg_dim_ratio": preset.get("bg_dim_ratio", 60),
            "bg_image_enabled": preset.get("bg_image_enabled", True),
            "reverb_enabled": reverb_on,
            "vertical_layout_mode": preset.get("vertical_layout_mode", self.combo_vertical_layout.currentText() if hasattr(self, "combo_vertical_layout") else "全画面フル展開 (標準Shorts)"),
        }

    # =========================================================================
    # 設定の反映と永続化
    # =========================================================================

    def _refresh_live_audition_reverb(self):
        """試聴停止し設定反映"""
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")

    def _set_active_recorded_take(self, file_path: str):
        """アクティブな録音テイクを設定・UI反映"""
        if not file_path or not os.path.exists(file_path):
            self.last_recorded_path = None
            self._rec_pcm = None
            if hasattr(self, "lbl_rec_take"):
                self.lbl_rec_take.setText("録音テイク: 未録音")
                self.lbl_rec_take.setStyleSheet("color: #64748B; font-size: 11px;")
            if hasattr(self, "btn_rec_listen"):
                self.btn_rec_listen.setEnabled(False)
            if hasattr(self, "_update_mixer_summary_label"):
                self._update_mixer_summary_label()
            return

        file_path = os.path.normpath(file_path).replace("\\", "/")
        self.last_recorded_path = file_path
        self._rec_pcm = None
        take_name = os.path.basename(file_path)
        if hasattr(self, "_set_elided_label_text") and hasattr(self, "lbl_rec_take"):
            self._set_elided_label_text(self.lbl_rec_take, f"採用テイク: {take_name}", file_path, max_width=310)
            self.lbl_rec_take.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        if hasattr(self, "btn_rec_listen"):
            self.btn_rec_listen.setEnabled(True)
        if hasattr(self, "_update_mixer_summary_label"):
            self._update_mixer_summary_label()

    def _on_select_rec_take(self):
        rec_dir = project_manager.get_active_takes_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "採用する録音テイク (WAV) を選択",
            rec_dir,
            "WAV Audio (*.wav);;Audio Files (*.wav *.mp3 *.flac *.m4a)"
        )
        if not file_path:
            return
        self._set_active_recorded_take(file_path)
        take_name = os.path.basename(self.last_recorded_path)
        self.lbl_status_msg.setText(f"📂 録音テイクを採用しました: {take_name}")
        self._save_current_song_profile()

    def _on_reverb_toggled(self, checked: bool):
        self.reverb_enabled = bool(checked)
        self.user_settings["reverb_enabled"] = self.reverb_enabled
        self._rec_pcm = None  # キャッシュ破棄
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("✨ リバーブ有効状態を変更しました ([▶ 試聴] で確認)")
        else:
            self.lbl_status_msg.setText(f"✨ リバーブ: {'有効' if checked else '無効'} ([▶ 試聴] で確認)")
        if getattr(self, "_rec_sync_monitoring", False) and hasattr(self, "_rec_resync_timer"):
            self._rec_resync_timer.start()
        self._save_current_settings()

    def _on_reverb_type_changed(self, r_type: str):
        is_on = (r_type != "なし (オフ)")
        if hasattr(self, "chk_reverb"):
            self.chk_reverb.blockSignals(True)
            self.chk_reverb.setChecked(is_on)
            self.chk_reverb.blockSignals(False)
        if hasattr(self, "slider_reverb_wet"):
            self.slider_reverb_wet.setEnabled(is_on)
        self.reverb_enabled = is_on
        self.user_settings["reverb_enabled"] = is_on
        if is_on:
            self.reverb_type = str(r_type)
            self.user_settings["reverb_type"] = self.reverb_type
        self._rec_pcm = None  # キャッシュ破棄
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            if hasattr(self, "btn_rec_listen"):
                self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("✨ リバーブ設定を変更しました ([▶ 試聴] で確認)")
        else:
            self.lbl_status_msg.setText(f"✨ リバーブ: {r_type} ([▶ 試聴] で確認)")
        if getattr(self, "_rec_sync_monitoring", False) and hasattr(self, "_rec_resync_timer"):
            self._rec_resync_timer.start()
        self._save_current_settings()

    def _on_reverb_slider_changed(self, val: int):
        self.reverb_wet_pct = int(val)
        self.lbl_reverb_wet.setText(f"深さ: {val}%")
        self.user_settings["reverb_wet_pct"] = self.reverb_wet_pct
        self._rec_pcm = None  # キャッシュ破棄
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            self.btn_rec_listen.setText("▶ 試聴")
            self.lbl_status_msg.setText("✨ リバーブ深さを変更しました ([▶ 試聴] で確認)")
        if getattr(self, "_rec_sync_monitoring", False) and hasattr(self, "_rec_resync_timer"):
            self._rec_resync_timer.start()
        self._save_current_settings()

    def _on_select_ext_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "伴奏・外部音源を選択", "",
            "オーディオファイル (*.mp3 *.wav *.m4a *.ogg *.flac *.aac);;全ファイル (*)"
        )
        if path:
            self._set_ext_audio(path)

    def _ensure_ext_pcm_loaded(self):
        """外部音源のPCMデータをメモリにキャッシュロード"""
        if getattr(self, "_ext_pcm", None) is not None:
            return self._ext_pcm
        if getattr(self, "ext_audio_path", "") and os.path.isfile(self.ext_audio_path):
            try:
                self._ext_pcm = load_external_audio_pcm(self.ext_audio_path, sample_rate=44100)
                return self._ext_pcm
            except Exception as e:
                print(f"[ExtAudio Load Error] {e}")
                self._ext_pcm = None
        return None

    def _stop_ext_playback(self):
        """外部音源の再生を安全に停止"""
        try:
            if hasattr(self, "_ext_channel") and self._ext_channel is not None:
                self._ext_channel.stop()
            self._ext_pending_start = False
        except Exception:
            pass

    def _set_ext_audio(self, path: str):
        if not path or not os.path.isfile(path):
            return
        self.ext_audio_path = path
        self.user_settings["ext_audio_path"] = path
        self._ext_pcm = None
        self._ensure_ext_pcm_loaded()

        base_name = os.path.basename(path)
        self._set_elided_label_text(self.lbl_ext_audio, base_name, path, max_width=290)
        self.lbl_ext_audio.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px; background-color: #121218; border: 1px solid #22222E; border-radius: 3px; padding: 2px 6px;")
        if hasattr(self, "lbl_prac_ext_status"):
            self.lbl_prac_ext_status.setText(f"伴奏音源: {base_name}")
            self.lbl_prac_ext_status.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        self.btn_ext_audition.setEnabled(True)
        self.btn_ext_restart.setEnabled(True)
        self.btn_ext_stop.setEnabled(True)
        self._save_current_song_profile()
        self.lbl_status_msg.setText(f"🎵 伴奏音源を設定しました: {base_name}")
        self._save_current_settings()

    def _on_clear_ext_audio(self):
        self.ext_audio_path = ""
        self.user_settings["ext_audio_path"] = ""
        self._ext_pcm = None
        self._stop_ext_playback()
        self.lbl_ext_audio.setText("未選択 (MP3/WAV等をD&D可)")
        self.lbl_ext_audio.setToolTip("")
        self.lbl_ext_audio.setStyleSheet("color: #64748B; font-size: 11px; background-color: #121218; border: 1px solid #22222E; border-radius: 3px; padding: 2px 6px;")
        if hasattr(self, "lbl_prac_ext_status"):
            self.lbl_prac_ext_status.setText("伴奏音源: 未設定 (MIDIガイド再生)")
            self.lbl_prac_ext_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.btn_ext_audition.setEnabled(False)
        self.btn_ext_restart.setEnabled(False)
        self.btn_ext_stop.setEnabled(False)
        self._save_current_song_profile()
        self.lbl_status_msg.setText("伴奏音源を解除しました")
        self._save_current_settings()

    def _on_ext_mode_changed(self, mode: str):
        self.ext_audio_mode = str(mode)
        self.user_settings["ext_audio_mode"] = self.ext_audio_mode

        for combo_name in ("combo_ext_mode", "combo_prac_audio_mode"):
            combo = getattr(self, combo_name, None)
            if combo is not None and combo.currentText() != mode:
                combo.blockSignals(True)
                combo.setCurrentText(mode)
                combo.blockSignals(False)

        is_mute = ("ガイド音のみ" in mode or "伴奏ミュート" in mode or "外部音源オフ" in mode)
        if is_mute:
            self._stop_ext_playback()
        elif self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
            cur_sec = self.clock.get_current_base_sec()
            self._sync_ext_audio_playback(True, cur_sec)

        if "伴奏のみ" in mode or "外部音源のみ" in mode:
            self.audio_engine.set_midi_notes_muted(True)
        else:
            self.audio_engine.set_midi_notes_muted(False)
        self._save_current_settings()

    def _on_ext_vol_changed(self, val: int):
        self.ext_volume = int(val)
        self.lbl_ext_vol.setText(f"{val}%")
        self.user_settings["ext_audio_volume"] = val
        try:
            v = max(0.0, min(1.0, (val / 100.0) * (self.vol_slider.value() / 100.0)))
            if hasattr(self, "_ext_channel") and self._ext_channel is not None:
                self._ext_channel.set_volume(v)
        except Exception:
            pass
        self._save_current_settings()

    def _get_current_mixer_settings(self) -> dict:
        """現在のミキサー設定ディクショナリを取得 (常に最新のUI状態を同期反映)"""
        ext_path = getattr(self, "ext_audio_path", "")
        rec_path = getattr(self, "last_recorded_path", "")
        has_ext = bool(ext_path and os.path.isfile(ext_path))
        has_rec = bool(rec_path and os.path.isfile(rec_path))

        if not hasattr(self, "_mixer_settings") or not isinstance(self._mixer_settings, dict):
            self._mixer_settings = {
                "track_ext_enabled": has_ext,
                "track_ext_path": ext_path,
                "track_ext_vol": int(self.slider_ext_vol.value()) if hasattr(self, "slider_ext_vol") else 100,
                "track_ext_offset_ms": int(self.spin_ext_offset.value()) if hasattr(self, "spin_ext_offset") else 0,

                "track_rec_enabled": has_rec,
                "track_rec_path": rec_path,
                "track_rec_vol": 100,
                "track_rec_reverb": bool(self.chk_reverb.isChecked()) if hasattr(self, "chk_reverb") else False,
                "track_rec_offset_ms": int(self.spin_rec_offset.value()) if hasattr(self, "spin_rec_offset") else 0,

                "track_midi_enabled": not has_ext and not has_rec,
                "track_midi_mode": "全パート再生",
                "track_midi_vol": int(self.vol_slider.value()) if hasattr(self, "vol_slider") else 100,
                "track_midi_offset_ms": 0,
            }
        else:
            if ext_path:
                self._mixer_settings["track_ext_path"] = ext_path
            if rec_path:
                self._mixer_settings["track_rec_path"] = rec_path
            if hasattr(self, "spin_ext_offset"):
                self._mixer_settings["track_ext_offset_ms"] = int(self.spin_ext_offset.value())
            if hasattr(self, "spin_rec_offset"):
                self._mixer_settings["track_rec_offset_ms"] = int(self.spin_rec_offset.value())
            if hasattr(self, "chk_reverb"):
                self._mixer_settings["track_rec_reverb"] = bool(self.chk_reverb.isChecked())

        self._mixer_settings["track_rec_reverb_type"] = self.user_settings.get("reverb_type", "標準ルーム (自然な部屋鳴り)")
        self._mixer_settings["track_rec_reverb_wet"] = int(self.user_settings.get("reverb_wet_pct", 35))

        return self._mixer_settings

    def _update_mixer_summary_label(self):
        """動画出力タブのミキサー概要テキストを更新"""
        if not hasattr(self, "lbl_mixer_summary"):
            return
        cfg = self._get_current_mixer_settings()
        parts = []
        if cfg.get("track_ext_enabled", False):
            parts.append(f"伴奏({cfg.get('track_ext_vol', 100)}%)")
        if cfg.get("track_rec_enabled", False):
            rev_str = "・Rev" if cfg.get("track_rec_reverb", False) else ""
            parts.append(f"録音({cfg.get('track_rec_vol', 100)}%{rev_str})")
        if cfg.get("track_midi_enabled", False):
            parts.append(f"MIDI({cfg.get('track_midi_vol', 100)}%)")
        if not parts:
            parts.append("無音")
        self.lbl_mixer_summary.setText("構成: " + " + ".join(parts))

        # 課題 56: クイック指定コンボとの双方向自動同期
        ext_on = cfg.get("track_ext_enabled", False)
        rec_on = cfg.get("track_rec_enabled", False)
        midi_on = cfg.get("track_midi_enabled", False)
        active_count = sum([ext_on, rec_on, midi_on])

        if hasattr(self, "combo_exp_audio"):
            self.combo_exp_audio.blockSignals(True)
            if active_count > 1:
                self.combo_exp_audio.setCurrentText("🎛️ カスタム (ミキサー詳細設定)")
            elif active_count == 1:
                if ext_on:
                    self.combo_exp_audio.setCurrentText("伴奏音源 (外部音源優先)")
                elif rec_on:
                    self.combo_exp_audio.setCurrentText("マイク録音テイク (演奏収録)")
                elif midi_on:
                    self.combo_exp_audio.setCurrentText("MIDIガイド音 (内部音源)")
            else:
                self.combo_exp_audio.setCurrentText("無音 (映像のみ)")
            self.combo_exp_audio.blockSignals(False)

    def _on_quick_audio_source_changed(self, choice: str):
        """クイック指定コンボが切り替えられた際にミキサー設定を追従"""
        cfg = self._get_current_mixer_settings()
        if "カスタム" in choice:
            pass  # カスタム選択時は現在のミキサー設定をそのまま維持
        elif "無音" in choice:
            cfg["track_ext_enabled"] = False
            cfg["track_rec_enabled"] = False
            cfg["track_midi_enabled"] = False
        elif "マイク録音" in choice:
            cfg["track_ext_enabled"] = False
            cfg["track_rec_enabled"] = True
            cfg["track_midi_enabled"] = False
        elif "伴奏音源" in choice:
            cfg["track_ext_enabled"] = True
            cfg["track_rec_enabled"] = False
            cfg["track_midi_enabled"] = False
        elif "MIDI" in choice:
            cfg["track_ext_enabled"] = False
            cfg["track_rec_enabled"] = False
            cfg["track_midi_enabled"] = True
        self._update_mixer_summary_label()

    def _on_open_audio_mixer_dialog(self):
        """音声トラック・ミキサーダイアログを開く"""
        cfg = self._get_current_mixer_settings()
        dlg = AudioTrackMixerDialog(cfg, timeline=self.timeline, parent=self)
        res = dlg.exec()
        res_settings = getattr(dlg, "result_settings", None)
        dlg.deleteLater()
        if res and res_settings:
            self._mixer_settings = res_settings
            self._update_mixer_summary_label()
            self.lbl_status_msg.setText("🎚️ 音声トラック・ミキサー設定を更新しました")
            self._save_current_settings()

    def _on_audition_export_volume(self):
        """動画音声音量＆ミキサーの5秒プレビュー試聴（課題32前半 / HIGH-1）"""
        # 既に再生中なら停止
        if hasattr(self, "audition_player") and self.audition_player.is_playing():
            self.audition_player.stop()
            if hasattr(self, "_exp_audition_timer"):
                self._exp_audition_timer.stop()
            if hasattr(self, "btn_exp_vol_audition"):
                self.btn_exp_vol_audition.setText("▶ 音量試聴 (5秒)")
            self.lbl_status_msg.setText("⏹ 音量試聴を停止しました")
            return

        cfg = self._get_current_mixer_settings()
        if not cfg.get("track_ext_enabled", False) and not cfg.get("track_rec_enabled", False) and not cfg.get("track_midi_enabled", False):
            self.lbl_status_msg.setText("⚠️ 有効な音声トラックが選択されていません")
            return

        pos_mode = self.combo_exp_audition_pos.currentText() if hasattr(self, "combo_exp_audition_pos") else ""
        total_sec = float(getattr(self.timeline, "total_duration_sec", 60.0)) if hasattr(self, "timeline") and self.timeline else 60.0
        if "中間" in pos_mode:
            start_sec = max(0.0, total_sec * 0.45)
        else:  # 発音開始から5秒
            start_sec = 0.0
            earliest_notes = []
            if hasattr(self, "timeline") and self.timeline:
                if getattr(self.timeline, "main_notes", None):
                    earliest_notes.append(min(
                        float(n.get("start_sec", 0.0) if isinstance(n, dict) else getattr(n, "start_sec", 0.0))
                        for n in self.timeline.main_notes
                    ))
                if getattr(self.timeline, "accomp_notes", None):
                    earliest_notes.append(min(
                        float(n.get("start_sec", 0.0) if isinstance(n, dict) else getattr(n, "start_sec", 0.0))
                        for n in self.timeline.accomp_notes
                    ))
            if earliest_notes:
                start_sec = max(0.0, min(earliest_notes) - 0.2)

        if hasattr(self, "btn_exp_vol_audition"):
            self.btn_exp_vol_audition.setText("⏳ 合成中...")
        QApplication.processEvents()

        temp_dir = get_portable_path("temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_wav = os.path.join(temp_dir, f"exp_vol_audition_{int(time.time())}.wav")

        try:
            midi_notes = self.timeline.main_notes if hasattr(self, "timeline") and self.timeline else []
            acc_notes = self.timeline.accomp_notes if hasattr(self, "timeline") and self.timeline else []
            measures = self.timeline.measures_timeline if hasattr(self, "timeline") and self.timeline else []

            synthesize_midi_to_wav(
                midi_notes=midi_notes,
                current_bpm=120.0,
                max_duration=5.0,
                is_count_in=False,
                is_metro=False,
                output_wav_path=temp_wav,
                measures_timeline=measures,
                sample_rate=44100,
                accompaniment_notes=acc_notes,
                sec_a_in_song=start_sec,
                mixer_settings=cfg,
                yt_limiter=bool(self.chk_yt_limiter.isChecked()) if hasattr(self, "chk_yt_limiter") else True,
                synth_engine=self.user_settings.get("synth_engine", "Windows標準MIDI (推奨)")
            )

            vol_val = self.slider_exp_audio_vol.value() / 100.0 if hasattr(self, "slider_exp_audio_vol") else 1.0
            if hasattr(self, "audition_player"):
                self.audition_player.play(temp_wav, volume=vol_val)

            if not hasattr(self, "_exp_audition_timer"):
                self._exp_audition_timer = QTimer(self)
                self._exp_audition_timer.setSingleShot(True)
                def _on_exp_audition_timeout():
                    if hasattr(self, "audition_player") and self.audition_player.is_playing():
                        self.audition_player.stop()
                    if hasattr(self, "btn_exp_vol_audition"):
                        self.btn_exp_vol_audition.setText("▶ 音量試聴 (5秒)")
                    self.lbl_status_msg.setText("⏹ 音量試聴が完了しました")
                self._exp_audition_timer.timeout.connect(_on_exp_audition_timeout)

            self._exp_audition_timer.start(5200)
            if hasattr(self, "btn_exp_vol_audition"):
                self.btn_exp_vol_audition.setText("⏹ 試聴停止")
            self.lbl_status_msg.setText(f"🔊 動画音声音量を試聴中 ({int(vol_val * 100)}%, 5秒間)")
        except Exception as e:
            if hasattr(self, "btn_exp_vol_audition"):
                self.btn_exp_vol_audition.setText("▶ 音量試聴 (5秒)")
            self.lbl_status_msg.setText(f"❌ 音量試聴合成エラー: {e}")

    def _apply_youtube_volume_preset(self):
        """YouTube音声仕様（目標 -14.0 LUFS / True Peak -1.0 dBFS）に基づき、動画出力全体の音量を自動測定・最適化"""
        if (not hasattr(self, "timeline") or not self.timeline or self.timeline.total_duration_sec <= 0) and \
           (not getattr(self, "ext_audio_path", "") or not os.path.isfile(self.ext_audio_path)):
            QMessageBox.information(self, "音量解析", "解析対象の楽曲（MIDI）または外部音声ファイルが読み込まれていません。")
            return

        # 音声ソース判定
        audio_choice = self.combo_exp_audio.currentText() if hasattr(self, "combo_exp_audio") else "MIDIガイド音 (内部音源)"
        if "無音" in audio_choice:
            QMessageBox.information(self, "YouTube音量 自動解析", "動画の音声ソースが「無音」に設定されているため、音量解析は不要です。")
            return

        self.lbl_status_msg.setText("⏳ YouTube音量を解析中 (FFmpegラウドネス測定)...")
        QApplication.processEvents()

        temp_wav = get_portable_path(os.path.join("temp", f"yt_loudness_test_{int(time.time())}.wav"))
        os.makedirs(os.path.dirname(temp_wav), exist_ok=True)

        try:
            # 1. 出力範囲の特定 (動画出力設定の指定範囲と一致させる)
            start_sec = max(0.0, float(self.spin_exp_start.value())) if hasattr(self, "spin_exp_start") else 0.0
            end_sec = float(self.spin_exp_end.value()) if hasattr(self, "spin_exp_end") else (self.timeline.total_duration_sec if self.timeline else 60.0)
            if end_sec <= start_sec:
                end_sec = float(getattr(self.timeline, "total_duration_sec", start_sec + 60.0))
            duration_sec = max(0.5, end_sec - start_sec)

            # 2. 外部音声ソースの選定とPCM読み込み
            audio_path = ""
            if "伴奏音源" in audio_choice:
                if getattr(self, "ext_audio_path", "") and os.path.isfile(self.ext_audio_path):
                    audio_path = self.ext_audio_path
                elif getattr(self, "last_recorded_path", "") and os.path.isfile(self.last_recorded_path):
                    audio_path = self.last_recorded_path
            elif "マイク録音" in audio_choice:
                if getattr(self, "last_recorded_path", "") and os.path.isfile(self.last_recorded_path):
                    audio_path = self.last_recorded_path
                elif getattr(self, "ext_audio_path", "") and os.path.isfile(self.ext_audio_path):
                    audio_path = self.ext_audio_path

            ext_pcm = None
            if audio_path and os.path.isfile(audio_path):
                try:
                    ext_pcm = load_external_audio_pcm(audio_path, sample_rate=44100)
                except Exception as e:
                    print(f"[YouTube Preset] 外部音源読み込みエラー: {e}")

            ext_audio_mode = getattr(self, "ext_audio_mode", "頭出し確認 (再生:両方 / 動画:外部のみ)")
            if ("伴奏音源" in audio_choice or "マイク録音" in audio_choice) and ext_pcm is not None:
                ext_audio_mode = "動画:外部のみ"

            part_mode = self.part_combo.currentText() if hasattr(self, "part_combo") else "全パート再生"

            # 3. 音声トラック合成 (基準ボリューム100%かつリミッターなしで生特性を測定)
            synthesize_midi_to_wav(
                midi_notes=self.timeline.main_notes if self.timeline else [],
                current_bpm=self.timeline.default_bpm if self.timeline else 120.0,
                max_duration=duration_sec,
                is_count_in=False,
                is_metro=False,
                output_wav_path=temp_wav,
                sample_rate=44100,
                accompaniment_notes=self.timeline.accomp_notes if self.timeline else [],
                part_play_mode=part_mode,
                ext_audio_pcm=ext_pcm,
                ext_audio_mode=ext_audio_mode,
                ext_audio_offset_ms=self.spin_ext_offset.value() if hasattr(self, "spin_ext_offset") else 0,
                ext_audio_vol_pct=float(self.slider_ext_vol.value()) if hasattr(self, "slider_ext_vol") else 100.0,
                sec_a_in_song=start_sec,
                yt_limiter=False,
                mixer_settings=self._get_current_mixer_settings(),
                synth_engine=self.user_settings.get("synth_engine", "Windows標準MIDI (推奨)")
            )

            # 4. FFmpeg loudnormフィルターによるITU-R BS.1770規格ラウドネス解析
            cmd = [
                "ffmpeg", "-hide_banner",
                "-i", temp_wav,
                "-af", "loudnorm=I=-14.0:TP=-1.0:print_format=json",
                "-f", "null", "-"
            ]
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)
            match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', proc.stderr)
            if not match:
                raise RuntimeError("FFmpegによるラウドネス解析データの取得に失敗しました。")

            data = json.loads(match.group(0))
            input_i = float(data.get("input_i", -99.0))
            input_tp = float(data.get("input_tp", -99.0))

            if input_i <= -70.0:
                QMessageBox.warning(
                    self,
                    "YouTube音量 自動解析",
                    f"測定された音声が無音または極めて小さいレベルです ({input_i:.1f} LUFS)。\n"
                    f"現在の音量設定を変更せずに維持しました。"
                )
                self.lbl_status_msg.setText("準備完了")
                return

            gain_lufs_db = -14.0 - input_i
            max_peak_gain_db = -1.0 - input_tp
            diff_db = min(gain_lufs_db, max_peak_gain_db)
            gain_linear = 10.0 ** (diff_db / 20.0)
            opt_vol_pct = max(10, min(200, int(round(100.0 * gain_linear))))

            # 5. UIへの反映
            if hasattr(self, "slider_exp_audio_vol"):
                self.slider_exp_audio_vol.setValue(opt_vol_pct)
            if hasattr(self, "chk_yt_limiter"):
                self.chk_yt_limiter.setChecked(True)

            sign_str = f"+{diff_db:.1f}" if diff_db > 0 else f"{diff_db:.1f}"
            status_text = f"YouTube最適化完了: 測定 {input_i:.1f} LUFS ➔ 音量 {opt_vol_pct}% ({sign_str} dB)"
            self.lbl_status_msg.setText(status_text)
            self._save_current_settings()

            QMessageBox.information(
                self,
                "YouTube音量 自動解析・最適化",
                f"【YouTube音量 最適化完了】\n\n"
                f"・測定ラウドネス: {input_i:.1f} LUFS （YouTube目標: -14.0 LUFS）\n"
                f"・測定トゥルーピーク: {input_tp:.1f} dBFS （上限基準: -1.0 dBFS）\n\n"
                f"▶ 推奨音量補正: {sign_str} dB ➔ 「動画音声音量」を 【 {opt_vol_pct}% 】 に自動設定しました。\n"
                f"▶ 音割れ防止リミッター: 【 有効 (ON) 】 にセットしました。\n\n"
                f"※YouTubeの自動音量減衰を受けず、最高のダイナミクスと音質で再生されます。"
            )
        except Exception as e:
            print(f"[YouTube Audio Analyzer Error] {e}")
            self.lbl_status_msg.setText(f"YouTube音量解析エラー: {e}")
            QMessageBox.warning(self, "音量解析エラー", f"音量解析中にエラーが発生しました:\n{e}\n\n現在の音量設定を維持します。")
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

    def _on_ext_offset_changed(self, val: int):
        try:
            self.ext_offset_ms = int(val)
            self.user_settings["ext_audio_offset_ms"] = val

            # 再生中の場合、前奏カウントイン中(cur_sec < 0)でなければデバウンス同期を起動
            if self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
                cur_sec = self.clock.get_current_base_sec()
                if cur_sec >= 0.0:
                    self._ext_resync_timer.start()

            # 設定・プロファイルの保存をデバウンス (連打時のディスクI/O競合を抑制)
            self._ext_save_timer.start()
        except Exception as e:
            print(f"[ExtAudio Offset Error] {e}")

    def _do_ext_audio_resync(self):
        try:
            if self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
                cur_sec = self.clock.get_current_base_sec()
                self._sync_ext_audio_playback(True, cur_sec)
        except Exception as e:
            print(f"[ExtAudio Offset Resync Warning] {e}")

    def _do_ext_offset_save(self):
        try:
            self._save_current_song_profile()
            self._save_current_settings()
        except Exception as e:
            print(f"[ExtAudio Offset Save Error] {e}")

    def _on_ext_offset_adjust(self, delta_ms: int):
        try:
            new_val = self.spin_ext_offset.value() + int(delta_ms)
            self.spin_ext_offset.setValue(max(-5000, min(5000, new_val)))
        except Exception as e:
            print(f"[ExtAudio Offset Adjust Error] {e}")

    def _sync_ext_audio_playback(self, is_playing: bool, target_sec: float = None):
        """外部音源をタイムラインと完全同期再生/一時停止 (PCMスライス再生方式)"""
        pcm = self._ensure_ext_pcm_loaded()
        if pcm is None or len(pcm) == 0:
            return

        mode = getattr(self, "ext_audio_mode", "")
        if "外部音源オフ" in mode or "ガイド音のみ" in mode or "伴奏ミュート" in mode:
            self._stop_ext_playback()
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

            if not hasattr(self, "_ext_channel") or self._ext_channel is None:
                self._ext_channel = pygame.mixer.Channel(1)

            cur_sec = self.clock.get_current_base_sec() if target_sec is None else target_sec
            offset_sec = float(self.spin_ext_offset.value()) / 1000.0
            # 共通計算式: src_sec = cur_sec - offset_sec (+offsetで遅らせる / -offsetで早める)
            src_sec = cur_sec - offset_sec
            vol = max(0.0, min(1.0, (self.slider_ext_vol.value() / 100.0) * (self.vol_slider.value() / 100.0)))

            if is_playing:
                if src_sec >= 0.0:
                    start_sample = int(round(src_sec * 44100))
                    if start_sample < len(pcm):
                        sound_slice = np.ascontiguousarray(pcm[start_sample:])
                        snd = pygame.sndarray.make_sound(sound_slice)
                        self._ext_channel.set_volume(vol)
                        self._ext_channel.play(snd)
                        self._ext_pending_start = False
                    else:
                        self._ext_channel.stop()
                        self._ext_pending_start = False
                else:
                    # まだ外部音源開始時刻に達していない (待機状態)
                    self._ext_channel.stop()
                    self._ext_pending_start = True
            else:
                self._ext_channel.stop()
                self._ext_pending_start = False
        except Exception as e:
            print(f"[ExtAudio Sync Error] {e}")

    def _on_ext_audition_play(self):
        """外部音源の頭出し試聴（メイン再生・画面描画・ガイド音と完全同期）"""
        self._on_play_toggle()

    def _on_ext_audition_restart(self):
        """外部音源を先頭から再生（巻き戻し＆再生同期キック）"""
        self._on_rewind()
        if self.clock.get_state() != SharedClockBridge.STATE_PLAYING:
            self._on_play_toggle()

    def _on_ext_audition_stop(self):
        """外部音源の試聴停止（メイン再生完全停止と同期）"""
        self._on_stop()
        if hasattr(self, "btn_ext_audition"):
            self.btn_ext_audition.setText("▶ 試聴")
            pass

    def _ensure_rec_pcm_loaded(self):
        """採用録音テイクのPCMデータをメモリにキャッシュロード（リバーブ有効時はリバーブWAV優先）"""
        if getattr(self, "_rec_pcm", None) is not None:
            return self._rec_pcm
        rec_path = getattr(self, "last_recorded_path", None)
        if rec_path and os.path.isfile(rec_path):
            try:
                clean_path = resolve_clean_recording_path(rec_path)
                target_path = clean_path
                if hasattr(self, "chk_reverb") and self.chk_reverb.isChecked():
                    rev_path = get_reverb_cache_path(clean_path)
                    rev_type = self.combo_reverb_type.currentText() if hasattr(self, "combo_reverb_type") else "ルーム (自然な部屋鳴り)"
                    wet = self.slider_reverb_wet.value() if hasattr(self, "slider_reverb_wet") else 35
                    apply_harmonica_reverb_numpy(clean_path, rev_path, rev_type, wet)
                    if os.path.exists(rev_path):
                        target_path = rev_path
                self._rec_pcm = load_external_audio_pcm(target_path, sample_rate=44100)
                return self._rec_pcm
            except Exception as e:
                print(f"[RecAudio Load Error] {e}")
                self._rec_pcm = None
        return None

    def _stop_rec_playback(self):
        """録音テイクの再生を安全に停止"""
        try:
            if hasattr(self, "_rec_channel") and self._rec_channel is not None:
                self._rec_channel.stop()
            self._rec_pending_start = False
        except Exception:
            pass

    def _sync_rec_take_playback(self, is_playing: bool, target_sec: float = None):
        """録音テイクをタイムラインと完全同期再生/停止 (Channel 2・PCMスライス再生方式)"""
        if not getattr(self, "_rec_sync_monitoring", False):
            self._stop_rec_playback()
            return

        pcm = self._ensure_rec_pcm_loaded()
        if pcm is None or len(pcm) == 0:
            self._stop_rec_playback()
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

            if not hasattr(self, "_rec_channel") or self._rec_channel is None:
                self._rec_channel = pygame.mixer.Channel(2)

            cur_sec = self.clock.get_current_base_sec() if target_sec is None else target_sec
            offset_sec = float(self.spin_rec_offset.value()) / 1000.0
            # ズレ補正計算式: src_sec = cur_sec - offset_sec (+offsetで録音音声を遅らせる / -offsetで録音音声を早める)
            src_sec = cur_sec - offset_sec
            vol = max(0.0, min(1.0, self.vol_slider.value() / 100.0))

            if is_playing:
                if src_sec >= 0.0:
                    start_sample = int(round(src_sec * 44100))
                    if start_sample < len(pcm):
                        sound_slice = np.ascontiguousarray(pcm[start_sample:])
                        snd = pygame.sndarray.make_sound(sound_slice)
                        self._rec_channel.set_volume(vol)
                        self._rec_channel.play(snd)
                        self._rec_pending_start = False
                    else:
                        self._rec_channel.stop()
                        self._rec_pending_start = False
                else:
                    self._rec_channel.stop()
                    self._rec_pending_start = True
            else:
                self._rec_channel.stop()
                self._rec_pending_start = False
        except Exception as e:
            print(f"[RecAudio Sync Error] {e}")

    def _on_rec_offset_changed(self, val: int):
        self.user_settings["rec_offset_ms"] = int(val)
        self._save_current_settings()
        if getattr(self, "_rec_sync_monitoring", False) and self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
            self._rec_resync_timer.start()

    def _do_rec_audio_resync(self):
        try:
            if self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
                cur_sec = self.clock.get_current_base_sec()
                self._sync_rec_take_playback(True, cur_sec)
        except Exception as e:
            print(f"[RecAudio Resync Error] {e}")

    def _on_rec_offset_adjust(self, delta_ms: int):
        new_val = self.spin_rec_offset.value() + int(delta_ms)
        self.spin_rec_offset.setValue(max(-2000, min(2000, new_val)))

    def _on_toggle_rec_sync_audition(self, checked: bool):
        self._rec_sync_monitoring = bool(checked)
        if checked:
            if not getattr(self, "last_recorded_path", None) or not os.path.exists(self.last_recorded_path):
                QMessageBox.information(self, "同期試聴", "試聴する録音テイクがありません。[🔴録音] で録音するか、[📂テイク選択...] でWAVファイルを選択してください。")
                self.btn_rec_sync_audition.setChecked(False)
                self._rec_sync_monitoring = False
                return
            if hasattr(self, "audition_player") and self.audition_player.is_playing():
                self.audition_player.stop()
                self.btn_rec_listen.setText("▶ 試聴")
            self._rec_pcm = None  # キャッシュ最新化
            if hasattr(self, "btn_rec_sync_audition"):
                self.btn_rec_sync_audition.setText("⏹ 同期試聴を停止")
                self.btn_rec_sync_audition.setStyleSheet(
                    "QPushButton { background-color: #7F1D1D; color: #FECACA; font-weight: bold; "
                    "border: 1px solid #EF4444; border-radius: 4px; padding: 4px 8px; }"
                    "QPushButton:hover { background-color: #991B1B; }"
                )
            self.lbl_status_msg.setText("🎧 伴奏との同期試聴モード: ON（再生ボタンを押すと録音テイクも一緒に鳴ります）")
            if self.clock.get_state() == SharedClockBridge.STATE_PLAYING:
                self._sync_rec_take_playback(True, self.clock.get_current_base_sec())
            else:
                self._on_play_toggle()
        else:
            self._rec_sync_monitoring = False
            self._stop_rec_playback()
            if self.clock.get_state() != SharedClockBridge.STATE_STOPPED:
                self._on_stop()
            elif hasattr(self, "btn_rec_sync_audition"):
                self.btn_rec_sync_audition.setText("▶ 伴奏と同期試聴")
                self.btn_rec_sync_audition.setStyleSheet(
                    "QPushButton:checked { background-color: #0284C7; color: white; font-weight: bold; border: 1px solid #38BDF8; }"
                )
            self.lbl_status_msg.setText("🎧 伴奏との同期試聴モード: OFF")


    def _on_preview_frame(self):
        """現在の再生位置のフレームを1枚オフスクリーンレンダリングしてポップアップ表示"""

        cur_sec = max(0.0, self.clock.get_current_base_sec())
        w, h = calc_export_resolution(self.combo_exp_res.currentText(), self.ratio_combo.currentText())

        render_settings = self._build_export_render_settings()

        tpl_str = self.combo_title_template.currentText() if hasattr(self, "combo_title_template") else "なし"
        title_enabled = (self.chk_exp_title.isChecked() and (tpl_str != "なし") and ("クロマキー" not in self.combo_exp_style.currentText()) and ("完全背景透過" not in self.combo_exp_style.currentText()))
        title_dur = float(self.spin_title_dur.value()) if hasattr(self, "spin_title_dur") else 3.5
        title_exit = self.combo_title_exit.currentText() if hasattr(self, "combo_title_exit") else "フェードアウトで消える"
        title_overlay = {
            "enabled": title_enabled,
            "template": tpl_str,
            "title": self.txt_exp_title.text().strip() or (self.timeline.filename or ""),
            "credit": self.txt_exp_credit.text().strip(),
            "intro_dur": title_dur,
            "exit_mode": title_exit,
        }

        try:
            renderer = OffscreenVisualizerRenderer(
                self.timeline,
                width=w,
                height=h,
                aspect_ratio=self.ratio_combo.currentText(),
                settings=render_settings
            )
            qimage = renderer.render_single_frame_qimage(cur_sec, title_overlay=title_overlay)
            show_sz = bool(self.chk_show_safe_zone.isChecked()) if hasattr(self, "chk_show_safe_zone") else False
            dlg = SingleFramePreviewDialog(qimage, f"再生位置: {cur_sec:.2f}s", show_safe_zone=show_sz, parent=self)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "プレビューエラー", f"プレビュー描画に失敗しました:\n{e}")

    def _on_start_video_export(self):
        """動画書き出し処理の開始"""
        if not getattr(self.timeline, "main_notes", None):
            QMessageBox.information(self, "書き出しエラー", "MIDIファイルが読み込まれていません。\n先にMIDIファイルを開いてください。")
            return

        if not check_ffmpeg_available():
            QMessageBox.warning(
                self,
                "FFmpegが見つかりません",
                "動画書き出しにはFFmpegが必要です。\nFFmpegがシステムにインストールされているか確認してください。"
            )
            return

        # 再生中なら停止
        if self.clock.get_state() != SharedClockBridge.STATE_STOPPED:
            self._on_stop()

        # 出力先パスの指定
        is_transparent = ("完全背景透過" in self.combo_exp_style.currentText())
        ext = ".mov" if is_transparent else ".mp4"
        filter_str = "QuickTime MOV Video (*.mov)" if is_transparent else "MP4 Video (*.mp4)"

        song_base = os.path.splitext(self.timeline.filename)[0] if self.timeline.filename else "harmonica_visualizer"
        out_dir = project_manager.get_active_exports_dir() or get_portable_path("exports")
        os.makedirs(out_dir, exist_ok=True)
        default_file = os.path.join(out_dir, f"{song_base}{ext}")

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "動画の保存先を指定",
            default_file,
            filter_str
        )
        if not out_path:
            return

        if is_transparent and not out_path.lower().endswith(".mov"):
            out_path = os.path.splitext(out_path)[0] + ".mov"

        # 解像度設定 (アスペクト比連動の真の解像度)
        w, h = calc_export_resolution(self.combo_exp_res.currentText(), self.ratio_combo.currentText())

        # フレームレート
        fps = 30 if "30" in self.combo_exp_fps.currentText() else 60

        # エンコーダー
        codec = self.combo_exp_codec.currentText()

        # 前後余白秒数
        try:
            intro_sec = float(self.combo_exp_intro.currentText().replace("秒", "").strip())
        except Exception:
            intro_sec = 1.0
        try:
            outro_sec = float(self.combo_exp_outro.currentText().replace("秒", "").strip())
        except Exception:
            outro_sec = 2.0

        # 範囲
        start_sec = self.spin_exp_start.value()
        end_sec = self.spin_exp_end.value()
        if end_sec <= start_sec:
            end_sec = self.timeline.total_duration_sec

        # 音声トラック選定
        audio_choice = self.combo_exp_audio.currentText()
        audio_path = ""
        if "伴奏音源" in audio_choice:
            if self.ext_audio_path and os.path.isfile(self.ext_audio_path):
                audio_path = self.ext_audio_path
            elif self.last_recorded_path and os.path.isfile(self.last_recorded_path):
                audio_path = self.last_recorded_path
        elif "マイク録音" in audio_choice:
            if self.last_recorded_path and os.path.isfile(self.last_recorded_path):
                audio_path = self.last_recorded_path
            elif self.ext_audio_path and os.path.isfile(self.ext_audio_path):
                audio_path = self.ext_audio_path

        # レンダラー向け設定ディクト (v3.1.0 共通生成)
        render_settings = self._build_export_render_settings()

        # タイトルカード情報
        title_text = self.txt_exp_title.text().strip() or (self.timeline.filename or "")
        credit_text = self.txt_exp_credit.text().strip()
        tpl_str = self.combo_title_template.currentText() if hasattr(self, "combo_title_template") else "なし"
        title_enabled = (self.chk_exp_title.isChecked() and (tpl_str != "なし") and ("クロマキー" not in self.combo_exp_style.currentText()) and ("完全背景透過" not in self.combo_exp_style.currentText()))
        title_dur = float(self.spin_title_dur.value()) if hasattr(self, "spin_title_dur") else 3.5
        title_exit = self.combo_title_exit.currentText() if hasattr(self, "combo_title_exit") else "フェードアウトで消える"
        title_overlay = {
            "enabled": title_enabled,
            "template": tpl_str,
            "title": title_text,
            "credit": credit_text,
            "intro_dur": title_dur,
            "exit_mode": title_exit,
        }

        # カウントイン小節数
        try:
            cleaned = self.combo_count_in.currentText().replace("小節", "").strip().split()[0]
            ci_m = int(cleaned)
        except Exception:
            ci_m = 0

        export_config = {
            "width": w,
            "height": h,
            "fps": fps,
            "aspect_ratio": self.ratio_combo.currentText(),
            "output_path": out_path,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "intro_sec": intro_sec,
            "outro_sec": outro_sec,
            "fade_in": self.chk_fade_in.isChecked(),
            "fade_out": self.chk_fade_out.isChecked(),
            "fade_in_sec": self.spin_fade_in.value(),
            "fade_out_sec": self.spin_fade_out.value(),
            "fade_title_mode": self.combo_fade_title.currentText(),
            "is_count_in": (ci_m > 0),
            "count_in_measures": ci_m,
            "is_metro": (self.combo_metro.currentText() != "なし"),
            "metronome_pattern": self.combo_metro.currentText(),
            "yt_limiter": self.chk_yt_limiter.isChecked() if hasattr(self, "chk_yt_limiter") else True,
            "export_audio_vol_pct": float(self.slider_exp_audio_vol.value()) if hasattr(self, "slider_exp_audio_vol") else 100.0,
            "ext_audio_offset_ms": self.spin_ext_offset.value(),
            "ext_audio_vol_pct": float(self.slider_ext_vol.value()),
            "mixer_settings": self._get_current_mixer_settings(),
            "ext_audio_mode": self.ext_audio_mode,
            "codec": codec,
            "audio_source": audio_choice,
            "audio_path": audio_path,
            "part_mode": self.part_combo.currentText(),
            "synth_engine": self.user_settings.get("synth_engine", "Windows標準MIDI (推奨)"),
            "reverb_enabled": self.chk_reverb.isChecked() if hasattr(self, "chk_reverb") else False,
            "reverb_type": self.user_settings.get("reverb_type", "ルーム (自然な部屋鳴り)"),
            "reverb_wet_pct": int(self.user_settings.get("reverb_wet_pct", 35)),
            "title_overlay": title_overlay,
            "settings": render_settings,
        }

        # 書き出しワーカースレッド生成＆ダイアログ表示
        try:
            export_thread = VideoExportThread(self.timeline, export_config, parent=self)
            dlg = ExportProgressDialog(export_thread, out_path, parent=self)
            export_thread.start()
            dlg.exec()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "動画書き出しエラー", f"動画書き出し処理の開始中にエラーが発生しました:\n{e}")



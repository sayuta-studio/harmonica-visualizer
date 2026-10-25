# タスク管理・実装指示書 (02_tasks.md)

## 進行中 (In Progress) / 次期マイルストーン: Ver.3.2.0
### 🎯 【v3.2.0】UI/UX摩擦ゼロ化（音名直交化・上部タイトル伸縮復元・プリセット直結・練習音源切替・録音テイク選択＆同期試聴）

> **【実装担当（Gemini 3.8）への絶対遵守ルール（Gotcha #7 & #8）】**
> 1. **Git層（Micro Commit）**: 以下の **Micro-Step 1 〜 7** を **必ず1ステップずつ順番に** 実行し、各ステップ完了ごとに構文チェック（`python -m py_compile`）と指定の **Gitコミット** を必ず打つこと（複数ステップの1コミットまとめは厳禁）。
> 2. **人間対話層（Batch Package）**: 人間の確認負荷軽減のため、**Package 1（Step 1〜2）**、**Package 2（Step 3〜4）**、**Package 3（Step 5〜7）** の単位で連続実行し、パッケージ完了ごとに報告すること。
> 3. **スコープ＆シグナル衛生**: 関数内でのインライン `import` は厳禁（ファイル先頭に集約）。UI値のプログラム変更時は必ず `blockSignals(True)` / `blockSignals(False)` で囲むこと。

---

### 📦 Batch Package 1: 表示系の直交化 ＆ 上部ヘッダー伸縮復元（Micro-Step 1 〜 2）

#### - [x] **Micro-Step 1: 音名表記（`lang_mode` 2択化）と穴下ノート表示（`grid4_mode` 3択化）の完全直交化**
- **対象ファイル**: `src/settings_manager.py`, `src/gl_visualizer.py`, `src/video_exporter.py`, `src/main.py`
- **背景・目的**: `lang_mode` に `"なし"` があるため、ノーツ音名チェック（`show_lookahead`）や穴下グリッド（`grid4_mode`）と干渉し、「枠だけ残って文字が消える」「チェックを入れても文字が出ない」矛盾が発生していた。表記言語（`"ドレミ"` / `"CDE"`）と表示可否トグルを完全直交化する。
- **実装内容**:
  1. **`src/settings_manager.py`**:
     - `DEFAULT_VIDEO_PRESETS["✨ シネマティックMV (横型・演出重視)"]`（166行付近）の `"lang_mode": "なし"` を `"lang_mode": "ドレミ"` に、`"grid4_mode": "4音グリッド表示"` を `"grid4_mode": "非表示"` に変更する。
     - `load_settings()` 内のマイグレーション処理（395行付近）で、トップレベル、`practice_visual`、および各 `video_presets` 内の辞書について、もし `d.get("lang_mode") == "なし"` であれば `d["lang_mode"] = "ドレミ"`, `d["show_lookahead"] = False`, `d["grid4_mode"] = "非表示"` に自動変換するロジックを追加する。
  2. **`src/gl_visualizer.py`**:
     - 818〜864行付近（`# 3. 穴下の音名表示`）を以下のように修正し、`"非表示"` 選択時は枠ごと非表示、それ以外は常に `lang_mode`（ドレミ/CDE）で文字を描画する：
       ```python
       grid_str = str(self.show_grid4)
       hide_hole_notes = (self.show_grid4 is False or "非表示" in grid_str or "なし" in grid_str)
       show_4grid = (not hide_hole_notes) and (self.show_grid4 is True or "4音" in grid_str)
       is_jp = (self.lang_mode != "CDE" and "英" not in str(self.lang_mode))
       ```
       - `if show_4grid:` 内の `if self.lang_mode != "なし":` ガードを外し、常に `cell_txt` を描画する。
       - `elif self.lang_mode != "なし":` を `elif not hide_hole_notes:` に変更する。
     - 1250行付近（ノーツ直上の音名描画）の `if should_draw_label and self.show_lookahead and self.lang_mode != "なし" ...` から `and self.lang_mode != "なし"` を除去する。
     - 1275〜1340行付近（`# 6. ... 穴下音名ハイライト`）も同様に `hide_hole_notes` を判定し、`if show_4grid:` 内の `if self.lang_mode != "なし":` を外し、`elif self.lang_mode != "なし" and hole_num in active_hole_notes:` を `elif (not hide_hole_notes) and hole_num in active_hole_notes:` に変更する。
  3. **`src/video_exporter.py`**:
     - `gl_visualizer.py` と全く同じ修正を 401〜447行付近、767行付近、789〜854行付近に適用する。
  4. **`src/main.py`**:
     - 1302行付近: `self.lang_combo.addItems(["ドレミ", "CDE"])` に変更（`"なし"` を撤去）。
     - 1487行付近: `self.combo_grid4.addItems(["4音グリッド表示", "1音表示 (従来)", "非表示"])` に変更。
     - `self.gl_widget.set_show_grid4(...)` を呼んでいる3箇所（2549行、2676行、2878行付近）で、`g4_mode == "4音グリッド表示"` という bool 変換をやめ、文字列 `str(g4_mode)`（または `str(mode)`）をそのまま渡すように修正する。
- **コミットメッセージ**: `fix(visual): orthogonalize lang_mode and grid4_mode visibility controls`

---

#### - [x] **Micro-Step 2: 上部パネル（Row 1）の曲名ボックス伸縮（`stretch=1`）復元と右詰め整列**
- **対象ファイル**: `src/main.py`
- **背景・目的**: `_load_midi_file`（4293行付近）で `self._set_elided_label_text(self.lbl_song_title, ..., max_width=240)` を呼んでいたため、曲名ラベルに `setMaximumWidth(240)` が掛かり、上部パネルのレイアウトが崩れていた問題を解消する。
- **実装内容**:
  1. `_init_ui` 内の `self.lbl_song_title` 生成部（687〜690行付近）に `self.lbl_song_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)` を追加する。
  2. `_load_midi_file` 内（4293行付近）の `self._set_elided_label_text(self.lbl_song_title, self.timeline.filename, filepath, max_width=240)` を以下に置き換える：
     ```python
     self.lbl_song_title.setMinimumWidth(140)
     self.lbl_song_title.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX (幅制限なし・最大伸縮)
     self.lbl_song_title.setText(self.timeline.filename)
     self.lbl_song_title.setToolTip(filepath)
     ```
- **コミットメッセージ**: `fix(ui-header): restore expanding song title label and right-aligned controls in top row1`

---

### 📦 Batch Package 2: 画面作りタブのプリセット直結 ＆ 練習時の再生音源ワンタッチ切替（Micro-Step 3 〜 4）

#### - [x] **Micro-Step 3: `🎨 画面作り` タブへの「動画プリセット選択・保存バー」直結配置**
- **対象ファイル**: `src/main.py`
- **背景・目的**: `🎨 画面作り` タブで「🎬 動画プリセットの画面スタイル」を編集した際、わざわざ `🎬 動画出力` タブへ移動しなくてもその場で対象プリセットの切り替え・上書き保存・別名保存・初期化を行えるようにする。
- **実装内容**:
  1. `_build_tab_design` の `f_target` フレーム内（1273行 `l_target.addWidget(self.lbl_visual_target_hint)` の直後）に、動画プリセット編集時のみ表示されるコンテナ `self.w_design_preset_bar = QWidget(self)` を追加する：
     - 1段目: `プリセット:` ラベル ＋ `self.combo_design_preset = QComboBox(self)`（`self._configure_sidebar_combo(self.combo_design_preset, max_width=230)` 適用、`currentTextChanged` を `self._on_video_preset_changed` に接続）
     - 2段目: `[💾 保存]`（`self._on_save_video_preset` に接続） ＋ `[➕ 別名保存...]`（`self._on_save_as_video_preset` に接続） ＋ `self.btn_design_preset_reset = QPushButton("↺ 初期化", self)`（`self._on_reset_or_delete_video_preset` に接続）
     - 初期状態は `self.w_design_preset_bar.setVisible(False)` とする。
  2. `_on_visual_target_changed`（2432行付近）で、`self._visual_edit_target == "video"` のときは `self.w_design_preset_bar.setVisible(True)`、`"practice"` のときは `self.w_design_preset_bar.setVisible(False)` に切り替える。
  3. `_refresh_video_preset_combo` および `_update_preset_button_states`（2881行付近）で、`self.combo_video_preset` だけでなく `self.combo_design_preset` と `self.btn_design_preset_reset` も同時に `blockSignals(True)` で完全同期するように更新する。
- **コミットメッセージ**: `feat(design-tab): embed synchronized video preset selector and save buttons in design tab`

---

#### - [x] **Micro-Step 4: 練習タブへの「🔊 練習時の再生音源切替」設置と外部伴奏モードの双方向連動**
- **対象ファイル**: `src/main.py`
- **背景・目的**: 動画作成用に外部伴奏を読み込んだ状態でも、練習タブで「普段のMIDIガイド音だけで練習する」か「外部伴奏と合わせて練習する」かを迷わずワンタッチで切り替えられるようにする。
- **実装内容**:
  1. `_build_tab_practice` の末尾（1223行 `v_box.addWidget(f_stepup)` の直後）に **「🔊 練習時の再生音源」フレーム（`f_prac_audio`、最大幅328px）** を追加する：
     - タイトル: `🔊 <b>練習時の再生音源 (伴奏切替):</b>`
     - コンボボックス `self.combo_prac_audio_mode = QComboBox(self)`:
       選択肢は `self.combo_ext_mode` と同一の3項目：
       `["ガイド音のみ (伴奏ミュート)", "伴奏 ＋ ガイド音 (両方再生)", "伴奏のみ (ガイド音オフ)"]`
       （※ `self._configure_sidebar_combo(self.combo_prac_audio_mode, max_width=310)` 適用）
     - 現在の外部伴奏ファイル状態を示す小型ラベル `self.lbl_prac_ext_status = QLabel("伴奏音源: 未設定 (MIDIガイド再生)", self)` を配置。
     - `self.combo_prac_audio_mode.currentTextChanged.connect(self._on_ext_mode_changed)` で接続する。
  2. `_on_ext_mode_changed(self, mode: str)`（4860行付近）で、`self.combo_ext_mode` と `self.combo_prac_audio_mode` の両方を `blockSignals(True)` で相互同期させる。また再生中にモードが切り替わった場合、`cur_sec = self.clock.get_current_base_sec()` で `self._sync_ext_audio_playback(self.clock.get_state() == SharedClockBridge.STATE_PLAYING, cur_sec)` を即時呼び出して音のON/OFFを即座に反映する。
  3. `_set_ext_audio` と `_on_clear_ext_audio` で `self.lbl_prac_ext_status` の表示テキストも連動更新する。
- **コミットメッセージ**: `feat(practice-tab): add quick practice audio source switcher synced with external backing track`

---

### 📦 Batch Package 3: 録音テイク選択 ＆ 録音ズレ同時試聴 ＆ v3.2.0 リリース（Micro-Step 5 〜 7）

#### - [x] **Micro-Step 5: `🎙️ 録音・音響` タブへの「📂 過去テイク・録音WAV選択」機能追加**
- **対象ファイル**: `src/main.py`
- **背景・目的**: 直前に録音した1ファイルだけでなく、複数回録音した過去テイクや任意の録音WAVファイルを選択して試聴・動画合成に採用できるようにする。
- **実装内容**:
  1. `_build_tab_audio` の録音テイクボタン行 `r_take`（1734〜1747行付近）に **`[📂 テイク選択...]` ボタン (`self.btn_select_rec_take`)** を追加する：
     - 配置: `[▶ 試聴]` (`btn_rec_listen`, 幅64px) ＋ `[📂 テイク選択...]` (`btn_select_rec_take`, stretch=1) ＋ `[📁 保存先]` (`btn_open_rec`, 幅68px)
     - クリック時に `self._on_select_rec_take()` を呼び出す。
  2. `_on_select_rec_take(self)` メソッド（4755行 `_on_open_rec_folder` の直前）を新設する：
     - 初期フォルダを `get_portable_path("recordings")` として `QFileDialog.getOpenFileName(self, "採用する録音テイク (WAV) を選択", rec_dir, "WAV Audio (*.wav);;Audio Files (*.wav *.mp3 *.flac *.m4a)")` を開く。
     - 選択されたファイルを `self.last_recorded_path = path` に設定し、`self._set_elided_label_text(self.lbl_rec_take, f"採用テイク: {os.path.basename(path)}", path, max_width=300)` でラベルを更新（エメラルド色 `#34D399`）、`self.btn_rec_listen.setEnabled(True)` にし、ミキサー設定（`_update_mixer_summary_label()`）も即時更新する。
- **コミットメッセージ**: `feat(audio-tab): allow selecting existing recorded WAV takes for audition and video export`

---

#### - [x] **Micro-Step 6: 録音ズレ補正の「▶ 伴奏と同期試聴」および微調整ボタン実装**
- **対象ファイル**: `src/main.py`
- **背景・目的**: 録音ズレ補正（`spin_rec_offset`）を調整する際、単体試聴では伴奏や画面ノーツと合っているか確認できないため、タイムライン再生（伴奏/MIDI＋ノーツ落下）と録音テイクを同時に鳴らしてズレを確認・微調整できる機構を追加する。
- **実装内容**:
  1. `_build_tab_audio` の録音ズレ補正行（1750〜1771行付近）の下に、微調整＆同期試聴行 `r_rec_sync` を追加する：
     - `[-10ms]`, `[+10ms]` 微調整ボタン ＋ **`[▶ 伴奏と同期試聴]` (`self.btn_rec_sync_audition`)** ボタンを配置する。
  2. 録音テイク用のメモリPCMキャッシュ `self._rec_pcm = None` と再生チャンネル `pygame.mixer.Channel(2)`（外部伴奏は Channel 1 を使用中）を導入し、`_sync_rec_take_playback(self, is_playing: bool, target_sec: float = None)` を実装する：
     - `self._rec_sync_monitoring = True`（同期試聴ON中）のとき、メイン再生・シーク・停止（`_on_play_toggle`, `_on_stop`, `_on_seek_released`）および `spin_rec_offset` 変更時に、`src_sec = cur_sec - (self.spin_rec_offset.value() / 1000.0)` の位置から録音テイクPCMを Channel 2 で完全同期スライス再生する！
- **コミットメッセージ**: `feat(audio-tab): add synchronized timeline audition for recorded take offset adjustment`

---

#### - [x] **Micro-Step 7: v3.2.0 全体結合テスト・引き継ぎドキュメント更新・Gitタグ `v3.2.0` 付与**
- **対象ファイル**: `src/main.py`, `.context/00_handover.md`, `.context/02_tasks.md`
- **実装内容**:
  1. `src/main.py` のウィンドウタイトルを `Harmonica Visualizer v3.2.0 [PyQt6 64-bit OpenGL Edition]` に更新。
  2. オフスクリーン自動検証スクリプトを実行し、Micro-Step 1〜6 の全機能（音名直交化、タイトル伸縮、デザインタブプリセット同期、練習音源切替、テイク選択、録音同期試聴）がエラーなく動作することを確認。
  3. `.context/02_tasks.md` と `.context/00_handover.md` を更新してコミットし、Gitタグ `v3.2.0` を付与する。
- **コミットメッセージ**: `docs(release): complete v3.2.0 frictionless UI milestone and update handover`

---

## 次期大型マイルストーン (Backlog): Ver.4.0.0「Harmonica Studio（楽曲プロジェクト自己完結化）」
（※ 詳細設計は `.context/01_architecture.md` 第5章に定義済み）
- [ ] **Phase 4-1: `src/project_manager.py` の新設（`projects/<曲名>/` コンテナ生成・SHA-256 同名MIDI衝突検知・相対パス管理）**
- [ ] **Phase 4-2: キー（移調）別・用途別の運指パターン保存システム（`project.json` 内の `fingering_patterns` 辞書管理）**
- [ ] **Phase 4-3: 環境設定ウィンドウ（`[⚙ 環境設定]` / `src/ui_settings_dialog.py`）の分離と練習画面スタイルの練習タブ統合**
- [ ] **Phase 4-4: `src/main.py` のモジュール分割と旧 `src/fingering/*.json` からの自動マイグレーション**
- [ ] **Ver.3.20 / Ver.4.00 配布用パッケージ（PyInstaller EXE）のクリーンビルドとZIP化**

---

## 完了 (Done)
- [x] **【v3.1.0】練習環境と動画出力プリセットの分離・UI/UX抜本改修（Micro-Step 1〜7 完遂）** (2026-10-25)
  - Micro-Step 1: `src/harmonica_map.py` へのカスタム運指判定ヘルパー追加 (`c6f6928`)
  - Micro-Step 2: `src/main.py` の移調ロック制御 ＆ 残存インラインimport除去 (`a698ae9`)
  - Micro-Step 3: `src/settings_manager.py` のデータ層拡張（`practice_visual` ＆ `video_presets` 自動マイグレーション） (`1c7f4ff`)
  - Micro-Step 4: `src/main.py` へのビジュアル状態抽出・適用ヘルパー導入 ＆ render_settings ビルダー統合 (`886fe2d`)
  - Micro-Step 5: `🎨 画面作り` タブの編集対象ターゲット切替（練習用 vs 動画プリセット）とタブ連動分離 (`4584b3b`)
  - Micro-Step 6: `🎬 動画出力` タブへの動画プリセット管理UI ＆ 練習コピーブリッジ追加 (`c5ed34c`)
  - Micro-Step 7: 全体結合検証（オフスクリーンQt自動テスト通過）、ドキュメント更新、Gitタグ `v3.1.0` 付与 (`9832fb3`)
- [x] **タスク粒度の2層構造化知見（Gotcha #8: Micro Commit × Batch Package）の記録** (2026-10-25) (`22d031b`)

---

## 完了 (Done)
- [x] **AIモデル分業運用（Architect-Builder パターン）の知見化と v3.1.0 マイクロ指示書策定** (2026-10-25)
  - `_shared_knowledge/architecture_patterns.md` に Gotcha #7 としてモデル分業パターンを記録。
  - `.context/01_architecture.md` および `.context/02_tasks.md` に v3.1.0 の詳細設計・全7マイクロステップ指示書を統合。
- [x] **Gitタグ `v3.0.0` の付与** (2026-10-25)
  - 基盤改修（Step 1〜8）、配布用パッケージビルド、フォルダ再編およびバッチ修正完了地点としてタグ付け。
- [x] **【課題C】配布用パッケージ（PyInstaller EXE）のクリーンビルドとZIP化** (2026-10-25)
- [x] **Step 8: フェードイン・前余白・タイトルの完全タイムライン同期** (コミット: `8d77ced`)
- [x] **Step 7: カスタムスキンの動画出力・プレビュー完全反映** (コミット: `5d40a7b`)
- [x] **Step 6: 【課題B】タイトルカード・クレジットの実幅相対スケーリング＆物理クリッピング** (コミット: `1e1b6b5`)
- [x] **Step 5: 【課題A】縦型動画（9:16）および 4:3 動画の解像度・アスペクト比計算と黒帯排除** (コミット: `d64a6f0`)
- [x] **Step 4: マルチトラック・オーディオミキサーダイアログの実装** (コミット: `fe66905`)
- [x] **Step 3: マイク録音の前奏（カウントイン）自動トリムと録音遅延補正** (コミット: `e6d657f`)
- [x] **Step 2: 外部音源PCM直接スライス再生エンジン・巻き戻し修正・リバーブ独立試聴** (コミット: `cc9cc3c`)
- [x] **Step 1: 右サイドバー固定幅（340px）徹底・録音テイク2段化・スピンボックス拡大** (コミット: `450272b`)

# タスク管理・実装指示書 (02_tasks.md)

## 進行中 (In Progress) / 次期マイルストーン: Ver.3.1.0
### 🎯 【v3.1.0】練習環境と動画出力プリセットの分離・UI/UX抜本改修（Gemini 3.8 実装指示書）

> **【実装担当（Gemini 3.8）への絶対遵守ルール】**
> 1. 以下の **Micro-Step 1 〜 7** を **必ず1ステップずつ順番に** 実行すること（複数ステップのまとめ実装は厳禁）。
> 2. 各 Micro-Step が完了するごとに、構文エラーがないことを確認し、指定されたコミットメッセージで **Git コミット（Micro Commit）** を打つこと。
> 3. 関数内でのインライン `import` は絶対に行わないこと（必要なモジュールはファイル先頭で import すること）。
> 4. UIウィジェットの値をプログラムから変更する際は、必ず `blockSignals(True)` / `blockSignals(False)` および `_is_loading` ガードを使用すること。

---

#### - [x] **Micro-Step 1: `src/harmonica_map.py` へのカスタム運指判定ヘルパー追加**
- **対象ファイル**: `src/harmonica_map.py`
- **実装内容**:
  - ファイル末尾（`get_note_fingering_for_song` 関数の直後、488行目以降）に以下の関数を追加する：
    ```python
    def has_custom_fingering() -> bool:
        """現在の曲に個別カスタム運指（変え指オーバーライド）が1件以上設定されているか判定"""
        return len(SONG_FINGERING_OVERRIDES) > 0
    ```
- **コミットメッセージ**: `feat(fingering): add has_custom_fingering helper in harmonica_map`

---

#### - [x] **Micro-Step 2: `src/main.py` の移調ロック制御 ＆ 残存インラインimport除去**
- **対象ファイル**: `src/main.py`
- **実装内容**:
  1. **残存インライン `import` の除去（Gotcha #1 防衛）**:
     - `_on_open_fingering_dialog` 内の `import harmonica_map`（2858行付近）、`_on_reset_song_fingering` 内の `from harmonica_map import reset_song_fingering`（2878行付近 ➔ `harmonica_map.reset_song_fingering` に変更）、`_save_current_song_profile` 内の `from harmonica_map import save_song_profile`（3107行付近 ➔ `harmonica_map.save_song_profile` に変更）、`_load_midi_file` 内の `import harmonica_map`（3243行・3283行付近）を削除し、ファイル先頭（40行目）の `import harmonica_map` を使う形に統一する。
  2. **移調ロック制御メソッド `_update_transpose_lock_state` の新設**:
     - `_on_transpose_changed`（2978行付近）の直前に以下のメソッドを追加する：
       ```python
       def _update_transpose_lock_state(self):
           """カスタム運指が1件以上存在する場合、音名ズレ防止のため移調コントロールをロック"""
           locked = harmonica_map.has_custom_fingering()
           for w_name in ("btn_trans_down_oct", "btn_trans_minus_1", "spin_transpose", "btn_trans_plus_1", "btn_trans_up_oct", "chk_transpose_accomp"):
               w = getattr(self, w_name, None)
               if w is not None:
                   w.setEnabled(not locked)
           if hasattr(self, "spin_transpose"):
               if locked:
                   self.spin_transpose.setStyleSheet("background-color: #2D1A10; border: 1px solid #D97706; color: #FBBF24; font-weight: bold;")
                   self.spin_transpose.setToolTip(
                       "🔒 カスタム運指（変え指）が設定されているため、音名ズレ防止のため移調をロックしています。\n"
                       "移調を変更したい場合は、練習タブの「🔄 初期化」から個別運指をリセットしてください。"
                   )
               else:
                   self.spin_transpose.setStyleSheet("")
                   self.spin_transpose.setToolTip("半音単位の移調 (-24〜+24半音 / ±2オクターブ) [直接入力 / マウスホイールで変更]")
       ```
  3. **呼び出し箇所の接続（4箇所）**:
     - `_on_canvas_fingering_changed`（2846行付近）の末尾に `self._update_transpose_lock_state()` を追加。
     - `_on_open_fingering_dialog`（2868行付近）の `if dlg.exec():` ブロック末尾に `self._update_transpose_lock_state()` を追加。
     - `_on_reset_song_fingering`（2887行付近）のリセット完了直後に `self._update_transpose_lock_state()` を追加。
     - `_load_midi_file`（3351行付近）の `self._check_out_of_range_and_notify()` の直前に `self._update_transpose_lock_state()` を追加。
     - `__init__` の初期化完了付近（`_apply_user_settings()` 呼び出し直後）にも `self._update_transpose_lock_state()` を追加。
- **コミットメッセージ**: `feat(ui): lock transpose controls when custom fingering is active and remove inline imports`

---

#### - [x] **Micro-Step 3: `src/settings_manager.py` のデータ層拡張（`practice_visual` ＆ `video_presets`）**
- **対象ファイル**: `src/settings_manager.py`
- **実装内容**:
  1. `VISUAL_KEYS` タプルおよび `DEFAULT_PRACTICE_VISUAL` 辞書を定義する：
     ```python
     VISUAL_KEYS = (
         "trajectory_mode", "lang_mode", "color_theme", "color_blow", "color_draw",
         "lever_deco_mode", "note_opacity", "show_notes", "show_lookahead",
         "show_grid", "show_bar_lines", "show_hole_num", "hole_num_style",
         "grid4_mode", "show_ring", "show_glow", "show_legend",
         "bg_image_enabled", "bg_image_path", "bg_dim_ratio", "bg_fit_mode", "bg_rotation",
         "skin_enabled", "skin_mouthpiece_path", "skin_lever_off_path", "skin_lever_on_path",
     )
     ```
  2. 公式4種の `DEFAULT_VIDEO_PRESETS` を定義する：
     - `"📱 YouTube Shorts (縦型・解説)"`: `aspect_ratio="9:16"`, `export_resolution="Full HD (1920x1080・推奨)"`, `export_fps="60 FPS (滑らか・推奨)"`, `export_style="完成動画 (背景・タイトル合成)"`, `show_legend=False`, `show_lookahead=True`, `show_grid=True`, `show_hole_num=True`, `export_title_template="イントロ中央＋左上常時"`, `export_intro_sec="1秒"`, `export_outro_sec="2秒"`, `export_fade_in=True`, `export_fade_in_sec=1.0`, `export_fade_out=True`, `export_fade_out_sec=1.5` 等
     - `"🎥 演奏解説・練習用 (横型・標準)"`: `aspect_ratio="16:9"`, 全ガイド・音名・凡例 `True`, `export_title_template="イントロ中央＋右上常時"` 等
     - `"✨ シネマティックMV (横型・演出重視)"`: `aspect_ratio="16:9"`, `trajectory_mode="2段階 (ビジュアル)"`, `lang_mode="なし"`, `show_lookahead=False`, `show_grid=False`, `show_bar_lines=False`, `show_hole_num=False`, `show_legend=False`, `show_glow=True`, `show_ring=True`, `export_title_template="イントロ中央のみ"`, `export_intro_sec="3秒"`, `export_outro_sec="3秒"`, `export_fade_in_sec=2.0`, `export_fade_out_sec=2.0` 等
     - `"🟩 クロマキー合成素材 (透過用)"`: `aspect_ratio="16:9"`, `export_style="クロマキー素材 (背景・タイトルなし)"`, `export_bg_color="グリーンバック"`, `show_grid=False`, `show_bar_lines=False`, `show_legend=False`, `export_fade_in=False`, `export_fade_out=False` 等
  3. `DEFAULT_SETTINGS` に `"practice_visual"`, `"active_video_preset"`, `"video_presets"` を追加する。
  4. `load_settings()` 内で、旧フラット設定が存在し `"practice_visual"` が未作成の場合は、フラットキーから `practice_visual` を自動生成する透過マイグレーションを行い、また `video_presets` に公式プリセットが不足していれば補完する。
  5. ヘルパー関数 `extract_visual_from_settings(s: dict) -> dict` および `get_active_preset_dict(s: dict) -> dict` を追加する。
- **コミットメッセージ**: `feat(settings): add practice_visual and video_presets schema with auto-migration`

---

#### - [x] **Micro-Step 4: `src/main.py` へのビジュアル状態抽出・適用ヘルパー導入**
- **対象ファイル**: `src/main.py`
- **実装内容**:
  1. `self._visual_edit_target = "practice"`（`"practice"` または `"video"`）属性を `__init__` に追加する。
  2. `_apply_user_settings` の直前に以下の3つのヘルパーメソッドを追加する：
     - `_get_current_visual_dict_from_ui(self) -> dict`: 現在の `🎨 画面作り` タブの各ウィジェットから `VISUAL_KEYS` 辞書を生成して返す。
     - `_apply_visual_dict_to_ui_and_gl(self, vis: dict, aspect_ratio: str = "16:9", is_chromakey: bool = False, chroma_color: str = "ノーマル（黒）")`: `blockSignals(True)` で `🎨 画面作り` タブのウィジェットと `self.gl_widget` に `vis` の内容を反映する。
     - `_build_export_render_settings(self, preset: dict = None) -> dict`: 動画出力・1フレームプレビュー用の `render_settings` 辞書を、選択中の動画プリセット（`preset`）から生成して返す（これまで4258行と4395行に重複していた35行の辞書生成をこの関数1つに統合する）。
  3. `_on_preview_frame` と `_on_start_video_export` の `render_settings = { ... }` を `render_settings = self._build_export_render_settings()` に置き換える。
- **コミットメッセージ**: `refactor(visual): unify render_settings builder and visual state helpers in main.py`

---

#### - [x] **Micro-Step 5: `🎨 画面作り` タブの「編集対象ターゲット切替」とタブ連動の分離**
- **対象ファイル**: `src/main.py`
- **実装内容**:
  1. `_build_tab_design`（1232行付近）の最上部（`v_box` の先頭）に **「🎯 編集対象の切り替え」フレーム（`f_target`、最大幅328px）** を追加する：
     - コンボボックスまたはセグメントボタンで `["🎯 練習用の画面スタイル (標準)", "🎬 動画プリセットの画面スタイル"]` を切り替え可能にする。
     - 画面比率（`f_ratio`）フレームは `"🎬 動画プリセットの画面スタイル"` 編集時のみ有効化（練習用スタイル編集時は `16:9 (練習標準)` 固定としてグレーアウトまたは注記表示）する。
  2. `_save_current_settings` 内で、`self._visual_edit_target == "practice"` のときは `self.user_settings["practice_visual"]` を更新し、`"video"` のときは現在選択中の `self.user_settings["video_presets"][active_name]` を更新するように分岐させる。
  3. `_on_tab_changed(self, index: int)` を更新する：
     - `index in (0, 2)`（練習タブ・録音タブ）のときは、常に `self.user_settings["practice_visual"]` と `"16:9"` を `self.gl_widget` に反映する。
     - `index == 3`（動画出力タブ）のときは、現在選択中の動画プリセットの設定とアスペクト比を `self.gl_widget` に反映する。
     - `index == 1`（画面作りタブ）のときは、`self._visual_edit_target` に応じて練習用または動画プリセット用の設定を反映する。
- **コミットメッセージ**: `feat(design-tab): separate practice visual editing from video preset visual editing`

---

#### - [ ] **Micro-Step 6: `🎬 動画出力` タブへの「🗂️ 動画出力プリセット」管理UI＆練習コピーブリッジ追加**
- **対象ファイル**: `src/main.py`
- **実装内容**:
  1. `from PyQt6.QtWidgets import ...`（26行付近）に `QInputDialog` を追加する（ファイル先頭でimport）。
  2. `_build_tab_export`（1928行付近）の最上部（`f_exp` の直前）に **「🗂️ 動画出力プリセット」フレーム（`f_preset`、最大幅328px）** を追加する：
     - 1段目: `プリセット:` ラベル ＋ `self.combo_video_preset`（`self._configure_sidebar_combo` 適用）
     - 2段目: `[💾 保存]` (`btn_preset_save`) ＋ `[➕ 別名保存...]` (`btn_preset_save_as`) ＋ `[↺ 初期化/削除]` (`btn_preset_reset`)
     - 3段目: `[📋 現在の「練習画面」の見た目を反映]` (`btn_copy_practice_visual`)
     - 4段目: `[🎨 このプリセットの画面デザインを編集...]` (`btn_jump_design_for_video`：`🎨 画面作り` タブへ移動し、編集対象を「🎬 動画プリセット」に自動切替するショートカットボタン)
  3. イベントハンドラ群を実装する：
     - `_on_video_preset_changed(preset_name: str)`: 選択されたプリセットの解像度・FPS・出力スタイル・余白・フェード・タイトル・ビジュアル設定を動画出力タブUIおよび `self.gl_widget` に一括反映（`blockSignals(True)` 徹底）。
     - `_on_save_video_preset()`: 現在の動画タブ設定＋動画ビジュアル設定を選択中プリセットに上書き保存。
     - `_on_save_as_video_preset()`: `QInputDialog.getText` で新規プリセット名を入力し、`video_presets` に追加してコンボボックスを選択。
     - `_on_reset_or_delete_video_preset()`: 公式4プリセットならデフォルト値へ初期化、ユーザー作成プリセットなら確認ダイアログ後に削除。
     - `_on_copy_practice_visual_to_preset()`: `self.user_settings["practice_visual"]` の見た目設定（色、スキン、背景、グリッド・音名ON/OFF等）を選択中プリセットへコピーし、キャンバスを即時更新。
- **コミットメッセージ**: `feat(export-tab): add video preset manager UI and practice-to-video copy bridge`

---

#### - [ ] **Micro-Step 7: 全体結合検証・引き継ぎドキュメント更新・Gitタグ `v3.1.0` 付与**
- **対象ファイル**: `.context/00_handover.md`, `.context/02_tasks.md`
- **実装内容**:
  1. 全ファイルの構文チェックとプリセット切替・マイグレーション動作の検証スクリプトを実行。
  2. `.context/02_tasks.md` の Micro-Step 1〜7 を完了（`[x]`）に更新し、`.context/00_handover.md` を `v3.1.0` 完了状態に更新してコミット。
  3. Gitタグ `v3.1.0`（Annotated Tag）を付与する。
- **コミットメッセージ**: `docs(release): complete v3.1.0 preset architecture milestone and update handover`

---

## 未着手 (Backlog)
- [ ] **Ver.3.10 配布用パッケージ（PyInstaller EXE）のクリーンビルドとZIP化**
- [ ] **運指マッピング・変え指プリセットの追加検証**
- [ ] **多言語対応（i18n）の将来検討**

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

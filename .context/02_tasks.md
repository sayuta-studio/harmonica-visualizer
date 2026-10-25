# タスク管理・実装指示書 (02_tasks.md)

## 進行中 (In Progress) / 次期メジャーマイルストーン: Ver.4.0.0
### 🚀 【v4.0.0】Harmonica Studio（楽曲プロジェクト自己完結化・キー別運指パターン・タブ抜本再編・モジュール分割）

> **【実装担当（Gemini 3.8 / Builder）への絶対遵守ルール（Gotcha #7, #8, #9）】**
> 1. **Git層（Micro Commit）**: 以下の **Micro-Step 1 〜 8** を **必ず1ステップずつ順番に** 実行し、各ステップ完了ごとに構文チェック（`python -m py_compile`）と指定の **Gitコミット** を必ず打つこと（複数ステップの1コミットまとめは厳禁）。
> 2. **人間対話層（Batch Package）**: 人間の確認負荷軽減のため、**Package 1（Step 1〜2）**、**Package 2（Step 3〜4）**、**Package 3（Step 5〜6）**、**Package 4（Step 7〜8）** の単位で連続実行し、パッケージ完了（または自動停止条件到達）ごとに報告すること。
> 3. **スコープ＆シグナル衛生**: 関数内でのインライン `import` は厳禁（ファイル先頭に集約）。UI値のプログラム変更時は必ず `blockSignals(True)` / `blockSignals(False)` で囲むこと。

---

### 📦 Batch Package 1: ポータブル基底パス刷新 ＆ 楽曲プロジェクトマネージャー (`src/project_manager.py`) の構築（Micro-Step 1 〜 2）

#### - [x] **Micro-Step 1: `src/config.py` のポータブル基底パス刷新（Gotcha #9 実装：開発時の `src/` 汚染完全防止）と `.gitignore` 保護**
- **対象ファイル**: `src/config.py`, `.gitignore`
- **背景・目的**: 開発時（`python src/main.py` や自動テスト実行時）に `__file__` のある `src/` 配下に `projects/` や `recordings/` が生成されたり、Git追跡下の `src/settings.json` や `src/fingering/demo_chromatic_profile.json` が書き換わって Git status が汚れる問題を根絶する。
- **実装内容**:
  1. **`src/config.py`** の `get_portable_path(relative_path)`（25〜35行付近）を以下のように刷新する：
     ```python
     import shutil

     def get_portable_base_dir() -> str:
         """
         EXE化時(frozen)は実行ファイルのあるフォルダ、
         開発時(.py実行)は src/ の1階層上（リポジトリルート）を返す。
         """
         if getattr(sys, "frozen", False):
             return os.path.dirname(sys.executable)
         return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

     def get_portable_path(relative_path: str) -> str:
         """
         ユーザーデータ・動的フォルダはポータブル基底ディレクトリ直下に解決する。
         ただし同梱静的アセット('skins')がルート直下に無い場合は src/skins へ自動フォールバックし、
         'settings.json' がルート直下に無く src/settings.json にある場合は初回のみ自動コピーして引き継ぐ。
         """
         base_dir = get_portable_base_dir()
         target_path = os.path.join(base_dir, relative_path)
         src_dir = os.path.dirname(os.path.abspath(__file__))

         norm_rel = relative_path.replace("\\", "/").strip("/")
         if norm_rel == "skins" or norm_rel.startswith("skins/"):
             if not os.path.exists(target_path):
                 src_fallback = os.path.join(src_dir, relative_path)
                 if os.path.exists(src_fallback):
                     return src_fallback
         elif norm_rel == "settings.json":
             if not os.path.exists(target_path):
                 src_settings = os.path.join(src_dir, "settings.json")
                 if os.path.isfile(src_settings):
                     try:
                         shutil.copy2(src_settings, target_path)
                     except Exception:
                         pass
         return target_path
     ```
  2. **`.gitignore`** にリポジトリルート直下の動的生成フォルダ・設定ファイルを追加し、`src/` 以外の動的データを完全に Git 追跡外とする：
     - `/projects/`
     - `/recordings/`
     - `/output/`
     - `/temp/`
     - `/fingering/`
     - `/settings.json`
- **コミットメッセージ**: `feat(config): resolve portable paths to repository root in dev mode to prevent src pollution`

---

#### - [x] **Micro-Step 2: 楽曲プロジェクト自己完結管理モジュール `src/project_manager.py` の新設と `src/harmonica_map.py` 連携**
- **対象ファイル**: `src/project_manager.py` (新規作成), `src/harmonica_map.py`
- **背景・目的**: 1曲＝1フォルダ（`projects/<曲名>/`）に MIDI原本、プロファイル（`project.json`）、録音テイク（`takes/`）、伴奏音源（`audio/`）、完成動画（`exports/`）を自己完結集約し、SHA-256ハッシュによる同名別MIDI衝突検知・リネーム追従・旧 `fingering/<曲名>_profile.json` からの自動マイグレーションを実現する。
- **実装内容**:
  1. **`src/project_manager.py`** を新規作成し、以下の機能を持つ `SongProjectManager`（およびモジュール関数）を実装する：
     - `compute_file_sha256(filepath: str) -> str`: ファイルの SHA-256 ハッシュを算出。
     - `sanitize_folder_name(name: str) -> str`: Windows禁止文字（`\/:*?"<>|`）を `_` に置換。
     - `resolve_song_project(midi_path: str, interactive_parent=None) -> dict`:
       - `midi_path` が空、または実在しないデモ識別子（例: `"demo_chromatic"`）の場合は、`projects/_demo_chromatic/` フォルダ（ファイルコピーなし）を割り当てる。
       - 実在する `.mid` / `.midi` ファイルの場合：
         1. もし既に `projects/<フォルダ>/source/` 内のMIDI自身が選択された場合は、その親プロジェクトフォルダをそのまま使用する（自己コピー防止）。
         2. 外部のMIDIファイルが選択された場合、`base_name = sanitize_folder_name(os.path.splitext(os.path.basename(midi_path))[0])` で `projects/<base_name>/` を候補とする。
         3. 候補フォルダ内に `project.json`（または `source/` 内MIDI）が既に存在し、記録されている `midi_sha256` と今回読み込んだ `midi_path` の SHA-256 が **異なる（同名・別内容MIDIの衝突）** 場合：
            - `interactive_parent` が指定されていれば `QMessageBox.question` で確認：
              *「同名のプロジェクト『{base_name}』が既に存在しますが、MIDIファイルの内容が異なります。\n\n【はい(Yes)】別プロジェクト『{base_name}_2』として新規作成する（推奨）\n【いいえ(No)】既存プロジェクトのMIDI原本を上書き更新する」*
            - `interactive_parent` が None（自動テスト時など）または「はい」が選ばれた場合は、空き連番 `projects/<base_name>_2/`（`_3`...）を自動採番する。
         4. プロジェクトサブフォルダ `source/`, `takes/`, `audio/`, `exports/` を `os.makedirs(..., exist_ok=True)` で自動生成し、`source/` に MIDI原本をコピーする。
         5. **旧プロファイル自動マイグレーション**: `projects/<folder>/project.json` がまだ存在しない場合、旧保存先（`get_portable_path("fingering")` または `src/fingering/`）に `<base_name>_profile.json` が存在すれば、その内容を `project.json` へ自動コピーして引き継ぐ。
         6. 現在のアクティブプロジェクト情報（`ACTIVE_PROJECT_DIR`, `ACTIVE_PROJECT_JSON` 等）を更新して返す。
     - ヘルパー関数：
       - `get_active_project_dir() -> str`
       - `get_active_takes_dir() -> str`（アクティブプロジェクトがあれば `<proj>/takes`、無ければ `get_portable_path("recordings")`）
       - `get_active_exports_dir() -> str`（アクティブプロジェクトがあれば `<proj>/exports`、無ければ `get_portable_path("output")`）
       - `get_project_profile_path(midi_path: str) -> str`: `projects/<曲名>/project.json` のパスを返す。
       - `to_project_rel_path(abs_path: str, proj_dir: str = None) -> str`: プロジェクトフォルダ内のパスであれば相対パスに変換（フォルダ名リネーム追従用）。
       - `from_project_rel_path(stored_path: str, proj_dir: str = None) -> str`: 相対パスを現在のプロジェクトフォルダ基準の絶対パスに復元（ファイルが存在すれば復元パスを返し、外部絶対パスならそのまま返す）。
  2. **`src/harmonica_map.py`** の更新：
     - ファイル先頭で `import project_manager` を行う（インライン `import` もすべてファイル先頭へ移動）。
     - `get_song_profile_path(midi_path)` と `get_song_fingering_path(midi_path)` が `project_manager.get_project_profile_path(midi_path)` および `project_manager.get_project_fingering_txt_path(midi_path)` を返すように接続する。
     - `load_song_profile` と `save_song_profile` で、`ext_audio_path` や `active_take_path` がプロジェクト内のファイルであれば相対パス変換・復元（`from_project_rel_path` / `to_project_rel_path`）を通すことで、**ユーザーがエクスプローラー上でプロジェクトフォルダ名をリネームしても100%追従する**ようにする。
- **コミットメッセージ**: `feat(project): implement self-contained SongProjectManager with SHA-256 collision detection and legacy migration`

---

### 📦 Batch Package 2: キー（移調）別・用途別の運指パターン保存システム拡張（Micro-Step 3 〜 4）

#### - [x] **Micro-Step 3: 変え指エディタ (`FingeringEditorDialog`) と `harmonica_map.py` の運指パターンへの「移調（Key/Transpose）情報」統合**
- **対象ファイル**: `src/harmonica_map.py`, `src/dialogs.py`
- **背景・目的**: 既存の変え指エディタにある「運指パターン別名保存（`patterns`）」を拡張し、「何調（移調±N）の何用」として移調値（`transpose`, `transpose_accomp`）ごとパターン保存・復元できるようにする。
- **実装内容**:
  1. **`src/harmonica_map.py`**:
     - グローバル変数 `CURRENT_ACTIVE_PATTERN_NAME = "標準パターン (基本)"` を追加し、`load_song_profile` / `save_song_profile` で `"active_pattern_name"` と `"patterns"` 辞書を標準保持するように拡張する。
     - `format_transpose_key_label(transpose_val: int) -> str` ヘルパーを追加（例: `0` -> `"原曲キー(±0)"`, `+2` -> `"Key+2(+2st)"`, `-3` -> `"Key-3(-3st)"`）。
     - `build_current_pattern_snapshot(transpose: int = 0, transpose_accomp: bool = True) -> dict`: 現在の `CURRENT_SONG_PRESET`, `CURRENT_MONOPHONIC_MODE`, `HIDE_MUTED_NOTES`, `SONG_FINGERING_OVERRIDES`, `SONG_MUTED_NOTES`, `transpose`, `transpose_accomp` を1つの辞書スナップショットとして返す関数を追加。
     - `apply_pattern_snapshot(pat_data: dict) -> tuple[int, bool]`: パターン辞書から運指オーバーライド・除外ノーツ・プリセット・単音化モードを復元し、`(transpose, transpose_accomp)` を返す関数を追加。
  2. **`src/dialogs.py` (`FingeringEditorDialog`)**:
     - `_on_save_new_pattern(self)`（1031行付近）で、新規パターン名のデフォルト提案テキストに現在の移調ラベルを自動付与する：
       `key_lbl = harmonica_map.format_transpose_key_label(getattr(self.timeline, "transpose", 0))`
       `default_name = f"{key_lbl} - パターン{len(self._patterns) + 1}"`
     - 保存辞書 `self._patterns[p_name]` に `"transpose": getattr(self.timeline, "transpose", 0)` と `"transpose_accomp": getattr(self.timeline, "transpose_accomp", True)` を含める。
     - `_on_pattern_switched(self, idx: int)`（985行付近）で、選択されたパターンに `"transpose"` が記録されていれば `self.timeline.set_transpose(pat_transpose, pat_trans_acc)` も同時に適用してテーブル・音声・OpenGLを再バインドする。
     - `CURRENT_ACTIVE_PATTERN_NAME` を選択パターン名と同期させる。
- **コミットメッセージ**: `feat(fingering): bind transpose key settings into saved fingering patterns`

---

#### - [ ] **Micro-Step 4: メイン画面（`🎹 練習` タブ）への「📂 運指パターン（キー別プロファイル）切替・新規保存」UI設置と別キー作成アンロック機能**
- **対象ファイル**: `src/main.py`
- **背景・目的**: 変え指エディタを開かなくても、練習タブ上で「原曲キー用」「Key+2 伴奏用」などの運指パターンをワンタッチで切り替えられるようにする。また、変え指設定後に別の移調キーでパターンを作りたくなった際、ワンクリックで現在パターンを保護保存しつつ別キー作成へ移行できるボタンを追加する。
- **実装内容**:
  1. `_build_tab_practice` の「2. 🎼 運指 & 重なり音処理」フレーム内（1085行付近、運指ルールの上）に **運指パターン選択行 (`r_fpat`)** を追加する：
     - `パターン:` ラベル ＋ `self.combo_main_fg_pattern = QComboBox(self)`（`stretch=1`、`_configure_sidebar_combo` 適用）
     - `[➕ 保存]` ボタン (`self.btn_main_save_fg_pattern`, 幅54px, ツールチップ: `"現在の移調キー・変え指・除外設定を名前付き運指パターンとして保存"`)
  2. 「3. 🎚️ 移調 (トランスポーズ)」フレーム内（1180行付近）に、移調ロック中のみ表示される **`self.btn_unlock_for_new_key = QPushButton("🔓 別キー用の運指を新規作成...", self)`** を追加する：
     - クリック時（`_on_unlock_for_new_key`）：現在の変え指をパターン（例: `"原曲キー(±0) - 自動保存"`）にバックアップ保存した上で、個別変え指（`SONG_FINGERING_OVERRIDES`）をクリアして移調ロックを即時解除し、自由に移調を変更できるようにする！
  3. メイン画面側のハンドラ `_refresh_main_fg_pattern_combo()`, `_on_main_fg_pattern_switched(name: str)`, `_on_main_save_fg_pattern()` を実装し、曲ロード時および変え指エディタ終了時にコンボボックスを最新状態に同期させる。
- **コミットメッセージ**: `feat(practice-tab): add quick key-based fingering pattern selector and new-key unlock workflow`

---

### 📦 Batch Package 3: タブ抜本再編（練習スタイル統合・画面作りタブの動画専用化）＆ 環境設定ウィンドウ `[⚙ 設定]` 分離（Micro-Step 5 〜 6）

#### - [ ] **Micro-Step 5: `🎨 画面作り` タブの「100%動画プリセット専用化」と、`🎹 練習` タブ下部への「🎨 練習画面スタイル」統合**
- **対象ファイル**: `src/main.py`
- **背景・目的**: ユーザーの構想通り、`🎨 画面作り` タブの「練習用 vs 動画用」ターゲット切替コンボを撤廃して **100%動画プリセット編集専用タブ（`🎨 動画画面`）** に純化する。そして日常の練習画面の見た目（軌道モード、音名表記、穴下ノート表示、カラーテーマ、ノーツ直上音名）は **`🎹 練習` タブの下部フレーム** に統合し、タブを行き来せずに練習タブ内で練習設定が完結するようにする。
- **実装内容**:
  1. `_build_tab_practice` の末尾（`f_prac_audio` の下）に **「5. 🎨 練習画面の表示スタイル」フレーム (`f_prac_style`、最大幅328px）** を新設する：
     - `軌道:` (`self.combo_prac_traj`: 3段階 / 2段階 / 垂直)
     - `音名:` (`self.combo_prac_lang`: ドレミ / CDE) ＋ `穴下:` (`self.combo_prac_grid4`: 4音グリッド表示 / 1音表示 (従来) / 非表示)
     - `配色:` (`self.combo_prac_theme`: ノーマル / サクラ / クールネオン / モノクロ / カスタム)
     - チェックボックス行: `self.chk_prac_lookahead` (`"ノーツ音名"`) ＋ `self.chk_prac_bar_lines` (`"小節線"`) ＋ `self.chk_prac_legend` (`"吹吸凡例"`)
     - これらの変更は即座に `self.user_settings["practice_visual"]` に保存され、現在練習表示中（タブ0またはタブ2）であればキャンバスにリアルタイム反映される！
  2. `_build_tab_design` の最上部（`f_target`）を刷新：
     - `self.combo_visual_target`（練習用/動画用の切替コンボ）を非表示（または内部的に常時 `"video"` 固定）にし、`self.w_design_preset_bar`（動画プリセット選択・保存・別名保存・初期化バー）を **常時表示 (`setVisible(True)`)** にする。
     - `self.f_ratio`（画面比率 16:9 / 9:16 / 4:3）も常時 `setEnabled(True)` にする。
     - 右サイドバーのタブ2のラベルを `"🎨 画面作り"` から **`"🎨 動画画面"`** に変更し、「タブ1＝🎹練習、タブ2＝🎨動画画面、タブ3＝🎙️録音・音響、タブ4＝🎬動画出力」と役割を明確化する。
  3. `_on_sidebar_tab_changed(self, index: int)` の連動をシンプル化：
     - `index in (0, 2)`（練習タブ・録音タブ）のときは `_visual_edit_target = "practice"` として `practice_visual`（16:9固定）をキャンバスに適用。
     - `index in (1, 3)`（動画画面タブ・動画出力タブ）のときは `_visual_edit_target = "video"` として現在選択中の `video_preset` のスタイルと比率をキャンバスに適用！
- **コミットメッセージ**: `feat(ui-tabs): integrate practice visual controls into practice tab and dedicate design tab to video presets`

---

#### - [ ] **Micro-Step 6: システム環境設定ウィンドウ（`[⚙ 環境設定]` / `HarmonicaSettingsDialog`）の刷新とメイン画面接続**
- **対象ファイル**: `src/dialogs.py`, `src/main.py`
- **背景・目的**: 頻繁に変更しないシステム環境設定（ガイドMIDI音源エンジン、主旋律ハーモニカ固定、マイク入力デバイス、録音チャンネル数、ハーモニカ本体外観スキン、プロジェクトフォルダ一括確認）を **`[⚙ 環境設定]` ダイアログ** に整理統合し、上部ヘッダー Row 1 右端の `[⚙ 環境設定]` ボタンからワンクリックで開けるようにする。
- **実装内容**:
  1. **`src/dialogs.py` (`HarmonicaSettingsDialog`)** を Ver.4.0 システム環境設定仕様にアップグレードする：
     - タブ1 **`🔊 音響・録音デバイス`**:
       - ガイド音源エンジン (`Windows標準MIDI (推奨)` / `内蔵軽量シンセ (遅延0ms)`)
       - 主旋律をハーモニカ音色(GM 22)に固定 (`force_harmonica`)
       - メトロノームクリックパターン (`metronome_mode`)
       - 録音チャンネル数 (`モノラル (1ch・DAW編集向き)` / `ステレオ (2ch)`)
       - 録音ズレ補正初期値 (`rec_offset_ms`)
     - タブ2 **`🎨 本体スキン・練習支援`**:
       - ハーモニカ外観スキン有効化 (`skin_enabled`) と `[🖼️ スキン画像選択...]` ボタン接続
       - ステップアップ練習設定 (`stepup_enabled`, 開始速度%, 目標速度%, 増分%)
     - タブ3 **`📁 プロジェクト・保存先管理`**:
       - 現在のポータブルデータ基底パス表示と、`[📂 projects フォルダを開く]`, `[📂 録音フォルダを開く]`, `[📂 動画出力フォルダを開く]` ショートカットボタン。
  2. **`src/main.py`**:
     - 上部ヘッダー Row 1 右端（サイドバー開閉ボタンの左隣）に **`self.btn_open_settings = QPushButton("⚙ 設定", self)`**（幅64px、ツールチップ: `"システム環境設定ウィンドウを開く"`）を配置。
     - クリック時に `_on_open_env_settings_dialog(self)` を呼び出し、`HarmonicaSettingsDialog` で保存された変更をメインウィンドウの各コンボ・チェックボックス・エンジンへ即時同期反映する。
- **コミットメッセージ**: `feat(settings-dialog): add global preferences window accessible from top header bar`

---

### 📦 Batch Package 4: `src/main.py` の安全なモジュール分割 ＆ プロジェクトフォルダ直結 ＆ Ver.4.0.0 リリース（Micro-Step 7 〜 8）

#### - [ ] **Micro-Step 7: スタジオ・エクスポート制御の `src/studio_controller.py` 分離と、録音・動画出力先の `projects/<曲名>/` 完全直結**
- **対象ファイル**: `src/studio_controller.py` (新規作成), `src/main.py`
- **背景・目的**:
  1. 約5,400行に肥大化した `src/main.py` から、録音・外部伴奏・YouTubeラウドネス解析・ミキサー・動画エクスポート制御ロジック（約700〜900行）を **`StudioExportMixin` (`src/studio_controller.py`)** として安全に分離し、循環インポートゼロで `src/main.py` をスリム化する。
  2. 同時に、MIDI読み込み時に `project_manager.resolve_song_project` を呼び出し、録音保存先を `projects/<曲名>/takes/`、動画出力先を `projects/<曲名>/exports/` へ直結する。さらに上部ヘッダーや録音・動画タブの「📁 保存先」ボタンで該当楽曲のプロジェクトサブフォルダが直接開くようにする。
- **実装内容**:
  1. **`src/studio_controller.py`** を新規作成し、`StudioExportMixin` クラスに以下のメソッド群を移動・整理する：
     - プロジェクトフォルダ操作: `_on_open_project_folder`, `_on_open_rec_folder` (`get_active_takes_dir()` を開く), `_on_open_output_folder` (`get_active_exports_dir()` を開く)
     - 録音・テイク・同期試聴制御: `_on_select_rec_take`, `_ensure_rec_pcm_loaded`, `_stop_rec_playback`, `_sync_rec_take_playback`, `_on_rec_offset_changed`, `_do_rec_audio_resync`, `_on_rec_offset_adjust`, `_on_toggle_rec_sync_audition`
     - 外部伴奏・同期制御: `_ensure_ext_pcm_loaded`, `_stop_ext_playback`, `_set_ext_audio`, `_on_clear_ext_audio`, `_on_ext_mode_changed`, `_on_ext_offset_changed`, `_do_ext_audio_resync`, `_do_ext_offset_save`, `_on_ext_offset_adjust`, `_sync_ext_audio_playback`, `_on_ext_audition_play`, `_on_ext_audition_restart`, `_on_ext_audition_stop`
     - ミキサー・YouTube音量解析・動画出力制御: `_get_current_mixer_settings`, `_update_mixer_summary_label`, `_on_open_audio_mixer`, `_apply_youtube_volume_preset`, `_build_export_render_settings`, `_on_preview_single_frame`, `_on_export_video`
  2. **`src/main.py`**:
     - `from studio_controller import StudioExportMixin` および `import project_manager` を先頭に追加。
     - `class HarmonicaMainWindow(QMainWindow, StudioExportMixin):` として継承。
     - `_load_midi_file` 内で `project_manager.resolve_song_project(filepath, interactive_parent=self)` を呼び出し、楽曲プロジェクトコンテナを自動準備する。
     - 録音開始時の出力パス生成（`_on_record_toggle`）で `rec_dir = project_manager.get_active_takes_dir()` を使用し、動画書き出し時（`_on_export_video`）のデフォルト保存先ディレクトリに `project_manager.get_active_exports_dir()` を使用する。
- **コミットメッセージ**: `refactor(studio): extract StudioExportMixin to studio_controller.py and bind takes/exports to song project container`

---

#### - [ ] **Micro-Step 8: Ver.4.0.0 全体結合テスト (`tests/verify_v400_studio.py`) 実行・ドキュメント更新・Gitタグ `v4.0.0` 付与**
- **対象ファイル**: `src/main.py`, `tests/verify_v400_studio.py` (新規作成), `.context/00_handover.md`, `.context/01_architecture.md`, `.context/02_tasks.md`
- **実装内容**:
  1. `src/main.py` のウィンドウタイトルを **`Harmonica Visualizer v4.0.0 [Harmonica Studio Edition]`** に更新。
  2. オフスクリーン自動検証スクリプト **`tests/verify_v400_studio.py`** を作成・実行し、以下の全8項目を自動テストする：
     - Test 1: `get_portable_path` が開発時にリポジトリルートを返し、テスト実行後も `src/` 配下の Git status が一切汚れないこと（`git status --porcelain src/` が空であること）。
     - Test 2: `project_manager.resolve_song_project` により `projects/<曲名>/`（`source/`, `takes/`, `audio/`, `exports/`, `project.json`）が自動生成されること。
     - Test 3: 同名で内容（SHA-256）が異なるMIDIファイルを読み込んだ際、衝突が検知され別プロジェクトフォルダ（`<曲名>_2`）として安全に分離されること。
     - Test 4: プロジェクトフォルダをリネームしても相対パス解決（`from_project_rel_path`）により内部アセットパスが正常に追従すること。
     - Test 5: 運指パターン（`patterns`）に移調値（`transpose`）が保存され、練習タブの `combo_main_fg_pattern` で切り替えると移調値と変え指がセットで切り替わること。また `btn_unlock_for_new_key` で別キー作成ロック解除が動作すること。
     - Test 6: 練習タブ下部の練習画面スタイル設定（`combo_prac_traj`, `combo_prac_lang`, `combo_prac_grid4` 等）が `practice_visual` に即座に反映され、動画画面タブ（`🎨 動画画面`）は100%動画プリセット専用として動作すること。
     - Test 7: 上部ヘッダーの `[⚙ 設定]` ボタン（`btn_open_settings`）および `HarmonicaSettingsDialog` が正常に初期化・設定反映できること。
     - Test 8: `StudioExportMixin`（`src/studio_controller.py`）分離後も録音・伴奏同期・動画レンダー設定構築がエラーなく動作し、`src/main.py` の行数が大幅に削減されていること。
  3. `.context/02_tasks.md`, `.context/01_architecture.md`, `.context/00_handover.md` を完了状態に更新してコミットし、Gitタグ **`v4.0.0`** を付与する。
- **コミットメッセージ**: `docs(release): complete v4.0.0 Harmonica Studio architecture milestone and tag release`

---

## 完了 (Done)
- [x] **【v3.2.0】UI/UX摩擦ゼロ化（音名直交化・上部タイトル伸縮復元・プリセット直結・練習音源切替・録音テイク選択＆同期試聴）** (2026-10-25)
  - Micro-Step 1: 音名表記（`lang_mode` 2択化）と穴下ノート表示（`grid4_mode` 3択化）の完全直交化 (`b84b922`)
  - Micro-Step 2: 上部パネル（Row 1）の曲名ボックス伸縮（`stretch=1`）復元と右詰め整列 (`5ab79e3`)
  - Micro-Step 3: `🎨 画面作り` タブへの「動画プリセット選択・保存バー」直結配置 (`d817949`)
  - Micro-Step 4: 練習タブへの「🔊 練習時の再生音源切替」設置と外部伴奏モードの双方向連動 (`69e4584`)
  - Micro-Step 5: `🎙️ 録音・音響` タブへの「📂 過去テイク・録音WAV選択」機能追加 (`5a6dd16`)
  - Micro-Step 6: 録音ズレ補正の「▶ 伴奏と同期試聴」および微調整ボタン実装 (`11d6564`)
  - Micro-Step 7: v3.2.0 全体結合テスト（全7項目PASS）・引き継ぎ更新・Gitタグ `v3.2.0` 付与 (`751f48b`)
- [x] **ポータブル基底パス解決規約と `src/` 汚染防止知見（Gotcha #9）の記録** (2026-10-25) (`0106276`)
- [x] **【v3.1.0】練習環境と動画出力プリセットの分離・UI/UX抜本改修（Micro-Step 1〜7 完遂）** (2026-10-25) (`9832fb3`)
- [x] **タスク粒度の2層構造化知見（Gotcha #8: Micro Commit × Batch Package）の記録** (2026-10-25) (`22d031b`)
- [x] **AIモデル分業運用（Architect-Builder パターン：Gotcha #7）の知見化** (2026-10-25)
- [x] **【v3.0.0】基盤改修（Step 1〜8）および配布用パッケージクリーンビルド** (2026-10-25)

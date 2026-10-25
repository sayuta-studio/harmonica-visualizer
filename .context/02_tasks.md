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

#### - [x] **Micro-Step 4: メイン画面（`🎹 練習` タブ）への「📂 運指パターン（キー別プロファイル）切替・新規保存」UI設置と別キー作成アンロック機能**
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

#### - [x] **Micro-Step 5: `🎨 画面作り` タブの「100%動画プリセット専用化」と、`🎹 練習` タブ下部への「🎨 練習画面スタイル」統合**
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

#### - [x] **Micro-Step 6: システム環境設定ウィンドウ（`[⚙ 環境設定]` / `HarmonicaSettingsDialog`）の刷新とメイン画面接続**
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

#### - [x] **Micro-Step 7: スタジオ・エクスポート制御の `src/studio_controller.py` 分離と、録音・動画出力先の `projects/<曲名>/` 完全直結**
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

#### - [x] **Micro-Step 8: Ver.4.0.0 全体結合テスト (`tests/verify_v400_studio.py`) 実行・ドキュメント更新・Gitタグ `v4.0.0` 付与**
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


---

## 📋 記録・課題ストック（デバッグ・UI見直し候補）

### 課題 1: メイン画面（表面）と [⚙ 設定] ウィンドウの間での設定項目の二重存在・仕分け曖昧問題
- **症状・違和感**:
  - メイン画面の表面（練習タブや上部コントロール）にある設定項目が、右上の `[⚙ 設定]` ウィンドウ内にも重複して存在している。
  - 具体例：
    1. **メトロノーム設定**: 表面の再生コントロール周辺にもあり、`[⚙ 設定]` の「音響・録音デバイス」タブにもある。
    2. **ステップアップループ練習設定**: 表面の練習タブ「ループ・区間練習」内にもあり、`[⚙ 設定]` の「本体スキン・練習支援」タブにもある。
- **原因・背景**:
  - `HarmonicaSettingsDialog` は Ver.3.0 時代に作られた総合ダイアログをベースとしていたため、Ver.4.0 で「システム環境設定」として右上ボタンに分離した際、表面タブに残すものと設定ウィンドウだけに追い出すものの境界線（役割分担）の整理が不十分なまま既存項目が残っていた。
- **改善案（仕分けの境界線定義）**:
  - **表面（メイン画面）に出すもの【練習・演奏中に頻繁にいじる日常操作】**:
    - メトロノーム（ON/OFF、拍子、音量）
    - ステップアップ練習（ループ速度のアップ%設定）
    - 再生速度、移調（キー）、運指パターン切替
    - 練習画面スタイル（軌道、音名言語、4音グリッド）
  - **[⚙ 設定] に隠すもの【一度決めたら滅多に変えないインフラ・環境設定】**:
    - ガイドMIDI音源エンジン（WinMM vs 内蔵シンセ）
    - マイク入力デバイス、録音チャンネル数（モノラル/ステレオ）
    - ハーモニカ本体外観スキン（マウスピース、レバーボタン各種）
    - ポータブル保存先フォルダ管理（projects, recordings, exports の直接オープン）
    - （※メトロノームやステップアップ練習などの日常操作項目は `[⚙ 設定]` から撤去し、表面に一本化する）

### 課題 2: プロジェクト出自（動画生成ファースト）と日常練習ツール（練習ファースト）のUI設計思想・優先順位の再検討
- **背景・歴史的経緯**:
  - 本アプリの出自は「YouTube等のハーモニカ演奏動画をリッチにビジュアル化・書き出す動画生成ツール」から始まっている。
  - そのビジュアル表現を進化させた結果、「普段の練習ツールとしても非常に有用である」という形で機能が拡張されてきた。
  - そのため、内部アーキテクチャやUI設計の根底において、自然と「ビジュアル設定が根本（先頭）にある作り」になってしまっている。
- **検討の論点**:
  1. **表面パネルの軽量化（手の込み感を抑える）**:
     - 練習時に頻繁にいじらない詳細な設定（表面に出すとゴチャゴチャして手が込む印象を与えるもの）は、思い切って右上の `[⚙ 設定]` ウィンドウに逃がし、メインの練習画面をスッキリと保つ。
  2. **動画設定と練習設定の力関係の整理**:
     - 「動画制作者モード」と「日常プレイヤー練習モード」のどちらを主軸と捉え、UIの初期動線やタブ順序をどう構成するのが最も直感的か。
     - 一度決めたら変えない装飾系ビジュアル（レバーON装飾ライン、詳細なスキンパーツ、ノーツ不透明度等）は奥に逃がし、練習時には「ドレミ/英語」や「キー」「テンポ」などの音楽的パラメータのみに集中できるようにする。

### 課題 3: 設定画面のプロジェクトフォルダ階層の見える化とトップ直下 `recordings/` 混入の解消
- **症状・違和感**:
  - `[⚙ 設定]` の「プロジェクト・保存先管理」タブにおいて、リポジトリルート直下のパス表示と、直下の `recordings/` や `exports/` を開くボタンが並んでいる。
  - そのため、リポジトリトップ直下に `recordings/` フォルダが生成されてしまっている（画像1枚目）。
  - Ver.4.0.0 のアーキテクチャでは、**「楽曲プロジェクト（`projects/<曲名>/`）」が親** であり、その中に `takes/`（録音テイク）、`audio/`（外部伴奏）、`exports/`（完成動画）、`project.json` が自己完結する設計であるため、UIとフォルダ生成の実態がチグハグに見える。
- **ユーザー提案・改善案（視覚的な親子構造化と親切な案内）**:
  1. **UI上の親子関係の明示**:
     - `プロジェクトフォルダーの作成先:`（例: `.../projects/`）を表示し、`[📁 projects フォルダを開く]` ボタンを配置。
     - その下にインデントや枠を付けて、**「プロジェクトフォルダ内に自動生成されるデータ」** として以下を説明・案内する：
       - `├── source/` （MIDI原本）
       - `├── takes/` （録音テイクWAV）
       - `├── audio/` （外部伴奏ファイル）
       - `├── exports/` （完成動画 MP4/MOV）
       - `└── project.json` （運指・音量・プロジェクト設定）
  2. **ルート直下への `recordings/` 生成防止**:
     - 曲が未ロード状態で録音された場合でも、未保存用のテンポラリプロジェクト（例: `projects/_scratch/takes/`）に逃がすなどして、アプリ直下に `recordings/` が散らかるのを根絶する。

### 課題 4: [⚙ 設定] で変更したカスタムスキンが表の画面に即時反映されない問題
- **症状**:
  - 右上の `[⚙ 設定]` ウィンドウからカスタムスキン（本体カバーやレバーボタン）を変更し、「保存して閉じる」を押しても、メイン画面のハーモニカの見た目が切り替わらない。
  - `settings.json` には設定値が正しく保存されているのに、表面（練習画面）に反映されない。
- **原因（データ二重化と描画上書きの競合）**:
  1. `[⚙ 設定]` で保存されるスキン設定は、設定辞書直下の `self.user_settings["skin_mouthpiece_path"]` 等に格納される。
  2. 一方で、練習画面（OpenGLキャンバス）を描画する際は、練習専用スタイル辞書 `self.user_settings["practice_visual"]` の値を使って描画している。
  3. `practice_visual` 内部にも個別の `skin_mouthpiece_path: ""`（空文字）が存在するため、設定保存直後の描画更新（`_apply_visual_dict_to_ui_and_gl(pv)`）で、`practice_visual` 側の空データが `gl_widget` に渡されて上書きされ、直下に保存した新スキンが打ち消されてしまっていた。
- **解決方針**:
  - `[⚙ 設定]` でスキンが更新された際、`user_settings` 直下だけでなく `practice_visual` 辞書内のスキンキー（`skin_mouthpiece_path`, `skin_lever_off_path`, `skin_lever_on_path`, `skin_enabled`）にも同期反映する。
  - スキン設定は「練習スタイルごとにコロコロ変わるもの」ではなく「プレイヤーが愛用する楽器の外観」であるため、共通のグローバル設定として常に練習画面へ直結して描画されるように一本化する。

### 課題 5: 変え指モード（Fキー）時の変え指可能インジケーター枠線がモノクロテーマで白潰れする問題
- **症状**:
  - 変え指エディタモード（Fキー）をONにした際、変え指可能なノーツの外枠に強調枠（インジケーター）が表示される。
  - しかしカラーテーマ「モノクロ」を選択している場合、吹音ノーツ自体が白（`#FFFFFF`）であるため、白ノーツの上に白枠が重なり、同化して完全に潰れて視認できなくなる。
- **原因コード**:
  - `src/gl_visualizer.py` L1177 付近:
    ```python
    if not is_muted and getattr(self, "fingering_edit_mode", False) and nd.get("is_editable", False):
        painter.setPen(QPen(QColor(255, 255, 255, 230), max(1.8, 2.0 * scale)))
        painter.drawPolygon(QPolygonF(poly_pts))
    ```
    枠線の色が固定で `QColor(255, 255, 255, 230)`（完全な白色）になっているため。
- **改善案（明暗適応 / 反対色・コントラスト確保）**:
  - ノーツの塗り色（`fill_color`）の輝度（`L = 0.299*R + 0.587*G + 0.114*B`）を判定：
    - ノーツが明るい色（白や高輝度カラー、`L > 180`）の場合：濃い黒枠（`QColor(20, 20, 20, 240)`）または視認性の高いアクセントカラー。
    - ノーツが暗い色の場合：白枠（`QColor(255, 255, 255, 240)`）。
    - または「黒枠＋内側白枠」の二重縁取り（光彩アウトライン）にすることで、どんな背景・どんなカスタムカラーであっても100%確実に浮き上がって見えるようにする。

### 課題 6: キー別運指パターンのデフォルト名が `Key+12(+12st)` と二重表記で冗長な問題
- **症状**:
  - キー（移調）を変更して別名保存しようとした際、提案されるデフォルト名が `Key+12(+12st) - パターン 1` のようになり、「Key+12」と「+12st（半音）」が重複して表示され冗長でくどい。
- **原因コード**:
  - `src/harmonica_map.py` L195:
    ```python
    def format_transpose_key_label(transpose_val: int) -> str:
        ...
        if val == 0:
            return "原曲キー (±0)"
        elif val > 0:
            return f"Key+{val}(+{val}st)"  # ← ここで Key と st が二重表記
        else:
            return f"Key{val}({val}st)"
    ```
- **改善案（スッキリ簡潔な表記へ統一）**:
  - `Key +12 - パターン 1` または `+12半音 (Key+12)` のように重複をなくし、スッキリと読みやすい表記（例: `Key +12 - パターン 1`、`原曲キー (±0) - パターン 1`）に統一する。

### 課題 7: ステータスバー（コントロールバー右端）の移調表示の重複・冗長表現の簡素化
- **症状**:
  - 画像（コントロールバー右端のステータス表示）において、移調（`+1`, `+12` など）した際に：
    `🎹 移調: +12 st (+12半音) (伴奏含む)`
    のように、「+12 st」と「+12半音」が重複して並んでおり、画面幅を取る上に冗長で見づらい。
- **原因コード**:
  - `src/main.py` L4058 付近:
    ```python
    self.lbl_status_msg.setText(f"🎹 移調: {sign} st ({'原曲キー' if val == 0 else f'{sign}半音'}){acc_str}")
    ```
- **改善案（ユーザー提案によるスッキリ表現）**:
  - 原曲キー（`val == 0`）のときのみ：
    `🎹 原曲キー (伴奏含む)`
  - 移調時（`val != 0`）のとき：
    `🎹 Key +12 (伴奏含む)` または `🎹 移調: Key +12 (伴奏含む)`
  - 「st」や「半音」などの重複説明を省き、誰が見ても一瞬で直感的にキーが把握できるスッキリした表記に統一する。

### 課題 8: 【新機能企画】YouTube Shorts (9:16) 上下2分割（スプリット）レイアウトの追加
- **ユーザー要望・利用シーン**:
  - 現在の YouTube Shorts（9:16縦型）は、縦長画面いっぱいに上から下までノーツが流れるレイアウトになっている。
  - TikTokやYouTube Shortsで主流となっている **「実写演奏動画・PV ＋ ハーモニカ運指」の上下2分割（スプリットスクリーン）** を作成したい。
    - **パターンA（上部ハーモニカ ＋ 下部自由動画/実写）**: 画面上部に通常の16:9比率でハーモニカノーツを配置し、下部エリアに実写の手元動画や背景動画を配置。
    - **パターンB（上部PV/実写 ＋ 下部ハーモニカ）**: 画面上部に本家PVや顔出し演奏動画を配置し、下部に16:9のハーモニカノーツを配置。
- **アーキテクチャ・設計アイデア**:
  1. **プリセットまたはレイアウト配置（Placement）設定の追加**:
     - 縦型 9:16 の出力時、ビジュアライザーの描画領域（ビューポート）を以下から選択可能にする：
       - `全画面（縦型フル展開）` （現在の標準Shorts）
       - `上部配置 (16:9)` （下半分を空き領域/背景動画エリアにする）
       - `下部配置 (16:9)` （上半分を空き領域/PVエリアにする）
       - `中央配置 (16:9)`
  2. **外部動画埋め込み / 透過エクスポートとの相乗効果**:
     - 下部（または上部）に外部動画（MP4）を直接指定してFFmpegで2画面合成するか、あるいは空きエリアを透過（透明）にしておき、動画編集ソフト（Premiere, DaVinci, CapCut等）で重ねやすくする。
  3. **動画プリセットへの採用検討**:
     - 公式プリセットとして `📱 YouTube Shorts (上下分割・上ハーモニカ)` / `📱 YouTube Shorts (上下分割・下ハーモニカ)` を追加するか、動画画面タブ内の配置オプションとして選べるようにする。

### 課題 9: 動画プリセット切替時に画面比率（ratio_combo）が同期されず、Shorts等のプリセット比率が4:3等に逆上書き破壊される問題
- **症状**:
  - 画像（`media_1792915527872_25d533ea.png`）の通り、`🎨 動画画面` タブでプリセット「📱 YouTube Shorts (縦型・解説)」を選択しているにもかかわらず、下の「比率」コンボが `4:3 (スタンダード)` のままになり、画面左のキャンバスも縦型にならず 4:3 のままになってしまう。
- **原因（比率コンボボックスの未同期と逆流上書き）**:
  1. `_on_video_preset_changed` および `_apply_visual_dict_to_ui_and_gl` において、`gl_widget.set_aspect_ratio(aspect_ratio)` は呼ばれているが、UIコントロールである `self.ratio_combo` をプリセットの `aspect_ratio` に合わせて切り替える処理が**完全に欠落**していた。
  2. そのため、`self.ratio_combo` に過去の比率（4:3や16:9）が取り残される。
  3. その状態でプリセット保存（`_on_save_video_preset`）や画面保存（`_save_current_settings`）が動くと、取り残された `ratio_combo` の値（4:3）が読み取られ、なんと **Shorts プリセット自身の `aspect_ratio` が `4:3` に逆上書きされて壊れてしまう**。
- **改善策**:
  1. `_apply_visual_dict_to_ui_and_gl`（および `_on_video_preset_changed`）で、プリセットの比率文字列（"9:16", "16:9", "4:3"）を検出し、`self.ratio_combo` を `blockSignals(True)` で即座に該当比率へ同期連動させる。
  2. 公式プリセット（Shorts等）の `aspect_ratio` がユーザー設定ファイルで誤って4:3等に上書きされてしまっている場合、公式デフォルト値（`settings_manager.DEFAULT_VIDEO_PRESETS`）から比率を自動修復・再バインドする安全ガードを追加する。

### 課題 10: `🎨 動画画面` タブ内の設定セクション縦配置の順序改善（思考の流れに沿った再配置）
- **現状の配置順（違和感）**:
  1. `🎬 動画プリセットのデザイン設定` (プリセット選択・保存)
  2. `🎵 演奏・ノーツ表示 (共通)` (ノーツ軌道、音名表記)  ← 間に挟まってしまっている
  3. `📐 画面比率 (構図プレビュー連動)` (比率コンボ)
  4. `カラーテーマ・描画オプション`
- **問題点**:
  - 動画作成時のユーザーの自然な思考フローは「①プリセット選択」→「②画面の形・比率（横型か縦型か）を決める」→「③その画面上でのノーツや色のデザインを調整する」という順序である。
  - しかし現在はプリセットの直後にノーツ表示があり、その下に画面比率があるため、構図決定の動線が分断されている。
- **改善案（自然な制作フローに沿った配置順）**:
  1. **`🎬 動画プリセットのデザイン設定`** (最上部: プリセット切替・保存・初期化)
  2. **`📐 画面比率 (構図プレビュー連動)`** (直下に配置: 16:9 / 9:16 / 4:3)
  3. **`🎵 演奏・ノーツ表示`** (ノーツ軌道、音名表記、4音グリッド)
  4. **`🎨 カラーテーマ・装飾設定`** (テーマ、吹吸色、レバー装飾、不透明度、表示チェック群)
  5. **`🖼️ 背景画像 & 減光 (コントラスト)`**
  6. **`🎷 ハーモニカ本体スキン`**

### 課題 11: 【実装漏れ 1】`🎨 動画画面` タブへの「📥 練習画面の設定を適用 (コピー)」機能の追加（v3.1.0 設計での合意項目の漏れ回収）
- **確認結果**:
  - `src/main.py` の `_build_tab_design`（動画画面タブ）を確認したところ、現在は「💾 保存」「➕ 別名保存」「↺ 初期化」の3ボタンのみが存在しており、**「練習画面のスタイルをそのまま動画画面に引っ張ってくる（インポートする）ボタン」は未実装**であることを確認しました。
- **ユーザー要望・利用シーン**:
  - 日頃の練習で細かく調整したお気に入りのビジュアルスタイル（ノーツ軌道・音名言語・カラーテーマ・スキンパーツ設定等）を、ワンクリックで選択中の動画プリセットにコピー＆適用したい。
- **改善案（機能設計）**:
  - `🎨 動画画面` タブ上部のプリセットバーに **`[📥 練習画面からコピー]`** ボタンを新設。
  - **動作フロー**:
    1. クリック時、「現在の練習画面のスタイル設定を、選択中の動画プリセットに読み込みますか？」と確認。
    2. OKであれば `self.user_settings["practice_visual"]` の設定辞書を選択中の動画プリセットにディープコピー。
    3. UI（軌道、音名、色、スキン）およびGLキャンバスに即時反映。

### 課題 12: 【実装漏れ 2】動画プリセット操作部における「自作プリセットの明示的削除（🗑️ 削除）」UIの欠落と初期化ボタン相乗り問題
- **打ち合わせ経緯・設計合意（v3.1.0 設計書 STEP 128）**:
  - 「ユーザーが微調整して『新規プリセット保存』『上書き』『削除』できること」と合意されていた。
- **現状の実装と課題**:
  - 現在の `🎨 動画画面` タブには `[💾 保存]`, `[➕ 別名保存...]`, `[↺ 初期化]` の3ボタンのみが配置されている。
  - 自作プリセットを削除したい場合、`[↺ 初期化]` ボタンに「公式プリセットは初期値へ復元、自作プリセットは削除します」と相乗り（兼任）させているため、直感的に「どうやって消せばいいかわからない」状態になっている。
- **改善案**:
  - 公式プリセット選択時は `[↺ 初期値に戻す]`、自作プリセット選択時は `[🗑️ 削除]` にボタンのラベルとアイコンを動的切り替えするか、明示的な `[🗑️ 削除]` ボタンを追加して制作フローの迷いをなくす。

### 課題 13: 動画プリセットの階層逆転・重複解消と「練習 vs 動画制作」の2階層タブ化（UI抜本整理）
- **症状・ユーザーの違和感**:
  1. **プリセット操作バーの重複と欠落**:
     - 「動画画面（タブ2）」と「動画出力（タブ4）」の両方にプリセット保存・別名保存バーが重複して存在している。
     - にもかかわらず、中間にある「録音・音響（タブ3）」にはプリセットバーが存在しないため、片側から順番に操作を進めると不自然に見える。
  2. **プリセットの包括範囲とUI階層の逆転**:
     - 本来、動画プリセット（`video_presets`）は「画面デザイン」「音声ミキサー」「出力エンコード」の全設定を丸ごと包括する最上位の入れ物（コンテナ）である。
     - にもかかわらず、下位のタブの中にプリセットバーが個別に配置されているため、「タブを切り替えているのにプリセットがタブの下にある」という階層の逆転が生じている。
  3. **右下の `[💾 設定を保存]` ボタンの迷い・目的不明**:
     - 右下に常時置かれている `[💾 設定を保存]`（`btn_save_all`）が、「プリセットの保存」と何が違うのかサッパリ分からず、何がどう保存されるのか迷いを生じさせている。
- **発見事項（コード照合結果）**:
  - 実は `_build_tab_export`（タブ4）の2234行目には `btn_copy_practice_visual`（「📋 現在の「練習画面」の見た目を反映」）が既に存在していた！
  - しかしタブ2（動画画面）側には設置されておらず、タブ4側だけに隠れていたため、「画面を作っているタブ2にコピーボタンが無い」という摩擦が生じていた。
- **ユーザー提案による抜本的解決策（2階層タブアーキテクチャ）**:
  1. **最上位（第1階層タブ）の2極化**:
     - **`🎹 練習`** モード
     - **`🎬 動画制作`** モード
  2. **`🎬 動画制作` モード内の構造（親子関係の正常化）**:
     - 上部ヘッダー部: **「📁 動画プリセット選択・保存バー」を常時1箇所のみに集約配置**
       （`[プリセット▼]` ＋ `[💾 保存]` ＋ `[➕ 別名保存...]` ＋ `[↺ 初期値/削除]` ＋ `[📋 練習画面からコピー]`）
     - その下部: プリセットの内訳を編集する **第2階層サブタブ（3タブ）** を展開：
       - **`[🎨 画面デザイン]`** （画面比率、ノーツ軌道・音名、カラー、スキン、背景画像）
       - **`[🎙️ 録音・音響]`** （テイク選択、外部伴奏、ラウドネス解析、リバーブ、音量ミキサー）
       - **`[🎬 動画書き出し]`** （出力範囲、フェードイン/アウト、エンコード設定、出力実行）
  3. **右下 `[💾 設定を保存]` ボタンの整理**:
     - プリセット側の「💾 保存」と競合・混乱を招くため、常時ボタンを撤去し、設定は都度自動永続化、または明確に分離する。

### 課題 14: 「録音・音響」タブ最上部の「音量制御 ＆ パート音色」の撤去・役割整理（UIスリム化）
- **症状・ユーザーの違和感**:
  - `🎙️ 録音・音響` タブ（タブ3）の最上部に「🔊 音量制御 ＆ パート音色」フレーム（マスター音量スライダー、ガイド音源切替、主旋律ハーモニカ固定）が居座っている。
  - しかし以下の理由から、ここに配置する必然性が全くなく、貴重な縦スペースを無駄に圧迫している：
    1. **マスター音量**: 動画作成・出力時には専用の「🎛️ 音量ミキサー（YouTube規格ラウドネス）」が下部に存在するため、ここでマスター音量をいじる必要がない。日常の練習音量としてもOS側やスピーカー側で調整できる。
    2. **ガイド音源（WinMM vs 内蔵軽量シンセ）**: MIDIが正常に鳴らない特殊環境向けの「システムバックアップ設定」であり、録音のたびに切り替えるものではない。これは右上 `[⚙ 設定]`（音響・録音デバイスタブ）にのみ存在すれば十分。
    3. **主旋律をハーモニカ音色に固定**: 上部ヘッダーの `[🎼 パート]` ウィンドウ側で曲ごとのパート割や音色制御を行うのが自然であり、サイドバーに常駐させる必要がない。
- **改善案（UIスッキリ化）**:
  - `🎙️ 録音・音響` タブから「🔊 音量制御 ＆ パート音色」フレーム（`f_vol`）を丸ごと撤去する。
  - ガイド音源エンジンは `[⚙ 設定]` に一本化、パート音色制御は `[🎼 パート]` に一本化する。
  - これにより、「録音・音響」タブは「①マイク録音・テイク選択」「②外部伴奏」「③リバーブ」「④音量ミキサー」という、本来の音響制作に特化したスリムで使いやすい構成になる。

### 課題 15: 動画出力タブの「音声にリバーブを適用」重複チェックボックスの撤去
- **症状・ユーザーの違和感**:
  - `🎬 動画出力` タブ（タブ4）の「動画の音声トラック」設定内に、ポツンと「音声にリバーブを適用（`chk_exp_reverb`）」チェックボックスが存在している。
  - しかし以下の問題がある：
    1. **二重リバーブのリスク**: すでに `🎙️ 録音・音響` タブ（タブ3）でマイク録音に対して空間タイプや深さ（%）を指定してリバーブを適用・試聴する仕組みが存在しているため、動画出力時にも重ねてリバーブが適用されると、二重にリバーブがかかって音が濁ってしまう。
    2. **パラメータ設定の欠落**: 動画出力タブ側には「リバーブの深さ」や「空間タイプ」の調整コントロールが一切なく、チェックボックスだけが置かれているため、何がどう適用されるのかが極めて不透明で不安を与える。
- **改善案（音響制作タブへの一本化）**:
  - `🎬 動画出力` タブの「音声にリバーブを適用」チェックボックス（`self.chk_exp_reverb`）を丸ごと撤去する。
  - リバーブの設定および適用は、すべて `🎙️ 録音・音響` タブ（または将来の2階層タブ内の音声・ミキサー部）に一本化し、動画書き出し時はその調整済みの録音テイクをそのまま合成する。
  - これにより、二重リバーブ事故を根本防止し、動画出力タブをさらにシンプルに整理できる。

### 課題 16: 動画出力タブのタイトル・クレジット設定とフェードイン/アウトの配置適正化（UI整理）
- **症状・ユーザーの違和感**:
  1. **タイトル表示チェックボックスとテンプレート「なし」の二重存在**:
     - 「タイトル・クレジットを表示（`chk_exp_title`）」チェックボックスがある一方で、すぐ下の「配置テンプレート」プルダウン内にも「なし」が存在している。
     - プルダウンで「なし」を選べば消えるため、チェックボックスが完全に冗長で1ステップ余計な操作になっている。
  2. **フェードイン・フェードアウトがタイトル欄に誤配置されている**:
     - 動画全体の明転・暗転効果である「フェードイン（秒）」と「フェードアウト（秒）」が、なぜか「タイトル＆クレジット表示」フレーム内に混入している。
     - これはタイトル設定ではなく「動画・画面演出（余白と連動するエンコード設定）」であるため、場所が不自然。
  3. **「フェード対象（フェード中のタイトル挙動）」の整理**:
     - 一方で、その下にある「フェード対象（`combo_fade_title`）」は「フェードイン/アウト中にタイトルをどう表示するか」という**タイトルの挙動**そのものであるため、これはタイトル欄に属しているのが自然。
- **改善案（自然な配置・UIスリム化）**:
  1. **チェックボックス撤去 ＆ 配置プルダウンへの一本化**:
     - `chk_exp_title`（チェックボックス）を廃止し、プルダウンのラベルを「表示 / 配置:」にして選択肢（`なし`, `イントロ中央のみ`, `左上常時`, `右上常時`, ...）に一本化。「なし」選択時はタイトル・クレジット入力欄を自動グレーアウトする。
  2. **フェードイン/アウトの移動**:
     - 「フェードイン（秒）」「フェードアウト（秒）」を、画面演出・時間制御のセクション（前余白・後余白のすぐ隣・直下）へ移動する（余白とフェードの長さを並べて確認・調整できるようにする）。
  3. **タイトル欄には「フェード中の表示挙動」を残す**:
     - タイトル欄には「曲名」「クレジット」および「フェード中のタイトル挙動（画面と一緒にフェード / 常時表示 / 非表示）」のみを配置し、タイトルの見た目設定として純化する。

### 課題 17: 【UI機能企画】サイドバー項目の折りたたみアコーディオン化（Collapsible Section）による俯瞰性の劇的向上
- **ユーザー要望・問題意識**:
  - 現在、右サイドバーの各タブ（練習タブ、動画画面タブ等）は設定項目が縦にずらりと並んでおり、縦スクロールが長すぎて「どんな項目があるのか」を一目で俯瞰できない。
  - 各セクション（グループフレーム）のヘッダーを「タイトル1行（▶ / ▼）」に最小化（アコーディオン開閉）できれば、スクロールなしで全体を見渡し、必要な項目だけを広げて操作できるようになるのではないか。
  - これができれば、練習タブの下部に動画デザインなどの詳細設定を同居させても画面が散らからず、スマートに管理できる。
- **技術的実現可能性の検証（PyQt6）**:
  - **100%可能（極めてシンプルかつ堅牢に実装可能）**:
    - `CollapsibleSection(QWidget)` という汎用コンポーネント（約40行）を作成。
    - ヘッダーバー（`[▶ タイトル]` / `[▼ タイトル]` をトグルするボタン）と、コンテンツ領域（中身のレイアウトを包む `QWidget`）の2層構造。
    - ヘッダークリック時に `content_widget.setVisible(is_expanded)` を切り替えるだけで、中身のボタンやスライダー等の既存コードを一切壊さずにそのまま収容可能。
    - アプリ起動時のデフォルト開閉状態（日常操作は展開、詳細設定は初期折りたたみ）や、ユーザーの開閉状態の記憶も容易。
- **UI/UX上の効果**:
  1. **全項目のワンビュー俯瞰**:
     - 例えば練習タブであれば、「🎷 ハーモニカモデル」「🎼 運指」「🎚️ 移調」「📈 ステップアップ」「🔊 音源切替」「🎨 表示スタイル」の6行のタイトルが1画面内にすっきりと収まる。
  2. **作業集中と省スペース化**:
     - 演奏・練習中は「運指」と「移調」だけを開いておき、スタイルやステップアップは折りたたんでおくことで、無駄な視覚的ノイズを遮断できる。

### 課題 18: タイトルカードの表示時間（秒数）および消え方（フェード/カット）の独立設定化
- **症状・ユーザーの違和感**:
  - タイトルを「フェードイン連携」にして書き出した際、動画が暗闇からフワーッとフェードインして明るくなり、ようやくタイトルがハッキリ見えた瞬間に **パッと唐突にタイトルが消えてしまう**。
  - タイトルを読ませる間（表示維持時間）がなく、余韻がぶち壊しになってしまう。
- **原因コード判明（`src/video_exporter.py` L905〜914）**:
  - タイトル中央カードの表示期間（`effective_intro_dur`）が、動画の「前余白（`intro_sec`）」に強制連動している。
  - そのため、前余白2.0秒・フェードイン1.5秒などに設定していると、フェードインが完了したまさにそのタイミング（2.0秒時点）でタイトル表示期間が終了し、瞬時に消滅する計算式になっていた。
- **改善案（独立した時間・演出パラメータの導入）**:
  1. **タイトルの「表示維持時間（秒）」スピンボックス新設**:
     - `タイトル表示時間:`（例: デフォルト 3.5秒、範囲 1.0〜10.0秒）
     - 動画の前余白とは独立して、「タイトルを動画開始から何秒間しっかり見せるか」をユーザーが自由に設定できるようにする。
  2. **タイトルの「消え方」オプション**:
     - `消え方:`（`フェードアウトで消える (推奨)` / `即座に消える (カット)`）
     - フェードアウト時は、設定した表示時間の最後の0.8秒ほどをかけて文字とカード背景が滑らかに透明（alpha=0）になってフェードアウト消去し、美しい余韻を残す。
  3. **UI配置（課題16のタイトル欄へ集約）**:
     - タイトル欄内に `表示・配置` ➔ `表示時間 (秒)` ➔ `消え方 (フェード/カット)` を並べ、完璧なタイトル演出コントロールを実現する。


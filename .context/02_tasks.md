# タスク管理・実装指示書 (02_tasks.md)

## 進行中 (In Progress) / 次期マイルストーン: Ver.4.1.0
### 🚀 【v4.1.0】全21課題の統合解消（UI/UX 2階層タブ刷新・折りたたみアコーディオン・公式5大プリセット再設計・演出＆起動高速化）

> **【実装担当（Gemini 3.8 / Builder）への絶対遵守ルール（Gotcha #7, #8, #9）】**
> 1. **Git層（Micro Commit）**: 以下の **Micro-Step 1 〜 10** を **必ず1ステップずつ順番に** 実行し、各ステップ完了ごとに構文チェック（`python -m py_compile`）と指定の **Gitコミット** を必ず打つこと（複数ステップの1コミットまとめは厳禁）。
> 2. **人間対話層（Batch Package）**: 人間の確認負荷軽減のため、**Package 1（Step 1〜2）**、**Package 2（Step 3〜4）**、**Package 3（Step 5〜6）**、**Package 4（Step 7〜8）**、**Package 5（Step 9〜10）** の単位で連続実行し、パッケージ完了（または自動停止条件到達）ごとに報告すること。
> 3. **スコープ＆シグナル衛生**: 関数内でのインライン `import` は厳禁（ファイル先頭に集約）。UI値のプログラム変更時は必ず `blockSignals(True)` / `blockSignals(False)` で囲むこと。また Windows コンソール出力時は `sys.stdout.reconfigure(encoding='utf-8')` を徹底すること。

---

### 📊 全21課題 ➔ Micro-Step 完全対応マトリクス

| 課題 | 内容要約 | 対応ステップ |
| :---: | :--- | :---: |
| **課題 1** | メイン画面と `[⚙ 設定]` の重複解消（メトロノーム・ステップアップを表面に一本化） | **Step 3** |
| **課題 2** | 練習ファースト vs 動画制作の優先度整理（装飾を奥へ、音楽パラメータを表面へ） | **Step 3, 5, 6** |
| **課題 3** | `[⚙ 設定]` のプロジェクト階層ツリー可視化 ＆ ルート直下 `recordings/` 混入防止 | **Step 1, 3** |
| **課題 4** | `[⚙ 設定]` で変更したカスタムスキンが練習画面に即時反映されないバグ修正 | **Step 1** |
| **課題 5** | モノクロテーマ時の変え指可能マーク白潰れ解消（明暗適応コントラスト二重枠） | **Step 2** |
| **課題 6** | キー別運指パターンのデフォルト名 `Key+12(+12st)` の二重表記解消（`Key +12`） | **Step 2** |
| **課題 7** | ステータスバー移調表示の簡素化（`🎹 原曲キー` / `🎹 Key +12`） | **Step 2** |
| **課題 8** | YouTube Shorts (9:16) 上下2分割（スプリットスクリーン）構図配置の追加 | **Step 9** |
| **課題 9** | 動画プリセット切替時に `ratio_combo` が未同期で Shorts が 4:3 等に逆上書き破壊されるバグ修正 | **Step 1** |
| **課題 10** | 動画画面デザインの縦配置順序改善（①画面比率 ➔ ②ノーツ表示 ➔ ③カラー・装飾） | **Step 6** |
| **課題 11** | 【実装漏れ1】動画プリセット操作部への「📋 練習画面からコピー」ボタン直結 | **Step 5** |
| **課題 12** | 【実装漏れ2】自作プリセット選択時の「🗑️ 削除」ボタン動的切替（公式は「↺ 初期値」） | **Step 5** |
| **課題 13** | 「🎹 練習」vs「🎬 動画制作」の2階層タブ化、プリセットバー一元化、右下保存ボタン撤去 | **Step 5** |
| **課題 14** | 録音タブ最上部の不要な「音量＆パート音色」枠の撤去と `[🎼 パート]` への音色固定移設 | **Step 3, 7** |
| **課題 15** | 動画出力タブの「音声にリバーブを適用（`chk_exp_reverb`）」重複チェックボックス撤去 | **Step 7** |
| **課題 16** | タイトル表示チェックボックス廃止（配置プルダウン一本化）とフェードの余白直下への移動 | **Step 7** |
| **課題 17** | サイドバー全セクションの「折りたたみアコーディオン（`CollapsibleSection`）」化 | **Step 6** |
| **課題 18** | タイトルカードの表示維持時間（`0.1s〜15.0s`）と消え方（フェード/カット）の独立設定化 | **Step 7, 8** |
| **課題 19** | 起動時スプラッシュ画面（`QSplashScreen`）、多重起動防止ロック、起動高速化 | **Step 10** |
| **課題 20** | `[⚙ 設定]` ウィンドウへの「🎬 公式プリセット一覧・マトリクス比較表」タブ搭載 | **Step 4** |
| **課題 21** | 公式初期プリセット（5種）の再設計（王道16:9背景画像MV追加、解説時の垂直落下化） | **Step 4** |

---

### 📦 Batch Package 1: 致命的バグ・データ破壊の即時解消 ＆ 表記・描画コントラスト改善（Micro-Step 1 〜 2）

#### - [x] **Micro-Step 1: 動画プリセット比率の逆上書き破壊バグ修正（課題9）、カスタムスキン即時反映（課題4）、およびトップ直下 `recordings/` 混入防止（課題3前半）**
- **対象ファイル**: `src/settings_manager.py`, `src/main.py`, `src/project_manager.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/settings_manager.py` (`load_settings`, L430付近)**:
     - 公式プリセットの `aspect_ratio` が過去のバグで 4:3 等に汚染されている場合、公式デフォルト定義の値で自動修復するガードを追加：
       ```python
       for p_name, def_p in DEFAULT_VIDEO_PRESETS.items():
           if p_name not in presets or not isinstance(presets[p_name], dict):
               presets[p_name] = copy.deepcopy(def_p)
           else:
               for pk, pv in def_p.items():
                   presets[p_name].setdefault(pk, copy.deepcopy(pv))
               # ★ Shorts等の公式プリセットの比率が誤って上書きされていた場合は公式比率に修復
               if "Shorts" in p_name or "縦型" in p_name:
                   presets[p_name]["aspect_ratio"] = "9:16"
       ```
  2. **`src/main.py` (`_apply_visual_dict_to_ui_and_gl`, L2796〜2876付近)**:
     - `aspect_ratio` 引数に応じて `self.ratio_combo` の選択状態を `blockSignals(True)` で確実に同期するコードを追加：
       ```python
       if hasattr(self, "ratio_combo"):
           self.ratio_combo.blockSignals(True)
           if "9:16" in str(aspect_ratio):
               self.ratio_combo.setCurrentText("9:16 (縦長 ショート/TikTok)")
           elif "4:3" in str(aspect_ratio):
               self.ratio_combo.setCurrentText("4:3 (スタンダード)")
           else:
               self.ratio_combo.setCurrentText("16:9 (横長 YouTube標準)")
           self.ratio_combo.blockSignals(False)
       ```
  3. **`src/main.py` (`_on_open_env_settings_dialog`, L2878〜2891付近)**:
     - `[⚙ 設定]` ダイアログで保存されたスキン設定を `self.user_settings["practice_visual"]` 辞書にも即時伝搬させる：
       ```python
       def _on_open_env_settings_dialog(self):
           dlg = HarmonicaSettingsDialog(self.user_settings, parent=self)
           if dlg.exec():
               new_settings = dlg.get_settings()
               self.user_settings.update(new_settings)
               # ★ 練習用ビジュアル辞書にもカスタムスキン設定を同期反映
               pv = self.user_settings.setdefault("practice_visual", copy.deepcopy(settings_manager.DEFAULT_PRACTICE_VISUAL))
               for sk in ("skin_enabled", "skin_mouthpiece_path", "skin_lever_off_path", "skin_lever_on_path", "lever_deco_mode", "note_opacity"):
                   if sk in new_settings:
                       pv[sk] = new_settings[sk]
               settings_manager.save_settings(self.user_settings)
               self._apply_user_settings()
               self._sync_practice_style_ui_values(pv)
               if getattr(self, "_visual_edit_target", "practice") == "practice":
                   self._apply_visual_dict_to_ui_and_gl(pv, aspect_ratio="16:9", is_chromakey=False, chroma_color="ノーマル（黒）")
               else:
                   self.gl_widget.set_skin_enabled(bool(new_settings.get("skin_enabled", True)))
                   self.gl_widget.set_custom_skins(
                       mouthpiece_path=new_settings.get("skin_mouthpiece_path", ""),
                       lever_off_path=new_settings.get("skin_lever_off_path", ""),
                       lever_on_path=new_settings.get("skin_lever_on_path", "")
                   )
                   self.gl_widget.update()
       ```
  4. **`src/project_manager.py` (`get_active_takes_dir`, `get_active_exports_dir`, L190〜210付近)**:
     - フォールバック先を `get_portable_path("projects/_demo_chromatic/takes")` および `get_portable_path("projects/_demo_chromatic/exports")` に変更して `os.makedirs(..., exist_ok=True)` を実行し、リポジトリルート直下に `recordings/` が生成されないようにする。またリポジトリ直下に空の `recordings` があれば削除する。
- **コミットメッセージ**: `fix(core): sync aspect ratio combo on preset switch, propagate custom skins to practice visual, and route fallback takes to project container`

---

#### - [x] **Micro-Step 2: モノクロ時の変え指枠線コントラスト改善（課題5）、キー別運指パターン名（課題6）＆ ステータスバー移調表記（課題7）のスリム化**
- **対象ファイル**: `src/gl_visualizer.py`, `src/harmonica_map.py`, `src/main.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/gl_visualizer.py` (L1175〜1182付近)**:
     - 変え指モード時の枠線描画を、ノーツ塗り色 `fill_color` の輝度に応じた二重コントラスト枠に刷新：
       ```python
       if not is_muted and getattr(self, "fingering_edit_mode", False) and nd.get("is_editable", False):
           lum = 0.299 * fill_color.red() + 0.587 * fill_color.green() + 0.114 * fill_color.blue()
           if lum > 175:
               # 白や高輝度ノーツ（モノクロテーマ等）: 外側ダーク枠 ＋ 内側シアン強調枠
               painter.setPen(QPen(QColor(15, 23, 42, 250), max(3.0, 3.4 * scale)))
               painter.drawPolygon(QPolygonF(poly_pts))
               painter.setPen(QPen(QColor(0, 229, 255, 255), max(1.5, 1.8 * scale)))
               painter.drawPolygon(QPolygonF(poly_pts))
           else:
               # 通常・暗色ノーツ: 外側黒縁 ＋ 内側白枠
               painter.setPen(QPen(QColor(0, 0, 0, 200), max(2.8, 3.2 * scale)))
               painter.drawPolygon(QPolygonF(poly_pts))
               painter.setPen(QPen(QColor(255, 255, 255, 245), max(1.5, 1.8 * scale)))
               painter.drawPolygon(QPolygonF(poly_pts))
       ```
  2. **`src/harmonica_map.py` (`format_transpose_key_label`, L190〜202付近)**:
     - `(+12st)` の冗長な二重表記を廃止：
       ```python
       def format_transpose_key_label(transpose_val: int) -> str:
           try:
               val = int(transpose_val)
           except Exception:
               val = 0
           if val == 0:
               return "原曲キー"
           elif val > 0:
               return f"Key +{val}"
           else:
               return f"Key {val}"
       ```
  3. **`src/main.py` (`_on_transpose_changed`, L4052〜4062付近)**:
     - ステータスバーの移調表示から `st` と `半音` の重複を省き、原曲時のみ「原曲キー」、移調時は「Key +12」のみとする：
       ```python
       acc_str = " (伴奏含む)" if accomp else " (主旋律のみ)"
       if val == 0:
           self.lbl_status_msg.setText(f"🎹 原曲キー{acc_str}")
       else:
           sign = f"+{val}" if val > 0 else str(val)
           self.lbl_status_msg.setText(f"🎹 Key {sign}{acc_str}")
       ```
- **コミットメッセージ**: `fix(ui-polish): add adaptive contrast outline for fingering edit mode and simplify transpose key labels`

---

### 📦 Batch Package 2: `[⚙ 設定]` ＆ `[🎼 パート]` ダイアログの役割整理と公式5大プリセット再設計・比較表搭載（Micro-Step 3 〜 4）

#### - [ ] **Micro-Step 3: `[⚙ 設定]` からの重複項目撤去（課題1, 2）、プロジェクト階層ツリー可視化（課題3後半）、および `[🎼 パート]` への主旋律音色固定移設（課題14前半）**
- **対象ファイル**: `src/dialogs.py`, `src/main.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/dialogs.py` (`HarmonicaSettingsDialog._init_ui`, L60〜225付近)**:
     - タブ1（`🔊 音響・録音デバイス`）: `row_metro`（メトロノーム）と `chk_force_harmonica` を画面レイアウトから外し（互換のため内部属性としては保持）、MIDI音源エンジン・録音チャンネル数・録音ズレ補正初期値のみを表示。
     - タブ2（`🎨 本体スキン・外観設定`）: タブ名を `"🎨 本体スキン・外観設定"` とし、練習タブと重複するステップアップ練習設定（`chk_stepup`, `row_sp`）を画面レイアウトから外す。
     - タブ3（`📁 プロジェクト・保存先管理`）を以下の親子階層デザインに全面刷新：
       ```python
       v_proj.addWidget(QLabel("<b>【1. プロジェクトフォルダーの作成先 (親フォルダー)】</b>"))
       v_proj.addWidget(QLabel("読み込んだMIDI曲ごとに固有フォルダーが自動作成される親ディレクトリ："))
       self.edit_base_path = QLineEdit(self)
       self.edit_base_path.setReadOnly(True)
       self.edit_base_path.setText(os.path.abspath(get_portable_path("projects")))
       v_proj.addWidget(self.edit_base_path)

       btn_proj_dir = QPushButton("📂 プロジェクト一覧フォルダー (projects/) を直接開く", self)
       btn_proj_dir.clicked.connect(lambda: self._open_dir(get_portable_path("projects")))
       v_proj.addWidget(btn_proj_dir)

       v_proj.addSpacing(8)
       v_proj.addWidget(QLabel("<b>【2. プロジェクトフォルダー内の自動生成構造 (子フォルダー)】</b>"))
       tree_frame = QFrame(self)
       tree_frame.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 8px; }")
       l_tree = QVBoxLayout(tree_frame)
       tree_label = QLabel(
           "📁 <b>projects / &lt;各MIDI曲名フォルダー&gt; /</b><br>"
           "&nbsp;&nbsp;├── 📂 <b>source/</b> &nbsp;&nbsp;<span style='color:#94A3B8;'>（読み込んだMIDI原本の自動バックアップ）</span><br>"
           "&nbsp;&nbsp;├── 📂 <b>takes/</b> &nbsp;&nbsp;&nbsp;<span style='color:#94A3B8;'>（マイク録音した演奏テイク WAV）</span><br>"
           "&nbsp;&nbsp;├── 📂 <b>audio/</b> &nbsp;&nbsp;&nbsp;<span style='color:#94A3B8;'>（外部伴奏音源 WAV/MP3）</span><br>"
           "&nbsp;&nbsp;├── 📂 <b>exports/</b> &nbsp;<span style='color:#94A3B8;'>（書き出した完成動画 MP4/MOV）</span><br>"
           "&nbsp;&nbsp;└── 📄 <b>project.json</b> <span style='color:#94A3B8;'>（曲別の運指パターン・移調・同期設定）</span>"
       )
       tree_label.setStyleSheet("font-size: 12px; line-height: 1.5;")
       l_tree.addWidget(tree_label)
       v_proj.addWidget(tree_frame)

       btn_cur_song_dir = QPushButton("📂 現在開いている楽曲の固有フォルダーを開く", self)
       btn_cur_song_dir.clicked.connect(lambda: self._open_dir(project_manager.get_active_project_dir()))
       v_proj.addWidget(btn_cur_song_dir)
       ```
       （※ `src/dialogs.py` 先頭に `import project_manager` を追加すること）。
  2. **`src/dialogs.py` (`PartSelectDialog`, L348〜512付近) & `src/main.py` (`_on_open_part_dialog`, L4442付近)**:
     - `PartSelectDialog.__init__` に `force_harmonica: bool = True` 引数を追加。
     - `PartSelectDialog._init_ui` の下部ボタン行（`btn_layout`）の左端に：
       ```python
       self.chk_force_harmonica = QCheckBox("主旋律パートをハーモニカ音色 (GM 22) に固定して再生", self)
       self.chk_force_harmonica.setChecked(bool(self.force_harmonica))
       btn_layout.addWidget(self.chk_force_harmonica)
       ```
       を追加。
     - `src/main.py` の `_on_open_part_dialog` で `PartSelectDialog(..., force_harmonica=self.user_settings.get("force_harmonica", True))` を渡し、`dlg.exec()` 確定時に `fh = dlg.chk_force_harmonica.isChecked()` を `self.user_settings["force_harmonica"] = fh` および `self.audio_engine.force_main_harmonica = fh`（さらに `self.chk_force_harmonica.setChecked(fh)`）へ同期反映する。
- **コミットメッセージ**: `feat(dialogs): declutter settings dialog, visualize project folder tree hierarchy, and move force-harmonica toggle to PartSelectDialog`

---

#### - [ ] **Micro-Step 4: 公式初期プリセット（5種）の再設計（課題21）と、`[⚙ 設定]` への「🎬 初期プリセット比較一覧表」タブ搭載（課題20）**
- **対象ファイル**: `src/settings_manager.py`, `src/dialogs.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/settings_manager.py` (`DEFAULT_VIDEO_PRESETS`, L59〜248付近)**:
     - 公式プリセットを以下の **5種** に刷新する（全プリセット共通で `"export_title_duration": 3.5`, `"export_title_exit_mode": "フェードアウトで消える"`, `"vertical_layout_mode": "全画面フル展開 (標準Shorts)"` も含める）：
       1. **`"📱 YouTube Shorts (縦型・解説)"`**: `aspect_ratio: "9:16"`, `trajectory_mode: "垂直落下 (穴直上)"`, `lang_mode: "ドレミ"`, `grid4_mode: "4音グリッド表示"`, `note_opacity: 100`, `bg_dim_ratio: 60`
       2. **`"🎥 演奏解説・レッスン (16:9)"`**: `aspect_ratio: "16:9"`, `trajectory_mode: "垂直落下 (穴直上)"`, `lang_mode: "ドレミ"`, `grid4_mode: "4音グリッド表示"`, `note_opacity: 100`, `bg_dim_ratio: 60`
       3. **`"🎨 演奏作品・MV (16:9・背景画像)"`** (★新設): `aspect_ratio: "16:9"`, `trajectory_mode: "3段階 (練習標準)"`, `lang_mode: "ドレミ"`, `show_lookahead: False`, `show_grid: False`, `show_bar_lines: False`, `show_hole_num: True`, `grid4_mode: "非表示"`, `note_opacity: 85`, `bg_image_enabled: True`, `bg_dim_ratio: 40`, `export_title_template: "イントロ中央＋右上常時"`
       4. **`"✨ ミニマル・シネマティック (16:9)"`**: `aspect_ratio: "16:9"`, `trajectory_mode: "2段階 (ビジュアル)"`, `show_lookahead: False`, `show_grid: False`, `show_bar_lines: False`, `show_hole_num: False`, `grid4_mode: "非表示"`, `note_opacity: 95`, `bg_dim_ratio: 60`, `export_title_template: "イントロ中央のみ"`
       5. **`"🟩 クロマキー透過素材 (外部編集用)"`**: `aspect_ratio: "16:9"`, `trajectory_mode: "垂直落下 (穴直上)"`, `export_style: "クロマキー素材 (背景・タイトルなし)"`, `export_bg_color: "グリーンバック"`, `export_title_template: "なし"`, `audio_quick_mode: "無音 (映像のみ)"`
  2. **`src/dialogs.py` (`HarmonicaSettingsDialog`, L220付近)**:
     - ダイアログサイズを `self.resize(720, 540)` に拡大し、**タブ4「🎬 初期プリセット一覧」** を追加する：
       - `self.table_presets = QTableWidget(5, 7, self)` を配置（列ヘッダー: `["初期プリセット名", "画面比率", "ノーツ軌道", "音名表記", "穴下表示", "ノーツ不透明度", "背景減光"]`）。
       - `settings_manager.DEFAULT_VIDEO_PRESETS`（および `self.settings.get("video_presets", {})` 内の該当プリセット）から5行を表示し、軌道・音名・穴下・不透明度・背景減光を一覧比較・直接編集可能にする。
       - 下部に `[↺ 公式初期プリセットを工場出荷時の設定に一括復元]` ボタン（`btn_restore_factory_presets`）を配置し、クリックすると `self.settings["video_presets"].update(copy.deepcopy(settings_manager.DEFAULT_VIDEO_PRESETS))` でいつでも初期状態に戻せるようにする。
- **コミットメッセージ**: `feat(presets): redesign 5 official video presets including 16:9 background MV and add preset comparison table tab in settings`

---

### 📦 Batch Package 3: サイドバー「2階層タブ化（🎹 練習 vs 🎬 動画制作）」＆「折りたたみアコーディオン（CollapsibleSection）」導入（Micro-Step 5 〜 6）

#### - [ ] **Micro-Step 5: サイドバーの「🎹 練習」vs「🎬 動画制作」2階層タブ化、プリセット操作バーの一元化、削除ボタン動的切替、右下保存ボタン撤去（課題11, 12, 13）**
- **対象ファイル**: `src/main.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **2階層タブ構造への再構築 (`src/main.py`, L1035〜1065付近)**:
     - `self.tab_widget`（最上位タブ）を **「🎹 練習」(Tab 0)** と **「🎬 動画制作」(Tab 1)** の2タブ構成に刷新する：
       ```python
       self.tab_widget = QTabWidget(self.sidebar_frame)

       # Tab 0: 🎹 練習
       self._build_tab_practice()

       # Tab 1: 🎬 動画制作 (上部: プリセット共通ヘッダー ＋ 下部: 3つのサブタブ)
       self.tab_video_production = QWidget(self)
       v_prod_layout = QVBoxLayout(self.tab_video_production)
       v_prod_layout.setContentsMargins(4, 6, 4, 4)
       v_prod_layout.setSpacing(6)

       # --- 動画制作 共通プリセットヘッダー (1箇所に完全一元化) ---
       self.f_video_preset_master = QFrame(self)
       self.f_video_preset_master.setObjectName("groupFrame")
       self.f_video_preset_master.setStyleSheet("QFrame#groupFrame { border: 1px solid #38BDF8; background-color: #0F172A; }")
       l_vpm = QVBoxLayout(self.f_video_preset_master)
       l_vpm.setContentsMargins(6, 6, 6, 6)
       l_vpm.setSpacing(4)

       r_vpm_top = QHBoxLayout()
       r_vpm_top.addWidget(QLabel("🎬 <b>プリセット:</b>"))
       self.combo_video_preset = QComboBox(self)
       self.combo_video_preset.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
       self._configure_sidebar_combo(self.combo_video_preset, max_width=230)
       self.combo_video_preset.currentTextChanged.connect(self._on_video_preset_changed)
       r_vpm_top.addWidget(self.combo_video_preset, stretch=1)
       l_vpm.addLayout(r_vpm_top)

       r_vpm_btns = QHBoxLayout()
       self.btn_preset_save = QPushButton("💾 保存", self)
       self.btn_preset_save.setToolTip("現在の画面・音響・出力設定を選択中プリセットに上書き保存")
       self.btn_preset_save.clicked.connect(self._on_save_video_preset)
       r_vpm_btns.addWidget(self.btn_preset_save)

       self.btn_preset_save_as = QPushButton("➕ 別名保存...", self)
       self.btn_preset_save_as.setToolTip("現在の設定で新しい動画プリセットを作成")
       self.btn_preset_save_as.clicked.connect(self._on_save_as_video_preset)
       r_vpm_btns.addWidget(self.btn_preset_save_as)

       self.btn_preset_reset = QPushButton("↺ 初期化", self)
       self.btn_preset_reset.setToolTip("公式プリセットは初期値へ復元、自作プリセットは削除します")
       self.btn_preset_reset.clicked.connect(self._on_reset_or_delete_video_preset)
       r_vpm_btns.addWidget(self.btn_preset_reset)
       l_vpm.addLayout(r_vpm_btns)

       self.btn_copy_practice_visual = QPushButton("📥 現在の「練習画面」の見た目を反映 (コピー)", self)
       self.btn_copy_practice_visual.setFixedHeight(24)
       self.btn_copy_practice_visual.setToolTip("普段の練習画面の軌道・音名・配色・スキン設定をこの動画プリセットに一括コピーします")
       self.btn_copy_practice_visual.clicked.connect(self._on_copy_practice_to_video_preset)
       l_vpm.addWidget(self.btn_copy_practice_visual)

       v_prod_layout.addWidget(self.f_video_preset_master)

       # --- 第2階層サブタブ (🎨 画面デザイン / 🎙️ 録音・音響 / 🎬 動画書き出し) ---
       self.video_sub_tabs = QTabWidget(self.tab_video_production)
       self._build_tab_design()
       self._build_tab_audio()
       self._build_tab_export()
       self.video_sub_tabs.currentChanged.connect(self._on_video_sub_tab_changed)
       v_prod_layout.addWidget(self.video_sub_tabs, stretch=1)

       self.tab_widget.addTab(self.tab_video_production, "🎬 動画制作")
       self.tab_widget.currentChanged.connect(self._on_tab_changed)
       ```
     - `_build_tab_design`, `_build_tab_audio`, `_build_tab_export` の末尾にある `self.tab_widget.addTab(tab, ...)` を **`self.video_sub_tabs.addTab(tab, ...)`**（ラベルは `"🎨 画面"`, `"🎙️ 録音・伴奏"`, `"🎬 動画出力"`）に変更する。
     - `_build_tab_design` 内の旧 `f_target` と `_build_tab_export` 内の旧 `f_preset`（重複していたプリセット枠）は `setVisible(False)` にし、マスターヘッダーの `self.combo_video_preset` に完全一本化する。
  2. **サイドバー最下部の `[💾 設定を保存]` (`btn_save_all`) の撤去**:
     - `sb_foot` から `btn_save_all` を削除（または `setVisible(False)`）し、`self.lbl_fps` と自動保存インジケーター `QLabel("✓ 設定自動保存", self)` のみにする。
  3. **タブ切替連動 (`_on_tab_changed`, `_on_video_sub_tab_changed`)**:
     - `self.tab_widget.currentIndex() == 0`（`🎹 練習`）のときは常に `_visual_edit_target = "practice"` で `practice_visual`（16:9）を表示。
     - `self.tab_widget.currentIndex() == 1`（`🎬 動画制作`）のときは、サブタブが `0`（画面）または `2`（動画出力）なら `_visual_edit_target = "video"` で選択中の動画プリセットをキャンバスに表示、サブタブが `1`（録音・伴奏）なら録音・練習しやすいよう `practice_visual`（または現在プリセット）を表示。
- **コミットメッセージ**: `feat(ui-hierarchy): implement 2-tier tab architecture (Practice vs Video Production) with unified preset header and dynamic delete button`

---

#### - [ ] **Micro-Step 6: 折りたたみアコーディオン（`CollapsibleSection`）の導入（課題17）と、「🎨 画面デザイン」内のセクション順序適正化（課題10）**
- **対象ファイル**: `src/main.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`CollapsibleSection` クラスおよびラッパーヘルパーの追加 (`src/main.py` 先頭クラス群付近)**:
     ```python
     class CollapsibleSection(QFrame):
         """タイトル行クリックで中身を1行に最小化・展開できるアコーディオンフレーム"""
         def __init__(self, title: str, content_frame: QWidget, expanded: bool = True, parent=None):
             super().__init__(parent)
             self.setObjectName("groupFrame")
             self.setMaximumWidth(328)
             self._title = title
             self._content = content_frame
             self._expanded = expanded

             layout = QVBoxLayout(self)
             layout.setContentsMargins(4, 4, 4, 4)
             layout.setSpacing(4)

             self.btn_toggle = QPushButton(self)
             self.btn_toggle.setCheckable(True)
             self.btn_toggle.setChecked(expanded)
             self.btn_toggle.setFlat(True)
             self.btn_toggle.setStyleSheet("""
                 QPushButton {
                     text-align: left;
                     font-weight: bold;
                     color: #E2E8F0;
                     background-color: #1E293B;
                     border: 1px solid #334155;
                     border-radius: 4px;
                     padding: 4px 8px;
                 }
                 QPushButton:hover {
                     background-color: #334155;
                     color: #38BDF8;
                 }
             """)
             self.btn_toggle.toggled.connect(self._on_toggled)
             layout.addWidget(self.btn_toggle)

             # 内部フレームの二重枠線を消してスッキリ収容
             self._content.setStyleSheet("QFrame#groupFrame { border: none; background: transparent; }")
             layout.addWidget(self._content)
             self._on_toggled(expanded)

         def _on_toggled(self, checked: bool):
             self._expanded = checked
             arrow = "▼" if checked else "▶"
             self.btn_toggle.setText(f"{arrow}  {self._title}")
             self._content.setVisible(checked)
     ```
  2. **「🎨 画面デザイン」タブ内のセクション順序入れ替え（課題10）**:
     - `_build_tab_design` 内で `v_box.addWidget(...)` する順序を以下のように変更する（各フレームを `CollapsibleSection` で包んで追加）：
       1. **`📐 画面比率 (構図プレビュー連動)`** (`self.f_ratio`, `expanded=True`) ← **最上部に配置！**
       2. **`🎵 演奏・ノーツ表示`** (`f_disp`, `expanded=True`)
       3. **`🎨 カラーテーマ ＆ ノーツ装飾`** (`f_col`, `expanded=True`)
       4. **`☑️ 表示要素 ON/OFF ＆ 穴番号`** (`f_opt`, `expanded=False`)
       5. **`🖼️ 背景画像 ＆ 減光 (コントラスト)`** (`f_bg`, `expanded=False`)
       6. **`🎷 ハーモニカ本体スキン`** (`f_skin`, `expanded=False`)
  3. **「🎹 練習」タブの各セクションも `CollapsibleSection` 化**:
     - モデル選択（`expanded=True`）、運指パターン＆重なり音（`expanded=True`）、落下速度（`expanded=True`）、ステップアップ練習（`expanded=False`）、練習時の再生音源（`expanded=False`）、練習画面の表示スタイル（`expanded=False`）としてラップし、スクロールなしで全項目を一望できるようにする！
- **コミットメッセージ**: `feat(ui-accordion): add CollapsibleSection for one-line folding across sidebar panels and reorder design tab sections`

---

### 📦 Batch Package 4: 録音・動画出力タブのスリム化 ＆ タイトル表示時間（0.1s〜）・フェード演出の刷新（Micro-Step 7 〜 8）

#### - [ ] **Micro-Step 7: 録音タブの不要音量枠撤去（課題14後半）、動画出力タブの二重リバーブ撤去（課題15）、およびタイトル・フェードUIの再配置（課題16, 18前半）**
- **対象ファイル**: `src/main.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **「🎙️ 録音・伴奏」タブの不要音量枠撤去 (`_build_tab_audio`, L1826〜1872付近)**:
     - `f_vol`（「🔊 音量制御 ＆ パート音色」）を `f_vol.setVisible(False)` にし、`v_box` の先頭からマイク録音（`f_rec`）、外部伴奏（`f_ext`）、リバーブ（`f_rev`）が表示されるようにする（各枠にも `CollapsibleSection` を適用）。
  2. **「🎬 動画出力」タブの二重リバーブ撤去 (`_build_tab_export`, L2415付近)**:
     - `self.chk_exp_reverb` を `self.chk_exp_reverb.setVisible(False)` にし、画面から撤去する。
  3. **フェードイン／アウト行（`r_fade`）を「前余白／後余白」のすぐ直下へ移動 (`_build_tab_export`, L2300〜2540付近)**:
     - `f_tit`（タイトル枠）内にあった `r_fade`（`chk_fade_in`, `spin_fade_in`, `chk_fade_out`, `spin_fade_out`）を切り出し、`f_fmt`（「1. 出力動画のフォーマット ＆ 範囲」）内の `r_margin`（前余白・後余白）の直下に `l_fmt.addLayout(r_fade)` で配置する。
  4. **タイトル設定のチェックボックス廃止と表示時間（0.1s〜15.0s）・消え方UIの新設 (`_build_tab_export`, L2450〜2552付近)**:
     - `self.chk_exp_title` を `setVisible(False)` にし、`self.lbl_title_tpl.setText("表示・配置:")` に変更。
     - `self.combo_title_template.currentTextChanged` で `"なし"` が選ばれたら `txt_exp_title` 等をグレーアウトし、`"なし"` 以外なら有効化する。
     - タイトル枠（`l_tit`）内に以下の **「表示時間（0.1s〜15.0s）＆ 消え方」行** を追加：
       ```python
       r_tdur = QHBoxLayout()
       r_tdur.addWidget(QLabel("表示時間:"))
       self.spin_title_dur = QDoubleSpinBox(self)
       self.spin_title_dur.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
       self.spin_title_dur.setRange(0.1, 15.0)
       self.spin_title_dur.setSingleStep(0.1)
       self.spin_title_dur.setDecimals(1)
       self.spin_title_dur.setSuffix("s")
       self.spin_title_dur.setFixedWidth(54)
       self.spin_title_dur.setAlignment(Qt.AlignmentFlag.AlignCenter)
       self.spin_title_dur.setValue(float(self.user_settings.get("export_title_duration", 3.5)))
       self.spin_title_dur.setToolTip("イントロ中央タイトルの表示維持秒数 (0.1〜15.0秒、0.1秒刻み)")
       self.spin_title_dur.valueChanged.connect(lambda _: self._save_current_settings())
       r_tdur.addWidget(self.spin_title_dur)

       r_tdur.addWidget(QLabel("消え方:"))
       self.combo_title_exit = QComboBox(self)
       self.combo_title_exit.addItems(["フェードアウトで消える", "即座に非表示 (カット)"])
       self.combo_title_exit.setCurrentText(str(self.user_settings.get("export_title_exit_mode", "フェードアウトで消える")))
       self.combo_title_exit.setToolTip("表示時間経過後のタイトルの消え方（滑らかに消える / パッと一瞬で消える）")
       self._configure_sidebar_combo(self.combo_title_exit, max_width=150)
       self.combo_title_exit.currentTextChanged.connect(lambda _: self._save_current_settings())
       r_tdur.addWidget(self.combo_title_exit, stretch=1)
       l_tit.addLayout(r_tdur)
       ```
     - `_on_video_preset_changed`, `_on_save_video_preset`, `_save_current_settings` で `"export_title_duration"` と `"export_title_exit_mode"` を保存・復元するように接続する。
- **コミットメッセージ**: `feat(export-ui): remove redundant volume/reverb widgets, relocate fade controls under margins, and add 0.1s title duration UI`

---

#### - [ ] **Micro-Step 8: `video_exporter.py` のタイトル独立表示時間（0.1s〜15.0s）＆ 消え方（フェード/カット）レンダリング実装（課題18後半）**
- **対象ファイル**: `src/studio_controller.py`, `src/video_exporter.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/studio_controller.py` (`_build_export_render_settings`, L530〜610付近)**:
     - `reverb_enabled` は `self.chk_reverb.isChecked()`（録音タブのリバーブ設定）を参照するように変更。
     - `title_overlay` 辞書の構築を更新：
       ```python
       tpl_str = self.combo_title_template.currentText() if hasattr(self, "combo_title_template") else "なし"
       title_enabled = (tpl_str != "なし")
       title_dur = float(self.spin_title_dur.value()) if hasattr(self, "spin_title_dur") else 3.5
       title_exit = self.combo_title_exit.currentText() if hasattr(self, "combo_title_exit") else "フェードアウトで消える"
       title_overlay = {
           "enabled": title_enabled,
           "template": tpl_str,
           "title": self.txt_exp_title.text() if hasattr(self, "txt_exp_title") else "",
           "credit": self.txt_exp_credit.text() if hasattr(self, "txt_exp_credit") else "",
           "intro_dur": title_dur,
           "exit_mode": title_exit,
       }
       ```
  2. **`src/video_exporter.py` (`_draw_title_overlay`, L889〜930付近)**:
     - 前余白（`intro_sec`）に強制束縛されていた古いロジックを撤廃し、`intro_dur`（0.1s〜15.0s）と `exit_mode`（フェードアウト / カット）に完全対応させる：
       ```python
       t_ref = t_in_video if t_in_video > 0.0 else max(0.0, cur_sec)
       configured_intro = max(0.1, float(overlay_info.get("intro_dur", 3.5)))
       exit_mode = str(overlay_info.get("exit_mode", "フェードアウトで消える"))
       fade_in_sec = float(overlay_info.get("fade_in_sec", 0.0))
       fade_title_mode = str(overlay_info.get("fade_title_mode", "フェード中もタイトル表示"))

       # 「フェード中はタイトル非表示」の場合はフェードイン完了時点から configured_intro 秒間表示する
       start_offset = fade_in_sec if fade_title_mode == "フェード中はタイトル非表示" else 0.0
       local_t = t_ref - start_offset
       effective_intro_dur = configured_intro

       show_intro = ("イントロ中央" in tpl and 0.0 <= local_t < effective_intro_dur)
       show_left = ("左上常時" in tpl)
       show_right = ("右上常時" in tpl)

       if show_intro:
           fade_in_time = min(0.4, effective_intro_dur * 0.25)
           if "カット" in exit_mode or "即座" in exit_mode:
               fade_out_time = 0.0
           else:
               fade_out_time = min(0.8, effective_intro_dur * 0.35)

           fade = 1.0
           if fade_in_time > 0.01 and local_t < fade_in_time:
               fade = max(0.1, local_t / fade_in_time)
           elif fade_out_time > 0.01 and local_t > (effective_intro_dur - fade_out_time):
               fade = max(0.0, (effective_intro_dur - local_t) / fade_out_time)
       ```
       （※ `render_frame_bytes` 内で `title_overlay["fade_title_mode"] = fade_title_mode` をセットして `_draw_title_overlay` に渡すこと）。
- **コミットメッセージ**: `feat(video-renderer): decouple title duration from intro margin and support 0.1s-15.0s timing with fade or cut exit`

---

### 📦 Batch Package 5: YouTube Shorts 上下2分割レイアウト ＆ 起動スプラッシュ・多重起動防止・全体結合テスト（Micro-Step 9 〜 10）

#### - [ ] **Micro-Step 9: YouTube Shorts (9:16) 上下2分割（スプリットスクリーン）構図配置の実装（課題8）**
- **対象ファイル**: `src/main.py`, `src/gl_visualizer.py`, `src/video_exporter.py`, `src/studio_controller.py`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/main.py` (`_build_tab_design` の `f_ratio` 内, L1510〜1530付近)**:
     - `self.ratio_combo` のすぐ下に **`縦型配置 (9:16時):` (`self.combo_vertical_layout`)** を追加：
       ```python
       r_vlay = QHBoxLayout()
       r_vlay.addWidget(QLabel("縦型配置:"))
       self.combo_vertical_layout = QComboBox(self)
       self.combo_vertical_layout.addItems([
           "全画面フル展開 (標準Shorts)",
           "上半分 16:9 ハーモニカ (下半分フリー)",
           "下半分 16:9 ハーモニカ (上半分フリー)",
           "中央 16:9 ハーモニカ"
       ])
       self._configure_sidebar_combo(self.combo_vertical_layout, max_width=220)
       self.combo_vertical_layout.setToolTip("9:16 縦型動画において、16:9比率のハーモニカ画面を上半分または下半分に配置し、残りの領域に別の動画やPVを合成しやすくします")
       self.combo_vertical_layout.currentTextChanged.connect(self._on_vertical_layout_changed)
       r_vlay.addWidget(self.combo_vertical_layout, stretch=1)
       l_ratio.addLayout(r_vlay)
       ```
     - `_on_vertical_layout_changed(self, text: str)` ハンドラを追加し、`self.gl_widget.set_vertical_layout_mode(text)` と設定保存を呼ぶ。また `_apply_visual_dict_to_ui_and_gl` および `_get_current_visual_dict_from_ui`、`_build_export_render_settings` にも `"vertical_layout_mode"` を接続する。
  2. **`src/gl_visualizer.py` & `src/video_exporter.py` のビューポート分割対応**:
     - 両クラスに `self.vertical_layout_mode = "全画面フル展開 (標準Shorts)"` と `set_vertical_layout_mode(self, mode: str)` を追加。
     - 描画時のキャンバス矩形計算（`gl_visualizer.py` の `paintGL` 内の `dest_rect` / `y_offset` / `disp_h`、および `video_exporter.py` の `render_frame_bytes` 内の `h` / `y_offset`）において：
       - アスペクト比が `"9:16"` かつ `self.vertical_layout_mode` に `"16:9"` が含まれる場合：
         - ハーモニカ描画バンドの高さ `band_h = int(effective_w * 9.0 / 16.0)` を算出。
         - `"上半分"` ならバンド上端 `band_y0 = base_y0 + int(full_h * 0.04)`
         - `"下半分"` ならバンド上端 `band_y0 = base_y0 + full_h - band_h - int(full_h * 0.04)`
         - `"中央"` ならバンド上端 `band_y0 = base_y0 + (full_h - band_h) // 2`
         - ノーツ落下開始Y〜ハーモニカ口金Yの座標系をこの `[band_y0, band_y0 + band_h]` 内にマッピング（クリッピング）して描画する！
- **コミットメッセージ**: `feat(shorts-layout): implement 9:16 vertical split-screen placement modes (top, bottom, center 16:9 viewport)`

---

#### - [ ] **Micro-Step 10: 起動時スプラッシュ画面（`QSplashScreen`）、多重起動防止ロック（課題19）および Ver.4.1.0 全体自動結合テスト (`tests/verify_v410_polish.py`)**
- **対象ファイル**: `src/main.py`, `tests/verify_v410_polish.py` (新規作成), `.context/00_handover.md`, `.context/01_architecture.md`, `.context/02_tasks.md`
- **詳細実装仕様（コードスニペット付き）**:
  1. **`src/main.py` のスプラッシュスクリーン ＆ 多重起動防止ロック (L4875 `main()` 関数)**:
     - ファイル先頭の `PyQt6.QtWidgets` インポートに `QSplashScreen`、`PyQt6.QtCore` インポートに `QSharedMemory` を追加。
     - ウィンドウタイトル（L655付近）を **`"Harmonica Visualizer v4.1.0 [Harmonica Studio Edition]"`** に更新。
     - `create_startup_splash() -> QSplashScreen` ヘルパー関数と `main()` 内の多重起動ロックを実装：
       ```python
       def create_startup_splash() -> QSplashScreen:
           pix = QPixmap(500, 260)
           pix.fill(QColor("#0F172A"))
           p = QPainter(pix)
           p.setRenderHint(QPainter.RenderHint.Antialiasing)
           p.setPen(QPen(QColor("#38BDF8"), 2))
           p.drawRoundedRect(1, 1, 498, 258, 10, 10)
           p.setPen(QColor("#38BDF8"))
           p.setFont(QFont("Meiryo UI", 18, QFont.Weight.Bold))
           p.drawText(QRectF(0, 55, 500, 45), Qt.AlignmentFlag.AlignCenter, "Harmonica Visualizer v4.1.0")
           p.setPen(QColor("#94A3B8"))
           p.setFont(QFont("Meiryo UI", 11, QFont.Weight.Bold))
           p.drawText(QRectF(0, 100, 500, 30), Qt.AlignmentFlag.AlignCenter, "[ Harmonica Studio Edition ]")
           p.setPen(QColor("#E2E8F0"))
           p.setFont(QFont("Meiryo UI", 10))
           p.drawText(QRectF(0, 175, 500, 30), Qt.AlignmentFlag.AlignCenter, "🚀 起動準備中... OpenGL ＆ オーディオエンジンを初期化しています")
           p.end()
           splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
           return splash

       def main():
           app = QApplication(sys.argv)
           app.setStyle("Fusion")

           # 多重起動防止ロック (オフスクリーンテスト時は除外)
           shared_mem = None
           if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
               shared_mem = QSharedMemory("HarmonicaVisualizerStudio_SingleInstance_v4")
               if not shared_mem.create(1):
                   QMessageBox.information(None, "起動中", "Harmonica Visualizer は既に起動しています。\nしばらくお待ちいただくか、タスクバーをご確認ください。")
                   sys.exit(0)

           splash = create_startup_splash()
           splash.show()
           app.processEvents()

           window = HarmonicaMainWindow()
           window._single_instance_lock = shared_mem
           window.show()
           splash.finish(window)
           sys.exit(app.exec())
       ```
  2. **全体自動検証スクリプト `tests/verify_v410_polish.py` の作成と実行**:
     - 全10ステップ（全21課題）の動作をオフスクリーンで自動テストし、すべて `PASS` すること、および `git status --porcelain src/` で未追跡のゴミファイルが生成されていないことを確認する。
  3. `.context/00_handover.md`, `.context/01_architecture.md`, `.context/02_tasks.md` を完了状態に更新してコミットし、Gitタグ **`v4.1.0`** を付与する。
- **コミットメッセージ**: `feat(release): add startup splash screen, single-instance guard, and complete v4.1.0 verification suite`

---

## 完了 (Done)
- [x] **【v4.0.0】Harmonica Studio（楽曲プロジェクト自己完結化・キー別運指パターン・タブ抜本再編・モジュール分割）** (2026-10-25) (`8f22c84`)
- [x] **【v3.2.0】UI/UX摩擦ゼロ化（音名直交化・上部タイトル伸縮復元・プリセット直結・練習音源切替・録音テイク選択＆同期試聴）** (2026-10-25) (`751f48b`)
- [x] **【v3.1.0】練習環境と動画出力プリセットの分離・UI/UX抜本改修** (2026-10-25) (`9832fb3`)
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
  1. **タイトルの「表示維持時間（秒）」スピンボックス新設（超短尺対応）**:
     - `タイトル表示時間:`（例: デフォルト 3.5秒、**範囲 0.1秒〜15.0秒、0.1秒刻み**）
     - ショート動画等での「フェードインして一瞬でパッと消えるスタイリッシュなカット演出」にも対応できるよう、最小値を 0.1秒 まで極小化可能にする。
     - 動画の前余白とは完全に独立して、クリエイターが意図した秒数だけタイトルを画面に維持できるようにする。
  2. **タイトルの「消え方」オプション**:
     - `消え方:`（`フェードアウトで消える (推奨)` / `即座に消える (カット)`）
     - フェードアウト時は、設定した表示時間の最後の0.8秒ほどをかけて文字とカード背景が滑らかに透明（alpha=0）になってフェードアウト消去し、美しい余韻を残す。
  3. **UI配置（課題16のタイトル欄へ集約）**:
     - タイトル欄内に `表示・配置` ➔ `表示時間 (秒)` ➔ `消え方 (フェード/カット)` を並べ、完璧なタイトル演出コントロールを実現する。

### 課題 19: 【起動UX＆パフォーマンス】スプラッシュスクリーン（起動準備中画面）の導入とEXE軽量化・高速起動・多重起動防止
- **ユーザー体験・課題意識**:
  1. **起動ラグと多重起動事故**:
     - EXE化した際、ダブルクリックしてからメインウィンドウが表示されるまでに数秒のラグがある。
     - そのため「あれ？起動したかな？」と不安になり、ユーザーが何度もアイコンをダブルクリックして複数アプリが立ち上がってしまう。
     - 重量級の本格ソフト（Photoshop, Premiere, 各種DAW等）のように、クリック直後に「起動中...」を示すスプラッシュ画面が欲しい。
  2. **EXEサイズ（約60MB）と解凍速度の軽量化**:
     - PyInstaller の単一ファイル形式（`--onefile`）は、毎回裏でテンポラリフォルダに巨大なランタイム（PyQt6, NumPy, OpenGL等）を展開してから起動するため、ディスクI/Oによる起動遅延が発生する。
- **技術的解決策（PyQt6 ＆ ビルド最適化）**:
  1. **`QSplashScreen` による起動中画面の即時表示**:
     - `QApplication` インスタンス化の直後（最速の数ミリ秒以内）に、アプリロゴ・バージョン・「Harmonica Studio 準備中...」を表示するスプラッシュ画面を画面中央にポップアップ。
     - メインウィンドウ（OpenGLやオーディオ）の初期化が完了した瞬間に `splash.finish(main_window)` でシームレスにメイン画面へ切り替える。
  2. **多重起動ガード（Single Instance Lock）**:
     - `QSharedMemory` またはプロセスミューテックスを用い、すでにアプリが起動中の場合は連打クリックを無視し、既存ウィンドウを最前面にフォーカスする安全機構を配備。
  3. **PyInstaller ビルドの高速化・軽量化**:
     - **未使用Qtモジュールの徹底除外**: PyQt6に含まれる `QtPdf`, `QtQml`, `QtQuick`, `QtNetwork`, `QtSql` 等の不要バイナリを `--exclude-module` で排除し、サイズを大幅削減。
     - **フォルダ形式（`--onedir`）配布の検討**: 解凍ラグをゼロ（起動が0.5秒以下の爆速）にするフォルダ形式のZIP配布パッケージングを整備。

### 課題 20: 【新機能企画】[⚙ 設定] ウィンドウへの「公式動画プリセット一覧・マトリクス比較表」の搭載
- **ユーザー要望・利用シーン**:
  - 打ち合わせ時に提示された「初期プリセットのパラメータ一覧表（Shorts、横動画、透過、MV等の比率・解像度・ノーツ・色・ミキサー比率の比較表）」が、各プリセットの狙いやパラメータ差異を理解する上で非常に参考になる。
  - 右上の `[⚙ 設定]` ウィンドウ内で、この公式初期プリセットの一覧表（罫線グリッドテーブル）をいつでも確認・参照できるようにしたい。
  - 自分で動画デザインを作る際のお手本・リファレンスシートとして機能し、必要に応じて表上で数値を俯瞰・微調整できるようにする。
- **UI・機能設計案**:
  1. **[⚙ 設定] ダイアログへの一覧テーブルタブ（またはセクション）の追加**:
     - `QTableWidget` による見やすいマトリクス比較表を配置。
     - **横軸（列）**: プリセット名（Shorts縦型、演奏解説16:9、グリーンバック、シネマティックMV）
     - **縦軸（行）**:
       - 📐 画面比率（9:16 / 16:9）
       - 🖥️ 解像度 ＆ FPS（1080x1920 60fps / 1920x1080 60fps）
       - 🎵 ノーツ軌道（3段階 / 垂直落下）
       - 🔤 音名表記 ＆ 穴下ノート（ドレミ＋4音グリッド / 英語＋1音 / 非表示）
       - 🎨 カラーテーマ ＆ 不透明度
       - 🎛️ 音声ミキサー推奨比率（主旋律%, 伴奏%, 録音テイク%, リバーブ%）
  2. **お手本リファレンス ＆ ワンクリック適用**:
     - ユーザーが自作プリセットを作る際、「公式はどういう設定値になっているか」を即座にカンニング・参照できる。
     - 「この公式プリセットの設定を読み込む」ボタンや初期値復元ボタンを併設し、学習・制作のサポートツールとして機能させる。

### 課題 21: 【設計打ち合わせ】公式初期プリセットのラインナップ再設計（王道16:9背景差し込みの追加・解説時の垂直落下化）
- **ユーザー指摘・問題意識**:
  1. **一番王道の「16:9 演奏動画 (背景画像差し込み)」の欠落**:
     - YouTubeやSNSで最も一般的な「背景に好きなイラストや写真、ジャケ写を敷き、手前にノーツとハーモニカを重ねて演奏を聴かせる動画」のプリセットが存在していない。
     - 背景減光（ディミング）やノーツの程よい透過度（例: 80%〜90%）が最初からセットされた、画像を選ぶだけですぐ作品になるプリセットが必須。
  2. **演奏解説動画は「垂直落下 (穴直上)」が最適**:
     - 現在の公式「演奏解説」は軌道が「3段階」になっているが、教材・解説としては「穴の真上に真っ直ぐ落ちてくる垂直落下」の方が「何番の穴を吹くべきか」が一目瞭然で圧倒的に分かりやすい。
- **初期プリセット（`DEFAULT_VIDEO_PRESETS`）の再構成案（検討用マトリクス）**:
  1. **`📱 YouTube Shorts (縦型・解説)`**:
     - 比率: 9:16 / 軌道: 垂直落下または3段階 / 音名・グリッド: ドレミ＋4音グリッド / テンポの良いShorts用
  2. **`🎥 演奏解説・チュートリアル (16:9)`**:
     - 比率: 16:9 / 軌道: **垂直落下 (穴直上)** / 音名: ドレミ / 穴下: 4音グリッド / 運指が一番学びやすい教材仕様
  3. **`🎨 演奏作品・MV (16:9・背景画像対応)` (★新設)**:
     - 比率: 16:9 / 軌道: 3段階 / 背景減光: 40% / ノーツ透過度: 85% / 余計な文字を抑え、背景画像を美しく引き立てる作品仕様
  4. **`✨ ミニマル・シネマティック (16:9)`**:
     - 比率: 16:9 / 軌道: 2段階または垂直 / 音名・グリッド: なし / シンプルで洗練された映像美仕様
  5. **`🟩 クロマキー・透過素材 (外部編集用)`**:
     - 比率: 16:9 / 背景: グリーンバック / PremiereやDaVinciで実写演奏と合成するための配信用素材仕様


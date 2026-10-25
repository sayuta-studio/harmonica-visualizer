# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 18:36 (本日の作業終了・全マイルストーンおよび次期 Ver.4.1.0 完全実装仕様書・上流ルール同期完了)

---

## 1. プロジェクト現在地と最新ステータス

- **現行リリースバージョン**: **`v4.0.0`**（Gitタグ `v4.0.0` 付与済み、全8項目自動結合テスト完全 PASS）
- **次期マイルストーン**: **`v4.1.0`「Harmonica Studio UI/UX Polish & Workflow Perfection」**
  - 実機動作確認フィードバックに基づく **全21課題の徹底分析・統合解消計画が策定完了**。
  - 上位モデル（Architect）から下位モデル（Builder）への引き継ぎ精度を極大化するため、**正確な行番号・関数名・コピペ適用可能な完全なPythonコードスニペット** を全10 Micro-Stepに完備した詳細実装仕様書が `.context/02_tasks.md` に配備済み。
- **リポジトリ状態**: `master` ブランチ、`working tree clean`（未コミット差分ゼロ）
- **上流テンプレート連携**: `_shared_knowledge/`（Gotcha #10）および `.agent/rules/safety_limits.md`（Rule #7）が上流マスターテンプレート（`00_template`）と 100% 整合・同期完了。

```text
harmonica-visualizer/
├── .agent/                    # AIエージェント行動規範・セーフティルール
│   └── rules/                 # safety_limits.md (★Rule #7: 仕様書コードスニペット義務化 追記済)
├── .context/                  # プロジェクト管理コンテキスト（最優先参照）
│   ├── 00_handover.md         # 本ファイル（現在地スナップショット・引き継ぎ情報）
│   ├── 01_architecture.md     # システム概要・技術スタック・設計制約
│   ├── 02_tasks.md            # 🌟 Ver.4.1.0 詳細実装仕様書（Micro-Step 1〜10 完全コード案付）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── _docs/                     # アイデア・ログ・外部資料
├── _shared_knowledge/         # 再利用可能な汎用知見集（★Gotcha #10 追記済）
├── src/                       # 🌟【現行稼働コード】メインコードベース（v4.0.0 安定稼働中）
│   ├── main.py                # メインウィンドウ、サイドバー構築、タブ連動 (4,892行)
│   ├── studio_controller.py   # StudioExportMixin（録音・伴奏同期・ミキサー・動画出力設定）
│   ├── project_manager.py     # SongProjectManager（1曲1フォルダ、ハッシュ衝突検知、相対パス解決）
│   ├── config.py              # ポータブル基底パス解決（開発時リポジトリルート、配布時exe直下）
│   ├── audio_engine.py        # WinMM MIDI再生、AudioRecorder、PCM音声スライス再生、WAV合成、リバーブDSP
│   ├── video_exporter.py      # OffscreenVisualizerRenderer、FFmpegパイプライン、動画書き出し
│   ├── gl_visualizer.py       # HarmonicaGLWidget（OpenGLノーツバー描画、ハーモニカ本体、穴発光アニメーション）
│   ├── midi_timeline.py       # MidiTimeline（Tick-秒変換、小節マップ、トラック分離、移調計算、音域診断）
│   ├── harmonica_map.py       # 12/14/16穴運指定義、キー別運指パターン保存、曲別プロファイル管理
│   ├── dialogs.py             # モーダルダイアログ群（HarmonicaSettingsDialog [⚙ 設定], PartSelectDialog 等）
│   ├── ipc_state.py           # SharedClockBridge（共有メモリスレッドクロック、再生状態管理）
│   └── settings_manager.py    # practice_visual と video_presets の永続化管理
├── projects/                  # 楽曲プロジェクト自己完結コンテナ
│   └── <曲名>/                # source/ (原本MIDI), takes/ (WAV), audio/ (外部伴奏), exports/ (動画), project.json
└── tests/                     # オフスクリーン単体・統合テスト群
    └── verify_v400_studio.py  # v4.0.0 自動統合検証スクリプト
```

---

## 2. 本日完了した作業・実績サマリー

### ① Ver.4.0.0「Harmonica Studio」アーキテクチャ刷新の完遂
- **楽曲プロジェクト自己完結化 (`SongProjectManager`)**:
  - `projects/<曲名>/` 配下に `source/`, `takes/`, `audio/`, `exports/`, `project.json` を相対パス集約。
  - SHA-256 ハッシュによる同名別曲MIDI衝突検知（自動連番分離）、フォルダ名リネーム自動追従。
- **キー別運指パターンの統合保存**:
  - 運指カスタムに移調値（`transpose`, `transpose_accomp`）をセット保存。練習タブからワンクリック切替・別キー作成ロック解除を実装。
- **UI直交分離 ＆ システム環境設定ウィンドウ新設**:
  - 練習スタイルを練習タブ下部に集約し、動画画面タブを100%動画プリセット専用化。
  - 上部ヘッダー右端に `[⚙ 設定]` ボタンを配置し、環境設定ダイアログを接続。
- **`StudioExportMixin` 分離 ＆ 全自動統合テスト PASS**:
  - `src/main.py` から録音・動画制御ロジック（約850行）を安全に分離。
  - `tests/verify_v400_studio.py`（全8項目自動テスト）が完全 PASS、Gitタグ `v4.0.0` を付与。

### ② 実機テストに基づくフィードバック・課題の徹底分析（全21課題の体系化）
- ユーザー様の実機操作に基づき、コード修正を行わず徹底的な原因究明と分析を実施：
  - プリセット比率の逆上書き破壊バグ（課題9）の根本原因特定と自己修復ガード設計。
  - カスタムスキンが練習画面に即時反映されないデータ二重化問題（課題4）の解決方針確立。
  - 過去の打ち合わせ記録（v3.1.0設計書）との照合による「練習スタイルコピーボタン」「自作プリセット削除UI」の実装漏れ回収（課題11, 12）。
  - 動画プリセットの階層逆転を解消する **「🎹 練習 vs 🎬 動画制作」2階層タブ化**（課題13）の設計。
  - サイドバー全セクションを1行最小化できる **折りたたみアコーディオン（`CollapsibleSection`）** によるスクロール不要・ワンビュー俯瞰の確立（課題17）。
  - 録音タブ・動画出力タブの重複・不要コントロール撤去（課題14, 15）。
  - タイトルカード表示時間（`0.1s 〜 15.0s`、0.1秒刻み）およびフェード/カット消去の独立パラメータ化（課題16, 18）。
  - 公式初期プリセットの5大ラインナップ再設計（王道16:9背景画像MV新設・解説の垂直落下化）および `[⚙ 設定]` へのマトリクス比較表タブ搭載（課題20, 21）。
  - 起動直後のスプラッシュ画面（`QSplashScreen`）＆多重起動防止ロック設計（課題19）。
  - YouTube Shorts (9:16) 上下2分割スプリットスクリーン構想（課題8）。

### ③ 知見のナレッジ化（Gotcha #10）とプロジェクトルールの公式化（Rule #7）
- 上位モデル（Architect）が実装指示書を策定する際、表題・要約のみで済ませると下位モデル（Builder）がコードを推測して破綻する落とし穴を **Gotcha #10** として知見化。
- 各ステップに「正確な行番号・関数名」「具体的Pythonコードスニペット」「コミットメッセージ」を完備することを **`.agent/rules/safety_limits.md`（Rule #7）** に公式ルール化。上流テンプレート（`00_template`）との双方向同期を完了。

---

## 3. 次期 Ver.4.1.0 実装ロードマップ（全5パッケージ / 10 Micro-Steps）

すべての詳細実装仕様、修正行番号、完成コードスニペットは **`.context/02_tasks.md`** に記載されています。

| パッケージ | ステップ | 対象ファイル | 主な実装内容 | 状態 |
| :--- | :--- | :--- | :--- | :---: |
| **Package 1** | **Step 1** | `settings_manager.py`<br>`main.py`<br>`project_manager.py` | プリセット切替時 `ratio_combo` 自動同期＆Shorts比率自己修復、カスタムスキンの練習画面即時反映、フォールバック保存先の `projects/_demo_chromatic` 集約 | **完了 (e413ed4)** |
| | **Step 2** | `gl_visualizer.py`<br>`harmonica_map.py`<br>`main.py` | モノクロ時の変え指マーク二重コントラスト枠線、`Key +12` パターン名＆ステータスバー移調表記の重複解消 | **完了 (cdda8ef)** |
| **Package 2** | **Step 3** | `dialogs.py`<br>`main.py` | `[⚙ 設定]` の重複項目（メトロノーム・ステップアップ）撤去、プロジェクト親子階層ツリー図解表示、`[🎼 パート]` への主旋律音色固定移設 | **完了 (64d2327)** |
| | **Step 4** | `settings_manager.py`<br>`dialogs.py` | 公式5大プリセット再設計（王道16:9背景MV追加・解説垂直落下）＆ `[⚙ 設定]` への「🎬 初期プリセット比較一覧表」タブ追加 | **完了 (878eef6)** |
| **Package 3** | **Step 5** | `main.py` | サイドバーの「🎹 練習 vs 🎬 動画制作」2階層タブ化、プリセットヘッダー一元化、「📥 練習からコピー」ボタン、自作プリセット「🗑️ 削除」動的切替、右下保存ボタン撤去 | **次回最初に着手** |
| | **Step 6** | `main.py` | 全セクションを1行最小化できる `CollapsibleSection` 導入、画面デザインタブの順序改善（比率を最上部に配置） | 未着手 |
| **Package 4** | **Step 7** | `main.py` | 録音タブの不要音量枠撤去、動画出力タブの二重リバーブ撤去、フェードの余白直下配置、タイトル表示時間（`0.1s〜15.0s`）＆消え方UI新設 | 未着手 |
| | **Step 8** | `studio_controller.py`<br>`video_exporter.py` | タイトル表示時間を前余白から独立させ、`0.1s〜15.0s` 維持＆フェード/カット消去レンダリング実装 | 未着手 |
| **Package 5** | **Step 9** | `main.py`<br>`gl_visualizer.py`<br>`video_exporter.py` | YouTube Shorts (9:16) 上下2分割レイアウト（上半分16:9 / 下半分16:9 / 中央16:9）の実装 | 未着手 |
| | **Step 10** | `main.py`<br>`tests/verify_v410_polish.py` | 起動直後の `QSplashScreen` ＆ `QSharedMemory` 多重起動防止ロック実装、全自動結合テスト実行・全PASS確認、タグ `v4.1.0` 付与 | 未着手 |

---

## 4. 次回作業再開時に最初に行うべきタスク

次回セッション開始時、AIエージェント（Gemini 3.8 Flash 等）に対して以下の指示を出すだけで、安全かつ確実に実装が再開されます：

> **「Package 1 から順番に Ver.4.1.0 の実装を進めてください」**

### 実行手順（AI側の動作）:
1. `.context/02_tasks.md` の **Batch Package 1（Micro-Step 1 〜 2）** の詳細コードスニペットと行番号を読み込む。
2. **Micro-Step 1** を実装し、構文チェック（`python -m py_compile`）後に `fix(core): sync aspect ratio combo on preset switch, propagate custom skins to practice visual, and route fallback takes to project container` で Git コミット。
3. **Micro-Step 2** を実装し、構文チェック後に `fix(ui-polish): add adaptive contrast outline for fingering edit mode and simplify transpose key labels` で Git コミット。
4. Package 1 の完了後、`.context/02_tasks.md` と `.context/00_handover.md` のチェックボックスを更新してコミットし、ユーザーへ報告して Package 2 への進行指示を仰ぐ。

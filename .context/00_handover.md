# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 15:37 (Ver.4.0.0 Batch Package 3 完遂: タブ抜本再編・練習スタイル統合・動画専用画面化・システム環境設定ダイアログ `[⚙ 設定]` 分離)

---

## 1. プロジェクト現在地と最新ディレクトリ構造

ビルトインタスク管理規則およびマスタールールに準拠し、Ver.4.0.0「Harmonica Studio」の Batch Package 1, 2, 3 の実装・単体テスト・コミットがすべて完了しました。

```text
harmonica-visualizer/
├── .agent/                    # AIエージェント行動規範・セーフティルール
│   └── rules/                 # knowledge_classifier.md, safety_limits.md
├── .context/                  # プロジェクト管理コンテキスト（最優先参照）
│   ├── 00_handover.md         # 本ファイル（現在地スナップショット・引き継ぎ情報）
│   ├── 01_architecture.md     # システム概要・技術スタック・設計制約・v4.0.0設計図
│   ├── 02_tasks.md            # タスク管理（完了・進行中・未着手）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── _docs/                     # アイデア・ログ・外部資料（旧 docs）
│   ├── ideas/
│   ├── logs/
│   └── sources/               # extracted_knowledge.md, ai_development_playbook.md 等
├── _shared_knowledge/         # 再利用可能な汎用知見集（旧 shared_knowledge）
│   ├── architecture_patterns.md  # Gotcha #7 (Architect-Builder), #8 (2層タスク粒度), #9 (基底パス規約)
│   ├── env_build.md
│   ├── ui_ux.md
│   └── inbox/
├── src/                       # 🌟【現行稼働コード】メインコードベース
│   ├── main.py                # メインウィンドウ、L型レイアウト、ヘッダー [⚙ 設定] ボタン、タブ切替連動
│   ├── audio_engine.py        # WinMM MIDI再生、AudioRecorder、PCM音声スライス再生、WAV合成、リバーブDSP
│   ├── video_exporter.py      # OffscreenVisualizerRenderer、FFmpegパイプライン、動画書き出し
│   ├── gl_visualizer.py       # HarmonicaGLWidget（OpenGLノーツバー描画、ハーモニカ本体、穴発光アニメーション）
│   ├── midi_timeline.py       # MidiTimeline（Tick-秒変換、小節マップ、トラック分離、移調計算、音域診断）
│   ├── harmonica_map.py       # 12/14/16穴運指定義、変え指、has_custom_fingering、曲別プロファイル管理
│   ├── dialogs.py             # モーダルダイアログ群（HarmonicaSettingsDialog [⚙ 設定], PartSelectDialog, FingeringEditorDialog 等）
│   ├── ipc_state.py           # SharedClockBridge（共有メモリスレッドクロック、再生状態管理）
│   ├── settings_manager.py    # practice_visual と video_presets (公式4種) の永続化管理
│   ├── project_manager.py     # 🌟 (New v4.0) SongProjectManager（1曲1フォルダ、ハッシュ衝突検知、相対パス解決）
│   ├── config.py              # 🌟 (Updated v4.0) ポータブル基底パス解決（開発時はリポジトリ直下、配布時はexe直下）
│   └── assets/                # アプリケーション内蔵アイコン・リソース
├── projects/                  # 🌟 (New v4.0) 楽曲プロジェクト自己完結コンテナ（開発時リポジトリ直下に配置）
│   └── <曲名>/                # source/ (原本MIDI), takes/ (WAV), audio/ (外部伴奏), exports/ (動画), project.json
├── recordings/                # レガシー録音フォルダ（旧テイク退避用）
└── tests/                     # オフスクリーン単体・統合テスト群
```

---

## 2. 直近の完了実績（Ver.4.0.0 Batch Package 1 〜 3）

1. **Batch Package 1: ポータブル基底パス刷新 ＆ `src/project_manager.py`（Micro-Step 1 〜 2）**
   - `src/config.py`: 開発環境実行時に `src/` 配下を汚さないリポジトリルート解決と `.gitignore` 遮断を確立 (`56ba68d`)。
   - `src/project_manager.py`: `SongProjectManager` を新設し、1曲＝1フォルダのコンテナ生成、SHA-256衝突検知、相対パス自動追従、旧 `fingering/` からのマイグレーションを実装 (`aa39003`)。
2. **Batch Package 2: キー別運指パターン統合 ＆ 練習タブ切替UI・別キー作成アンロック（Micro-Step 3 〜 4）**
   - `src/dialogs.py` (`FingeringEditorDialog`) & `src/harmonica_map.py`: 運指パターンに `transpose` / `transpose_accomp` をスナップショット保存 (`1d38423`)。
   - `src/main.py`: `🎹 練習` タブにキー別運指パターン切替コンボ（`combo_main_fg_pattern`）と、現在パターンを保護したまま別キー用を作成できる `[🔓 別キー用の運指を新規作成...]` ボタンを実装 (`1ce5f0a`)。
3. **Batch Package 3: タブ抜本再編 ＆ システム環境設定 `[⚙ 設定]` 分離（Micro-Step 5 〜 6）**
   - `src/main.py`: `🎨 画面作り` タブを100%動画プリセット専用化（`🎨 動画画面` へ名称変更）し、練習時の視覚スタイル設定（軌道・音名・穴下グリッド・テーマ等）を `🎹 練習` タブ下部の「5. 🎨 練習画面の表示スタイル」フレームに集約・双方向連動 (`6176667`)。
   - `src/dialogs.py` & `src/main.py`: `HarmonicaSettingsDialog` をシステム環境設定仕様（タブ1: `🔊 音響・録音デバイス`、タブ2: `🎨 本体スキン・練習支援`、タブ3: `📁 プロジェクト・保存先管理`）に全面刷新。メイン画面上部ヘッダー Row 1 右端に `[⚙ 設定]` ボタン（`btn_open_settings`）を配置し、設定保存時の即時反映を接続 (`ddfdbb4`)。

---

## 3. 次回着手すべきタスク（Ver.4.0.0 Batch Package 4: Micro-Step 7 〜 8）

残すタスクは Ver.4.0.0 の最終パッケージ（Batch Package 4）のみです：

- [ ] **Micro-Step 7: スタジオ・エクスポート制御の `src/studio_controller.py` 分離と、録音・動画出力先の `projects/<曲名>/` 完全直結**
  - **対象ファイル**: `src/studio_controller.py` (新規作成), `src/main.py`
  - **内容**: `src/main.py` から録音制御・外部伴奏同期・ミキサー呼び出し・動画レンダリング設定コード（約800行）を `StudioExportMixin`（`src/studio_controller.py`）へ分離。録音保存先と動画出力先を `projects/<曲名>/takes/` および `projects/<曲名>/exports/` に直結。
  - **コミットメッセージ**: `refactor(studio): extract StudioExportMixin to studio_controller.py and bind takes/exports to song project container`

- [ ] **Micro-Step 8: Ver.4.0.0 全体結合テスト (`tests/verify_v400_studio.py`) 実行・ドキュメント更新・Gitタグ `v4.0.0` 付与**
  - **対象ファイル**: `src/main.py`, `tests/verify_v400_studio.py` (新規作成), `.context/00_handover.md`, `.context/01_architecture.md`, `.context/02_tasks.md`
  - **内容**: アプリタイトルを `Harmonica Visualizer v4.0.0 [Harmonica Studio Edition]` に更新。全8項目オフスクリーン統合テストを作成・実行してパス確認後、全コンテキストを更新し、Gitタグ `v4.0.0` を付与。
  - **コミットメッセージ**: `docs(release): complete v4.0.0 Harmonica Studio architecture milestone and tag release`

---

## 4. 特記事項・注意事項
- **安全なモジュール分割**: `StudioExportMixin` は Python の多重継承 Mixin パターンを採用し、`self` 経由の Qt ウィジェット参照（`self.audio_engine`, `self.timeline`, `self.clock` 等）のシグネチャを一切壊さず安全に抽出すること。
- **Gitコミットの厳守**: Micro-Step 7 と Micro-Step 8 をそれぞれ独立してコミットし、動作確認を行ってから最終タグ付けを実施すること。

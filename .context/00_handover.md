# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 15:08 (Gemini 4.0 による Ver.4.0.0「Harmonica Studio」全8 Micro-Step 実装指示書策定完了)

---

## 1. プロジェクト現在地と最新ディレクトリ構造

マスターテンプレート（`00_template`）の規約に完全準拠し、フォルダ再編成、基盤改修、UI/UX摩擦解消が完了しています。

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
├── src/                       # 🌟【現行稼働コード】メインコードベース（v3.2.0 稼働中）
│   ├── main.py                # メインウィンドウ、L型レイアウト、プリセット直結バー、録音同期試聴、UI構築
│   ├── audio_engine.py        # WinMM MIDI再生、AudioRecorder、PCM音声スライス再生、WAV合成、リバーブDSP
│   ├── video_exporter.py      # OffscreenVisualizerRenderer、FFmpegパイプライン、動画書き出し
│   ├── gl_visualizer.py       # HarmonicaGLWidget（OpenGLノーツバー描画、ハーモニカ本体、穴発光アニメーション）
│   ├── midi_timeline.py       # MidiTimeline（Tick-秒変換、小節マップ、トラック分離、移調計算、音域診断）
│   ├── harmonica_map.py       # 12/14/16穴運指定義、変え指、has_custom_fingering、曲別プロファイル管理
│   ├── dialogs.py             # モーダルダイアログ群（総合設定、パート選択、変え指エディタ、音声ミキサー）
│   ├── ipc_state.py           # SharedClockBridge（共有メモリスレッドクロック、再生状態管理）
│   ├── settings_manager.py    # practice_visual と video_presets (公式4種) の永続化・自動マイグレーション
│   ├── config.py              # ポータブルパス解決（get_portable_path）、フォント・定数設定
│   ├── fingering/             # 曲別プロファイル（<曲名>_profile.json）保存領域
│   └── skins/                 # ハーモニカ本体外観スキン画像（メタル、ウッド、ゴールド等）
├── tests/                     # 🧪 リグレッション防止・自動検証テストスイート
│   └── verify_v320_features.py# v3.2.0 全機能オフスクリーン検証スクリプト (All 7 Tests Passed)
├── _archives/                 # 📦【過去資産アーカイブ】（自律参照・編集は厳禁）
├── releases/                  # 🚀【配布パッケージ領域】（大容量zip・Git除外）
│   ├── Chromatic_Harmonica_Trainer_Ver.1.01.zip
│   ├── Chromatic_Harmonica_Trainer_Ver.2.10.zip
│   └── Chromatic_Harmonica_Trainer_Ver.3.00.zip  # Ver.3.00ビルド（65.4MB・全改修内包）
├── AGENTS.md                  # AI開発者向けコアインストラクション
├── .gitignore                 # 統合除外設定（_archives/ や releases/ を除外）
├── sync_to_template.bat       # 共有知見を 00_template へ同期・還元するバッチ
└── update_from_template.bat   # 00_template から最新規約・知見を取り込むバッチ
```

---

## 2. これまでに達成した全機能・改修完了サマリー

### 【v3.2.0: UI/UX摩擦ゼロ化（Frictionless Studio Update）】 (2026-10-25 完遂)
1. **音名表記と穴下ノート表示の直交化 (Package 1: Micro-Step 1)**:
   - 表記言語 `lang_mode`（ドレミ / CDE）と穴下グリッド `grid4_mode`（4音グリッド / 1音 / 非表示）を完全分離。
   - `lang_mode` から「なし」を撤廃し、非表示時もノーツ直上音名トグルと干渉せず枠だけ残る描画バグを完全根絶。
2. **上部ヘッダー（Row 1）曲名ラベルの伸縮復元 (Package 1: Micro-Step 2)**:
   - `_load_midi_file` での幅制限（240px固定）を解除し、`Expanding` かつ最大幅 `16777215` でウィンドウ幅に応じて自然に伸縮。右側操作ボタンを綺麗に右詰め整列。
3. **`🎨 画面作り` タブへの動画プリセット直結バー配置 (Package 2: Micro-Step 3)**:
   - 動画プリセット編集時に、画面作りタブ内にプリセット選択・上書き保存・別名保存・初期化バーが即時出現。動画出力タブへ移動しなくてもワンクリックで保存・切替が完結。動画出力タブ側とも完全双方向同期。
4. **練習タブへの「🔊 練習時の再生音源」切替設置 (Package 2: Micro-Step 4)**:
   - 練習タブ末尾に伴奏切替フレームを追加。外部伴奏を読み込んだ状態でも「MIDIガイド音のみで練習」「伴奏と合わせて練習」「伴奏のみ」を練習タブからワンクリックで即座に切り替え可能に。
5. **`🎙️ 録音・音響` タブへの「📂 過去テイク選択」追加 (Package 3: Micro-Step 5)**:
   - 直前テイクだけでなく、過去の録音テイクや任意の外部WAVファイルを選択して採用可能に。即座に試聴＆動画エクスポートへ反映。
6. **録音ズレ補正の「▶ 伴奏と同期試聴」＆微調整ボタン実装 (Package 3: Micro-Step 6)**:
   - `[-10ms]`, `[+10ms]` の即時微調整ボタンを設置。
   - `Channel(2)` を用いた録音テイクPCMスライス同期再生機構を新設。タイムライン再生（外部伴奏/MIDI＋ノーツ落下）と同時に録音音声を鳴らしてズレをリアルタイム確認可能に。
7. **全体結合自動検証全PASS ＆ Gitタグ `v3.2.0` 付与 (Package 3: Micro-Step 7)**:
   - `tests/verify_v320_features.py` による全7項目のオフスクリーン自動テスト完全通過。

---

## 3. 次期大型マイルストーン: Ver.4.0.0「Harmonica Studio（楽曲プロジェクト自己完結化 ＆ タブ抜本再編）」

Gemini 4.0（Architect）により、実装担当（Gemini 3.8 / Builder）が1ステップずつ安全に実装・コミットできる **全8 Micro-Step（Batch Package 1 〜 4）の詳細実装指示書** を [`.context/02_tasks.md`](file:///c:/AI_Dev_Workspace/01_2026_10_00_harmonica-visualizer/.context/02_tasks.md) に完備しました。

### 🚀 実装パッケージ構成（Batch Package 1 〜 4）
1. **Batch Package 1（Micro-Step 1 〜 2）: ポータブル基底パス刷新 ＆ `src/project_manager.py` 新設**
   - **Step 1**: `src/config.py` の `get_portable_path` を刷新し、開発時（`.py` 実行）に動的データがすべてリポジトリルート直下に解決されるようにして `src/` 汚染を完全遮断（Gotcha #9 実装）。
   - **Step 2**: `src/project_manager.py` を新設。`projects/<曲名>/` コンテナ生成、SHA-256 ハッシュによる同名別MIDI衝突検知、相対パス変換によるフォルダリネーム追従、旧 `fingering/*.json` からの自動マイグレーションを実装。
2. **Batch Package 2（Micro-Step 3 〜 4）: キー（移調）別・用途別の運指パターン保存システム拡張**
   - **Step 3**: `FingeringEditorDialog` と `harmonica_map.py` の運指パターン（`patterns`）に移調値（`transpose`, `transpose_accomp`）を統合。
   - **Step 4**: メイン画面の `🎹 練習` タブに運指パターン切替コンボと新規保存ボタンを設置。さらに移調ロック時にワンクリックで現在パターンを保護しつつ別キー作成へ移行できる `[🔓 別キー用の運指を新規作成...]` ボタンを実装。
3. **Batch Package 3（Micro-Step 5 〜 6）: タブ抜本再編 ＆ 環境設定ウィンドウ `[⚙ 設定]` 分離**
   - **Step 5**: `🎨 画面作り` タブのターゲット切替コンボを撤廃し、100%動画プリセット編集専用タブ（`🎨 動画画面`）へ純化。練習画面のスタイル設定は `🎹 練習` タブ下部に統合。
   - **Step 6**: システム環境設定（MIDI音源エンジン、録音チャンネル、本体スキン選択、保存先フォルダ管理）を `HarmonicaSettingsDialog`（`[⚙ 設定]` ウィンドウ）に統合し、上部ヘッダー Row 1 右端の `[⚙ 設定]` ボタンから呼び出し可能に。
4. **Batch Package 4（Micro-Step 7 〜 8）: `src/studio_controller.py` 分離・プロジェクト直結 ＆ v4.0.0 リリース**
   - **Step 7**: `src/main.py` から録音・外部伴奏・ミキサー・動画エクスポート制御（約800行）を `StudioExportMixin`（`src/studio_controller.py`）へ安全に分離。同時に録音・動画保存先を `projects/<曲名>/takes/` および `exports/` に完全直結。
   - **Step 8**: オフスクリーン自動検証スクリプト（`tests/verify_v400_studio.py` 全8テスト）の実行・パス確認、ドキュメント更新、Gitタグ `v4.0.0` 付与。

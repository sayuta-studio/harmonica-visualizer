# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 14:25 (Gemini 4.0による Ver.3.2.0 摩擦解消 Micro-Step 指示書 ＆ Ver.4.0.0 プロジェクト自己完結化アーキテクチャ設計完了)

---

## 1. プロジェクト現在地と最新ディレクトリ構造

マスターテンプレート（`00_template`）の規約に完全準拠し、フォルダ再編成およびクリーンアップが完了しています。

```text
harmonica-visualizer/
├── .agent/                    # AIエージェント行動規範・セーフティルール
│   └── rules/                 # knowledge_classifier.md, safety_limits.md
├── .context/                  # プロジェクト管理コンテキスト（最優先参照）
│   ├── 00_handover.md         # 本ファイル（現在地スナップショット・引き継ぎ情報）
│   ├── 01_architecture.md     # システム概要・技術スタック・設計制約
│   ├── 02_tasks.md            # タスク管理（完了・進行中・未着手）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── _docs/                     # アイデア・ログ・外部資料（旧 docs）
│   ├── ideas/
│   ├── logs/
│   └── sources/               # extracted_knowledge.md, ai_development_playbook.md 等
├── _shared_knowledge/         # 再利用可能な汎用知見集（旧 shared_knowledge）
│   ├── architecture_patterns.md  # Gotcha #7 (Architect-Builder), Gotcha #8 (2層タスク粒度) 追記済
│   ├── env_build.md
│   ├── ui_ux.md
│   └── inbox/
├── src/                       # 🌟【現行稼働コード】メインコードベース（v3.1.0 稼働中）
│   ├── main.py                # メインウィンドウ、L型レイアウト、動画プリセット管理、移調ロック、UI構築
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
├── _archives/                 # 📦【過去資産アーカイブ】（自律参照・編集は厳禁）
│   ├── v0_v1_notepad_prototypes/  # （旧bbbbb）メモ帳コピー時代の黎明期プロトタイプ
│   ├── v2.0/                  # VS Code / Antigravity 移行後の第1世代
│   └── v2.1/                  # VS Code / Antigravity 移行後の第2世代
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

### 【v3.1.0: 練習環境と動画出力プリセットの完全分離・UI/UX抜本改修】
1. **移調（トランスポーズ）× カスタム運指のロック制御**:
   - `harmonica_map.py` に `has_custom_fingering()` を実装。
   - 個別変え指が1件以上存在する場合、音名破綻を防ぐため移調コントロールを即時ロック（`🔒 原曲キー固定` ツールチップ表示）。
2. **練習設定と動画出力プリセットのデータ層完全分離**:
   - `settings_manager.py` に `practice_visual`（日常の作業机）と `video_presets`（用途別動画プリセット4種）スキーマを定義。
   - 既存の `user_settings.json` からの無損失マイグレーションを実装。
3. **動画出力レンダー設定（`render_settings`）の一元化**:
   - 重複していた出力パラメータ構築ロジックを `_build_export_render_settings` に一本化。
4. **`🎨 画面作り` タブの編集対象切り替え（練習用 vs 動画プリセット）**:
   - 編集ターゲットコンボボックスを最上部に新設。練習用編集時は16:9固定、動画プリセット編集時のみ比率切り替えを有効化。
   - タブ切り替え時にキャンバス（OpenGL）の表示内容と比率を自動同期。
5. **`🎬 動画出力` タブ最上部へのプリセットマネージャー＆ブリッジ実装**:
   - プリセット選択コンボ、保存、別名保存、初期化/削除ボタンを配置。
   - 「📋 現在の「練習画面」の見た目を反映」ワンクリックボタンで、練習画面のデザインを動画プリセットに即時コピー可能に。
   - 「🎨 このプリセットの画面デザインを編集...」ジャンプボタンを設置。
6. **全自動結合テスト合格＆Gitタグ `v3.1.0` 付与**:
   - オフスクリーンQtテストで全プリセット切替・コピーブリッジ・レンダラー構築の正常動作を完全確認。

### 【v3.0.0 までの基盤改修 (Step 1 〜 Step 8)】
- Step 1: 右サイドバー固定幅（340px）徹底・録音テイク2段化
- Step 2: 外部音源PCM直接スライス再生・安全シーク・独立リバーブ試聴
- Step 3: マイク録音の前奏（カウントイン）自動トリムと録音遅延補正
- Step 4: マルチトラック・オーディオミキサーダイアログの実装（3層ミキシング）
- Step 5: 縦型動画（9:16）および 4:3 動画の真の解像度・アスペクト比計算と黒帯排除
- Step 6: タイトルカード・クレジットの実幅相対スケーリング＆物理クリッピング
- Step 7: カスタムスキンの動画出力・プレビュー完全反映
- Step 8: フェードイン・前余白・タイトルの完全タイムライン同期

---

## 3. 次期マイルストーン計画: Ver.3.2.0（UI/UX摩擦ゼロ化）＆ Ver.4.0.0（Harmonica Studio 構想）

### 🎯 Phase 1: Ver.3.2.0「UI/UX 摩擦ゼロ化（Frictionless Studio Update）」
実機確認で判明した6つの操作摩擦を解消する全7マイクロステップ（Batch Package 1〜3）の実装指示書を [`.context/02_tasks.md`](file:///c:/AI_Dev_Workspace/01_2026_10_00_harmonica-visualizer/.context/02_tasks.md) に完備済みです。
- **Package 1 (Micro-Step 1〜2)**:
  - **Step 1**: 音名表記（`lang_mode`: ドレミ/CDE 2択化）と穴下ノート表示（`grid4_mode`: 4音/1音/非表示 3択化）の完全直交化。
  - **Step 2**: 上部パネル（Row 1）の曲名ボックス伸縮（`stretch=1`・幅制限解除）復元と右詰め整列。
- **Package 2 (Micro-Step 3〜4)**:
  - **Step 3**: `🎨 画面作り` タブへの「動画プリセット選択・保存バー」直結配置（タブ移動なしでプリセット切替・保存・別名保存が完結）。
  - **Step 4**: `🎵 練習` タブへの「🔊 練習時の再生音源切替（MIDIガイドのみ / 伴奏合わせ）」設置と双方向連動。
- **Package 3 (Micro-Step 5〜7)**:
  - **Step 5**: `🎙️ 録音・音響` タブへの「📂 過去テイク・録音WAV選択」ボタン追加。
  - **Step 6**: 録音ズレ補正の「▶ 伴奏と同期試聴（Channel 2 メモリPCMスライス同期再生）」および微調整ボタン追加。
  - **Step 7**: v3.2.0 全体結合テスト・ドキュメント更新・Gitタグ `v3.2.0` 付与。

### 🚀 Phase 2: Ver.4.0.0「Harmonica Studio（楽曲プロジェクト自己完結型アーキテクチャ）」
詳細青写真・JSONスキーマ・モジュール分割計画を [`.context/01_architecture.md`](file:///c:/AI_Dev_Workspace/01_2026_10_00_harmonica-visualizer/.context/01_architecture.md) 第5章に定義済みです。
1. **1楽曲 ＝ 1プロジェクトフォルダ（`projects/<曲名>/`）**: MIDI原本、設定・変え指（`project.json`）、録音テイク群（`takes/`）、伴奏（`audio/`）、完成動画（`exports/`）を完全自己完結管理。
2. **SHA-256 同名MIDI衝突検知 ＆ フォルダ名リネーム自動追従**。
3. **キー（移調）別・用途別の運指パターン保存システム**。
4. **`[⚙ 環境設定]` ウィンドウの分離と `src/main.py` の5モジュール分割**。

---

## 4. 設計・運用の絶対遵守ルール（Gotchas）

1. **実装コードの配置場所**:
   - 実装コードはすべて `src/` 配下に配置されています（旧 `v3.0/` は存在しません）。
2. **過去アーカイブ（`_archives/`）の不可侵**:
   - `_archives/` 配下のファイルは歴史的資産であり、明示的に指示された場合を除き**自律参照および編集・変更を厳禁**とします。
3. **存在しない外部実体の推測補完（捏造）の厳禁（Gotcha #6）**:
   - 外部ツールやバッチファイルが存在しない場合、勝手に想像して作成・補完せず、必ず停止してユーザーに確認してください。
4. **Windows PowerShell の `cp932` 文字コード対策**:
   - テストスクリプト実行時、標準出力に絵文字が含まれると `cp932` 例外が発生するため、スクリプト冒頭で `sys.stdout.reconfigure(encoding="utf-8")` を徹底してください。
5. **ポータブルパス解決（`_resolve_skin_file`）の維持**:
   - スキン画像や設定ファイルは、環境移行やフォルダ移動があっても自動探索で解決される堅牢な設計を維持してください。
6. **Windows バッチファイル（.bat）の改行コード・文字コード規約**:
   - `.bat` ファイルは必ず **Shift-JIS (CP932) + CRLF (`\r\n`)** で保存し、冒頭に `cd /d "%~dp0"` を付与すること（LF改行やUTF-8だとcmd.exeで構文エラー即落ちの原因となる）。
7. **AIモデル分業運用（Architect-Builder パターン / Gotcha #7）**:
   - 上位モデルで `.context/02_tasks.md` に詳細な Micro-Step 指示書を作成し、高速モデル（3.8等）ではその指示書に従い **1ステップずつ実装 ➔ 検証 ➔ Micro Commit** を厳守すること。

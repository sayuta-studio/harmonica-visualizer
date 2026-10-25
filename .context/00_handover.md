# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 18:10 (Ver.4.1.0 全21課題統合・実装仕様書［Batch Package 1〜5 / Micro-Step 1〜10］策定完了)

---

## 1. プロジェクト現在地と最新ディレクトリ構造

現在、Ver.4.0.0 リリース後の実機動作確認および過去の打ち合わせ照合によって洗い出された **全21課題（バグ解消、2階層タブ化、折りたたみアコーディオン、公式5大プリセット再設計、タイトル0.1s演出、Shorts上下分割、起動スプラッシュ等）** を解決するための **Ver.4.1.0 詳細実装仕様書** が `.context/02_tasks.md` に完成しています。

```text
harmonica-visualizer/
├── .agent/                    # AIエージェント行動規範・セーフティルール
│   └── rules/                 # knowledge_classifier.md, safety_limits.md
├── .context/                  # プロジェクト管理コンテキスト（最優先参照）
│   ├── 00_handover.md         # 本ファイル（現在地スナップショット・引き継ぎ情報）
│   ├── 01_architecture.md     # システム概要・技術スタック・設計制約
│   ├── 02_tasks.md            # 🌟 Ver.4.1.0 詳細実装仕様書（Micro-Step 1〜10 コードスニペット付）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── _docs/                     # アイデア・ログ・外部資料
├── _shared_knowledge/         # 再利用可能な汎用知見集（Gotcha #7, #8, #9）
├── src/                       # 🌟【現行稼働コード】メインコードベース
│   ├── main.py                # メインウィンドウ、サイドバー構築、タブ連動、スプラッシュ起動
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
│   └── settings_manager.py    # practice_visual と video_presets (公式5種) の永続化管理
├── projects/                  # 楽曲プロジェクト自己完結コンテナ
│   └── <曲名>/                # source/ (原本MIDI), takes/ (WAV), audio/ (外部伴奏), exports/ (動画), project.json
└── tests/                     # オフスクリーン単体・統合テスト群
    └── verify_v400_studio.py  # v4.0.0 自動統合検証スクリプト（次ステップで verify_v410_polish.py を追加）
```

---

## 2. Ver.4.1.0 実装ロードマップ（Batch Package 1 〜 5 / Micro-Step 1 〜 10）

すべての詳細仕様・対象ファイル・行番号・実装コードスニペットは **`.context/02_tasks.md`** に記載されています。

| パッケージ | ステップ | 解決課題 | 実装概要 | 状態 |
| :--- | :--- | :--- | :--- | :---: |
| **Package 1** | **Step 1** | 課題 3, 4, 9 | プリセット比率（`ratio_combo`）逆上書きバグ修正、カスタムスキンの練習画面即時反映、フォールバック保存先の `_demo_chromatic` 集約 | 未着手 |
| | **Step 2** | 課題 5, 6, 7 | モノクロ時の変え指二重コントラスト枠線、`Key +12` パターン名＆ステータスバー移調表記の重複解消 | 未着手 |
| **Package 2** | **Step 3** | 課題 1, 2, 3, 14 | `[⚙ 設定]` からの重複項目（メトロノーム・ステップアップ）撤去、プロジェクト親子階層ツリー図解、`[🎼 パート]` への主旋律音色固定移設 | 未着手 |
| | **Step 4** | 課題 20, 21 | 公式5大プリセット再設計（王道16:9背景画像MV追加・解説の垂直落下化）＆ `[⚙ 設定]` への「🎬 初期プリセット比較一覧表」タブ追加 | 未着手 |
| **Package 3** | **Step 5** | 課題 11, 12, 13 | サイドバーの「🎹 練習 vs 🎬 動画制作」2階層タブ化、プリセットヘッダー一元化、「📥 練習画面からコピー」ボタン、自作プリセット「🗑️ 削除」動的切替、右下保存ボタン撤去 | 未着手 |
| | **Step 6** | 課題 10, 17 | 全セクションをタイトル1行に最小化できる `CollapsibleSection`（折りたたみアコーディオン）導入 ＆ 画面デザインタブの順序適正化（比率を最上部へ） | 未着手 |
| **Package 4** | **Step 7** | 課題 14, 15, 16, 18 | 録音タブの不要音量枠撤去、動画出力タブの二重リバーブ撤去、フェードの余白直下への移動、タイトル表示時間（`0.1s〜15.0s`）＆消え方UI新設 | 未着手 |
| | **Step 8** | 課題 18 | `video_exporter.py` のタイトル表示時間を前余白から独立させ、`0.1s〜15.0s` 維持＆フェード/カット消去レンダリング実装 | 未着手 |
| **Package 5** | **Step 9** | 課題 8 | YouTube Shorts (9:16) 上下2分割レイアウト（上半分16:9 / 下半分16:9 / 中央16:9）の実装 | 未着手 |
| | **Step 10** | 課題 19 | 起動直後の `QSplashScreen`（起動準備中画面）＆ `QSharedMemory` 多重起動防止ロック実装、`tests/verify_v410_polish.py` 全項目PASS検証、タグ `v4.1.0` 付与 | 未着手 |

---

## 3. 次回アクション（Builder / Gemini 3.8 への引き継ぎ指示）
- `.context/02_tasks.md` の **Batch Package 1（Micro-Step 1 〜 2）** から順番に着手してください。
- **1 Micro-Step 完了ごとに必ず `python -m py_compile` で構文検証を行い、指定されたコミットメッセージで Git コミットを刻んでください**（複数ステップのまとめコミットは厳禁）。
- 1つの Batch Package（2ステップ）が完了するごとに `.context/00_handover.md` と `.context/02_tasks.md` のチェックボックスを更新してコミットし、ユーザーへ進行状況を報告してください。

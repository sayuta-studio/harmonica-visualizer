# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 15:52 (Ver.4.0.0 Harmonica Studio 全8 Micro-Step 完遂・全体自動統合テスト PASS・v4.0.0 リリース準備完了)

---

## 1. プロジェクト現在地と最新ディレクトリ構造

ビルトインタスク管理規則およびマスタールールに準拠し、**Ver.4.0.0「Harmonica Studio」の全8ステップ（Batch Package 1 〜 4）がすべて実装・結合テスト・コミットされ、完全リリース状態** に到達しました。

```text
harmonica-visualizer/
├── .agent/                    # AIエージェント行動規範・セーフティルール
│   └── rules/                 # knowledge_classifier.md, safety_limits.md
├── .context/                  # プロジェクト管理コンテキスト（最優先参照）
│   ├── 00_handover.md         # 本ファイル（現在地スナップショット・引き継ぎ情報）
│   ├── 01_architecture.md     # システム概要・技術スタック・設計制約・v4.0.0完成設計図
│   ├── 02_tasks.md            # タスク管理（全マイルストーン完遂状態）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── _docs/                     # アイデア・ログ・外部資料（旧 docs）
├── _shared_knowledge/         # 再利用可能な汎用知見集（Gotcha #7, #8, #9）
├── src/                       # 🌟【現行稼働コード】メインコードベース（v4.0.0 リリース）
│   ├── main.py                # メインウィンドウ、L型レイアウト、ヘッダー [⚙ 設定] ボタン、タブ切替連動 (4,888行)
│   ├── studio_controller.py   # 🌟 (New v4.0) StudioExportMixin（録音・伴奏同期・ミキサー・動画出力）
│   ├── project_manager.py     # 🌟 (New v4.0) SongProjectManager（1曲1フォルダ、ハッシュ衝突検知、相対パス解決）
│   ├── config.py              # 🌟 (Updated v4.0) ポータブル基底パス解決（開発時リポジトリルート、配布時exe直下）
│   ├── audio_engine.py        # WinMM MIDI再生、AudioRecorder、PCM音声スライス再生、WAV合成、リバーブDSP
│   ├── video_exporter.py      # OffscreenVisualizerRenderer、FFmpegパイプライン、動画書き出し
│   ├── gl_visualizer.py       # HarmonicaGLWidget（OpenGLノーツバー描画、ハーモニカ本体、穴発光アニメーション）
│   ├── midi_timeline.py       # MidiTimeline（Tick-秒変換、小節マップ、トラック分離、移調計算、音域診断）
│   ├── harmonica_map.py       # 12/14/16穴運指定義、キー別運指パターン保存、曲別プロファイル管理
│   ├── dialogs.py             # モーダルダイアログ群（HarmonicaSettingsDialog [⚙ 設定], PartSelectDialog 等）
│   ├── ipc_state.py           # SharedClockBridge（共有メモリスレッドクロック、再生状態管理）
│   └── settings_manager.py    # practice_visual と video_presets (公式4種) の永続化管理
├── projects/                  # 🌟 (New v4.0) 楽曲プロジェクト自己完結コンテナ
│   └── <曲名>/                # source/ (原本MIDI), takes/ (WAV), audio/ (外部伴奏), exports/ (動画), project.json
└── tests/                     # オフスクリーン単体・統合テスト群
    └── verify_v400_studio.py  # 🌟 (New v4.0) 全8項目オフスクリーン自動統合検証スクリプト
```

---


### 🛠️ 直近の修正（Ver.4.0.0 安定化パッチ）
1. **[⚙ 設定] ダイアログ保存時の強制終了（クラッシュ）の解消**:
   - src/main.py の _on_open_env_settings_dialog において、存在しない関数 settings_manager.save_user_settings を呼び出していたため AttributeError でアプリが落ちていた問題を特定し、正しく settings_manager.save_settings を呼ぶように修正。
2. **カスタムスキン設定の完全直交化（動画版 SkinSelectDialog との統合）**:
   - HarmonicaSettingsDialog の外観スキン設定ボタンから、動画画面タブと同じ **SkinSelectDialog**（マウスピース、レバーOFF、レバーON、リアルタイム合成プレビュー）を開けるように接続。
   - 設定保存時にメイン画面の _apply_user_settings で gl_widget.set_custom_skins(...) を実行し、練習画面のハーモニカにも即時反映されるように改修。

## 2. Ver.4.0.0 全マイルストーン完了実績一覧

| パッケージ | ステップ | コミット | 主な成果 |
| :--- | :--- | :--- | :--- |
| **Package 1** | Step 1 | `56ba68d` | `src/config.py`: 開発環境実行時に `src/` 配下を汚さないリポジトリルート解決と `.gitignore` 遮断を確立（Gotcha #9） |
| | Step 2 | `aa39003` | `src/project_manager.py`: 1曲＝1フォルダのコンテナ生成、SHA-256衝突検知、相対パス自動追従、旧プロファイルマイグレーション |
| **Package 2** | Step 3 | `1d38423` | `src/dialogs.py` & `src/harmonica_map.py`: 運指パターンに `transpose` / `transpose_accomp` をスナップショット統合保存 |
| | Step 4 | `1ce5f0a` | `src/main.py`: `🎹 練習` タブにキー別運指パターン切替コンボと、別キー作成アンロックボタンを実装 |
| **Package 3** | Step 5 | `6176667` | `src/main.py`: `🎨 動画画面` タブを100%動画プリセット専用化し、練習時の視覚スタイル設定を `🎹 練習` タブ下部に集約 |
| | Step 6 | `ddfdbb4` | `src/dialogs.py` & `src/main.py`: システム環境設定ダイアログ（`[⚙ 設定]`）の3タブ刷新とメイン画面上部ヘッダー分離 |
| **Package 4** | Step 7 | `0c09126` | `src/studio_controller.py`: `StudioExportMixin` へ録音・動画エクスポート制御（約850行）を分離し、プロジェクトフォルダへ完全直結 |
| | Step 8 | （本コミット） | `tests/verify_v400_studio.py`（全8項目自動テスト）パス確認、タイトル更新、Gitタグ `v4.0.0` 付与 |

---

## 3. 全体自動統合テスト（`tests/verify_v400_studio.py`）検証結果
- **TEST 1**: ポータブル基底パス解決（開発時リポジトリルート解決・`src/` 汚染ゼロ） -> **PASS**
- **TEST 2 & 3**: 楽曲プロジェクト自己完結コンテナ生成 ＆ SHA-256 ハッシュ同名別曲衝突検知・自動分離 -> **PASS**
- **TEST 4**: プロジェクトフォルダ名リネーム時の相対パス解決追従 -> **PASS**
- **TEST 5**: キー（移調）別運指パターン切替 ＆ 別キー作成アンロック動作 -> **PASS**
- **TEST 6**: 練習タブ下部スタイル設定と 100%動画専用画面タブの完全直交分離 -> **PASS**
- **TEST 7**: ヘッダー `[⚙ 設定]` ボタンと `HarmonicaSettingsDialog`（3タブ構成）の初期化・設定反映 -> **PASS**
- **TEST 8**: `StudioExportMixin` 分離後の録音・動画設定構築動作確認 ＆ `src/main.py` 行数削減（4,888行 < 5,000行） -> **PASS**

---

## 4. 次回アクション（課題ストック・トリアージと修正フェーズ準備）
- ユーザーによる実機動作確認フィードバックおよび過去の打ち合わせ記録（v3.1.0/v3.2.0/v4.0.0）を全件精査・照合しました。
- 打ち合わせで合意済みだった「実装漏れ」2件を含む全17課題（折りたたみアコーディオン化構想、タイトル簡素化、二重リバーブ撤去、2階層タブ化構想を含む）を `.context/02_tasks.md` に分析・記録完了しています。
- **指示があるまで修正コードの改変は行わず、ユーザーからの着手指示および優先度決定を待ちます**。

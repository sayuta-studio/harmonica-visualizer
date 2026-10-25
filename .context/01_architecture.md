# プロジェクト基本設計・アーキテクチャ (01_architecture.md)

## 1. システム概要
- **名称**: クロマチックハーモニカ・ビジュアライザー / スタジオ (Harmonica Visualizer v4.1.0 [Harmonica Studio Edition])
- **主目的**:
  - クロマチックハーモニカ（12穴48音・14穴56音・16穴64音）演奏者のための練習支援、リアルタイム運指提示、伴奏再生、マイク録音、残響（リバーブ）付与、および YouTube/Shorts/TikTok/高精細横動画の作品級動画書き出し（ProRes 4444 / H.264 MP4）。
- **主要アーキテクチャ（Ver.4.0.0 刷新）**:
  - **楽曲プロジェクト自己完結コンテナ (`SongProjectManager`)**:
    - 1曲＝1フォルダ（`projects/<曲名>/`）で原本MIDI・テイクWAV・外部伴奏・完成動画・`project.json` を相対パス管理。フォルダ名変更にも自動追従。
    - SHA-256 ハッシュによる同名別曲の衝突検知・自動分離コンテナ生成。
  - **スタジオ制御 Mixin (`StudioExportMixin`)**:
    - `src/main.py` から録音制御・外部伴奏同期・ミキサー・動画レンダリング設定（約850行）を分離し、循環依存ゼロで保守性を極大化。
  - **キー（移調）別運指パターン・プロファイル管理**:
    - 移調値（`transpose` / `transpose_accomp`）と変え指スナップショットを統合保存。練習タブからワンタッチ切替および別キー作成ロック解除が可能。
  - **システム環境設定ダイアログ (`HarmonicaSettingsDialog`)**:
    - 音響・録音デバイス、本体外観スキン・練習支援、ポータブルデータ管理の3タブ構成。上部ヘッダー `[⚙ 設定]` ボタンから即座にアクセス・双方向同期。
  - **練習スタイルと動画プリセットの完全直交分離 ＆ 2階層タブ構成 (v4.1.0)**:
    - 第1階層（`🎹 練習` vs `🎬 動画制作`）の直感的なワークフロー直交分離。
    - 動画制作タブ内を「🎨 画面デザイン」「🎙️ 録音・伴奏」「🎬 動画出力」の3サブタブに整理し、上部に「🎬 プリセットヘッダー」を一元配置。
    - サイドバー全セクションに1行最小化アコーディオン（`CollapsibleSection`）を導入。
  - **YouTube Shorts (9:16) 上下2分割レイアウト (v4.1.0)**:
    - 9:16縦長動画において、16:9比率のハーモニカ演奏画面を「上半分」「下半分」「中央」に配置可能なスプリットスクリーン構図対応。
  - **タイトル独立表示時間 (0.1s〜15.0s) ＆ フェード/カット消去 (v4.1.0)**:
    - タイトルカードの表示秒数を前余白から完全独立化し、0.1秒単位で柔軟に設定可能。
  - **起動スプラッシュ (`QSplashScreen`) ＆ 多重起動防止 (`QSharedMemory`) (v4.1.0)**:
    - 起動時の視覚フィードバックと、プロセスの多重起動防止ガードを完備。

---

## 2. 技術スタック
- **言語 / ランタイム**: Python 3.14.5 (64-bit Windows)
- **GUI フレームワーク**: PyQt6 (6.8.1)
- **グラフィックス / 描画**: PyOpenGL (3.1.9) + QOpenGLWidget (オフスクリーンFBO / シェーダー描画)
- **オーディオ再生・録音**: pygame-ce (2.5.7) [SDL 2.32.10, SDL_mixer, SDL_audio / NumPy PCM direct slicing]
- **MIDI 再生・解析**: WinMM API (ctypes 直接呼出) ＋ mido (1.3.3)
- **音響信号処理 (DSP)**: NumPy (2.2.3) [畳み込み残響演算・ITU-R BS.1770 ラウドネス解析・ソフトリミッター]
- **動画エンコード**: FFmpeg (外部パイプライン / ProRes 4444 透過MOV / H.264 MP4, 48kHz AAC/PCM)
- **パッケージング / 配布**: PyInstaller (6.11.1)

---

## 3. ディレクトリ構造と主要モジュールの責務

```text
harmonica-visualizer/
├── .agent/                    # AIエージェント行動規範・セーフティルール
│   └── rules/                 # knowledge_classifier.md, safety_limits.md
├── .context/                  # プロジェクト管理コンテキスト
│   ├── 00_handover.md         # 現在地スナップショット・引き継ぎ情報
│   ├── 01_architecture.md     # 本ファイル（基本設計・技術スタック）
│   ├── 02_tasks.md            # タスク管理（完了・進行・未着手）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── _docs/                     # アイデア・ログ・外部資料
├── _shared_knowledge/         # 再利用可能な汎用知見集（Gotcha #7, #8, #9）
├── src/                       # 🌟【現行稼働コード】
│   ├── main.py                # メインウィンドウ、L型レイアウト、ヘッダー [⚙ 設定] ボタン、タブ切替連動
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
└── tests/                     # オフスクリーン単体・統合テスト群（verify_v400_studio.py, verify_v410_polish.py）
```

---

## 4. 設計制約・コーディング規約（Ver.4.0 準拠）
1. **基底パス解決規約（Gotcha #9）**:
   - 動的データ（プロジェクト、録音テイク、設定ファイル）のパス解決は必ず `config.get_portable_path()` を経由すること。開発時（`.py` 実行）はリポジトリ直下、配布時（`.exe` 実行）は実行バイナリ直下を基準とし、`src/` 配下を絶対に汚さない。
2. **モジュール分割規約（Mixin パターン）**:
   - `HarmonicaMainWindow` の肥大化を防ぐため、スタジオ録音・伴奏・動画エクスポート関連は `StudioExportMixin`（`src/studio_controller.py`）に集約する。ウィジェットへの参照は多重継承経由で安全に行う。
3. **楽曲プロジェクト自己完結規約**:
   - 1曲に関わる原本MIDI・録音テイク・外部伴奏・動画出力先・設定（`project.json`）はすべて `projects/<曲名>/` 内で相対パス完結させ、フォルダ名変更やPC間移動に対して高い耐性を持たせる。

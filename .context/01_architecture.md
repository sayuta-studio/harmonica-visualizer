# プロジェクト基本設計・アーキテクチャ (01_architecture.md)

## 1. システム概要
- **名称**: クロマチックハーモニカ・ビジュアライザー＆トレーナー (v3.0)
- **目的**: 
  - クロマチックハーモニカ（12穴48音・14穴56音・16穴64音）奏者のための練習支援、リアルタイム運指可視化、外部伴奏音源同期再生、マイクワンクリック録音、空間残響（リバーブ）付与、およびYouTube/Shorts/TikTok/透過合成向けの高品位動画書き出し（ProRes 4444 / H.264 MP4）。
- **主要アーキテクチャ特徴**:
  - **PyQt6 + OpenGL 64-bit Core**: GPUアクセラレーションによる60fps常時同期のノーツフォール・ハーモニカ本体アニメーション。
  - **多重クロック完全同期**: WinMM MIDI再生クロック、メモリPCM直接スライスオーディオエンジン、OpenGL描画ループ、動画レンダラーの単一基準時間同期。
  - **3階層運指解決システム**: 個別オーバーライド（Layer 1） ＞ 全体プリセット（Layer 2） ＞ 物理楽器テーブル（Layer 3）による異名同音（変え指）柔軟解決。
  - **3層マルチトラック・オーディオミキサー**: 外部伴奏 ＋ マイク録音 ＋ MIDIガイド伴奏の自由加算合成、ITU-R BS.1770規格ラウドネス解析（目標 `-14.0 LUFS`）、True Peak（`-1.0 dBFS`）リミッター。

---

## 2. 技術スタック
- **言語 / ランタイム**: Python 3.14.5 (64-bit Windows)
- **GUI フレームワーク**: PyQt6 (6.8.1)
- **グラフィックス / 描画**: PyOpenGL (3.1.9) + QOpenGLWidget (オフスクリーンFBO / シェーダー描画)
- **オーディオ再生・録音**: pygame-ce (2.5.7) [SDL 2.32.10, SDL_mixer, SDL_audio / NumPy PCM direct slicing]
- **MIDI 再生・解析**: WinMM API (ctypes 直接呼出) ＋ mido (1.3.3)
- **音響信号処理 (DSP)**: NumPy (2.2.3) [畳み込み残響演算・ITU-R BS.1770 ラウドネス解析・ソフトニーリミッター]
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
│   ├── 02_tasks.md            # タスク管理（完了・進行中・未着手）
│   └── 03_troubleshooting.md  # プロジェクト固有トラブルシューティング
├── docs/                      # アイデア・ログ・外部資料格納
│   ├── ideas/
│   ├── logs/
│   └── sources/               # extracted_knowledge.md, ai_development_playbook.md 等
├── shared_knowledge/          # 再利用可能な汎用知見集（8割の汎用知見）
│   ├── architecture_patterns.md
│   ├── env_build.md
│   ├── ui_ux.md
│   └── inbox/
├── 00_template/               # マスターテンプレート（複製元・還元用）
├── v3.0/                      # 🌟【現行稼働バージョン (v3.0)】メインコードベース（トップ常駐）
│   ├── main.py                # メインウィンドウ、L型レイアウト統括、イベント制御、UI構築
│   ├── audio_engine.py        # WinMM MIDI再生、AudioRecorder、PCM音声スライス再生、WAV合成、リバーブDSP
│   ├── video_exporter.py      # OffscreenVisualizerRenderer、FFmpegパイプライン、動画書き出し
│   ├── gl_visualizer.py       # HarmonicaGLWidget（OpenGLノーツバー描画、ハーモニカ本体、穴発光アニメーション）
│   ├── midi_timeline.py       # MidiTimeline（Tick-秒変換、小節マップ、トラック分離、移調計算、音域診断）
│   ├── harmonica_map.py       # 12/14/16穴運指定義、変え指、単音化フィルター、曲別プロファイル（JSON）管理
│   ├── dialogs.py             # モーダルダイアログ群（総合設定、パート選択、変え指エディタ、音声ミキサー）
│   ├── ipc_state.py           # SharedClockBridge（共有メモリスレッドクロック、再生状態管理）
│   ├── settings_manager.py    # グローバル設定（user_settings.json）永続化
│   ├── config.py              # ポータブルパス解決（get_portable_path）、フォント・定数設定
│   ├── fingering/             # 曲別プロファイル（<曲名>_profile.json）保存領域
│   └── skins/                 # ハーモニカ本体外観スキン画像
├── archives/                  # 📦【過去資産アーカイブ】
│   ├── v0_v1_notepad_prototypes/  # （旧bbbbb）メモ帳コピー時代の黎明期プロトタイプ（Ver 0.001〜1.01）
│   ├── v2.0/                  # VS Code / Antigravity 移行後の第1世代
│   └── v2.1/                  # VS Code / Antigravity 移行後の第2世代
├── releases/                  # 🚀【配布パッケージ領域】（旧公開ファイル）
│   ├── Chromatic_Harmonica_Trainer_Ver.1.01.zip
│   ├── Chromatic_Harmonica_Trainer_Ver.2.10.zip
│   └── Chromatic_Harmonica_Trainer_Ver.3.00.zip
├── AGENTS.md                  # AI開発者向けコアインストラクション
└── .gitignore                 # 統合除外設定（archives/v0_v1_notepad_prototypes等を除外）
```

---

## 4. 設計上の制約・決定事項

1. **防衛的UI設計（Defensive UI）の徹底**:
   - 右サイドバー幅は `370px` 固定。内部スクロールコンテナは `340px`、各グループ枠は `328px` を上限とし、可変長ラベルの中央省略（`ElideMiddle`）とコンボボックスのサイズポリシー強制（`AdjustToMinimumContentsLengthWithIcon`）を全ウィジェットに義務付ける。
2. **リアルタイム再生と動画合成の「単一基準式」共有**:
   - 外部音源・マイク録音・MIDIの配置時間は、再生系（pygame/PCM）と動画合成系（NumPy/WAV）で全く同一のオフセット計算式（$t_{\text{src}} = t_{\text{song}} - \Delta t_{\text{offset}}$）を共有し、試聴と出力結果の完全一致を保証する。
3. **データ永続化の分離原則**:
   - アプリ全般の設定（音量、オーディオ入出力デバイス、外観テーマ等）は `user_settings.json` に保存する。
   - 楽曲固有のコンテキスト（使用楽器、主旋律トラック、移調量、運指プリセット、個別変え指・ミュート、A-Bループ区間、伴奏パス、オフセット等）は `fingering/<曲名>_profile.json` に完全カプセル化して曲別に自動保存・復元する。
4. **スコープ衛生とシグナル安全弁**:
   - Python関数内でのインライン `import` はスコープ競合（`UnboundLocalError`）を引き起こすため原則禁止とし、ファイル冒頭に集約する。
   - プログラムからのUI値変更時は `blockSignals(True)` と `_is_loading` フラグによる二重ガードを必須とし、シグナル連鎖による意図せぬ上書き保存を防止する。

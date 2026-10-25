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
├── _docs/                     # アイデア・ログ・外部資料格納（アンダーバー規則）
│   ├── ideas/
│   ├── logs/
│   └── sources/               # extracted_knowledge.md, ai_development_playbook.md 等
├── _shared_knowledge/         # 再利用可能な汎用知見集（8割の汎用知見）
│   ├── architecture_patterns.md
│   ├── env_build.md
│   ├── ui_ux.md
│   └── inbox/
├── src/                       # 🌟【現行稼働コード】メインコードベース（旧v3.0移行）
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
├── _archives/                 # 📦【過去資産アーカイブ】（自律参照・編集禁止）
│   ├── v0_v1_notepad_prototypes/  # （旧bbbbb）メモ帳コピー時代の黎明期プロトタイプ（Ver 0.001〜1.01）
│   ├── v2.0/                  # VS Code / Antigravity 移行後の第1世代
│   └── v2.1/                  # VS Code / Antigravity 移行後の第2世代
├── releases/                  # 🚀【配布パッケージ領域】（大容量zip・Git除外）
│   ├── Chromatic_Harmonica_Trainer_Ver.1.01.zip
│   ├── Chromatic_Harmonica_Trainer_Ver.2.10.zip
│   └── Chromatic_Harmonica_Trainer_Ver.3.00.zip
├── AGENTS.md                  # AI開発者向けコアインストラクション
├── .gitignore                 # 統合除外設定（_archives/ や releases/ を除外）
├── sync_to_template.bat       # 共有知見を 00_template へ同期・還元するバッチ
└── update_from_template.bat   # 00_template から最新規約・知見を取り込むバッチ
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
5. **練習環境（`practice_visual`）と動画出力プリセット（`video_presets`）の完全分離（v3.1.0〜）**:
   - 日常の練習用表示設定（`practice_visual`：常時16:9・見やすさ最優先・操作時オートセーブ）と、用途別の動画書き出し設定（`video_presets`：Shorts縦型 9:16、演奏解説 16:9、シネマティックMV 16:9、クロマキー素材等の複数プリセット）をデータ層（`settings.json`）および描画反映層で分離する。
   - `🎨 画面作り` タブの編集対象ターゲット切替（`🎯 練習用` / `🎬 動画プリセット`）により、同一のUIウィジェット群を使いながら保存先・反映先を明確に切り替える。
   - `🎬 動画出力` タブからワンクリックで「現在の練習画面の見た目を動画プリセットに反映」できるブリッジ機能を備える。
6. **移調（Transpose）× カスタム運指（`SONG_FINGERING_OVERRIDES`）の排他保護**:
   - カスタム運指の内部辞書キー `(start_tick, lookup_note)` が移調後のMIDIノート番号に依存するため、1件以上のカスタム運指が存在する間は移調コントロール群をロック（`🔒 原曲キー固定`）し、意図せぬ運指破綻を防止する。
7. **表記形式（`lang_mode`）と表示可否トグル（`show_lookahead` / `grid4_mode`）の完全直交化（v3.2.0〜）**:
   - `lang_mode` は純粋な音名表記フォーマット（`["ドレミ", "CDE"]` の2択）のみを担い、`"なし"` を持たない。
   - ノーツ直上の音名表示可否は `show_lookahead`（bool）、穴下の音名・グリッド表示可否は `grid4_mode`（`["4音グリッド表示", "1音表示 (従来)", "非表示"]` の3択）が独立して担う。

---

## 5. 次世代メジャーアーキテクチャ青写真: Ver.4.0.0「Harmonica Studio（楽曲プロジェクト自己完結型）」

### 5.1 楽曲プロジェクトフォルダ（Song Project Container）のディレクトリ構造
従来の散在型（`src/fingering/`, `recordings/`, `output/` に全曲のファイルが混在する構造）を廃止し、DAW（Cubase / Logic / Studio One）と同様の **「1楽曲 ＝ 1自己完結フォルダ」** 構造へ移行する。

```text
projects/
└── Autumn_Leaves/                      # プロジェクトフォルダ（フォルダ名リネームに自動追従）
    ├── project.json                    # 🌟 プロジェクト統合マニフェスト（全設定・ハッシュ・テイク管理）
    ├── source/
    │   └── Autumn_Leaves.mid           # MIDI原本バックアップ（インポート時に自動コピー、SHA-256検証用）
    ├── audio/
    │   └── backing_track.mp3           # 外部伴奏音源（プロジェクト内コピーまたは相対/絶対パス参照）
    ├── takes/
    │   ├── take_001_20261025_1400.wav  # マイク録音テイク1（ドライ原本）
    │   ├── take_001_reverb.wav         # リバーブ適用キャッシュ
    │   └── take_002_20261025_1415.wav  # マイク録音テイク2（採用テイク）
    └── exports/
        ├── Autumn_Leaves_Shorts.mp4    # 書き出し完成動画（9:16）
        └── Autumn_Leaves_MV.mp4        # 書き出し完成動画（16:9）
```

### 5.2 同名MIDI衝突検知（SHA-256 ハッシュ比較）とリネーム追従仕様
1. **MIDI読み込み時のプロジェクト解決フロー**:
   - ユーザーが `foo.mid` を開いた際、まずファイルの **SHA-256 ハッシュ** を算出する。
   - `projects/foo/project.json` が既に存在する場合：
     - **ハッシュが一致**: 同一楽曲と判定し、既存の `projects/foo/` プロジェクトをそのままロードする。
     - **ハッシュが不一致（同名・別内容MIDI）**: 警告ダイアログ *「同名ですが内容が異なるMIDIファイルです。新しいプロジェクトフォルダ（例: `foo_2`）を作成しますか？ それとも既存プロジェクトのMIDIを差し替えますか？」* を表示し、運指や録音テイクの誤上書き事故を100%防止する。
2. **フォルダ名リネーム追従**:
   - `project.json` 内のパス参照はすべて **プロジェクトルートからの相対パス**（`source/...`, `takes/...`, `audio/...`）で保持する。
   - これにより、ユーザーがエクスプローラー上でフォルダ名を `Autumn_Leaves` から `枯葉_本番用` に変更しても、リンク切れを起こさず完全に追従する。

### 5.3 `project.json` データモデル（キー別運指パターン対応）
1曲の中で「原曲キー用」「移調+2（ボーカル合わせ）用」など、**移調値（`transpose`）と個別変え指（`overrides`）をセットにした複数の運指パターン** を保持できるスキーマとする。

```json
{
  "schema_version": "4.0.0",
  "project_name": "Autumn_Leaves",
  "midi_source": {
    "relative_path": "source/Autumn_Leaves.mid",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "instrument_type": "16穴 (64音・C調)",
  "tracks": {
    "main_track_indices": [1],
    "accomp_track_indices": [2, 3],
    "monophonic_mode": "すべて有効"
  },
  "active_fingering_pattern": "Key +2 (D調) - ボーカル伴奏用",
  "fingering_patterns": {
    "原曲キー (±0) - 標準": {
      "transpose": 0,
      "transpose_accomp": true,
      "base_rule": "スライド最小化 (標準)",
      "hide_muted_notes": false,
      "overrides": { "480:60": [5, "吹", "OFF", false] },
      "muted_notes": []
    },
    "Key +2 (D調) - ボーカル伴奏用": {
      "transpose": 2,
      "transpose_accomp": true,
      "base_rule": "スライド優先 (異名同音)",
      "hide_muted_notes": true,
      "overrides": { "480:62": [5, "吸", "OFF", false] },
      "muted_notes": ["960:64"]
    }
  },
  "audio_assets": {
    "ext_audio_rel_path": "audio/backing_track.mp3",
    "ext_offset_ms": -120,
    "ext_volume": 80,
    "active_take_rel_path": "takes/take_002_20261025_1415.wav",
    "rec_offset_ms": 0,
    "takes_history": [
      { "file": "takes/take_001_20261025_1400.wav", "duration_sec": 185.2, "memo": "ウォームアップ" },
      { "file": "takes/take_002_20261025_1415.wav", "duration_sec": 185.4, "memo": "本番採用テイク" }
    ]
  },
  "practice_state": {
    "loop_enabled": false,
    "loop_a": 1,
    "loop_b": 32,
    "practice_audio_source": "midi_only",
    "active_video_preset": "📱 YouTube Shorts (縦型・解説)"
  }
}
```

### 5.4 `src/main.py`（約5,000行）の段階的モジュール分割計画（Ver.4.0.0）
肥大化した `src/main.py` を以下の5モジュールへ安全に責務分離する：
1. `src/project_manager.py`: プロジェクトフォルダ作成、SHA-256ハッシュ照合、`project.json` 読み書き、旧 `src/fingering/*.json` からの自動インポート。
2. `src/ui_settings_dialog.py`: 使用頻度の低いシステム環境設定（オーディオデバイス、MIDI音源エンジン、カスタムスキン画像パス、FFmpegエンコーダ詳細等）を集約した `[⚙ 環境設定]` モーダル/モードレスウィンドウ。
3. `src/ui_tab_practice.py`: 練習タブUI（楽器・キー別運指パターン切替・練習画面スタイル簡易設定・練習音源切替）。
4. `src/ui_tab_studio.py`: 録音・伴奏同期・動画プリセット・書き出しタブUI。
5. `src/main.py`: メインウィンドウ骨格、上部トランスポート、OpenGLキャンバス配置、クロック・イベント統括（約1,500行以下にスリム化）。

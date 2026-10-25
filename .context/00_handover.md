# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 12:50 (Gemini 4.0によるv3.1.0詳細設計・Micro-Step指示書の `02_tasks.md` 統合完了)

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
│   ├── architecture_patterns.md  # Gotcha #6（存在しない実体の推測補完厳禁）追記済
│   ├── env_build.md
│   ├── ui_ux.md
│   └── inbox/
├── src/                       # 🌟【現行稼働コード】メインコードベース（旧 v3.0 より完全移行）
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
│   └── skins/                 # ハーモニカ本体外観スキン画像（メタル、ウッド、ゴールド等）
├── _archives/                 # 📦【過去資産アーカイブ】（自律参照・編集は厳禁）
│   ├── v0_v1_notepad_prototypes/  # （旧bbbbb）メモ帳コピー時代の黎明期プロトタイプ
│   ├── v2.0/                  # VS Code / Antigravity 移行後の第1世代
│   └── v2.1/                  # VS Code / Antigravity 移行後の第2世代
├── releases/                  # 🚀【配布パッケージ領域】（大容量zip・Git除外）
│   ├── Chromatic_Harmonica_Trainer_Ver.1.01.zip
│   ├── Chromatic_Harmonica_Trainer_Ver.2.10.zip
│   └── Chromatic_Harmonica_Trainer_Ver.3.00.zip  # 最新ビルド（65.4MB・全改修内包）
├── AGENTS.md                  # AI開発者向けコアインストラクション
├── .gitignore                 # 統合除外設定（_archives/ や releases/ を除外）
├── sync_to_template.bat       # 共有知見を 00_template へ同期・還元するバッチ
└── update_from_template.bat   # 00_template から最新規約・知見を取り込むバッチ
```

---

## 2. これまでに達成した全機能・改修完了サマリー

### 【基盤・音響・録音改善 (Step 1 〜 Step 4)】
- **Step 1 (コミット `450272b`)**:
  - 右サイドバー幅を340pxに厳格制限（`setMaximumWidth(340)`、グループ枠328px）。
  - 録音テイク行を2段構成に変更（1段目: ファイル名ラベル、2段目: 試聴・エクスポートボタン）。横溢れを物理根絶。
  - 同期ズレ補正スピンボックスを90pxに拡大（`-5000 ms` が欠けずに収まる）。
- **Step 2 (コミット `cc9cc3c`)**:
  - 外部音源再生を `pygame.mixer.music` からメモリPCM直接スライス再生（専用チャンネル）に刷新し、ミリ秒単位の同期精度を確立。
  - 「⏮ 先頭」巻き戻し時のフリーズを解消（安全シークシーケンス）。
  - リバーブ調整をスライダー操作＋「▶ 試聴」ボタンによるクリーンな独立試聴方式に改善。
- **Step 3 (コミット `e6d657f`)**:
  - マイク録音時、前奏（カウントイン）時間を録音WAVの先頭から自動トリム（サンプル境界バイトスライス）する処理を実装。
  - マイク録音遅延補正スピンボックス（`spin_rec_offset`: -2000ms〜+2000ms）を追加。
- **Step 4 (コミット `fe66905`)**:
  - 動画出力タブに「🎼 音声トラック・ミキサー...」ボタンを新設。
  - トラック①伴奏、トラック②マイク録音、トラック③内蔵MIDIシンセを自由に組み合わせ可能な3層ミキシングパイプラインを実装。True Peak（`-1.0 dBFS`）制限およびYouTubeラウドネス基準対応。

### 【動画レンダリング・演出・スキン改善 (Step 5 〜 Step 8)】
- **Step 5 (コミット `d64a6f0`) 【課題A】**:
  - 解像度算出関数 `calc_export_resolution` を新設。
  - 9:16（1080x1920 / 720x1280 / 2160x3840）、4:3（1440x1080 / 960x720 / 2880x2160）の真のピクセル解像度（偶数ピクセル保証）を算出して FFmpeg およびレンダラーに供給。中央ピラーボックス（黒帯）を完全排除。
  - `config.py` の `get_canvas_height_by_ratio` を高精度浮動小数 `960.0 * 16.0 / 9.0` に精密化（上下0.375pxの隙間根絶）。
- **Step 6 (コミット `1e1b6b5`) 【課題B】**:
  - `_draw_bordered_text_qt` に `painter.setClipRect` と `QFontMetricsF.elidedText` を導入し、タイトル・クレジット文字の枠外はみ出しを物理根絶。
  - 縦型（9:16）動画において常時表示カード幅を `w * 0.70` に拡張、内側パディング（左右20px等）を厳密分離。
- **Step 7 (コミット `5d40a7b`)**:
  - `main.py` の `render_settings` に `skin_mouthpiece_path`, `skin_lever_off_path`, `skin_lever_on_path` を完全注入。
  - `video_exporter.py` に `_resolve_skin_file` を新設し、ポータブル環境でもカスタムスキン（ウッド・ゴールド等）を自動探索・テクスチャ適用。フレームプレビューにも即時反映。
- **Step 8 (コミット `8d77ced`)**:
  - タイトル出現・退場の基準時間を楽曲時間（`cur_sec`）から動画絶対時間（`t_in_video`）に刷新。
  - 前余白（例: 5秒）設定時、動画開始と同時に黒フェードインしてタイトルが浮かび上がり、演奏開始直前に綺麗にフェードアウトする理想的な演出を確立。

### 【配布パッケージのクリーンビルド＆ZIP化 (課題C)】
- Step 1〜8 の全改修を内包した単一実行ファイル `Chromatic_Harmonica_Trainer.exe`（65,776,384 bytes）をビルド完了。
- クリーンなポータブル配布用初期設定（`settings.json`）を適用したZIPアーカイブ（[`releases/Chromatic_Harmonica_Trainer_Ver.3.00.zip`](file:///c:/Users/j28k1/Desktop/harmonica-visualizer/releases/Chromatic_Harmonica_Trainer_Ver.3.00.zip): 65,473,469 bytes、全38エントリ検証済）を生成完了。

---

## 3. 直近のチャットやり取りと課題意識（UI/UX再設計の背景）

ユーザー様より**「継ぎ足し開発の結果、機能がとっ散らかってパネル分類や使い勝手が悪くなっている」**という重要なご相談をいただき、以下の4大矛盾と解決方針で合意形成・整理を行いました：

1. **移調（トランスポーズ）× カスタム運指の衝突**:
   - 移調すると手動で指定したカスタム運指の音名とMIDIノートがズレて破綻する。
   - ➔ **解決案**: カスタム運指適用中は移調スピンボックスをロック（`🔒 原曲キー固定 (カスタム運指適用中)`）し、ツールチップ等で理由を明示。移調したい場合は自動運指への切り替え確認を促す。
2. **音声設定の二重構造（練習と動画で重複）**:
   - 練習タブにも動画タブにも音量・外部音源・リバーブがあり、どこをいじれば何が鳴るのか混乱する。
   - ➔ **解決案**: 音響設定を「共通ミキサー」1つに一本化。動画側の音声設定は「練習と同じ音（ミキサー連動）」を選択するのみとし、重複スライダーを全廃。
3. **ビジュアル設定とアスペクト比の非対称性**:
   - スキンや背景画像は共通なのに、縦横比（16:9 / 9:16 / 4:3）だけが動画タブに隔離されている。
   - ➔ **解決案**: 「画面スタイル」枠にアスペクト比を集約し、練習中も9:16を選べばそのままShorts構図で練習・確認できるように一元化。
4. **サイドバーの分類カオス**:
   - ➔ **解決案**: 上部に「作業モード切り替え（練習 / 録音 / 動画書き出し）」を配置し、下部に「共通リソース（🎨 画面スタイル / 🎛️ 音声ミキサー）」をアコーディオン開閉で配置する上下分離アーキテクチャへの再編。

---

## 4. 次期マイルストーン計画: Ver.3.1.0（Gemini 3.8 向け Micro-Step 指示書完備）

上位モデル（Gemini 4.0）にてコードベース全体を精査し、Gemini 3.8 が迷わず1ステップずつ実装・コミットできるよう、**全7マイクロステップの詳細実装指示書（対象ファイル・行番号・コードブロック・コミットメッセージ付き）** を [`.context/02_tasks.md`](file:///c:/AI_Dev_Workspace/01_2026_10_00_harmonica-visualizer/.context/02_tasks.md) に統合済みです。

- **Micro-Step 1**: `src/harmonica_map.py` に `has_custom_fingering()` 判定ヘルパー追加
- **Micro-Step 2**: `src/main.py` の移調ロック制御（`_update_transpose_lock_state`）実装 ＆ 残存インライン `import` 除去
- **Micro-Step 3**: `src/settings_manager.py` に `practice_visual` と公式4種の `video_presets`、および自動マイグレーションを追加
- **Micro-Step 4**: `src/main.py` にビジュアル状態抽出・適用ヘルパーと `_build_export_render_settings` を統合
- **Micro-Step 5**: `🎨 画面作り` タブの編集対象ターゲット切替（`🎯 練習用` / `🎬 動画プリセット`）とタブ切替連動を実装
- **Micro-Step 6**: `🎬 動画出力` タブ最上部に「🗂️ 動画出力プリセット」管理UIおよび「📋 練習画面の見た目を反映」ブリッジを実装
- **Micro-Step 7**: 全体結合検証・引き継ぎドキュメント更新・Gitタグ `v3.1.0` 付与

---

## 5. 設計・運用の絶対遵守ルール（Gotchas）

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

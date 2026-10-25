# Current Status & Handover (00_handover.md)

## 最終更新日時
- 2026-10-25 21:25 (Ver.4.1.0 実装完了・静的コード全体監査による7大潜在バグ修正完了・全テスト100% PASS・実機デバッグ準備完了)

---

## 1. プロジェクト現在地と最新ステータス

- **現行リリースバージョン**: **`v4.1.0`**（静的監査パッチ適用完了、Gitタグ `v4.1.0` 更新済）
- **完了マイルストーン**: **`v4.1.0`「Harmonica Studio UI/UX Polish & Workflow Perfection」**
  - 実機動作確認フィードバックに基づく **全21課題が完全解消（Batch Package 1〜5、Micro-Step 1〜10 すべて完遂）**。
  - **Gemini 4.0 による静的コード全体監査（全6カテゴリ）** に基づき、コード段階で判明した潜在問題（比率同期の表記揺れによる逆上書き、旧非表示フレームによるボタン属性破壊、リバーブ配線、Shortsスプリットスクリーンのオクターブ点線境界クリッピングなど全7点）の修正パッチを完全適用。
  - `tests/verify_v400_studio.py`（全8項目）および `tests/verify_v410_polish.py`（全8項目）の双方で **100% PASS（完全合格）** を確認。
- **リポジトリ状態**: `master` ブランチ、`working tree clean`（未コミット差分ゼロ）
- **次回最初に行うこと**: **人間による実機操作・音出し・動画書き出しデバッグの実施**。

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
├── src/                       # 🌟【現行稼働コード】メインコードベース（v4.1.0 安定稼働中）
│   ├── main.py                # メインウィンドウ、サイドバー構築、タブ連動
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
    ├── verify_v400_studio.py  # v4.0.0 自動統合検証スクリプト
    └── verify_v410_polish.py  # v4.1.0 全8項目総合回帰検証スクリプト
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
  - `tests/verify_v400_studio.py`（全8項目自動テスト）が完全 PASS。

### ② Ver.4.1.0「Harmonica Studio UI/UX Polish」全21課題の完全解消
- 実機動作確認フィードバックに基づき、Package 1〜5（Micro-Step 1〜10）を段階的かつ確実に完遂。
  - プリセット切替時 `ratio_combo` 自動同期＆Shorts比率自己修復
  - カスタムスキンの練習画面即時反映
  - フォールバック保存先の `projects/_demo_chromatic` 集約
  - 変え指マーク二重コントラスト枠線、移調表記重複解消
  - `[⚙ 設定]` の整理とプロジェクト親子階層ツリー図解表示、`[🎼 パート]` への主旋律音色固定移設
  - 公式5大プリセット再設計（王道16:9背景MV追加・解説垂直落下）＆比較一覧表タブ
  - 2階層タブ化（🎹 練習 vs 🎬 動画制作）、プリセットヘッダー一元化、セクション折りたたみ（`CollapsibleSection`）
  - 録音タブの不要音量枠撤去、動画出力タブの二重リバーブ撤去
  - タイトルカード表示時間（`0.1s〜15.0s`）＆消滅演出（フェード/カット）の独立化
  - YouTube Shorts (9:16) 上下2分割レイアウト（上半分16:9 / 下半分16:9 / 中央16:9）
  - 起動直後の `QSplashScreen` ＆ `QSharedMemory` 多重起動防止ロック

### ③ 静的コード全体監査（Inspector Mode）による潜在バグの事前解消
- Gemini 4.0 による全6カテゴリの静的監査で指摘された全7項目を完全修正：
  1. `ratio_combo` のテキスト完全一致による逆上書きバグをインデックス検索へ修正
  2. 非表示フレーム `f_preset` 内でのボタン参照破壊を撤去
  3. 動画エクスポートパイプラインにおける `reverb_enabled` の参照先を `self.chk_reverb.isChecked()` に統一
  4. OpenGL描画および動画レンダラーにおける YouTube Shorts スプリットスクリーンのオクターブ点線境界クリッピング適用
  5. タイトルカードのフェード消去境界計算の整合性担保
  6. テストスイートのバージョン互換性確保

---

## 3. Ver.4.1.0 実装ロードマップ（全5パッケージ / 10 Micro-Steps）

| パッケージ | ステップ | 対象ファイル | 主な実装内容 | 状態 |
| :--- | :--- | :--- | :--- | :--- |
| **Package 1** | **Step 1** | `settings_manager.py`<br>`main.py`<br>`project_manager.py` | プリセット切替時 `ratio_combo` 自動同期＆Shorts比率自己修復、カスタムスキンの練習画面即時反映、フォールバック保存先の `projects/_demo_chromatic` 集約 | **完了 (e413ed4)** |
| | **Step 2** | `gl_visualizer.py`<br>`harmonica_map.py`<br>`main.py` | モノクロ時の変え指マーク二重コントラスト枠線、`Key +12` パターン名＆ステータスバー移調表記の重複解消 | **完了 (cdda8ef)** |
| **Package 2** | **Step 3** | `dialogs.py`<br>`main.py` | `[⚙ 設定]` の重複項目（メトロノーム・ステップアップ）撤去、プロジェクト親子階層ツリー図解表示、`[🎼 パート]` への主旋律音色固定移設 | **完了 (64d2327)** |
| | **Step 4** | `settings_manager.py`<br>`dialogs.py` | 公式5大プリセット再設計（王道16:9背景MV追加・解説垂直落下）＆ `[⚙ 設定]` への「🎬 初期プリセット比較一覧表」タブ追加 | **完了 (878eef6)** |
| **Package 3** | **Step 5** | `main.py` | サイドバーの「🎹 練習 vs 🎬 動画制作」2階層タブ化、プリセットヘッダー一元化、「📥 練習からコピー」ボタン、自作プリセット「🗑️ 削除」動的切替、右下保存ボタン撤去 | **完了 (cc4bca0)** |
| | **Step 6** | `main.py` | 全セクションを1行最小化できる `CollapsibleSection` 導入、画面デザインタブの順序改善（比率を最上部に配置） | **完了 (b89f49b)** |
| **Package 4** | **Step 7** | `main.py` | 録音タブの不要音量枠撤去、動画出力タブの二重リバーブ撤去、フェードの余白直下配置、タイトル表示時間（`0.1s〜15.0s`）＆消え方UI新設 | **完了 (cd1dd38)** |
| | **Step 8** | `studio_controller.py`<br>`video_exporter.py` | タイトル表示時間を前余白から独立させ、`0.1s〜15.0s` 維持＆フェード/カット消去レンダリング実装 | **完了 (65fdb31)** |
| **Package 5** | **Step 9** | `main.py`<br>`gl_visualizer.py`<br>`video_exporter.py` | YouTube Shorts (9:16) 上下2分割レイアウト（上半分16:9 / 下半分16:9 / 中央16:9）の実装 | **完了 (9ffb006)** |
| | **Step 10** | `main.py`<br>`tests/verify_v410_polish.py` | 起動直後の `QSplashScreen` ＆ `QSharedMemory` 多重起動防止ロック実装、全自動結合テスト実行・全PASS確認 | **完了 (c28ebd3, 27c829e)** |
| **Inspector** | **Audit Fix** | `main.py`<br>`studio_controller.py`<br>`gl_visualizer.py`<br>`video_exporter.py` | Gemini 4.0 静的コード全体監査による全7項目の潜在バグ修正、全自動テスト PASS | **完了** |

---

## 4. 次回作業再開時に最初に行うべきタスク

Ver.4.1.0 の実装および静的コード全体監査パッチの適用がすべて完了し、全自動テスト（v4.0.0 & v4.1.0）が 100% PASS しました。
次回セッション開始時は、**人間による実機デバッグおよび動作確認** に進みます。

### 実機デバッグ時の重点確認チェックリスト：
1. **スプラッシュ画面＆多重起動防止**: アプリ起動時にロゴ付きスプラッシュが表示されるか、2重起動しようとした際に警告が出るか。
2. **プリセット切り替えと比率同期**: 公式5大プリセットを切り替えた際、16:9 と 9:16（Shorts）が正しく切り替わり、意図しない逆上書きが発生しないか。
3. **YouTube Shorts (9:16) スプリットスクリーン**: 上半分16:9 / 下半分16:9 / 中央16:9 の各モードで、ハーモニカとノーツが各領域に正確にクリッピングされ、オクターブ点線が上下領域へ突き抜けないか。
4. **動画書き出しとリバーブ**: 録音タブのリバーブON/OFF設定が、動画エクスポート時の音声パイプラインに正確に反映されるか。
5. **タイトルカード表示時間と消滅演出**: 0.1秒〜15.0秒の設定、フェードアウト / カットの切り替えが動画内で正しく反映されるか。
6. **2階層タブとセクション折りたたみ**: サイドバーの「🎹 練習」「🎬 動画制作」タブの切り替え、各セクションの1行最小化がスムーズに動作するか。

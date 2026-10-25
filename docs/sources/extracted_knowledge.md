# クロマチックハーモニカ・ビジュアライザー 開発知見・トラブルシューティング大全 (extracted_knowledge.md)

本ドキュメントは、デスクトップアプリケーション「クロマチックハーモニカ・ビジュアライザー＆トレーナー」の初期プロトタイプ（v1.01）から v2.0、v2.1、そして PyQt6 + 64-bit OpenGL + 高品位音響・動画エンジン（v3.0）に至る全開発プロセスで発生したエラー、試行錯誤、根本原因、および解決した具体的なコード・設定ポイントを網羅した知見録である。

---

## 1. UI/UX周りで発生した問題・レイアウト崩れ・イベント処理の注意点

### 1-1. 可変長文字列（長いファイル名等）によるパネル幅溢れとボタン押し出し
* **起きた事実・現象**:
  * 伴奏ファイルや録音テイク名に長い名前（例: `紅楼 ～ Eastern Dream(ハーモニカ…)_take_036_reverb.wav`）を読み込むと、右サイドバー（幅 `370px`）が外側に押し広げられ、横スクロールバーが出たり、同列にあったボタン（「▶ 試聴」「💾 エクスポート」）がパネル枠外に押し出されて見えなくなった。
  * 「すべてのパネルについて対応して」と指示された後も、録音テイクラベル、背景画像情報ラベル、スピンボックス等で幅溢れが再発した。
* **原因**:
  * `QLabel` に `setWordWrap(True)` を設定しても、アンダースコア（`_`）やハイフン、日本語が連続する文字列は「単語区切り（空白）」がないため折り返されず、最小幅（`minimumSizeHint`）が文字列実寸（数百ピクセル）まで肥大化する。
  * `QComboBox` のデフォルト動作（`SizeAdjustPolicy.AdjustToContents`）により、プルダウンに含まれる最も長い選択肢に合わせてコンボボックス自体の最小幅が自動拡張されていた。
  * `QHBoxLayout` で `[QLabel(stretch=1)] [QPushButton] [QPushButton]` を1行に配置していたため、ラベルの肥大化がボタンを物理的に押し出していた。
* **解決コード・対策**:
  1. **コンテナ側でのハードリミット**:
     ```python
     # スクロール内コンテナとグループ枠に最大幅を明示
     scroll_content.setMaximumWidth(340)
     for group in self.findChildren(QGroupBox):
         group.setMaximumWidth(328)
     ```
  2. **ラベルの中央省略（ElideMiddle）とツールチップ退避**:
     ```python
     def _set_elided_label_text(self, label: QLabel, text: str, full_tooltip: str = "", max_width: int = 270):
         label.setMinimumWidth(0)
         label.setToolTip(full_tooltip or text)
         fm = label.fontMetrics()
         elided = fm.elidedText(text, Qt.TextElideMode.ElideMiddle, max_width)
         label.setText(elided)
     ```
  3. **コンボボックスのサイズポリシー強制**:
     ```python
     def _configure_sidebar_combo(self, combo: QComboBox, min_chars: int = 8):
         combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
         combo.setMinimumContentsLength(min_chars)
     ```
  4. **行構造の2段分離（物理隔離）**:
     可変長ラベルと操作ボタン群を同一行に並べるのをやめ、1段目をラベル単独、2段目をボタン列（`QHBoxLayout`）に分けるレイアウトに変更した。
  5. **スピンボックスの固定幅**:
     `-5000 ms` のような8文字＋矢印ボタンが入るよう、`setFixedWidth(90)` を設定して文字切れ（`-5000 m`）を防止。

---

### 1-2. UI初期化・ファイル読み込み時の「シグナル暴発（Signal Storm）」
* **起きた事実・現象**:
  * MIDIファイルを読み込んだ際、以前保存したはずの移調設定や運指プリセット、単音化モードが初期値（0stやデフォルト）に勝手に上書きされてしまった。
* **原因**:
  * プログラム側から `self.spin_transpose.setValue(val)` や `self.combo_preset.setCurrentText(...)` を実行した瞬間に、Qtの `valueChanged` や `currentTextChanged` シグナルが同期的に発火。
  * それらに接続されていた「設定変更ハンドラ（`_on_transpose_changed` 等）」が走り、まだ読み込みが完了していない中途半端な状態のまま曲別プロファイルJSONを上書き保存していた。
* **解決コード・対策**:
  * シグナルの個別一時ブロックと、ロード中フラグによる二重ガード：
  ```python
  self._is_loading_midi = True
  try:
      self.spin_transpose.blockSignals(True)
      self.spin_transpose.setValue(saved_val)
      self.spin_transpose.blockSignals(False)
      # ...
  finally:
      self._is_loading_midi = False

  # 各設定ハンドラ側
  def _on_transpose_changed(self):
      if getattr(self, "_is_loading_midi", False):
          return  # ロード中は保存や再計算をスキップ
      self._save_current_settings()
  ```

---

### 1-3. OpenGLウィジェットとQtイベントループの描画タイミング競合
* **起きた事実・現象**:
  * 再生停止中やシーク操作時に、ノーツバーやハーモニカのハイライト位置が1フレーム遅れて描画されたり、リサイズ時に黒いチラつきが発生した。
* **原因**:
  * QOpenGLWidget の描画サイクル（`paintGL`）と、タイマー駆動のクロック更新が非同期に走り、`update()` の要求がQtの描画キューに溜まっていた。
* **解決コード・対策**:
  * シーク時やノーツ変え指の編集直後に `self.gl_widget.update()` を明示的に呼び出し、さらに一時停止中であってもアンカー秒数に基づく強制フレーム更新（`render_frame(sec)`）を実行するように統一。

---

## 2. 環境構築、ライブラリの依存関係、ビルドやパッケージング（PyInstaller等）、OS固有の挙動

### 2-1. PyInstaller EXEビルドとPythonソースコードの非同期（認識ギャップ）
* **起きた事実・現象**:
  * Pythonファイル（`.py`）でバグ修正を行いテストが通っているにもかかわらず、ユーザーが手元で実行したEXEでは同じバグ（UI崩れやエラー）が発生し続け、すれ違いが発生した。
* **原因**:
  * 「`.py` のコード修正」と「PyInstallerによるビルド生成物（`dist/...exe` や `公開ファイル/...exe`）」は完全に別物であり、再ビルドを実行しない限りEXEの中身は更新されない。
  * ファイルのタイムスタンプを確認したところ、コード改修（22:30）に対してEXEは夕方（16:44）にビルドされた旧バージョンのままであった。
* **教訓・対策**:
  * 作業フェーズを「①Pythonコード改修・単体テスト完了」と「②配布パッケージEXEビルド・統合検証」に明確に切り分け、ビルドが完了するまでは「現在はPythonソースのみ修正済み」と明言する。
  * アプリのタイトルバーや詳細ログにビルド日時（またはGitコミットハッシュ）を表示し、起動中のバイナリが最新か即座に判別できるようにする。

---

### 2-2. Windows PowerShellにおける `cp932` 文字コード例外
* **起きた事実・現象**:
  * 自動テストスクリプトや検証用ワンライナーをPowerShell経由で実行した際、`UnicodeEncodeError: 'cp932' codec can't encode character ...` でPythonがクラッシュした。
* **原因**:
  * 日本語WindowsのPowerShell標準出力（stdout）のデフォルトエンコーディングが `cp932`（Shift-JIS）であり、絵文字（`🎵`, `🎼`, `❌`, `▶` 等）を出力しようとするとエンコードできずに例外を送出する。
* **解決コード・対策**:
  * スクリプト冒頭で標準出力のエンコーディングを明示的に UTF-8 に再設定する：
  ```python
  import sys
  if sys.stdout and hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8")
  ```

---

### 2-3. FFmpegおよびOpenGLのヘッドレス・PyInstallerバンドル
* **起きた事実・現象**:
  * ビルド環境で動画出力を行おうとすると `ffmpeg.exe not found` になったり、他PCで起動した際にDLLが見つからずクラッシュした。
* **解決策**:
  * `config.py` 内にポータブルパス解決ヘルパー（`get_portable_path()`）を実装：
  ```python
  def get_portable_path(rel_path: str) -> str:
      if getattr(sys, "frozen", False):
          base = os.path.dirname(sys.executable)
      else:
          base = os.path.dirname(os.path.abspath(__file__))
      return os.path.normpath(os.path.join(base, rel_path))
  ```
  * `ffmpeg.exe` はアプリフォルダ直下の `ffmpeg/bin/ffmpeg.exe` またはシステムPATHを透過的にフォールバック検索する構造にした。

---

## 3. アーキテクチャ、非同期処理、ファイル入出力、設定管理で学んだこと

### 3-1. Pythonの関数内インライン `import` が招く `UnboundLocalError`
* **起きた事実・エラー内容**:
  ```text
  UnboundLocalError: cannot access local variable 'harmonica_map' where it is not associated with a value
  ```
  * ファイル先頭で `import harmonica_map` しているにもかかわらず、`_load_midi_file` 関数内でこの例外が発生した。
* **原因**:
  * Pythonコンパイラは、関数内に1箇所でも `import harmonica_map` や代入文があると、その関数スコープ全体で `harmonica_map` を「ローカル変数」として予約（`STORE_FAST` / `LOAD_FAST`）する。
  * 関数の後方（3283行目）に関数内インポートが書かれていたため、関数の前方（3277行目）で呼んだ `harmonica_map.normalize_fingering_preset()` が未束縛ローカル変数とみなされた。
* **教訓・対策**:
  * **関数内インライン `import` の原則禁止**。すべてのモジュールインポートはファイル最上部（モジュールレベル）に集約する。

---

### 3-2. リアルタイム再生と動画書き出しにおける音声配置計算の二重管理破綻
* **起きた事実・現象**:
  * 外部音源の同期ズレ補正（`offset_ms`）を設定し、アプリ上でタイミングを合わせても、動画出力（WAV合成）を行うと伴奏の頭出しがズレていた。
* **原因**:
  * 再生時の計算式（pygame側）と、オフライン合成時の計算式（NumPy/WAV側）が別々の関数にハードコードされ、片方は `sec - offset`、もう片方は `sec + offset` と符号が逆になっていた。
* **解決コード・対策**:
  * **単一の基準計算式（$t_{\text{src}} = t_{\text{song}} - \Delta t_{\text{offset}}$）の徹底**:
  ```python
  # リアルタイム再生・動画合成共通
  offset_sec = offset_ms / 1000.0
  src_sec = cur_song_sec - offset_sec

  # 正オフセット（音源を遅らせる場合）: src_sec < 0 の間は発音待機
  # 負オフセット（音源を早める場合）: src_sec >= 0 からスライス再生
  ```

---

### 3-3. 設定管理の粒度（「全体設定」vs「曲別プロファイル」）
* **学んだこと**:
  * 「音量」「オーディオデバイス」「外観テーマ」はアプリ全体のグローバル設定（`user_settings.json`）。
  * 一方、「使用楽器（12/14/16穴）」「主旋律トラック番号」「移調量」「A-Bループ区間」「外部伴奏ファイルパスと同期オフセット」「運指変え指オーバーライド」「個別ミュートノーツ」は**曲ごとに固有のコンテキスト**である。
  * これらを分離し、`fingering/<midi名>_profile.json` として曲別に自動保存・自動復元するアーキテクチャにしたことで、曲を切り替えても前回の練習環境が一発で蘇るようになった。

---

## 4. このアプリ固有のロジックや特殊な仕様に関するトラブルシューティング

### 4-1. 外部音源のミリ秒同期と「先頭巻き戻し」フリーズ
* **起きた事実・現象**:
  * 外部伴奏（MP3/WAV）再生中に「⏮ 先頭」ボタンを押すと、GUIが完全にフリーズ（ハングアップ）した。また正のオフセット（遅延発音）が効かなかった。
* **原因**:
  * `pygame.mixer.music` はストリーミングデコード方式であり、ミリ秒単位のシーク精度が出ない。また `play(start=sec)` に負の秒数を渡せないため正オフセット（待機）が機能しなかった。
  * さらにハンドラ内で存在しない `self.seek(0.0)` を呼び出し、内部ロックの競合を起こしていた。
* **解決策**:
  * **「メモリPCM直接スライス再生」への完全移行**:
    1. ロード時に 44.1kHz / 16bit / Stereo の NumPy 配列としてメモリに展開。
    2. 再生時は `src_sec >= 0` であれば `start_idx = int(src_sec * 44100)` から配列を直接スライスし、`pygame.sndarray.make_sound()` で専用チャンネルから即座に発音（0.02ms精度）。
    3. `src_sec < 0` の場合は待機フラグ（`_ext_pending_start`）を立て、タイマーで楽曲時間がオフセットに達した瞬間に0フレーム目から再生。
    4. 「先頭」ボタンでは専用チャンネルの `.stop()` ➔ 内部クロックのアンカーリセット（`_on_rewind()`）の安全シーケンスを実行。

---

### 4-2. マイク録音の前奏（カウントイン）混入と動画出力時の頭ズレ
* **起きた事実・現象**:
  * 前奏（カウントイン 1〜2小節）を入れて録音を開始すると、前奏分の無音やブレス音が録音WAVの冒頭にそのまま入る。しかし動画出力時は前奏を除外して本編0.0秒から始まるため、動画と自分の演奏が前奏秒数分だけ丸ごとズレてしまう。
* **解決策**:
  * 録音停止時に前奏秒数分を自動で切り落とす**「サンプル境界バイトトリム」**:
  ```python
  # AudioRecorder.stop_recording 内
  if trim_start_sec > 0.0 and len(self.buffer) > 0:
      frame_bytes = self.channels * 2  # 16-bit PCM = 2 bytes per sample
      trim_frames = int(round(trim_start_sec * self.sample_rate))
      trim_bytes = trim_frames * frame_bytes
      if trim_bytes < len(self.buffer):
          self.buffer = self.buffer[trim_bytes:]
      else:
          self.buffer = bytearray()
  ```
  * これにより、ユーザーが前奏を何小節設定して録音しても、保存されるWAVは常に「楽曲本編0.0秒ジャスト」に頭出しされる。

---

### 4-3. 縦型動画（9:16）および 4:3 動画の「黒帯ピラーボックス化」不具合
* **起きた事実・現象**:
  * 画面作りタブで「9:16（縦型・Shorts/TikTok）」や「4:3」を選択して書き出しても、1920x1080（16:9）の横長画面の中央に黒帯付きで配置された動画が出力され、タイトル文字が黒帯にはみ出していた。
* **原因**:
  * プレビュー用ピラーボックス描画と、出力動画ファイルのコンテナ解像度を混同し、FFmpegおよびOpenGLオフスクリーンレンダラーに渡す解像度を `1920x1080` / `1280x720` 等の16:9固定値にしていた。
* **解決策**:
  * 解像度グレード（720p / Full HD / 4K）とアスペクト比（16:9 / 9:16 / 4:3）のマトリクスから真のフレームバッファサイズ（9:16なら `1080x1920`, 4:3なら `1440x1080`）を算出してFFmpegに渡し、ピラーボックス描画をバイパスして全域レンダリングする。
  * タイトル・クレジット描画座標を実レンダリング幅 $W$ に対する相対比率（フォントサイズ・マージン等）で動的計算する。

---

### 4-4. 和音の単音化フィルターとハーモニカ異名同音（変え指）の階層解決
* **起きた事実・現象**:
  * ピアノ譜などのMIDIを読み込むと、主旋律に重音（和音）が含まれており複数の穴が同時に光って演奏できない。また、曲や奏者の好みによって変え指（例：C5を4穴吹か3穴吸レバーONか）を選びたい。
* **解決策**:
  1. **時間窓クラスタリングによる単音化**:
     微小Tick窓内の重なりノーツ群を検出し、「高音優先（メロディライン）」「低音優先」「すべて有効」を切り替えて非優先ノーツに `is_muted` を付与。
  2. **3階層運指解決システム**:
     * Layer 1（最優先）: ユーザーが画面クリックやエディタで設定した個別オーバーライド（`(tick, pitch) -> candidate_idx`）
     * Layer 2（中優先）: 曲全体の運指プリセット（スライド最小化、吹吸統一等）
     * Layer 3（基底）: 楽器モデル基本運指テーブル

---

### 4-5. マルチトラック合成とYouTubeラウドネス規格（ITU-R BS.1770）
* **起きた事実・現象**:
  * 「外部伴奏 ＋ マイク録音 ＋ MIDIシンセ音」を重ねて動画出力すると、合計振幅が 1.0（0 dBFS）を超えて激しいデジタルクリッピング（バリバリという音割れ）が発生した。
* **解決策**:
  * 3層マルチトラック・ミキサーダイアログ（[`AudioTrackMixerDialog`](file:///c:/Users/j28k1/Desktop/harmonica-visualizer/v3.0/dialogs.py)）を新設。
  * 合成後に ITU-R BS.1770 準拠のラウドネス解析（目標 `-14.0 LUFS`）を行い、True Peak を `-1.0 dBFS`（振幅上限 `0.891`）にクランプするソフトニーリミッターを最終段に適用。音割れのない高音質出力を担保した。

---

## 5. 次世代プロジェクトへの黄金律チェックリスト

1. **[防衛的UI]** 固定幅パネルには `setMaximumWidth()`、コンボボックスの最小幅制限、ラベルの `ElideMiddle`、ラベルとボタンの2行分離をDay 1から適用せよ。
2. **[スコープ衛生]** Pythonの関数内インライン `import` はスコープ競合（`UnboundLocalError`）の原因となるため全廃し、トップレベルに集約せよ。
3. **[シグナル保護]** UIウィジェットにプログラムから値を設定する際は、必ず `blockSignals(True)` と `_is_loading` フラグでハンドラの連鎖発火を防げ。
4. **[クロック統一]** リアルタイム再生と動画書き出しの音声・映像オフセット計算は、同一の数式とロジックを共有せよ。
5. **[PCMスライス]** ミリ秒精度の頭出し・同期が必要な音声は、ストリーミング再生ではなくメモリ展開したPCM配列のスライス再生を行え。
6. **[録音正規化]** 前奏（カウントイン）付き録音は、停止時に前奏分のバイト数を切り落として常に「楽曲本編0.0秒」に正規化せよ。
7. **[真の解像度]** 縦型や4:3動画を出力する際、黒帯付きの横長動画にせず、アスペクト比に応じた真の縦横ピクセル数をエンコーダに渡せ。
8. **[段階的検証]** 複合的なバグ改修はコードを書く前に全体設計を行い、1ステップごとに自動テストとGitコミットを実施せよ。
9. **[ビルド同期]** Pythonソースコードの修正状態と、PyInstallerによる配布用EXEのビルド状態を常に区別・一致させよ。


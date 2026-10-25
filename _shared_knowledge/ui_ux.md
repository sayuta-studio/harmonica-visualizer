# UI/UX 共通知見・落とし穴（Gotchas）

> **記録指針**: 一般的なUIデザイン原則ではなく、「実装時にAIや人間が踏み抜きやすい罠・ライブラリの癖・回避策」を簡潔に追記してください。

## 蓄積された知見

### 1. 可変長文字列（長いファイル名等）によるパネル幅溢れとボタン押し出し
- **落とし穴 (Gotcha)**:
  - `QLabel` に `setWordWrap(True)` を設定しても、空白区切りのない文字列（アンダースコア `_`、ハイフン、日本語連続等）は折り返されず、最小幅（`minimumSizeHint`）が数百ピクセルまで肥大化する。
  - `QComboBox` のデフォルト挙動（`AdjustToContents`）により、最も長い選択肢に合わせて幅が自動拡張される。
  - `QHBoxLayout` で `[QLabel] [QPushButton]` を1行に並べると、ラベル肥大化によりボタンが画面外に押し出される。
- **回避策・ベストプラクティス**:
  - **コンテナ上限**: スクロールエリア内コンテナやグループ枠に明示的な最大幅（`setMaximumWidth(...)`）を設定する。
  - **中央省略（ElideMiddle）**: `QFontMetrics.elidedText(..., Qt.TextElideMode.ElideMiddle, max_width)` で中央を `...` 省略し、完全な文字列は `setToolTip()` に退避する。
  - **コンボボックス設定**: `setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)` を指定し、`setMinimumContentsLength(8)` などで幅上限を抑制する。
  - **上下2段分離**: 可変長テキストラベルと操作ボタン群を同一行に並べず、1段目をラベル、2段目をボタン列（`QHBoxLayout`）に分ける。
  - **スピンボックス固定幅**: 文字数＋矢印ボタン幅を考慮し、`setFixedWidth(90)` 等を明示して末尾文字切れを防ぐ。

### 2. UI初期化・設定復元時の「シグナル暴発（Signal Storm）」によるデータ上書き
- **落とし穴 (Gotcha)**:
  - プログラム側から `spin.setValue(val)` や `combo.setCurrentText(...)` を呼ぶと、Qtの `valueChanged` や `currentTextChanged` が同期的に発火する。
  - その結果、初期化・ロード途中の不完全なUI値で設定保存ハンドラが実行され、ユーザーの保存データやプロファイルが初期値で上書き破壊される。
- **回避策・ベストプラクティス**:
  - **シグナル一時ブロック**: 値代入の直前直後で `widget.blockSignals(True)` / `widget.blockSignals(False)` を行う。
  - **ロード中フラグの二重防御**:
    ```python
    self._is_loading = True
    try:
        # UIウィジェットへの一括データ流し込み
        self.spin.blockSignals(True)
        self.spin.setValue(saved_val)
        self.spin.blockSignals(False)
    finally:
        self._is_loading = False

    # 各イベントハンドラ側でガード
    def _on_value_changed(self):
        if getattr(self, "_is_loading", False):
            return
        self._save_settings()
    ```

### 3. OpenGLウィジェット描画とQtイベントループのタイミング競合
- **落とし穴 (Gotcha)**:
  - `QOpenGLWidget` の描画サイクル（`paintGL`）とタイマー駆動のクロック更新が非同期になり、シークや停止操作時に1フレーム遅れやチラつきが発生する。
- **回避策・ベストプラクティス**:
  - シーク操作やデータ編集直後に `self.gl_widget.update()` を明示的に呼び出し、一時停止中であっても現在位置に基づく強制フレーム描画を実行する。

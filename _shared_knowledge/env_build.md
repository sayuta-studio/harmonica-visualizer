# 環境構築・パッケージング・OS起因の知見（Gotchas）

> **記録指針**: インストール手順の丸写しではなく、「ビルドエラー、パスの差異、依存関係の衝突、実行環境の癖」とその解決策を記録してください。

## 蓄積された知見

### 1. PyInstaller EXEビルドとPythonソースコードの非同期ギャップ
- **落とし穴 (Gotcha)**:
  - Pythonソースコード（`.py`）で修正を完了して単体テストがパスしていても、PyInstallerでビルドされた配布用EXE（`dist/` 配下等）は自動更新されない。
  - その結果、開発者が「修正完了」と認識している一方、ユーザーが旧ビルドのEXEを実行して「直っていない」とすれ違いが発生する。
- **回避策・ベストプラクティス**:
  - 作業フェーズを「①Pythonコード改修・単体テスト」と「②配布パッケージEXEビルド・統合検証」に厳密に分離し、EXEビルド完了まで「ソースのみ改修完了」と明示する。
  - アプリのタイトルバーやログ出力にビルド日時・Gitコミットハッシュを表示し、実行中のバイナリ世代を一目で判別可能にする。

### 2. Windows PowerShellにおける標準出力の `cp932`（Shift-JIS）例外
- **落とし穴 (Gotcha)**:
  - 日本語WindowsのPowerShell環境下でテストスクリプトやCLIを実行すると、stdoutのデフォルトエンコーディングが `cp932` になる。
  - 絵文字（`🎵`, `🎼`, `❌`, `▶` 等）や特殊文字を `print()` した瞬間に `UnicodeEncodeError: 'cp932' codec can't encode character...` でプロセスがクラッシュする。
- **回避策・ベストプラクティス**:
  - Pythonスクリプトの冒頭で標準出力のエンコーディングを UTF-8 に再設定する：
    ```python
    import sys
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ```

### 3. 外部バイナリ（FFmpeg等）およびリソースのPyInstallerポータブルパス解決
- **落とし穴 (Gotcha)**:
  - PyInstallerで単一EXEやディレクトリパッケージ化（frozen環境）した場合、開発環境の `__file__` 基準相対パスやカレントディレクトリ依存のコードは、配布先で外部バイナリ（`ffmpeg.exe` 等）や設定ファイルを見失いクラッシュする。
- **回避策・ベストプラクティス**:
  - `sys.frozen` を判定してベースディレクトリを切り替える共通ヘルパーを定義する：
    ```python
    import sys
    import os

    def get_portable_path(rel_path: str) -> str:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(base, rel_path))
    ```
  - 外部ツール呼び出しは、同梱パス（例: `ffmpeg/bin/ffmpeg.exe`）を最優先探索し、存在しない場合はシステムPATH（`shutil.which` 等）へ透過的にフォールバックする。

### 4. Windowsの「コントロールされたフォルダー アクセス」によるディレクトリ作成遮断
- **落とし穴 (Gotcha)**:
  - `C:\Users\<User>\Documents` 直下などで開発を行う際、Windows Defenderの「コントロールされたフォルダー アクセス（ランサムウェア保護）」が有効だと、`git.exe` や `powershell.exe`、`python.exe` などの子プロセスからのフォルダ作成（`git init` や `os.mkdir`）が `WinError 2 (FileNotFoundError)` やアクセス拒否で阻まれる。
- **回避策・ベストプラクティス**:
  - 開発ワークスペースは保護対象の `Documents` 直下を避け、`C:\Dev\` やユーザーホーム直下など保護対象外のパスに配置する。
  - もしくは Windows セキュリティの「ランサムウェアの防止」設定から、使用するCLI・ツールを「アプリをコントロールされたフォルダー アクセスで許可する」に追加する。

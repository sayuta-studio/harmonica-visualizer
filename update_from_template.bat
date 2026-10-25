@echo off
chcp 65001 > nul
echo ====================================================
echo  00_template から最新規約・共有知見を取り込みます
echo ====================================================

set TEMPLATE_DIR=..\00_template

if not exist "%TEMPLATE_DIR%" (
    echo [エラー] 親フォルダに 00_template が見つかりません。
    echo フォルダの階層構造（親フォルダに 00_template があるか）を確認してください。
    pause
    exit /b
)

echo [1/3] 共有知見（_shared_knowledge）を同期中...
if exist "%TEMPLATE_DIR%\_shared_knowledge" (
    xcopy /E /I /Y "%TEMPLATE_DIR%\_shared_knowledge" ".\_shared_knowledge" > nul
    echo 完了: _shared_knowledge
)

echo [2/3] エージェント規約（.agent）を同期中...
if exist "%TEMPLATE_DIR%\.agent" (
    xcopy /E /I /Y "%TEMPLATE_DIR%\.agent" ".\.agent" > nul
    echo 完了: .agent
)

echo [3/3] AGENTS.md を同期中...
if exist "%TEMPLATE_DIR%\AGENTS.md" (
    copy /Y "%TEMPLATE_DIR%\AGENTS.md" ".\AGENTS.md" > nul
    echo 完了: AGENTS.md
)

echo.
echo 最新テンプレート規約の同期が完了しました。
echo.
pause

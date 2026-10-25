@echo off
chcp 65001 > nul
echo ====================================================
echo  共有知見を 00_template へ同期・還元します
echo ====================================================

set TARGET_INBOX=..\00_template\_shared_knowledge\inbox
set CURRENT_DIR=.\_shared_knowledge

if not exist "%TARGET_INBOX%" (
    echo [エラー] 00_template\_shared_knowledge\inbox が見つかりません。
    echo フォルダの階層構造（親フォルダに 00_template があるか）を確認してください。
    pause
    exit /b
)

set /p PROJ_NAME="プロジェクト識別名（英数字、例: p01_harmonica）を入力してください: "

if "%PROJ_NAME%"=="" (
    echo [エラー] プロジェクト名が入力されませんでした。処理を中断します。
    pause
    exit /b
)

for %%f in ("%CURRENT_DIR%\*.md") do (
    copy /Y "%%f" "%TARGET_INBOX%\from_%PROJ_NAME%_%%~nxf" > nul
    echo コピー完了: %%~nxf -^> %TARGET_INBOX%\from_%PROJ_NAME%_%%~nxf
)

echo.
echo すべての共有知見を 00_template\_shared_knowledge\inbox に安全に転送しました。
echo ※ 既存の 00_template のファイルは上書きされていません。
echo.
pause

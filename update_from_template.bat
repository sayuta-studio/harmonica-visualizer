@echo off
chcp 65001 > nul
echo ====================================================
echo  00_template から最新のルールと共通知見を取得します
echo ====================================================

set TEMPLATE_DIR=..\00_template

if not exist "%TEMPLATE_DIR%" (
    echo [エラー] 親階層に 00_template が見つかりません。
    echo フォルダの配置を確認してください。
    pause
    exit /b
)

echo.
echo [1/2] 最新のルール (.agent/rules/) を更新中...
if exist "%TEMPLATE_DIR%\.agent\rules" (
    xcopy /Y /E /I "%TEMPLATE_DIR%\.agent\rules" ".\.agent\rules\" > nul
    echo  - ルールの更新が完了しました。
)

echo.
echo [2/2] 最新の共通知見 (_shared_knowledge/) を更新中...
if exist "%TEMPLATE_DIR%\_shared_knowledge" (
    for %%f in ("%TEMPLATE_DIR%\_shared_knowledge\*.md") do (
        copy /Y "%%f" ".\_shared_knowledge\" > nul
    )
    echo  - 共通知見の更新が完了しました。
)

echo.
echo ====================================================
echo  更新が正常に完了しました！
echo  ※ プロジェクト固有の .context やコードは保護されています。
echo ====================================================
pause


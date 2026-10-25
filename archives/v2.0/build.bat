@echo off
echo ====================================================================
echo  Chromatic Harmonica Visualizer ^& Trainer - EXE Build Script
echo ====================================================================

rem 1. Clean up old build files
echo [1/3] Cleaning up old build files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "Chromatic_Harmonica_Trainer.spec" del /q "Chromatic_Harmonica_Trainer.spec"
echo Clean up completed.

rem 2. Run PyInstaller via Python module call with automatic customtkinter collection
echo.
echo [2/3] Bundling and packaging with PyInstaller...
echo (This may take a minute, please wait...)

rem 🚀【解決】：--add-data から --collect-all customtkinter に切り替え！
rem これによりローカルにフォルダがなくても、site-packagesから全データを安全に自動収集・同梱します。
python -m PyInstaller --clean --onefile --noconsole --name="Chromatic_Harmonica_Trainer" --collect-all customtkinter main.py

rem 3. Build result verification
echo.
echo --------------------------------------------------------------------
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] 'dist/Chromatic_Harmonica_Trainer.exe' has been generated!
    echo It runs in standalone mode. 
    echo Feel free to distribute it now.
) else (
    echo [ERROR] Packaging failed.
    echo Please make sure PyInstaller is installed correctly in python.
    echo You can try to run: pip install pyinstaller
)
echo --------------------------------------------------------------------
echo.
pause
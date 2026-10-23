@echo off
echo ====================================================================
echo  Chromatic Harmonica Visualizer ^& Trainer v3.0 - EXE Build Script
echo ====================================================================

rem 1. Clean up old build files safely
echo [1/3] Preparing build environment...
if exist "Chromatic_Harmonica_Trainer.spec" ren "Chromatic_Harmonica_Trainer.spec" "Chromatic_Harmonica_Trainer.spec.bak"

rem 2. Run PyInstaller with PyQt6 and pygame audio backends
echo.
echo [2/3] Bundling and packaging with PyInstaller...
echo (This may take a couple of minutes, please wait...)

python -m PyInstaller --clean --onefile --noconsole --name="Chromatic_Harmonica_Trainer" --hidden-import=pygame._sdl2.audio --hidden-import=PyQt6.QtOpenGLWidgets --exclude-module=matplotlib --exclude-module=scipy --exclude-module=unittest --exclude-module=customtkinter main.py

rem 3. Build result verification
echo.
echo --------------------------------------------------------------------
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] 'dist/Chromatic_Harmonica_Trainer.exe' has been generated!
    echo It runs in standalone mode with full PyQt6 / OpenGL acceleration.
    echo Feel free to distribute it now.
) else (
    echo [ERROR] Packaging failed.
    echo Please make sure PyInstaller and dependencies are installed.
)
echo --------------------------------------------------------------------
echo.
pause


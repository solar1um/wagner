@echo off
echo ============================================
echo   Wagner Windows Build Script
echo ============================================
echo.

cd /d "%~dp0"

echo [1/4] Creating virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create venv. Is Python installed?
    pause
    exit /b 1
)

echo [2/4] Installing dependencies...
call .venv\Scripts\activate
pip install --upgrade pip --quiet
pip install git+https://github.com/philippkosarev/acd.git flask pywebview pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo [3/4] Building Wagner.exe...
python build.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo [4/4] Done!
echo.
echo Executable: dist\Wagner.exe
echo.
echo First run will offer to register right-click menu.
echo Copy Wagner.exe anywhere you want - it's portable.
echo.
pause

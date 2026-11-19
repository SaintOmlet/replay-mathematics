@echo off
setlocal
cd /d "%~dp0"
py -3 -B -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    py -3 -B -m backend.server --open-browser %*
    if errorlevel 1 pause
    exit /b
)
python -B -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    python -B -m backend.server --open-browser %*
    if errorlevel 1 pause
    exit /b
)
echo Python 3.10 or newer is required.
echo Install it from https://www.python.org/downloads/ then run Start.bat again.
pause
exit /b 1

@echo off
cd /d "%~dp0"
echo Starting preloader...
echo.
python data\preloader.py
echo.
echo Done. Press any key to exit.
pause >nul

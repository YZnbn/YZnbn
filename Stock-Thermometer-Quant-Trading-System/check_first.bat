@echo off
cd /d "%~dp0"
python check_env.py > check_result.txt 2>&1
type check_result.txt
pause

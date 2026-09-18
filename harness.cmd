@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0scripts\cli\harness.py" %*
) else (
    py -3 "%~dp0scripts\cli\harness.py" %*
)
exit /b %ERRORLEVEL%

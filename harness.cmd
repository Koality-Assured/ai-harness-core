@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if "%1"=="video" goto run_python
if "%1"=="prompt" goto run_python

where harness.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    harness.exe %*
    exit /b %ERRORLEVEL%
)

:run_python

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%~dp0scripts\cli\harness.py" %*
) else (
    py -3 "%~dp0scripts\cli\harness.py" %*
)
exit /b %ERRORLEVEL%

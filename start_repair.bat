@echo off
setlocal enabledelayedexpansion
title POS Auto-Repair Assistant Daemon
set "PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

cd /d "%~dp0"

:: Auto-detect Python executable
set "PY_CMD="
if exist "%USERPROFILE%\.local\bin\python3.14.exe" (
    set "PY_CMD=%USERPROFILE%\.local\bin\python3.14.exe"
    goto :found_python
)
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto :found_python
)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py"
    goto :found_python
)
where python3.14 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python3.14"
    goto :found_python
)

:found_python
if "%PY_CMD%"=="" (
    echo [ERROR] Python was not found on your system!
    pause
    exit /b 1
)

echo ======================================================================
echo          POS AUTO-REPAIR DAEMON - HUMAN TYPING SIMULATOR
echo ======================================================================
echo  Trigger Hotkey : [Ctrl] + [Keypad *]
echo  Target File    : pos_system.py
echo ======================================================================
echo.

"%PY_CMD%" src\auto_repair.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Daemon stopped.
    pause
)

@echo off
setlocal enabledelayedexpansion
title Modern Retail POS Terminal

:: Guarantee standard Windows system utilities are in PATH
set "PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

echo ======================================================================
echo             PHILIPPINE RETAIL POS TERMINAL - ONE CLICK LAUNCHER
echo ======================================================================
echo.

:: Ensure current working directory is the folder where this batch script lives
cd /d "%~dp0"

:: 1. Auto-detect Python executable
set "PY_CMD="

:: Check user local bin Python first
if exist "%USERPROFILE%\.local\bin\python3.14.exe" (
    set "PY_CMD=%USERPROFILE%\.local\bin\python3.14.exe"
    goto :found_python
)

:: Check standard python command in PATH
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto :found_python
)

:: Check Windows Python Launcher (py)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py"
    goto :found_python
)

:: Check python3.14 in PATH
where python3.14 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python3.14"
    goto :found_python
)

:: Check standard AppData Python installations
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto :found_python
    )
)

:: Check Program Files Python installations
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto :found_python
    )
)

:: Check uv package runner
where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=uv run python"
    goto :found_python
)

:found_python
if "%PY_CMD%"=="" (
    echo [ERROR] Python was not found on your system!
    echo Please install Python 3.10+ from https://www.python.org/
    echo or make sure python.exe is added to your PATH environment variable.
    echo.
    pause
    exit /b 1
)

echo [*] Detected Python Engine : %PY_CMD%
echo [*] System Directory       : %~dp0
echo [*] Launching Server on     : http://localhost:8000
echo.

:: Automatically open default browser after a brief 1-second pause in background
start "" cmd /c "timeout /t 1 /nobreak >nul & start http://localhost:8000"

echo ======================================================================
echo   POS Terminal is LIVE!
echo   Main POS Register : http://localhost:8000/
echo   Barcode Test Sheet: http://localhost:8000/barcodes.html
echo.
echo   Press [CTRL + C] in this window anytime to stop the server.
echo ======================================================================
echo.

:: Run POS Server with Watchdog Auto-Recovery
:server_loop
if exist "src\server.py" (
    "%PY_CMD%" src\server.py 8000
) else (
    "%PY_CMD%" server.py 8000
)

set "EXIT_CODE=%ERRORLEVEL%"
if %EXIT_CODE% equ 0 goto :clean_exit
if %EXIT_CODE% equ 130 goto :clean_exit

echo.
echo [!] Server exited with status code %EXIT_CODE%.
echo [*] Watchdog auto-restarting POS server and stealth daemon in 3 seconds...
echo     (Press CTRL+C anytime in this window to stop)
timeout /t 3 /nobreak >nul
goto :server_loop

:clean_exit
echo.
echo [*] POS Server exited cleanly.

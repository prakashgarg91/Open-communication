@echo off
chcp 65001 >nul 2>&1
title Vakya Control Center — AI-to-AI Communication Bridge
color 0F

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   Vakya Control Center v2.0                               ║
echo  ║   Live AI APIs + Cross-IDE + Multi-Model Chat             ║
echo  ║   OpenAI / Anthropic / Ollama / Gemini                    ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Check if .venv exists
if not exist ".venv\Scripts\python.exe" (
    echo  [!] Virtual environment not found. Setting up...
    echo.
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -e . >nul 2>&1
    echo  [OK] Environment ready.
) else (
    call .venv\Scripts\activate.bat
)

echo  Starting Vakya Control Center...
echo  ─────────────────────────────────────────────────────────
echo.

:: Check command line args
set ARGS=
if "%1"=="--demo"  set ARGS=--demo
if "%1"=="demo"    set ARGS=--demo
if "%1"=="--auto"  set ARGS=--auto
if "%1"=="auto"    set ARGS=--auto
if "%2"=="--demo"  set ARGS=%ARGS% --demo
if "%2"=="--auto"  set ARGS=%ARGS% --auto
if "%1"=="--port"  set ARGS=%ARGS% --port %2

:: Run the control center
.venv\Scripts\python.exe vakya_control.py %ARGS%

echo.
echo  Vakya Control Center stopped. Namaste!
pause

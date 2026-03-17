@echo off
REM ============================================================================
REM dev.bat — Start/stop/restart the SDLC Dashboard dev servers
REM
REM Usage (CMD or PowerShell):
REM   scripts\dev.bat          — restart (stop + start)
REM   scripts\dev.bat start    — start only
REM   scripts\dev.bat stop     — stop only
REM   scripts\dev.bat status   — check if running
REM ============================================================================

setlocal enabledelayedexpansion

set ROOT=%~dp0..
set BACKEND_PORT=8001
set FRONTEND_PORT=4200
set BACKEND_LOG=%ROOT%\logs\backend-dev.log
set FRONTEND_LOG=%ROOT%\logs\frontend-dev.log

if "%~1"=="" goto restart
if "%~1"=="start" goto start
if "%~1"=="stop" goto stop
if "%~1"=="restart" goto restart
if "%~1"=="status" goto status
echo Usage: %~nx0 {start^|stop^|restart^|status}
exit /b 1

REM ── STOP ───────────────────────────────────────────────────────────────────
:stop
echo Stopping dev servers...
call :kill_port %BACKEND_PORT%
call :kill_port %FRONTEND_PORT%
REM Brute force fallback
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Stopped.
goto :eof

REM ── START ──────────────────────────────────────────────────────────────────
:start
echo Starting dev servers...
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

REM Check ports
call :check_port %BACKEND_PORT%
if !errorlevel! equ 0 (
    echo Port %BACKEND_PORT% in use — stopping first...
    call :kill_port %BACKEND_PORT%
    timeout /t 2 /nobreak >nul
)
call :check_port %FRONTEND_PORT%
if !errorlevel! equ 0 (
    echo Port %FRONTEND_PORT% in use — stopping first...
    call :kill_port %FRONTEND_PORT%
    timeout /t 2 /nobreak >nul
)

REM Find Python
set PYTHON=python
if exist "%ROOT%\.venv\Scripts\python.exe" set PYTHON=%ROOT%\.venv\Scripts\python.exe

REM Start backend
echo   Starting backend...
start /B "" "%PYTHON%" -m uvicorn ui.backend.main:app --host 127.0.0.1 --port %BACKEND_PORT% --reload > "%BACKEND_LOG%" 2>&1

REM Start frontend
echo   Starting frontend...
pushd "%ROOT%\ui\frontend"
start /B "" npm start > "%FRONTEND_LOG%" 2>&1
popd

REM Wait for backend
echo   Waiting for servers...
call :wait_port %BACKEND_PORT% Backend 30
call :wait_port %FRONTEND_PORT% Frontend 30

echo.
echo Dev servers running:
echo   Frontend:  http://localhost:%FRONTEND_PORT%
echo   Backend:   http://localhost:%BACKEND_PORT%
echo   Logs:      %BACKEND_LOG%
echo              %FRONTEND_LOG%
goto :eof

REM ── RESTART ────────────────────────────────────────────────────────────────
:restart
call :stop
call :start
goto :eof

REM ── STATUS ─────────────────────────────────────────────────────────────────
:status
echo Dev server status:
call :check_port %BACKEND_PORT%
if !errorlevel! equ 0 (
    echo   Backend:  RUNNING on :%BACKEND_PORT%
) else (
    echo   Backend:  NOT RUNNING
)
call :check_port %FRONTEND_PORT%
if !errorlevel! equ 0 (
    echo   Frontend: RUNNING on :%FRONTEND_PORT%
) else (
    echo   Frontend: NOT RUNNING
)
goto :eof

REM ── HELPERS ────────────────────────────────────────────────────────────────

:kill_port
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%~1" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   Killed PID %%a on port %~1
)
exit /b 0

:check_port
netstat -ano 2>nul | findstr ":%~1" | findstr "LISTENING" >nul 2>&1
exit /b %errorlevel%

:wait_port
set _port=%~1
set _label=%~2
set _max=%~3
set _i=0
:wait_loop
if !_i! geq !_max! (
    echo   %_label% failed to start on :%_port%
    exit /b 1
)
netstat -ano 2>nul | findstr ":%_port%" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo   %_label% ready on :%_port%
    exit /b 0
)
timeout /t 1 /nobreak >nul
set /a _i+=1
goto wait_loop

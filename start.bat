@echo off
REM =============================================================================
REM SDLC Pilot - One-Click Start (Docker) for Windows CMD/PowerShell
REM
REM Usage:
REM   start.bat                    start Dashboard
REM   start.bat stop               stop Dashboard
REM   start.bat logs               show logs
REM =============================================================================

REM Ins Verzeichnis der start.bat wechseln (wichtig bei Doppelklick)
cd /d "%~dp0"

set COMPOSE_FILE=ui/docker-compose.ui.yml

if "%1"=="stop" (
    echo Stopping SDLC Pilot...
    docker compose -f %COMPOSE_FILE% down
    echo [OK] Dashboard stopped.
    exit /b 0
)

if "%1"=="logs" (
    docker compose -f %COMPOSE_FILE% logs -f
    exit /b 0
)

echo.
echo =========================================
echo   SDLC Pilot - Dashboard Startup
echo =========================================
echo.

REM Check Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo         Please start Docker Desktop first.
    exit /b 1
)
echo [OK] Docker is running.

REM Check .env
if not exist ".env" (
    copy .env.example .env >nul
    echo [!] .env created from template.
    echo.
    echo     Please edit .env and set your API key:
    echo       OPENAI_API_KEY=sk-your-actual-key
    echo.
    echo     Then run start.bat again.
    exit /b 1
)

findstr /C:"sk-your-api-key-here" .env >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] API key not configured!
    echo.
    echo   Open .env in a text editor and replace:
    echo     OPENAI_API_KEY=sk-your-api-key-here
    echo   with your actual API key.
    echo.
    echo   Then run start.bat again.
    exit /b 1
)

echo [OK] .env configured.

REM Create directories
if not exist knowledge mkdir knowledge
if not exist logs mkdir logs
if not exist reports mkdir reports

echo.
echo Building and starting Dashboard...
echo (First time takes 2-3 minutes)
echo.

docker compose -f %COMPOSE_FILE% up --build -d

echo.
echo =========================================
echo   Dashboard is ready!
echo.
echo   Open: http://localhost
echo.
echo   Backend API: http://localhost:8001/api/health
echo =========================================
echo.
echo Commands:
echo   start.bat logs     Show live logs
echo   start.bat stop     Stop the Dashboard
echo.
pause

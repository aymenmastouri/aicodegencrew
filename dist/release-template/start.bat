@echo off
REM =============================================================================
REM SDLC Pilot - One-Click Dashboard Launcher
REM
REM Usage:
REM   start.bat              Start the dashboard
REM   start.bat stop         Stop the dashboard
REM   start.bat logs         Show live logs
REM =============================================================================

REM Change to the directory where this script lives
cd /d "%~dp0"

echo.
echo =========================================
echo   SDLC Pilot - Dashboard
echo =========================================
echo.

if "%1"=="stop" (
    docker compose down
    echo [OK] Dashboard stopped.
    pause
    exit /b 0
)

if "%1"=="logs" (
    docker compose logs -f
    exit /b 0
)

REM --- Pre-flight checks ---

REM 1. Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo.
    echo   Please start Docker Desktop and wait until the icon
    echo   appears in your system tray, then run start.bat again.
    echo.
    pause
    exit /b 1
)
echo [OK] Docker is running.

REM 2. Environment file
if not exist ".env" (
    copy .env.example .env >nul
    echo [!] .env file created from template.
    echo.
    echo   Please open .env with a text editor and configure:
    echo     PROJECT_PATH=C:\path\to\your\repo
    echo     OPENAI_API_KEY=sk-your-actual-key
    echo.
    echo   Then run start.bat again.
    echo.
    pause
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
    echo.
    pause
    exit /b 1
)
echo [OK] API key configured.

findstr /C:"path\to\your\repo" .env >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] Repository path not configured!
    echo.
    echo   Open .env and set PROJECT_PATH to your repository, e.g.:
    echo     PROJECT_PATH=C:\projects\myapp
    echo.
    echo   Then run start.bat again.
    echo.
    pause
    exit /b 1
)
echo [OK] Repository path configured.

REM 3. Create data directories
if not exist knowledge mkdir knowledge
if not exist logs mkdir logs
if not exist inputs mkdir inputs
if not exist config mkdir config

REM 4. Load Docker images on first run
docker image inspect sdlc-pilot/backend:latest >nul 2>&1
if errorlevel 1 (
    echo.
    echo Loading Docker images -- this only happens once, ~1-2 minutes...
    docker load -i sdlc-pilot-backend.tar.gz
    docker load -i sdlc-pilot-frontend.tar.gz
    echo [OK] Images loaded.
)

REM --- Start ---
echo.
echo Starting dashboard...
docker compose up -d

echo.
echo =========================================
echo.
echo   Dashboard is ready!
echo.
echo   Open in browser: http://localhost
echo.
echo =========================================
echo.
echo   start.bat stop    Stop the dashboard
echo   start.bat logs    Show live logs
echo.
pause

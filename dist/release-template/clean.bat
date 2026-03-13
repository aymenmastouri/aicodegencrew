@echo off
REM =============================================================================
REM SDLC Pilot - Full Cleanup
REM Stops containers, removes named volumes, deletes Docker images.
REM Preserved: .env, .env.example, config/ (contains release config files).
REM =============================================================================

cd /d "%~dp0"

echo.
echo =========================================
echo   SDLC Pilot - Full Cleanup
echo =========================================
echo.

REM Detect docker compose command
set DC=
docker compose version >nul 2>&1
if not errorlevel 1 (
    set DC=docker compose
) else (
    docker-compose version >nul 2>&1
    if not errorlevel 1 (
        set DC=docker-compose
    ) else (
        echo [ERROR] Docker not found.
        exit /b 1
    )
)

REM 1. Stop containers and remove named volumes
echo [1/2] Stopping containers and removing volumes...
%DC% down -v --remove-orphans 2>nul
echo [OK] Containers and volumes removed.

REM 2. Remove Docker images
echo [2/2] Removing Docker images...
docker rmi sdlc-pilot/backend:latest 2>nul
docker rmi sdlc-pilot/frontend:latest 2>nul
echo [OK] Images removed.

echo.
echo =========================================
echo.
echo   Cleanup complete!
echo.
echo   Your .env, .env.example, and config/ are preserved.
echo   To reinstall, run start.bat again.
echo.
echo =========================================
echo.
pause

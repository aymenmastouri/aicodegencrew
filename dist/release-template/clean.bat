@echo off
REM =============================================================================
REM SDLC Pilot - Full Cleanup
REM Stops containers, removes volumes, deletes Docker images,
REM and wipes runtime data directories (knowledge, logs, inputs, reports).
REM Preserved: .env, .env.example, config/ (contains release config files).
REM =============================================================================

cd /d "%~dp0"

echo.
echo =========================================
echo   SDLC Pilot - Full Cleanup
echo =========================================
echo.

REM 1. Clean data directories via container (handles file ownership)
echo [1/4] Cleaning data directories via container...
docker exec sdlc-pilot-backend rm -rf /app/knowledge/* /app/logs/* /app/inputs/* 2>nul
echo [OK] Data cleaned.

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

REM 2. Stop containers, remove volumes and networks
echo [2/4] Stopping containers...
%DC% down -v --remove-orphans 2>nul
docker rm -f sdlc-pilot-backend sdlc-pilot-frontend 2>nul
echo [OK] Containers and volumes removed.

REM 3. Remove Docker images
echo [3/4] Removing Docker images...
docker rmi sdlc-pilot/backend:latest 2>nul
docker rmi sdlc-pilot/frontend:latest 2>nul
echo [OK] Images removed.

REM 4. Remove runtime data directories (config/ is preserved)
echo [4/4] Removing data directories...
if exist knowledge rmdir /s /q knowledge
if exist logs rmdir /s /q logs
if exist inputs rmdir /s /q inputs
if exist reports rmdir /s /q reports
echo [OK] Data directories removed.

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

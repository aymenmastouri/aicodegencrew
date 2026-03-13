@echo off
REM =============================================================================
REM SDLC Pilot - Full Cleanup
REM Stops containers, removes volumes, deletes Docker images,
REM and wipes ALL data directories (knowledge, logs, inputs, config, reports).
REM Only .env and .env.example are preserved.
REM =============================================================================

cd /d "%~dp0"

echo.
echo =========================================
echo   SDLC Pilot - Full Cleanup
echo =========================================
echo.

REM 1. Clean data directories via container (handles file ownership)
echo [1/4] Cleaning data directories via container...
docker exec sdlc-pilot-backend rm -rf /app/knowledge/* /app/logs/* /app/inputs/* /app/config/* 2>nul
echo [OK] Data cleaned.

REM 2. Stop containers and remove volumes
echo [2/4] Stopping containers...
docker compose down -v 2>nul
echo [OK] Containers stopped.

REM 3. Remove Docker images
echo [3/4] Removing Docker images...
docker rmi sdlc-pilot/backend:latest 2>nul
docker rmi sdlc-pilot/frontend:latest 2>nul
echo [OK] Images removed.

REM 4. Remove data directories
echo [4/4] Removing data directories...
if exist knowledge rmdir /s /q knowledge
if exist logs rmdir /s /q logs
if exist inputs rmdir /s /q inputs
if exist config rmdir /s /q config
if exist reports rmdir /s /q reports
echo [OK] Data directories removed.

echo.
echo =========================================
echo.
echo   Cleanup complete!
echo.
echo   Your .env and .env.example are preserved.
echo   To reinstall, run start.bat again.
echo.
echo =========================================
echo.
pause

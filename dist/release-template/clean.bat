@echo off
REM =============================================================================
REM SDLC Pilot - Full Cleanup
REM Stops containers, removes volumes, and deletes Docker images.
REM Your .env and uploaded files are NOT deleted.
REM =============================================================================

cd /d "%~dp0"

echo.
echo =========================================
echo   SDLC Pilot - Full Cleanup
echo =========================================
echo.

REM 1. Stop containers and remove volumes
echo [1/3] Stopping containers...
docker compose down -v 2>nul
echo [OK] Containers stopped.

REM 2. Remove Docker images
echo [2/3] Removing Docker images...
docker rmi sdlc-pilot/backend:latest 2>nul
docker rmi sdlc-pilot/frontend:latest 2>nul
echo [OK] Images removed.

REM 3. Clean up data directories
echo [3/3] Cleaning data directories...
if exist knowledge rmdir /s /q knowledge
if exist logs rmdir /s /q logs
if exist inputs rmdir /s /q inputs
if exist config rmdir /s /q config
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

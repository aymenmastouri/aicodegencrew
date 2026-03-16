@echo off
REM ============================================================================
REM setup-windows.bat — Complete SDLC Pilot Setup for Windows
REM
REM The manager receives ONLY this file and runs it with a double-click.
REM Everything else happens automatically: Git, Python, Node.js, repo, dashboard.
REM
REM IMPORTANT: Right-click > Run as Administrator
REM ============================================================================

REM --- Check for admin rights ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Please run as Administrator!
    echo   Right-click on setup-windows.bat ^> "Run as administrator"
    echo.
    pause
    exit /b 1
)

REM --- Run the PowerShell script with execution policy bypass ---
powershell -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1" %*

if %errorlevel% neq 0 (
    echo.
    echo   Setup failed. Please read the output above.
    echo.
    pause
    exit /b 1
)

pause

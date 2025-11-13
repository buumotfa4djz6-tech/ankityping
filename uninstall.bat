@echo off
echo AnkiTyping Plugin Uninstallation Script
echo ======================================
echo.

rem Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

rem Run the package uninstallation
python package.py uninstall %*

if errorlevel 1 (
    echo.
    echo Uninstallation failed. Please check the error messages above.
    pause
    exit /b 1
) else (
    echo.
    echo Uninstallation completed successfully!
    echo Please restart Anki to complete removal.
    pause
)
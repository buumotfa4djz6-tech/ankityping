@echo off
echo AnkiTyping Plugin Installation Script
echo =====================================
echo.

rem Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher first
    pause
    exit /b 1
)

rem Run the package installation
python package.py install %*

if errorlevel 1 (
    echo.
    echo Installation failed. Please check the error messages above.
    pause
    exit /b 1
) else (
    echo.
    echo Installation completed successfully!
    echo Please restart Anki to load the plugin.
    pause
)
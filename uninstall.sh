#!/bin/bash

# AnkiTyping Plugin Uninstallation Script
# =======================================

set -e

echo "AnkiTyping Plugin Uninstallation Script"
echo "======================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH"
    exit 1
fi

# Use python3 if available, otherwise python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "Using Python: $($PYTHON_CMD --version)"
echo

# Run the package uninstallation
$PYTHON_CMD package.py uninstall "$@"

if [ $? -eq 0 ]; then
    echo
    echo "Uninstallation completed successfully!"
    echo "Please restart Anki to complete removal."
else
    echo
    echo "Uninstallation failed. Please check the error messages above."
    exit 1
fi
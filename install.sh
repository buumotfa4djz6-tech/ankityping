#!/bin/bash

# AnkiTyping Plugin Installation Script
# =====================================

set -e

echo "AnkiTyping Plugin Installation Script"
echo "====================================="
echo

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH"
    echo "Please install Python 3.8 or higher first"
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

# Run the package installation
$PYTHON_CMD package.py install "$@"

if [ $? -eq 0 ]; then
    echo
    echo "Installation completed successfully!"
    echo "Please restart Anki to load the plugin."
else
    echo
    echo "Installation failed. Please check the error messages above."
    exit 1
fi
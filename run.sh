#!/bin/bash
# Quick start script for NitiArthik
# This script assumes the virtual environment is already set up.
# Run ./setup.sh first if you haven't set up the environment yet.

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run ./setup.sh first to set up the environment."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Dependencies not installed. Installing..."
    pip install -r requirements.txt
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Run the application
echo "Starting NitiArthik application..."
echo "Access the application at http://localhost:5000"
echo ""
python app.py


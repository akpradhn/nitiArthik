#!/bin/bash
# Virtual environment setup script for NitiArthik

set -e  # Exit on error

echo "=========================================="
echo "NitiArthik - Virtual Environment Setup"
echo "=========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python version: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf venv
        echo "Creating new virtual environment..."
        python3 -m venv venv
    else
        echo "Using existing virtual environment."
    fi
else
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p uploads

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit .env file and set your SECRET_KEY"
    else
        echo "SECRET_KEY=dev-secret-key-change-in-production" > .env
        echo "DATABASE_URL=sqlite:///nitiarthik.db" >> .env
        echo "Created .env file with default values. Please update SECRET_KEY for production."
    fi
fi

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "To activate the virtual environment manually, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application:"
echo "  python app.py"
echo ""
echo "Or use the run script:"
echo "  ./run.sh"
echo ""






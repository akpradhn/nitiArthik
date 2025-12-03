#!/bin/bash
# Combined setup and run script for NitiArthik

set -e  # Exit on error

echo "=========================================="
echo "NitiArthik - Setup and Start"
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
    echo "Creating .env file..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit .env file and set your SECRET_KEY"
    else
        cat > .env << EOF
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///nitiarthik.db
# GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here
EOF
        echo "Created .env file with default values. Please update SECRET_KEY for production."
        echo "Optional: Add GOOGLE_GEMINI_API_KEY for better PDF parsing with Gemini AI"
    fi
fi

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Dependencies not fully installed. Installing..."
    pip install -r requirements.txt
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Run the application
echo ""
echo "=========================================="
echo "Starting NitiArthik application..."
echo "=========================================="
echo ""
echo "Access the application at http://localhost:5000"
echo "Press CTRL+C to stop the server"
echo ""
echo "=========================================="
echo ""

python app.py




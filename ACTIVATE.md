# Virtual Environment Quick Reference

## Initial Setup

Run the setup script to create and configure the virtual environment:

**Linux/macOS:**
```bash
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

## Activating the Virtual Environment

After setup, activate the virtual environment before working on the project:

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

When activated, your terminal prompt will show `(venv)`.

## Deactivating

To deactivate the virtual environment:

**Linux/macOS/Windows:**
```bash
deactivate
```

## Running the Application

**Option 1: Use the run script (recommended)**
```bash
# Linux/macOS
./run.sh

# Windows
run.bat
```

**Option 2: Manual activation and run**
```bash
# Activate first
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Then run
python app.py
```

## Installing New Dependencies

If you add new packages:

1. Activate the virtual environment
2. Install the package: `pip install package-name`
3. Update requirements.txt: `pip freeze > requirements.txt`

## Troubleshooting

**Virtual environment not found:**
- Run `./setup.sh` (Linux/macOS) or `setup.bat` (Windows) first

**Permission denied on scripts:**
- Linux/macOS: `chmod +x setup.sh run.sh`
- Windows: Run from Command Prompt (not PowerShell) or use Git Bash

**Python not found:**
- Ensure Python 3.8+ is installed and in your PATH
- Try `python3` instead of `python` on some systems






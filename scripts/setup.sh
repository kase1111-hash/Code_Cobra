#!/bin/bash
# Setup script for Autonomous Coding Ensemble System
# Creates virtual environment and installs dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Code Cobra Setup ==="
echo "Project root: $PROJECT_ROOT"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "Python version: $PYTHON_VERSION"

# Create virtual environment
VENV_DIR="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r "$PROJECT_ROOT/requirements.txt"

# Optional: Install dev dependencies
if [ "$1" == "--dev" ]; then
    echo "Installing development dependencies..."
    pip install -r "$PROJECT_ROOT/requirements-dev.txt"
fi

# Verify installation
echo "Verifying installation..."
python "$PROJECT_ROOT/autonomous_ensemble.py" --dry-run --guide "$PROJECT_ROOT/coding_guide.txt"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run Code Cobra:"
echo "  python autonomous_ensemble.py --help"
echo ""
echo "To run with Ollama (ensure Ollama is running):"
echo "  python autonomous_ensemble.py --spec 'Your project spec' --guide coding_guide.txt"

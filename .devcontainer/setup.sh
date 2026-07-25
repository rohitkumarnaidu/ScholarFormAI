#!/bin/bash
set -euo pipefail

echo "=== AMF Development Container Setup ==="
echo

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv /workspace/backend/.venv
source /workspace/backend/.venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
pip install --upgrade pip
pip install -r /workspace/backend/requirements-dev.txt
pip install -e /workspace/backend/

# Install frontend dependencies if package.json exists
if [ -f /workspace/frontend/package.json ]; then
    echo "Installing frontend dependencies..."
    cd /workspace/frontend
    npm install
    cd /workspace
fi

# Install CLI dependencies
if [ -f /workspace/cli/pyproject.toml ]; then
    echo "Installing CLI..."
    pip install -e /workspace/cli/
fi

# Install SDK dependencies
if [ -f /workspace/sdk/pyproject.toml ]; then
    echo "Installing SDK..."
    pip install -e /workspace/sdk/
fi

# Set up pre-commit hooks
echo "Configuring pre-commit hooks..."
if [ -f /workspace/.pre-commit-config.yaml ]; then
    pre-commit install
    pre-commit install --hook-type commit-msg
fi

# Create necessary directories
mkdir -p /workspace/backend/output
mkdir -p /workspace/backend/uploads

echo
echo "Setup complete!"
echo "Python: $(python3 --version)"
echo "Node: $(node --version)"
echo "npm: $(npm --version)"
echo "k6: $(k6 version 2>/dev/null || echo 'not installed')"
echo "locust: $(locust --version 2>/dev/null || echo 'not installed')"

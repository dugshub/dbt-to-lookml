#!/bin/bash
# Script to properly clear cache and reinstall dbt-to-lookml

set -e  # Exit on error

echo "=========================================="
echo "Clearing Python Cache and Reinstalling"
echo "=========================================="

# Step 1: Clear ALL Python cache in the project
echo "Step 1: Clearing Python bytecode cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Cache cleared"

# Step 2: Uninstall current version
echo ""
echo "Step 2: Uninstalling current version..."
uv pip uninstall -y dbt-to-lookml || true
echo "✓ Uninstalled"

# Step 3: Reinstall in editable mode
echo ""
echo "Step 3: Reinstalling in editable mode..."
uv pip install -e .
echo "✓ Reinstalled"

# Step 4: Verify installation
echo ""
echo "Step 4: Verifying installation..."
python3 -c "
import sys
from pathlib import Path

# Import the module
from dbt_to_lookml import wizard
import inspect

# Get the source file location
source_file = inspect.getfile(wizard.generate_wizard.run_generate_wizard)
print(f'✓ Module location: {source_file}')

# Check if execution prompt code exists in source
with open(source_file, 'r') as f:
    content = f.read()
    has_execution_prompt = 'Execute this command now?' in content
    has_old_message = 'To execute this command, run it in your terminal' in content

    print(f'✓ Has execution prompt: {has_execution_prompt}')
    print(f'✓ Has old message in source: {has_old_message}')

    if has_execution_prompt and not has_old_message:
        print('')
        print('✅ Installation verified! The new code is in place.')
    else:
        print('')
        print('⚠️  WARNING: Source code may not be correct')
"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Now try running: d2l wizard generate"

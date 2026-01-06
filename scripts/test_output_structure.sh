#!/bin/bash
# test_output_structure.sh - Evaluate the output restructuring implementation
# Run from repo root: ./scripts/test_output_structure.sh

set -e

echo "=============================================="
echo "Output Restructuring Evaluation"
echo "=============================================="

cd examples/spothero

# Clean previous output
echo ""
echo "=== Cleaning previous output ==="
rm -rf lookml/

# Update sp.yml with new config format
echo ""
echo "=== Updating sp.yml with project config ==="
cat > sp.yml << 'EOF'
project: spothero

input: .
output: ./lookml
schema: gold

model:
  name: spothero
  connection: database

explores:
  - fact: rentals
  - fact: facility_lifecycle

output_options:
  clean: clean
  manifest: true

options:
  dialect: redshift
  pop_strategy: dynamic
  date_selector: true
  convert_tz: false
EOF

echo "Config updated:"
cat sp.yml

# Run build
echo ""
echo "=== Running sp build ==="
sp build --verbose

# Display structure
echo ""
echo "=== Output Structure ==="
if command -v tree &> /dev/null; then
    tree lookml/ -I '__pycache__' --noreport
else
    find lookml/ -type f | sort
fi

# Verification checks
echo ""
echo "=== Verification Checks ==="

check() {
    if [ "$1" = "dir" ]; then
        [ -d "$2" ] && echo "✓ $3" || echo "✗ $3 (missing: $2)"
    else
        [ -f "$2" ] && echo "✓ $3" || echo "✗ $3 (missing: $2)"
    fi
}

check dir "lookml/spothero" "Project folder exists"
check dir "lookml/spothero/views" "Views folder exists"
check dir "lookml/spothero/models" "Models folder exists"
check file "lookml/spothero/.sp-manifest.json" "Manifest exists"
check dir "lookml/spothero/views/rentals" "Domain folder (rentals) exists"
check file "lookml/spothero/views/rentals/rentals.view.lkml" "rentals.view.lkml exists"
check file "lookml/spothero/views/rentals/rentals.metrics.view.lkml" "rentals.metrics.view.lkml exists"
check file "lookml/spothero/models/spothero.model.lkml" "Rollup model exists"
check file "lookml/spothero/models/rentals.explore.lkml" "rentals.explore.lkml exists"

# Show manifest
echo ""
echo "=== Manifest Contents (first 40 lines) ==="
if [ -f "lookml/spothero/.sp-manifest.json" ]; then
    head -40 lookml/spothero/.sp-manifest.json
else
    echo "Manifest not found!"
fi

# Show model includes
echo ""
echo "=== Rollup Model File ==="
if [ -f "lookml/spothero/models/spothero.model.lkml" ]; then
    cat lookml/spothero/models/spothero.model.lkml
else
    echo "Rollup model not found!"
fi

# Check relative paths in model file
echo ""
echo "=== Checking Relative Paths ==="
if [ -f "lookml/spothero/models/spothero.model.lkml" ]; then
    if grep -q '/views/' lookml/spothero/models/spothero.model.lkml; then
        echo "✓ Model file uses relative view paths (/views/...)"
    else
        echo "✗ Model file missing relative view paths"
    fi
    if grep -q '/models/' lookml/spothero/models/spothero.model.lkml; then
        echo "✓ Model file uses relative explore paths (/models/...)"
    else
        echo "✗ Model file missing relative explore paths"
    fi
fi

# Test orphan cleanup
echo ""
echo "=== Testing Orphan Cleanup ==="
mkdir -p lookml/spothero/views/orphan_model
echo "view: orphan {}" > lookml/spothero/views/orphan_model/orphan.view.lkml
echo "Created orphan file: lookml/spothero/views/orphan_model/orphan.view.lkml"

sp build --force

if [ -f "lookml/spothero/views/orphan_model/orphan.view.lkml" ]; then
    echo "✗ Orphan file still exists (cleanup failed)"
else
    echo "✓ Orphan file removed (cleanup works)"
fi

echo ""
echo "=============================================="
echo "Evaluation Complete"
echo "=============================================="

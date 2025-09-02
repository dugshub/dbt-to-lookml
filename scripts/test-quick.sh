#!/bin/bash
# Quick test runner for common test scenarios

set -e

echo "🚀 dbt-to-lookml Quick Test Suite"
echo "=================================="

# Function to run tests with timing
run_test() {
    local test_type=$1
    local description=$2
    
    echo ""
    echo "📋 Running $description..."
    start_time=$(date +%s)
    
    if python scripts/test.py "$test_type" --parallel; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "✅ $description completed in ${duration}s"
    else
        echo "❌ $description failed"
        exit 1
    fi
}

# Parse command line arguments
case "${1:-fast}" in
    "fast")
        echo "Running fast test suite..."
        run_test "fast" "Fast Tests"
        ;;
    "full")
        echo "Running full test suite..."
        run_test "unit" "Unit Tests"
        run_test "integration" "Integration Tests"
        run_test "golden" "Golden File Tests"
        run_test "cli" "CLI Tests"
        run_test "error-handling" "Error Handling Tests"
        echo ""
        echo "🎯 Running linting and type checks..."
        python scripts/test.py lint
        python scripts/test.py type-check
        ;;
    "coverage")
        echo "Running tests with coverage analysis..."
        run_test "coverage" "Coverage Tests"
        echo ""
        echo "📊 Coverage report generated in htmlcov/"
        ;;
    "performance")
        echo "Running performance tests..."
        run_test "performance" "Performance Tests"
        ;;
    "ci")
        echo "Running CI test suite..."
        run_test "all" "All Tests"
        python scripts/test.py lint
        python scripts/test.py type-check
        ;;
    *)
        echo "Usage: $0 [fast|full|coverage|performance|ci]"
        echo ""
        echo "  fast        - Run fast tests only (default)"
        echo "  full        - Run all tests including slow ones"
        echo "  coverage    - Run tests with coverage analysis"
        echo "  performance - Run performance tests only"
        echo "  ci          - Run full CI test suite"
        exit 1
        ;;
esac

echo ""
echo "🎉 All tests passed successfully!"
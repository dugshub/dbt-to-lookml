#!/usr/bin/env python3
"""
Test runner script for dbt-to-lookml.

Provides convenient commands for running different types of tests.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> int:
    """Run a command and return the exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    
    if result.returncode == 0:
        print(f"\n✅ {description} passed!")
    else:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
    
    return result.returncode


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Test runner for dbt-to-lookml")
    
    parser.add_argument(
        "test_type",
        choices=[
            "all", "unit", "integration", "golden", "cli", "performance", 
            "error-handling", "coverage", "fast", "slow", "lint", "type-check"
        ],
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel using pytest-xdist"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--html-cov",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    # Add parallel execution if requested
    if args.parallel:
        base_cmd.extend(["-n", "auto"])
    
    # Add verbosity
    if args.verbose:
        base_cmd.append("-vv")
    
    # Coverage options
    if not args.no_cov:
        base_cmd.extend([
            "--cov=dbt_to_lookml",
            "--cov-report=term-missing",
            "--cov-branch"
        ])
        
        if args.html_cov:
            base_cmd.append("--cov-report=html")
    
    exit_code = 0
    
    if args.test_type == "all":
        # Run all tests except slow performance tests
        cmd = base_cmd + ["-m", "not slow"]
        exit_code = run_command(cmd, "All Tests (excluding slow)")
        
    elif args.test_type == "unit":
        # Run unit tests
        cmd = base_cmd + ["tests/unit/"]
        exit_code = run_command(cmd, "Unit Tests")
        
    elif args.test_type == "integration":
        # Run integration tests
        cmd = base_cmd + ["tests/integration/"]
        exit_code = run_command(cmd, "Integration Tests")
        
    elif args.test_type == "golden":
        # Run golden file tests
        cmd = base_cmd + ["tests/test_golden.py"]
        exit_code = run_command(cmd, "Golden File Tests")
        
    elif args.test_type == "cli":
        # Run CLI tests
        cmd = base_cmd + ["tests/test_cli.py"]
        exit_code = run_command(cmd, "CLI Tests")
        
    elif args.test_type == "performance":
        # Run performance tests
        cmd = base_cmd + ["tests/test_performance.py"]
        exit_code = run_command(cmd, "Performance Tests")
        
    elif args.test_type == "error-handling":
        # Run error handling tests
        cmd = base_cmd + ["tests/test_error_handling.py"]
        exit_code = run_command(cmd, "Error Handling Tests")
        
    elif args.test_type == "coverage":
        # Run tests with detailed coverage
        cmd = base_cmd + [
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-report=term-missing",
            "--cov-fail-under=95"
        ]
        exit_code = run_command(cmd, "Coverage Tests")
        
    elif args.test_type == "fast":
        # Run fast tests only
        cmd = base_cmd + ["-m", "not slow and not performance"]
        exit_code = run_command(cmd, "Fast Tests")
        
    elif args.test_type == "slow":
        # Run slow tests only
        cmd = base_cmd + ["-m", "slow"]
        exit_code = run_command(cmd, "Slow Tests")
        
    elif args.test_type == "lint":
        # Run linting
        lint_cmd = ["python", "-m", "ruff", "check", "src/", "tests/"]
        exit_code = run_command(lint_cmd, "Linting (ruff)")
        
        if exit_code == 0:
            # Also run formatting check
            format_cmd = ["python", "-m", "ruff", "format", "--check", "src/", "tests/"]
            format_exit = run_command(format_cmd, "Format Check (ruff)")
            exit_code = max(exit_code, format_exit)
            
    elif args.test_type == "type-check":
        # Run type checking
        cmd = ["python", "-m", "mypy", "src/dbt_to_lookml"]
        exit_code = run_command(cmd, "Type Checking (mypy)")
    
    # Print final summary
    print(f"\n{'='*60}")
    if exit_code == 0:
        print("🎉 All checks passed!")
    else:
        print(f"💥 Tests failed with exit code {exit_code}")
    print(f"{'='*60}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Comprehensive test runner script for dbt-to-lookml.

This script provides different testing modes and options for thorough validation
of the dbt-to-lookml tool.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


class TestRunner:
    """Comprehensive test runner with multiple modes and reporting."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.test_results: Dict[str, Any] = {}
    
    def run_unit_tests(self, verbose: bool = False) -> bool:
        """Run unit tests with coverage."""
        print("🧪 Running unit tests...")

        cmd = [
            "python", "-m", "pytest",
            "__tests__/unit/",
            "--tb=line",  # Compact traceback format
            "--no-header",  # Skip pytest header
            "--quiet" if not verbose else "-v",
            "--cov=dbt_to_lookml",
            "--cov-report=term-missing:skip-covered",  # Only show uncovered lines
            "--cov-report=html",
            "--cov-branch",
            "--cov-fail-under=70",
        ]

        # Run without capturing output to show progress
        result = subprocess.run(cmd, cwd=self.root_dir)

        self.test_results["unit_tests"] = {
            "passed": result.returncode == 0,
        }

        if result.returncode == 0:
            print("✅ Unit tests passed")
        else:
            print("❌ Unit tests failed")

        return result.returncode == 0
    
    def run_integration_tests(self, verbose: bool = False) -> bool:
        """Run integration tests."""
        print("🔗 Running integration tests...")

        cmd = [
            "python", "-m", "pytest",
            "__tests__/integration/",
            "--tb=line",
            "--no-header",
            "--quiet" if not verbose else "-v",
            "--no-cov",  # Skip coverage for integration tests to avoid duplication
        ]

        # Run without capturing output to show progress
        result = subprocess.run(cmd, cwd=self.root_dir)

        self.test_results["integration_tests"] = {
            "passed": result.returncode == 0,
        }

        if result.returncode == 0:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")

        return result.returncode == 0
    
    def run_golden_file_tests(self, verbose: bool = False) -> bool:
        """Run golden file tests."""
        print("🏆 Running golden file tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "__tests__/test_golden.py",
            "-v" if verbose else "-q",
        ]
        
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        self.test_results["golden_tests"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        if result.returncode == 0:
            print("✅ Golden file tests passed")
        else:
            print("❌ Golden file tests failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return result.returncode == 0
    
    def run_error_handling_tests(self, verbose: bool = False) -> bool:
        """Run error handling tests."""
        print("🚨 Running error handling tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "__tests__/test_error_handling.py",
            "-v" if verbose else "-q",
            "-m", "error_handling",
        ]
        
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        self.test_results["error_handling_tests"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        if result.returncode == 0:
            print("✅ Error handling tests passed")
        else:
            print("❌ Error handling tests failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return result.returncode == 0
    
    def run_performance_tests(self, verbose: bool = False, include_slow: bool = False) -> bool:
        """Run performance tests."""
        print("🚀 Running performance tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "__tests__/test_performance.py",
            "-v" if verbose else "-q",
        ]
        
        if include_slow:
            cmd.extend(["-m", "not slow or slow"])
        else:
            cmd.extend(["-m", "not slow"])
        
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        self.test_results["performance_tests"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "included_slow": include_slow
        }
        
        if result.returncode == 0:
            print("✅ Performance tests passed")
        else:
            print("❌ Performance tests failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return result.returncode == 0
    
    def run_cli_tests(self, verbose: bool = False) -> bool:
        """Run CLI tests."""
        print("💻 Running CLI tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "__tests__/test_cli.py",
            "-v" if verbose else "-q",
        ]
        
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        self.test_results["cli_tests"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        if result.returncode == 0:
            print("✅ CLI tests passed")
        else:
            print("❌ CLI tests failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return result.returncode == 0
    
    def run_linting(self, verbose: bool = False) -> bool:
        """Run code linting with ruff."""
        print("🔍 Running linting...")
        
        # Run ruff check
        cmd = ["python", "-m", "ruff", "check", "src/", "__tests__/"]
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        linting_passed = result.returncode == 0
        
        self.test_results["linting"] = {
            "passed": linting_passed,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        if linting_passed:
            print("✅ Linting passed")
        else:
            print("❌ Linting failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return linting_passed
    
    def run_type_checking(self, verbose: bool = False) -> bool:
        """Run type checking with mypy."""
        print("🎯 Running type checking...")
        
        cmd = ["python", "-m", "mypy", "src/dbt_to_lookml"]
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        type_check_passed = result.returncode == 0
        
        self.test_results["type_checking"] = {
            "passed": type_check_passed,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        if type_check_passed:
            print("✅ Type checking passed")
        else:
            print("❌ Type checking failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return type_check_passed
    
    def run_smoke_tests(self, verbose: bool = False) -> bool:
        """Run smoke tests with real data."""
        print("💨 Running smoke tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "__tests__/integration/test_end_to_end.py::TestEndToEndIntegration::test_real_world_semantic_models_integration",
            "-v" if verbose else "-q",
        ]
        
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        self.test_results["smoke_tests"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        if result.returncode == 0:
            print("✅ Smoke tests passed")
        else:
            print("❌ Smoke tests failed")
            if verbose:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        
        return result.returncode == 0
    
    def run_all_tests(self, verbose: bool = False, include_slow: bool = False) -> bool:
        """Run all test suites."""
        print("🎯 Running complete test suite...")
        start_time = time.time()
        
        all_passed = True
        
        # Run tests in logical order
        test_suites = [
            ("linting", self.run_linting),
            ("type_checking", self.run_type_checking),
            ("unit_tests", self.run_unit_tests),
            ("integration_tests", self.run_integration_tests),
            ("golden_file_tests", self.run_golden_file_tests),
            ("error_handling_tests", self.run_error_handling_tests),
            ("cli_tests", self.run_cli_tests),
            ("smoke_tests", self.run_smoke_tests),
        ]
        
        # Add performance tests if requested
        if include_slow:
            test_suites.append(("performance_tests", 
                              lambda v: self.run_performance_tests(v, include_slow=True)))
        
        for suite_name, test_func in test_suites:
            print(f"\\n--- {suite_name.replace('_', ' ').title()} ---")
            try:
                passed = test_func(verbose)
                all_passed = all_passed and passed
                
                if not passed:
                    print(f"❌ {suite_name} failed - continuing with other tests...")
            except Exception as e:
                print(f"💥 {suite_name} crashed: {e}")
                all_passed = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        
        for suite_name, result in self.test_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{suite_name.replace('_', ' ').title():<25} {status}")
        
        print(f"\\nTotal Duration: {duration:.2f} seconds")
        
        if all_passed:
            print("\\n🎉 All tests passed!")
        else:
            print("\\n💔 Some tests failed!")
        
        return all_passed
    
    def generate_report(self, output_file: Optional[Path] = None) -> None:
        """Generate JSON test report."""
        if output_file is None:
            output_file = self.root_dir / "test_results.json"
        
        report = {
            "timestamp": time.time(),
            "results": self.test_results,
            "summary": {
                "total_suites": len(self.test_results),
                "passed_suites": sum(1 for r in self.test_results.values() if r["passed"]),
                "failed_suites": sum(1 for r in self.test_results.values() if not r["passed"]),
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Test report written to {output_file}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for dbt-to-lookml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Modes:
  all         Run all test suites
  unit        Run unit tests only
  integration Run integration tests only
  golden      Run golden file tests only
  error       Run error handling tests only
  performance Run performance tests only
  cli         Run CLI tests only
  lint        Run linting only
  types       Run type checking only
  smoke       Run smoke tests only

Examples:
  python scripts/run-tests.py all --verbose
  python scripts/run-tests.py unit --coverage
  python scripts/run-tests.py performance --include-slow
  python scripts/run-tests.py smoke
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["all", "unit", "integration", "golden", "error", "performance", 
                "cli", "lint", "types", "smoke"],
        help="Test mode to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--include-slow",
        action="store_true",
        help="Include slow-running tests (for performance mode)"
    )
    
    parser.add_argument(
        "--report",
        type=Path,
        help="Generate JSON report to specified file"
    )
    
    args = parser.parse_args()
    
    # Find project root
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    
    runner = TestRunner(root_dir)
    
    # Dispatch to appropriate test runner
    success = False
    
    if args.mode == "all":
        success = runner.run_all_tests(args.verbose, args.include_slow)
    elif args.mode == "unit":
        success = runner.run_unit_tests(args.verbose)
    elif args.mode == "integration":
        success = runner.run_integration_tests(args.verbose)
    elif args.mode == "golden":
        success = runner.run_golden_file_tests(args.verbose)
    elif args.mode == "error":
        success = runner.run_error_handling_tests(args.verbose)
    elif args.mode == "performance":
        success = runner.run_performance_tests(args.verbose, args.include_slow)
    elif args.mode == "cli":
        success = runner.run_cli_tests(args.verbose)
    elif args.mode == "lint":
        success = runner.run_linting(args.verbose)
    elif args.mode == "types":
        success = runner.run_type_checking(args.verbose)
    elif args.mode == "smoke":
        success = runner.run_smoke_tests(args.verbose)
    
    # Generate report if requested
    if args.report:
        runner.generate_report(args.report)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
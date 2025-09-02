# Makefile for dbt-to-lookml development and testing

.PHONY: help install test test-fast test-full test-unit test-integration test-golden test-cli test-performance test-error test-coverage lint format type-check clean dev-install smoke-test ci-test benchmark test-all-verbose

# Default target
help:
	@echo "dbt-to-lookml Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  install          Install project dependencies"
	@echo "  dev-install      Install development dependencies"
	@echo "  dev-setup        Complete development environment setup"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run essential test suite (unit + integration)"
	@echo "  test-fast        Run unit tests only (fastest)"
	@echo "  test-full        Run complete test suite (all tests)"
	@echo "  test-unit        Run unit tests with coverage"
	@echo "  test-integration Run integration tests"
	@echo "  test-golden      Run golden file tests"
	@echo "  test-cli         Run CLI tests"
	@echo "  test-performance Run performance tests (fast subset)"
	@echo "  test-error       Run error handling tests"
	@echo "  test-coverage    Generate detailed coverage report"
	@echo "  smoke-test       Run smoke tests with real data"
	@echo "  test-all-verbose Run all tests with verbose output"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting (ruff)"
	@echo "  format           Format code (ruff)"
	@echo "  type-check       Run type checking (mypy)"
	@echo "  check-all        Run all code quality checks"
	@echo "  quality-gate     Complete quality gate (lint + types + tests)"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci-test          Run CI test suite"
	@echo "  benchmark        Run performance benchmarks"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Clean build artifacts and cache"
	@echo "  clean-all        Deep clean including coverage reports"

# Installation targets
install:
	@echo "📦 Installing project dependencies..."
	uv sync

dev-install:
	@echo "🛠️  Installing development dependencies..."
	uv sync --group dev

# Test targets using comprehensive test runner
test:
	@echo "🧪 Running essential test suite..."
	@python scripts/run-tests.py unit
	@python scripts/run-tests.py integration

test-fast:
	@echo "⚡ Running unit tests (fastest)..."
	@python scripts/run-tests.py unit

test-full:
	@echo "🎯 Running complete test suite..."
	@python scripts/run-tests.py all

test-unit:
	@echo "🧪 Running unit tests with coverage..."
	@python scripts/run-tests.py unit

test-integration:
	@echo "🔗 Running integration tests..."
	@python scripts/run-tests.py integration

test-golden:
	@echo "🏆 Running golden file tests..."
	@python scripts/run-tests.py golden

test-cli:
	@echo "💻 Running CLI tests..."
	@python scripts/run-tests.py cli

test-performance:
	@echo "🚀 Running performance tests..."
	@python scripts/run-tests.py performance

test-error:
	@echo "🚨 Running error handling tests..."
	@python scripts/run-tests.py error

test-coverage:
	@echo "📊 Generating coverage report..."
	@python -m pytest tests/unit/ --cov=dbt_to_lookml --cov-report=html --cov-report=term-missing --cov-branch --cov-fail-under=95
	@echo "📊 Coverage report: htmlcov/index.html"

smoke-test:
	@echo "💨 Running smoke tests..."
	@python scripts/run-tests.py smoke

test-all-verbose:
	@echo "🎯 Running all tests with verbose output..."
	@python scripts/run-tests.py all --verbose

# Code quality targets
lint:
	@echo "🔍 Running linter..."
	@python scripts/run-tests.py lint

format:
	@echo "🎨 Formatting code..."
	@python -m ruff format src/ tests/
	@python -m ruff check src/ tests/ --fix
	@echo "✅ Code formatted"

type-check:
	@echo "🔎 Running type checker..."
	@python scripts/run-tests.py types

check-all: lint type-check
	@echo "✅ All code quality checks passed"

quality-gate: lint type-check test
	@echo "🏁 Quality gate passed - ready for commit/PR"

# Maintenance targets
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .testmoncore/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned build artifacts"

clean-all: clean
	@echo "🧹 Deep cleaning..."
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf coverage.xml
	@rm -rf .mypy_cache/
	@rm -rf .ruff_cache/
	@rm -rf test_results.json
	@rm -rf .testmoncore/
	@echo "✅ Deep clean completed"

# CI/CD targets
ci-test:
	@echo "🚀 Running CI test suite..."
	@python scripts/run-tests.py all --report test_results.json
	@echo "📄 Test results saved to test_results.json"

# Development workflow
dev-setup: dev-install
	@echo "🔧 Setting up development environment..."
	@chmod +x scripts/run-tests.py
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Quick start commands:"
	@echo "  make test           - Run essential tests"
	@echo "  make test-fast      - Run unit tests only"
	@echo "  make test-full      - Run all tests"
	@echo "  make quality-gate   - Complete quality check"
	@echo "  make lint           - Check code style"
	@echo "  make format         - Format code"
	@echo "  make smoke-test     - Quick validation with real data"

first-run: dev-setup smoke-test
	@echo "🎉 First run complete! Tool is working correctly."

validate-setup:
	@echo "🔍 Validating development setup..."
	@python -c "import dbt_to_lookml; print('✅ Package imports correctly')"
	@python scripts/run-tests.py smoke
	@echo "✅ Setup validation complete"

# Performance and benchmarking
benchmark:
	@echo "⚡ Running performance benchmarks..."
	@python scripts/run-tests.py performance --include-slow --verbose

test-stress:
	@echo "💪 Running stress tests..."
	@python -m pytest tests/test_performance.py::TestPerformance::test_stress_test_many_models -v -s
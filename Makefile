# Makefile for dbt-to-lookml development and testing

.PHONY: help install test test-fast test-full test-unit test-integration test-golden test-cli test-performance test-error test-coverage lint format type-check clean dev-install smoke-test ci-test benchmark test-all-verbose \
	lookml-generate lookml-preview lookml-validate lookml-validate-strict lookml-demo \
	tasks-list tasks-show tasks-update tasks-reindex tasks-next-id

# Defaults for LookML generation commands (override via: make <target> INPUT_DIR=... OUTPUT_DIR=...)
INPUT_DIR ?= semantic_models
OUTPUT_DIR ?= build/lookml

# Default target
help:
	@echo "dbt-to-lookml Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Generation:"
	@echo "  lookml-preview    Dry-run generation with summary (INPUT_DIR, OUTPUT_DIR)"
	@echo "  lookml-generate   Generate LookML files (INPUT_DIR, OUTPUT_DIR)"
	@echo "  lookml-gold       Generate Gold Layer LookML (SpotHero production)"
	@echo "  lookml-validate   Validate semantic models (-v)"
	@echo "  lookml-validate-strict  Validate in strict mode (-v, --strict)"
	@echo "  lookml-demo       Preview using default sample folder 'semantic_models/'"
	@echo ""
	@echo "Task Management:"
	@echo "  tasks-list        List all issues"
	@echo "  tasks-show ID=... Show issue details (e.g., make tasks-show ID=DTL-001)"
	@echo "  tasks-update      Update issue (ID, STATUS, LABEL, EVENT, DESC)"
	@echo "  tasks-reindex     Regenerate index.md"
	@echo "  tasks-next-id     Show next available issue ID"
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
	@uv run python scripts/run-tests.py unit
	@uv run python scripts/run-tests.py integration

test-fast:
	@echo "⚡ Running unit tests (fastest)..."
	@uv run python scripts/run-tests.py unit

test-full:
	@echo "🎯 Running complete test suite..."
	@uv run python scripts/run-tests.py all

test-unit:
	@echo "🧪 Running unit tests with coverage..."
	@uv run python scripts/run-tests.py unit

test-integration:
	@echo "🔗 Running integration tests..."
	@uv run python scripts/run-tests.py integration

test-golden:
	@echo "🏆 Running golden file tests..."
	@uv run python scripts/run-tests.py golden

test-cli:
	@echo "💻 Running CLI tests..."
	@uv run python scripts/run-tests.py cli

test-performance:
	@echo "🚀 Running performance tests..."
	@uv run python scripts/run-tests.py performance

test-error:
	@echo "🚨 Running error handling tests..."
	@uv run python scripts/run-tests.py error

test-coverage:
	@echo "📊 Generating coverage report..."
	@uv run pytest src/tests/unit/ --cov=dbt_to_lookml --cov-report=html --cov-report=term-missing --cov-branch --cov-fail-under=95
	@echo "📊 Coverage report: htmlcov/index.html"

smoke-test:
	@echo "💨 Running smoke tests..."
	@uv run python scripts/run-tests.py smoke

test-all-verbose:
	@echo "🎯 Running all tests with verbose output..."
	@uv run python scripts/run-tests.py all --verbose

# Code quality targets
lint:
	@echo "🔍 Running linter..."
	@uv run python scripts/run-tests.py lint

format:
	@echo "🎨 Formatting code..."
	@uv run ruff format src/
	@uv run ruff check src/ --fix
	@echo "✅ Code formatted"

type-check:
	@echo "🔎 Running type checker..."
	@uv run python scripts/run-tests.py types

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
	@rm -rf .benchmarks/
	@rm -rf output/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf coverage.xml
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.log" -delete
	@find . -type f -name ".DS_Store" -delete
	@find . -type f -name "*.tmp" -delete
	@find . -type f -name "*.swp" -delete
	@find . -type f -name "*.swo" -delete
	@find . -type f -name "*~" -delete
	@echo "✅ Cleaned build artifacts"

clean-all: clean
	@echo "🧹 Deep cleaning..."
	@rm -rf .mypy_cache/
	@rm -rf .ruff_cache/
	@rm -rf .uv-cache/
	@rm -rf test_results.json
	@uv cache clean
	@echo "✅ Deep clean completed"

# CI/CD targets
ci-test:
	@echo "🚀 Running CI test suite..."
	@uv run python scripts/run-tests.py all --report test_results.json
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
	@uv run python -c "import dbt_to_lookml; print('✅ Package imports correctly')"
	@uv run python scripts/run-tests.py smoke
	@echo "✅ Setup validation complete"

# Performance and benchmarking
benchmark:
	@echo "⚡ Running performance benchmarks..."
	@uv run python scripts/run-tests.py performance --include-slow --verbose

test-stress:
	@echo "💪 Running stress tests..."
	@uv run pytest src/tests/test_performance.py::TestPerformance::test_stress_test_many_models -v -s

# LookML generation helpers (wrap CLI until a separate tool is built)
lookml-preview:
	@echo "👀 Previewing LookML generation (dry run) from $(INPUT_DIR) -> $(OUTPUT_DIR)"
	@uv run python -m dbt_to_lookml generate -i $(INPUT_DIR) -o $(OUTPUT_DIR) --dry-run --show-summary

lookml-generate:
	@echo "🧩 Generating LookML files from $(INPUT_DIR) -> $(OUTPUT_DIR)"
	@uv run python -m dbt_to_lookml generate -i $(INPUT_DIR) -o $(OUTPUT_DIR)

# Gold Layer generation (SpotHero production)
lookml-gold:
	@echo "🥇 Generating Gold Layer LookML"
	@d2l generate \
		-i /Users/doug/Work/data-modelling/official-models/redshift_gold/models/3_semantic/models \
		-md /Users/doug/Work/data-modelling/official-models/redshift_gold/models/3_semantic/metrics \
		-o /Users/doug/Work/data-modelling/analytics_lookML/GoldLayer \
		--view-prefix gold_ \
		--explore-prefix gold_ \
		--model-name gold_semantic_models \
		--no-convert-tz \
		--bi-field-only \
		--schema gold_sandbox \
		--fact-models "rentals, facility_monthly_status" \
		--include-children \
		--use-group-item-label \
		--date-selector \
		--show-summary \
		--yes

lookml-validate:
	@echo "🔎 Validating semantic models in $(INPUT_DIR)"
	@uv run python -m dbt_to_lookml validate -i $(INPUT_DIR) -v

lookml-validate-strict:
	@echo "🔒 Strict validation of semantic models in $(INPUT_DIR)"
	@uv run python -m dbt_to_lookml validate -i $(INPUT_DIR) --strict -v

lookml-demo:
	@echo "🎬 Demo: preview generation using default sample folder (semantic_models/)"
	@$(MAKE) lookml-preview INPUT_DIR=semantic_models OUTPUT_DIR=$(OUTPUT_DIR)

# Task Management Commands
tasks-list:
	@uv run python scripts/dtl_tasks.py list

tasks-show:
ifndef ID
	@echo "Error: ID parameter required. Usage: make tasks-show ID=DTL-001"
	@exit 1
endif
	@uv run python scripts/dtl_tasks.py show $(ID)

tasks-update:
ifndef ID
	@echo "Error: ID parameter required. Usage: make tasks-update ID=DTL-001 STATUS=in-progress"
	@exit 1
endif
ifdef STATUS
	@uv run python scripts/dtl_tasks.py update $(ID) --status $(STATUS)
endif
ifdef LABEL
	@uv run python scripts/dtl_tasks.py update $(ID) --add-label $(LABEL)
endif
ifdef EVENT
ifndef DESC
	@echo "Error: DESC parameter required when using EVENT"
	@exit 1
endif
	@uv run python scripts/dtl_tasks.py update $(ID) --event "$(EVENT)" --description "$(DESC)"
endif

tasks-reindex:
	@uv run python scripts/dtl_tasks.py reindex

tasks-next-id:
	@uv run python scripts/dtl_tasks.py next-id

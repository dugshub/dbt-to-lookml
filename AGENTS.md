# Repository Guidelines

## Project Structure & Module Organization
- `src/dbt_to_lookml/`: Core package — `parser.py`, `mapper.py`, `generator.py`, `models.py`, CLI in `__main__.py`.
- `tests/`: Pytest suites — `unit/`, `integration/`, plus `test_cli.py`, `test_golden.py`, `test_performance.py`, `test_error_handling.py`, and `fixtures/`.
- `scripts/`: Utilities (e.g., `run-tests.py` orchestrates lint, types, and test modes).
- `Makefile`: Common dev commands. Other docs/specs in `IMPLEMENTATION_PLAN.md`, `CLAUDE.md`, `specs/`, and sample `semantic_models/`.

## Build, Test, and Development Commands
- Install: `make install` (runtime deps via uv), `make dev-install` or `make dev-setup` (adds dev tools).
- Test quick sets: `make test` (unit+integration), `make test-fast`, `make test-full`.
- Quality: `make lint` (ruff), `make type-check` (mypy), `make format` (ruff format+fix), `make quality-gate` (lint+types+tests).
- Coverage report: `make test-coverage` (HTML at `htmlcov/index.html`).
- CI-like run: `make ci-test` (writes `test_results.json`).

## Coding Style & Naming Conventions
- Python 3.13, type hints required; mypy `strict=true`.
- Ruff enforced (line length 88; rules: E,F,I,N,W,UP). Run `make lint` / `make format` before commits.
- Modules, functions, variables: `snake_case`; classes and Pydantic models: `PascalCase`.
- Keep docstrings concise; prefer explicit names over abbreviations.

## Testing Guidelines
- Framework: pytest with markers (`unit`, `integration`, `golden`, `cli`, `performance`, `error_handling`, `smoke`, `slow`).
- Coverage: branch coverage with threshold `--cov-fail-under=95`.
- Naming: files `tests/**/test_*.py`; classes `Test*`; functions `test_*` (configured in `pyproject.toml`).
- Examples: `pytest -m unit -q`, `pytest tests/unit/test_parser.py -q`, or `python scripts/run-tests.py all -v`.

## Commit & Pull Request Guidelines
- Commit style follows Conventional Commits (seen in history): `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`. Use imperative mood and scope where helpful.
- PRs must include: clear description, linked issues, CLI examples (e.g., `dbt-to-lookml generate -i semantic_models -o out --dry-run`), and notes on tests/coverage.
- Before opening: run `make quality-gate` and ensure formatting, typing, and coverage pass.

## Security & Configuration Tips
- Use `uv sync` (via Make targets) to manage locked deps (`uv.lock`). Python version pinned in `.python-version`.
- Generator requires `lkml`; CLI entrypoint is `dbt-to-lookml`.
- Avoid committing secrets; prefer environment variables and local config files ignored by Git.

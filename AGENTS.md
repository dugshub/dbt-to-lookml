# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/dbt_to_lookml/`, with `parser.py`, `mapper.py`, `generator.py`, `models.py`, and the CLI entrypoint in `__main__.py`. Tests sit under `tests/`, split into `unit/`, `integration/`, and targeted suites such as `test_cli.py` and `test_golden.py` with fixtures in `tests/fixtures/`. Utilities like `scripts/run-tests.py` orchestrate CI-like workflows, while reference docs live in `IMPLEMENTATION_PLAN.md`, `CLAUDE.md`, `specs/`, and sample LookML inputs in `semantic_models/`.

## Build, Test, and Development Commands
- `make install` — sync runtime dependencies via `uv`.
- `make dev-install` / `make dev-setup` — add linters, type checkers, and tooling.
- `make test`, `make test-fast`, `make test-full` — run progressively broader pytest suites.
- `make lint`, `make type-check`, `make format` — enforce Ruff style, mypy strict typing, and formatting fixes.
- `make quality-gate` — run lint, type checks, and tests together before commits.
- `dbt-to-lookml generate -i semantic_models -o out --dry-run` — exercise the CLI locally.

## Coding Style & Naming Conventions
Target Python 3.13 with strict typing; annotate functions and dataclasses. Follow Ruff’s 88-character line width, rulesets E,F,I,N,W,UP, and prefer descriptive snake_case for variables and functions, PascalCase for classes and Pydantic models. Keep docstrings concise and only introduce ASCII characters.

## Testing Guidelines
Use pytest with markers like `unit`, `integration`, `cli`, and `golden`. Naming follows `tests/**/test_*.py`, `Test*` classes, and `test_*` functions. Aim for branch coverage ≥95% (`pytest --cov --cov-fail-under=95`) and leverage targeted runs such as `pytest -m unit -q` or `python scripts/run-tests.py all -v` before pushing.

## Commit & Pull Request Guidelines
Write Conventional Commits (e.g., `feat(generator): add lookml flag`). Each PR should link issues, describe the change, cite relevant CLI runs, and note test coverage. Run `make quality-gate` locally, attach output from representative commands, and mention any follow-up work.

## Security & Configuration Tips
Dependencies are locked via `uv.lock`; use `uv sync` (through the Make targets) to stay in sync. Respect `.python-version` when creating virtual environments. Keep secrets out of source control—configure them through environment variables or ignored local files.

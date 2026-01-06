# Contributing to semantic-patterns

Thank you for your interest in contributing to semantic-patterns! This guide will help you get started.

## How to Report Bugs

1. **Check existing issues** - Search [GitHub Issues](https://github.com/dugshub/semantic-patterns/issues) to see if the bug has already been reported
2. **Create a new issue** - If not found, open a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Your environment (Python version, OS, package version)
   - Relevant configuration (sp.yml) and semantic model YAML (sanitized)

## How to Suggest Features

1. **Check existing issues** - Your idea may already be under discussion
2. **Open a feature request** - Create a new issue with:
   - A clear description of the feature
   - The problem it solves or use case it enables
   - Any proposed implementation ideas (optional)

## Development Setup

### Prerequisites

- Python 3.10 or higher
- `uv` (recommended) or `pip`

### Installation

```bash
# Clone the repository
git clone https://github.com/dugshub/semantic-patterns.git
cd semantic-patterns

# Install with development dependencies
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

### Verify Setup

```bash
# Run tests
uv run pytest tests/

# Run type checking
uv run mypy semantic_patterns/

# Run linting
uv run ruff check semantic_patterns/
```

## Code Style

We enforce consistent code style using automated tools:

### Formatting

- **Line length**: 88 characters maximum
- **Formatter**: `ruff format`
- **Import sorting**: Handled by ruff (isort-compatible)

### Linting

- **Linter**: `ruff check`
- **Rules**: E (pycodestyle errors), F (pyflakes), I (isort), N (pep8-naming), W (warnings), UP (pyupgrade)

### Type Checking

- **Type checker**: `mypy --strict`
- **All functions must have type hints**
- **No `Any` types without justification**

### Naming Conventions

- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants

### CLI Output

- Use `rich.console.Console` for terminal output
- Never use bare `print()` statements

## Testing Requirements

All contributions must include appropriate tests:

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_domain.py

# Run with coverage
uv run pytest tests/ --cov=semantic_patterns
```

### Test Guidelines

- Write tests for all new functionality
- Maintain or improve code coverage
- Use descriptive test names that explain the scenario
- Place fixtures in `tests/fixtures/`

## Pull Request Process

### Before Submitting

1. **Create a branch** from `main` for your changes
2. **Write/update tests** for your changes
3. **Run the full test suite** and ensure all tests pass:
   ```bash
   uv run pytest tests/
   ```
4. **Run type checking** and fix any errors:
   ```bash
   uv run mypy semantic_patterns/
   ```
5. **Run linting** and fix any issues:
   ```bash
   uv run ruff check semantic_patterns/
   uv run ruff format semantic_patterns/
   ```

### Submitting

1. **Push your branch** to your fork
2. **Open a Pull Request** against the `main` branch
3. **Fill out the PR template** with:
   - A clear description of the changes
   - Any related issues (use `Fixes #123` to auto-close)
   - Testing performed
4. **Address review feedback** promptly

### PR Guidelines

- Keep PRs focused on a single change
- Write clear commit messages
- Update documentation if needed
- Add changelog entry for user-facing changes

## Questions?

If you have questions about contributing, feel free to:
- Open a GitHub issue with the `question` label
- Start a discussion in GitHub Discussions (if enabled)

Thank you for contributing!

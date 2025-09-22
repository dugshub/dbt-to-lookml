# Installation Guide for dbt-to-lookml

## Quick Install

### From PyPI (when published)
```bash
pip install dbt-to-lookml
```

### From Source (Development)
```bash
git clone https://github.com/yourusername/dbt-to-lookml.git
cd dbt-to-lookml
pip install -e .
```

### Using uv (Recommended for Development)
```bash
git clone https://github.com/yourusername/dbt-to-lookml.git
cd dbt-to-lookml
uv pip install -e .
```

## Building from Source

### Prerequisites
- Python >= 3.13
- pip or uv package manager

### Build Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dbt-to-lookml.git
cd dbt-to-lookml
```

2. Install build dependencies:
```bash
pip install build
# or with uv:
uv pip install build
```

3. Build the package:
```bash
python -m build
```

This creates two files in the `dist/` directory:
- `dbt_to_lookml-0.1.0-py3-none-any.whl` (wheel distribution)
- `dbt_to_lookml-0.1.0.tar.gz` (source distribution)

4. Install the built package:
```bash
pip install dist/dbt_to_lookml-0.1.0-py3-none-any.whl
# or
pip install dist/dbt_to_lookml-0.1.0.tar.gz
```

## Development Installation

For development with all testing and linting tools:

```bash
# Clone the repository
git clone https://github.com/yourusername/dbt-to-lookml.git
cd dbt-to-lookml

# Create virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or using uv:
uv pip install -e ".[dev]"
```

## Verify Installation

After installation, verify that the CLI is available:

```bash
# Check version
dbt-to-lookml --version

# View help
dbt-to-lookml --help

# Test with sample files
dbt-to-lookml validate -i semantic_models/
```

## Publishing to PyPI

For maintainers who want to publish new versions:

1. Update version in `pyproject.toml`
2. Build the package:
```bash
python -m build
```

3. Upload to Test PyPI (optional):
```bash
twine upload --repository testpypi dist/*
```

4. Upload to PyPI:
```bash
twine upload dist/*
```

## Troubleshooting

### Python Version Issues
This package requires Python 3.13 or later. Check your Python version:
```bash
python --version
```

### Import Errors
If you encounter import errors, ensure you're in the correct virtual environment:
```bash
which python
which dbt-to-lookml
```

### Permission Errors
On Unix systems, you may need to use `sudo` for global installation:
```bash
sudo pip install dbt-to-lookml
```

However, using a virtual environment is recommended instead.

## Uninstallation

To remove the package:
```bash
pip uninstall dbt-to-lookml
```
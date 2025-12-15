# Testing Guide

## Test Organization

| Test Type | Location | Purpose |
|-----------|----------|---------|
| Unit | `src/tests/unit/` | Fast, isolated tests for parsers, generators, schemas |
| Integration | `src/tests/integration/` | End-to-end file parsing → LookML generation |
| Golden | `src/tests/test_golden.py` | Compare generated LookML against expected output |
| CLI | `src/tests/test_cli.py` | Test command-line interface |
| Error Handling | `src/tests/test_error_handling.py` | Test error scenarios and recovery |
| Performance | `src/tests/test_performance.py` | Benchmarking (use `--include-slow`) |

## Test Markers

```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.golden
@pytest.mark.cli
@pytest.mark.performance
@pytest.mark.error_handling
@pytest.mark.slow
@pytest.mark.smoke
```

## Commands

```bash
# Testing
make test              # Unit + integration tests
make test-fast         # Unit tests only (fastest feedback)
make test-full         # All test suites

# Single file
python -m pytest src/tests/unit/test_dbt_parser.py -v

# Single method
python -m pytest src/tests/unit/test_lookml_generator.py::TestLookMLGenerator::test_generate_view_lookml -xvs

# With markers
python -m pytest -m "unit and not slow" -v
```

## Coverage Requirements

| Scope | Target |
|-------|--------|
| Overall | 95% branch coverage |
| CI Minimum | 60% (enforced) |
| make test-coverage | 95% (enforced) |

```bash
# Generate HTML report
make test-coverage  # → htmlcov/index.html
```

## Test Isolation Rules

1. **Unit tests**: Never write to disk; use fixtures and mocks
2. **Integration tests**: Use temporary directories via `tmp_path` fixture
3. **Golden tests**: Compare against committed expected files

## Key Test Files

| Feature | Test File |
|---------|-----------|
| Parser | `test_dbt_parser.py` |
| Generator | `test_lookml_generator.py` |
| Schemas | `test_schemas.py` |
| Hidden fields | `test_hidden_parameter.py` |
| BI field filter | `test_bi_field_filter.py` |
| Timezone variants | `test_timezone_variant.py` |
| Wizard detection | `test_wizard_detection.py` |
| Wizard prompts | `test_generate_wizard.py` |

## Performance Testing

```bash
make benchmark        # Performance benchmarks with slow tests
make test-stress      # Stress testing for many models
```

Target: < 500ms for typical generation operations.

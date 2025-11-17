# Implementation Specification: DTL-012
**Issue**: DTL-012 - Update integration and golden tests
**Generated**: 2025-11-12
**Stack**: backend
**Type**: feature

---

## Executive Summary

DTL-012 is the validation and integration testing layer for the timezone conversion epic (DTL-007). This spec defines the detailed implementation plan to:

1. Update golden files to include `convert_tz: no` in all dimension_groups
2. Add comprehensive integration tests for the timezone conversion feature
3. Validate that all existing tests pass without regression
4. Ensure 95%+ branch coverage is maintained

This work depends on the successful completion of:
- **DTL-008**: Dimension schema supports `convert_tz` parameter
- **DTL-009**: LookMLGenerator accepts and propagates `convert_tz`
- **DTL-010**: CLI flags for timezone conversion control
- **DTL-011**: Unit tests for timezone conversion

---

## Detailed Implementation Plan

### Phase 1: Golden File Updates (Estimated: 20 minutes)

#### 1.1 Update expected_users.view.lkml

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_users.view.lkml`

**Current state**: Contains dimension_group for `created_date` without `convert_tz` specification.

**Changes required**:
- Add `convert_tz: no` to the `dimension_group: created_date` block
- Place after the `sql:` line and before `description:`

**Before**:
```lookml
dimension_group: created_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: created_at ;;
  description: "Date when user account was created"
}
```

**After**:
```lookml
dimension_group: created_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: created_at ;;
  convert_tz: no
  description: "Date when user account was created"
}
```

**Validation**:
- File must parse successfully with `lkml.load()`
- No LookML syntax errors
- Test: `test_generate_users_view_matches_golden()` must pass

#### 1.2 Update expected_searches.view.lkml

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_searches.view.lkml`

**Current state**: Contains dimension_group for `search_date` without `convert_tz` specification.

**Changes required**:
- Add `convert_tz: no` to the `dimension_group: search_date` block
- Place after the `sql:` line and before `description:`

**Before**:
```lookml
dimension_group: search_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: searched_at ;;
  description: "Date when search was performed"
}
```

**After**:
```lookml
dimension_group: search_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: searched_at ;;
  convert_tz: no
  description: "Date when search was performed"
}
```

**Validation**:
- File must parse successfully with `lkml.load()`
- No LookML syntax errors
- Test: `test_generate_searches_view_matches_golden()` must pass

#### 1.3 Update expected_rental_orders.view.lkml

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_rental_orders.view.lkml`

**Current state**: Contains dimension_group for `rental_date` without `convert_tz` specification.

**Changes required**:
- Add `convert_tz: no` to the `dimension_group: rental_date` block
- Place after the `sql:` line and before `description:`

**Before**:
```lookml
dimension_group: rental_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: booking_date ;;
  description: "Date of rental booking"
}
```

**After**:
```lookml
dimension_group: rental_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: booking_date ;;
  convert_tz: no
  description: "Date of rental booking"
}
```

**Validation**:
- File must parse successfully with `lkml.load()`
- No LookML syntax errors
- Test: `test_generate_rental_orders_view_matches_golden()` must pass

#### 1.4 Syntax Validation

After updating all three golden files, verify LookML syntax:

```bash
python -c "
import lkml

files = [
    'src/tests/golden/expected_users.view.lkml',
    'src/tests/golden/expected_searches.view.lkml',
    'src/tests/golden/expected_rental_orders.view.lkml',
]

for f in files:
    try:
        parsed = lkml.load(open(f).read())
        print(f'{f}: VALID')
    except Exception as e:
        print(f'{f}: INVALID - {e}')
"
```

**Expected output**: All three files should show VALID.

---

### Phase 2: Integration Test Implementation (Estimated: 45 minutes)

#### 2.1 Test Default convert_tz Behavior

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`

**Location**: Add to `TestEndToEndIntegration` class

**Test method**:
```python
def test_dimension_groups_have_default_convert_tz_no(self) -> None:
    """Test that dimension_groups have convert_tz: no by default."""
    # Parse semantic models with time dimensions
    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
    parser = DbtParser()
    semantic_models = parser.parse_directory(semantic_models_dir)

    # Verify we have models with time dimensions
    assert len(semantic_models) > 0

    # Check that we have at least one model with time dimensions
    has_time_dimension = False
    for model in semantic_models:
        for dimension in model.dimensions:
            if dimension.type == DimensionType.TIME:
                has_time_dimension = True
                break
    assert has_time_dimension, "Test fixture must have models with time dimensions"

    # Generate LookML with default settings
    generator = LookMLGenerator()

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            semantic_models, output_dir
        )

        # Ensure no validation errors
        assert len(validation_errors) == 0, (
            f"Unexpected validation errors: {validation_errors}"
        )

        # Check each view file for dimension_groups
        view_files = list(output_dir.glob("*.view.lkml"))
        assert len(view_files) > 0, "Should generate at least one view file"

        dimension_group_found = False
        for view_file in view_files:
            content = view_file.read_text()

            # If file has dimension_group, it should have convert_tz: no
            if "dimension_group:" in content:
                dimension_group_found = True
                assert "convert_tz: no" in content, (
                    f"View {view_file.name} has dimension_group but missing convert_tz: no. "
                    f"Full content:\n{content}"
                )

        # Ensure at least one dimension_group was found and validated
        assert dimension_group_found, (
            "Test expects at least one dimension_group in generated views"
        )
```

**Validation**:
- Test parses all semantic models from test fixtures
- Test generates LookML with default settings
- Test verifies all dimension_groups explicitly include `convert_tz: no`
- Test fails if any dimension_group lacks `convert_tz: no`

**Expected behavior**: Test should pass, confirming default behavior is `convert_tz: no`

#### 2.2 Test convert_tz Parameter Propagation

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`

**Location**: Add to `TestEndToEndIntegration` class

**Test method**:
```python
def test_generator_convert_tz_parameter_propagates(self) -> None:
    """Test that generator convert_tz parameter is applied to dimension_groups."""
    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
    parser = DbtParser()
    semantic_models = parser.parse_directory(semantic_models_dir)

    assert len(semantic_models) > 0

    # Test with convert_tz=False (explicit default)
    generator_no_tz = LookMLGenerator(convert_tz=False)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator_no_tz.generate_lookml_files(
            semantic_models, output_dir
        )

        assert len(validation_errors) == 0

        # All dimension_groups should have convert_tz: no
        view_files = list(output_dir.glob("*.view.lkml"))
        for view_file in view_files:
            content = view_file.read_text()
            if "dimension_group:" in content:
                assert "convert_tz: no" in content, (
                    f"Generator with convert_tz=False should produce convert_tz: no "
                    f"in {view_file.name}"
                )

    # Test with convert_tz=True
    generator_with_tz = LookMLGenerator(convert_tz=True)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator_with_tz.generate_lookml_files(
            semantic_models, output_dir
        )

        assert len(validation_errors) == 0

        # All dimension_groups should have convert_tz: yes
        view_files = list(output_dir.glob("*.view.lkml"))
        for view_file in view_files:
            content = view_file.read_text()
            if "dimension_group:" in content:
                assert "convert_tz: yes" in content, (
                    f"Generator with convert_tz=True should produce convert_tz: yes "
                    f"in {view_file.name}"
                )
```

**Validation**:
- Test verifies `convert_tz=False` produces `convert_tz: no` in output
- Test verifies `convert_tz=True` produces `convert_tz: yes` in output
- Tests both explicit parameter settings

**Expected behavior**: Test should pass, confirming generator parameter propagates correctly

#### 2.3 Test Dimension Metadata Override

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`

**Location**: Add to `TestEndToEndIntegration` class

**Test method**:
```python
def test_dimension_metadata_convert_tz_override(self) -> None:
    """Test that dimension-level convert_tz metadata can override generator setting."""
    # Parse semantic models
    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
    parser = DbtParser()
    semantic_models = parser.parse_directory(semantic_models_dir)

    assert len(semantic_models) > 0

    # Generate with default settings
    generator = LookMLGenerator()

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            semantic_models, output_dir
        )

        assert len(validation_errors) == 0

        # Verify dimension_groups have proper convert_tz setting
        view_files = list(output_dir.glob("*.view.lkml"))
        assert len(view_files) > 0

        for view_file in view_files:
            content = view_file.read_text()

            # Every dimension_group should have an explicit convert_tz setting
            if "dimension_group:" in content:
                # Should have either convert_tz: yes or convert_tz: no
                has_convert_tz_setting = (
                    "convert_tz: no" in content or "convert_tz: yes" in content
                )
                assert has_convert_tz_setting, (
                    f"View {view_file.name} has dimension_group with no explicit "
                    f"convert_tz setting"
                )
```

**Validation**:
- Test verifies all dimension_groups have explicit `convert_tz` setting
- Test validates both `convert_tz: yes` and `convert_tz: no` are handled correctly

**Expected behavior**: Test should pass, confirming dimension_groups always have explicit convert_tz

---

### Phase 3: Golden File Validation Tests (Estimated: 30 minutes)

#### 3.1 Add Golden File Validation Test

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_golden.py`

**Location**: Add to `TestGoldenFiles` class

**Test method**:
```python
def test_golden_dimension_groups_have_convert_tz(self, golden_dir: Path) -> None:
    """Test that golden files have convert_tz: no in all dimension_groups.

    This validates that the golden files reflect the new default behavior where
    all dimension_groups explicitly include convert_tz: no.
    """
    golden_files = [
        golden_dir / "expected_users.view.lkml",
        golden_dir / "expected_searches.view.lkml",
        golden_dir / "expected_rental_orders.view.lkml",
    ]

    files_checked = 0
    dimension_groups_found = 0

    for golden_file in golden_files:
        if not golden_file.exists():
            # Skip non-existent golden files
            continue

        files_checked += 1
        content = golden_file.read_text()

        # Count dimension_group blocks in this file
        dimension_groups_in_file = content.count("dimension_group:")
        dimension_groups_found += dimension_groups_in_file

        # If file has dimension_group, should have convert_tz: no
        if dimension_groups_in_file > 0:
            assert "convert_tz: no" in content, (
                f"Golden file {golden_file.name} has {dimension_groups_in_file} "
                f"dimension_group(s) but missing convert_tz: no. "
                f"File content:\n{content}"
            )

    # Ensure we checked at least some golden files
    assert files_checked > 0, (
        "Golden files should exist at expected locations"
    )

    # Ensure we found dimension_groups to validate
    assert dimension_groups_found > 0, (
        "Golden files should contain dimension_groups to validate"
    )
```

**Validation**:
- Test verifies golden files exist and are readable
- Test checks that dimension_groups have `convert_tz: no`
- Test counts and reports findings

**Expected behavior**: Test should pass with all golden files containing proper convert_tz settings

#### 3.2 Update Golden File Comparison Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_golden.py`

**No changes needed**, but the existing comparison tests will now pass because:
- The golden files will include `convert_tz: no`
- The generator now (from DTL-008/009/011) produces `convert_tz: no` by default
- The comparison will succeed because generated output matches golden files

**Tests affected**:
- `test_generate_users_view_matches_golden()` - will pass after golden file update
- `test_generate_searches_view_matches_golden()` - will pass after golden file update
- `test_generate_rental_orders_view_matches_golden()` - will pass after golden file update

---

### Phase 4: Verification and Testing (Estimated: 45 minutes)

#### 4.1 Run Golden Tests

**Command**:
```bash
python -m pytest src/tests/test_golden.py -xvs
```

**Expected output**:
- All golden file comparison tests pass
- New `test_golden_dimension_groups_have_convert_tz()` test passes
- No failures or skips

**Success criteria**:
- Test output shows: `PASSED test_golden_dimension_groups_have_convert_tz`
- Test output shows: `PASSED test_generate_users_view_matches_golden`
- Test output shows: `PASSED test_generate_searches_view_matches_golden`
- Test output shows: `PASSED test_generate_rental_orders_view_matches_golden`

#### 4.2 Run Integration Tests

**Command**:
```bash
python -m pytest src/tests/integration/test_end_to_end.py -xvs
```

**Expected output**:
- New integration tests pass:
  - `test_dimension_groups_have_default_convert_tz_no()` ✓
  - `test_generator_convert_tz_parameter_propagates()` ✓
  - `test_dimension_metadata_convert_tz_override()` ✓
- All existing integration tests continue to pass
- No new failures

**Success criteria**:
- All three new tests marked as PASSED
- No regressions in existing tests

#### 4.3 Run Full Test Suite

**Command**:
```bash
make test-full
```

**Expected output**:
- Unit tests pass
- Integration tests pass
- Golden tests pass
- CLI tests pass
- Error handling tests pass
- All tests pass without failures

**Success criteria**:
- Test summary shows all test categories passing
- No failures, errors, or skips
- Coverage report shows 95%+ branch coverage maintained

#### 4.4 Verify Coverage

**Command**:
```bash
make test-coverage
```

**Expected output**:
- Coverage report generated
- Branch coverage ≥ 95%
- HTML report available at `htmlcov/index.html`

**Success criteria**:
- Total branch coverage ≥ 95%
- No coverage regression compared to baseline
- All modified files have adequate coverage

---

## Testing Strategy

### Test Execution Order

1. **Golden file syntax validation** (manual check)
   - Parse each golden file with `lkml.load()`
   - Verify no syntax errors

2. **Golden file unit tests** (automated)
   - `test_golden_dimension_groups_have_convert_tz()`
   - `test_generate_*_view_matches_golden()` (existing tests)

3. **Integration tests** (automated)
   - `test_dimension_groups_have_default_convert_tz_no()`
   - `test_generator_convert_tz_parameter_propagates()`
   - `test_dimension_metadata_convert_tz_override()`

4. **Full test suite** (comprehensive validation)
   - `make test-full` - all test categories
   - `make test-coverage` - coverage verification

### Test Data Requirements

**Semantic models**: Already exist from DTL-006
- `src/semantic_models/sem_users.yml` - contains time dimension `created_date`
- `src/semantic_models/sem_searches.yml` - contains time dimension `search_date`
- `src/semantic_models/sem_rental_orders.yml` - contains time dimension `rental_date`

**Golden files**: To be updated
- `src/tests/golden/expected_users.view.lkml`
- `src/tests/golden/expected_searches.view.lkml`
- `src/tests/golden/expected_rental_orders.view.lkml`

### Dependencies and Prerequisites

**Must be complete before starting DTL-012**:
- ✓ DTL-008: Dimension schema supports `convert_tz` parameter
  - `Dimension._to_dimension_group_dict()` includes `convert_tz: no` by default
  - `ConfigMeta` model includes `convert_tz` field

- ✓ DTL-009: LookMLGenerator accepts and propagates `convert_tz`
  - `LookMLGenerator.__init__()` accepts `convert_tz` parameter
  - Generator passes convert_tz to dimension conversion

- ✓ DTL-010: CLI flags for timezone conversion control
  - `--convert-tz` and `--no-convert-tz` flags implemented
  - Flags passed to `LookMLGenerator` constructor

- ✓ DTL-011: Unit tests for timezone conversion
  - Unit tests pass validating timezone conversion behavior
  - Tests cover all precedence scenarios

---

## Implementation Checklist

### Pre-Implementation Verification
- [ ] DTL-008 dependencies met (Dimension schema)
- [ ] DTL-009 dependencies met (Generator propagation)
- [ ] DTL-010 dependencies met (CLI flags)
- [ ] DTL-011 dependencies met (Unit tests)
- [ ] Current golden files exist and are valid
- [ ] Semantic model fixtures parse correctly
- [ ] `make test-unit` baseline passes

### Golden File Updates
- [ ] Update `expected_users.view.lkml` - add `convert_tz: no`
- [ ] Update `expected_searches.view.lkml` - add `convert_tz: no`
- [ ] Update `expected_rental_orders.view.lkml` - add `convert_tz: no`
- [ ] Verify syntax with `lkml.load()` for all three files
- [ ] Ensure all dimension_groups have `convert_tz: no`

### Integration Test Implementation
- [ ] Add `test_dimension_groups_have_default_convert_tz_no()` to test_end_to_end.py
- [ ] Add `test_generator_convert_tz_parameter_propagates()` to test_end_to_end.py
- [ ] Add `test_dimension_metadata_convert_tz_override()` to test_end_to_end.py
- [ ] Verify all new tests can import required modules
- [ ] Verify tests use correct assertion patterns

### Golden File Validation Tests
- [ ] Add `test_golden_dimension_groups_have_convert_tz()` to test_golden.py
- [ ] Test handles missing golden files gracefully
- [ ] Test provides clear error messages for failures

### Testing and Verification
- [ ] Run `python -m pytest src/tests/test_golden.py -xvs` - all pass
- [ ] Run `python -m pytest src/tests/integration/test_end_to_end.py -xvs` - all pass
- [ ] Run `make test-full` - all test categories pass
- [ ] Run `make test-coverage` - verify 95%+ branch coverage
- [ ] No regressions in existing tests

### Final Validation
- [ ] All acceptance criteria met
- [ ] Issue status updated to `ready` (from `awaiting-strategy-review`)
- [ ] Label `state:has-spec` added
- [ ] All test output captured and reviewed

---

## Success Metrics

### Quantitative Metrics

| Metric | Target | Success Criteria |
|--------|--------|------------------|
| Golden files updated | 3 | All three updated with `convert_tz: no` |
| New integration tests | 3 | All three added and passing |
| New golden validation tests | 1 | Test added and passing |
| Test pass rate | 100% | No failures or regressions |
| Branch coverage | ≥95% | Maintained or improved |
| LookML syntax validation | 100% | All golden files parse successfully |

### Qualitative Metrics

- All dimension_groups explicitly include `convert_tz` setting
- Generated output matches golden files exactly
- Tests clearly document timezone conversion behavior
- No regressions in existing functionality
- Error messages are helpful for debugging

---

## Known Constraints and Considerations

### LookML Syntax

The `convert_tz` property must appear as a property within the `dimension_group` block:

```lookml
dimension_group: example {
  type: time
  timeframes: [...]
  sql: ... ;;
  convert_tz: no
  description: "..."
}
```

Not as a separate statement or outside the block.

### Whitespace and Formatting

Golden file comparisons are exact text matches, so:
- Whitespace must match exactly
- Property order should match generator output
- Indentation must be consistent

Generated files use LKML formatter which produces consistent formatting, so updating golden files to match generator output ensures tests will pass.

### Test Isolation

Integration tests use `TemporaryDirectory()` to isolate file I/O:
- No shared state between tests
- Files are cleaned up automatically
- Tests can run in any order

### Backward Compatibility

The changes should not break existing code:
- Golden files are test fixtures only
- No public API changes required
- Generator changes are backward compatible (convert_tz parameter optional)

---

## Risk Analysis

### Low Risk Areas

- Golden file updates are straightforward additions
- Tests use existing fixtures and utilities
- Integration tests follow established patterns
- No changes to core generation logic required

### Potential Issues

| Issue | Mitigation |
|-------|-----------|
| Whitespace mismatch in golden files | Use exact formatter output when updating |
| Test flakiness | Use consistent temporary directories and cleanup |
| Coverage regression | Run full coverage report before finalizing |
| Missing dependency implementation | Verify DTL-008/009/010/011 complete before starting |

---

## Implementation Notes

### Golden File Format

When updating golden files manually:

1. Edit the file with a text editor
2. Find the `dimension_group:` block
3. Add `convert_tz: no` after the `sql:` line
4. Ensure proper indentation (2 spaces per level)
5. Verify syntax with: `python -c "import lkml; lkml.load(open('file').read())"`

### Import Statements

Integration tests require these imports:
```python
from pathlib import Path
from tempfile import TemporaryDirectory
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.types import DimensionType
```

Ensure these are already imported in test_end_to_end.py.

### Test Method Naming

Follow existing naming convention:
- `test_<feature>_<expected_outcome>`
- Use clear, descriptive names
- Include docstring explaining test purpose

---

## Acceptance Criteria

### Functional Requirements

1. **Golden files updated**
   - [ ] `expected_users.view.lkml` includes `convert_tz: no` in dimension_group
   - [ ] `expected_searches.view.lkml` includes `convert_tz: no` in dimension_group
   - [ ] `expected_rental_orders.view.lkml` includes `convert_tz: no` in dimension_group

2. **Integration tests added**
   - [ ] `test_dimension_groups_have_default_convert_tz_no()` validates default behavior
   - [ ] `test_generator_convert_tz_parameter_propagates()` validates parameter propagation
   - [ ] `test_dimension_metadata_convert_tz_override()` validates metadata override

3. **Golden file validation**
   - [ ] `test_golden_dimension_groups_have_convert_tz()` validates golden files

4. **All tests pass**
   - [ ] Golden tests pass: `make test-golden` or `pytest src/tests/test_golden.py`
   - [ ] Integration tests pass: `pytest src/tests/integration/test_end_to_end.py`
   - [ ] Full suite passes: `make test-full`

5. **Coverage maintained**
   - [ ] Branch coverage ≥ 95%
   - [ ] No coverage regression from baseline

### Non-Functional Requirements

1. **Code quality**
   - [ ] Type hints correct (mypy passes)
   - [ ] Code follows style guide
   - [ ] Docstrings present for all new methods

2. **Documentation**
   - [ ] Test docstrings explain purpose and expected behavior
   - [ ] Comments explain non-obvious logic

3. **Test organization**
   - [ ] Tests in correct files
   - [ ] Tests use correct fixtures and helpers
   - [ ] Test names follow conventions

---

## Estimation

| Phase | Task | Time Estimate |
|-------|------|----------------|
| 1 | Update 3 golden files | 20 min |
| 2 | Add 3 integration tests | 45 min |
| 3 | Add golden validation test | 30 min |
| 4 | Verification and testing | 45 min |
| **Total** | **Complete implementation** | **~2.5 hours** |

---

## Related Issues and Epics

- **Epic**: DTL-007 - Implement timezone conversion configuration feature
- **Dependencies**: DTL-008, DTL-009, DTL-010, DTL-011
- **Blocks**: DTL-013 - Documentation for timezone conversion

---

## Additional Resources

### LookML Documentation

- LookML dimension_group: https://cloud.google.com/looker/docs/reference/param-explore-dimension-group
- convert_tz property: https://cloud.google.com/looker/docs/reference/param-dimension-group-convert-tz

### Python Testing Tools

- pytest documentation: https://docs.pytest.org/
- lkml library: https://github.com/joshtemple/lkml

### Project Documentation

- CLAUDE.md - Project architecture and patterns
- Test organization - src/tests/
- Golden files - src/tests/golden/

---

## Approval and Status

**Status**: Ready for Implementation
**Created**: 2025-11-12
**Updated**: 2025-11-12

To proceed with implementation:
1. Review this specification
2. Verify all dependencies (DTL-008, 009, 010, 011) are complete
3. Begin with Phase 1: Golden File Updates
4. Follow implementation checklist
5. Execute testing phases
6. Update issue status upon completion

# Implementation Strategy: DTL-012

**Issue**: DTL-012 - Update integration and golden tests
**Analyzed**: 2025-11-12T20:00:00Z
**Stack**: backend
**Type**: feature

## Approach

Update integration tests and golden files to reflect the new default behavior (`convert_tz: no`) in generated LookML dimension_groups. This involves:

1. Updating golden files to include `convert_tz: no` in all dimension_group blocks
2. Ensuring integration tests validate the timezone conversion feature works correctly
3. Running the full test suite to confirm no regressions
4. Maintaining test coverage at 95%+ branch coverage

This is the validation layer for the timezone conversion configuration epic (DTL-007), ensuring that:
1. Generated dimension_groups explicitly include `convert_tz: no` by default
2. Integration tests validate timezone conversion behavior at all levels
3. All existing tests continue to pass without modification
4. Coverage remains at 95%+

## Architecture Impact

**Layer**: Testing (validation layer for schemas + generators)

**Files to Modify**:
- `src/tests/golden/expected_users.view.lkml` - Add `convert_tz: no` to dimension_group
- `src/tests/golden/expected_searches.view.lkml` - Add `convert_tz: no` to dimension_group
- `src/tests/golden/expected_rental_orders.view.lkml` - Add `convert_tz: no` to dimension_group
- `src/tests/test_golden.py` - Add tests for `convert_tz` in dimension_groups
- `src/tests/integration/test_end_to_end.py` - Add integration test for `convert_tz` flow

**No new files needed**: Fixtures and semantic models already exist from DTL-006

## Dependencies

- **Depends on**:
  - DTL-008: Dimension schema supports `convert_tz` parameter (MUST be complete)
  - DTL-009: LookMLGenerator accepts and propagates `convert_tz` settings (MUST be complete)
  - DTL-010: CLI flags for timezone conversion control (MUST be complete)
  - DTL-011: Unit tests for timezone conversion (MUST be complete)

- **Blocking**: DTL-013 (documentation depends on tests passing)

- **Test Data Requirements**:
  - Existing semantic model fixtures: `src/semantic_models/sem_users.yml`, `src/semantic_models/sem_searches.yml`, `src/semantic_models/sem_rental_orders.yml`
  - All contain time dimensions (created_date, search_date, rental_date) that will generate dimension_groups

## Testing Strategy

### Golden File Updates

**Current State Analysis**:
- Three golden view files exist with dimension_groups (no `convert_tz` yet):
  - `expected_users.view.lkml` - has `dimension_group: created_date`
  - `expected_searches.view.lkml` - has `dimension_group: search_date`
  - `expected_rental_orders.view.lkml` - has `dimension_group: rental_date`
- All dimension_groups are missing `convert_tz: no` which should now be the explicit default

**Update Process**:

1. **Add `convert_tz: no` to each dimension_group**:
   - In `expected_users.view.lkml`:
     ```lookml
     dimension_group: created_date {
       type: time
       timeframes: [date, week, month, quarter, year]
       sql: created_at ;;
       convert_tz: no
       description: "Date when user account was created"
     }
     ```

   - In `expected_searches.view.lkml`:
     ```lookml
     dimension_group: search_date {
       type: time
       timeframes: [date, week, month, quarter, year]
       sql: searched_at ;;
       convert_tz: no
       description: "Date when search was performed"
     }
     ```

   - In `expected_rental_orders.view.lkml`:
     ```lookml
     dimension_group: rental_date {
       type: time
       timeframes: [date, week, month, quarter, year]
       sql: booking_date ;;
       convert_tz: no
       description: "Date of rental booking"
     }
     ```

2. **Regenerate expected output files** (method already exists in test_golden.py):
   - The helper method `update_golden_files_if_requested()` can be extended
   - Or manually run generator and inspect output

3. **Verify all dimension_groups have `convert_tz: no`**:
   - Run: `grep -n "convert_tz" src/tests/golden/expected_*.view.lkml`
   - Should show 3 occurrences (one per file)
   - All should have `convert_tz: no`

### Integration Test Updates

**Location**: `src/tests/integration/test_end_to_end.py`

**New test methods to add**:

1. **Test default `convert_tz` behavior**:
   ```python
   def test_dimension_groups_have_default_convert_tz_no(self) -> None:
       """Test that dimension_groups have convert_tz: no by default."""
       # Parse semantic models with time dimensions
       semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
       parser = DbtParser()
       semantic_models = parser.parse_directory(semantic_models_dir)

       # Generate LookML
       generator = LookMLGenerator()

       with TemporaryDirectory() as temp_dir:
           output_dir = Path(temp_dir)
           generated_files, validation_errors = generator.generate_lookml_files(
               semantic_models, output_dir
           )

           assert len(validation_errors) == 0

           # Check each view file for dimension_groups
           for view_file in output_dir.glob("*.view.lkml"):
               content = view_file.read_text()

               # If file has dimension_group, it should have convert_tz: no
               if "dimension_group:" in content:
                   assert "convert_tz: no" in content, (
                       f"View {view_file.name} has dimension_group but missing convert_tz: no"
                   )
   ```

2. **Test `convert_tz` parameter propagation**:
   ```python
   def test_generator_convert_tz_parameter_propagates(self) -> None:
       """Test that generator convert_tz parameter is applied to dimension_groups."""
       semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
       parser = DbtParser()
       semantic_models = parser.parse_directory(semantic_models_dir)

       # Test with convert_tz=False (explicit)
       generator_no_tz = LookMLGenerator(convert_tz=False)

       with TemporaryDirectory() as temp_dir:
           output_dir = Path(temp_dir)
           generated_files, validation_errors = generator_no_tz.generate_lookml_files(
               semantic_models, output_dir
           )

           assert len(validation_errors) == 0

           # All dimension_groups should have convert_tz: no
           for view_file in output_dir.glob("*.view.lkml"):
               content = view_file.read_text()
               if "dimension_group:" in content:
                   assert "convert_tz: no" in content
   ```

3. **Test CLI flag integration**:
   ```python
   def test_cli_convert_tz_flag_affects_output(self) -> None:
       """Test that --no-convert-tz CLI flag produces LookML with convert_tz: no."""
       # This test verifies the full flow from CLI through generator
       semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
       parser = DbtParser()
       semantic_models = parser.parse_directory(semantic_models_dir)

       # Simulate CLI with --no-convert-tz flag (the default)
       generator = LookMLGenerator(convert_tz=False)

       with TemporaryDirectory() as temp_dir:
           output_dir = Path(temp_dir)
           generated_files, validation_errors = generator.generate_lookml_files(
               semantic_models, output_dir
           )

           assert len(validation_errors) == 0

           # Verify output includes convert_tz: no
           for view_file in output_dir.glob("*.view.lkml"):
               content = view_file.read_text()
               if "dimension_group:" in content:
                   assert "convert_tz: no" in content, (
                       f"View {view_file.name} dimension_group missing convert_tz: no"
                   )
   ```

4. **Test dimension-level metadata override**:
   ```python
   def test_dimension_metadata_convert_tz_override(self) -> None:
       """Test that per-dimension convert_tz metadata overrides generator setting."""
       # Parse semantic model
       semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
       parser = DbtParser()

       # Parse users model which has metadata configuration
       users_file = semantic_models_dir / "sem_users.yml"
       semantic_models = parser.parse_file(users_file)

       # Generate with default (convert_tz: no)
       generator = LookMLGenerator()

       with TemporaryDirectory() as temp_dir:
           output_dir = Path(temp_dir)
           generated_files, validation_errors = generator.generate_lookml_files(
               semantic_models, output_dir
           )

           assert len(validation_errors) == 0

           users_view = output_dir / "users.view.lkml"
           content = users_view.read_text()

           # Verify dimension_group has convert_tz setting
           # (could be no, or yes if overridden in metadata)
           assert "dimension_group:" in content
           # Should have explicit convert_tz setting
           assert ("convert_tz: no" in content or "convert_tz: yes" in content)
   ```

**Updates to existing tests**:

In `src/tests/test_golden.py`, add method to verify golden files:

```python
def test_golden_dimension_groups_have_convert_tz(self, golden_dir: Path) -> None:
    """Test that golden files have convert_tz: no in dimension_groups."""
    golden_files = [
        golden_dir / "expected_users.view.lkml",
        golden_dir / "expected_searches.view.lkml",
        golden_dir / "expected_rental_orders.view.lkml",
    ]

    for golden_file in golden_files:
        if golden_file.exists():
            content = golden_file.read_text()

            # If file has dimension_group, should have convert_tz: no
            if "dimension_group:" in content:
                assert "convert_tz: no" in content, (
                    f"Golden file {golden_file.name} has dimension_group without convert_tz: no"
                )
```

### Test Execution Plan

**Manual update of golden files** (recommended approach):

1. **Manually edit each golden file**:
   ```bash
   # Edit src/tests/golden/expected_users.view.lkml
   # Add "convert_tz: no" after "sql:" line in dimension_group blocks

   # Edit src/tests/golden/expected_searches.view.lkml
   # Add "convert_tz: no" after "sql:" line in dimension_group blocks

   # Edit src/tests/golden/expected_rental_orders.view.lkml
   # Add "convert_tz: no" after "sql:" line in dimension_group blocks
   ```

2. **Verify LookML syntax is valid**:
   ```bash
   python -c "import lkml; print(lkml.load(open('src/tests/golden/expected_users.view.lkml').read()))"
   ```

3. **Run golden tests**:
   ```bash
   python -m pytest src/tests/test_golden.py -xvs
   ```

4. **Run integration tests**:
   ```bash
   python -m pytest src/tests/integration/test_end_to_end.py -xvs
   ```

5. **Run full test suite**:
   ```bash
   make test-full
   ```

**Alternative: Programmatic regeneration**:

If manual editing is error-prone, use the existing helper method:

```python
# In test_golden.py (manual call during development)
def regenerate_golden_files_with_convert_tz(self, golden_dir: Path) -> None:
    """Helper to regenerate golden files with convert_tz: no.

    Usage: Call manually during development when schema changes.
    Not run as part of regular test suite.
    """
    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
    parser = DbtParser()
    generator = LookMLGenerator()  # Uses default convert_tz=False

    # Parse all fixture models
    all_models = parser.parse_directory(semantic_models_dir)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, _ = generator.generate_lookml_files(
            all_models, output_dir
        )

        # Copy each view file to golden directory
        for generated_file in generated_files:
            if generated_file.name.endswith(".view.lkml"):
                # Extract model name and create golden filename
                content = generated_file.read_text()

                # Find which model this is
                if "view: users" in content:
                    golden_file = golden_dir / "expected_users.view.lkml"
                elif "view: searches" in content:
                    golden_file = golden_dir / "expected_searches.view.lkml"
                elif "view: rental_orders" in content:
                    golden_file = golden_dir / "expected_rental_orders.view.lkml"
                else:
                    continue

                golden_file.write_text(content)
```

## Implementation Sequence

1. **Update schema layer** (dependency: DTL-008 must be complete):
   - Verify `Dimension._to_dimension_group_dict()` includes `convert_tz: no` by default
   - This should already be implemented in DTL-008

2. **Update generator layer** (dependency: DTL-009 must be complete):
   - Verify `LookMLGenerator.__init__()` accepts `convert_tz` parameter
   - Verify parameter is propagated to dimension generation
   - This should already be implemented in DTL-009

3. **Update CLI layer** (dependency: DTL-010 must be complete):
   - Verify `--convert-tz` and `--no-convert-tz` flags work correctly
   - This should already be implemented in DTL-010

4. **Verify unit tests** (dependency: DTL-011 must be complete):
   - Run: `python -m pytest src/tests/unit/ -v`
   - All should pass with timezone conversion features

5. **Update golden files** (30 min):
   - Manually edit or programmatically regenerate:
   - `src/tests/golden/expected_users.view.lkml`
   - `src/tests/golden/expected_searches.view.lkml`
   - `src/tests/golden/expected_rental_orders.view.lkml`
   - Add `convert_tz: no` to dimension_group blocks

6. **Add integration tests** (45 min):
   - Create new test methods in `src/tests/integration/test_end_to_end.py`
   - Test default convert_tz behavior
   - Test generator parameter propagation
   - Test CLI flag integration
   - Test dimension metadata override

7. **Add golden file validation tests** (30 min):
   - Add test in `src/tests/test_golden.py`
   - Verify all golden dimension_groups have `convert_tz: no`
   - Verify generated output matches golden files

8. **Run full test suite** (45 min):
   - `make test-full` - Run all tests
   - `make test-coverage` - Verify 95%+ branch coverage
   - Fix any regressions or failures

## Validation Criteria

### Golden File Content

After updates, each golden file should have dimension_groups like:

**expected_users.view.lkml**:
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

**expected_searches.view.lkml**:
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

**expected_rental_orders.view.lkml**:
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

### Test Verification

1. **Syntax validation**:
   - All golden files parse successfully with `lkml.load()`
   - No malformed LookML syntax

2. **Generate matches golden**:
   - `test_generate_users_view_matches_golden()` passes
   - `test_generate_searches_view_matches_golden()` passes
   - `test_generate_rental_orders_view_matches_golden()` passes

3. **Integration tests pass**:
   - `test_dimension_groups_have_default_convert_tz_no()` passes
   - `test_generator_convert_tz_parameter_propagates()` passes
   - `test_cli_convert_tz_flag_affects_output()` passes
   - `test_dimension_metadata_convert_tz_override()` passes

4. **No regressions**:
   - All existing tests in `test_golden.py` pass
   - All existing tests in `test_end_to_end.py` pass
   - Full suite: `make test-full` passes

5. **Coverage maintained**:
   - Branch coverage remains at 95%+
   - `make test-coverage` shows no coverage decrease

## Estimated Complexity

**Complexity**: Low-Medium
**Estimated Time**: 2-3 hours

**Breakdown**:
- Understanding current state: 20 min
- Updating golden files: 20 min
- Adding integration tests: 45 min
- Adding golden file validation: 15 min
- Running test suite and fixing issues: 30 min

**Risk factors**:
- Depends on DTL-008/009/010/011 being fully complete
- Golden file format must match generator output exactly (whitespace, ordering)
- Must ensure no regressions in existing tests

## Success Metrics

- [ ] All three golden view files updated with `convert_tz: no`
- [ ] All golden view files have valid LookML syntax
- [ ] Golden tests pass: `test_generate_*_view_matches_golden()` all pass
- [ ] Golden dimension group tests pass: `test_golden_dimension_groups_have_convert_tz()`
- [ ] Integration tests added and passing for timezone conversion flow
- [ ] No regressions in existing test suite
- [ ] Full test suite passes: `make test-full`
- [ ] Coverage maintained at 95%+

## Pre-Implementation Checklist

Before starting DTL-012 implementation:

- [ ] Verify DTL-008 is complete (Dimension schema updated)
- [ ] Verify DTL-009 is complete (LookMLGenerator accepts convert_tz)
- [ ] Verify DTL-010 is complete (CLI flags implemented)
- [ ] Verify DTL-011 is complete (Unit tests pass)
- [ ] Confirm current golden files exist and are valid
- [ ] Confirm semantic model fixtures exist and parse correctly
- [ ] Check that `make test-unit` passes (baseline)

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-012.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-012`

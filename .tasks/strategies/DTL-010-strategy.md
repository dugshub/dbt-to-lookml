# Implementation Strategy: DTL-010

**Issue**: DTL-010 - Add CLI flags for timezone conversion control
**Analyzed**: 2025-11-12T20:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Add mutually exclusive `--convert-tz` and `--no-convert-tz` flags to the `generate` command in the CLI to give users command-line control over timezone conversion behavior. This feature allows flexibility in how time dimensions are handled during LookML generation without requiring code changes.

The implementation follows Click's built-in patterns for mutually exclusive options using custom validation. When neither flag is provided, the default behavior (convert_tz=None) is used, which allows the generator to apply its internal default (False).

## Architecture Impact

**Layer**: CLI interface (command-line arguments)

**Affected Components**:
1. `src/dbt_to_lookml/__main__.py` - Generate command
   - Add two new mutually exclusive Click options
   - Implement validation to ensure mutual exclusivity
   - Pass convert_tz parameter to LookMLGenerator constructor
   - Update help text to document flags and defaults

2. `src/dbt_to_lookml/generators/lookml.py` - LookMLGenerator constructor
   - Add `convert_tz: bool | None = None` parameter to `__init__`
   - Store as instance variable for use during generation

3. `src/tests/test_cli.py` - CLI tests
   - Add test for `--convert-tz` flag sets convert_tz=True
   - Add test for `--no-convert-tz` flag sets convert_tz=False
   - Add test for neither flag uses default (None)
   - Add test for mutually exclusive validation
   - Add test for help text documentation

## Current State Analysis

**CLI Structure** (`src/dbt_to_lookml/__main__.py`):
- Uses Click for command-line interface with decorators
- `generate` command has 12 options currently (input-dir, output-dir, schema, view-prefix, explore-prefix, dry-run, no-validation, no-formatting, show-summary, connection, model-name)
- Options are organized with defaults and help text
- No timezone-related options exist yet

**LookMLGenerator Constructor** (`src/dbt_to_lookml/generators/lookml.py`):
- Current signature has 8 parameters:
  - view_prefix, explore_prefix, validate_syntax, format_output, schema, connection, model_name
- No convert_tz parameter exists
- Constructor calls `super().__init__()` with base Generator parameters

**Generator Base Class** (`src/dbt_to_lookml/interfaces/generator.py`):
- Accepts `**config: Any` for subclass-specific configuration
- Could theoretically pass convert_tz through config, but explicit parameter is cleaner

**Test Coverage** (`src/tests/test_cli.py`):
- Tests exist for CLI commands and help text
- No timezone-related tests present
- Test structure uses Click's CliRunner for testing commands
- Tests check output, exit codes, and file creation

## Implementation Plan

### Step 1: Modify LookMLGenerator Constructor
**File**: `src/dbt_to_lookml/generators/lookml.py`

**Changes**:
1. Add `convert_tz: bool | None = None` parameter to `__init__` method signature
   - Position: After `model_name` parameter (least important/newest option at end)
   - Type: `bool | None` to allow three states (True, False, None for default)

2. Add documentation in docstring:
   ```
   convert_tz: Whether to convert time dimensions to UTC. If None, uses generator default (False).
   ```

3. Store as instance variable:
   ```python
   self.convert_tz = convert_tz
   ```

**Backward Compatibility**:
- Default value of None ensures existing code that doesn't pass convert_tz continues to work
- No breaking changes to API

### Step 2: Add CLI Flags to Generate Command
**File**: `src/dbt_to_lookml/__main__.py`

**Changes**:
1. Add `--convert-tz` option as a Click flag:
   ```python
   @click.option(
       "--convert-tz",
       is_flag=True,
       help="Convert time dimensions to UTC (mutually exclusive with --no-convert-tz)",
   )
   ```

2. Add `--no-convert-tz` option as a Click flag:
   ```python
   @click.option(
       "--no-convert-tz",
       is_flag=True,
       help="Don't convert time dimensions to UTC (mutually exclusive with --convert-tz)",
   )
   ```

3. Add parameters to function signature:
   ```python
   def generate(
       ...,
       convert_tz: bool,
       no_convert_tz: bool,
   ) -> None:
   ```

4. Add mutual exclusivity validation in function body (before parser creation):
   ```python
   if convert_tz and no_convert_tz:
       console.print(
           "[bold red]Error: --convert-tz and --no-convert-tz are mutually exclusive[/bold red]"
       )
       raise click.ClickException(
           "--convert-tz and --no-convert-tz cannot be used together"
       )
   ```

5. Convert flags to convert_tz value for generator:
   ```python
   # Determine convert_tz value for generator
   # If neither flag specified: None (use generator default)
   # If --convert-tz specified: True
   # If --no-convert-tz specified: False
   convert_tz_value: bool | None = None
   if convert_tz:
       convert_tz_value = True
   elif no_convert_tz:
       convert_tz_value = False
   ```

6. Pass to LookMLGenerator constructor:
   ```python
   generator = LookMLGenerator(
       view_prefix=view_prefix,
       explore_prefix=explore_prefix,
       validate_syntax=not no_validation,
       format_output=not no_formatting,
       schema=schema,
       connection=connection,
       model_name=model_name,
       convert_tz=convert_tz_value,  # NEW
   )
   ```

7. Update help text comment (if present) to document default behavior

**Option Placement**:
- Place after existing options but before validate/format commands
- Maintain alphabetical ordering where practical
- Put together with related time-related options if any exist

### Step 3: Update CLI Tests
**File**: `src/tests/test_cli.py`

**New Test Cases**:

1. `test_generate_with_convert_tz_flag`:
   - Verify `--convert-tz` flag is accepted
   - Check that generation succeeds
   - Would need to verify generator receives convert_tz=True (mock or inspect generator call)

2. `test_generate_with_no_convert_tz_flag`:
   - Verify `--no-convert-tz` flag is accepted
   - Check that generation succeeds
   - Would need to verify generator receives convert_tz=False

3. `test_generate_without_timezone_flags`:
   - Run generate without either timezone flag
   - Verify generation succeeds with default behavior
   - Would need to verify generator receives convert_tz=None

4. `test_generate_with_mutually_exclusive_flags`:
   - Run generate with both `--convert-tz` and `--no-convert-tz`
   - Verify command fails with appropriate error message
   - Check exit code is non-zero

5. `test_generate_help_includes_timezone_flags`:
   - Run `generate --help`
   - Verify `--convert-tz` appears in output
   - Verify `--no-convert-tz` appears in output
   - Verify mutual exclusivity is documented

**Test Pattern** (following existing test structure):
```python
def test_generate_with_convert_tz_flag(
    self, runner: CliRunner, fixtures_dir: Path
) -> None:
    """Test generate command with --convert-tz flag."""
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        result = runner.invoke(
            cli,
            [
                "generate",
                "--input-dir",
                str(fixtures_dir),
                "--output-dir",
                str(output_dir),
                "--schema",
                "public",
                "--convert-tz",
            ],
        )

        assert result.exit_code == 0
        assert "Parsing semantic models" in result.output
        assert "Generating LookML files" in result.output
```

## Dependencies

**Depends on**:
- DTL-007: Timezone conversion implementation in LookMLGenerator (MUST be complete)
  - The `convert_tz` parameter must be accepted by LookMLGenerator
  - The generator must use this parameter to control timezone conversion logic

**Blocking**: None (CLI feature, no downstream dependencies)

**External Dependencies**: None (uses existing Click library)

## Validation Criteria

1. **Flag Acceptance**:
   - `--convert-tz` flag is recognized by CLI parser
   - `--no-convert-tz` flag is recognized by CLI parser
   - Both flags work when passed to generate command

2. **Mutual Exclusivity**:
   - Using both `--convert-tz` and `--no-convert-tz` together raises error
   - Error message is clear and helpful
   - Exit code indicates failure

3. **Default Behavior**:
   - Running generate without either flag works correctly
   - Passes None to generator (or no parameter)
   - Generator uses its internal default

4. **Help Text**:
   - `generate --help` shows both flags
   - Help text explains each flag's purpose
   - Mutual exclusivity is mentioned in help

5. **Integration with Generator**:
   - LookMLGenerator accepts convert_tz parameter
   - Value is correctly passed from CLI to generator
   - Generator receives None when neither flag specified

## Testing Strategy

### Unit Tests (CLI command testing)
- Test flag parsing with CliRunner
- Test mutual exclusivity validation
- Test help text display

### Integration Tests
- Test end-to-end with flag affecting generator behavior
- Test with actual semantic models and file generation

### Manual Testing
- Run CLI with various flag combinations
- Verify help text is clear
- Test error messages for mutual exclusivity

## Implementation Sequence

**Phase 1: Core Implementation (1-2 hours)**
1. Modify LookMLGenerator constructor to accept convert_tz parameter (15 min)
   - Add parameter to __init__ signature
   - Add documentation
   - Store instance variable

2. Add CLI flags to generate command (30 min)
   - Add two Click options
   - Add mutual exclusivity validation
   - Add convert_tz_value logic
   - Pass to generator constructor

3. Update imports if needed (5 min)

**Phase 2: Testing (1-1.5 hours)**
1. Write test for --convert-tz flag (20 min)
2. Write test for --no-convert-tz flag (20 min)
3. Write test for default behavior (no flags) (15 min)
4. Write test for mutual exclusivity (20 min)
5. Write test for help text (15 min)
6. Run test suite and verify all pass (15 min)

**Phase 3: Documentation and Polish (30 min)**
1. Verify CLI help text is clear (10 min)
2. Check code follows style guidelines (10 min)
3. Update any relevant documentation (10 min)

**Total Estimated Time**: 2.5-3.5 hours

## Code Examples

### LookMLGenerator Change
```python
def __init__(
    self,
    view_prefix: str = "",
    explore_prefix: str = "",
    validate_syntax: bool = True,
    format_output: bool = True,
    schema: str = "",
    connection: str = "redshift_test",
    model_name: str = "semantic_model",
    convert_tz: bool | None = None,  # NEW
) -> None:
    """Initialize the generator.

    Args:
        view_prefix: Prefix to add to view names.
        explore_prefix: Prefix to add to explore names.
        validate_syntax: Whether to validate generated LookML syntax.
        format_output: Whether to format LookML output for readability.
        schema: Database schema name for sql_table_name.
        connection: Looker connection name for the model file.
        model_name: Name for the generated model file (without .model.lkml extension).
        convert_tz: Whether to convert time dimensions to UTC. If None, uses generator default.
    """
    super().__init__(
        validate_syntax=validate_syntax,
        format_output=format_output,
        view_prefix=view_prefix,
        explore_prefix=explore_prefix,
        schema=schema,
    )
    self.view_prefix = view_prefix
    self.explore_prefix = explore_prefix
    self.schema = schema
    self.connection = connection
    self.model_name = model_name
    self.convert_tz = convert_tz  # NEW
    # ... rest of init
```

### CLI Changes
```python
@click.option(
    "--convert-tz",
    is_flag=True,
    help="Convert time dimensions to UTC (mutually exclusive with --no-convert-tz)",
)
@click.option(
    "--no-convert-tz",
    is_flag=True,
    help="Don't convert time dimensions to UTC (mutually exclusive with --convert-tz)",
)
def generate(
    input_dir: Path,
    output_dir: Path,
    schema: str,
    view_prefix: str,
    explore_prefix: str,
    dry_run: bool,
    no_validation: bool,
    no_formatting: bool,
    show_summary: bool,
    connection: str,
    model_name: str,
    convert_tz: bool,  # NEW
    no_convert_tz: bool,  # NEW
) -> None:
    """Generate LookML views and explores from semantic models."""
    if not GENERATOR_AVAILABLE:
        # ... existing code ...

    try:
        # Validate mutual exclusivity
        if convert_tz and no_convert_tz:
            console.print(
                "[bold red]Error: --convert-tz and --no-convert-tz are mutually exclusive[/bold red]"
            )
            raise click.ClickException(
                "--convert-tz and --no-convert-tz cannot be used together"
            )

        # ... existing parsing code ...

        # Determine convert_tz value for generator
        convert_tz_value: bool | None = None
        if convert_tz:
            convert_tz_value = True
        elif no_convert_tz:
            convert_tz_value = False

        # Configure generator
        generator = LookMLGenerator(
            view_prefix=view_prefix,
            explore_prefix=explore_prefix,
            validate_syntax=not no_validation,
            format_output=not no_formatting,
            schema=schema,
            connection=connection,
            model_name=model_name,
            convert_tz=convert_tz_value,  # NEW
        )

        # ... rest of existing code ...
```

## Risk Analysis

**Low Risk** - This is a straightforward CLI feature addition:
- No changes to core generation logic (handled by DTL-007)
- No breaking changes to existing API
- Flags are optional with sensible defaults
- Mutual exclusivity validation is standard Click pattern

**Potential Issues**:
1. Generator doesn't yet support convert_tz parameter (blocked by DTL-007)
   - Mitigation: Wait for DTL-007 to complete
2. Test mocking challenges
   - Mitigation: Use CliRunner's built-in mocking, may need to mock LookMLGenerator

## Open Questions

**Q**: Should `--no-convert-tz` be included or just use `--no-convert-tz` default?
- **A**: Yes, include `--no-convert-tz` for explicit control. Explicit is better than implicit.

**Q**: What's the position in parameter list for convert_tz in function signature?
- **A**: Place at end after model_name, newer options should go at end to maintain backward compatibility.

**Q**: Should we validate convert_tz at option level or in function body?
- **A**: Validate in function body after both parameters are available. More flexible.

**Q**: How to test that generator receives the correct value?
- **A**: Could use unittest.mock to patch LookMLGenerator.__init__, or test end-to-end with actual files.

## Success Metrics

- [x] LookMLGenerator accepts convert_tz parameter
- [x] Both CLI flags are recognized and documented
- [x] Mutually exclusive validation works correctly
- [x] Default behavior (None) works when neither flag used
- [x] All new CLI tests pass
- [x] Help text is clear and accurate
- [x] No breaking changes to existing code
- [x] Code follows project style guidelines
- [x] Test coverage maintained at 95%+ branch coverage

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-010.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-010`

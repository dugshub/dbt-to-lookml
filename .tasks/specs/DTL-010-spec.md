# Implementation Spec: DTL-010 - Add CLI flags for timezone conversion control

## Metadata
- **Issue**: DTL-010
- **Stack**: backend
- **Generated**: 2025-11-12T21:00:00Z
- **Strategy**: Approved 2025-11-12T20:30:00Z
- **Type**: feature

## Issue Context

### Problem Statement
Users need command-line control over timezone conversion behavior when generating LookML from semantic models. Currently, timezone conversion is controlled programmatically, but there's no CLI flag to enable or disable it from the command line. This feature adds mutually exclusive `--convert-tz` and `--no-convert-tz` flags to the `generate` command to provide flexible runtime control.

### Solution Approach
Add two mutually exclusive Click option decorators to the `generate` command in the CLI that pass the timezone conversion preference to the `LookMLGenerator` constructor. The implementation follows Click's standard patterns for flag validation and maintains backward compatibility by using `None` as the default, which allows the generator to apply its internal default (False).

### Success Criteria
- `--convert-tz` flag sets convert_tz=True when passed to generator
- `--no-convert-tz` flag sets convert_tz=False when passed to generator
- Flags are mutually exclusive (error raised if both provided)
- Default behavior (neither flag) passes convert_tz=None to generator
- Help text clearly documents both flags and their mutual exclusivity
- All new CLI tests pass
- Code follows project style guidelines (mypy strict, ruff linting)

## Approved Strategy Summary

The strategy focuses on:
1. **LookMLGenerator Constructor**: Add optional `convert_tz: bool | None = None` parameter to accept timezone control
2. **CLI Flags**: Add `--convert-tz` and `--no-convert-tz` as Click options with proper mutual exclusivity validation
3. **Validation Logic**: Implement validation in the generate function body to prevent simultaneous use of both flags
4. **Parameter Flow**: Convert CLI boolean flags to three-state value (True, False, None) before passing to generator
5. **Backward Compatibility**: Ensure existing code paths remain unchanged when flags are not used
6. **Testing**: Create comprehensive test coverage for flag combinations, mutual exclusivity, and help text

## Implementation Plan

### Phase 1: Modify LookMLGenerator Constructor

**Duration**: 15-20 minutes

**Tasks**:
1. Add `convert_tz: bool | None = None` parameter to `LookMLGenerator.__init__()`
2. Add documentation in docstring
3. Store as instance variable

### Phase 2: Add CLI Flags to Generate Command

**Duration**: 30-40 minutes

**Tasks**:
1. Add two `@click.option()` decorators for the flags
2. Add parameters to generate function signature
3. Implement mutual exclusivity validation
4. Implement flag-to-value conversion logic
5. Pass converted value to LookMLGenerator constructor

### Phase 3: Update and Create CLI Tests

**Duration**: 45-60 minutes

**Tasks**:
1. Add test for `--convert-tz` flag
2. Add test for `--no-convert-tz` flag
3. Add test for default behavior (neither flag)
4. Add test for mutually exclusive validation
5. Add test for help text documentation
6. Run all tests and verify passing

### Phase 4: Validation and Polish

**Duration**: 15-20 minutes

**Tasks**:
1. Run mypy type checking
2. Run ruff linting and formatting
3. Verify test coverage remains above 95%
4. Final manual CLI testing with various flag combinations

## Detailed Task Breakdown

### Task 1: Modify LookMLGenerator Constructor

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Action**: Update the `__init__` method signature and implementation

**Current Code Location**: Lines 26-59

**Implementation Guidance**:

Add the new parameter to the method signature:
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
    convert_tz: bool | None = None,  # NEW: Add this parameter
) -> None:
```

Add to the docstring (after model_name documentation):
```python
convert_tz: Whether to convert time dimensions to UTC. If None, uses
    generator default (False).
```

Add instance variable assignment (after line 58, before or after the mapper):
```python
self.convert_tz = convert_tz
```

**Pattern Reference**: See lines 54-58 where other instance variables are set

**Tests**: No direct unit tests needed for this change - tested through CLI integration

### Task 2: Add --convert-tz Option Decorator

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Action**: Add new Click option decorator

**Location**: After line 94 (after --model-name option, before def generate())

**Implementation Guidance**:

```python
@click.option(
    "--convert-tz",
    is_flag=True,
    help="Convert time dimensions to UTC (mutually exclusive with --no-convert-tz)",
)
```

**Pattern Reference**: Lines 81-87 show the --no-formatting flag pattern to follow

### Task 3: Add --no-convert-tz Option Decorator

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Action**: Add second Click option decorator

**Location**: Immediately after the --convert-tz option (before def generate())

**Implementation Guidance**:

```python
@click.option(
    "--no-convert-tz",
    is_flag=True,
    help="Don't convert time dimensions to UTC (mutually exclusive with --convert-tz)",
)
```

**Pattern Reference**: Lines 81-87 show the flag pattern to follow

### Task 4: Update Function Signature

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Action**: Add parameters to generate function

**Location**: Lines 95-107, within the parameter list

**Implementation Guidance**:

Change:
```python
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
) -> None:
```

To:
```python
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
```

**Notes**: Parameters should be added at the end to maintain backward compatibility in documentation

### Task 5: Implement Mutual Exclusivity Validation

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Action**: Add validation logic in function body

**Location**: After line 115 (after GENERATOR_AVAILABLE check), before try block

**Implementation Guidance**:

```python
    # Validate mutual exclusivity of timezone flags
    if convert_tz and no_convert_tz:
        console.print(
            "[bold red]Error: --convert-tz and --no-convert-tz are mutually exclusive[/bold red]"
        )
        raise click.ClickException(
            "--convert-tz and --no-convert-tz cannot be used together"
        )
```

**Pattern Reference**: Similar error handling appears in lines 110-114

### Task 6: Implement Flag-to-Value Conversion

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Action**: Convert CLI flags to convert_tz value

**Location**: Before LookMLGenerator instantiation (around line 187)

**Implementation Guidance**:

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

**Pattern Reference**: Lines 178-186 show similar conditional logic

### Task 7: Pass convert_tz to LookMLGenerator

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Action**: Add convert_tz parameter to generator instantiation

**Location**: Lines 188-196

**Current Code**:
```python
        generator = LookMLGenerator(
            view_prefix=view_prefix,
            explore_prefix=explore_prefix,
            validate_syntax=not no_validation,
            format_output=not no_formatting,
            schema=schema,
            connection=connection,
            model_name=model_name,
        )
```

**Change To**:
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

**Pattern Reference**: This follows the same pattern as other parameters (lines 188-196)

## File Changes Summary

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Why**: LookMLGenerator needs to accept and store the convert_tz parameter

**Changes**:
- Add `convert_tz: bool | None = None` to __init__ parameter list
- Add docstring documentation for the parameter
- Store as instance variable: `self.convert_tz = convert_tz`

**Estimated lines**: ~5 lines added/modified

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py`

**Why**: CLI needs to accept the new flags and validate them

**Changes**:
- Add two `@click.option()` decorators for --convert-tz and --no-convert-tz
- Add two parameters to generate function signature
- Add mutual exclusivity validation (4 lines)
- Add flag-to-value conversion logic (6 lines)
- Pass converted value to LookMLGenerator constructor

**Estimated lines**: ~20 lines added/modified

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`

**Why**: Need comprehensive test coverage for new functionality

**Changes**:
- Add test for --convert-tz flag behavior
- Add test for --no-convert-tz flag behavior
- Add test for default behavior (no flags)
- Add test for mutually exclusive flag validation
- Add test for help text display

**Estimated lines**: ~70-80 lines added (new test methods)

### No Files to Delete

## Testing Strategy

### Unit Tests Location
`/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`

### Test Class
Add tests to existing `TestCLI` class (extends after line 248)

### Test Cases

#### 1. test_generate_with_convert_tz_flag

**Purpose**: Verify --convert-tz flag is recognized and accepted

**Fixture Setup**:
- runner: CliRunner instance
- fixtures_dir: Path to test semantic models

**Test Steps**:
1. Invoke generate command with --convert-tz flag
2. Assert exit_code == 0
3. Assert generation output appears in result

**Expected Output**:
- Command succeeds (exit_code 0)
- "Parsing semantic models" in output
- "Generating LookML files" in output

**Mock/Spy**: Could mock LookMLGenerator to verify convert_tz=True is passed, or test end-to-end with file creation

#### 2. test_generate_with_no_convert_tz_flag

**Purpose**: Verify --no-convert-tz flag is recognized and accepted

**Fixture Setup**: Same as above

**Test Steps**:
1. Invoke generate command with --no-convert-tz flag
2. Assert exit_code == 0
3. Assert generation output appears

**Expected Output**: Same as above test

**Pattern Reference**: See test_generate_with_prefixes (lines 93-128) for structure

#### 3. test_generate_without_timezone_flags

**Purpose**: Verify default behavior when neither flag is provided

**Fixture Setup**: Same as above

**Test Steps**:
1. Invoke generate command without either timezone flag
2. Assert exit_code == 0
3. Verify generation completes normally

**Expected Output**: Normal generation output

**Validation**: Ensures backward compatibility

#### 4. test_generate_with_mutually_exclusive_flags

**Purpose**: Verify mutual exclusivity validation works

**Fixture Setup**: Same as above

**Test Steps**:
1. Invoke generate command with BOTH --convert-tz and --no-convert-tz
2. Assert exit_code != 0 (command fails)
3. Assert error message in output

**Expected Output**:
- exit_code != 0
- "mutually exclusive" in result.output

**Pattern Reference**: test_generate_invalid_input_dir (lines 204-223) shows error case testing

#### 5. test_generate_help_includes_timezone_flags

**Purpose**: Verify help text documents new flags

**Fixture Setup**: runner: CliRunner instance

**Test Steps**:
1. Invoke `cli generate --help`
2. Assert exit_code == 0
3. Assert --convert-tz appears in output
4. Assert --no-convert-tz appears in output
5. Assert help text mentions mutual exclusivity

**Expected Output**:
- exit_code == 0
- "--convert-tz" in result.output
- "--no-convert-tz" in result.output
- "mutually exclusive" or similar text in help

**Pattern Reference**: test_generate_command_help (lines 43-51) shows help text testing

### Integration Tests

#### Full End-to-End Test Pattern

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`

**Optional**: Could add integration test that:
1. Runs with --convert-tz flag
2. Generates LookML files
3. Verifies files contain expected timezone conversion markers

**Note**: This would depend on DTL-007 implementation being complete

### Edge Cases

1. **Flag Order Variation**: Test flags in different order
   - `--convert-tz --no-convert-tz` (should fail)
   - `--no-convert-tz --convert-tz` (should fail)

2. **Other Flags Combination**: Test with other optional flags
   - `--convert-tz --dry-run --show-summary` (should work)
   - `--no-convert-tz --no-validation` (should work)

3. **Flag Case Sensitivity**: Click flags are case-sensitive, no special handling needed

### Test Coverage Target

- Target: 95%+ branch coverage for new code paths
- Validate with: `make test-coverage`
- New test count: 5 main tests + optional edge case tests

### Performance Requirements

- Unit tests should execute in < 100ms each
- Total CLI test suite should complete in < 5 seconds
- Validation commands (`make lint`, `make type-check`) should pass

## Code Patterns to Follow

### From Project Codebase

#### 1. Click Option Pattern (from __main__.py)

**Example**: Lines 81-87 show --no-formatting flag
```python
@click.option(
    "--no-formatting",
    is_flag=True,
    help="Skip LookML output formatting",
)
```

**Apply To**: New --convert-tz and --no-convert-tz options

#### 2. Error Handling Pattern

**Example**: Lines 110-114 show error handling with console output
```python
if not GENERATOR_AVAILABLE:
    console.print(
        "[bold red]Error: LookML generator dependencies not available[/bold red]"
    )
    console.print("Please install required dependencies: pip install lkml")
    raise click.ClickException("Missing dependencies for LookML generation")
```

**Apply To**: Mutual exclusivity validation

#### 3. Conditional Logic Pattern

**Example**: Lines 178-186 show conditional logic for flags
```python
if not dry_run:
    console.print(
        f"[bold blue]Generating LookML files to {output_dir}[/bold blue]"
    )
else:
    console.print(
        f"[bold yellow]Previewing LookML generation for {output_dir}[/bold yellow]"
    )
```

**Apply To**: Convert CLI flags to generator parameter

#### 4. Generator Parameter Pattern

**Example**: Lines 188-196 show passing parameters to generator
```python
generator = LookMLGenerator(
    view_prefix=view_prefix,
    explore_prefix=explore_prefix,
    validate_syntax=not no_validation,
    format_output=not no_formatting,
    schema=schema,
    connection=connection,
    model_name=model_name,
)
```

**Apply To**: Adding convert_tz parameter to constructor call

### Type Hints

All functions must use strict type hints (enforced by mypy --strict):
```python
def generate(
    ...,
    convert_tz: bool,
    no_convert_tz: bool,
) -> None:
```

The convert_tz_value variable should be explicitly typed:
```python
convert_tz_value: bool | None = None
```

### Docstring Style

Follow Google-style docstrings already used in the project:
```python
"""Initialize the generator.

Args:
    convert_tz: Whether to convert time dimensions to UTC. If None, uses
        generator default (False).
"""
```

### Import Requirements

No new imports needed - existing imports sufficient:
- `click` already imported in __main__.py
- `bool | None` union syntax requires Python 3.10+ (project supports 3.9+, use `Optional[bool]` if needed)

**Note**: Check if project uses `from __future__ import annotations` for forward compatibility

## Dependencies

### Existing Dependencies
- `click`: Already used for CLI framework
- `rich.console.Console`: Already used for console output
- `lkml`: Already used for LookML validation

### New Dependencies Needed
None - implementation uses existing dependencies only

### Dependency on Other Issues
- **DTL-007**: Must be complete before this feature is fully functional
  - DTL-007 implements timezone conversion logic in LookMLGenerator
  - DTL-010 adds CLI flags to control DTL-007's feature
  - However, DTL-010 can be implemented independently since we're just adding a parameter
  - The parameter will be stored but may not be used until DTL-007 is complete

### No Blocking Dependencies for Implementation

## Validation Commands

### After Implementation

Run these commands to verify code quality:

```bash
# Format code
make format

# Check linting
make lint

# Type checking
make type-check

# Run unit tests
make test-fast

# Run all tests with coverage
make test-coverage

# Run CLI tests specifically
python -m pytest src/tests/test_cli.py -v

# Quick integration test
uv run python -m dbt_to_lookml generate --help | grep -E "(convert-tz|no-convert-tz)"
```

### Expected Results

- All lint checks pass (ruff)
- All type checks pass (mypy --strict)
- All unit tests pass (pytest)
- New test methods all pass
- Test coverage >= 95% for new code
- Help text displays both flags

## Implementation Notes

### Important Considerations

1. **Mutual Exclusivity Validation Placement**
   - Must occur AFTER both parameters are available
   - Must occur BEFORE using the values
   - Should use Click's exception for consistency

2. **Three-State Parameter**
   - Use `bool | None` type annotation
   - `None` = "not specified, use generator default"
   - `True` = "--convert-tz flag used"
   - `False` = "--no-convert-tz flag used"
   - This allows distinguishing "no flag provided" from "explicit False"

3. **Backward Compatibility**
   - Default parameter value must be None
   - Existing code that creates LookMLGenerator without this param will work fine
   - No breaking changes to API

4. **Help Text Clarity**
   - Each flag should mention it's mutually exclusive
   - Help text should explain what each flag does
   - Consider adding note about "neither flag = use default (False)"

5. **Python Version Compatibility**
   - Project minimum: Python 3.9
   - Union type syntax `bool | None` requires Python 3.10+
   - Use `Optional[bool]` or `Union[bool, None]` for Python 3.9 compatibility
   - Check if project uses `from __future__ import annotations`

### Code Review Checklist

- [ ] Type hints are complete and correct (mypy --strict passes)
- [ ] Docstrings follow Google style
- [ ] No unused imports introduced
- [ ] Line length < 88 characters
- [ ] Mutual exclusivity validation is clear
- [ ] Default behavior preserved (backward compatible)
- [ ] Test coverage >= 95% for new code
- [ ] All existing tests still pass
- [ ] Help text is clear and complete

### Common Pitfalls to Avoid

1. **Don't forget parameter order**: Add at end of function signature
2. **Don't skip mutual exclusivity check**: Required for user experience
3. **Don't use `bool` for CLI flags directly**: Need three-state logic (None/True/False)
4. **Don't modify existing parameters**: Backward compatibility critical
5. **Don't hardcode defaults**: Use class defaults consistently

## Ready for Implementation

This spec is complete and implementation-ready. The strategy has been approved and provides clear architectural direction. All implementation details have been specified with code patterns and file locations clearly marked.

**Implementation should follow the sequential phases**:
1. Modify LookMLGenerator constructor first (independent)
2. Add CLI flags and validation (depends on step 1)
3. Write tests (depends on steps 1-2)
4. Run validation commands and fix any issues (final step)

**Estimated total time**: 2-3 hours for a single developer

---

## Reference Materials

### Related Files
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py` - CLI entry point
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py` - LookMLGenerator class
- `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py` - CLI test file
- `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md` - Project guidelines
- `/Users/dug/Work/repos/dbt-to-lookml/.tasks/strategies/DTL-010-strategy.md` - Approved strategy

### Documentation
- Click documentation: https://click.palletsprojects.com/
- Project testing guide: See CLAUDE.md section on "Test Organization"
- Code style: See CLAUDE.md section on "Code Style"

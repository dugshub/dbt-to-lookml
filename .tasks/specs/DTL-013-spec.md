# Implementation Spec: Update documentation for timezone conversion feature

## Metadata
- **Issue**: DTL-013
- **Stack**: backend (documentation)
- **Type**: chore
- **Generated**: 2025-11-12T20:45:00Z
- **Strategy**: Approved 2025-11-12T20:30:00Z

## Issue Context

### Problem Statement
Update comprehensive project documentation to explain the new timezone conversion configuration feature introduced in the DTL-007 epic. The timezone conversion feature is complete across the codebase (DTL-008 through DTL-012) but lacks integrated documentation explaining configuration precedence, usage patterns, and code examples.

### Solution Approach
Multi-level documentation update covering:
1. **CLAUDE.md** - Comprehensive section documenting timezone conversion with precedence chain and examples
2. **Docstrings** - Enhanced with parameter documentation and usage examples
3. **README.md** - Brief reference note about timezone conversion capabilities
4. **ConfigMeta class** - Document convert_tz field in schema

### Success Criteria
- [ ] CLAUDE.md has comprehensive "Timezone Conversion Configuration" section
- [ ] Section includes 4 configuration levels, precedence chain, and 3+ examples
- [ ] Docstrings updated with examples and type hints
- [ ] ConfigMeta class documents convert_tz field
- [ ] README.md references timezone feature
- [ ] All code examples are syntactically valid
- [ ] Documentation matches implementation behavior
- [ ] Google-style format maintained throughout

## Approved Strategy Summary

**Architecture Impact**: Documentation layer (no code changes to implementation)

**Key Design Decisions**:
1. Insert "Timezone Conversion Configuration" section after "Hierarchy Labels" in CLAUDE.md
2. Include default behavior, all 4 configuration levels, and precedence rules
3. Provide 3+ examples: dimension metadata, generator, and CLI usage
4. Enhance docstrings in `Dimension._to_dimension_group_dict()`, `LookMLGenerator.__init__()`, and `ConfigMeta` class
5. Add optional README.md reference linking to CLAUDE.md for details

**Dependencies**: None (documentation-only, depends on completed features DTL-007 through DTL-012)

**Testing**: Manual/review-based syntax and accuracy validation

## Implementation Plan

### Phase 1: CLAUDE.md Section Addition (60 min)

Add comprehensive timezone conversion section with examples and precedence documentation.

**Tasks**:
1. **Insert "Timezone Conversion Configuration" section**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`
   - Location: After "Hierarchy Labels" section (after line 115)
   - Length: ~450 lines including examples
   - Pattern: Follow existing section structure with markdown formatting
   - Reference: Strategy document lines 59-212 contain complete text to integrate

### Phase 2: ConfigMeta Docstring Update (20 min)

Document the convert_tz field in ConfigMeta class docstring.

**Tasks**:
1. **Update ConfigMeta class docstring**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Location: Class definition around line 25
   - Action: Replace current brief docstring with comprehensive version
   - Reference: Strategy document lines 401-440 contain updated docstring

### Phase 3: Dimension Method Docstring Update (30 min)

Enhance _to_dimension_group_dict() docstring with comprehensive documentation.

**Tasks**:
1. **Update _to_dimension_group_dict() docstring**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Location: Around line 187
   - Action: Replace current brief docstring with comprehensive version
   - Reference: Strategy document lines 228-279 contain updated docstring

### Phase 4: LookMLGenerator Docstring Update (30 min)

Enhance __init__() docstring to document convert_tz parameter.

**Tasks**:
1. **Update LookMLGenerator.__init__() docstring**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`
   - Location: Around line 36
   - Action: Replace current docstring with comprehensive version including convert_tz
   - Reference: Strategy document lines 312-377 contain updated docstring

### Phase 5: README.md Update (15 min)

Add brief reference to timezone conversion feature in README.

**Tasks**:
1. **Add timezone conversion reference to README.md**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/README.md`
   - Location: In "CLI Usage" section (after line 59)
   - Action: Add brief section or note about timezone flags
   - Reference: Strategy document lines 452-468 contain suggested text

### Phase 6: Validation and Testing (30 min)

Manual validation that documentation is accurate and complete.

**Tasks**:
1. **Syntax validation**
   - Verify all code examples are syntactically valid YAML, Python, and LookML
   - Use lkml library to validate LookML examples if needed

2. **Accuracy check**
   - Verify documentation matches implementation behavior
   - Cross-reference with implementation in schemas.py and lookml.py
   - Confirm default behavior is convert_tz: no
   - Verify precedence chain is correct

3. **Consistency check**
   - Ensure all docstrings follow Google-style format
   - Verify cross-references between sections are accurate
   - Check for broken or inconsistent links

## Detailed Task Breakdown

### Task 1: Add CLAUDE.md Section

**File**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Action**: Insert new section after "Hierarchy Labels" section

**Implementation Guidance**:

The section should be inserted after line 115 (after "Implementation: `schemas.py:Dimension.get_dimension_labels()` and `schemas.py:Measure.get_measure_labels()`")

Complete text from strategy document includes:
- Default Behavior subsection explaining convert_tz: no default
- Configuration Levels subsection (4 levels with precedence)
- Examples subsection (3 different configuration approaches)
- Implementation Details subsection explaining code flow
- LookML Output Examples showing actual generated output

**Location Context**:
```markdown
### Hierarchy Labels

[Existing content...]
Implementation: `schemas.py:Dimension.get_dimension_labels()` and `schemas.py:Measure.get_measure_labels()`

### Timezone Conversion Configuration  [INSERT HERE]
[New section content...]

### Parser Error Handling
```

**Pattern Notes**:
- Use markdown formatting consistent with existing sections
- Include code examples in proper markdown code blocks
- Use #### for subsections (level 4 headers)
- Include cross-references to other documentation

**Reference**: Strategy document lines 59-212 contain complete formatted text

**Tests**:
- Verify markdown syntax is valid
- Check that all code examples are properly formatted
- Confirm section flows naturally from Hierarchy Labels to Parser Error Handling

### Task 2: Update ConfigMeta Docstring

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Replace ConfigMeta class docstring (currently lines 25-26)

**Current Docstring**:
```python
class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""
```

**Updated Docstring**:
Should include:
- Description of purpose and supported metadata fields
- Explanation of each attribute with examples
- Special documentation for convert_tz field
- Example showing hierarchy and convert_tz together
- Reference to CLAUDE.md for detailed configuration rules

**Pattern Notes**:
- Google-style docstring format
- Include Attributes: section listing all fields
- Include Example: section showing real YAML
- Keep indentation consistent with existing docstrings

**Reference**: Strategy document lines 401-440 contain complete updated docstring

**Tests**:
- Verify docstring is valid Google-style format
- Check that all attributes are documented
- Confirm example is syntactically valid YAML

### Task 3: Update Dimension._to_dimension_group_dict() Docstring

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Replace method docstring at line 187-188

**Current Docstring**:
```python
def _to_dimension_group_dict(self) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group."""
```

**Updated Docstring**:
Should include:
- Detailed description of what method does
- Explanation of timezone conversion support
- Documentation of precedence rules (3 levels)
- Args section with parameter documentation
- Returns section describing output dictionary structure
- Example section showing dimension with and without override
- Reference to CLAUDE.md timezone section

**Pattern Notes**:
- Google-style docstring format
- Include Args: section for parameters
- Include Returns: section describing dict structure
- Include Example: section with 2+ examples
- Use proper type hints in docstring

**Reference**: Strategy document lines 228-279 contain complete updated docstring

**Tests**:
- Verify docstring follows Google-style format
- Check that parameter and return documentation is complete
- Confirm examples are syntactically valid Python
- Verify cross-references are accurate

### Task 4: Update LookMLGenerator.__init__() Docstring

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Action**: Replace __init__() docstring at lines 36-46

**Current Docstring**:
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
) -> None:
    """Initialize the generator.

    Args:
        view_prefix: Prefix to add to view names.
        ...
    """
```

**Updated Docstring**:
Should include:
- Enhanced introduction explaining generator's role
- Documentation of convert_tz parameter and its purpose
- Explanation of timezone behavior and precedence
- Args section with comprehensive parameter docs
- Example section showing different configuration approaches
- See Also section referencing CLAUDE.md and related methods

**Pattern Notes**:
- Google-style docstring format
- Add convert_tz parameter documentation after model_name
- Include detailed explanation of True/False/None behavior
- Add Example: section with 3 examples
- Include See Also: section with cross-references

**Reference**: Strategy document lines 312-377 contain complete updated docstring

**Tests**:
- Verify docstring follows Google-style format
- Check that convert_tz parameter is well-documented
- Confirm examples are syntactically valid Python
- Verify cross-references are accurate and helpful

### Task 5: Add README.md Reference

**File**: `/Users/dug/Work/repos/dbt-to-lookml/README.md`

**Action**: Add timezone conversion section to CLI Usage area

**Location**: In "CLI Usage" section (after line 59)

**Current CLI Usage**:
```markdown
## CLI Usage
- `dbt-to-lookml generate -i <input_dir> -o <output_dir> [--view-prefix X] [--explore-prefix Y] [--dry-run] [--no-validation] [--no-formatting] [--show-summary]`
- `dbt-to-lookml validate -i <input_dir> [--strict] [-v]`
```

**Option 1 - Comprehensive Subsection** (if README lacks detail):
Add new subsection "## Timezone Conversion" with explanation of:
- --convert-tz and --no-convert-tz flags
- Default behavior (disabled)
- Per-dimension override capability
- Reference to CLAUDE.md for details

**Option 2 - Brief Note** (if README is concise):
Add note within CLI Usage section:
```markdown
See CLAUDE.md "Timezone Conversion Configuration" for timezone control details and examples.
```

**Pattern Notes**:
- Keep consistent with README's concise style
- Link to CLAUDE.md for detailed docs
- Mention CLI flags are mutually exclusive
- Reference dimension-level overrides

**Reference**: Strategy document lines 452-468 contain suggested text for both options

**Tests**:
- Verify markdown syntax is valid
- Check that references to CLAUDE.md are accurate
- Confirm flags are correctly documented

### Task 6: Validation and Testing

**File**: Multiple (review phase)

**Action**: Perform comprehensive validation of all documentation

**Syntax Validation**:
1. Check CLAUDE.md markdown syntax
   - All headers properly formatted
   - Code blocks have proper language tags
   - Links are properly formatted
   - No broken reference patterns

2. Check Python docstring syntax
   - All docstrings follow Google-style format
   - Type hints are correct
   - No syntax errors in examples

3. Check code examples
   - YAML examples are valid YAML syntax
   - Python examples are valid Python syntax
   - LookML examples are valid LookML (test with lkml library)

**Accuracy Validation**:
1. Cross-reference with implementation
   - Default behavior matches code (convert_tz: no)
   - Precedence chain matches actual code flow
   - Method signatures match documentation

2. Verify examples produce expected output
   - Dimension-level override examples work as documented
   - Generator parameter examples work as documented
   - CLI flag examples work as documented

3. Check consistency
   - All references between sections are accurate
   - No contradictions between documentation layers
   - Consistent naming and terminology

**Completeness Validation**:
1. Verify all required topics are covered
   - Default behavior explained
   - All configuration levels documented
   - Precedence rules clearly illustrated
   - Examples provided for each approach

2. Check documentation is discoverable
   - CLAUDE.md section links to implementation details
   - Docstrings link to CLAUDE.md for full context
   - README.md references detailed documentation

## File Changes

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`
**Why**: Add comprehensive timezone conversion documentation section

**Changes**:
- Insert "Timezone Conversion Configuration" section after "Hierarchy Labels"
- Include 4 configuration levels with detailed explanation
- Add precedence chain diagram
- Include 3+ examples with output
- Add implementation details section
- Add LookML output examples

**Estimated lines**: ~450 lines of new content

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
**Why**: Document ConfigMeta and Dimension methods with timezone conversion support

**Changes**:
- Update ConfigMeta class docstring with comprehensive documentation
- Update Dimension._to_dimension_group_dict() docstring with parameter and example documentation
- Add cross-references to CLAUDE.md timezone section

**Estimated lines**: ~50 lines modified (docstrings only)

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`
**Why**: Document LookMLGenerator timezone conversion capability in __init__()

**Changes**:
- Update LookMLGenerator.__init__() docstring
- Document convert_tz parameter fully
- Add examples showing different configuration approaches
- Add "See Also" section with cross-references

**Estimated lines**: ~40 lines modified (docstring only)

#### `/Users/dug/Work/repos/dbt-to-lookml/README.md`
**Why**: Provide brief reference to timezone conversion feature

**Changes**:
- Add timezone conversion section or note in CLI Usage
- Include CLI flags and reference to detailed docs
- Optional: brief explanation of configuration levels

**Estimated lines**: ~10-15 lines of new content

## Testing Strategy

### Manual Syntax Validation

**Markdown Validation**:
1. Check CLAUDE.md file renders correctly in markdown viewer
   - Headers properly formatted
   - Code blocks properly highlighted
   - Links render correctly
   - No markdown syntax errors

2. Run markdown linter (if available)
   ```bash
   markdownlint CLAUDE.md  # or similar tool
   ```

**Python Docstring Validation**:
1. Verify docstrings are extractable with help()
   ```python
   from dbt_to_lookml.schemas import ConfigMeta, Dimension
   from dbt_to_lookml.generators.lookml import LookMLGenerator
   help(ConfigMeta)
   help(Dimension._to_dimension_group_dict)
   help(LookMLGenerator.__init__)
   ```

2. Check with type hints
   ```bash
   mypy --strict src/dbt_to_lookml/schemas.py
   mypy --strict src/dbt_to_lookml/generators/lookml.py
   ```

### Code Example Validation

**YAML Example Validation**:
1. Verify all YAML examples in CLAUDE.md are valid
   ```python
   import yaml
   # Copy each example and verify parses
   yaml.safe_load(example_text)
   ```

2. Check semantic correctness
   - dimension structures match schema requirements
   - All field names match actual schema fields
   - Type values are valid

**Python Example Validation**:
1. Verify all Python examples in docstrings can be executed
   ```python
   # Copy examples and verify they run without errors
   from dbt_to_lookml.generators.lookml import LookMLGenerator
   generator = LookMLGenerator(view_prefix="stg_", convert_tz=True)
   ```

2. Check import statements are correct
   - All classes and enums are correctly imported
   - No undefined references

**LookML Example Validation**:
1. Verify all LookML examples in CLAUDE.md are valid
   ```python
   import lkml
   # Test each example
   parsed = lkml.load(example_text)
   ```

2. Check syntax correctness
   - All LookML blocks properly formatted
   - All properties valid
   - convert_tz values are "yes" or "no" strings

### Accuracy Validation

**Cross-Reference Verification**:
1. Confirm all references between sections are accurate
   - CLAUDE.md references point to actual file locations
   - Docstring references point to actual methods
   - Section names match exactly

2. Verify code examples match implementation
   - Run through examples manually to verify output
   - Check parameter names match actual code
   - Confirm type hints are correct

**Documentation Accuracy**:
1. Verify default behavior
   - Documentation states convert_tz: no default
   - Code behavior matches (verify in implementation)
   - Examples show correct default output

2. Verify precedence chain
   - Documentation lists correct priority order
   - Each example demonstrates correct precedence
   - Code flow matches documented precedence

3. Test configuration examples
   - Dimension-level override examples work
   - Generator parameter examples work
   - CLI flag examples work

### Completeness Validation

**Coverage Check**:
1. Verify all required documentation sections are present
   - [ ] CLAUDE.md section with default behavior
   - [ ] CLAUDE.md section with 4 configuration levels
   - [ ] CLAUDE.md section with precedence chain
   - [ ] CLAUDE.md section with 3+ examples
   - [ ] CLAUDE.md section with implementation details
   - [ ] ConfigMeta docstring updated
   - [ ] Dimension method docstring updated
   - [ ] LookMLGenerator docstring updated
   - [ ] README.md updated or referenced

2. Verify each section is complete
   - No placeholder text remains
   - All examples are provided
   - All fields are documented
   - Cross-references are included

## Validation Commands

**Markdown Validation**:
```bash
# View CLAUDE.md in markdown viewer
cat /Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md | less

# Check syntax (if markdownlint available)
markdownlint CLAUDE.md

# Verify links work
grep -n "\.md\|http" CLAUDE.md | head -20
```

**Python Docstring Validation**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml

# Type check all modified files
make type-check

# View docstrings
python -c "from dbt_to_lookml.schemas import ConfigMeta; help(ConfigMeta)"
python -c "from dbt_to_lookml.schemas import Dimension; help(Dimension._to_dimension_group_dict)"
python -c "from dbt_to_lookml.generators.lookml import LookMLGenerator; help(LookMLGenerator.__init__)"
```

**Code Example Validation**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml

# Test YAML examples
python -c "import yaml; yaml.safe_load(open('CLAUDE.md').read())"

# Test Python examples (run in Python REPL)
python -c "
from dbt_to_lookml.generators.lookml import LookMLGenerator
g = LookMLGenerator(view_prefix='stg_', convert_tz=True)
print('✓ LookMLGenerator with convert_tz=True works')
"

# Test LookML examples with lkml library
python -c "
import lkml
example = '''dimension_group: created_at { type: time timeframes: [date] sql: \${TABLE}.created_at ;; convert_tz: yes }'''
parsed = lkml.load(example)
print('✓ LookML example parses correctly')
"
```

## Dependencies

### Existing Dependencies
- `Pydantic`: Used for schema validation (already present)
- `lkml`: Used for LookML validation (already present)
- `rich`: Used for CLI output (already present)

### New Dependencies Needed
None - this is a documentation-only update.

## Implementation Notes

### Important Considerations

1. **Documentation Accuracy**: All examples must match actual implementation behavior
   - The timezone conversion feature is already implemented in DTL-007 through DTL-012
   - Documentation should explain existing behavior, not propose new behavior
   - Verify default behavior is indeed convert_tz: no

2. **Google-Style Format**: All docstrings must follow project conventions
   - Use Google-style docstring format consistently
   - Include Args, Returns, Example sections
   - Include cross-references in "See Also" sections

3. **Markdown Consistency**: CLAUDE.md section must blend seamlessly
   - Follow existing markdown formatting conventions
   - Use same header levels as surrounding sections
   - Match code block and example formatting

4. **Cross-References**: Documentation must be mutually referential
   - CLAUDE.md section references method implementations
   - Method docstrings reference CLAUDE.md for detailed info
   - README.md links to CLAUDE.md for comprehensive docs

### Code Patterns to Follow

**Docstring Pattern** (Google-style):
```python
def method_name(self, param1: str, param2: bool | None = None) -> dict[str, Any]:
    """Brief description.

    Detailed explanation of what method does, including any special behavior
    or side effects. Can span multiple paragraphs.

    Args:
        param1: Description of param1, including type and constraints.
        param2: Description of param2, including default behavior.
            - True: Behavior when True
            - False: Behavior when False
            - None: Default behavior

    Returns:
        Dictionary with structure:
        - key1: Description of value
        - key2: Description of value

    Example:
        Example code demonstrating usage with expected results.

    See Also:
        - RelatedClass: For related functionality
        - document.md: For detailed information
    """
```

**Markdown Code Block Pattern** (in CLAUDE.md):
```markdown
#### Example 1: Description

```yaml
# YAML example
key: value
```

**Generated LookML**:
```lookml
# LookML output
block_name: name {
  property: value
}
```
```

### References

- Implementation: `src/dbt_to_lookml/schemas.py:25-36` (ConfigMeta class)
- Implementation: `src/dbt_to_lookml/schemas.py:187-224` (Dimension._to_dimension_group_dict)
- Implementation: `src/dbt_to_lookml/generators/lookml.py:26-71` (LookMLGenerator.__init__)
- Strategy: `.tasks/strategies/DTL-013-strategy.md` (comprehensive strategy document)
- Existing Section: `CLAUDE.md:102-115` (Hierarchy Labels section to match style)

## Ready for Implementation

This spec is complete and ready for implementation. All required information is present:
- Clear file locations and line numbers
- Comprehensive text from strategy document for each section
- Examples and patterns to follow
- Validation commands for quality assurance
- No dependencies on other features (all depend on completed DTL-007 epic)

### Next Steps After Implementation
1. Run validation commands to ensure syntax and accuracy
2. Have team review documentation for clarity and completeness
3. Merge to main branch
4. Close DTL-013 issue


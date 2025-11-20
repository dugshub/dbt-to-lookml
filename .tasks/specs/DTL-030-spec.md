# Implementation Spec: DTL-030 - Research and document LookML field organization patterns

**Issue ID**: DTL-030
**Type**: Chore
**Priority**: Medium
**Status**: Ready
**Created**: 2025-11-19
**Spec Version**: 1.0

## Overview

This spec provides detailed implementation guidance for the research and documentation phase of the time dimension organization epic (DTL-029). The work is **purely research and documentation** - no code changes are required. This issue captures comprehensive research on LookML field organization parameters and documents best practices for implementing hierarchical time dimension organization in subsequent issues.

## Goals

1. **Complete Understanding**: Thoroughly document LookML's `group_label`, `label`, and `group_item_label` parameters
2. **Design Precedence Rules**: Define multi-level configuration system (dimension > generator > CLI > default)
3. **Integration Analysis**: Identify interaction points with existing features (hierarchy, convert_tz, hidden, bi_field)
4. **Implementation Blueprint**: Create clear technical design for subsequent issues (DTL-031 through DTL-035)
5. **Test Coverage Plan**: Define comprehensive testing strategy targeting 95%+ coverage

## Architecture Context

### Current Codebase Status

The dbt-to-lookml tool currently generates time dimension_groups with minimal labeling:

**Current LookML Output**:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}

dimension_group: updated_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: no
}
```

**Looker Field Picker (Current)**:
```
Time Dimensions
  Rental Created Date
  Rental Created Week
  Rental Created Month
  Rental Created Quarter
  Rental Created Year
  Rental Updated Date
  Rental Updated Week
  Rental Updated Month
  Rental Updated Quarter
  Rental Updated Year
```

This creates a **flat list** of all timeframe fields mixed together.

### Desired Behavior

Implement hierarchical organization using LookML parameters:

**Enhanced LookML Output**:
```lookml
dimension_group: created_at {
  label: "Rental Created"
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}

dimension_group: updated_at {
  label: "Rental Updated"
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: no
}
```

**Looker Field Picker (Desired)**:
```
Time Dimensions
  Rental Created Date
  Rental Created Week
  Rental Created Month
  Rental Created Quarter
  Rental Created Year
  Rental Updated Date
  Rental Updated Week
  Rental Updated Month
  Rental Updated Quarter
  Rental Updated Year
```

**Note**: While the fields appear similarly, they are now organized under a common "Time Dimensions" group, providing better categorization and field picker organization.

### Related Codebase Patterns

The tool already implements similar multi-level configuration for timezone conversion:

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
```python
def _to_dimension_group_dict(
    self, default_convert_tz: bool | None = None
) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group."""
    # ...

    # Check dimension-level override first
    convert_tz = self.config.meta.convert_tz if self.config and self.config.meta else None

    # Fall back to generator parameter
    if convert_tz is None:
        convert_tz = default_convert_tz

    # Fall back to default
    if convert_tz is None:
        convert_tz = False

    result["convert_tz"] = "yes" if convert_tz else "no"
```

This same pattern will be followed for `time_dimension_group_label`.

## Research Deliverables

### Deliverable 1: LookML Parameter Research Document

**Status**: ✅ COMPLETED - See `/Users/dug/Work/repos/dbt-to-lookml/.tasks/strategies/DTL-030-strategy.md`

**Contents**:
- Comprehensive documentation of `group_label`, `label`, and `group_item_label` parameters
- How dimension_group automatically creates field groupings
- Interaction between parameters for time dimensions
- Before/after LookML examples showing desired transformation
- LookML documentation references and citations

**Key Findings**:

1. **`group_label` Parameter**:
   - Combines fields into custom groups within a view
   - Works with both regular dimensions and dimension_groups
   - Creates expandable sections in field picker
   - Cannot group dimensions and measures together

2. **`label` Parameter**:
   - Provides human-readable name for dimension_group
   - Becomes base name for all timeframe fields
   - Automatically suffixed with timeframe names (Date, Week, Month, etc.)

3. **`group_item_label` Parameter**:
   - Customizes how individual fields appear within group_label section
   - Only displays in field picker (not in Data section or visualizations)
   - Typically NOT needed for dimension_groups (label handles this)
   - Optional feature to implement later (DTL-033)

4. **Hierarchical Nesting Limitation**:
   - LookML group_label creates **one level** of grouping only
   - True nested hierarchy (dimension_group name as parent with timeframes as children) may not be achievable with standard parameters
   - Further investigation needed in actual Looker instance

### Deliverable 2: Configuration Precedence Design

**Status**: ✅ COMPLETED - See strategy document Section "Configuration Precedence Design"

**Design**: Multi-level configuration with sensible precedence chain

**Precedence Chain (Highest to Lowest)**:

1. **Dimension Metadata Override** (Highest Priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           time_dimension_group_label: "Important Dates"
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(
       time_dimension_group_label="Time Dimensions"
   )
   ```

3. **CLI Flag**
   ```bash
   dbt-to-lookml generate -i semantic_models -o build/lookml \
     --time-dimension-group-label "Time Dimensions"
   ```

4. **Default Behavior** (Lowest Priority)
   - No group_label applied to dimension_groups
   - Preserves backward compatibility
   - Users must explicitly enable grouping

**Design Rationale**:
- **Backward compatibility**: Default to no grouping (matches current behavior)
- **Opt-in philosophy**: Advanced organization is enhancement, not requirement
- **Fine-grained control**: Dimension-level override for specific use cases
- **Consistent pattern**: Matches existing convert_tz precedence system

### Deliverable 3: Implementation Approach Recommendation

**Status**: ✅ COMPLETED - See strategy document Section "Implementation Approach"

**Recommended Approach**: Extend ConfigMeta with `time_dimension_group_label` field

**Schema Changes Required**:

**File**: `src/dbt_to_lookml/schemas/config.py` (or relevant config module)
```python
class ConfigMeta(BaseModel):
    # ... existing fields ...
    convert_tz: bool | None = None
    hidden: bool | None = None
    bi_field: bool | None = None
    time_dimension_group_label: str | None = None  # NEW FIELD
```

**Alternative Approaches Considered**:

**Option 2**: Reuse hierarchy.category for time dimensions
- ❌ Conflates different concepts (hierarchy vs. time grouping)
- ❌ Less intuitive for users
- ❌ May cause confusion with measure hierarchy

**Option 3**: Add separate time_dimension configuration block
- ❌ More verbose
- ❌ Breaking change to config structure
- ✅ Clean separation of concerns (future consideration)

**Why Option 1 is Best**:
- ✅ Follows existing pattern (convert_tz, hidden, bi_field)
- ✅ Supports dimension-level override
- ✅ Clear separation from hierarchy.category
- ✅ Minimal schema changes
- ✅ Backward compatible

### Deliverable 4: Integration with Existing Features

**Status**: ✅ COMPLETED - See strategy document Section "Interaction with Existing Features"

**Integration Points Identified**:

1. **Hierarchy Labels (view_label, group_label)**:
   - `hierarchy.category` → Used for categorical dimensions
   - `time_dimension_group_label` → Used for time dimension_groups
   - Both can coexist on same dimension without conflict
   - `time_dimension_group_label` takes precedence for dimension_groups

2. **Timezone Conversion (convert_tz)**:
   - No conflict - both parameters can coexist
   - Both use same precedence pattern
   - Independent configuration

3. **Field Visibility (hidden, bi_field)**:
   - group_label applied BEFORE hidden filtering
   - If dimension has `hidden: true`, won't appear in LookML (group_label irrelevant)
   - bi_field filtering happens at explore join level (not view level)

4. **Dimension Sets (dimensions_only)**:
   - No impact - sets reference individual timeframe fields
   - group_label is presentation layer only

**Example of Multiple Features**:
```yaml
dimensions:
  - name: created_at
    type: time
    config:
      meta:
        hierarchy:
          entity: "rental"
          category: "temporal"  # → view_label for dimension
        time_dimension_group_label: "Time Dimensions"  # → group_label for dimension_group
        convert_tz: true
```

**Generated LookML**:
```lookml
dimension_group: created_at {
  view_label: "Rental"                # from hierarchy.entity
  group_label: "Time Dimensions"      # from time_dimension_group_label
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: yes                     # from convert_tz
}
```

### Deliverable 5: Test Coverage Plan

**Status**: ✅ COMPLETED - See strategy document Section "Test Coverage Requirements"

**Coverage Targets**:
- **Per-Module**: 95%+ branch coverage
- **Overall**: Maintain project-wide 95%+ coverage
- **New Code**: 100% coverage for time_dimension_group_label feature

**Test Strategy**:

#### Unit Tests

**File**: `src/tests/unit/test_schemas.py`
- ConfigMeta with time_dimension_group_label field (validation tests)
- Dimension._to_dimension_group_dict() with group_label parameter
- Label precedence chain (dimension > generator > default)

**File**: `src/tests/unit/test_lookml_generator.py`
- LookMLGenerator initialization with time_dimension_group_label parameter
- group_label propagation to dimension_groups
- Multiple dimension_groups with same group_label
- Mixed time dimensions (some with group_label, some without)

**File**: `src/tests/unit/test_hierarchy.py` (or new file)
- Ensure time_dimension_group_label doesn't conflict with hierarchy.category
- Both parameters can coexist on same dimension
- Verify correct precedence when both present

#### Integration Tests

**File**: `src/tests/integration/test_time_dimension_organization.py` (new)
- End-to-end: Parse semantic models → Generate LookML → Validate output
- Verify group_label appears in generated LookML
- Test all precedence levels (dimension meta, generator param, CLI flag)
- Test lkml library correctly parses generated output

#### Golden Tests

**File**: `src/tests/test_golden.py`
- Add new golden files with group_label examples
- Verify backward compatibility (no group_label when not configured)
- Update existing golden files if needed

**New Golden Files**:
- `src/tests/golden/expected_time_dimensions_grouped.view.lkml`
- `src/tests/golden/expected_time_dimensions_ungrouped.view.lkml`

**Test Count Estimate**: 15-20 new test methods across all files

### Deliverable 6: Implementation Sequence Documentation

**Status**: ✅ COMPLETED - See strategy document Section "Implementation Sequence"

**Epic Sub-Issues**:

1. ✅ **DTL-030** (This Issue): Research and documentation
2. **DTL-031**: Add time_dimension_group_label to schema and CLI
3. **DTL-032**: Implement group_label in dimension_group generation
4. **DTL-033**: Add optional group_item_label support
5. **DTL-034**: Update comprehensive test suite
6. **DTL-035**: Update documentation (CLAUDE.md, README)

**Dependencies**:
- DTL-031 depends on DTL-030 (this research)
- DTL-032 depends on DTL-031 (schema must exist)
- DTL-034 depends on DTL-031 and DTL-032 (code must exist to test)
- DTL-035 depends on DTL-031, DTL-032, DTL-034 (document completed features)
- DTL-033 is optional, can be implemented later

**Estimated Timeline**:
- DTL-030: 1-2 hours (research and documentation) - COMPLETED
- DTL-031: 2-3 hours (schema and CLI changes)
- DTL-032: 2-3 hours (generator implementation)
- DTL-033: 1-2 hours (optional, future work)
- DTL-034: 3-4 hours (comprehensive testing)
- DTL-035: 2-3 hours (documentation updates)

**Total Estimated Effort**: 10-15 hours for core features (excluding DTL-033)

## Open Questions & Research Gaps

**Status**: ✅ DOCUMENTED - See strategy document Section "Open Questions & Research Gaps"

### Question 1: True Hierarchical Nesting

**Question**: Can we achieve this structure in Looker's field picker?
```
Time Dimensions
  Created  <-- This level of nesting
    Date
    Week
    Month
```

**Current Evidence**:
- LookML group_label creates one level of grouping
- dimension_group's label becomes a prefix, not a nested section
- May require Looker version-specific features or UI behavior

**Investigation Needed**:
- Test generated LookML in actual Looker instance
- Check Looker documentation for field picker rendering rules
- Explore view_label + group_label combinations
- **Defer to implementation phase (DTL-032)** - can validate in actual Looker

### Question 2: Interaction with view_label

**Question**: Does view_label affect time dimension grouping?

**Current Understanding**:
- view_label moves fields to different view section in field picker
- Typically used for cross-view organization
- May conflict with group_label grouping

**Test Needed**: Generate LookML with both view_label and group_label on dimension_group
**Defer to**: DTL-034 (testing phase)

### Question 3: Looker Version Compatibility

**Question**: Are there version-specific differences in field picker behavior?

**Recommendation**: Document minimum Looker version if field organization has known issues
**Defer to**: DTL-035 (documentation phase) - note as known limitation if discovered

### Question 4: Performance Impact

**Question**: Does heavy use of group_label impact Looker field picker performance?

**Assessment**: Unlikely to be an issue, but worth noting in documentation
**Not Critical**: Monitor during testing, document if issues arise

## Documentation Updates Required

### Update 1: CLAUDE.md - Time Dimension Organization Section

**File**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Location**: Add after "Timezone Conversion Configuration" section (around line 650)

**Section Structure**:
```markdown
### Time Dimension Organization Configuration

LookML dimension_groups support field organization through the `group_label` parameter,
which controls whether time dimensions are grouped together in the field picker.
This feature supports multi-level configuration with a sensible precedence chain.

#### Default Behavior

- **Default**: No group_label applied (backward compatible)
- Time dimensions appear in the standard field picker locations
- Users must explicitly enable grouping if needed

#### Configuration Levels (Precedence: Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           time_dimension_group_label: "Time Dimensions"
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(
       view_prefix="my_",
       time_dimension_group_label="Time Dimensions"
   )
   ```

3. **CLI Flag**
   ```bash
   # Enable time dimension grouping
   dbt-to-lookml generate -i semantic_models -o build/lookml \
     --time-dimension-group-label "Time Dimensions"
   ```

4. **Default** (Lowest priority)
   - No group_label applied
   - Backward compatible behavior

#### Examples

##### Example 1: Override at Dimension Level
[... detailed YAML and LookML examples ...]

##### Example 2: Generator-Level Configuration
[... detailed Python examples ...]

##### Example 3: CLI Usage
[... detailed CLI examples ...]

#### Implementation Details

- **Dimension._to_dimension_group_dict()**: Accepts `default_time_dimension_group_label` parameter
- **LookMLGenerator.__init__()**: Accepts optional `time_dimension_group_label: str | None` parameter
- **SemanticModel.to_lookml_dict()**: Propagates setting to dimension generation
- **CLI Flags**: `--time-dimension-group-label` option

#### LookML Output Examples

[... before/after examples ...]
```

**Estimated Lines**: ~150 lines

**Defer to**: DTL-035 (documentation issue)

### Update 2: Strategy Document (Already Complete)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/.tasks/strategies/DTL-030-strategy.md`

**Status**: ✅ COMPLETED

**Contents**:
- Comprehensive LookML parameter research
- Configuration precedence design
- Implementation approach recommendations
- Integration analysis
- Test coverage plan
- Code examples and references

**No further action needed**

## Implementation Notes

### Important Considerations

1. **No Code Changes in This Issue**: DTL-030 is research and documentation only
2. **Strategy Document is Primary Deliverable**: All research captured in comprehensive strategy
3. **Implementation Blueprint**: Strategy provides detailed guidance for DTL-031 through DTL-035
4. **Backward Compatibility**: Default behavior must remain unchanged (no group_label)
5. **Consistent Patterns**: Follow existing convert_tz precedence pattern exactly

### Code Patterns to Reference

**Pattern 1: Multi-Level Configuration Precedence** (from convert_tz):

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
```python
def _to_dimension_group_dict(
    self, default_convert_tz: bool | None = None
) -> dict[str, Any]:
    # Level 1: Dimension metadata override
    convert_tz = self.config.meta.convert_tz if self.config and self.config.meta else None

    # Level 2: Generator parameter
    if convert_tz is None:
        convert_tz = default_convert_tz

    # Level 3: Default
    if convert_tz is None:
        convert_tz = False
```

**Apply Same Pattern for time_dimension_group_label**:
```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None  # NEW PARAMETER
) -> dict[str, Any]:
    # ... existing code ...

    # Time dimension group_label precedence
    group_label_override = (
        self.config.meta.time_dimension_group_label
        if self.config and self.config.meta
        else None
    )

    if group_label_override:
        result["group_label"] = group_label_override
    elif default_time_dimension_group_label:
        result["group_label"] = default_time_dimension_group_label
    # else: no group_label (backward compatible default)
```

**Pattern 2: CLI Flag Definition** (from convert_tz):

**File**: `src/dbt_to_lookml/__main__.py`
```python
@click.option(
    "--convert-tz/--no-convert-tz",
    default=None,
    help="Enable/disable timezone conversion for dimension_groups",
)
```

**New Flag to Add**:
```python
@click.option(
    "--time-dimension-group-label",
    type=str,
    default=None,
    help="Group label for time dimension_groups in field picker",
)
```

**Pattern 3: Generator Parameter** (from convert_tz):

**File**: `src/dbt_to_lookml/generators/lookml.py`
```python
class LookMLGenerator(Generator):
    def __init__(
        self,
        view_prefix: str = "",
        explore_prefix: str = "",
        convert_tz: bool | None = None,  # Existing
        time_dimension_group_label: str | None = None,  # NEW
    ):
        self.convert_tz = convert_tz
        self.time_dimension_group_label = time_dimension_group_label  # NEW
```

### References to Existing Code

**Key Files to Study**:
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas/semantic_layer.py` - Dimension._to_dimension_group_dict() method
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py` - LookMLGenerator class
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/__main__.py` - CLI command definitions
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas/config.py` - ConfigMeta schema

**Key Code Sections**:
- Dimension.get_dimension_labels() (semantic_layer.py) - Label extraction pattern
- LookMLGenerator.generate() (lookml.py) - Parameter propagation
- CLI generate command (\_\_main\_\_.py) - Flag handling

**Test Files to Reference**:
- `src/tests/unit/test_schemas.py` - ConfigMeta validation tests
- `src/tests/unit/test_lookml_generator.py` - Generator parameter tests
- `src/tests/integration/test_end_to_end.py` - Full workflow tests
- `src/tests/test_golden.py` - Golden file comparison patterns

## Success Criteria

### Research Deliverables
- [x] Comprehensive LookML parameter documentation (group_label, label, group_item_label)
- [x] Configuration precedence rules designed and documented
- [x] Implementation approach recommended with rationale
- [x] Integration points with existing features identified
- [x] Test coverage plan defined (95%+ target)
- [x] Open questions documented for future investigation
- [x] Strategy document completed and approved

### Documentation Deliverables
- [x] Before/after LookML examples created
- [x] Code patterns identified and documented
- [x] Implementation sequence defined (DTL-031 through DTL-035)
- [x] References to existing codebase patterns documented

### Ready for Implementation
- [x] Strategy document provides sufficient detail for DTL-031 (schema changes)
- [x] Strategy document provides sufficient detail for DTL-032 (generator changes)
- [x] Test coverage plan ready for DTL-034 (testing)
- [x] Documentation plan ready for DTL-035 (CLAUDE.md updates)

## Validation Commands

### Review Strategy Document
```bash
# Read completed strategy
cat /Users/dug/Work/repos/dbt-to-lookml/.tasks/strategies/DTL-030-strategy.md

# Verify completeness (should contain all sections)
grep -E "(group_label|label|group_item_label|precedence|implementation)" \
  /Users/dug/Work/repos/dbt-to-lookml/.tasks/strategies/DTL-030-strategy.md
```

### Verify Issue Files
```bash
# Check issue exists and is properly structured
cat /Users/dug/Work/repos/dbt-to-lookml/.tasks/issues/DTL-030.md

# Check spec exists (this file)
cat /Users/dug/Work/repos/dbt-to-lookml/.tasks/specs/DTL-030-spec.md
```

### Verify Related Files
```bash
# Check epic exists
cat /Users/dug/Work/repos/dbt-to-lookml/.tasks/epics/DTL-029.md

# List all related issues in epic
ls -la /Users/dug/Work/repos/dbt-to-lookml/.tasks/issues/DTL-03*.md
```

## Ready for Implementation

This spec is complete and ready for review. **No code implementation is required for DTL-030**.

**Deliverables Summary**:
- ✅ Comprehensive research completed in strategy document
- ✅ Configuration precedence designed
- ✅ Implementation approach recommended
- ✅ Integration analysis completed
- ✅ Test coverage plan defined
- ✅ Implementation sequence documented

**Next Steps**:
1. Update DTL-030 issue status to "Ready" and add "state:has-spec" label
2. Move to DTL-031 (Add time_dimension_group_label to schema and CLI)
3. Use strategy document as reference during implementation

**Key References**:
- Strategy: `/Users/dug/Work/repos/dbt-to-lookml/.tasks/strategies/DTL-030-strategy.md`
- Epic: `/Users/dug/Work/repos/dbt-to-lookml/.tasks/epics/DTL-029.md`
- Issue: `/Users/dug/Work/repos/dbt-to-lookml/.tasks/issues/DTL-030.md`

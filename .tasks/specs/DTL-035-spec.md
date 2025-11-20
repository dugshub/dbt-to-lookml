---
id: DTL-035-spec
issue: DTL-035
title: "Implementation Spec: Update documentation for time dimension organization"
type: spec
status: Ready
created: 2025-11-19
stack: backend
---

# Implementation Spec: Update documentation for time dimension organization

## Metadata
- **Issue**: `DTL-035`
- **Stack**: `backend`
- **Type**: `chore`
- **Generated**: 2025-11-19
- **Strategy**: Approved 2025-11-19

## Issue Context

### Problem Statement

Update CLAUDE.md with comprehensive documentation for the new time dimension organization features. This documentation will help both Claude Code (AI assistant) and human developers understand how to configure and use hierarchical time dimension organization in LookML field pickers.

### Solution Approach

Follow the established documentation pattern used for similar features (Timezone Conversion Configuration, Field Visibility Control) to create a comprehensive "Time Dimension Organization" section in CLAUDE.md. The documentation will cover:

1. Feature overview and problem it solves
2. Default behavior and out-of-box experience
3. Multi-level configuration with precedence chain
4. Comprehensive examples (YAML, CLI, Python, LookML output)
5. Implementation details (classes, methods, parameters)
6. Field picker organization examples (before/after)

### Success Criteria

- [ ] Complete "Time Dimension Organization" section added to CLAUDE.md
- [ ] All configuration levels documented with precedence
- [ ] All CLI flags documented with examples
- [ ] All generator parameters documented
- [ ] Before/after field picker examples included
- [ ] LookML output examples showing generated code
- [ ] Documentation follows existing patterns and style
- [ ] All code examples are accurate and verifiable

## Approved Strategy Summary

The strategy (from `.tasks/strategies/DTL-035-strategy.md`) provides a structured approach:

1. **Research & Verification**: Understand implemented features vs. planned features
2. **Core Documentation**: Write overview, default behavior, precedence chain
3. **Examples**: Create YAML, CLI, Python, and LookML examples
4. **Field Picker Visualizations**: Show before/after organization
5. **LookML Output Examples**: Show generated code samples
6. **Review & Polish**: Ensure accuracy and consistency
7. **Update Issue Tracking**: Mark as documented

**Key Architectural Decisions**:
- Model after "Timezone Conversion Configuration" section (lines 161-312)
- Use consistent section structure and terminology
- Document precedence chain clearly (dimension metadata > generator > CLI > default)
- Include both required features (group_label) and optional features (group_item_label)
- Emphasize backward compatibility and opt-in nature

## Implementation Plan

### Phase 1: Research & Verification (NOT IMPLEMENTED YET)

**Objective**: Determine what features are actually implemented vs. planned

**Note**: Based on codebase analysis, the time dimension organization features (DTL-030 through DTL-034) have NOT been implemented yet. This documentation task should be treated as **documenting planned features** that will be implemented.

**Actions**:
1. Document features as designed (from strategies)
2. Mark examples as "Expected behavior" or "Planned implementation"
3. Add note that features require DTL-031, DTL-032, DTL-033 to be implemented first

### Phase 2: Draft Core Documentation

**Objective**: Create main documentation sections following established patterns

**Location**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md` (after line 458, before "Parser Error Handling")

**Structure** (based on Timezone Conversion pattern):

```markdown
### Time Dimension Organization

[Overview paragraph]

#### Default Behavior

[Default settings and behavior]

#### Configuration Levels (Precedence: Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
2. **Generator Parameter**
3. **CLI Flag**
4. **Default** (Lowest priority)

#### Examples

##### Example 1: Default Behavior
##### Example 2: Dimension Metadata Override
##### Example 3: Generator-Level Configuration
##### Example 4: CLI Usage
##### Example 5: Disabling Grouping
##### Example 6: Using group_item_label (Optional)

#### Implementation Details

[Classes, methods, parameters]

#### Field Picker Organization

[Before/after visual examples]

#### LookML Output Examples

[Generated code samples]
```

### Phase 3: Create Detailed Examples

**Objective**: Develop comprehensive, tested examples for all use cases

#### Example 1: Default Behavior (No Configuration)

**Semantic Model**:
```yaml
# semantic_models/rentals.yaml
semantic_model:
  name: rentals
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day

    - name: updated_at
      type: time
      type_params:
        time_granularity: day
```

**Generated LookML**:
```lookml
dimension_group: created_at {
  label: "Created At"
  group_label: "Time Dimensions"  # Applied by default
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}

dimension_group: updated_at {
  label: "Updated At"
  group_label: "Time Dimensions"  # Applied by default
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: no
}
```

**Field Picker Result**:
```
Time Dimensions
  Created At
    Date
    Week
    Month
    Quarter
    Year
  Updated At
    Date
    Week
    Month
    Quarter
    Year
```

#### Example 2: Dimension Metadata Override

**Semantic Model**:
```yaml
# semantic_models/orders.yaml
semantic_model:
  name: orders
  dimensions:
    - name: order_date
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          time_dimension_group_label: "Order Timeline"  # Custom group

    - name: shipped_at
      type: time
      type_params:
        time_granularity: day
      # Uses default "Time Dimensions"
```

**Generated LookML**:
```lookml
dimension_group: order_date {
  label: "Order Date"
  group_label: "Order Timeline"  # From dimension metadata
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.order_date ;;
  convert_tz: no
}

dimension_group: shipped_at {
  label: "Shipped At"
  group_label: "Time Dimensions"  # Default
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.shipped_at ;;
  convert_tz: no
}
```

#### Example 3: Generator-Level Configuration

**Python Code**:
```python
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser

parser = DbtParser()
models = parser.parse_directory("semantic_models/")

# Set custom group label for all time dimensions
generator = LookMLGenerator(
    view_prefix="stg_",
    time_dimension_group_label="Date Fields"
)

output = generator.generate(models)
generator.write_files("build/lookml", output)
```

**Result**: All time dimension_groups use `group_label: "Date Fields"` unless overridden by dimension metadata.

#### Example 4: CLI Usage

**With Custom Group Label**:
```bash
# Apply custom group label to all time dimensions
dbt-to-lookml generate \
  -i semantic_models/ \
  -o build/lookml/ \
  -s public \
  --time-dimension-group-label "Date Dimensions"
```

**Disable Grouping**:
```bash
# Explicitly disable time dimension grouping
dbt-to-lookml generate \
  -i semantic_models/ \
  -o build/lookml/ \
  -s public \
  --no-time-dimension-group-label
```

#### Example 5: Disabling Grouping at Dimension Level

**Semantic Model**:
```yaml
dimensions:
  - name: event_timestamp
    type: time
    type_params:
      time_granularity: hour
    config:
      meta:
        time_dimension_group_label: ""  # Empty string disables grouping
```

**Generated LookML**:
```lookml
dimension_group: event_timestamp {
  label: "Event Timestamp"
  # No group_label parameter (disabled)
  type: time
  timeframes: [time, hour, date, week, month, quarter, year]
  sql: ${TABLE}.event_timestamp ;;
  convert_tz: no
}
```

#### Example 6: Using group_item_label (Optional Feature)

**CLI Command**:
```bash
# Enable group_item_label for cleaner field labels
dbt-to-lookml generate \
  -i semantic_models/ \
  -o build/lookml/ \
  -s public \
  --use-group-item-label
```

**Generated LookML**:
```lookml
dimension_group: rental_created {
  label: "Rental Created"
  group_label: "Time Dimensions"
  group_item_label: "{% assign tf = _field._name | remove: 'rental_created_' | replace: '_', ' ' | capitalize %}{{ tf }}"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.rental_created_at ;;
  convert_tz: no
}
```

**Field Picker Result** (with `group_item_label`):
```
Time Dimensions
  Rental Created
    Date         ← Just "Date" instead of "Rental Created Date"
    Week         ← Just "Week" instead of "Rental Created Week"
    Month
    Quarter
    Year
```

### Phase 4: Field Picker Visualizations

**Objective**: Show clear before/after examples of field organization

#### Before (Without Time Dimension Organization)

```
DIMENSIONS
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
  Customer Name
  Location
```

**Problem**: All timeframes are in a flat list, mixed with other dimensions.

#### After (With Default Time Dimension Organization)

```
DIMENSIONS
  Time Dimensions
    Rental Created
      Rental Created Date
      Rental Created Week
      Rental Created Month
      Rental Created Quarter
      Rental Created Year
    Rental Updated
      Rental Updated Date
      Rental Updated Week
      Rental Updated Month
      Rental Updated Quarter
      Rental Updated Year
  Customer Name
  Location
```

**Solution**: Time dimensions are grouped hierarchically under "Time Dimensions", with each dimension_group creating its own sub-category.

#### After (With group_item_label Enabled)

```
DIMENSIONS
  Time Dimensions
    Rental Created
      Date         ← Cleaner labels
      Week
      Month
      Quarter
      Year
    Rental Updated
      Date
      Week
      Month
      Quarter
      Year
  Customer Name
  Location
```

**Enhancement**: `group_item_label` shows just the timeframe name without repetition.

### Phase 5: LookML Output Examples

**Objective**: Show complete generated LookML code for various scenarios

#### Scenario 1: Default Behavior

**Input**: No configuration provided

**Output**:
```lookml
view: rentals {
  sql_table_name: public.rentals ;;

  dimension_group: rental_created {
    label: "Rental Created"
    group_label: "Time Dimensions"
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.rental_created_at ;;
    convert_tz: no
  }

  dimension_group: rental_updated {
    label: "Rental Updated"
    group_label: "Time Dimensions"
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.rental_updated_at ;;
    convert_tz: no
  }
}
```

#### Scenario 2: Custom Group Label via CLI

**Command**: `--time-dimension-group-label "Transaction Dates"`

**Output**:
```lookml
dimension_group: order_date {
  label: "Order Date"
  group_label: "Transaction Dates"  # Custom label from CLI
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.order_date ;;
  convert_tz: no
}
```

#### Scenario 3: Grouping Disabled

**Command**: `--no-time-dimension-group-label`

**Output**:
```lookml
dimension_group: created_at {
  label: "Created At"
  # No group_label parameter
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}
```

#### Scenario 4: Combined with Other Features

**Semantic Model**:
```yaml
dimensions:
  - name: transaction_date
    type: time
    type_params:
      time_granularity: day
    config:
      meta:
        convert_tz: yes  # Enable timezone conversion
        time_dimension_group_label: "Transaction Dates"
        hierarchy:
          entity: "transaction"
          category: "dates"
```

**Generated LookML**:
```lookml
dimension_group: transaction_date {
  label: "Transaction Date"
  group_label: "Transaction Dates"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.transaction_date ;;
  convert_tz: yes
}
```

### Phase 6: Implementation Details Section

**Objective**: Document technical implementation for AI and developers

**Content**:

```markdown
#### Implementation Details

- **ConfigMeta Schema** (`schemas/config.py`):
  - Field: `time_dimension_group_label: str | None = None`
  - Controls dimension-level override of group label
  - Empty string `""` explicitly disables grouping for that dimension
  - `None` (default) uses generator/CLI/default value

- **LookMLGenerator Parameters** (`generators/lookml.py`):
  - `time_dimension_group_label: str | None = None`
    - Sets default group label for all time dimension_groups
    - Default behavior: `"Time Dimensions"` if not specified
    - Can be set to empty string to disable globally

  - `use_group_item_label: bool = False`
    - Enables `group_item_label` parameter in dimension_groups
    - Uses Liquid templating to extract timeframe name
    - Disabled by default (backward compatible)

- **Dimension._to_dimension_group_dict()** (`schemas/semantic_layer.py`):
  - Accepts `default_time_dimension_group_label: str | None` parameter
  - Implements precedence logic:
    1. Check `config.meta.time_dimension_group_label` (dimension override)
    2. Check `default_time_dimension_group_label` parameter (from generator)
    3. Use `"Time Dimensions"` (hardcoded default)
  - Applies `group_label` to output dict if not empty string
  - Generates `group_item_label` if `use_group_item_label=True`

- **CLI Flags** (`__main__.py`):
  - `--time-dimension-group-label TEXT`: Set custom group label
  - `--no-time-dimension-group-label`: Disable grouping (mutually exclusive)
  - `--use-group-item-label`: Enable group_item_label feature
  - Flags pass values to `LookMLGenerator.__init__()`

- **Precedence Chain**:
  1. Dimension metadata (`config.meta.time_dimension_group_label`)
  2. Generator parameter (`time_dimension_group_label=...`)
  3. CLI flag (`--time-dimension-group-label`)
  4. Default (`"Time Dimensions"`)
```

### Phase 7: Integration with Existing Documentation

**Objective**: Ensure new section fits seamlessly with existing content

**Updates Required**:

1. **Update "Semantic Model → LookML Conversion" section** (line ~143):
   ```markdown
   4. **Time dimensions**: Automatically generate appropriate timeframes based on
      `type_params.time_granularity`. Time dimension_groups are organized under
      a configurable group_label (default: "Time Dimensions") for better field
      picker organization. See "Time Dimension Organization" section for details.
   ```

2. **Add cross-reference in "Timezone Conversion Configuration"** (after line 312):
   ```markdown
   **Related Features**:
   - See "Time Dimension Organization" for hierarchical grouping of time dimensions
   - See "Field Visibility Control" for hiding/showing specific fields
   ```

3. **Add to "Common Pitfalls" section** (if relevant):
   ```markdown
   8. **Time dimension organization**: The default `"Time Dimensions"` group_label
      applies to all time dimension_groups unless overridden. Use empty string `""`
      to explicitly disable grouping, not `None`.
   ```

## Detailed Task Breakdown

### Task 1: Create "Time Dimension Organization" Section

**File**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Action**: Insert new section after line 458 (after "Field Visibility Control" section)

**Implementation Guidance**:

1. Start with overview paragraph explaining the problem (flat list of timeframes)
2. Describe the solution (hierarchical organization with group_label)
3. Document default behavior clearly ("Time Dimensions" as default)
4. Create precedence chain following Timezone Conversion pattern (4 levels)
5. Add 6+ comprehensive examples covering all use cases
6. Include implementation details with class/method references
7. Add field picker before/after visualizations
8. Include LookML output examples for each scenario

**Estimated lines**: ~300-350 (similar to Timezone Conversion section)

**Reference**: Lines 161-312 (Timezone Conversion Configuration) for structure and style

### Task 2: Add Cross-References

**File**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Action**: Update existing sections to reference new feature

**Changes**:
1. Line ~143: Update time dimensions bullet point
2. Line ~312: Add "Related Features" note at end of Timezone Conversion
3. Line ~664-673: Consider adding to Common Pitfalls if relevant

**Estimated lines**: ~10 lines of changes

### Task 3: Validate Examples

**Action**: Ensure all code examples are accurate

**Validation**:
1. YAML examples follow semantic model schema format
2. CLI commands use correct flag syntax
3. Python examples follow generator API patterns
4. LookML output matches expected format
5. Precedence chain logic is correct
6. Cross-references are accurate

**Note**: Since features aren't implemented yet, validation is against design specs (DTL-031, DTL-032, DTL-033 strategies)

## File Changes

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Why**: Add comprehensive documentation for time dimension organization features

**Changes**:
- Insert new "Time Dimension Organization" section (~300-350 lines) after line 458
- Update "Semantic Model → LookML Conversion" section (line ~143)
- Add cross-reference in "Timezone Conversion Configuration" (line ~312)
- Potentially update "Common Pitfalls" (line ~664)

**Estimated total lines**: ~360 lines added/modified

**Structure**:
```markdown
### Time Dimension Organization (NEW - after line 458)

#### Overview
[Problem statement and solution]

#### Default Behavior
[Out-of-box behavior with "Time Dimensions"]

#### Configuration Levels (Precedence: Highest to Lowest)
1. Dimension Metadata Override
2. Generator Parameter
3. CLI Flag
4. Default

#### Examples
##### Example 1: Default Behavior
##### Example 2: Dimension Metadata Override
##### Example 3: Generator-Level Configuration
##### Example 4: CLI Usage
##### Example 5: Disabling Grouping
##### Example 6: Using group_item_label

#### Implementation Details
[Technical details]

#### Field Picker Organization
[Before/after examples]

#### LookML Output Examples
[Generated code samples]
```

## Testing Strategy

### Documentation Validation

**Manual Review**:
1. Read through entire new section for clarity
2. Verify formatting consistency with existing sections
3. Check all cross-references are accurate
4. Ensure code examples are syntactically correct

**Accuracy Checks**:
1. YAML examples match semantic model schema
2. CLI flags match expected syntax
3. Python examples follow LookMLGenerator API
4. LookML output examples match format
5. Precedence chain matches implementation design

**Completeness Checks**:
1. All configuration levels documented
2. All CLI flags documented
3. All generator parameters documented
4. All edge cases covered (None, empty string, disabled)
5. Both required and optional features covered

### Integration with Codebase

**Prerequisites**:
- This documentation task assumes DTL-031, DTL-032, DTL-033 will be implemented
- Documentation should be accurate for planned implementation
- Mark as "Expected behavior" or "Planned" where appropriate

**When features are implemented**:
- Validate all examples against actual generated output
- Test all CLI commands work as documented
- Verify precedence chain matches implementation
- Update any discrepancies found

## Validation Commands

**Documentation Review**:
```bash
# View the updated section
sed -n '458,850p' CLAUDE.md

# Check for consistent formatting
grep -n "####" CLAUDE.md | tail -20

# Verify cross-references exist
grep -n "Time Dimension Organization" CLAUDE.md
```

**Markdown Linting** (if available):
```bash
# Check markdown syntax
markdownlint CLAUDE.md

# Or use prettier
npx prettier --check CLAUDE.md
```

**Git Diff Review**:
```bash
# Review changes before committing
git diff CLAUDE.md

# Check line count changes
git diff --stat CLAUDE.md
```

## Dependencies

### Existing Dependencies

No new dependencies required. This is a documentation-only task.

### Related Issues

**Blocked by** (features not yet implemented):
- DTL-031: Add time_dimension_group_label configuration to schemas and CLI
- DTL-032: Implement group_label in dimension_group generation
- DTL-033: Add group_item_label support for cleaner timeframe labels

**Note**: This documentation can be written ahead of implementation to guide development. Examples should reflect planned behavior from approved strategies.

## Implementation Notes

### Important Considerations

1. **Feature Implementation Status**:
   - Time dimension organization features (DTL-030-034) are NOT yet implemented
   - Document as "planned features" based on approved strategies
   - Examples show expected behavior, not current behavior
   - Add note that features require DTL-031, DTL-032, DTL-033 to be implemented

2. **Documentation Pattern Consistency**:
   - Follow Timezone Conversion section structure exactly
   - Use same heading levels and organization
   - Use same code block formatting (```yaml, ```bash, ```lookml)
   - Use numbered precedence levels (1, 2, 3, 4)

3. **Backward Compatibility Emphasis**:
   - Default "Time Dimensions" provides better organization out-of-box
   - Feature can be disabled if needed (--no-time-dimension-group-label)
   - group_item_label is opt-in (disabled by default)

4. **Target Audience**:
   - Claude Code needs: implementation details, precedence rules, method signatures
   - Human developers need: usage examples, CLI commands, YAML patterns
   - Balance both audiences in documentation

5. **Example Quality**:
   - Use realistic semantic model names (rentals, orders, transactions)
   - Show complete YAML/LookML blocks (not fragments)
   - Include comments explaining key points
   - Cover both common cases and edge cases

### Code Patterns to Follow

**Section Structure** (from Timezone Conversion):
```markdown
### [Feature Name]

[Overview paragraph explaining problem and solution]

#### Default Behavior

[Clear statement of defaults]

#### Configuration Levels (Precedence: Highest to Lowest)

1. **[Highest Priority]** (Highest priority)
   [Code example]

2. **[Second Priority]**
   [Code example]

3. **[Third Priority]**
   [Code example]

4. **[Lowest Priority]** (Lowest priority)
   [Code example]

#### Examples

##### Example 1: [Use Case]
[Complete example with YAML/CLI/Python/LookML]

[More examples...]

#### Implementation Details

- **[Component 1]**: [Description]
- **[Component 2]**: [Description]

#### [Feature-Specific Section]

[Additional examples or visualizations]
```

**Code Block Formatting**:
```markdown
```yaml
# Comment explaining the example
semantic_model:
  name: example
```

```bash
# Comment explaining the command
dbt-to-lookml generate -i input/ -o output/
```

```lookml
dimension_group: example {
  label: "Example"
  group_label: "Time Dimensions"
  type: time
}
```
```

### References

- **Timezone Conversion Configuration**: Lines 161-312 in CLAUDE.md
- **Field Visibility Control**: Lines 314-458 in CLAUDE.md
- **Hierarchy Labels**: Lines 146-159 in CLAUDE.md
- **DTL-029 Epic**: `.tasks/epics/DTL-029.md`
- **DTL-030 Strategy**: `.tasks/strategies/DTL-030-strategy.md`
- **DTL-031 Strategy**: `.tasks/strategies/DTL-031-strategy.md`
- **DTL-032 Strategy**: `.tasks/strategies/DTL-032-strategy.md`
- **DTL-033 Strategy**: `.tasks/strategies/DTL-033-strategy.md`

## Ready for Implementation

This spec is complete and ready for documentation work.

**Next Steps**:
1. Review this spec for completeness
2. Begin drafting the "Time Dimension Organization" section
3. Follow the structure and examples provided
4. Validate against strategy documents
5. Mark DTL-035 as Ready when complete

**Estimated Effort**: 3-4 hours
- Phase 2 (Core Documentation): 1 hour
- Phase 3 (Examples): 1 hour
- Phase 4-5 (Visualizations & LookML): 45 minutes
- Phase 6-7 (Implementation Details & Integration): 45 minutes
- Validation & Polish: 30 minutes

**Success Criteria**:
- [ ] ~350 lines of comprehensive documentation added
- [ ] All 6+ examples are complete and accurate
- [ ] Field picker before/after visualizations included
- [ ] LookML output examples for all scenarios
- [ ] Implementation details section complete
- [ ] Cross-references added to existing sections
- [ ] Follows Timezone Conversion pattern exactly
- [ ] Ready for Claude Code and human developers to use

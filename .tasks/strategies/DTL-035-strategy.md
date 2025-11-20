---
id: DTL-035-strategy
issue: DTL-035
title: "Strategy: Update documentation for time dimension organization"
type: strategy
status: Approved
created: 2025-11-19
---

# Strategy: Update documentation for time dimension organization

## Overview

This strategy outlines the approach for comprehensively documenting the time dimension organization features in CLAUDE.md. The documentation will follow the established pattern used for similar features (timezone conversion, field visibility control) to ensure consistency and clarity.

## Analysis

### Documentation Patterns in CLAUDE.md

The existing CLAUDE.md documentation follows a consistent pattern for feature documentation:

1. **Feature overview** - Brief description of what the feature does and why it exists
2. **Default behavior** - Clear statement of defaults and out-of-box behavior
3. **Configuration levels** - Precedence chain from highest to lowest priority
4. **Examples** - Multiple real-world examples showing different use cases
5. **Implementation details** - Technical details about classes/methods involved
6. **LookML output examples** - Side-by-side comparisons of generated code

### Similar Features to Model After

**Timezone Conversion Configuration** (lines 161-312 in CLAUDE.md):
- Clear precedence chain (4 levels)
- Multiple examples (dimension override, generator, CLI)
- Implementation details section
- LookML output examples with before/after

**Field Visibility Control** (lines 314-458 in CLAUDE.md):
- Feature overview with use cases
- Configuration precedence
- Combined example showing multiple features
- Implementation details

### Target Audience

The documentation serves two audiences:
1. **Claude Code (AI assistant)** - Needs clear implementation details, precedence rules, method signatures
2. **Human developers** - Needs usage examples, CLI commands, YAML configuration patterns

### Feature Scope (Based on Issue Analysis)

From analyzing DTL-029 through DTL-034, the time dimension organization features include:

1. **group_label Configuration**:
   - Default: "Time Dimensions" for all time dimension_groups
   - Configurable at: dimension metadata, generator parameter, CLI flag
   - Can be explicitly disabled with empty string or --no-time-dimension-group-label

2. **group_item_label Support** (Optional):
   - Disabled by default (backward compatible)
   - Enabled via --use-group-item-label CLI flag or generator parameter
   - Uses Liquid templating to extract timeframe names
   - Shows clean labels like "Date", "Month" instead of "Rental Created Date"

3. **Hierarchical Organization**:
   - Creates nested structure in Looker field picker
   - Uses dimension_group's label for sub-grouping
   - Prevents flat list of all timeframes mixed together

## Implementation Strategy

### 1. Documentation Structure

Add new section "Time Dimension Organization" in CLAUDE.md under "Important Implementation Details" (after line 458, following Field Visibility Control).

**Section outline**:
```
### Time Dimension Organization

#### Overview
[What it does, why it exists, problem it solves]

#### Default Behavior
[Out-of-box behavior with "Time Dimensions" default]

#### Configuration Levels (Precedence: Highest to Lowest)
[3-tier precedence chain]

#### Examples
##### Example 1: Default Behavior
##### Example 2: Dimension Metadata Override
##### Example 3: Generator-Level Configuration
##### Example 4: CLI Usage
##### Example 5: Disabling Grouping

#### group_item_label (Optional)
[How to enable, what it does, examples]

#### Implementation Details
[Classes, methods, parameters involved]

#### Field Picker Organization
[Before/after visual examples]

#### LookML Output Examples
[Generated code samples]
```

### 2. Content Development Approach

**Phase 1: Core Documentation**
- Write overview and problem statement
- Document default behavior
- Create precedence chain with explanations

**Phase 2: Examples**
- Develop YAML examples for semantic model configuration
- Create CLI command examples with all flags
- Show generator parameter examples
- Include edge cases (disabling, empty string)

**Phase 3: Technical Details**
- Document ConfigMeta schema field
- Document LookMLGenerator parameters
- Document CLI flags
- Reference implementation methods

**Phase 4: Visual Examples**
- Create before/after field picker organization examples
- Show LookML output with group_label
- Show LookML output with group_item_label
- Show combined examples

### 3. Consistency Guidelines

**Follow existing patterns**:
- Use same section structure as Timezone Conversion
- Use code blocks with language hints (```yaml, ```bash, ```lookml, ```python)
- Use precedence numbering (1, 2, 3, 4) with bold labels
- Use #### for subsections within feature
- Include "Implementation Details" section with bullet points
- Reference specific files and methods

**Terminology**:
- "dimension_group" (LookML term)
- "time dimension" (semantic layer term)
- "field picker" (Looker UI)
- "hierarchical organization" (feature name)
- "timeframes" (date, week, month, quarter, year)

### 4. Integration Points

**Update existing sections**:
- Add reference in "Semantic Model → LookML Conversion" (line 143)
- Potentially add to "Common Pitfalls" if relevant

**Cross-references**:
- Link to related features (hierarchy labels, field visibility)
- Reference implementation files
- Link to related test files

### 5. Validation Approach

**Accuracy checks**:
1. Verify all code examples match actual implementation
2. Test all CLI commands shown in examples
3. Verify YAML examples parse correctly
4. Ensure precedence chain matches implementation logic
5. Validate LookML output examples match generator output

**Completeness checks**:
1. All configuration levels documented
2. All CLI flags documented
3. All generator parameters documented
4. Edge cases covered (None, empty string, disabled)
5. Both required and optional features covered

**Quality checks**:
1. Clear and concise writing
2. Consistent with existing documentation style
3. Helpful for both AI and human audiences
4. Examples are realistic and useful

## Implementation Plan

### Step 1: Research & Verification (NOT IMPLEMENTED YET)

**Objective**: Understand what features have actually been implemented vs. planned

**Tasks**:
1. Examine ConfigMeta schema for time_dimension_group_label field
2. Check LookMLGenerator for time_dimension_group_label and use_group_item_label parameters
3. Review CLI flags in __main__.py
4. Examine Dimension._to_dimension_group_dict() implementation
5. Check test files to understand actual behavior

**Output**:
- List of implemented features
- List of features still in planning
- Understanding of actual precedence chain
- Knowledge of exact parameter names and types

### Step 2: Draft Core Documentation

**Objective**: Create main documentation sections

**Tasks**:
1. Write overview section explaining the problem and solution
2. Document default behavior ("Time Dimensions" as default group_label)
3. Create precedence chain with accurate levels
4. Draft implementation details with correct class/method references

**Output**: Core documentation structure with accurate technical details

### Step 3: Create Examples

**Objective**: Develop comprehensive, tested examples

**Tasks**:
1. Create semantic model YAML examples showing metadata configuration
2. Write CLI command examples for all flags
3. Develop Python examples showing generator usage
4. Create examples showing how to disable grouping
5. Add group_item_label examples

**Output**: 5-7 complete, working examples

### Step 4: Add Field Picker Visualizations

**Objective**: Show before/after organization

**Tasks**:
1. Create text representation of flat structure (before)
2. Create text representation of hierarchical structure (after)
3. Show multiple dimension_groups organized under "Time Dimensions"
4. Demonstrate the nesting and sub-grouping

**Output**: Clear visual examples of field picker organization

### Step 5: Create LookML Output Examples

**Objective**: Show generated code

**Tasks**:
1. Example with default group_label
2. Example with custom group_label
3. Example with group_label disabled
4. Example with group_item_label enabled
5. Example combining multiple features

**Output**: 5+ LookML code snippets showing actual output

### Step 6: Review & Polish

**Objective**: Ensure quality and consistency

**Tasks**:
1. Verify all examples against implementation
2. Check formatting consistency
3. Validate cross-references
4. Ensure terminology consistency
5. Proofread for clarity

**Output**: Polished, production-ready documentation

### Step 7: Update Issue Tracking

**Objective**: Mark issue as documented

**Tasks**:
1. Update DTL-035 issue status
2. Add state:has-strategy label
3. Reference documentation location
4. Note any deviations from original plan

**Output**: Updated issue tracking

## Success Criteria

### Completeness
- [ ] All configuration levels documented with precedence
- [ ] All CLI flags documented with examples
- [ ] All generator parameters documented
- [ ] All metadata fields documented
- [ ] Edge cases covered (None, empty string, disabled)
- [ ] Optional features (group_item_label) documented

### Accuracy
- [ ] All code examples are syntactically correct
- [ ] All CLI commands work as shown
- [ ] Precedence chain matches implementation
- [ ] LookML output examples match actual generator output
- [ ] Method/class references are accurate

### Quality
- [ ] Follows existing documentation patterns
- [ ] Clear and concise writing
- [ ] Helpful examples covering common use cases
- [ ] Visual examples aid understanding
- [ ] Appropriate level of detail for target audience

### Integration
- [ ] Placed in appropriate section of CLAUDE.md
- [ ] Cross-references to related features
- [ ] Consistent with existing documentation style
- [ ] References updated in other sections if needed

## Risk Mitigation

### Risk: Features Not Yet Implemented

**Likelihood**: Medium (based on no search results in codebase)
**Impact**: High (documentation would be inaccurate)

**Mitigation**:
1. Start with thorough code review in Step 1
2. Only document features that exist in code
3. Add notes if features are planned but not implemented
4. Verify examples against actual generator output

### Risk: Documentation Becomes Stale

**Likelihood**: Low (feature is mature once implemented)
**Impact**: Medium (users get incorrect information)

**Mitigation**:
1. Include implementation details that are stable
2. Reference specific method names that are testable
3. Include in test coverage to validate examples
4. Follow established patterns that are already maintained

### Risk: Inconsistency with Existing Documentation

**Likelihood**: Low (clear patterns exist)
**Impact**: Medium (confuses AI and human readers)

**Mitigation**:
1. Model after Timezone Conversion section explicitly
2. Use same section headers and structure
3. Use same terminology consistently
4. Review against existing sections before finalizing

### Risk: Examples Don't Match Implementation

**Likelihood**: Medium (without testing)
**Impact**: High (users can't use examples)

**Mitigation**:
1. Test all CLI commands before documenting
2. Validate YAML examples parse correctly
3. Run generator with example configs
4. Compare LookML output to documented examples

## Notes

### Important Considerations

1. **Feature Implementation Status**: This documentation assumes features DTL-030 through DTL-034 have been implemented. If not, we need to document what exists vs. what's planned.

2. **Backward Compatibility**: The documentation should emphasize backward compatibility - existing users won't see changes unless they opt in via CLI flags or metadata.

3. **Default Behavior**: The "Time Dimensions" default should be clearly stated as providing better organization out-of-box without requiring configuration.

4. **Optional Features**: group_item_label is an optional enhancement - documentation should clearly mark it as opt-in.

5. **Testing**: All examples should be verifiable through the test suite (unit, integration, golden tests).

### Documentation Placement

The new section will be inserted after "Field Visibility Control" (line 458) and before "Parser Error Handling" (line 459), making it part of the "Important Implementation Details" section.

This placement groups it with other feature-specific configuration documentation (timezone conversion, field visibility) while keeping it in the context of semantic model to LookML conversion details.

### Related Documentation

Consider also updating:
- README.md (if it has user-facing documentation)
- CLI help text (already done in implementation)
- Code docstrings (already done in implementation)
- Test documentation (in test files themselves)

For this issue, focus on CLAUDE.md as specified. Other documentation can be separate issues if needed.

## Approval

This strategy is approved for implementation once features DTL-030 through DTL-034 are confirmed to be implemented in the codebase.

**Next Steps**:
1. Create implementation spec (DTL-035-spec.md)
2. Verify feature implementation status
3. Begin documentation drafting following this strategy
4. Review and iterate
5. Update issue tracking

---

**Document History**:
- 2025-11-19: Initial strategy created

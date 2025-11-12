# Implementation Strategy: DTL-004

**Issue**: DTL-004 - Update join generation with fields parameter
**Analyzed**: 2025-11-12T23:00:00Z
**Stack**: backend
**Type**: feature

## Approach

Modify the join generation logic in `LookMLGenerator` to include a `fields` parameter that constrains exposed fields to dimensions only. This builds on DTL-002 (schema support for sets) and DTL-003 (dimension-only set generation) to complete the field exposure control mechanism. The implementation updates `_build_join_graph()` to add the fields parameter to join dictionaries, and `_generate_explores_lookml()` to serialize it correctly in the LookML output.

## Architecture Impact

**Layer**: generators (src/dbt_to_lookml/generators/)

**New Files**:
- None (modifications only)

**Modified Files**:
- `src/dbt_to_lookml/generators/lookml.py` - Add `fields` parameter to join dictionaries in `_build_join_graph()` method (lines 139-251) and ensure proper serialization in `_generate_explores_lookml()` (lines 403-480)

## Dependencies

- **Depends on**:
  - DTL-002 (LookML set schema support must be complete)
  - DTL-003 (dimension-only sets must be generated in views)
- **Packages**:
  - `lkml` library (already in use for serialization)
- **Patterns**:
  - Dictionary-based join representation (existing pattern at lines 236-241)
  - lkml library serialization patterns (existing at lines 444-454)

## Testing Strategy

- **Unit**:
  - Test `_build_join_graph()` includes `fields` parameter in all join dictionaries
  - Verify `fields` value follows format: `["{view_name}.dimensions_only*"]`
  - Test multi-hop joins (2-level deep) include fields parameter on all levels
  - Test view prefix handling in fields parameter (e.g., `v_users.dimensions_only*`)
- **Integration**:
  - Verify generated explores.lkml file contains fields parameter in join blocks
  - Confirm fields parameter appears after `relationship:` and before or after `type:` (verify lkml library serialization order)
  - Test that missing dimension sets don't cause crashes (graceful degradation)
- **Coverage Target**: 95%+ (branch coverage for fields parameter logic)

## Implementation Sequence

1. **Update `_build_join_graph()` method** (src/dbt_to_lookml/generators/lookml.py:236-241)
   - Add `fields` key to join dictionary with value `[{view_name}.dimensions_only*]`
   - Use `target_view_name` variable (already computed at line 197) for consistency

2. **Verify lkml library serialization** (src/dbt_to_lookml/generators/lookml.py:444-454)
   - Test that lkml library correctly serializes `fields` as a list parameter
   - Ensure ordering is correct (sql_on, relationship, fields, type)

3. **Add unit tests** (src/tests/unit/test_lookml_generator.py)
   - Add test case: `test_build_join_graph_includes_fields_parameter()`
   - Update existing join tests to assert `fields` key exists
   - Add test for view prefix in fields parameter

4. **Update integration/golden tests** (coordinate with DTL-006)
   - Ensure golden LookML files reflect new fields parameter
   - Update test assertions to check for fields in join blocks

5. **Manual validation**
   - Generate sample explores.lkml and verify syntax
   - Use lkml library to parse generated output as validation

## Open Questions

- **LookML syntax verification**: Does lkml library preserve list syntax for fields parameter correctly? (e.g., `fields: [view.dimensions_only*]`)
  - *Resolution approach*: Add explicit validation in unit tests to parse generated LookML back through lkml.load()

- **Field parameter ordering**: What is the correct/conventional order of join parameters in LookML?
  - *Resolution approach*: Check Looker documentation or examine lkml library serialization behavior; order may not be strictly enforced

- **Missing dimension sets**: Should joins fail or warn if a view doesn't have a dimensions_only set?
  - *Resolution approach*: Assume DTL-003 ensures all views have sets; this issue focuses only on join generation

## Estimated Complexity

**Complexity**: Low
**Estimated Time**: 2-3 hours

**Rationale**:
- Simple dictionary modification (1 line addition in join dict)
- Well-established testing patterns already exist
- No new dependencies or architectural changes
- Main work is comprehensive test coverage

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-004.md`
3. Change status from `awaiting-strategy-review` to `strategy-approved`
4. Run: `/plan:spec DTL-004`

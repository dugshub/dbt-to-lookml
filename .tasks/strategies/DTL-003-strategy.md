# Implementation Strategy: DTL-003

**Issue**: DTL-003 - Generate dimension-only field sets in views
**Analyzed**: 2025-11-12T19:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Add automatic generation of `set: dimensions_only` field sets to all LookML view files. This set will contain references to all dimension fields (including hidden entity dimensions) to support selective field exposure in explore joins.

The implementation adds a new `_generate_dimension_set()` private method to `LookMLGenerator` and integrates it into the existing `_generate_view_lookml()` method to emit the set alongside dimensions and measures in the view structure.

## Architecture Impact

**Layer**: generators (backend)

**New Files**: None

**Modified Files**:
- `src/dbt_to_lookml/generators/lookml.py` - Add `_generate_dimension_set()` method and integrate into view generation
- `src/dbt_to_lookml/schemas.py` - Add `LookMLSet` Pydantic schema class for type safety
- `src/tests/unit/test_lookml_generator.py` - Add test coverage for dimension set generation

## Dependencies

**Depends on**: DTL-002 (LookML set support in schemas) - blocking dependency
**Packages**:
- `lkml` - Already used for LookML serialization
- `pydantic` - Already used for schema validation

**Patterns**:
- Follow existing generator patterns in `LookMLGenerator` class
- Use private `_generate_*` methods for sub-component generation
- Maintain strict type hints (mypy --strict)
- Preserve existing view structure ordering: entities → dimensions → measures → sets

## Implementation Sequence

1. **Add LookMLSet schema** (if not in DTL-002)
   - Create `LookMLSet` Pydantic model in `schemas.py`
   - Fields: `name: str`, `fields: list[str]`
   - Add `to_lookml_dict()` method for serialization

2. **Implement `_generate_dimension_set()` method**
   - Create private method in `LookMLGenerator` class
   - Accept `SemanticModel` as parameter
   - Collect dimension names from:
     - All entities (entity.name)
     - All dimensions (dimension.name)
   - Return `LookMLSet(name="dimensions_only", fields=[...])`
   - Handle empty case gracefully (views with no dimensions)

3. **Integrate into `_generate_view_lookml()`**
   - Call `_generate_dimension_set()` after dimension/measure conversion
   - Add 'sets' key to view_dict if dimensions exist
   - Maintain existing lkml.dump() serialization flow
   - Ensure proper formatting with `_format_lookml_content()`

4. **Update `SemanticModel.to_lookml_dict()`**
   - Add sets collection to view_dict structure
   - Ensure sets appear after measures in output
   - Handle case where view has no dimensions (no set needed)

5. **Testing**
   - Unit test: `test_generate_dimension_set()` - verify all dimensions collected
   - Unit test: `test_generate_dimension_set_empty()` - verify graceful handling of no dimensions
   - Unit test: `test_dimension_set_includes_hidden_entities()` - verify hidden entities included
   - Unit test: `test_dimension_set_in_view_output()` - verify set appears in generated LookML
   - Target: 95%+ branch coverage for new code

## Open Questions

- Should the set name be configurable (`dimensions_only` vs custom names)?
  - **Answer**: Start with hardcoded `dimensions_only` - matches epic requirement
- Should dimension_groups be included in the set?
  - **Answer**: Yes - dimension_groups are dimensions (time-based), must be in set
- How to handle views with zero dimensions?
  - **Answer**: Don't generate set if no dimensions exist (validation edge case)

## Estimated Complexity

**Complexity**: Low
**Estimated Time**: 2-3 hours

**Breakdown**:
- Schema additions: 30 mins
- Generator method implementation: 45 mins
- Integration into view generation: 30 mins
- Unit test coverage: 60 mins
- Manual testing and validation: 15 mins

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-003.md`
3. Change status from `awaiting-strategy-review` to `strategy-approved`
4. Run: `/plan:spec DTL-003`

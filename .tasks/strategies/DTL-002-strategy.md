# Implementation Strategy: DTL-002

**Issue**: DTL-002 - Add LookML set support to schemas
**Analyzed**: 2025-11-12T22:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Add LookML `set:` support to the schema layer by creating a new `LookMLSet` Pydantic model and integrating it into `LookMLView`. Sets represent reusable field collections in LookML, critical for field exposure control in explores and joins. This is a pure schema extension with no parser or generator changes required at this stage.

## Architecture Impact

**Layer**: schemas (atoms layer - core data models)

**New Files**:
- None (extending existing `src/dbt_to_lookml/schemas.py`)

**Modified Files**:
- `src/dbt_to_lookml/schemas.py` - Add `LookMLSet` class and integrate into `LookMLView`
  - Add `LookMLSet(BaseModel)` class after `LookMLMeasure` (line ~427)
  - Add `sets: List[LookMLSet]` field to `LookMLView` (line ~437)
  - Update `LookMLView.to_lookml_dict()` to include sets in output (line ~439-478)
  - Ensure sets appear after `sql_table_name` but before `dimensions` in dict ordering

## Dependencies

- **Depends on**: None (foundational schema work for DTL-001 epic)
- **Packages**:
  - `pydantic` (already in use for all schema models)
  - No new dependencies required
- **Patterns**:
  - Follow existing `LookML*` model patterns (BaseModel with Optional fields)
  - Use `to_lookml_dict()` pattern with `convert_bools()` helper
  - Maintain backward compatibility with `Optional` and `default_factory=list`
  - Follow mypy --strict requirements (full type hints)

## Testing Strategy

- **Unit**:
  - Test `LookMLSet` model validation (required fields, optional fields)
  - Test `LookMLSet` with various field lists
  - Test `LookMLView.to_lookml_dict()` with and without sets
  - Test sets ordering in output dict (after sql_table_name, before dimensions)
  - Test backward compatibility (views without sets still work)
- **Integration**:
  - Not required at this stage (no parser/generator changes)
- **Coverage Target**: 95%+ (per project standards)

## Implementation Sequence

1. **Add LookMLSet model** (15 min)
   - Create `LookMLSet(BaseModel)` class in `schemas.py` after `LookMLMeasure`
   - Fields: `name: str`, `fields: List[str]`
   - Follow existing schema patterns

2. **Integrate sets into LookMLView** (10 min)
   - Add `sets: List[LookMLSet] = Field(default_factory=list)` to `LookMLView`
   - Maintain backward compatibility with Optional default

3. **Update LookMLView.to_lookml_dict()** (20 min)
   - Add sets serialization logic after `sql_table_name`
   - Use existing `convert_bools()` helper pattern
   - Ensure dict ordering: `name` → `sql_table_name` → `sets` → `dimensions` → `dimension_groups` → `measures`

4. **Write unit tests** (45 min)
   - Test `LookMLSet` validation in `test_schemas.py`
   - Test `LookMLView` with sets in `test_schemas.py`
   - Test `to_lookml_dict()` output format and ordering
   - Test backward compatibility

5. **Verify type checking and coverage** (10 min)
   - Run `make type-check` (mypy --strict)
   - Run `make test-coverage` (verify 95%+ branch coverage)

## Open Questions

- **Field naming convention**: Should set fields use dimension names directly or require prefixes?
  - *Decision*: Use dimension names directly (standard LookML pattern)
- **Set ordering**: Should sets have explicit ordering control?
  - *Decision*: Not needed for this iteration - simple list is sufficient

## Estimated Complexity

**Complexity**: Low
**Estimated Time**: 1.5-2 hours

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-002.md`
3. Change status from `awaiting-strategy-review` to `strategy-approved`
4. Run: `/plan:spec DTL-002`

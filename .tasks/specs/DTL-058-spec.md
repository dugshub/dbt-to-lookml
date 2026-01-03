---
id: DTL-058-spec
issue: DTL-058
title: "Implementation Spec: Update documentation for derived metric PoP support"
type: spec
status: Ready
created: 2025-12-22
stack: backend
---

# Implementation Spec: Update documentation for derived metric PoP support

## Metadata
- **Issue**: `DTL-058`
- **Stack**: `backend`
- **Type**: `chore`
- **Generated**: 2025-12-22
- **Epic**: DTL-054 (PoP Support for Same-Model Derived Metrics)
- **Depends on**: DTL-055 (COMPLETE), DTL-056

## Issue Context

### Problem Statement

The project documentation currently states that derived metrics don't support PoP. Once DTL-056 is implemented, this documentation needs to be updated to reflect the new capability.

**Current documentation** (CLAUDE.md line 124):
> **Limitation**: Only simple metrics are supported (they generate direct aggregates). Ratio/derived metrics silently skip PoP due to Looker `type: number` limitations.

This is outdated once derived/ratio metrics with same-model parents support PoP.

### Solution Approach

Update CLAUDE.md and .claude/ai-docs/conversion-rules.md to:
1. Remove or update the limitation note
2. Document the new same-model PoP support for derived/ratio metrics
3. Explain qualifying criteria
4. Provide examples

### Success Criteria

- [ ] CLAUDE.md limitation note updated
- [ ] Conversion rules documented
- [ ] Examples provided for derived metric PoP
- [ ] Documentation accurate and clear

## Implementation Plan

### Phase 1: Update CLAUDE.md

**File**: `CLAUDE.md`

**Location**: Lines 105-127 (Period-over-Period section)

**Current content** (lines 105-126):
```markdown
### Period-over-Period (PoP) on Metrics

Define PoP directly on simple metrics (cleaner than measure-level PoP):

```yaml
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    meta:
      primary_entity: order
      pop:
        enabled: true
        comparisons: [pp, py]  # prior period, prior year
        windows: [month]       # month, quarter, week
        format: usd            # optional value format
```

**Limitation**: Only simple metrics are supported (they generate direct aggregates). Ratio/derived metrics silently skip PoP due to Looker `type: number` limitations.
```

**Updated content**:
```markdown
### Period-over-Period (PoP) on Metrics

Define PoP on metrics to generate period_over_period comparison measures:

```yaml
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    meta:
      primary_entity: order
      pop:
        enabled: true
        comparisons: [pp, py]  # prior period, prior year
        windows: [month]       # month, quarter, week
        format: usd            # optional value format
```

**Supported Metric Types**:
- **Simple metrics**: Always supported (generate direct aggregates)
- **Ratio metrics**: Supported when numerator and denominator are from the same semantic model
- **Derived metrics**: Supported when all parent metrics recursively resolve to same-model simple/ratio metrics

**Same-Model Requirement**: Ratio and derived metrics qualify for PoP only when all referenced measures/metrics belong to the same semantic model (share the same `primary_entity`). Cross-model metrics are silently skipped.

#### Derived Metric PoP Example

```yaml
metrics:
  # Simple metrics (same model)
  - name: gained_eom
    type: simple
    type_params:
      measure: gained_count
    meta:
      primary_entity: facility

  - name: lost_eom
    type: simple
    type_params:
      measure: lost_count
    meta:
      primary_entity: facility

  # Derived metric with PoP (all parents same-model)
  - name: net_change_eom
    type: derived
    type_params:
      expr: gained - lost
      metrics:
        - name: gained_eom
          alias: gained
        - name: lost_eom
          alias: lost
    meta:
      primary_entity: facility
      pop:
        enabled: true
        comparisons: [py, pp]
        windows: [month]
```

**Generated PoP measures** for `net_change_eom`:
- `net_change_eom_py` - Prior year value
- `net_change_eom_py_change` - Year-over-year change
- `net_change_eom_py_pct_change` - Year-over-year percent change
- `net_change_eom_pm` - Prior month value
- `net_change_eom_pm_change` - Month-over-month change
- `net_change_eom_pm_pct_change` - Month-over-month percent change
```

### Phase 2: Update conversion-rules.md

**File**: `.claude/ai-docs/conversion-rules.md`

**Location**: After line 116 (after Reference Resolution section)

**Add new section**:
```markdown
## Period-over-Period (PoP) Support

### Metric Eligibility

Not all metrics support PoP generation. Eligibility is determined by the `is_pop_eligible_metric` function:

| Metric Type | PoP Supported | Condition |
|-------------|---------------|-----------|
| Simple | Yes | Has `primary_entity` specified |
| Ratio | Conditional | Numerator and denominator measures from same semantic model |
| Derived | Conditional | All parent metrics recursively resolve to eligible metrics on same model |
| Conversion | No | Not supported |

### Same-Model Detection

For ratio and derived metrics, "same-model" means:
1. All measures/metrics share the same `primary_entity`
2. For derived: recursively checked through all parent metrics
3. For nested derived: all leaf simple metrics must be same-model

### Generated PoP Measures

For each eligible metric with `pop.enabled: true`, the following measures are generated:

| Suffix | Type | Description |
|--------|------|-------------|
| `_py` | previous | Prior year value |
| `_pm` | previous | Prior month value |
| `_pq` | previous | Prior quarter value |
| `_pw` | previous | Prior week value |
| `_py_change` | difference | Current - Prior year |
| `_py_pct_change` | relative_change | (Current - Prior) / Prior |

### LookML Output

```lookml
# Generated from derived metric with pop.enabled
measure: net_change_eom_py {
  type: period_over_period
  based_on: net_change_eom
  based_on_time: report_date_date
  period: year
  kind: previous
  view_label: " Metrics (PoP)"
  group_label: "Net Change Eom (PoP)"
  label: "Net Change Eom (Prior Year)"
}
```

### Implementation Details

- **Function**: `is_pop_eligible_metric()` in `generators/lookml.py`
- **Filtering**: Applied in `generate()` method before PoP measure generation
- **Backwards compatibility**: `is_same_model_derived_metric()` wrapper for derived-only checks
```

### Phase 3: Update Key Conversion Rules Table

**File**: `CLAUDE.md`

**Location**: Lines 93-102 (Key Conversion Rules table)

**Update the table** to include PoP information:

**Current**:
```markdown
| Metric PoP | `period_over_period` measures referencing metric directly (no hidden base) |
```

**Updated**:
```markdown
| Metric PoP | `period_over_period` measures; simple always supported, ratio/derived if same-model |
```

## File Changes

### Files to Modify

#### `CLAUDE.md`

**Why**: Primary project documentation

**Changes**:
1. Update "Period-over-Period (PoP) on Metrics" section (lines 105-126)
2. Replace "Limitation" note with "Supported Metric Types" section
3. Add derived metric PoP example
4. Update Key Conversion Rules table

**Estimated changes**: ~50 lines modified/added

#### `.claude/ai-docs/conversion-rules.md`

**Why**: Detailed conversion rules documentation

**Changes**:
1. Add "Period-over-Period (PoP) Support" section after line 116
2. Document eligibility criteria
3. Document generated measures
4. Include LookML output example

**Estimated changes**: ~60 lines added

## Validation

### Documentation Accuracy Check

After making changes, verify:

1. **Example YAML is valid**: Can be parsed without errors
2. **LookML output is accurate**: Matches actual generated output
3. **Terminology is consistent**: Same terms used throughout
4. **Cross-references work**: Links to related sections are correct

### Manual Verification

1. Generate LookML with a derived metric + PoP enabled
2. Compare output to documented examples
3. Verify any discrepancies and update docs

## Dependencies

### Related Issues

- **Parent**: DTL-054 (Epic)
- **Depends on**: DTL-055 (COMPLETE), DTL-056 (implementation must be complete first)

## Implementation Notes

### Key Points to Document

1. **Same-model requirement**: Critical for understanding which metrics qualify
2. **Recursive resolution**: Nested derived metrics are supported
3. **Silent skipping**: Cross-model metrics don't error, just skip PoP
4. **Generated measure naming**: Predictable pattern for users

### Documentation Style

Follow existing documentation patterns:
- Use code blocks for YAML and LookML examples
- Use tables for mappings and options
- Bold key terms on first use
- Keep paragraphs concise

## Ready for Implementation

This spec is ready for implementation after DTL-056 is complete.

**Implementation Steps**:
1. Wait for DTL-056 implementation to be merged
2. Update CLAUDE.md PoP section
3. Add PoP section to conversion-rules.md
4. Review and verify accuracy

**Estimated Effort**: 30-45 minutes
- CLAUDE.md updates: 20 minutes
- conversion-rules.md updates: 15 minutes
- Review and verification: 10 minutes

**Success Criteria**:
- [ ] Limitation note removed/updated
- [ ] Same-model support documented
- [ ] Derived metric example added
- [ ] Conversion rules updated
- [ ] Documentation accurate and consistent

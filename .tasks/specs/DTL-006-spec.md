# Implementation Spec: DTL-006 - Update integration and golden tests

**Issue**: DTL-006
**Strategy**: [DTL-006-strategy.md](../strategies/DTL-006-strategy.md)
**Generated**: 2025-11-12T19:00:00Z
**Type**: feature
**Stack**: backend

---

## Overview

This spec details the implementation of comprehensive integration and golden file tests to validate the field exposure control epic (DTL-001). The tests will verify that:

1. Field sets (`set: dimensions_only`) are generated correctly in all views
2. Explore joins properly constrain exposed fields using the `fields:` parameter
3. Multi-hop joins maintain field constraints through the chain
4. Generated LookML matches expected golden file output

**Dependencies**: Requires DTL-002 (LookML set schema support), DTL-003 (field set generation), and DTL-004 (join field constraints) to be complete.

---

## 1. Test Fixture Setup in `src/semantic_models/`

### 1.1 Directory Structure

Create semantic model fixtures that represent real-world scenarios:

```
src/semantic_models/
├── sem_users.yml           # Dimension table with primary entity
├── sem_searches.yml        # Dimension table with foreign key (for multi-hop)
└── sem_rental_orders.yml   # Fact table with foreign keys
```

**Note**: The directory `src/semantic_models/` already exists (created empty). We need to populate it with YAML files.

### 1.2 Fixture: `sem_users.yml` (Dimension Table)

**Purpose**: Dimension table representing user data with both dimensions and measures.

**Structure**:
```yaml
semantic_models:
  - name: users
    model: ref('dim_renter')
    description: User dimension table with renter profile data

    entities:
      - name: user_sk
        type: primary
        expr: user_sk
        description: Primary surrogate key for users

    dimensions:
      - name: user_id
        type: categorical
        expr: user_id
        description: Natural user identifier

      - name: email_domain
        type: categorical
        expr: "SPLIT_PART(email, '@', 2)"
        description: Email domain for user segmentation

      - name: account_status
        type: categorical
        expr: status
        description: Current account status (active, suspended, closed)

      - name: created_date
        type: time
        expr: created_at
        type_params:
          time_granularity: day
        description: Date when user account was created

      - name: signup_source
        type: categorical
        expr: signup_source
        description: Channel through which user signed up

    measures:
      - name: user_count
        agg: count
        description: Total number of users

      - name: active_users
        agg: count_distinct
        expr: "CASE WHEN status = 'active' THEN user_id END"
        description: Count of active users

      - name: avg_lifetime_rentals
        agg: average
        expr: total_rentals
        description: Average number of rentals per user
```

**Expected dimension count**: 9 (1 entity + 5 categorical + 3 time dimension fields [created_date_date, created_date_month, created_date_year])
**Expected measure count**: 3
**Key features**: Primary entity (hidden), time dimension with granularity, complex SQL expressions, multiple aggregation types

### 1.3 Fixture: `sem_searches.yml` (Dimension with FK)

**Purpose**: Dimension table with foreign key to enable multi-hop join testing (rentals → searches → sessions future scenario).

**Structure**:
```yaml
semantic_models:
  - name: searches
    model: ref('dim_searches')
    description: Search dimension table for search analytics

    entities:
      - name: search_sk
        type: primary
        expr: search_sk
        description: Primary surrogate key for searches

      - name: user_sk
        type: foreign
        expr: user_sk
        description: Foreign key to users dimension

    dimensions:
      - name: search_query
        type: categorical
        expr: search_query_text
        description: User search query text

      - name: results_count
        type: categorical
        expr: "CAST(num_results AS VARCHAR)"
        description: Number of search results returned

      - name: search_date
        type: time
        expr: searched_at
        type_params:
          time_granularity: day
        description: Date when search was performed

      - name: result_quality
        type: categorical
        expr: "CASE WHEN num_results > 0 THEN 'with_results' ELSE 'no_results' END"
        description: Quality indicator for search results

    measures:
      - name: search_count
        agg: count
        description: Total number of searches

      - name: searches_with_results
        agg: count_distinct
        expr: "CASE WHEN num_results > 0 THEN search_sk END"
        description: Count of searches that returned results
```

**Expected dimension count**: 8 (2 entities + 3 categorical + 3 time fields)
**Expected measure count**: 2
**Key features**: Primary + foreign entity (both hidden), enables multi-hop join testing

### 1.4 Fixture: `sem_rental_orders.yml` (Fact Table)

**Purpose**: Fact table with foreign keys to both users and searches, representing the base explore.

**Structure**:
```yaml
semantic_models:
  - name: rental_orders
    model: ref('fct_rental')
    description: Rental transaction fact table

    entities:
      - name: rental_sk
        type: primary
        expr: rental_sk
        description: Primary surrogate key for rental transactions

      - name: user_sk
        type: foreign
        expr: renter_sk
        description: Foreign key to users dimension

      - name: search_sk
        type: foreign
        expr: search_sk
        description: Foreign key to searches dimension

    dimensions:
      - name: booking_status
        type: categorical
        expr: status
        description: Current booking status (confirmed, cancelled, completed)

      - name: rental_date
        type: time
        expr: booking_date
        type_params:
          time_granularity: day
        description: Date of rental booking

      - name: payment_method
        type: categorical
        expr: payment_type
        description: Method of payment used

    measures:
      - name: rental_count
        agg: count
        description: Total number of rentals

      - name: total_revenue
        agg: sum
        expr: checkout_amount
        description: Total rental revenue

      - name: avg_rental_value
        agg: average
        expr: checkout_amount
        description: Average revenue per rental
```

**Expected dimension count**: 6 (3 entities + 2 categorical + 3 time fields, but entities hidden)
**Expected measure count**: 3
**Key features**: Multiple foreign keys, enables join graph testing

---

## 2. Golden File Regeneration Process

### 2.1 Prerequisites

**Before regenerating golden files**, ensure:
- DTL-002 (LookML set schema) is implemented and merged
- DTL-003 (field set generation) is implemented and merged
- DTL-004 (join field constraints) is implemented and merged
- Semantic model fixtures (from Section 1) are created in `src/semantic_models/`

### 2.2 Regeneration Steps

**Step 1: Generate baseline LookML output**

```bash
# From repository root
uv run python -m dbt_to_lookml generate \
  -i src/semantic_models \
  -o src/tests/golden/temp_output \
  --validate
```

**Expected output**:
- `temp_output/users.view.lkml`
- `temp_output/searches.view.lkml`
- `temp_output/rental_orders.view.lkml`
- `temp_output/explores.lkml`

**Step 2: Manual validation**

Review each generated file to verify:

1. **View files contain `set: dimensions_only`**:
   ```bash
   grep -n "set: dimensions_only" src/tests/golden/temp_output/*.view.lkml
   ```
   Expected: 3 matches (one per view)

2. **Sets include all dimensions** (including hidden entities):
   ```bash
   # Verify users.view.lkml has user_sk in set
   grep -A 15 "set: dimensions_only" src/tests/golden/temp_output/users.view.lkml
   ```
   Expected: `user_sk` should appear in fields list

3. **Explores file has `fields:` in joins**:
   ```bash
   grep "fields:" src/tests/golden/temp_output/explores.lkml
   ```
   Expected: 2 matches (one for `join: users`, one for `join: searches`)

4. **Parse with lkml library**:
   ```bash
   python -c "import lkml; print(lkml.load(open('src/tests/golden/temp_output/users.view.lkml').read()))"
   ```
   Expected: No parse errors

**Step 3: Copy to golden directory**

```bash
# Copy view files with expected_ prefix
cp src/tests/golden/temp_output/users.view.lkml \
   src/tests/golden/expected_users.view.lkml

cp src/tests/golden/temp_output/searches.view.lkml \
   src/tests/golden/expected_searches.view.lkml

cp src/tests/golden/temp_output/rental_orders.view.lkml \
   src/tests/golden/expected_rental_orders.view.lkml

# Copy explores file
cp src/tests/golden/temp_output/explores.lkml \
   src/tests/golden/expected_explores.lkml

# Clean up temporary directory
rm -rf src/tests/golden/temp_output
```

**Step 4: Verify golden files**

```bash
# Ensure files exist
ls -lh src/tests/golden/expected_*.lkml

# Quick validation
make test-golden
```

### 2.3 Helper Method for Regeneration

Add to `src/tests/test_golden.py` (not run as part of test suite):

```python
def regenerate_golden_files_for_field_sets(self, golden_dir: Path) -> None:
    """Helper to regenerate golden files with field set support.

    This is a development utility, not a test. Run manually when:
    - DTL-002/003/004 implementations are complete
    - Semantic model fixtures in src/semantic_models/ are created
    - Expected output format has changed due to schema updates

    Usage:
        pytest src/tests/test_golden.py::TestGoldenFiles::regenerate_golden_files_for_field_sets -v

    Note: This will OVERWRITE existing golden files. Review changes before committing.
    """
    from tempfile import TemporaryDirectory

    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
    parser = DbtParser()
    generator = LookMLGenerator()

    # Parse all fixture models
    all_models = parser.parse_directory(semantic_models_dir)
    assert len(all_models) == 3, f"Expected 3 models, found {len(all_models)}"

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            all_models, output_dir
        )

        assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"

        # Copy each view file to golden directory with expected_ prefix
        for generated_file in generated_files:
            if generated_file.name.endswith(".view.lkml"):
                # Extract model name (e.g., "users" from "users.view.lkml")
                model_name = generated_file.stem.replace(".view", "")
                golden_file = golden_dir / f"expected_{model_name}.view.lkml"
                content = generated_file.read_text()
                golden_file.write_text(content)
                print(f"Regenerated: {golden_file.name}")

            elif generated_file.name == "explores.lkml":
                golden_file = golden_dir / "expected_explores.lkml"
                content = generated_file.read_text()
                golden_file.write_text(content)
                print(f"Regenerated: {golden_file.name}")

    print(f"\nRegenerated {len(all_models)} view files + 1 explores file")
    print("Review changes with: git diff src/tests/golden/")
```

---

## 3. Integration Test Additions

### 3.1 New File: `src/tests/integration/test_join_field_exposure.py`

**Purpose**: Dedicated integration tests for field exposure control in joins.

**Test Cases**:

#### 3.1.1 Test: Single Join Field Exposure

```python
"""Integration tests for join field exposure control."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Any

import pytest
lkml = pytest.importorskip("lkml")

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.generators.lookml import LookMLGenerator


class TestJoinFieldExposure:
    """Test field exposure control in explore joins."""

    @pytest.fixture
    def semantic_models_dir(self) -> Path:
        """Return path to semantic models test fixtures."""
        return Path(__file__).parent.parent / "semantic_models"

    def test_single_join_has_field_constraint(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that single join includes fields parameter with dimensions_only set.

        Scenario: Fact table (rental_orders) joins dimension table (users)
        Expected: Join should have fields: [users.dimensions_only*]
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        # Parse rental_orders (fact) and users (dimension)
        all_models = parser.parse_directory(semantic_models_dir)
        fact_models = [m for m in all_models if m.name == 'rental_orders']

        assert len(fact_models) == 1

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Parse explores file
            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            # Find rental_orders explore
            rental_explore = None
            for explore in parsed.get('explores', []):
                if explore['name'] == 'rental_orders':
                    rental_explore = explore
                    break

            assert rental_explore is not None, "rental_orders explore not found"

            # Verify joins exist
            joins = rental_explore.get('joins', [])
            assert len(joins) >= 1, "Expected at least one join"

            # Find users join
            users_join = None
            for join in joins:
                if join['name'] == 'users':
                    users_join = join
                    break

            assert users_join is not None, "users join not found"

            # Verify fields parameter exists and references dimensions_only
            assert 'fields' in users_join, "fields parameter missing from join"
            fields_value = users_join['fields']

            # Should be a list with one element: "users.dimensions_only*"
            assert isinstance(fields_value, list)
            assert len(fields_value) == 1
            assert fields_value[0] == 'users.dimensions_only*'
```

#### 3.1.2 Test: Multi-hop Join Field Exposure

```python
    def test_multi_hop_joins_have_field_constraints(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that multi-hop joins maintain field constraints at each level.

        Scenario: rental_orders → users, rental_orders → searches
        Expected: Both joins should have fields parameter
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            # Find rental_orders explore
            rental_explore = None
            for explore in parsed.get('explores', []):
                if explore['name'] == 'rental_orders':
                    rental_explore = explore
                    break

            assert rental_explore is not None
            joins = rental_explore.get('joins', [])

            # Should have at least 2 joins (users and searches)
            assert len(joins) >= 2

            # Verify each join has fields parameter
            for join in joins:
                join_name = join['name']
                assert 'fields' in join, f"fields parameter missing from {join_name} join"

                fields_value = join['fields']
                assert isinstance(fields_value, list)
                assert len(fields_value) == 1

                # Should reference the joined view's dimensions_only set
                expected_field = f"{join_name}.dimensions_only*"
                assert fields_value[0] == expected_field, \
                    f"Expected {expected_field}, got {fields_value[0]}"
```

#### 3.1.3 Test: Dimension-only Exposure Verification

```python
    def test_join_fields_exclude_measures(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that joined views only expose dimensions, not measures.

        Verification: Parse generated view to extract dimension names,
        then verify the dimensions_only set matches those dimensions
        and does NOT include measure names.
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)
        users_model = next(m for m in all_models if m.name == 'users')

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Parse users view
            users_view_file = output_dir / "users.view.lkml"
            users_content = users_view_file.read_text()
            parsed_view = lkml.load(users_content)

            view = parsed_view['views'][0]

            # Extract set definition
            sets = view.get('sets', [])
            assert len(sets) == 1, "Expected exactly one set (dimensions_only)"

            dimensions_only_set = sets[0]
            assert dimensions_only_set['name'] == 'dimensions_only'

            set_fields = dimensions_only_set['fields']

            # Collect actual dimension names from view
            dimension_names = [d['name'] for d in view.get('dimensions', [])]

            # Collect time dimension field names (dimension_group generates multiple fields)
            dimension_group_fields = []
            for dg in view.get('dimension_groups', []):
                base_name = dg['name']
                timeframes = dg.get('timeframes', ['date', 'week', 'month', 'quarter', 'year'])
                for tf in timeframes:
                    dimension_group_fields.append(f"{base_name}_{tf}")

            all_dimension_fields = dimension_names + dimension_group_fields

            # Verify all dimensions are in the set
            for dim_field in all_dimension_fields:
                assert dim_field in set_fields, \
                    f"Dimension {dim_field} missing from dimensions_only set"

            # Verify measures are NOT in the set
            measure_names = [m['name'] for m in view.get('measures', [])]
            for measure_name in measure_names:
                assert measure_name not in set_fields, \
                    f"Measure {measure_name} should NOT be in dimensions_only set"
```

#### 3.1.4 Test: Hidden Entity Inclusion in Sets

```python
    def test_hidden_entities_included_in_dimension_sets(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that hidden entities (primary/foreign keys) are included in dimension sets.

        Rationale: Hidden entities are needed for join relationships to work,
        so they must be in the dimensions_only set even though they're hidden.
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check users view (has user_sk primary entity)
            users_view_file = output_dir / "users.view.lkml"
            users_content = users_view_file.read_text()
            parsed_view = lkml.load(users_content)

            view = parsed_view['views'][0]

            # Find the primary key dimension (should be hidden)
            user_sk_dim = None
            for dim in view.get('dimensions', []):
                if dim['name'] == 'user_sk':
                    user_sk_dim = dim
                    break

            assert user_sk_dim is not None, "user_sk dimension not found"
            assert user_sk_dim.get('hidden') == 'yes', "user_sk should be hidden"
            assert user_sk_dim.get('primary_key') == 'yes', "user_sk should be primary key"

            # Verify it's in the dimensions_only set
            sets = view.get('sets', [])
            dimensions_only_set = next(s for s in sets if s['name'] == 'dimensions_only')

            assert 'user_sk' in dimensions_only_set['fields'], \
                "Hidden entity user_sk must be in dimensions_only set for joins to work"
```

### 3.2 Updates to `src/tests/integration/test_end_to_end.py`

Add assertions to existing tests to verify field set presence:

```python
# Add to TestEndToEndIntegration class

def test_generated_views_contain_field_sets(self) -> None:
    """Test that all generated views contain dimensions_only field sets."""
    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"

    parser = DbtParser()
    generator = LookMLGenerator()

    all_models = parser.parse_directory(semantic_models_dir)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            all_models, output_dir
        )

        assert len(validation_errors) == 0

        # Verify each view has a dimensions_only set
        view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]

        for view_file in view_files:
            content = view_file.read_text()
            assert "set: dimensions_only" in content, \
                f"View {view_file.name} missing dimensions_only set"

            # Parse and verify structure
            parsed = lkml.load(content)
            view = parsed['views'][0]
            sets = view.get('sets', [])

            assert len(sets) == 1, f"Expected 1 set in {view_file.name}"
            assert sets[0]['name'] == 'dimensions_only'
            assert 'fields' in sets[0]
            assert len(sets[0]['fields']) > 0

def test_generated_explores_have_join_field_constraints(self) -> None:
    """Test that all explore joins include fields parameter."""
    semantic_models_dir = Path(__file__).parent.parent / "semantic_models"

    parser = DbtParser()
    generator = LookMLGenerator()

    all_models = parser.parse_directory(semantic_models_dir)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            all_models, output_dir
        )

        assert len(validation_errors) == 0

        explores_file = output_dir / "explores.lkml"
        explores_content = explores_file.read_text()
        parsed = lkml.load(explores_content)

        # Find explores with joins
        for explore in parsed.get('explores', []):
            joins = explore.get('joins', [])

            # If explore has joins, verify they have fields parameter
            for join in joins:
                assert 'fields' in join, \
                    f"Join {join['name']} in explore {explore['name']} missing fields parameter"

                # Verify format: [view_name.dimensions_only*]
                fields_value = join['fields']
                assert isinstance(fields_value, list)
                assert len(fields_value) == 1
                assert fields_value[0].endswith('.dimensions_only*')
```

---

## 4. Field Exposure Validation Logic

### 4.1 Validation Helper Functions

Add to `src/tests/integration/test_join_field_exposure.py`:

```python
def _extract_dimension_fields_from_view(
    view_dict: Dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Extract dimension and measure field names from parsed LookML view.

    Args:
        view_dict: Parsed LookML view dictionary

    Returns:
        Tuple of (dimension_field_names, measure_field_names)
    """
    dimension_fields = []
    measure_fields = []

    # Regular dimensions
    for dim in view_dict.get('dimensions', []):
        dimension_fields.append(dim['name'])

    # Dimension groups (time dimensions) generate multiple fields
    for dg in view_dict.get('dimension_groups', []):
        base_name = dg['name']
        timeframes = dg.get('timeframes', ['date', 'week', 'month', 'quarter', 'year'])
        for tf in timeframes:
            dimension_fields.append(f"{base_name}_{tf}")

    # Measures
    for measure in view_dict.get('measures', []):
        measure_fields.append(measure['name'])

    return dimension_fields, measure_fields


def _verify_set_contains_only_dimensions(
    set_fields: list[str],
    dimension_fields: list[str],
    measure_fields: list[str],
    view_name: str
) -> None:
    """Verify that a dimensions_only set contains all dimensions and no measures.

    Args:
        set_fields: List of field names in the set
        dimension_fields: List of expected dimension field names
        measure_fields: List of measure field names (should NOT be in set)
        view_name: Name of the view (for error messages)

    Raises:
        AssertionError: If validation fails
    """
    # Verify all dimensions are present
    for dim_field in dimension_fields:
        assert dim_field in set_fields, \
            f"Dimension {dim_field} missing from {view_name}.dimensions_only set"

    # Verify no measures are present
    for measure_field in measure_fields:
        assert measure_field not in set_fields, \
            f"Measure {measure_field} should NOT be in {view_name}.dimensions_only set"

    # Verify set doesn't contain unexpected fields
    for field in set_fields:
        assert field in dimension_fields, \
            f"Unexpected field {field} in {view_name}.dimensions_only set"
```

### 4.2 Comprehensive Validation Test

```python
def test_comprehensive_field_exposure_validation(
    self, semantic_models_dir: Path
) -> None:
    """Comprehensive test validating entire field exposure control system.

    This test validates:
    1. All views have dimensions_only sets
    2. Sets contain all dimensions (including hidden entities)
    3. Sets exclude all measures
    4. All joins reference the correct sets
    5. Multi-hop joins maintain constraints
    """
    parser = DbtParser()
    generator = LookMLGenerator()

    all_models = parser.parse_directory(semantic_models_dir)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            all_models, output_dir
        )

        assert len(validation_errors) == 0

        # Phase 1: Validate all views have correct sets
        view_sets = {}  # Track set contents for join validation

        view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]
        for view_file in view_files:
            content = view_file.read_text()
            parsed = lkml.load(content)
            view = parsed['views'][0]
            view_name = view['name']

            # Verify set exists
            sets = view.get('sets', [])
            assert len(sets) == 1, f"View {view_name} should have exactly 1 set"

            dimensions_only_set = sets[0]
            assert dimensions_only_set['name'] == 'dimensions_only'

            # Extract fields
            dimension_fields, measure_fields = _extract_dimension_fields_from_view(view)
            set_fields = dimensions_only_set['fields']

            # Validate set contents
            _verify_set_contains_only_dimensions(
                set_fields, dimension_fields, measure_fields, view_name
            )

            # Track for join validation
            view_sets[view_name] = set_fields

        # Phase 2: Validate explore joins reference correct sets
        explores_file = output_dir / "explores.lkml"
        explores_content = explores_file.read_text()
        parsed_explores = lkml.load(explores_content)

        for explore in parsed_explores.get('explores', []):
            joins = explore.get('joins', [])

            for join in joins:
                join_name = join['name']

                # Verify fields parameter exists
                assert 'fields' in join, \
                    f"Join {join_name} missing fields parameter in explore {explore['name']}"

                # Verify correct format
                fields_value = join['fields']
                expected_field = f"{join_name}.dimensions_only*"
                assert fields_value == [expected_field], \
                    f"Join {join_name} should have fields: [{expected_field}], got {fields_value}"

                # Verify referenced view exists and has the set
                assert join_name in view_sets, \
                    f"Join references {join_name} but that view was not generated"
```

---

## 5. Multi-hop Join Test Scenarios

### 5.1 Test Scenario: Two-level Join Chain

**Scenario**: `rental_orders` (fact) → `users` (dim) and `rental_orders` → `searches` (dim)

**Test implementation** (in `test_join_field_exposure.py`):

```python
def test_two_level_join_chain_field_constraints(
    self, semantic_models_dir: Path
) -> None:
    """Test field constraints in two-level join chain.

    Graph:
        rental_orders (fact)
        ├── users (dim via user_sk)
        └── searches (dim via search_sk)

    Verification:
    - rental_orders explore has 2 joins
    - Each join has fields parameter
    - Fields reference correct view's dimensions_only set
    """
    parser = DbtParser()
    generator = LookMLGenerator()

    all_models = parser.parse_directory(semantic_models_dir)

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            all_models, output_dir
        )

        assert len(validation_errors) == 0

        explores_file = output_dir / "explores.lkml"
        explores_content = explores_file.read_text()
        parsed = lkml.load(explores_content)

        # Find rental_orders explore
        rental_explore = next(
            (e for e in parsed['explores'] if e['name'] == 'rental_orders'),
            None
        )
        assert rental_explore is not None

        joins = rental_explore.get('joins', [])
        join_names = {j['name'] for j in joins}

        # Verify expected joins
        assert 'users' in join_names, "Expected users join"
        assert 'searches' in join_names, "Expected searches join"

        # Verify each join has correct fields parameter
        for join in joins:
            join_name = join['name']
            assert 'fields' in join
            assert join['fields'] == [f"{join_name}.dimensions_only*"]

            # Verify relationship is correct (many_to_one for FK → PK)
            assert join['relationship'] == 'many_to_one'

            # Verify sql_on clause references correct entities
            sql_on = join['sql_on']
            assert f"${{rental_orders." in sql_on
            assert f"${{" + join_name + "." in sql_on
```

### 5.2 Test Scenario: Three-level Join Chain (Future)

**Note**: This scenario would require a fourth semantic model (e.g., `sessions`) with `search_sk` as a foreign key. Not implemented in initial fixtures but documented for future extension.

**Potential scenario**:
```
rental_orders → searches → sessions
```

**Test structure** (skeleton for future implementation):

```python
@pytest.mark.skip(reason="Requires sessions semantic model fixture")
def test_three_level_join_chain_field_constraints(
    self, semantic_models_dir: Path
) -> None:
    """Test field constraints in three-level join chain.

    Graph:
        rental_orders (fact)
        └── searches (dim via search_sk)
            └── sessions (dim via session_sk)

    This test would verify:
    - Multi-hop join relationships are discovered
    - Each level maintains field constraints
    - Transitive relationships are handled correctly
    """
    # Implementation would follow similar pattern to two-level test
    # but with additional session dimension join verification
    pass
```

---

## 6. Expected LookML Output Structure

### 6.1 Expected View Structure (`expected_users.view.lkml`)

**Key structural elements**:

```lookml
view: users {
  sql_table_name: dim_renter ;;

  # Field set for dimension-only exposure in joins
  set: dimensions_only {
    fields: [
      user_sk,              # Hidden primary entity (needed for joins)
      user_id,              # Regular dimensions
      email_domain,
      account_status,
      signup_source,
      created_date_date,    # Time dimension fields
      created_date_week,
      created_date_month,
      created_date_quarter,
      created_date_year
    ]
  }

  # Entities (all hidden)
  dimension: user_sk {
    primary_key: yes
    hidden: yes
    type: string
    sql: ${TABLE}.user_sk ;;
    description: "Primary surrogate key for users"
  }

  # Regular dimensions
  dimension: user_id {
    type: string
    sql: ${TABLE}.user_id ;;
    description: "Natural user identifier"
  }

  dimension: email_domain {
    type: string
    sql: SPLIT_PART(email, '@', 2) ;;
    description: "Email domain for user segmentation"
  }

  # Time dimensions
  dimension_group: created_date {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
    description: "Date when user account was created"
  }

  # Measures (NOT in dimensions_only set)
  measure: user_count {
    type: count
    description: "Total number of users"
  }

  measure: active_users {
    type: count_distinct
    sql: CASE WHEN status = 'active' THEN user_id END ;;
    description: "Count of active users"
  }
}
```

**Validation points**:
- `set: dimensions_only` appears after `sql_table_name` but before dimensions
- Set contains 9 fields (1 entity + 5 categorical dims + 3 time fields from created_date)
- Hidden entity (`user_sk`) is in the set
- Measures (`user_count`, `active_users`) are NOT in the set

### 6.2 Expected Explores Structure (`expected_explores.lkml`)

**Key structural elements**:

```lookml
include: "*.view.lkml"

explore: rental_orders {
  from: rental_orders
  description: "Rental transaction fact table"

  join: users {
    type: left_outer
    sql_on: ${rental_orders.user_sk} = ${users.user_sk} ;;
    relationship: many_to_one
    fields: [users.dimensions_only*]
  }

  join: searches {
    type: left_outer
    sql_on: ${rental_orders.search_sk} = ${searches.search_sk} ;;
    relationship: many_to_one
    fields: [searches.dimensions_only*]
  }
}

explore: users {
  from: users
  description: "User dimension table with renter profile data"
}

explore: searches {
  from: searches
  description: "Search dimension table for search analytics"
}
```

**Validation points**:
- `include: "*.view.lkml"` at top
- 3 explores total (1 fact with joins, 2 standalone dimensions)
- `rental_orders` explore has 2 joins
- Each join has `fields: [view_name.dimensions_only*]`
- `fields` parameter appears after `relationship`

### 6.3 File Structure Summary

**Expected golden files** (4 total):

```
src/tests/golden/
├── expected_users.view.lkml         (~80-100 lines)
├── expected_searches.view.lkml      (~70-90 lines)
├── expected_rental_orders.view.lkml (~70-90 lines)
└── expected_explores.lkml           (~40-50 lines)
```

**Total line count**: ~260-330 lines across all golden files

---

## 7. Test Coverage Requirements

### 7.1 Golden Test Coverage

**File**: `src/tests/test_golden.py`

**New tests to add**:

1. `test_view_field_sets_match_golden()` - Verify generated views have correct sets
2. `test_explore_join_fields_match_golden()` - Verify joins have correct fields parameter
3. `test_searches_view_matches_golden()` - Add golden test for searches view
4. `test_rental_orders_view_matches_golden()` - Add golden test for rental_orders view

**Existing tests to update**:

- `test_generate_users_view_matches_golden()` - Update to use new users.yml fixture
- `test_generate_all_explores_matches_golden()` - Update to validate fields in joins

**Coverage metrics**:
- All 3 semantic model fixtures must be tested
- All 4 golden files must be validated
- Both view sets and explore joins must be verified

### 7.2 Integration Test Coverage

**File**: `src/tests/integration/test_join_field_exposure.py` (NEW)

**Tests**:
- 4 core tests (single join, multi-hop, dimension-only, hidden entity)
- 1 comprehensive validation test
- 1 two-level join chain test
- 1 skipped three-level test (for future)

**Total**: 7 test methods (6 active, 1 skipped)

**File**: `src/tests/integration/test_end_to_end.py` (UPDATED)

**New tests**:
- `test_generated_views_contain_field_sets()` - Verify all views have sets
- `test_generated_explores_have_join_field_constraints()` - Verify all joins have fields

**Total new**: 2 test methods

### 7.3 Coverage Target

**Branch coverage goal**: 95%+

**Lines to cover**:
- `LookMLGenerator._generate_dimension_set()` (new method from DTL-003)
- `LookMLGenerator._build_join_graph()` field parameter addition (from DTL-004)
- `LookMLView.to_lookml_dict()` set serialization (from DTL-002)

**Validation**:
```bash
pytest src/tests/test_golden.py src/tests/integration/test_join_field_exposure.py \
  --cov=src/dbt_to_lookml \
  --cov-report=term-missing \
  --cov-report=html
```

Expected result: Coverage ≥ 95% for `schemas.py`, `generators/lookml.py`

---

## 8. Implementation Checklist

### 8.1 Phase 1: Test Fixtures (30 min)

- [ ] Create `src/semantic_models/sem_users.yml` (10 min)
- [ ] Create `src/semantic_models/sem_searches.yml` (10 min)
- [ ] Create `src/semantic_models/sem_rental_orders.yml` (10 min)
- [ ] Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('src/semantic_models/sem_users.yml'))"`

### 8.2 Phase 2: Golden File Generation (20 min)

- [ ] Verify DTL-002, DTL-003, DTL-004 are complete and merged
- [ ] Run generator to create baseline: `uv run python -m dbt_to_lookml generate -i src/semantic_models -o src/tests/golden/temp_output --validate`
- [ ] Manual validation of generated files (check for sets, fields parameters)
- [ ] Copy to golden directory with `expected_` prefix
- [ ] Clean up temp directory
- [ ] Verify golden files with quick test run

### 8.3 Phase 3: Integration Tests (60 min)

- [ ] Create `src/tests/integration/test_join_field_exposure.py` (30 min)
  - [ ] Add test class and fixture
  - [ ] Implement `test_single_join_has_field_constraint()`
  - [ ] Implement `test_multi_hop_joins_have_field_constraints()`
  - [ ] Implement `test_join_fields_exclude_measures()`
  - [ ] Implement `test_hidden_entities_included_in_dimension_sets()`
- [ ] Add helper functions for field extraction and validation (15 min)
- [ ] Implement comprehensive validation test (15 min)

### 8.4 Phase 4: Golden Test Updates (45 min)

- [ ] Update `test_golden.py` imports and fixtures (5 min)
- [ ] Add `test_searches_view_matches_golden()` (10 min)
- [ ] Add `test_rental_orders_view_matches_golden()` (10 min)
- [ ] Update `test_generate_users_view_matches_golden()` for new fixture (10 min)
- [ ] Add field set validation tests (10 min)

### 8.5 Phase 5: End-to-End Test Updates (30 min)

- [ ] Add `test_generated_views_contain_field_sets()` to `test_end_to_end.py` (15 min)
- [ ] Add `test_generated_explores_have_join_field_constraints()` (15 min)

### 8.6 Phase 6: Validation and Cleanup (45 min)

- [ ] Run full test suite: `make test-full` (10 min)
- [ ] Run golden tests specifically: `pytest src/tests/test_golden.py -v` (5 min)
- [ ] Run integration tests: `pytest src/tests/integration/ -v` (5 min)
- [ ] Check coverage: `make test-coverage` (verify ≥95%) (10 min)
- [ ] Fix any test failures (10 min)
- [ ] Review diffs in golden files: `git diff src/tests/golden/` (5 min)

### 8.7 Phase 7: Documentation (15 min)

- [ ] Add docstring to `regenerate_golden_files_for_field_sets()` helper
- [ ] Update test README if exists (or create docstring in test files)
- [ ] Document multi-hop test scenarios in test docstrings
- [ ] Add comments explaining field exposure validation strategy

---

## 9. Testing Commands

### 9.1 Development Testing

```bash
# Test single file
pytest src/tests/integration/test_join_field_exposure.py -v

# Test single method
pytest src/tests/integration/test_join_field_exposure.py::TestJoinFieldExposure::test_single_join_has_field_constraint -xvs

# Test golden files only
pytest src/tests/test_golden.py -v

# Test with coverage
pytest src/tests/test_golden.py src/tests/integration/test_join_field_exposure.py \
  --cov=src/dbt_to_lookml \
  --cov-report=term-missing

# Regenerate golden files (manual helper)
pytest src/tests/test_golden.py::TestGoldenFiles::regenerate_golden_files_for_field_sets -v -s
```

### 9.2 CI/CD Testing

```bash
# Full test suite
make test-full

# Golden tests marker
pytest -m golden -v

# Integration tests marker
pytest -m integration -v

# Coverage report
make test-coverage
```

### 9.3 Validation Commands

```bash
# Validate YAML fixtures
find src/semantic_models -name "*.yml" -exec python -c "import yaml; yaml.safe_load(open('{}'))" \;

# Validate LookML golden files
find src/tests/golden -name "*.lkml" -exec python -c "import lkml; lkml.load(open('{}').read())" \;

# Check for required golden files
ls -lh src/tests/golden/expected_*.lkml

# Diff golden files after regeneration
git diff src/tests/golden/
```

---

## 10. Success Criteria

### 10.1 Functional Requirements

- [ ] All 3 semantic model fixtures created and parse successfully
- [ ] All 4 golden files generated and contain expected structure:
  - [ ] `expected_users.view.lkml` has `set: dimensions_only` with 9 fields
  - [ ] `expected_searches.view.lkml` has `set: dimensions_only` with 8 fields
  - [ ] `expected_rental_orders.view.lkml` has `set: dimensions_only` with 6 fields
  - [ ] `expected_explores.lkml` has 2 joins with `fields:` parameters
- [ ] All golden tests pass without modification to generated output
- [ ] All integration tests pass and verify field exposure control

### 10.2 Test Quality Requirements

- [ ] Golden tests validate both structure and content
- [ ] Integration tests cover single join, multi-hop, and edge cases
- [ ] Helper functions extract and validate field sets correctly
- [ ] Test isolation maintained (no test dependencies)
- [ ] Tests use fixtures consistently

### 10.3 Coverage Requirements

- [ ] Branch coverage ≥ 95% for affected modules
- [ ] All new generator methods covered (field set generation, join field parameters)
- [ ] All LookML schema changes covered (set serialization)
- [ ] No regressions in existing test coverage

### 10.4 Documentation Requirements

- [ ] Golden file regeneration process documented in helper method
- [ ] Test scenarios documented in docstrings
- [ ] Multi-hop join behavior explained in tests
- [ ] Field exposure validation strategy documented

---

## 11. Risk Mitigation

### 11.1 Dependency Risks

**Risk**: DTL-002/003/004 not complete when implementing tests
**Mitigation**:
- Check implementation status before starting
- Run unit tests for those issues to verify completion
- Skip integration tests temporarily if dependencies not ready

### 11.2 Golden File Risks

**Risk**: Generated output doesn't match expected structure
**Mitigation**:
- Manual validation before copying to golden directory
- Use lkml library to parse and verify syntax
- Run tests immediately after copying golden files
- Maintain temp_output for comparison if tests fail

### 11.3 Test Isolation Risks

**Risk**: Tests depend on external semantic models or state
**Mitigation**:
- Use fixtures in `src/semantic_models/` (checked into repo)
- Always use `TemporaryDirectory()` for test output
- Don't rely on hardcoded paths to external repositories
- Clean up test artifacts in teardown

### 11.4 Multi-hop Join Discovery Risks

**Risk**: Generator doesn't discover multi-hop joins correctly
**Mitigation**:
- Verify DTL-004 implementation includes multi-hop logic
- Test with simplified two-level scenario first
- Add debug logging in tests to inspect join graph
- Document expected join relationships in test docstrings

---

## 12. Approval Checklist

Before marking DTL-006 as "ready for implementation":

- [ ] Strategy document reviewed and approved
- [ ] DTL-002 status = "completed" (LookML set schema support)
- [ ] DTL-003 status = "completed" (field set generation)
- [ ] DTL-004 status = "completed" (join field constraints)
- [ ] DTL-005 status = "completed" (unit tests updated) - RECOMMENDED
- [ ] Semantic model fixture designs reviewed
- [ ] Golden file regeneration process validated
- [ ] Test coverage plan approved
- [ ] Estimated complexity confirmed (3.5-4.5 hours)

---

## 13. Definition of Done

- [ ] All 3 semantic model fixtures created in `src/semantic_models/`
- [ ] All 4 golden files generated in `src/tests/golden/`
- [ ] `test_join_field_exposure.py` created with 6 passing tests
- [ ] `test_golden.py` updated with field set validation tests
- [ ] `test_end_to_end.py` updated with 2 new tests
- [ ] `make test-full` passes with no regressions
- [ ] Coverage report shows ≥95% branch coverage
- [ ] All validation errors = 0 in golden file generation
- [ ] Git diff reviewed for golden files (expected changes only)
- [ ] Issue DTL-006 status = "ready" with "state:has-spec" label
- [ ] Spec document committed to `.tasks/specs/DTL-006-spec.md`

---

**Spec completed**: 2025-11-12
**Ready for implementation**: After DTL-002, DTL-003, DTL-004 completion
**Estimated implementation time**: 3.5-4.5 hours

# LookML View Label & Group Label Comparison

**Date**: 2026-01-06
**Purpose**: Identify differences between legacy LookML views and new generated views to align field organization

## Directories Compared

- **Old (Legacy)**: `/Users/doug/Work/data-modelling/analytics_lookML/GoldLayer/`
- **New (Generated)**: `/Users/doug/Work/data-modelling/official-models/redshift_gold/lookml_output/semantic-patterns`

---

## Global Patterns (Consistent Across All Domains)

### 1. View Labels on Dimensions ❌ MISSING IN NEW
- **Old**: Dimensions organized into view_labels: `"Identifiers"`, `"Reservation"`, `"Customer Feedback"`, `"Status History"`, `" Date Dimensions"` (with leading space for sorting)
- **New**: **NO view_labels** - all dimensions appear in the default view

### 2. Hierarchical Group Labels on Dimensions ❌ SIMPLIFIED IN NEW
- **Old**: Fine-grained group_labels within each view_label
- **New**: Single-level group_labels only

### 3. View Labels on Measures ❌ MISSING IN NEW
- **Old**: All visible measures have `view_label: "  Metrics"` or `"  Renter"` (with leading spaces for top sorting)
- **New**: **NO view_labels** on measures

### 4. Descriptive Group Labels on Measures ❌ GENERIC IN NEW
- **Old**: Domain-specific, meaningful group_labels
- **New**: Generic `"Metrics"` for almost everything

---

## Domain-Specific Differences

### RENTALS (gold_rentals → sp_rentals)

#### Dimensions - View Labels

| Old View Label | Fields in Old | New Behavior |
|----------------|---------------|--------------|
| `"Identifiers"` | rental_id, facility_id, renter_id, etc. | ❌ No view_label |
| `"Reservation"` | reservation_status, payment_status, segments, etc. | ❌ No view_label |
| `" Date Dimensions"` | created_at, starts_at, ends_at (date fields) | ❌ No view_label |

#### Dimensions - Group Labels Lost

**Within Identifiers view_label**, old had:
- `"Rental"` - rental_id
- `"Subscription"` - rental_recurrence_id, monthly_subscription_id
- `"Facility"` - facility_id, canonical_facility_id
- `"Customer"` - renter_id, profile_id
- `"Event"` - event_id
- `"Partner"` - affiliate_id, partner_id
- `"Pricing"` - rule_id
- `"User Journey"` - search_id, action_id

**New**: All just grouped as `"Identifiers"` (no sub-categorization)

**Within Reservation view_label**, old had:
- `"Status"` - reservation_status, payment_status, transaction_type
- `"Segment"` - is_monthly_rental, rental_segment_rollup, rental_segment
- `"Customer Type"` - is_first_completed_rental, is_guest_rental
- `"Temporal Pattern"` - temporal_segment
- `"Duration"` - rental_length_minutes
- `"Payment"` - payment_type
- `"Channel"` - rental_source, rental_source_application, source_device_category

**New**: All just grouped as `"Reservation"` (no sub-categorization)

#### Measures - Group Labels Lost

| Old Group Label | Measures | New Group Label |
|-----------------|----------|-----------------|
| `"Revenue"` | gov, gmv, aov, amv, gmv_per_facility, gov_per_location, etc. | `"Metrics"` |
| `"Rental"` | rental_count | `"Metrics"` |
| `"Renters"` | renter_count | `"Renter"` |
| `"Facility"` | transacting_facility_count, canonical_parking_spot_count | `"Metrics"` |
| `"Duration"` | rental_hours, average_rental_hours, lead_time_hours | `"Metrics"` |

#### Specific Dimension Changes

**Date dimensions**: Old used simple `dimension: created_at` with `type: date`, New uses `dimension_group: created_at` with multiple timeframes.

---

### REVIEWS (gold_reviews → sp_reviews)

#### Dimensions - View Labels

| Old View Label | Fields in Old | New Behavior |
|----------------|---------------|--------------|
| `"Identifiers"` | facility_id | ❌ No view_label |
| `"Customer Feedback"` | star_rating, review_status, feedback flags, concerns | ❌ No view_label |

#### Dimensions - Group Labels Lost

**Within Customer Feedback view_label**, old had:
- `"Rating"` - star_rating
- `"Status"` - review_status
- `"Device"` - review_device_source
- `"Sentiment"` - has_positive_feedback, has_negative_feedback
- `"Concerns"` - has_safety_concern, has_value_concern, has_cleanliness_concern, has_navigation_concern, has_service_concern, has_operations_concern
- `"Comments"` - redacted_review_comments

**New**: All just grouped as `"Customer Feedback"` (no sub-categorization)

#### Measures - Group Labels

| Old Group Label | New Group Label |
|-----------------|-----------------|
| `"Ratings And Reviews"` | `"Metrics"` |

---

### FACILITY_MONTHLY_STATUS (gold_facility_monthly_status → sp_facility_monthly_status)

#### Dimensions - View Labels

| Old View Label | Fields in Old | New Behavior |
|----------------|---------------|--------------|
| `"Status History"` | canonical_is_on, is_canonical_gained, is_canonical_lost | ❌ No view_label |
| `"Identifiers"` | canonical_facility_id | ❌ No view_label |

#### Dimensions - Group Labels Lost

**Within Status History view_label**, old had:
- `"Status"` - canonical_is_on
- `"Transition"` - is_canonical_gained, is_canonical_lost

**New**: All just grouped as `"Status History"` (no sub-categorization)

#### Measures - Group Labels

| Old Group Label | New Group Label |
|-----------------|-----------------|
| `"Location Counts"` | `"Metrics"` |
| `"Location Flow"` | `"Metrics"` |

---

### FACILITY_LIFECYCLE (gold_facility_lifecycle → sp_facility_lifecycle)

#### Dimensions - View Labels

| Old View Label | Fields in Old | New Behavior |
|----------------|---------------|--------------|
| `"Status History"` | All status/transition dimensions | ❌ No view_label |
| `"Identifiers"` | facility_id, canonical_facility_id | ❌ No view_label |
| `" Date Dimensions"` | valid_from, valid_to, calendar dates | ❌ No view_label |

#### Dimensions - Group Labels Lost

**Within Status History view_label**, old had:
- `"Status"` - is_on, is_active, is_on_and_active, facility_status, activity_state
- `"Transition"` - is_current, days_in_state, transition_type, is_status_gained, is_status_lost
- `"History"` - days_off_before_gain, days_on_before_loss, gain_sequence, loss_sequence, days_since_last_gain, days_since_last_loss

**New**: All just grouped as `"Status History"` (no sub-categorization)

#### Measures - Group Labels

| Old Group Label | New Group Label |
|-----------------|-----------------|
| `"Location Counts"` | `"Metrics"` |

---

## What Needs to Be Updated

To align the new generated LookML with the old structure, the generator needs the following modifications:

### 1. Add view_label to dimensions
**File**: `semantic_patterns/adapters/lookml/renderers/view.py`

Dimensions should be categorized into view_labels based on their semantic purpose:
- Use leading spaces for `" Date Dimensions"` and `"  Metrics"` for sorting to top/bottom

### 2. Add hierarchical group_labels to dimensions
Not just single-level grouping, but sub-categorization within each view_label:

**Identifiers view_label** should have sub-groups:
- Rental, Subscription, Facility, Customer, Event, Partner, Pricing, User Journey

**Reservation view_label** should have sub-groups:
- Status, Segment, Customer Type, Temporal Pattern, Duration, Payment, Channel

**Customer Feedback view_label** should have sub-groups:
- Rating, Status, Device, Sentiment, Concerns, Comments

**Status History view_label** should have sub-groups:
- Status, Transition, History

### 3. Add view_label to measures
**File**: `semantic_patterns/adapters/lookml/renderers/view.py` or metrics renderer

Measures should have `view_label: "  Metrics"` or `"  Renter"` (with leading spaces for sorting)

### 4. Add domain-specific group_labels to measures
Replace generic "Metrics" with meaningful categories:
- **For rentals**: Revenue, Rental, Renters, Facility, Duration
- **For reviews**: Ratings And Reviews
- **For facility domains**: Location Counts, Location Flow

---

## Implementation Notes

The current generator appears to:
1. Set group_label on dimensions from the YAML metadata
2. Use a generic "Metrics" group_label for all measures
3. **Not set view_label at all** on dimensions or measures

The legacy views use a sophisticated two-level organization:
- **Level 1**: view_label (organizes fields into major categories)
- **Level 2**: group_label (organizes fields within each view_label)

This creates a user-friendly hierarchical navigation in Looker's field picker.

---

## Additional Observations

1. **Calendar/Date handling**: Old views extend `gold_base_calendar` for date dimension utilities, new views use native `dimension_group` with timeframes
2. **Hidden measures**: New views have many measures marked `hidden: yes` in the base view, made visible in the `.metrics.view.lkml` refinement
3. **Measure view_label placement**: Old views use `view_label: "  Metrics"` (2 spaces) for primary sort to top
4. **Entity keys**: Both old and new properly hide join keys (rental, facility, canonical_facility, etc.)

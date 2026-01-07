"""Tests for dbt semantic model ingestion."""

from pathlib import Path

from semantic_patterns.ingestion import DomainBuilder
from semantic_patterns.ingestion.dbt import (
    DbtLoader,
    DbtMapper,
    map_dimension,
    map_entity,
    map_measure,
    map_metric,
    map_semantic_model,
    parse_jinja_filter,
)

DBT_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "dbt"


class TestJinjaFilterParsing:
    """Tests for parse_jinja_filter function."""

    def test_parse_equals_filter(self) -> None:
        """Test parsing equals filter."""
        result = parse_jinja_filter(
            "{{ Dimension('rental__transaction_type') }} = 'completed'"
        )
        assert result == {"transaction_type": "completed"}

    def test_parse_not_equals_filter(self) -> None:
        """Test parsing not equals filter."""
        result = parse_jinja_filter("{{ Dimension('rental__status') }} != 'cancelled'")
        assert result == {"status": "!=cancelled"}

    def test_parse_greater_than_filter(self) -> None:
        """Test parsing greater than filter."""
        result = parse_jinja_filter("{{ Dimension('rental__amount') }} > 100")
        assert result == {"amount": ">100"}

    def test_parse_greater_than_or_equals_filter(self) -> None:
        """Test parsing greater than or equals filter."""
        result = parse_jinja_filter("{{ Dimension('rental__count') }} >= 5")
        assert result == {"count": ">=5"}

    def test_parse_less_than_filter(self) -> None:
        """Test parsing less than filter."""
        result = parse_jinja_filter("{{ Dimension('rental__days') }} < 30")
        assert result == {"days": "<30"}

    def test_parse_in_filter(self) -> None:
        """Test parsing IN filter."""
        result = parse_jinja_filter(
            "{{ Dimension('rental__segment') }} IN ('Monthly', 'Event')"
        )
        assert result == {"segment": ["Monthly", "Event"]}

    def test_parse_filter_with_double_quotes(self) -> None:
        """Test parsing filter with double quotes."""
        result = parse_jinja_filter(
            '{{ Dimension("rental__transaction_type") }} = "completed"'
        )
        assert result == {"transaction_type": "completed"}

    def test_parse_invalid_filter(self) -> None:
        """Test parsing invalid filter returns empty dict."""
        result = parse_jinja_filter("invalid filter")
        assert result == {}


class TestMapDimension:
    """Tests for map_dimension function."""

    def test_map_categorical_dimension(self) -> None:
        """Test mapping a categorical dimension."""
        dbt_dim = {
            "name": "transaction_type",
            "label": "Order Status",
            "type": "categorical",
            "expr": "rental_event_type",
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "group": "Status",
                    }
                }
            },
        }
        result = map_dimension(dbt_dim)

        assert result["name"] == "transaction_type"
        assert result["label"] == "Order Status"
        assert result["type"] == "categorical"
        assert result["expr"] == "rental_event_type"
        assert result["group"] == "Status"

    def test_map_time_dimension(self) -> None:
        """Test mapping a time dimension with granularity."""
        dbt_dim = {
            "name": "created_at",
            "label": "Rental Created",
            "type": "time",
            "type_params": {
                "time_granularity": "day",
            },
            "expr": "rental_created_at_utc",
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "group": "Dates",
                        "date_selector": True,
                    }
                }
            },
        }
        result = map_dimension(dbt_dim)

        assert result["name"] == "created_at"
        assert result["type"] == "time"
        assert result["granularity"] == "day"
        assert result["group"] == "Dates"

    def test_map_hidden_dimension(self) -> None:
        """Test mapping a hidden dimension."""
        dbt_dim = {
            "name": "internal_id",
            "type": "categorical",
            "expr": "internal_id",
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "hidden": True,
                    }
                }
            },
        }
        result = map_dimension(dbt_dim)

        assert result["hidden"] is True

    def test_map_dimension_with_legacy_subject_category(self) -> None:
        """Test mapping dimension with legacy subject + category -> group dot notation."""
        dbt_dim = {
            "name": "star_rating",
            "label": "Star Rating",
            "type": "categorical",
            "expr": "star_rating",
            "config": {
                "meta": {
                    "subject": "Customer Feedback",
                    "category": "Rating",
                    "bi_field": True,
                }
            },
        }
        result = map_dimension(dbt_dim)

        assert result["name"] == "star_rating"
        # subject + category should be combined with dot notation
        assert result["group"] == "Customer Feedback.Rating"

    def test_map_dimension_with_subject_only(self) -> None:
        """Test mapping dimension with only subject (no category)."""
        dbt_dim = {
            "name": "created_at",
            "type": "time",
            "type_params": {"time_granularity": "day"},
            "expr": "created_at_utc",
            "config": {
                "meta": {
                    "subject": "Date Dimensions",
                    "bi_field": True,
                }
            },
        }
        result = map_dimension(dbt_dim)

        # subject alone should become group
        assert result["group"] == "Date Dimensions"

    def test_map_dimension_with_group_category(self) -> None:
        """Test mapping dimension with group + category (new convention)."""
        dbt_dim = {
            "name": "month_end_date",
            "label": "Month End Date",
            "type": "time",
            "type_params": {"time_granularity": "day"},
            "expr": "month_end_date",
            "config": {
                "meta": {
                    "group": "Date Dimensions",
                    "category": "Month End",
                    "bi_field": True,
                }
            },
        }
        result = map_dimension(dbt_dim)

        # group + category should be combined with dot notation
        assert result["group"] == "Date Dimensions.Month End"


class TestMapMeasure:
    """Tests for map_measure function."""

    def test_map_sum_measure(self) -> None:
        """Test mapping a sum measure."""
        dbt_measure = {
            "name": "checkout_amount",
            "label": "Checkout Amount",
            "agg": "sum",
            "expr": "rental_checkout_amount_local",
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "group": "Revenue",
                        "format": "usd",
                        "hidden": True,
                    }
                }
            },
        }
        result = map_measure(dbt_measure)

        assert result["name"] == "checkout_amount"
        assert result["label"] == "Checkout Amount"
        assert result["agg"] == "sum"
        assert result["expr"] == "rental_checkout_amount_local"
        assert result["group"] == "Revenue"
        assert result["format"] == "usd"
        assert result["hidden"] is True

    def test_map_count_distinct_measure(self) -> None:
        """Test mapping a count_distinct measure."""
        dbt_measure = {
            "name": "rental_count",
            "agg": "count_distinct",
            "expr": "unique_rental_sk",
        }
        result = map_measure(dbt_measure)

        assert result["name"] == "rental_count"
        assert result["agg"] == "count_distinct"
        assert result["expr"] == "unique_rental_sk"


class TestMapEntity:
    """Tests for map_entity function."""

    def test_map_primary_entity(self) -> None:
        """Test mapping a primary entity."""
        dbt_entity = {
            "name": "rental",
            "type": "primary",
            "expr": "unique_rental_sk",
            "label": "Reservation",
        }
        result = map_entity(dbt_entity)

        assert result["name"] == "rental"
        assert result["type"] == "primary"
        assert result["expr"] == "unique_rental_sk"
        assert result["label"] == "Reservation"

    def test_map_foreign_entity(self) -> None:
        """Test mapping a foreign entity."""
        dbt_entity = {
            "name": "facility",
            "type": "foreign",
            "expr": "facility_sk",
        }
        result = map_entity(dbt_entity)

        assert result["name"] == "facility"
        assert result["type"] == "foreign"
        assert result["expr"] == "facility_sk"

    def test_map_entity_with_complete(self) -> None:
        """Test mapping an entity with complete flag."""
        dbt_entity = {
            "name": "rental",
            "type": "foreign",
            "expr": "rental_sk",
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "complete": True,
                    }
                }
            },
        }
        result = map_entity(dbt_entity)

        assert result["complete"] is True


class TestMapMetric:
    """Tests for map_metric function."""

    def test_map_simple_metric(self) -> None:
        """Test mapping a simple metric."""
        dbt_metric = {
            "name": "gov",
            "label": "Gross Order Value (GOV)",
            "type": "simple",
            "type_params": {
                "measure": "checkout_amount",
            },
            "filter": [
                "{{ Dimension('rental__transaction_type') }} = 'completed'",
            ],
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "format": "usd",
                        "group": "Revenue",
                        "entity": "rental",
                        "pop": {
                            "comparisons": ["py", "pm"],
                            "outputs": ["previous", "pct_change"],
                        },
                    }
                }
            },
        }
        result = map_metric(dbt_metric)

        assert result["name"] == "gov"
        assert result["label"] == "Gross Order Value (GOV)"
        assert result["type"] == "simple"
        assert result["measure"] == "checkout_amount"
        assert result["filter"] == {"transaction_type": "completed"}
        assert result["format"] == "usd"
        assert result["group"] == "Revenue"
        assert result["entity"] == "rental"
        assert result["pop"]["comparisons"] == ["py", "pm"]

    def test_map_derived_metric(self) -> None:
        """Test mapping a derived metric."""
        dbt_metric = {
            "name": "aov",
            "label": "Average Order Value",
            "type": "derived",
            "type_params": {
                "expr": "gov / NULLIF(rental_count, 0)",
                "metrics": ["gov", "rental_count"],
            },
            "config": {
                "meta": {
                    "semantic_patterns": {
                        "format": "usd",
                        "entity": "rental",
                    }
                }
            },
        }
        result = map_metric(dbt_metric)

        assert result["name"] == "aov"
        assert result["type"] == "derived"
        assert result["expr"] == "gov / NULLIF(rental_count, 0)"
        assert result["metrics"] == ["gov", "rental_count"]
        assert result["entity"] == "rental"

    def test_map_derived_metric_with_dict_metrics(self) -> None:
        """Test mapping a derived metric where metrics are dicts with name keys."""
        dbt_metric = {
            "name": "aov",
            "type": "derived",
            "type_params": {
                "expr": "gov / NULLIF(rental_count, 0)",
                "metrics": [
                    {"name": "gov", "offset_window": 1},
                    {"name": "rental_count"},
                ],
            },
            "config": {"meta": {"semantic_patterns": {"entity": "rental"}}},
        }
        result = map_metric(dbt_metric)

        assert result["metrics"] == ["gov", "rental_count"]

    def test_map_metric_with_legacy_subject_category(self) -> None:
        """Test mapping a metric with legacy subject + category -> group dot notation."""
        dbt_metric = {
            "name": "total_parking_spot_count",
            "label": "Total Parking Spot Count",
            "type": "simple",
            "type_params": {
                "measure": "parking_spot_count",
            },
            "config": {
                "meta": {
                    "subject": "Facilities",
                    "category": "Counts",
                    "bi_field": True,
                    "primary_entity": "facility",
                    "format": "decimal_0",
                }
            },
        }
        result = map_metric(dbt_metric)

        assert result["name"] == "total_parking_spot_count"
        # subject + category should be combined with dot notation
        assert result["group"] == "Facilities.Counts"
        # primary_entity should map to entity
        assert result["entity"] == "facility"
        assert result["format"] == "decimal_0"


class TestMapSemanticModel:
    """Tests for map_semantic_model function."""

    def test_map_semantic_model(self) -> None:
        """Test mapping a complete semantic model."""
        dbt_model = {
            "name": "rentals",
            "description": "Core rental fact model",
            "model": "ref('rentals')",
            "defaults": {
                "agg_time_dimension": "created_at",
            },
            "entities": [
                {
                    "name": "rental",
                    "type": "primary",
                    "expr": "unique_rental_sk",
                },
            ],
            "dimensions": [
                {
                    "name": "created_at",
                    "type": "time",
                    "expr": "rental_created_at_utc",
                    "config": {
                        "meta": {
                            "semantic_patterns": {
                                "date_selector": True,
                            }
                        }
                    },
                },
                {
                    "name": "status",
                    "type": "categorical",
                    "expr": "status",
                },
            ],
            "measures": [
                {
                    "name": "checkout_amount",
                    "agg": "sum",
                    "expr": "amount",
                },
            ],
        }
        result = map_semantic_model(dbt_model)

        assert result["name"] == "rentals"
        assert result["description"] == "Core rental fact model"
        assert result["time_dimension"] == "created_at"
        assert len(result["entities"]) == 1
        assert len(result["dimensions"]) == 2
        assert len(result["measures"]) == 1
        assert result["date_selector"]["dimensions"] == ["created_at"]


class TestDbtLoader:
    """Tests for DbtLoader class."""

    def test_load_all(self) -> None:
        """Test loading all semantic models and metrics from directory."""
        loader = DbtLoader(DBT_FIXTURES_DIR)
        semantic_models, metrics = loader.load_all()

        assert len(semantic_models) == 1
        assert semantic_models[0]["name"] == "rentals"

        assert len(metrics) == 3
        metric_names = {m["name"] for m in metrics}
        assert metric_names == {"gov", "rental_count", "aov"}

    def test_loader_from_directory(self) -> None:
        """Test factory method."""
        loader = DbtLoader.from_directory(DBT_FIXTURES_DIR)
        semantic_models, _ = loader.load_all()
        assert len(semantic_models) == 1


class TestDbtMapper:
    """Tests for DbtMapper class."""

    def test_mapper_get_documents(self) -> None:
        """Test DbtMapper produces correct document format."""
        mapper = DbtMapper()
        mapper.add_semantic_models(
            [
                {
                    "name": "rentals",
                    "entities": [{"name": "rental", "type": "primary", "expr": "id"}],
                    "dimensions": [],
                    "measures": [],
                }
            ]
        )
        mapper.add_metrics(
            [
                {
                    "name": "gov",
                    "type": "simple",
                    "type_params": {"measure": "amount"},
                    "config": {"meta": {"semantic_patterns": {"entity": "rental"}}},
                }
            ]
        )

        docs = mapper.get_documents()
        assert len(docs) == 1
        assert len(docs[0]["semantic_models"]) == 1
        assert len(docs[0]["metrics"]) == 1


class TestEndToEnd:
    """End-to-end tests for dbt ingestion."""

    def test_dbt_to_domain_models(self) -> None:
        """Test full pipeline from dbt format to domain models."""
        # Load dbt files
        loader = DbtLoader(DBT_FIXTURES_DIR)
        semantic_models, metrics = loader.load_all()

        # Map to our format
        mapper = DbtMapper()
        mapper.add_semantic_models(semantic_models)
        mapper.add_metrics(metrics)
        documents = mapper.get_documents()

        # Build domain models
        builder = DomainBuilder()
        for doc in documents:
            builder._collect_from_document(doc)
        models = builder.build()

        # Verify results
        assert len(models) == 1
        rentals = models[0]

        assert rentals.name == "rentals"
        assert rentals.primary_entity is not None
        assert rentals.primary_entity.name == "rental"

        # Check dimensions
        dim_names = {d.name for d in rentals.dimensions}
        assert "created_at" in dim_names
        assert "transaction_type" in dim_names

        # Check measures
        measure_names = {m.name for m in rentals.measures}
        assert "checkout_amount" in measure_names
        assert "rental_count" in measure_names

        # Check metrics
        assert len(rentals.metrics) == 3
        metric_names = {m.name for m in rentals.metrics}
        assert metric_names == {"gov", "rental_count", "aov"}

        # Check date selector was built from date_selector: true dimensions
        assert rentals.date_selector is not None
        assert "created_at" in rentals.date_selector.dimensions
        assert "starts_at" in rentals.date_selector.dimensions

    def test_gov_metric_has_pop_and_filter(self) -> None:
        """Test that GOV metric has PoP config and filter parsed correctly."""
        loader = DbtLoader(DBT_FIXTURES_DIR)
        semantic_models, metrics = loader.load_all()

        mapper = DbtMapper()
        mapper.add_semantic_models(semantic_models)
        mapper.add_metrics(metrics)
        documents = mapper.get_documents()

        builder = DomainBuilder()
        for doc in documents:
            builder._collect_from_document(doc)
        models = builder.build()

        rentals = models[0]
        gov = rentals.get_metric("gov")

        assert gov is not None
        assert gov.has_pop
        assert gov.filter is not None
        assert len(gov.filter.conditions) == 1
        assert gov.filter.conditions[0].field == "transaction_type"
        assert gov.filter.conditions[0].value == "completed"

    def test_derived_metric_has_expression(self) -> None:
        """Test that derived metrics have expression parsed correctly."""
        loader = DbtLoader(DBT_FIXTURES_DIR)
        semantic_models, metrics = loader.load_all()

        mapper = DbtMapper()
        mapper.add_semantic_models(semantic_models)
        mapper.add_metrics(metrics)
        documents = mapper.get_documents()

        builder = DomainBuilder()
        for doc in documents:
            builder._collect_from_document(doc)
        models = builder.build()

        rentals = models[0]
        aov = rentals.get_metric("aov")

        assert aov is not None
        assert aov.type.value == "derived"
        assert aov.expr is not None
        assert "NULLIF" in aov.expr
        assert aov.metrics == ["gov", "rental_count"]

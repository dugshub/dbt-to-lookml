"""Unit tests for flat meta structure (subject, category) labeling."""

from dbt_to_lookml.schemas.config import Config, ConfigMeta
from dbt_to_lookml.schemas.semantic_layer import (
    Dimension,
    Entity,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.types import AggregationType, DimensionType


class TestFlatMetaLabeling:
    """Test cases for flat meta structure (subject, category) labeling."""

    def test_dimension_with_subject_and_category(self) -> None:
        """Test that dimensions get labels from flat meta structure."""
        config = Config(
            meta=ConfigMeta(subject="Rentals", category="Transaction Details")
        )

        dimension = Dimension(
            name="payment_status",
            type=DimensionType.CATEGORICAL,
            expr="rental_payment_status",
            config=config,
        )

        view_label, group_label = dimension.get_dimension_labels()
        assert view_label == "Rentals"
        assert group_label == "Transaction Details"

    def test_dimension_lookml_with_flat_meta(self) -> None:
        """Test dimension LookML output includes labels from flat meta.

        Time dimension view_label gets 1-space prefix for sort order positioning.
        """
        config = Config(meta=ConfigMeta(subject="Universal", category="Time Periods"))

        dimension = Dimension(
            name="created_date",
            type=DimensionType.TIME,
            expr="rental_created_date",
            description="Date the rental was created.",
            config=config,
        )

        lookml_dict = dimension.to_lookml_dict()
        # Time dimensions get 1-space prefix on view_label for sort order
        assert lookml_dict["view_label"] == " Universal"
        assert lookml_dict["group_label"] == "Time Periods"
        assert lookml_dict["name"] == "created_date"
        assert lookml_dict["type"] == "time"

    def test_measure_with_category(self) -> None:
        """Test that measures get labels with flat meta structure."""
        config = Config(meta=ConfigMeta(category="Revenue Metrics"))

        measure = Measure(
            name="total_revenue",
            agg=AggregationType.SUM,
            expr="rental_checkout_amount_local",
            config=config,
        )

        view_label, group_label = measure.get_measure_labels()
        # get_measure_labels returns raw value; to_lookml_dict adds the prefix
        assert view_label == "Metrics"
        assert group_label == "Revenue Metrics"

    def test_measure_without_meta_uses_model_name(self) -> None:
        """Test that measures without meta use model name for group_label."""
        measure = Measure(
            name="total_revenue",
            agg=AggregationType.SUM,
            expr="rental_checkout_amount_local",
        )

        view_label, group_label = measure.get_measure_labels(model_name="rentals")
        # get_measure_labels returns raw value; to_lookml_dict adds the prefix
        assert view_label == "Metrics"
        assert group_label == "Rentals Performance"

    def test_measure_lookml_with_flat_meta(self) -> None:
        """Test measure LookML output with flat meta structure."""
        config = Config(meta=ConfigMeta(category="Activity Metrics"))

        measure = Measure(
            name="rental_count",
            agg=AggregationType.COUNT_DISTINCT,
            expr="rental_id",
            description="Number of distinct rentals",
            config=config,
        )

        lookml_dict = measure.to_lookml_dict(model_name="rentals")
        assert lookml_dict["view_label"] == "  Metrics"
        assert lookml_dict["group_label"] == "Activity Metrics"
        assert lookml_dict["name"] == "rental_count_measure"

    def test_entity_in_fact_table_with_labels(self) -> None:
        """Test that primary entities in fact tables get labels and are hidden."""
        entity = Entity(
            name="rental",
            type="primary",
            expr="unique_rental_sk",
            description="Primary rental key",
        )

        lookml_dict = entity.to_lookml_dict(view_label="Rentals", is_fact_table=True)

        assert lookml_dict["primary_key"] == "yes"
        assert lookml_dict["view_label"] == "Rentals"
        assert lookml_dict["group_label"] == "Join Keys"
        assert lookml_dict["hidden"] == "yes"

    def test_entity_in_dimension_table_no_labels(self) -> None:
        """Test that primary entities in dimension tables don't get group_label but are hidden."""
        entity = Entity(
            name="facility",
            type="primary",
            expr="facility_sk",
            description="Primary facility key",
        )

        lookml_dict = entity.to_lookml_dict(
            view_label="Facilities", is_fact_table=False
        )

        assert lookml_dict["primary_key"] == "yes"
        assert "view_label" not in lookml_dict
        assert "group_label" not in lookml_dict
        assert lookml_dict["hidden"] == "yes"

    def test_semantic_model_with_flat_meta(self) -> None:
        """Test complete semantic model with flat meta structure."""
        model = SemanticModel(
            name="rentals",
            model="ref('fct_rental')",
            description="Core rental fact semantic model",
            entities=[Entity(name="rental", type="primary", expr="unique_rental_sk")],
            dimensions=[
                Dimension(
                    name="payment_status",
                    type=DimensionType.CATEGORICAL,
                    expr="rental_payment_status",
                    description="Rental payment status category.",
                    config=Config(
                        meta=ConfigMeta(
                            subject="Rentals", category="Transaction Details"
                        )
                    ),
                )
            ],
            measures=[
                Measure(
                    name="total_revenue",
                    agg=AggregationType.SUM,
                    expr="rental_checkout_amount_local",
                    description="Sum of rental checkout amounts.",
                )
            ],
        )

        lookml_dict = model.to_lookml_dict(schema="gold_production")

        # Check view structure
        assert "views" in lookml_dict
        assert len(lookml_dict["views"]) == 1
        view = lookml_dict["views"][0]

        # Check entity labels
        rental_entity = view["dimensions"][0]
        assert rental_entity["name"] == "rental"
        assert rental_entity["primary_key"] == "yes"
        assert (
            rental_entity["view_label"] == "Rentals"
        )  # From first dimension's subject
        assert rental_entity["group_label"] == "Join Keys"  # Fact table

        # Check dimension labels
        payment_dim = view["dimensions"][1]
        assert payment_dim["name"] == "payment_status"
        assert payment_dim["view_label"] == "Rentals"
        assert payment_dim["group_label"] == "Transaction Details"

        # Check measure labels
        revenue_measure = view["measures"][0]
        assert revenue_measure["name"] == "total_revenue_measure"
        assert revenue_measure["view_label"] == "  Metrics"
        assert revenue_measure["group_label"] == "Rentals Performance"

    def test_flat_meta_precedence_over_hierarchy(self) -> None:
        """Test that flat meta (subject, category) takes precedence over hierarchy."""
        from dbt_to_lookml.schemas import Hierarchy

        config = Config(
            meta=ConfigMeta(
                subject="Flat Subject",
                category="Flat Category",
                hierarchy=Hierarchy(
                    entity="Hierarchical Entity", category="Hierarchical Category"
                ),
            )
        )

        dimension = Dimension(
            name="test_dim", type=DimensionType.CATEGORICAL, config=config
        )

        view_label, group_label = dimension.get_dimension_labels()
        # Flat structure should take precedence
        assert view_label == "Flat Subject"
        assert group_label == "Flat Category"

    def test_hierarchy_fallback_when_flat_meta_absent(self) -> None:
        """Test that hierarchy is used as fallback when flat meta is absent."""
        from dbt_to_lookml.schemas import Hierarchy

        config = Config(
            meta=ConfigMeta(
                hierarchy=Hierarchy(
                    entity="Hierarchical Entity", category="Hierarchical Category"
                )
            )
        )

        dimension = Dimension(
            name="test_dim", type=DimensionType.CATEGORICAL, config=config
        )

        view_label, group_label = dimension.get_dimension_labels()
        # Should fall back to hierarchy
        assert view_label == "Hierarchical Entity"
        assert group_label == "Hierarchical Category"

    def test_underscore_formatting_in_flat_meta(self) -> None:
        """Test that underscores in flat meta are properly formatted."""
        config = Config(
            meta=ConfigMeta(subject="rental_profile", category="customer_behavior")
        )

        dimension = Dimension(
            name="test_dim", type=DimensionType.CATEGORICAL, config=config
        )

        view_label, group_label = dimension.get_dimension_labels()
        assert view_label == "Rental Profile"
        assert group_label == "Customer Behavior"

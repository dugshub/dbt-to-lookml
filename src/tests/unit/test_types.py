"""Unit tests for type enumerations using new architecture."""

import pytest

from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
    TimeGranularity,
)


class TestDimensionType:
    """Test cases for DimensionType enum."""

    def test_dimension_type_values(self) -> None:
        """Test all dimension type values."""
        assert DimensionType.CATEGORICAL == "categorical"
        assert DimensionType.TIME == "time"

    def test_dimension_type_from_string(self) -> None:
        """Test creating dimension types from strings."""
        assert DimensionType("categorical") == DimensionType.CATEGORICAL
        assert DimensionType("time") == DimensionType.TIME

    def test_invalid_dimension_type(self) -> None:
        """Test invalid dimension type raises error."""
        with pytest.raises(ValueError):
            DimensionType("invalid_type")


class TestAggregationType:
    """Test cases for AggregationType enum."""

    def test_aggregation_type_values(self) -> None:
        """Test all aggregation type values."""
        assert AggregationType.COUNT == "count"
        assert AggregationType.COUNT_DISTINCT == "count_distinct"
        assert AggregationType.SUM == "sum"
        assert AggregationType.AVERAGE == "average"
        assert AggregationType.MIN == "min"
        assert AggregationType.MAX == "max"
        assert AggregationType.MEDIAN == "median"

    def test_aggregation_type_from_string(self) -> None:
        """Test creating aggregation types from strings."""
        assert AggregationType("count") == AggregationType.COUNT
        assert AggregationType("sum") == AggregationType.SUM
        assert AggregationType("average") == AggregationType.AVERAGE

    def test_invalid_aggregation_type(self) -> None:
        """Test invalid aggregation type raises error."""
        with pytest.raises(ValueError):
            AggregationType("invalid_agg")


class TestTimeGranularity:
    """Test cases for TimeGranularity enum."""

    def test_time_granularity_values(self) -> None:
        """Test all time granularity values."""
        assert TimeGranularity.MINUTE == "minute"
        assert TimeGranularity.HOUR == "hour"
        assert TimeGranularity.DAY == "day"
        assert TimeGranularity.WEEK == "week"
        assert TimeGranularity.MONTH == "month"
        assert TimeGranularity.QUARTER == "quarter"
        assert TimeGranularity.YEAR == "year"

    def test_time_granularity_from_string(self) -> None:
        """Test creating time granularity from strings."""
        assert TimeGranularity("day") == TimeGranularity.DAY
        assert TimeGranularity("hour") == TimeGranularity.HOUR
        assert TimeGranularity("minute") == TimeGranularity.MINUTE

    def test_invalid_time_granularity(self) -> None:
        """Test invalid time granularity raises error."""
        with pytest.raises(ValueError):
            TimeGranularity("invalid_granularity")

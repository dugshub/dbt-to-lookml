"""Type definitions and enums for dbt-to-lookml."""

from enum import Enum


class AggregationType(str, Enum):
    """Supported aggregation types for measures."""

    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    SUM_BOOLEAN = "sum_boolean"
    PERCENTILE = "percentile"


class DimensionType(str, Enum):
    """Supported dimension types."""

    CATEGORICAL = "categorical"
    TIME = "time"


class TimeGranularity(str, Enum):
    """Supported time granularities."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    HOUR = "hour"
    MINUTE = "minute"


# Type mapping from dbt aggregation types to LookML measure types
LOOKML_TYPE_MAP = {
    AggregationType.COUNT: "count",
    AggregationType.COUNT_DISTINCT: "count_distinct",
    AggregationType.SUM: "sum",
    AggregationType.AVERAGE: "average",
    AggregationType.MIN: "min",
    AggregationType.MAX: "max",
    AggregationType.MEDIAN: "median",
    AggregationType.SUM_BOOLEAN: "sum",
    AggregationType.PERCENTILE: "percentile",
}

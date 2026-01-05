"""
Metric domain - business-level measures with semantic meaning.

Includes MetricVariant which is owned by Metric (not a separate entity).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Union

from pydantic import BaseModel, Field, computed_field

from semantic_patterns.domain.filter import Filter

# =============================================================================
# Types
# =============================================================================


class MetricType(str, Enum):
    """Metric types - how the metric is computed."""

    SIMPLE = "simple"  # Direct aggregation of a measure
    DERIVED = "derived"  # Computation over other metrics
    RATIO = "ratio"  # Ratio of two metrics


class VariantKind(str, Enum):
    """The kind of variant - what type of rendering."""

    BASE = "base"  # The base metric itself
    POP = "pop"  # Period-over-Period comparison
    BENCHMARK = "benchmark"  # Benchmark comparison


class PopComparison(str, Enum):
    """Period-over-Period comparison period."""

    PRIOR_YEAR = "py"
    PRIOR_MONTH = "pm"
    PRIOR_QUARTER = "pq"
    PRIOR_WEEK = "pw"


class PopOutput(str, Enum):
    """What the PoP variant outputs."""

    PREVIOUS = "previous"  # The prior period value
    CHANGE = "change"  # Absolute difference
    PERCENT_CHANGE = "pct_change"  # Relative change


# =============================================================================
# PoP Configuration
# =============================================================================


class PopConfig(BaseModel):
    """PoP configuration from YAML - expanded into variants by builder."""

    comparisons: list[PopComparison] = Field(default_factory=list)
    outputs: list[PopOutput] = Field(default_factory=list)

    def expand_variants(self, value_format: str | None = None) -> list[MetricVariant]:
        """Expand this config into concrete MetricVariant objects."""
        variants = []
        for comparison in self.comparisons:
            for output in self.outputs:
                variants.append(
                    MetricVariant.pop(
                        comparison=comparison,
                        output=output,
                        value_format=value_format,
                    )
                )
        return variants

    model_config = {"frozen": True}


# =============================================================================
# Variant Parameters
# =============================================================================


class PopParams(BaseModel):
    """Parameters for a PoP variant."""

    comparison: PopComparison
    output: PopOutput

    @property
    def suffix(self) -> str:
        """Generate suffix like '_py', '_pm_change', '_py_pct_change'."""
        base = f"_{self.comparison.value}"
        if self.output == PopOutput.PREVIOUS:
            return base
        elif self.output == PopOutput.CHANGE:
            return f"{base}_change"
        else:
            return f"{base}_pct_change"

    model_config = {"frozen": True}


class BenchmarkParams(BaseModel):
    """Parameters for a Benchmark variant."""

    slice: str  # market, segment, region, etc.
    label: str | None = None

    @property
    def suffix(self) -> str:
        return f"_vs_{self.slice}"

    model_config = {"frozen": True}


# =============================================================================
# MetricVariant
# =============================================================================


class MetricVariant(BaseModel):
    """
    A specific rendering of a metric. NOT a separate metric.

    Has no independent identity - name is always derived from parent metric.
    """

    kind: VariantKind
    params: Union[PopParams, BenchmarkParams, None] = None
    value_format: str | None = None

    @property
    def suffix(self) -> str:
        if self.kind == VariantKind.BASE:
            return ""
        elif self.params is not None:
            return self.params.suffix
        return ""

    def resolve_name(self, parent: Metric) -> str:
        """Variant name is ALWAYS parent.name + suffix."""
        return f"{parent.name}{self.suffix}"

    @classmethod
    def base(cls) -> MetricVariant:
        return cls(kind=VariantKind.BASE)

    @classmethod
    def pop(
        cls,
        comparison: PopComparison,
        output: PopOutput,
        value_format: str | None = None,
    ) -> MetricVariant:
        return cls(
            kind=VariantKind.POP,
            params=PopParams(comparison=comparison, output=output),
            value_format=value_format,
        )

    @classmethod
    def benchmark(
        cls, slice: str, label: str | None = None, value_format: str | None = None
    ) -> MetricVariant:
        return cls(
            kind=VariantKind.BENCHMARK,
            params=BenchmarkParams(slice=slice, label=label),
            value_format=value_format,
        )

    model_config = {"frozen": False}


# =============================================================================
# Metric
# =============================================================================


class Metric(BaseModel):
    """
    A metric is a business-level measure with semantic meaning.

    Metrics OWN their variants. A metric with 7 variants is still ONE metric.

    Supports three types:
    - simple: Direct aggregation of a measure
    - derived: Computation over other metrics
    - ratio: Ratio of two metrics
    """

    name: str
    type: MetricType
    label: str | None = None
    description: str | None = None

    # Simple metric params
    measure: str | None = None  # Reference to measure name

    # Derived metric params
    expr: str | None = None  # SQL expression
    metrics: list[str] | None = None  # Metric dependencies

    # Ratio metric params
    numerator: str | None = None  # Numerator metric
    denominator: str | None = None  # Denominator metric

    # Filter
    filter: Filter | None = None

    # PoP configuration (expanded into variants by builder)
    pop: PopConfig | None = None

    # Benchmarks configuration (expanded into variants by builder)
    benchmarks: list[BenchmarkParams] | None = None

    # Variants are OWNED by this metric (populated by builder)
    variants: list[MetricVariant] = Field(default_factory=list)

    # Display/organization
    format: str | None = None  # usd, decimal_0, percent_1, etc.
    group: str | None = None  # Grouping (supports dot notation)
    entity: str | None = None  # Associated entity

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def variant_count(self) -> int:
        return len(self.variants)

    @computed_field
    @property
    def has_pop(self) -> bool:
        return any(v.kind == VariantKind.POP for v in self.variants)

    @computed_field
    @property
    def has_benchmark(self) -> bool:
        return any(v.kind == VariantKind.BENCHMARK for v in self.variants)

    @property
    def group_parts(self) -> list[str]:
        """Parse group into parts (handles dot notation and lists)."""
        if not self.group:
            return []
        if isinstance(self.group, list):
            return self.group
        return self.group.split(".")

    def expand_variants(self) -> None:
        """Expand pop/benchmarks config into concrete variants."""
        # Always add base variant if not present
        if not any(v.kind == VariantKind.BASE for v in self.variants):
            self.variants.insert(0, MetricVariant.base())

        # Expand PoP
        if self.pop:
            pop_variants = self.pop.expand_variants(value_format=self.format)
            self.variants.extend(pop_variants)

        # Expand benchmarks
        if self.benchmarks:
            for bench in self.benchmarks:
                self.variants.append(
                    MetricVariant.benchmark(
                        slice=bench.slice,
                        label=bench.label,
                        value_format=self.format,
                    )
                )

    model_config = {"frozen": False, "extra": "forbid"}

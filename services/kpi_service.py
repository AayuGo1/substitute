"""KPI calculation service for the engineering monitoring dashboard.

This module exposes :class:`KPIService`, the component responsible for
turning a metric's raw historical values into the standard set of KPIs
shown throughout the dashboard: total, average, last registered value,
maximum, minimum, trend, and percentage change. It also exposes
section-level aggregated KPIs, rolling up every metric in a section (and
optionally its subsections) into a single summary.

The calculations are entirely generic: they operate on whatever
:class:`~models.metric.Metric` and :class:`~models.metric.MetricDataPoint`
objects a section happens to contain, discovered dynamically via
:class:`~services.section_service.SectionService`. No department,
section, subsection, or metric name (NPCL, DG, GG, Air Compressor,
Freon, Water, Energy, or any other) is ever referenced here — this
service works identically for every section the workbook defines,
including ones that don't exist yet.

This service deliberately contains:

* No chart generation.
* No Streamlit or any other UI code.
* No re-parsing or re-discovery of workbook structure — it only reads
  metric values already built by the parser, via
  :class:`~services.section_service.SectionService`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, List, Optional, Protocol, Sequence, runtime_checkable

from models.metric import Metric, MetricDataPoint
from models.section import Section, SubSection


# A predicate used to filter a metric's data points before KPIs are
# computed from them. This is the single extension point for "future
# filters": date range and month filtering are both implemented as
# factories that produce one of these, and any further filter (for
# example a shift or a specific weekday) can be added the same way
# without changing any calculation method's signature.
DataPointFilter = Callable[[MetricDataPoint], bool]


class TrendDirection:
    """Enumeration-like constants describing a metric's trend direction.

    Kept as plain string constants rather than an ``enum.Enum`` so KPI
    results serialize trivially (for example to JSON or a DataFrame cell)
    without extra handling in calling code.
    """

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class KPIResult:
    """The standard set of KPIs computed for a single metric.

    Attributes:
        metric_name: The metric's normalized (slugified) name.
        display_name: The metric's human-readable label.
        unit: The metric's unit of measure, if any.
        total: The sum of all in-range, non-``None`` values.
        average: The mean of all in-range, non-``None`` values.
        last_value: The most recent in-range, non-``None`` value.
        last_timestamp: The timestamp associated with ``last_value``.
        maximum: The largest in-range, non-``None`` value.
        minimum: The smallest in-range, non-``None`` value.
        trend: The overall direction of change across the in-range
            values (see :class:`TrendDirection`).
        percentage_change: The percentage change from the first to the
            last in-range, non-``None`` value.
        sample_count: The number of in-range, non-``None`` values the
            KPIs were computed from.
    """

    metric_name: str
    display_name: str
    unit: str
    total: Optional[float]
    average: Optional[float]
    last_value: Optional[float]
    last_timestamp: Optional[datetime]
    maximum: Optional[float]
    minimum: Optional[float]
    trend: str
    percentage_change: Optional[float]
    sample_count: int = 0


@dataclass(frozen=True)
class SectionKPISummary:
    """Aggregated KPIs rolled up across every metric in a section.

    Unlike :class:`KPIResult`, which describes one metric, this describes
    the section as a whole: every in-range, non-``None`` value from every
    included metric is pooled together before the same KPI calculations
    are applied.

    Attributes:
        section_name: The section's normalized (slugified) name.
        display_name: The section's human-readable label.
        units: The distinct units of measure found among the section's
            metrics, in first-seen order. A section commonly mixes units
            (for example kWh and m3), so this is a list rather than a
            single value.
        total: The sum of every in-range, non-``None`` value across all
            included metrics.
        average: The mean of every in-range, non-``None`` value across
            all included metrics.
        last_value: The most recent in-range, non-``None`` value across
            all included metrics.
        last_timestamp: The timestamp associated with ``last_value``.
        maximum: The largest in-range, non-``None`` value across all
            included metrics.
        minimum: The smallest in-range, non-``None`` value across all
            included metrics.
        trend: The overall direction of change across the pooled,
            chronologically ordered values (see :class:`TrendDirection`).
        percentage_change: The percentage change from the first to the
            last pooled, chronologically ordered value.
        metric_count: The number of metrics the summary was aggregated
            from.
        sample_count: The number of in-range, non-``None`` values the
            summary was computed from, across all included metrics.
    """

    section_name: str
    display_name: str
    units: List[str]
    total: Optional[float]
    average: Optional[float]
    last_value: Optional[float]
    last_timestamp: Optional[datetime]
    maximum: Optional[float]
    minimum: Optional[float]
    trend: str
    percentage_change: Optional[float]
    metric_count: int = 0
    sample_count: int = 0


@runtime_checkable
class SectionServiceLike(Protocol):
    """Structural interface required of an injected section service.

    :class:`KPIService` depends on this narrow interface rather than the
    concrete ``SectionService`` class, keeping it decoupled from that
    service's implementation (Dependency Inversion Principle) and
    straightforward to test with fakes.
    """

    def list_section_metrics(
        self, section: Section, include_subsections: bool = True
    ) -> List[Metric]:
        """Lists every metric belonging to a section, in workbook order."""
        ...

    def list_subsection_metrics(self, subsection: SubSection) -> List[Metric]:
        """Lists every metric belonging to a single subsection, in order."""
        ...

    def list_subsections(
        self, section: Section, predicate: Optional[Callable] = None
    ) -> List[SubSection]:
        """Lists every subsection belonging to a section, in order."""
        ...

    def list_units(self, section: Section) -> List[str]:
        """Lists the distinct units used within a single section."""
        ...


class KPIService:
    """Computes standard KPIs for any section, subsection, or metric.

    :class:`KPIService` is the entry point dashboard pages should use to
    turn parsed metric history into displayable KPI figures. It never
    assumes anything about which sections or metrics a workbook contains;
    every calculation is driven purely by the shape of the
    :class:`~models.metric.Metric` objects it's handed.

    Attributes:
        section_service: The injected service used to enumerate a
            section's or subsection's metrics.
    """

    def __init__(self, section_service: SectionServiceLike) -> None:
        """Initializes the service with its section service dependency.

        Args:
            section_service: An object satisfying
                :class:`SectionServiceLike`.
        """
        self.section_service = section_service

    # ------------------------------------------------------------------
    # Filter factories
    # ------------------------------------------------------------------

    @staticmethod
    def build_date_range_filter(
        start: Optional[date], end: Optional[date]
    ) -> DataPointFilter:
        """Builds a filter that keeps data points within a date range.

        Args:
            start: The earliest date to include (inclusive). ``None``
                means no lower bound.
            end: The latest date to include (inclusive). ``None`` means
                no upper bound.

        Returns:
            A :data:`DataPointFilter` that accepts a data point when its
            timestamp's date falls within ``[start, end]``.
        """

        def _matches(point: MetricDataPoint) -> bool:
            point_date = point.timestamp.date()
            if start is not None and point_date < start:
                return False
            if end is not None and point_date > end:
                return False
            return True

        return _matches

    @staticmethod
    def build_month_filter(year: int, month: int) -> DataPointFilter:
        """Builds a filter that keeps data points within a calendar month.

        Args:
            year: The four-digit year to match.
            month: The month to match, from 1 (January) to 12 (December).

        Returns:
            A :data:`DataPointFilter` that accepts a data point when its
            timestamp falls in the given year and month.
        """

        def _matches(point: MetricDataPoint) -> bool:
            return point.timestamp.year == year and point.timestamp.month == month

        return _matches

    @staticmethod
    def combine_filters(*filters: Optional[DataPointFilter]) -> DataPointFilter:
        """Combines several filters into one that requires all to match.

        ``None`` entries are ignored, so callers can pass optional
        filters (for example a date range that may or may not be set)
        without special-casing them.

        Args:
            *filters: Any number of optional :data:`DataPointFilter`
                callables.

        Returns:
            A single :data:`DataPointFilter` that accepts a data point
            only when every supplied filter accepts it.
        """
        active_filters = [f for f in filters if f is not None]

        def _matches(point: MetricDataPoint) -> bool:
            return all(f(point) for f in active_filters)

        return _matches

    # ------------------------------------------------------------------
    # Metric-level KPIs
    # ------------------------------------------------------------------

    def calculate_metric_kpis(
        self,
        metric: Metric,
        data_point_filter: Optional[DataPointFilter] = None,
    ) -> KPIResult:
        """Computes the standard KPI set for a single metric.

        Args:
            metric: The metric to compute KPIs for.
            data_point_filter: An optional filter restricting which of
                the metric's historical values are included (for example
                a date range or month filter). When omitted, every
                historical value is used.

        Returns:
            The metric's :class:`KPIResult`. Numeric fields are ``None``
            when there are no in-range, non-``None`` values to compute
            them from.
        """
        points = self._select_points(metric.historical_values, data_point_filter)
        values = [p.value for p in points if p.value is not None]

        total = self._calculate_total(values)
        average = self._calculate_average(values)
        maximum = self._calculate_maximum(values)
        minimum = self._calculate_minimum(values)
        last_value, last_timestamp = self._calculate_last_registered(points)
        trend = self._calculate_trend(values)
        percentage_change = self._calculate_percentage_change(values)

        return KPIResult(
            metric_name=metric.name,
            display_name=metric.display_name,
            unit=metric.unit,
            total=total,
            average=average,
            last_value=last_value,
            last_timestamp=last_timestamp,
            maximum=maximum,
            minimum=minimum,
            trend=trend,
            percentage_change=percentage_change,
            sample_count=len(values),
        )

    # ------------------------------------------------------------------
    # Section / subsection level KPIs (per metric)
    # ------------------------------------------------------------------

    def calculate_section_kpis(
        self,
        section: Section,
        include_subsections: bool = True,
        data_point_filter: Optional[DataPointFilter] = None,
    ) -> List[KPIResult]:
        """Computes KPIs for every metric belonging to a section.

        Works identically regardless of which section is passed in and
        regardless of whether it has subsections, so any expandable
        section panel in the dashboard can call this with no further
        branching.

        Args:
            section: The section to compute KPIs for.
            include_subsections: Whether to include metrics nested in
                the section's subsections. Defaults to ``True``.
            data_point_filter: An optional filter restricting which
                historical values are included in each metric's KPIs.

        Returns:
            One :class:`KPIResult` per metric, in the same order
            :class:`~services.section_service.SectionService` returns
            them.
        """
        metrics = self.section_service.list_section_metrics(
            section, include_subsections=include_subsections
        )
        return [
            self.calculate_metric_kpis(metric, data_point_filter)
            for metric in metrics
        ]

    def calculate_subsection_kpis(
        self,
        subsection: SubSection,
        data_point_filter: Optional[DataPointFilter] = None,
    ) -> List[KPIResult]:
        """Computes KPIs for every metric belonging to a subsection.

        Args:
            subsection: The subsection to compute KPIs for.
            data_point_filter: An optional filter restricting which
                historical values are included in each metric's KPIs.

        Returns:
            One :class:`KPIResult` per metric, in the subsection's
            workbook order.
        """
        metrics = self.section_service.list_subsection_metrics(subsection)
        return [
            self.calculate_metric_kpis(metric, data_point_filter)
            for metric in metrics
        ]

    def calculate_kpis_by_subsection(
        self,
        section: Section,
        data_point_filter: Optional[DataPointFilter] = None,
    ) -> List[tuple]:
        """Computes KPIs for a section, grouped subsection by subsection.

        Useful for expandable panels that render one group of KPI cards
        per subsection (for example one group per department) rather
        than a single flat list.

        Args:
            section: The section to compute KPIs for.
            data_point_filter: An optional filter restricting which
                historical values are included in each metric's KPIs.

        Returns:
            A list of ``(subsection, kpi_results)`` tuples, one per
            subsection, in workbook order. Metrics attached directly to
            the section (outside any subsection) are not included; use
            :meth:`calculate_section_kpis` with
            ``include_subsections=False`` for those.
        """
        subsections = self.section_service.list_subsections(section)
        return [
            (subsection, self.calculate_subsection_kpis(subsection, data_point_filter))
            for subsection in subsections
        ]

    # ------------------------------------------------------------------
    # Section-level aggregated KPI summary
    # ------------------------------------------------------------------

    def calculate_section_summary(
        self,
        section: Section,
        include_subsections: bool = True,
        data_point_filter: Optional[DataPointFilter] = None,
    ) -> SectionKPISummary:
        """Computes a single aggregated KPI summary across a section.

        Every in-range, non-``None`` value from every metric belonging to
        ``section`` (and, when requested, its subsections) is pooled into
        one combined series before the standard KPI calculations are
        applied. This gives one set of section-wide figures — total,
        average, last registered value, maximum, minimum, trend, and
        percentage change — regardless of how many metrics or
        subsections the section happens to contain.

        The implementation is fully dynamic: it never references any
        particular section, subsection, or metric name, and works
        identically for every section discovered in the workbook.

        Args:
            section: The section to aggregate.
            include_subsections: Whether to include metrics nested in
                the section's subsections in the aggregate. Defaults to
                ``True``.
            data_point_filter: An optional filter restricting which
                historical values are included (for example a date range
                or month filter), applied identically to every metric
                before pooling.

        Returns:
            The section's :class:`SectionKPISummary`. Numeric fields are
            ``None`` when there are no in-range, non-``None`` values
            anywhere in the section to compute them from.
        """
        metrics = self.section_service.list_section_metrics(
            section, include_subsections=include_subsections
        )
        pooled_points = self._pool_metric_points(metrics, data_point_filter)
        values = [p.value for p in pooled_points if p.value is not None]

        total = self._calculate_total(values)
        average = self._calculate_average(values)
        maximum = self._calculate_maximum(values)
        minimum = self._calculate_minimum(values)
        last_value, last_timestamp = self._calculate_last_registered(pooled_points)
        trend = self._calculate_trend(values)
        percentage_change = self._calculate_percentage_change(values)

        return SectionKPISummary(
            section_name=section.name,
            display_name=section.display_name,
            units=self.section_service.list_units(section),
            total=total,
            average=average,
            last_value=last_value,
            last_timestamp=last_timestamp,
            maximum=maximum,
            minimum=minimum,
            trend=trend,
            percentage_change=percentage_change,
            metric_count=len(metrics),
            sample_count=len(values),
        )

    def calculate_subsection_summary(
        self,
        subsection: SubSection,
        data_point_filter: Optional[DataPointFilter] = None,
    ) -> SectionKPISummary:
        """Computes a single aggregated KPI summary across a subsection.

        Mirrors :meth:`calculate_section_summary` but for a single
        subsection's metrics, useful when a panel wants one summary card
        per subsection rather than per top-level section.

        Args:
            subsection: The subsection to aggregate.
            data_point_filter: An optional filter restricting which
                historical values are included, applied identically to
                every metric before pooling.

        Returns:
            A :class:`SectionKPISummary` describing the subsection.
            (The same shape is reused for subsections since the
            aggregation semantics are identical.)
        """
        metrics = self.section_service.list_subsection_metrics(subsection)
        pooled_points = self._pool_metric_points(metrics, data_point_filter)
        values = [p.value for p in pooled_points if p.value is not None]

        total = self._calculate_total(values)
        average = self._calculate_average(values)
        maximum = self._calculate_maximum(values)
        minimum = self._calculate_minimum(values)
        last_value, last_timestamp = self._calculate_last_registered(pooled_points)
        trend = self._calculate_trend(values)
        percentage_change = self._calculate_percentage_change(values)

        return SectionKPISummary(
            section_name=subsection.name,
            display_name=subsection.display_name,
            units=list(dict.fromkeys(unit for unit in subsection.units if unit)),
            total=total,
            average=average,
            last_value=last_value,
            last_timestamp=last_timestamp,
            maximum=maximum,
            minimum=minimum,
            trend=trend,
            percentage_change=percentage_change,
            metric_count=len(metrics),
            sample_count=len(values),
        )

    # ------------------------------------------------------------------
    # Point selection / pooling
    # ------------------------------------------------------------------

    @staticmethod
    def _select_points(
        history: Sequence[MetricDataPoint],
        data_point_filter: Optional[DataPointFilter],
    ) -> List[MetricDataPoint]:
        """Applies an optional filter to a metric's historical values.

        Args:
            history: The metric's full historical values, in workbook
                order.
            data_point_filter: An optional filter to apply.

        Returns:
            The data points for which ``data_point_filter`` is truthy,
            or every data point when no filter is supplied.
        """
        if data_point_filter is None:
            return list(history)
        return [point for point in history if data_point_filter(point)]

    def _pool_metric_points(
        self,
        metrics: Sequence[Metric],
        data_point_filter: Optional[DataPointFilter],
    ) -> List[MetricDataPoint]:
        """Pools the filtered historical values of several metrics.

        The pooled points are sorted chronologically so that section-wide
        "last registered value", trend, and percentage-change
        calculations reflect the true time order of readings across all
        of the section's metrics, rather than metric-by-metric order.

        Args:
            metrics: The metrics to pool, typically every metric in a
                section or subsection.
            data_point_filter: An optional filter restricting which
                historical values are included, applied identically to
                every metric.

        Returns:
            The combined, chronologically sorted data points across all
            metrics.
        """
        pooled: List[MetricDataPoint] = []
        for metric in metrics:
            pooled.extend(self._select_points(metric.historical_values, data_point_filter))
        pooled.sort(key=lambda point: point.timestamp)
        return pooled

    # ------------------------------------------------------------------
    # Individual KPI calculations
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_total(values: Sequence[float]) -> Optional[float]:
        """Sums a metric's in-range values.

        Args:
            values: The non-``None`` values to sum.

        Returns:
            The sum, or ``None`` if there are no values.
        """
        if not values:
            return None
        return sum(values)

    @staticmethod
    def _calculate_average(values: Sequence[float]) -> Optional[float]:
        """Averages a metric's in-range values.

        Args:
            values: The non-``None`` values to average.

        Returns:
            The mean, or ``None`` if there are no values.
        """
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _calculate_maximum(values: Sequence[float]) -> Optional[float]:
        """Finds the largest of a metric's in-range values.

        Args:
            values: The non-``None`` values to inspect.

        Returns:
            The maximum, or ``None`` if there are no values.
        """
        if not values:
            return None
        return max(values)

    @staticmethod
    def _calculate_minimum(values: Sequence[float]) -> Optional[float]:
        """Finds the smallest of a metric's in-range values.

        Args:
            values: The non-``None`` values to inspect.

        Returns:
            The minimum, or ``None`` if there are no values.
        """
        if not values:
            return None
        return min(values)

    @staticmethod
    def _calculate_last_registered(
        points: Sequence[MetricDataPoint],
    ) -> tuple:
        """Finds the most recent in-range, non-``None`` observation.

        Points are assumed to be in chronological order — either the
        workbook's own row order for a single metric, or already sorted
        by timestamp when pooled across several metrics.

        Args:
            points: The (already filtered/pooled) data points to search.

        Returns:
            A ``(value, timestamp)`` tuple for the last non-``None``
            observation, or ``(None, None)`` if none exists.
        """
        for point in reversed(points):
            if point.value is not None:
                timestamp = (
                    point.timestamp if point.timestamp != datetime.min else None
                )
                return point.value, timestamp
        return None, None

    @staticmethod
    def _calculate_percentage_change(values: Sequence[float]) -> Optional[float]:
        """Computes the percentage change from the first to last value.

        Args:
            values: The non-``None`` values, in chronological order.

        Returns:
            The percentage change, or ``None`` if there are fewer than
            two values or the first value is zero (which would make the
            percentage undefined).
        """
        if len(values) < 2:
            return None
        first_value = values[0]
        last_value = values[-1]
        if first_value == 0:
            return None
        return ((last_value - first_value) / abs(first_value)) * 100

    @classmethod
    def _calculate_trend(cls, values: Sequence[float]) -> str:
        """Determines the overall direction of change across values.

        The trend is derived by comparing the average of the first half
        of the in-range values against the average of the second half,
        which is more resilient to single-point noise than comparing
        only the first and last observations.

        Args:
            values: The non-``None`` values, in chronological order.

        Returns:
            One of the :class:`TrendDirection` constants.
        """
        if len(values) < 2:
            return TrendDirection.UNKNOWN

        midpoint = len(values) // 2
        first_half = values[:midpoint] or values[:1]
        second_half = values[midpoint:] or values[-1:]

        first_average = cls._calculate_average(first_half)
        second_average = cls._calculate_average(second_half)
        if first_average is None or second_average is None:
            return TrendDirection.UNKNOWN

        if first_average == 0:
            if second_average == 0:
                return TrendDirection.STABLE
            return (
                TrendDirection.INCREASING
                if second_average > 0
                else TrendDirection.DECREASING
            )

        relative_change = (second_average - first_average) / abs(first_average)
        stability_threshold = 0.01  # Changes within 1% are treated as flat.

        if relative_change > stability_threshold:
            return TrendDirection.INCREASING
        if relative_change < -stability_threshold:
            return TrendDirection.DECREASING
        return TrendDirection.STABLE

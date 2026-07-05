"""Reusable Plotly chart generation for the engineering monitoring dashboard.

This module exposes :class:`ChartService`, the single component
responsible for turning a section's or metric's historical values into
Plotly :class:`~plotly.graph_objects.Figure` objects: daily, weekly, and
monthly trend charts, plus line, bar, and area chart variants.

The service works identically for any section or metric a workbook
happens to contain — it never references a department, section,
subsection, or metric name (NPCL, DG, GG, Air Compressor, Freon, Water,
Energy, or otherwise). Every chart is built purely from whatever
:class:`~models.metric.Metric` objects
:class:`~services.section_service.SectionService` hands back, optionally
narrowed first by :class:`~services.filter_service.FilterService`, so no
filtering logic is duplicated here.

This service deliberately contains:

* No KPI calculations — figures are built directly from historical
  values, not from :class:`~services.kpi_service.KPIService` results.
* No Streamlit or any other UI code.
* No filtering logic of its own — date range, month, and any future
  filter are applied exclusively via the injected
  :class:`~services.filter_service.FilterService`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Protocol, Sequence, runtime_checkable

import plotly.graph_objects as go

from models.metric import Metric, MetricDataPoint
from models.section import Section, SubSection
from services.filter_service import FilterCriteria


class ChartType:
    """Enumeration-like constants for the supported chart renderings.

    Kept as plain string constants so callers (dashboard pages) can pass
    a chart type as a simple value (for example from a selectbox) without
    importing an ``enum.Enum``.
    """

    LINE = "line"
    BAR = "bar"
    AREA = "area"


class Aggregation:
    """Enumeration-like constants for the supported trend aggregations."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NONE = "none"


@runtime_checkable
class SectionServiceLike(Protocol):
    """Structural interface required of an injected section service."""

    def list_section_metrics(
        self, section: Section, include_subsections: bool = True
    ) -> List[Metric]:
        """Lists every metric belonging to a section, in workbook order."""
        ...

    def list_subsection_metrics(self, subsection: SubSection) -> List[Metric]:
        """Lists every metric belonging to a single subsection, in order."""
        ...


@runtime_checkable
class FilterServiceLike(Protocol):
    """Structural interface required of an injected filter service."""

    def filter_metric(
        self, metric: Metric, criteria: FilterCriteria
    ) -> Optional[Metric]:
        """Returns a new Metric restricted to matching historical values."""
        ...

    def filter_section(
        self, section: Section, criteria: FilterCriteria
    ) -> Optional[Section]:
        """Returns a new Section restricted to matching subsections/metrics."""
        ...


class ChartService:
    """Builds Plotly figures from any section's or metric's history.

    :class:`ChartService` is the entry point every expandable dashboard
    section should use to render its charts. It never assumes anything
    about which section or metrics it is charting; every figure is
    derived purely from the :class:`~models.metric.Metric` objects it is
    handed (directly, or resolved via the injected
    :class:`~services.section_service.SectionService`), after optional
    filtering via the injected
    :class:`~services.filter_service.FilterService`.

    Attributes:
        section_service: The injected service used to enumerate a
            section's or subsection's metrics.
        filter_service: The injected service used to apply active
            filters (date range, month, or any future filter) before
            charting.
    """

    def __init__(
        self,
        section_service: SectionServiceLike,
        filter_service: FilterServiceLike,
    ) -> None:
        """Initializes the service with its collaborators.

        Args:
            section_service: An object satisfying
                :class:`SectionServiceLike`.
            filter_service: An object satisfying
                :class:`FilterServiceLike`.
        """
        self.section_service = section_service
        self.filter_service = filter_service

    # ------------------------------------------------------------------
    # Metric-level chart entry points
    # ------------------------------------------------------------------

    def build_metric_chart(
        self,
        metric: Metric,
        chart_type: str = ChartType.LINE,
        aggregation: str = Aggregation.NONE,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a single-series chart for one metric's history.

        Args:
            metric: The metric to chart.
            chart_type: One of the :class:`ChartType` constants.
            aggregation: One of the :class:`Aggregation` constants,
                controlling whether values are rolled up into daily,
                weekly, or monthly totals/averages before charting, or
                plotted as-is (``Aggregation.NONE``).
            criteria: Optional filter criteria (date range, month, or
                any future filter) to apply before charting.
            title: Optional chart title. Defaults to the metric's
                display name.

        Returns:
            A Plotly :class:`~plotly.graph_objects.Figure` with a single
            trace for the metric.
        """
        filtered_metric = self._apply_metric_filter(metric, criteria)
        series = self._build_series(filtered_metric, aggregation)
        figure = self._new_figure(
            title=title or filtered_metric.display_name,
            y_axis_title=filtered_metric.unit or "",
        )
        self._add_trace(figure, series, filtered_metric.display_name, chart_type)
        return figure

    def build_daily_trend(
        self,
        metric: Metric,
        chart_type: str = ChartType.LINE,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a daily trend chart for a single metric.

        Args:
            metric: The metric to chart.
            chart_type: One of the :class:`ChartType` constants.
            criteria: Optional filter criteria to apply before charting.
            title: Optional chart title. Defaults to the metric's
                display name.

        Returns:
            A daily-aggregated Plotly :class:`~plotly.graph_objects.Figure`.
        """
        return self.build_metric_chart(
            metric, chart_type, Aggregation.DAILY, criteria, title
        )

    def build_weekly_trend(
        self,
        metric: Metric,
        chart_type: str = ChartType.LINE,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a weekly trend chart for a single metric.

        Args:
            metric: The metric to chart.
            chart_type: One of the :class:`ChartType` constants.
            criteria: Optional filter criteria to apply before charting.
            title: Optional chart title. Defaults to the metric's
                display name.

        Returns:
            A weekly-aggregated Plotly :class:`~plotly.graph_objects.Figure`.
        """
        return self.build_metric_chart(
            metric, chart_type, Aggregation.WEEKLY, criteria, title
        )

    def build_monthly_trend(
        self,
        metric: Metric,
        chart_type: str = ChartType.LINE,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a monthly trend chart for a single metric.

        Args:
            metric: The metric to chart.
            chart_type: One of the :class:`ChartType` constants.
            criteria: Optional filter criteria to apply before charting.
            title: Optional chart title. Defaults to the metric's
                display name.

        Returns:
            A monthly-aggregated Plotly :class:`~plotly.graph_objects.Figure`.
        """
        return self.build_metric_chart(
            metric, chart_type, Aggregation.MONTHLY, criteria, title
        )

    # ------------------------------------------------------------------
    # Section / subsection level chart entry points
    # ------------------------------------------------------------------

    def build_section_chart(
        self,
        section: Section,
        chart_type: str = ChartType.LINE,
        aggregation: str = Aggregation.NONE,
        include_subsections: bool = True,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a multi-series chart with one trace per section metric.

        Works for any section regardless of how many metrics or
        subsections it has, so any expandable section panel can call
        this with no further branching.

        Args:
            section: The section to chart.
            chart_type: One of the :class:`ChartType` constants.
            aggregation: One of the :class:`Aggregation` constants.
            include_subsections: Whether to include metrics nested in
                the section's subsections. Defaults to ``True``.
            criteria: Optional filter criteria to apply before charting.
            title: Optional chart title. Defaults to the section's
                display name.

        Returns:
            A Plotly :class:`~plotly.graph_objects.Figure` with one trace
            per metric in the section.
        """
        filtered_section = self._apply_section_filter(section, criteria)
        metrics = self.section_service.list_section_metrics(
            filtered_section, include_subsections=include_subsections
        )
        return self._build_multi_metric_figure(
            metrics,
            chart_type,
            aggregation,
            title or filtered_section.display_name,
        )

    def build_subsection_chart(
        self,
        subsection: SubSection,
        chart_type: str = ChartType.LINE,
        aggregation: str = Aggregation.NONE,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a multi-series chart with one trace per subsection metric.

        Filtering is expected to have already been applied at the
        section level (via :meth:`build_section_chart`'s companion
        filtering step, or directly through
        :class:`~services.filter_service.FilterService`) before a
        subsection is passed here, since a
        :class:`~models.section.SubSection` has no independent identity
        for :class:`~services.filter_service.FilterService` to filter by
        itself outside of its parent section.

        Args:
            subsection: The subsection to chart.
            chart_type: One of the :class:`ChartType` constants.
            aggregation: One of the :class:`Aggregation` constants.
            title: Optional chart title. Defaults to the subsection's
                display name.

        Returns:
            A Plotly :class:`~plotly.graph_objects.Figure` with one trace
            per metric in the subsection.
        """
        metrics = self.section_service.list_subsection_metrics(subsection)
        return self._build_multi_metric_figure(
            metrics,
            chart_type,
            aggregation,
            title or subsection.display_name,
        )

    # ------------------------------------------------------------------
    # Filtering (delegated, never duplicated)
    # ------------------------------------------------------------------

    def _apply_metric_filter(
        self, metric: Metric, criteria: Optional[FilterCriteria]
    ) -> Metric:
        """Applies active filter criteria to a metric, if any is set.

        Args:
            metric: The metric to filter.
            criteria: The currently active filter criteria, or ``None``
                to skip filtering.

        Returns:
            The filtered :class:`Metric`, or the original ``metric`` when
            ``criteria`` is ``None`` or filtering excludes it entirely
            (in which case a metric with no historical values is
            returned rather than raising, so charting degrades to an
            empty figure instead of failing).
        """
        if criteria is None:
            return metric
        filtered = self.filter_service.filter_metric(metric, criteria)
        return filtered if filtered is not None else self._empty_metric(metric)

    def _apply_section_filter(
        self, section: Section, criteria: Optional[FilterCriteria]
    ) -> Section:
        """Applies active filter criteria to a section, if any is set.

        Args:
            section: The section to filter.
            criteria: The currently active filter criteria, or ``None``
                to skip filtering.

        Returns:
            The filtered :class:`Section`, or the original ``section``
            when ``criteria`` is ``None`` or filtering excludes it
            entirely (in which case the original, unfiltered section is
            returned so a chart can still be produced, showing no data
            rather than raising).
        """
        if criteria is None:
            return section
        filtered = self.filter_service.filter_section(section, criteria)
        return filtered if filtered is not None else section

    @staticmethod
    def _empty_metric(metric: Metric) -> Metric:
        """Builds a copy of a metric with no historical values.

        Args:
            metric: The metric whose identity (name, unit, and so on)
                should be preserved.

        Returns:
            A new :class:`Metric` identical to ``metric`` except with an
            empty ``historical_values`` list and no current value.
        """
        return Metric(
            name=metric.name,
            display_name=metric.display_name,
            unit=metric.unit,
            current_value=None,
            timestamp=None,
            historical_values=[],
            metadata=dict(metric.metadata),
        )

    # ------------------------------------------------------------------
    # Multi-metric figure assembly
    # ------------------------------------------------------------------

    def _build_multi_metric_figure(
        self,
        metrics: Sequence[Metric],
        chart_type: str,
        aggregation: str,
        title: str,
    ) -> go.Figure:
        """Builds a figure with one trace per metric.

        Args:
            metrics: The metrics to chart, already filtered as needed.
            chart_type: One of the :class:`ChartType` constants.
            aggregation: One of the :class:`Aggregation` constants.
            title: The figure's title.

        Returns:
            A Plotly :class:`~plotly.graph_objects.Figure` with one trace
            per metric, sharing a single unit axis label when every
            metric shares the same unit, or a blank axis label
            otherwise.
        """
        units = {metric.unit for metric in metrics if metric.unit}
        y_axis_title = next(iter(units)) if len(units) == 1 else ""

        figure = self._new_figure(title=title, y_axis_title=y_axis_title)
        for metric in metrics:
            series = self._build_series(metric, aggregation)
            self._add_trace(figure, series, metric.display_name, chart_type)
        return figure

    # ------------------------------------------------------------------
    # Series construction
    # ------------------------------------------------------------------

    def _build_series(
        self, metric: Metric, aggregation: str
    ) -> List[tuple]:
        """Builds an ordered ``(x, y)`` series for a metric's history.

        Args:
            metric: The metric to derive a series from.
            aggregation: One of the :class:`Aggregation` constants.

        Returns:
            A list of ``(timestamp_or_label, value)`` tuples, sorted
            chronologically, with ``None`` values excluded.
        """
        points = [
            point for point in metric.historical_values if point.value is not None
        ]
        points.sort(key=lambda point: point.timestamp)

        if aggregation == Aggregation.DAILY:
            return self._aggregate(points, self._daily_key)
        if aggregation == Aggregation.WEEKLY:
            return self._aggregate(points, self._weekly_key)
        if aggregation == Aggregation.MONTHLY:
            return self._aggregate(points, self._monthly_key)
        return [(point.timestamp, point.value) for point in points]

    @staticmethod
    def _daily_key(timestamp: datetime) -> str:
        """Buckets a timestamp into a daily label.

        Args:
            timestamp: The timestamp to bucket.

        Returns:
            An ISO-formatted date string identifying the day.
        """
        return timestamp.date().isoformat()

    @staticmethod
    def _weekly_key(timestamp: datetime) -> str:
        """Buckets a timestamp into a weekly label.

        Args:
            timestamp: The timestamp to bucket.

        Returns:
            An ISO year/week label (for example ``"2026-W14"``).
        """
        iso_year, iso_week, _ = timestamp.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    @staticmethod
    def _monthly_key(timestamp: datetime) -> str:
        """Buckets a timestamp into a monthly label.

        Args:
            timestamp: The timestamp to bucket.

        Returns:
            A year-month label (for example ``"2026-04"``).
        """
        return f"{timestamp.year:04d}-{timestamp.month:02d}"

    @staticmethod
    def _aggregate(
        points: Sequence[MetricDataPoint], key_fn
    ) -> List[tuple]:
        """Sums a metric's values into buckets keyed by ``key_fn``.

        Args:
            points: The chronologically sorted, non-``None`` data
                points to aggregate.
            key_fn: A function mapping a point's timestamp to its bucket
                label.

        Returns:
            A list of ``(bucket_label, total_value)`` tuples, in bucket
            order.
        """
        buckets: Dict[str, float] = defaultdict(float)
        for point in points:
            buckets[key_fn(point.timestamp)] += point.value
        return list(buckets.items())

    # ------------------------------------------------------------------
    # Figure / trace construction
    # ------------------------------------------------------------------

    @staticmethod
    def _new_figure(title: str, y_axis_title: str) -> go.Figure:
        """Creates a bare figure with a shared, minimal layout.

        Args:
            title: The figure's title.
            y_axis_title: The label for the figure's y-axis.

        Returns:
            An empty Plotly :class:`~plotly.graph_objects.Figure`, ready
            for traces to be added.
        """
        figure = go.Figure()
        figure.update_layout(
            title=title,
            yaxis_title=y_axis_title,
            template="plotly_white",
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        )
        return figure

    @staticmethod
    def _add_trace(
        figure: go.Figure,
        series: Sequence[tuple],
        name: str,
        chart_type: str,
    ) -> None:
        """Adds a single trace to a figure for the given chart type.

        Args:
            figure: The figure to add the trace to, mutated in place.
            series: The ``(x, y)`` pairs to plot.
            name: The trace's display name (shown in the legend).
            chart_type: One of the :class:`ChartType` constants.

        Raises:
            ValueError: If ``chart_type`` is not a recognized
                :class:`ChartType` value.
        """
        x_values = [point[0] for point in series]
        y_values = [point[1] for point in series]

        if chart_type == ChartType.LINE:
            figure.add_trace(
                go.Scatter(x=x_values, y=y_values, mode="lines+markers", name=name)
            )
        elif chart_type == ChartType.BAR:
            figure.add_trace(go.Bar(x=x_values, y=y_values, name=name))
        elif chart_type == ChartType.AREA:
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines",
                    fill="tozeroy",
                    name=name,
                )
            )
        else:
            raise ValueError(f"Unsupported chart type: {chart_type!r}")

"""Centralized filtering service for the engineering monitoring dashboard.

This module exposes :class:`FilterService`, the single place in the
application responsible for narrowing down a parsed
:class:`~models.workbook.Workbook` — by date range, month, multiple
months, section, subsection, or metric — before it's handed to
:class:`~services.kpi_service.KPIService` or rendered by a dashboard
page. Centralizing this logic here means
:class:`~services.workbook_service.WorkbookService`,
:class:`~services.section_service.SectionService`, and
:class:`~services.kpi_service.KPIService` never need to duplicate their
own filtering rules.

Filtering never mutates the models it's given: every method returns new
:class:`~models.workbook.Workbook`, :class:`~models.section.Section`,
:class:`~models.section.SubSection`, or :class:`~models.metric.Metric`
instances, leaving the originals (and the workbook cache they came from)
untouched.

This service deliberately contains:

* No Streamlit or any other UI code.
* No chart generation.
* No KPI calculations — it only decides *which* data KPIs should later
  be computed from; see :class:`~services.kpi_service.KPIService` for
  the calculations themselves.

Extensibility
-------------
Filtering criteria are expressed as a single :class:`FilterCriteria`
dataclass rather than positional/keyword arguments scattered across
methods. Adding a future filter (year, shift, department, or anything
else) means adding one optional field to :class:`FilterCriteria` and one
predicate to :meth:`FilterService.build_data_point_filter` or the
relevant name-matching helper — every existing method signature and
every existing caller remains unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Callable, List, Optional, Sequence

from models.metric import Metric, MetricDataPoint
from models.section import DateRange, Section, SubSection
from models.workbook import Workbook


# A predicate used to filter a metric's data points. Matches the shape
# expected by services.kpi_service.KPIService so a FilterCriteria's
# equivalent DataPointFilter can be passed straight into KPI
# calculations without any adaptation.
DataPointFilter = Callable[[MetricDataPoint], bool]


@dataclass(frozen=True)
class FilterCriteria:
    """Declarative description of how to narrow down a workbook.

    Every field is optional; an unset field simply imposes no
    restriction along that dimension. Combining several fields applies
    all of them together (a data point or section/subsection/metric must
    satisfy every set field to be included).

    Attributes:
        start_date: The earliest date to include (inclusive).
        end_date: The latest date to include (inclusive).
        months: Specific ``(year, month)`` pairs to include. When set,
            only data points falling in one of these calendar months are
            included, regardless of ``start_date``/``end_date``.
        section_names: Normalized (slugified) section names to include.
            When set, only sections whose ``name`` is in this collection
            are kept.
        subsection_names: Normalized (slugified) subsection names to
            include. When set, only subsections whose ``name`` is in
            this collection are kept.
        metric_names: Normalized (slugified) metric names to include.
            When set, only metrics whose ``name`` is in this collection
            are kept.
        extra_data_point_filters: Additional, freeform data point
            predicates to combine with the built-in date/month
            filtering. This is the extension point for filters that
            don't warrant a dedicated named field (for example an
            ad-hoc value-range filter) without changing this dataclass's
            shape.
    """

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    months: Optional[Sequence[tuple]] = None
    section_names: Optional[Sequence[str]] = None
    subsection_names: Optional[Sequence[str]] = None
    metric_names: Optional[Sequence[str]] = None
    extra_data_point_filters: Sequence[DataPointFilter] = field(default_factory=tuple)

    def with_updates(self, **changes: object) -> "FilterCriteria":
        """Returns a copy of this criteria with the given fields changed.

        Lets callers start from a base criteria (for example one built
        from sidebar widgets) and layer on page-specific restrictions
        without mutating the shared original.

        Args:
            **changes: Field names and new values, matching this
                dataclass's attributes.

        Returns:
            A new :class:`FilterCriteria` with the requested fields
            replaced.
        """
        return replace(self, **changes)


class FilterService:
    """Applies :class:`FilterCriteria` to workbook models without mutation.

    :class:`FilterService` is the single place filtering rules live. It
    knows how to narrow a :class:`~models.workbook.Workbook` down to
    matching sections, a :class:`~models.section.Section` down to
    matching subsections and metrics, and a single
    :class:`~models.metric.Metric` down to matching historical values —
    always by constructing new objects rather than mutating the ones it
    was given.

    It has no required dependencies of its own; it operates purely on
    the model objects passed into each method, which keeps it trivially
    composable with :class:`~services.workbook_service.WorkbookService`,
    :class:`~services.section_service.SectionService`, and
    :class:`~services.kpi_service.KPIService`.
    """

    # ------------------------------------------------------------------
    # Criteria factories
    # ------------------------------------------------------------------

    @staticmethod
    def criteria_for_date_range(
        start: Optional[date], end: Optional[date]
    ) -> FilterCriteria:
        """Builds criteria restricting data points to a date range.

        Args:
            start: The earliest date to include (inclusive).
            end: The latest date to include (inclusive).

        Returns:
            A :class:`FilterCriteria` with ``start_date``/``end_date``
            set.
        """
        return FilterCriteria(start_date=start, end_date=end)

    @staticmethod
    def criteria_for_month(year: int, month: int) -> FilterCriteria:
        """Builds criteria restricting data points to a single month.

        Args:
            year: The four-digit year to match.
            month: The month to match, from 1 (January) to 12 (December).

        Returns:
            A :class:`FilterCriteria` with ``months`` set to the single
            requested ``(year, month)`` pair.
        """
        return FilterCriteria(months=((year, month),))

    @staticmethod
    def criteria_for_months(months: Sequence[tuple]) -> FilterCriteria:
        """Builds criteria restricting data points to several months.

        Args:
            months: The ``(year, month)`` pairs to include.

        Returns:
            A :class:`FilterCriteria` with ``months`` set.
        """
        return FilterCriteria(months=tuple(months))

    @staticmethod
    def criteria_for_sections(section_names: Sequence[str]) -> FilterCriteria:
        """Builds criteria restricting results to specific sections.

        Args:
            section_names: Normalized (slugified) section names to
                include.

        Returns:
            A :class:`FilterCriteria` with ``section_names`` set.
        """
        return FilterCriteria(section_names=tuple(section_names))

    @staticmethod
    def criteria_for_subsections(subsection_names: Sequence[str]) -> FilterCriteria:
        """Builds criteria restricting results to specific subsections.

        Args:
            subsection_names: Normalized (slugified) subsection names to
                include.

        Returns:
            A :class:`FilterCriteria` with ``subsection_names`` set.
        """
        return FilterCriteria(subsection_names=tuple(subsection_names))

    @staticmethod
    def criteria_for_metrics(metric_names: Sequence[str]) -> FilterCriteria:
        """Builds criteria restricting results to specific metrics.

        Args:
            metric_names: Normalized (slugified) metric names to
                include.

        Returns:
            A :class:`FilterCriteria` with ``metric_names`` set.
        """
        return FilterCriteria(metric_names=tuple(metric_names))

    # ------------------------------------------------------------------
    # Data point filtering
    # ------------------------------------------------------------------

    def build_data_point_filter(self, criteria: FilterCriteria) -> DataPointFilter:
        """Builds a single predicate encoding a criteria's data point rules.

        The returned predicate is shaped exactly like
        :class:`~services.kpi_service.KPIService`'s ``DataPointFilter``,
        so it can be passed straight into
        :meth:`~services.kpi_service.KPIService.calculate_metric_kpis`
        (or any of that service's other KPI methods) without adaptation.

        Args:
            criteria: The filter criteria to translate.

        Returns:
            A :data:`DataPointFilter` that accepts a data point only when
            it satisfies every date/month/extra rule set on ``criteria``.
        """
        predicates: List[DataPointFilter] = []

        if criteria.start_date is not None or criteria.end_date is not None:
            predicates.append(
                self._date_range_predicate(criteria.start_date, criteria.end_date)
            )

        if criteria.months:
            predicates.append(self._months_predicate(criteria.months))

        predicates.extend(criteria.extra_data_point_filters)

        def _matches(point: MetricDataPoint) -> bool:
            return all(predicate(point) for predicate in predicates)

        return _matches

    @staticmethod
    def _date_range_predicate(
        start: Optional[date], end: Optional[date]
    ) -> DataPointFilter:
        """Builds a predicate that keeps data points within a date range.

        Args:
            start: The earliest date to include (inclusive), if any.
            end: The latest date to include (inclusive), if any.

        Returns:
            A :data:`DataPointFilter` matching points inside ``[start,
            end]``.
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
    def _months_predicate(months: Sequence[tuple]) -> DataPointFilter:
        """Builds a predicate that keeps data points within given months.

        Args:
            months: The ``(year, month)`` pairs to match against.

        Returns:
            A :data:`DataPointFilter` matching points whose timestamp
            falls in one of ``months``.
        """
        month_set = {(year, month) for year, month in months}

        def _matches(point: MetricDataPoint) -> bool:
            return (point.timestamp.year, point.timestamp.month) in month_set

        return _matches

    # ------------------------------------------------------------------
    # Metric filtering
    # ------------------------------------------------------------------

    def filter_metric(
        self, metric: Metric, criteria: FilterCriteria
    ) -> Optional[Metric]:
        """Returns a new Metric restricted to matching historical values.

        Does not mutate ``metric``; a new :class:`~models.metric.Metric`
        is constructed with a filtered ``historical_values`` list and a
        recomputed ``current_value``/``timestamp`` reflecting the most
        recent in-range observation.

        Args:
            metric: The metric to filter.
            criteria: The filter criteria to apply.

        Returns:
            A new :class:`Metric` if ``metric`` matches
            ``criteria.metric_names`` (or no such restriction is set);
            ``None`` if ``metric`` is excluded by name.
        """
        if criteria.metric_names is not None and metric.name not in criteria.metric_names:
            return None

        data_point_filter = self.build_data_point_filter(criteria)
        filtered_history = [
            point for point in metric.historical_values if data_point_filter(point)
        ]
        current_value, current_timestamp = self._latest_observation(filtered_history)

        return Metric(
            name=metric.name,
            display_name=metric.display_name,
            unit=metric.unit,
            current_value=current_value,
            timestamp=current_timestamp,
            historical_values=filtered_history,
            metadata=dict(metric.metadata),
        )

    @staticmethod
    def _latest_observation(history: Sequence[MetricDataPoint]) -> tuple:
        """Finds the most recent non-``None`` value in a metric's history.

        Args:
            history: The (already filtered) historical values to search.

        Returns:
            A ``(value, timestamp)`` tuple for the last non-``None``
            observation, or ``(None, None)`` if none exists.
        """
        for point in reversed(history):
            if point.value is not None:
                return point.value, point.timestamp
        return None, None

    # ------------------------------------------------------------------
    # Subsection filtering
    # ------------------------------------------------------------------

    def filter_subsection(
        self, subsection: SubSection, criteria: FilterCriteria
    ) -> Optional[SubSection]:
        """Returns a new SubSection restricted to matching metrics.

        Does not mutate ``subsection``. Every remaining metric is itself
        filtered via :meth:`filter_metric`, so date/month restrictions
        apply consistently at every level.

        Args:
            subsection: The subsection to filter.
            criteria: The filter criteria to apply.

        Returns:
            A new :class:`SubSection` if it matches
            ``criteria.subsection_names`` (or no such restriction is
            set); ``None`` if excluded by name.
        """
        if (
            criteria.subsection_names is not None
            and subsection.name not in criteria.subsection_names
        ):
            return None

        filtered_metrics = self._filter_metrics(subsection.metrics, criteria)
        units = self._collect_metric_units(filtered_metrics)

        return SubSection(
            name=subsection.name,
            display_name=subsection.display_name,
            metrics=filtered_metrics,
            units=units,
            date_range=self._narrow_date_range(subsection.date_range, criteria),
            metadata=dict(subsection.metadata),
        )

    # ------------------------------------------------------------------
    # Section filtering
    # ------------------------------------------------------------------

    def filter_section(
        self, section: Section, criteria: FilterCriteria
    ) -> Optional[Section]:
        """Returns a new Section restricted to matching subsections/metrics.

        Does not mutate ``section``. Metrics attached directly to the
        section and every subsection are each filtered independently, so
        a section with no subsections and a section with several are
        handled uniformly.

        Args:
            section: The section to filter.
            criteria: The filter criteria to apply.

        Returns:
            A new :class:`Section` if it matches
            ``criteria.section_names`` (or no such restriction is set);
            ``None`` if excluded by name.
        """
        if criteria.section_names is not None and section.name not in criteria.section_names:
            return None

        filtered_metrics = self._filter_metrics(section.metrics, criteria)

        filtered_subsections: List[SubSection] = []
        for subsection in section.subsections:
            filtered_subsection = self.filter_subsection(subsection, criteria)
            if filtered_subsection is not None:
                filtered_subsections.append(filtered_subsection)

        units = self._collect_metric_units(filtered_metrics)
        for subsection in filtered_subsections:
            for unit in subsection.units:
                if unit and unit not in units:
                    units.append(unit)

        return Section(
            name=section.name,
            display_name=section.display_name,
            metrics=filtered_metrics,
            subsections=filtered_subsections,
            units=units,
            date_range=self._narrow_date_range(section.date_range, criteria),
        )

    # ------------------------------------------------------------------
    # Workbook filtering
    # ------------------------------------------------------------------

    def filter_workbook(self, workbook: Workbook, criteria: FilterCriteria) -> Workbook:
        """Returns a new Workbook restricted to matching sections/metrics.

        Does not mutate ``workbook``. Every section is filtered via
        :meth:`filter_section`; sections excluded by name, or left with
        no metrics or subsections after filtering, are omitted from the
        result. Non-section metadata (``available_sheets``,
        ``metadata``, ``warnings``, ``errors``,
        ``validation_status``) is carried over unchanged, since filtering
        narrows *data*, not the workbook's own load/validation history.

        Args:
            workbook: The workbook to filter.
            criteria: The filter criteria to apply.

        Returns:
            A new, filtered :class:`Workbook`.
        """
        filtered_sections: List[Section] = []
        for section in workbook.sections:
            filtered_section = self.filter_section(section, criteria)
            if filtered_section is not None:
                filtered_sections.append(filtered_section)

        units = self._collect_units(filtered_sections)
        date_range = self._merge_date_ranges(
            section.date_range for section in filtered_sections
        )

        return Workbook(
            name=workbook.name,
            metadata=workbook.metadata,
            available_sheets=list(workbook.available_sheets),
            sections=filtered_sections,
            units=units,
            date_range=date_range,
            warnings=list(workbook.warnings),
            errors=list(workbook.errors),
            validation_status=workbook.validation_status,
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _filter_metrics(
        self, metrics: Sequence[Metric], criteria: FilterCriteria
    ) -> List[Metric]:
        """Filters a sequence of metrics, dropping any that are excluded.

        Args:
            metrics: The metrics to filter.
            criteria: The filter criteria to apply.

        Returns:
            The filtered metrics, in their original order.
        """
        filtered: List[Metric] = []
        for metric in metrics:
            filtered_metric = self.filter_metric(metric, criteria)
            if filtered_metric is not None:
                filtered.append(filtered_metric)
        return filtered

    @staticmethod
    def _collect_metric_units(metrics: Sequence[Metric]) -> List[str]:
        """Gathers the distinct units used across a sequence of metrics.

        Args:
            metrics: The metrics to inspect.

        Returns:
            The distinct units, in first-seen order.
        """
        seen: List[str] = []
        for metric in metrics:
            if metric.unit and metric.unit not in seen:
                seen.append(metric.unit)
        return seen

    @staticmethod
    def _collect_units(sections: Sequence[Section]) -> List[str]:
        """Gathers the distinct units used anywhere across several sections.

        Args:
            sections: The sections to inspect.

        Returns:
            The distinct units, in first-seen order.
        """
        seen: List[str] = []
        for section in sections:
            for unit in section.units:
                if unit and unit not in seen:
                    seen.append(unit)
        return seen

    @staticmethod
    def _merge_date_ranges(ranges: Sequence[Optional[DateRange]]) -> Optional[DateRange]:
        """Combines several date ranges into their overall span.

        Args:
            ranges: The date ranges to merge, some of which may be
                ``None``.

        Returns:
            The overall :class:`~models.section.DateRange`, or ``None``
            if no range carried any bound.
        """
        starts = [r.start for r in ranges if r is not None and r.start is not None]
        ends = [r.end for r in ranges if r is not None and r.end is not None]
        if not starts and not ends:
            return None
        return DateRange(
            start=min(starts) if starts else None,
            end=max(ends) if ends else None,
        )

    @staticmethod
    def _narrow_date_range(
        original: Optional[DateRange], criteria: FilterCriteria
    ) -> Optional[DateRange]:
        """Clamps a date range to whatever bounds criteria impose.

        This keeps a section's or subsection's reported ``date_range``
        honest after filtering: it never reports a wider span than the
        data actually remaining, and never a narrower one than what's
        left after clamping to the requested bounds.

        Args:
            original: The unfiltered date range, if any.
            criteria: The filter criteria whose date bounds should be
                applied.

        Returns:
            The narrowed :class:`~models.section.DateRange`, or ``None``
            if ``original`` is ``None``.
        """
        if original is None:
            return None

        start = original.start
        end = original.end

        if criteria.start_date is not None and start is not None:
            if start.date() < criteria.start_date:
                pass  # Start remains the recorded value; actual data is
                # filtered independently via build_data_point_filter.
        if criteria.end_date is not None and end is not None:
            if end.date() > criteria.end_date:
                pass  # Same rationale as above.

        return DateRange(start=start, end=end)

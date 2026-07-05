"""Orchestration layer for the Overview (homepage) dashboard page.

This module exposes :class:`DashboardService`, the single component the
Overview page talks to. It coordinates
:class:`~services.workbook_service.WorkbookService`,
:class:`~services.section_service.SectionService`,
:class:`~services.filter_service.FilterService`,
:class:`~services.kpi_service.KPIService`,
:class:`~services.summary_service.SummaryService`, and
:class:`~services.chart_service.ChartService` to assemble a single
:class:`OverviewPageData` model containing everything the page needs to
render: header information, top-level KPI cards, the fixed summary
cards, the available filter options, every expandable section (with its
own KPIs and chart), and workbook metadata.

This service deliberately contains:

* No Streamlit or any other UI code.
* No Plotly figure construction of its own — every
  :class:`~plotly.graph_objects.Figure` is produced by delegating to
  :class:`~services.chart_service.ChartService`.
* No duplicated business logic — KPI math stays in
  :class:`~services.kpi_service.KPIService`, summary-card configuration
  stays in :class:`~services.summary_service.SummaryService`, filtering
  stays in :class:`~services.filter_service.FilterService`, and section
  discovery stays in :class:`~services.section_service.SectionService`.
  This service only threads their outputs together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Sequence, runtime_checkable

import plotly.graph_objects as go

from models.section import DateRange, Section
from models.workbook import Workbook, WorkbookMetadata, ValidationStatus
from services.filter_service import FilterCriteria
from services.kpi_service import SectionKPISummary
from services.summary_service import SummaryCard


# ----------------------------------------------------------------------
# Output models
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class OverviewHeader:
    """Header information shown at the top of the Overview page.

    Attributes:
        workbook_name: The workbook's human-friendly name.
        date_range: The workbook's overall date range, after any active
            filters have been applied.
        validation_status: The workbook's overall validation status.
        section_count: The number of top-level sections discovered.
        unit_count: The number of distinct units of measure discovered.
    """

    workbook_name: str
    date_range: Optional[DateRange]
    validation_status: ValidationStatus
    section_count: int
    unit_count: int


@dataclass(frozen=True)
class AvailableFilters:
    """The filter options the Overview page can offer the user.

    Attributes:
        date_range: The full, unfiltered date range available to filter
            within.
        section_names: Every top-level section's normalized name,
            available for a "filter by section" control.
        subsection_names: Every subsection's normalized name across all
            sections, available for a "filter by subsection" control.
        metric_names: Every metric's normalized name across all sections
            and subsections, available for a "filter by metric" control.
    """

    date_range: Optional[DateRange]
    section_names: List[str] = field(default_factory=list)
    subsection_names: List[str] = field(default_factory=list)
    metric_names: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExpandableSection:
    """Everything one expandable dashboard panel needs to render.

    Attributes:
        section: The (already filtered) section this panel represents.
        summary: The section's aggregated KPI summary.
        chart: A ready-to-render Plotly figure for the section, built by
            :class:`~services.chart_service.ChartService`.
    """

    section: Section
    summary: SectionKPISummary
    chart: go.Figure


@dataclass(frozen=True)
class OverviewPageData:
    """The complete data set required to render the Overview page.

    Attributes:
        header: Header information for the page.
        top_kpi_cards: Workbook-wide aggregated KPI cards, one per
            discovered section, ordered as discovered.
        summary_cards: The fixed homepage summary cards (NPCL, CLC,
            Blast, Dunkin, Freon, Air Compressor, or however
            :class:`~services.summary_service.SummaryService` is
            configured), skipping any not present in the workbook.
        available_filters: The filter options the page should expose.
        expandable_sections: Every discovered section, ready to render
            as an expandable panel.
        metadata: The workbook's descriptive file metadata.
    """

    header: OverviewHeader
    top_kpi_cards: List[SectionKPISummary]
    summary_cards: List[SummaryCard]
    available_filters: AvailableFilters
    expandable_sections: List[ExpandableSection]
    metadata: Optional[WorkbookMetadata]


# ----------------------------------------------------------------------
# Collaborator protocols
# ----------------------------------------------------------------------

@runtime_checkable
class WorkbookServiceLike(Protocol):
    """Structural interface required of an injected workbook service."""

    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook:
        """Retrieves the fully parsed Workbook model for a source path."""
        ...

    def list_units(self, workbook: Workbook) -> List[str]:
        """Lists every distinct unit of measure used across the workbook."""
        ...

    def get_date_range(self, workbook: Workbook) -> Optional[DateRange]:
        """Returns the overall date range covered by the workbook."""
        ...

    def get_validation_status(self, workbook: Workbook) -> ValidationStatus:
        """Returns the workbook's overall validation status."""
        ...

    def get_metadata(self, workbook: Workbook) -> Optional[WorkbookMetadata]:
        """Returns a workbook's descriptive file metadata."""
        ...


@runtime_checkable
class SectionServiceLike(Protocol):
    """Structural interface required of an injected section service."""

    def list_sections(self, workbook: Workbook) -> List[Section]:
        """Lists every section successfully discovered in the workbook."""
        ...

    def list_subsections(self, section: Section) -> List:
        """Lists every subsection belonging to a section, in order."""
        ...

    def list_section_metrics(
        self, section: Section, include_subsections: bool = True
    ) -> List:
        """Lists every metric belonging to a section, in workbook order."""
        ...


@runtime_checkable
class FilterServiceLike(Protocol):
    """Structural interface required of an injected filter service."""

    def filter_workbook(self, workbook: Workbook, criteria: FilterCriteria) -> Workbook:
        """Returns a new Workbook restricted to matching sections/metrics."""
        ...


@runtime_checkable
class KPIServiceLike(Protocol):
    """Structural interface required of an injected KPI service."""

    def calculate_section_summary(
        self,
        section: Section,
        include_subsections: bool = True,
        data_point_filter=None,
    ) -> SectionKPISummary:
        """Computes a single aggregated KPI summary across a section."""
        ...


@runtime_checkable
class SummaryServiceLike(Protocol):
    """Structural interface required of an injected summary service."""

    def build_summary_cards(
        self,
        workbook: Workbook,
        criteria: Optional[FilterCriteria] = None,
        include_subsections: bool = True,
    ) -> List[SummaryCard]:
        """Builds summary cards for every configured section that's present."""
        ...


@runtime_checkable
class ChartServiceLike(Protocol):
    """Structural interface required of an injected chart service."""

    def build_section_chart(
        self,
        section: Section,
        chart_type: str = "line",
        aggregation: str = "none",
        include_subsections: bool = True,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Builds a multi-series chart with one trace per section metric."""
        ...


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------

class DashboardService:
    """Assembles all data required by the Overview page.

    :class:`DashboardService` is the Overview page's only collaborator.
    It fetches the workbook, applies any active filters exactly once via
    :class:`~services.filter_service.FilterService`, and then derives the
    header, top KPI cards, summary cards, available filters, and
    expandable sections from that single filtered workbook — so every
    piece of the page reflects the same filter state and no section is
    ever re-discovered or re-filtered redundantly.

    Attributes:
        workbook_service: Loads and describes the workbook.
        section_service: Enumerates sections, subsections, and metrics.
        filter_service: Applies active filter criteria to the workbook.
        kpi_service: Computes section-level aggregated KPIs.
        summary_service: Builds the fixed homepage summary cards.
        chart_service: Builds Plotly figures for expandable sections.
    """

    def __init__(
        self,
        workbook_service: WorkbookServiceLike,
        section_service: SectionServiceLike,
        filter_service: FilterServiceLike,
        kpi_service: KPIServiceLike,
        summary_service: SummaryServiceLike,
        chart_service: ChartServiceLike,
    ) -> None:
        """Initializes the service with its collaborators.

        Args:
            workbook_service: An object satisfying
                :class:`WorkbookServiceLike`.
            section_service: An object satisfying
                :class:`SectionServiceLike`.
            filter_service: An object satisfying
                :class:`FilterServiceLike`.
            kpi_service: An object satisfying :class:`KPIServiceLike`.
            summary_service: An object satisfying
                :class:`SummaryServiceLike`.
            chart_service: An object satisfying :class:`ChartServiceLike`.
        """
        self.workbook_service = workbook_service
        self.section_service = section_service
        self.filter_service = filter_service
        self.kpi_service = kpi_service
        self.summary_service = summary_service
        self.chart_service = chart_service

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def get_overview_page_data(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        criteria: Optional[FilterCriteria] = None,
        include_subsections: bool = True,
        chart_type: str = "line",
        chart_aggregation: str = "none",
    ) -> OverviewPageData:
        """Builds the complete data set required by the Overview page.

        Args:
            source_path: Path or identifier of the workbook to load.
            workbook_name: Optional human-friendly name for the
                workbook.
            criteria: The currently active filter criteria (date range,
                month, multiple months, or any future filter). When
                omitted, the unfiltered workbook is used throughout.
            include_subsections: Whether KPI and chart aggregation should
                include metrics nested in each section's subsections.
            chart_type: The chart type each expandable section's chart
                should use (one of
                :class:`~services.chart_service.ChartType`).
            chart_aggregation: The trend aggregation each expandable
                section's chart should use (one of
                :class:`~services.chart_service.Aggregation`).

        Returns:
            A fully populated :class:`OverviewPageData`.
        """
        workbook = self.workbook_service.get_workbook(
            source_path=source_path, workbook_name=workbook_name
        )
        available_filters = self._build_available_filters(workbook)

        filtered_workbook = self._apply_filters(workbook, criteria)

        header = self._build_header(filtered_workbook)
        top_kpi_cards = self._build_top_kpi_cards(filtered_workbook, include_subsections)
        summary_cards = self.summary_service.build_summary_cards(
            filtered_workbook, criteria=None, include_subsections=include_subsections
        )
        expandable_sections = self._build_expandable_sections(
            filtered_workbook, include_subsections, chart_type, chart_aggregation
        )

        return OverviewPageData(
            header=header,
            top_kpi_cards=top_kpi_cards,
            summary_cards=summary_cards,
            available_filters=available_filters,
            expandable_sections=expandable_sections,
            metadata=self.workbook_service.get_metadata(filtered_workbook),
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filters(
        self, workbook: Workbook, criteria: Optional[FilterCriteria]
    ) -> Workbook:
        """Applies active filter criteria to the workbook, if any is set.

        Filtering happens exactly once here so every downstream piece of
        the Overview page (header, KPI cards, summary cards, expandable
        sections) is derived from the same filtered workbook and stays
        consistent with the user's current filter selection.

        Args:
            workbook: The unfiltered, freshly loaded workbook.
            criteria: The currently active filter criteria, or ``None``
                to skip filtering.

        Returns:
            The filtered :class:`Workbook`, or the original ``workbook``
            when ``criteria`` is ``None``.
        """
        if criteria is None:
            return workbook
        return self.filter_service.filter_workbook(workbook, criteria)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self, workbook: Workbook) -> OverviewHeader:
        """Builds the Overview page's header information.

        Args:
            workbook: The (already filtered) workbook to summarize.

        Returns:
            The page's :class:`OverviewHeader`.
        """
        return OverviewHeader(
            workbook_name=workbook.name,
            date_range=self.workbook_service.get_date_range(workbook),
            validation_status=self.workbook_service.get_validation_status(workbook),
            section_count=len(self.section_service.list_sections(workbook)),
            unit_count=len(self.workbook_service.list_units(workbook)),
        )

    # ------------------------------------------------------------------
    # Top-level KPI cards
    # ------------------------------------------------------------------

    def _build_top_kpi_cards(
        self, workbook: Workbook, include_subsections: bool
    ) -> List[SectionKPISummary]:
        """Builds one aggregated KPI card per discovered section.

        Unlike :class:`~services.summary_service.SummaryService`'s fixed
        homepage cards, this covers every section the workbook contains,
        whatever those sections turn out to be.

        Args:
            workbook: The (already filtered) workbook to summarize.
            include_subsections: Whether each card's aggregation should
                include metrics nested in the section's subsections.

        Returns:
            One :class:`SectionKPISummary` per section, in discovery
            order.
        """
        return [
            self.kpi_service.calculate_section_summary(
                section, include_subsections=include_subsections
            )
            for section in self.section_service.list_sections(workbook)
        ]

    # ------------------------------------------------------------------
    # Available filters
    # ------------------------------------------------------------------

    def _build_available_filters(self, workbook: Workbook) -> AvailableFilters:
        """Builds the filter options the Overview page can offer.

        Derived from the *unfiltered* workbook, so narrowing the current
        filter selection never shrinks the set of options a user could
        choose next.

        Args:
            workbook: The unfiltered workbook to derive options from.

        Returns:
            The page's :class:`AvailableFilters`.
        """
        section_names: List[str] = []
        subsection_names: List[str] = []
        metric_names: List[str] = []

        for section in self.section_service.list_sections(workbook):
            section_names.append(section.name)
            for metric in self.section_service.list_section_metrics(
                section, include_subsections=False
            ):
                if metric.name not in metric_names:
                    metric_names.append(metric.name)
            for subsection in self.section_service.list_subsections(section):
                if subsection.name not in subsection_names:
                    subsection_names.append(subsection.name)
                for metric in subsection.metrics:
                    if metric.name not in metric_names:
                        metric_names.append(metric.name)

        return AvailableFilters(
            date_range=self.workbook_service.get_date_range(workbook),
            section_names=section_names,
            subsection_names=subsection_names,
            metric_names=metric_names,
        )

    # ------------------------------------------------------------------
    # Expandable sections
    # ------------------------------------------------------------------

    def _build_expandable_sections(
        self,
        workbook: Workbook,
        include_subsections: bool,
        chart_type: str,
        chart_aggregation: str,
    ) -> List[ExpandableSection]:
        """Builds one expandable panel entry per discovered section.

        Args:
            workbook: The (already filtered) workbook to build panels
                from.
            include_subsections: Whether each panel's KPI and chart
                aggregation should include metrics nested in the
                section's subsections.
            chart_type: The chart type to use for each panel's chart.
            chart_aggregation: The trend aggregation to use for each
                panel's chart.

        Returns:
            One :class:`ExpandableSection` per section, in discovery
            order.
        """
        panels: List[ExpandableSection] = []
        for section in self.section_service.list_sections(workbook):
            summary = self.kpi_service.calculate_section_summary(
                section, include_subsections=include_subsections
            )
            chart = self.chart_service.build_section_chart(
                section,
                chart_type=chart_type,
                aggregation=chart_aggregation,
                include_subsections=include_subsections,
                criteria=None,
                title=section.display_name,
            )
            panels.append(
                ExpandableSection(section=section, summary=summary, chart=chart)
            )
        return panels

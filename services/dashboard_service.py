"""
services/dashboard_service.py — INSTRUMENTED FOR RUNTIME HANG DIAGNOSIS
(TEMPORARY LOGGING)

All original business logic, models, and return values are unchanged.
Only ENTER/EXIT/BEFORE/AFTER debug logging has been added. Remove all
lines marked "# DEBUG" once the hang is diagnosed.
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Sequence, runtime_checkable

import plotly.graph_objects as go

from models.section import DateRange, Section
from models.workbook import Workbook, WorkbookMetadata, ValidationStatus
from services.filter_service import FilterCriteria
from services.kpi_service import SectionKPISummary
from services.summary_service import SummaryCard


# ---------------------------------------------------------------------
# DEBUG: logging helper (temporary)
# ---------------------------------------------------------------------
def _dbg(msg: str) -> None:  # DEBUG
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)  # DEBUG


# ----------------------------------------------------------------------
# Output models
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class OverviewHeader:
    workbook_name: str
    date_range: Optional[DateRange]
    validation_status: ValidationStatus
    section_count: int
    unit_count: int


@dataclass(frozen=True)
class AvailableFilters:
    date_range: Optional[DateRange]
    section_names: List[str] = field(default_factory=list)
    subsection_names: List[str] = field(default_factory=list)
    metric_names: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExpandableSection:
    section: Section
    summary: SectionKPISummary
    chart: go.Figure


@dataclass(frozen=True)
class OverviewPageData:
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
    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook: ...

    def list_units(self, workbook: Workbook) -> List[str]: ...

    def get_date_range(self, workbook: Workbook) -> Optional[DateRange]: ...

    def get_validation_status(self, workbook: Workbook) -> ValidationStatus: ...

    def get_metadata(self, workbook: Workbook) -> Optional[WorkbookMetadata]: ...


@runtime_checkable
class SectionServiceLike(Protocol):
    def list_sections(self, workbook: Workbook) -> List[Section]: ...

    def list_subsections(self, section: Section) -> List: ...

    def list_section_metrics(
        self, section: Section, include_subsections: bool = True
    ) -> List: ...


@runtime_checkable
class FilterServiceLike(Protocol):
    def filter_workbook(self, workbook: Workbook, criteria: FilterCriteria) -> Workbook: ...


@runtime_checkable
class KPIServiceLike(Protocol):
    def calculate_section_summary(
        self,
        section: Section,
        include_subsections: bool = True,
        data_point_filter=None,
    ) -> SectionKPISummary: ...


@runtime_checkable
class SummaryServiceLike(Protocol):
    def build_summary_cards(
        self,
        workbook: Workbook,
        criteria: Optional[FilterCriteria] = None,
        include_subsections: bool = True,
    ) -> List[SummaryCard]: ...


@runtime_checkable
class ChartServiceLike(Protocol):
    def build_section_chart(
        self,
        section: Section,
        chart_type: str = "line",
        aggregation: str = "none",
        include_subsections: bool = True,
        criteria: Optional[FilterCriteria] = None,
        title: Optional[str] = None,
    ) -> go.Figure: ...


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------

class DashboardService:
    """Assembles all data required by the Overview page."""

    def __init__(
        self,
        workbook_service: WorkbookServiceLike,
        section_service: SectionServiceLike,
        filter_service: FilterServiceLike,
        kpi_service: KPIServiceLike,
        summary_service: SummaryServiceLike,
        chart_service: ChartServiceLike,
    ) -> None:
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
        _dbg("ENTER services.dashboard_service.DashboardService.get_overview_page_data")  # DEBUG
        try:
            _dbg("BEFORE workbook_service.get_workbook()")  # DEBUG
            workbook = self.workbook_service.get_workbook(
                source_path=source_path, workbook_name=workbook_name
            )
            _dbg("AFTER workbook_service.get_workbook()")  # DEBUG
            _dbg(f"Workbook loaded: name={workbook.name}, "
                 f"available_sheets={workbook.available_sheets}, "
                 f"validation_status={workbook.validation_status}")  # DEBUG

            _dbg("BEFORE _build_available_filters()")  # DEBUG
            available_filters = self._build_available_filters(workbook)
            _dbg("AFTER _build_available_filters()")  # DEBUG

            _dbg("BEFORE _apply_filters()")  # DEBUG
            filtered_workbook = self._apply_filters(workbook, criteria)
            _dbg("AFTER _apply_filters()")  # DEBUG

            _dbg("BEFORE _build_header()")  # DEBUG
            header = self._build_header(filtered_workbook)
            _dbg("AFTER _build_header()")  # DEBUG

            _dbg("BEFORE _build_top_kpi_cards()")  # DEBUG
            top_kpi_cards = self._build_top_kpi_cards(filtered_workbook, include_subsections)
            _dbg("AFTER _build_top_kpi_cards()")  # DEBUG

            _dbg("BEFORE summary_service.build_summary_cards()")  # DEBUG
            summary_cards = self.summary_service.build_summary_cards(
                filtered_workbook, criteria=None, include_subsections=include_subsections
            )
            _dbg("AFTER summary_service.build_summary_cards()")  # DEBUG

            _dbg("BEFORE _build_expandable_sections()")  # DEBUG
            expandable_sections = self._build_expandable_sections(
                filtered_workbook, include_subsections, chart_type, chart_aggregation
            )
            _dbg("AFTER _build_expandable_sections()")  # DEBUG

            _dbg("BEFORE workbook_service.get_metadata()")  # DEBUG
            metadata = self.workbook_service.get_metadata(filtered_workbook)
            _dbg("AFTER workbook_service.get_metadata()")  # DEBUG

            result = OverviewPageData(
                header=header,
                top_kpi_cards=top_kpi_cards,
                summary_cards=summary_cards,
                available_filters=available_filters,
                expandable_sections=expandable_sections,
                metadata=metadata,
            )
            _dbg("Final OverviewPageData created successfully")  # DEBUG
            _dbg("EXIT services.dashboard_service.DashboardService.get_overview_page_data (success)")  # DEBUG
            return result
        except Exception:
            _dbg("EXCEPTION in DashboardService.get_overview_page_data")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filters(
        self, workbook: Workbook, criteria: Optional[FilterCriteria]
    ) -> Workbook:
        _dbg("ENTER DashboardService._apply_filters")  # DEBUG
        try:
            if criteria is None:
                _dbg("No criteria supplied; skipping filter_service call")  # DEBUG
                _dbg("EXIT DashboardService._apply_filters (unfiltered)")  # DEBUG
                return workbook
            _dbg("BEFORE filter_service.filter_workbook()")  # DEBUG
            result = self.filter_service.filter_workbook(workbook, criteria)
            _dbg("AFTER filter_service.filter_workbook()")  # DEBUG
            _dbg("EXIT DashboardService._apply_filters (filtered)")  # DEBUG
            return result
        except Exception:
            _dbg("EXCEPTION in DashboardService._apply_filters")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self, workbook: Workbook) -> OverviewHeader:
        _dbg("ENTER DashboardService._build_header")  # DEBUG
        try:
            result = OverviewHeader(
                workbook_name=workbook.name,
                date_range=self.workbook_service.get_date_range(workbook),
                validation_status=self.workbook_service.get_validation_status(workbook),
                section_count=len(self.section_service.list_sections(workbook)),
                unit_count=len(self.workbook_service.list_units(workbook)),
            )
            _dbg("EXIT DashboardService._build_header")  # DEBUG
            return result
        except Exception:
            _dbg("EXCEPTION in DashboardService._build_header")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

    # ------------------------------------------------------------------
    # Top-level KPI cards
    # ------------------------------------------------------------------

    def _build_top_kpi_cards(
        self, workbook: Workbook, include_subsections: bool
    ) -> List[SectionKPISummary]:
        _dbg("ENTER DashboardService._build_top_kpi_cards")  # DEBUG
        try:
            sections = self.section_service.list_sections(workbook)
            _dbg(f"Found {len(sections)} section(s) for top KPI cards")  # DEBUG
            result = [
                self.kpi_service.calculate_section_summary(
                    section, include_subsections=include_subsections
                )
                for section in sections
            ]
            _dbg("EXIT DashboardService._build_top_kpi_cards")  # DEBUG
            return result
        except Exception:
            _dbg("EXCEPTION in DashboardService._build_top_kpi_cards")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

    # ------------------------------------------------------------------
    # Available filters
    # ------------------------------------------------------------------

    def _build_available_filters(self, workbook: Workbook) -> AvailableFilters:
        _dbg("ENTER DashboardService._build_available_filters")  # DEBUG
        try:
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

            result = AvailableFilters(
                date_range=self.workbook_service.get_date_range(workbook),
                section_names=section_names,
                subsection_names=subsection_names,
                metric_names=metric_names,
            )
            _dbg("EXIT DashboardService._build_available_filters")  # DEBUG
            return result
        except Exception:
            _dbg("EXCEPTION in DashboardService._build_available_filters")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

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
        _dbg("ENTER DashboardService._build_expandable_sections")  # DEBUG
        try:
            panels: List[ExpandableSection] = []
            sections = self.section_service.list_sections(workbook)
            _dbg(f"Building {len(sections)} expandable section(s)")  # DEBUG
            for section in sections:
                _dbg(f"BEFORE kpi_service.calculate_section_summary() for section={section.name}")  # DEBUG
                summary = self.kpi_service.calculate_section_summary(
                    section, include_subsections=include_subsections
                )
                _dbg(f"AFTER kpi_service.calculate_section_summary() for section={section.name}")  # DEBUG

                _dbg(f"BEFORE chart_service.build_section_chart() for section={section.name}")  # DEBUG
                chart = self.chart_service.build_section_chart(
                    section,
                    chart_type=chart_type,
                    aggregation=chart_aggregation,
                    include_subsections=include_subsections,
                    criteria=None,
                    title=section.display_name,
                )
                _dbg(f"AFTER chart_service.build_section_chart() for section={section.name}")  # DEBUG

                panels.append(
                    ExpandableSection(section=section, summary=summary, chart=chart)
                )
            _dbg("EXIT DashboardService._build_expandable_sections")  # DEBUG
            return panels
        except Exception:
            _dbg("EXCEPTION in DashboardService._build_expandable_sections")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

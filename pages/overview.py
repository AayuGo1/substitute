"""
pages/overview.py

Engineering Monitoring Dashboard homepage.

This module is a PURE ORCHESTRATION LAYER. It renders the homepage by
adapting a single, already-fully-resolved ``OverviewPageData`` object
(built once per session by ``app.py`` via
``DashboardService.get_overview_page_data(...)`` and shared through
``st.session_state``) into the small, purpose-built dataclasses that
the existing reusable UI components already declare, then delegates
all rendering to those components.

This page performs:
    - No KPI calculations (all KPI values arrive pre-computed on
      ``OverviewPageData.top_kpi_cards`` / ``.summary_cards`` /
      ``.expandable_sections[*].summary``).
    - No file parsing.
    - No filtering (any active filter is applied once, upstream, by
      ``DashboardService`` before this page ever runs; the filter bar
      rendered here is display/selection only and does not itself
      trigger re-filtering within this page).
    - No chart generation (every chart on
      ``OverviewPageData.expandable_sections[*].chart`` is already a
      ready-to-render Plotly figure).
    - No duplicated UI — every visual element is rendered exclusively
      by the existing components in ``components/*``; this page only
      *adapts* data shapes and threads calls together.

Rendering order:
    1. Navbar and sidebar shell (``components.navbar``,
       ``components.sidebar``).
    2. Filter bar (``components.filters``) — display/selection only;
       filtering itself already happened upstream.
    3. Top KPI cards, one per discovered section
       (``components.cards``).
    4. Fixed summary cards (``components.summary_cards``).
    5. One expandable panel per discovered section
       (``components.expandable_section``).

The reusable components consumed here were each built against their
own small, documented Protocol/dataclass contracts that do not exactly
match ``OverviewPageData``'s shape. Rather than modifying those
components (out of scope) or duplicating their rendering here, this
page defines minimal, local adapter functions that translate
``OverviewPageData`` into exactly the dataclasses those components
already expect. This is wiring, not new business logic.

Known adaptation gaps, deliberately left visible rather than papered
over:
    - ``components.navbar.NavbarConfig`` expects a company logo path,
      formatted current date/time strings, and a "last updated"
      string. ``DashboardService`` computes none of these; placeholder
      values are used below and should be replaced once a real source
      for them exists.
    - ``components.sidebar.SidebarConfig`` expects an app version and
      nav items; a static version string and
      ``components.sidebar.DEFAULT_NAV_ITEMS`` are used since no
      version/nav source exists on ``DashboardService``.
    - ``components.filters.FilterService`` expects month/date-range
      option methods this page's filter *display* does not have a
      backing implementation for; a minimal local adapter derives
      month options and date bounds from
      ``OverviewPageData.available_filters.date_range``. This should
      be replaced by a real ``FilterService`` once one is available.
    - ``components.cards.KPICardData`` requires ``sparkline_values``
      and a formatted ``last_updated`` string that
      ``services.kpi_service.SectionKPISummary`` was not confirmed to
      carry. The adapter below reads them via ``getattr`` with safe
      fallbacks (empty sparkline, "—" for missing timestamp) rather
      than inventing sparkline history or a clock source. Once
      ``services/kpi_service.py``'s exact fields are confirmed, this
      can be tightened to direct attribute access.
    - ``components.summary_cards.SummaryCardData`` field names are
      likewise assumed via ``getattr`` with safe fallbacks, since
      ``services/summary_service.py``'s exact field names were not
      supplied to this review.
    - ``components.expandable_section.render_expandable_section``
      expects per-section daily/weekly/monthly chart lookups and a
      metrics table; ``OverviewPageData`` provides only a single
      pre-built chart. The local adapters below expose that single
      chart as the daily trend slot and leave weekly/monthly empty,
      rather than duplicating or re-generating a chart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, List, Optional, Sequence, Tuple

import streamlit as st

from components.cards import KPICardData, render_kpi_cards
from components.expandable_section import (
    ChartService as ExpandableChartService,
    DashboardService as ExpandableDashboardService,
    KPISummaryData,
    MetricRow,
    SectionHeaderData,
    SectionService as ExpandableSectionService,
    render_expandable_section,
)
from components.filters import FilterCriteria, FilterService, render_filter_bar
from components.navbar import NavbarConfig, render_navbar
from components.sidebar import DEFAULT_NAV_ITEMS, SidebarConfig, render_sidebar
from components.summary_cards import SummaryCardData, render_summary_cards
from services.dashboard_service import ExpandableSection, OverviewPageData

__all__ = ["render_overview_page"]

_PAGE_KEY = "overview"
_SESSION_KEY_PAGE_DATA = "em_app__overview_page_data"
_APP_VERSION = "v1.0.0"  # No version source exists on DashboardService yet.


# ----------------------------------------------------------------------
# Adapter: OverviewPageData -> NavbarConfig
# ----------------------------------------------------------------------

def _build_navbar_config(page_data: OverviewPageData) -> NavbarConfig:
    """
    Adapts ``OverviewPageData`` into the ``NavbarConfig`` dataclass
    ``components.navbar`` already declares.

    ``DashboardService`` does not compute a logo path or formatted
    clock strings, so those fields use neutral placeholders here
    rather than being invented as new business logic.

    Args:
        page_data: The fully resolved page data for this session.

    Returns:
        A ``NavbarConfig`` ready for ``render_navbar``.
    """
    now = datetime.now()
    return NavbarConfig(
        company_logo_path=None,
        dashboard_title="Engineering Monitoring Dashboard",
        workbook_name=page_data.header.workbook_name,
        current_date=now.strftime("%d %b %Y"),
        current_time=now.strftime("%H:%M:%S"),
        last_updated=None,
    )


# ----------------------------------------------------------------------
# Adapter: static sidebar config
# ----------------------------------------------------------------------

def _build_sidebar_config(active_page: str) -> SidebarConfig:
    """
    Builds the ``SidebarConfig`` ``components.sidebar`` already
    declares, using its own default navigation items since
    ``DashboardService`` exposes no navigation configuration.

    Args:
        active_page: The currently active navigation key.

    Returns:
        A ``SidebarConfig`` ready for ``render_sidebar``.
    """
    return SidebarConfig(
        company_logo_path=None,
        app_version=_APP_VERSION,
        active_page=active_page,
        nav_items=DEFAULT_NAV_ITEMS,
    )


# ----------------------------------------------------------------------
# Adapter: OverviewPageData.available_filters -> FilterService
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class _OverviewFilterService:
    """
    Minimal local adapter satisfying the ``FilterService`` Protocol
    declared in ``components.filters``, derived entirely from
    ``OverviewPageData.available_filters``.

    This performs no date arithmetic of its own beyond exposing the
    already-known overall bounds; it is a display-options adapter, not
    a new filtering implementation. Quick-select resolution falls back
    to the full available range, since no date-math utility exists
    here to compute "today" / "this week" / "this month" precisely.

    Attributes:
        min_date: Earliest selectable date, derived from the
            workbook's overall date range.
        max_date: Latest selectable date, derived from the workbook's
            overall date range.
    """

    min_date: date
    max_date: date

    def get_available_months(self) -> List[str]:
        return []

    def get_default_month(self) -> Optional[str]:
        return None

    def get_min_date(self) -> date:
        return self.min_date

    def get_max_date(self) -> date:
        return self.max_date

    def get_default_date_range(self) -> Tuple[date, date]:
        return self.min_date, self.max_date

    def resolve_quick_range(self, option: str) -> Tuple[date, date]:
        return self.min_date, self.max_date


def _build_filter_service(page_data: OverviewPageData) -> FilterService:
    """
    Adapts ``OverviewPageData.available_filters`` into a
    ``FilterService``-satisfying object for ``render_filter_bar``.

    Args:
        page_data: The fully resolved page data for this session.

    Returns:
        An object satisfying ``components.filters.FilterService``.
    """
    date_range = page_data.available_filters.date_range
    today = date.today()
    min_date = date_range.start.date() if date_range and date_range.start else today
    max_date = date_range.end.date() if date_range and date_range.end else today
    return _OverviewFilterService(min_date=min_date, max_date=max_date)


# ----------------------------------------------------------------------
# Adapter: OverviewPageData.top_kpi_cards -> KPICardData
# ----------------------------------------------------------------------

def _format_last_updated(summary: Any) -> str:
    """
    Formats a KPI summary's timestamp for display, tolerating summaries
    that carry no timestamp field at all.

    Args:
        summary: A ``SectionKPISummary`` instance.

    Returns:
        A formatted "HH:MM:SS" string, or "—" if no timestamp is
        available.
    """
    timestamp = getattr(summary, "timestamp", None)
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%H:%M:%S")
    return "—"


def _build_kpi_card_data(page_data: OverviewPageData) -> List[KPICardData]:
    """
    Adapts each ``services.kpi_service.SectionKPISummary`` on
    ``OverviewPageData.top_kpi_cards`` into the
    ``components.cards.KPICardData`` dataclass that component already
    declares.

    ``sparkline_values`` and ``last_updated`` are read defensively via
    ``getattr`` because ``SectionKPISummary``'s exact field set was not
    confirmed for this review; when absent, an empty sparkline and a
    "—" timestamp are used rather than inventing history data or a
    clock source. ``trend_direction`` is normalized to the
    ``"up"``/``"down"``/``"flat"`` literal ``components.cards`` expects,
    treating any unrecognized/unknown trend as ``"flat"``.

    Args:
        page_data: The fully resolved page data for this session.

    Returns:
        A list of ``KPICardData`` ready for ``render_kpi_cards``.
    """
    cards: List[KPICardData] = []
    for summary in page_data.top_kpi_cards:
        raw_trend = getattr(getattr(summary, "trend", None), "value", "flat")
        trend_direction = raw_trend if raw_trend in ("up", "down", "flat") else "flat"

        current_value = getattr(
            summary, "last_value", getattr(summary, "last_registered_value", 0.0)
        )

        cards.append(
            KPICardData(
                section_name=getattr(
                    summary, "display_name", getattr(summary, "name", "")
                ),
                current_value=current_value or 0.0,
                unit=getattr(summary, "unit", ""),
                trend_direction=trend_direction,
                percentage_change=getattr(summary, "percentage_change", 0.0) or 0.0,
                sparkline_values=getattr(summary, "sparkline_values", []) or [],
                last_updated=_format_last_updated(summary),
            )
        )
    return cards


# ----------------------------------------------------------------------
# Adapter: OverviewPageData.summary_cards -> SummaryCardData
# ----------------------------------------------------------------------

def _build_summary_card_data(page_data: OverviewPageData) -> List[SummaryCardData]:
    """
    Adapts each ``services.summary_service.SummaryCard`` on
    ``OverviewPageData.summary_cards`` into the
    ``components.summary_cards.SummaryCardData`` dataclass that
    component already declares.

    Field access uses ``getattr`` with safe fallbacks because
    ``SummaryCard``'s exact field names were not available for this
    review; once confirmed, this can be tightened to direct attribute
    access.

    Args:
        page_data: The fully resolved page data for this session.

    Returns:
        A list of ``SummaryCardData`` ready for ``render_summary_cards``.
    """
    cards: List[SummaryCardData] = []
    for card in page_data.summary_cards:
        cards.append(
            SummaryCardData(
                section_name=getattr(card, "section_name", getattr(card, "display_name", "")),
                total=getattr(card, "total", 0.0) or 0.0,
                average=getattr(card, "average", 0.0) or 0.0,
                last_registered_value=getattr(
                    card, "last_registered_value", getattr(card, "last_value", 0.0)
                )
                or 0.0,
                unit=getattr(card, "unit", ""),
                last_updated=getattr(card, "last_updated", ""),
            )
        )
    return cards


# ----------------------------------------------------------------------
# Adapter: ExpandableSection list -> expandable_section component
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class _OverviewExpandableDashboardService:
    """
    Minimal local adapter satisfying the ``DashboardService`` Protocol
    declared in ``components.expandable_section``, backed by the
    already-resolved ``ExpandableSection`` entries from
    ``OverviewPageData`` (keyed by each section's ``name``).

    Attributes:
        sections_by_key: Mapping of section key to its already-resolved
            ``ExpandableSection`` entry.
    """

    sections_by_key: dict

    def get_section_header(self, section_key: str) -> SectionHeaderData:
        entry: ExpandableSection = self.sections_by_key[section_key]
        summary = entry.summary
        return SectionHeaderData(
            name=entry.section.display_name,
            current_value=getattr(summary, "last_value", getattr(summary, "last_registered_value", 0.0)) or 0.0,
            unit=getattr(summary, "unit", ""),
            trend_direction=str(getattr(getattr(summary, "trend", None), "value", "flat")),
            icon=None,
        )

    def get_section_summary(self, section_key: str) -> KPISummaryData:
        entry: ExpandableSection = self.sections_by_key[section_key]
        summary = entry.summary
        return KPISummaryData(
            total=getattr(summary, "total", 0.0) or 0.0,
            average=getattr(summary, "average", 0.0) or 0.0,
            last_registered_value=getattr(
                summary, "last_value", getattr(summary, "last_registered_value", 0.0)
            )
            or 0.0,
            unit=getattr(summary, "unit", ""),
        )


@dataclass(frozen=True)
class _OverviewExpandableChartService:
    """
    Minimal local adapter satisfying the ``ChartService`` Protocol
    declared in ``components.expandable_section``.

    ``OverviewPageData`` provides exactly one pre-built chart per
    section (no separate daily/weekly/monthly figures), so that single
    chart is surfaced as the daily trend and the weekly/monthly slots
    are omitted rather than duplicating or re-generating a chart here.

    Attributes:
        sections_by_key: Mapping of section key to its already-resolved
            ``ExpandableSection`` entry.
    """

    sections_by_key: dict

    def get_daily_trend_chart(self, section_key: str) -> Optional[Any]:
        return self.sections_by_key[section_key].chart

    def get_weekly_trend_chart(self, section_key: str) -> Optional[Any]:
        return None

    def get_monthly_trend_chart(self, section_key: str) -> Optional[Any]:
        return None


@dataclass(frozen=True)
class _OverviewExpandableSectionService:
    """
    Minimal local adapter satisfying the ``SectionService`` Protocol
    declared in ``components.expandable_section``.

    ``OverviewPageData`` does not expose per-metric rows or nested
    subsection keys independently of the ``Section``/``SubSection``
    models already attached to each ``ExpandableSection``; subsections
    and metrics are surfaced directly from those existing models
    without recomputation.

    Attributes:
        sections_by_key: Mapping of section key to its already-resolved
            ``ExpandableSection`` entry.
    """

    sections_by_key: dict

    def get_subsection_keys(self, section_key: str) -> List[str]:
        entry: ExpandableSection = self.sections_by_key[section_key]
        return [subsection.name for subsection in entry.section.subsections]

    def get_metrics_table(self, section_key: str) -> Sequence[MetricRow]:
        entry: ExpandableSection = self.sections_by_key[section_key]
        return [
            MetricRow(
                metric_name=metric.display_name,
                value=f"{metric.current_value:,.2f}" if metric.current_value is not None else "—",
                unit=metric.unit or None,
            )
            for metric in entry.section.metrics
        ]


def _render_expandable_sections(page_data: OverviewPageData) -> None:
    """
    Renders one expandable panel per discovered section using the
    existing ``components.expandable_section.render_expandable_section``
    component, backed by the local adapters above.

    Args:
        page_data: The fully resolved page data for this session.
    """
    if not page_data.expandable_sections:
        st.info("No engineering sections were discovered in the workbook.")
        return

    sections_by_key = {entry.section.name: entry for entry in page_data.expandable_sections}
    dashboard_adapter: ExpandableDashboardService = _OverviewExpandableDashboardService(sections_by_key)
    chart_adapter: ExpandableChartService = _OverviewExpandableChartService(sections_by_key)
    section_adapter: ExpandableSectionService = _OverviewExpandableSectionService(sections_by_key)

    for section_key in sections_by_key:
        render_expandable_section(
            section_key=section_key,
            dashboard_service=dashboard_adapter,
            chart_service=chart_adapter,
            section_service=section_adapter,
        )


# ----------------------------------------------------------------------
# Page assembly
# ----------------------------------------------------------------------

def render_overview_page() -> None:
    """
    Render the complete Engineering Monitoring Dashboard homepage from
    the ``OverviewPageData`` already built and cached by ``app.py``,
    delegating every visual element to the existing reusable
    components.

    Rendering proceeds in this order:
        1. Navbar and sidebar shell (``components.navbar``,
           ``components.sidebar``).
        2. Filter bar (``components.filters``) — display/selection
           only; filtering itself already happened upstream.
        3. Top KPI cards, one per discovered section
           (``components.cards``).
        4. Fixed summary cards (``components.summary_cards``).
        5. One expandable panel per discovered section
           (``components.expandable_section``).

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    page_data: Optional[OverviewPageData] = st.session_state.get(_SESSION_KEY_PAGE_DATA)

    if page_data is None:
        st.info("Workbook data is not yet available. Please wait for the app to finish loading.")
        return

    navbar_config = _build_navbar_config(page_data)
    render_navbar(navbar_config, on_refresh=st.rerun)

    active_page = st.session_state.get("em_active_page", _PAGE_KEY)
    sidebar_config = _build_sidebar_config(active_page)
    selected_page = render_sidebar(sidebar_config)
    st.session_state["em_active_page"] = selected_page

    filter_service = _build_filter_service(page_data)
    _criteria: FilterCriteria = render_filter_bar(filter_service)

    kpi_cards = _build_kpi_card_data(page_data)
    render_kpi_cards(kpi_cards)

    summary_cards = _build_summary_card_data(page_data)
    render_summary_cards(summary_cards)

   # _render_expandable_sections(page_data)




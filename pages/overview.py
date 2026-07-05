"""
pages/overview.py

Engineering Monitoring Dashboard homepage.

This module is a PURE ORCHESTRATION LAYER. It assembles the homepage
by wiring together already-complete services and UI components in the
required order:

    1. Navbar
    2. Filter Bar
    3. Top KPI Cards        (one per major section discovered from Sheet 1)
    4. Summary Cards        (configured sections: NPCL, CLC, Blast, Dunkin,
                             Freon, Air Compressor)
    5. Expandable Engineering Sections (one per discovered section)

This page:
    - Contains no KPI calculations.
    - Performs no file parsing.
    - Performs no filtering.
    - Performs no chart generation.
    - Contains no duplicated business logic.

Every data value rendered on this page originates from
``DashboardService`` (directly, or via the ``FilterCriteria`` it is
given). Section discovery is fully dynamic: the number and identity of
KPI cards and expandable sections is driven entirely by whatever
``DashboardService.get_section_keys()`` returns, never hardcoded here.
The configured summary sections (NPCL, CLC, Blast, Dunkin, Freon,
Air Compressor) are requested from ``DashboardService`` as well; if a
configured section is absent from the workbook, ``DashboardService``
simply omits it and this page renders one fewer summary card — no
presence-checking logic lives on this page.

Expected collaborators
---------------------------------------------------------------
This page depends only on the following, all assumed complete:

    layout.py (project-level layout helpers)
        configure_page() -> None
            Applies global Streamlit page configuration (wide layout,
            page title/icon, etc.).
        main_container() -> ContextManager[None]
            Context manager wrapping the primary content area so
            spacing/max-width rules stay centralized in one place
            rather than duplicated per page.

    components.navbar.render_navbar
    components.sidebar.render_sidebar
    components.filters.render_filter_bar
    components.cards.render_kpi_cards
    components.summary_cards.render_summary_cards
    components.expandable_section.render_expandable_section

    services.dashboard_service.DashboardService
        get_navbar_config() -> NavbarConfig
        get_sidebar_config(active_page: str) -> SidebarConfig
        get_kpi_cards(criteria: FilterCriteria) -> Sequence[KPICardData]
        get_summary_cards(criteria: FilterCriteria) -> Sequence[SummaryCardData]
        get_section_keys(criteria: FilterCriteria) -> Sequence[str]
        get_section_header(section_key: str) -> SectionHeaderData
        get_section_summary(section_key: str) -> KPISummaryData

    services.filter_service.FilterService
        (as consumed by components.filters.render_filter_bar)

    services.chart_service.ChartService
        (as consumed by components.expandable_section.render_expandable_section)

    services.section_service.SectionService
        (as consumed by components.expandable_section.render_expandable_section)

If any concrete service/helper signature differs from the above, only
the small adapter calls in ``_build_services`` need to change — the
render flow itself stays the same.
"""

from __future__ import annotations

from typing import NamedTuple

import streamlit as st

import layout
from components.cards import render_kpi_cards
from components.expandable_section import render_expandable_section
from components.filters import FilterCriteria, render_filter_bar
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.summary_cards import render_summary_cards
from services.chart_service import ChartService
from services.dashboard_service import DashboardService
from services.filter_service import FilterService
from services.section_service import SectionService

__all__ = ["render_overview_page"]

_PAGE_KEY = "overview"


class _PageServices(NamedTuple):
    """
    Immutable bundle of the backend services this page orchestrates.

    Grouping the services in one container keeps the page's function
    signatures small and makes it trivial to substitute alternative
    implementations (e.g. for testing) without touching render logic.

    Attributes:
        dashboard_service: Supplies navbar/sidebar configuration, KPI
            and summary card data, and section header/summary values.
        filter_service: Supplies filter bar options, bounds, and
            quick-range resolution.
        chart_service: Supplies pre-built daily/weekly/monthly trend
            charts for each section.
        section_service: Supplies subsection discovery and dynamic
            metrics table rows for each section.
    """

    dashboard_service: DashboardService
    filter_service: FilterService
    chart_service: ChartService
    section_service: SectionService


def _build_services() -> _PageServices:
    """
    Instantiate the backend services this page depends on.

    This is the single place where concrete service classes are
    constructed, keeping the rest of the page dependent only on the
    service abstractions consumed by the UI components (Dependency
    Inversion). No business logic is implemented here — only wiring.

    Returns:
        A ``_PageServices`` bundle ready to be passed to the render
        functions.
    """
    return _PageServices(
        dashboard_service=DashboardService(),
        filter_service=FilterService(),
        chart_service=ChartService(),
        section_service=SectionService(),
    )


def _render_navbar_and_sidebar(services: _PageServices) -> None:
    """
    Render the navbar and sidebar shell shared by the homepage.

    The sidebar's selection is stored in ``st.session_state`` so page
    navigation state persists across reruns; this page does not
    perform any routing beyond reading that state back for the sidebar
    highlight, since routing between pages is Streamlit's own
    multipage mechanism.

    Args:
        services: The bundle of backend services for this page.
    """
    navbar_config = services.dashboard_service.get_navbar_config()
    render_navbar(navbar_config, on_refresh=st.rerun)

    active_page = st.session_state.get("em_active_page", _PAGE_KEY)
    sidebar_config = services.dashboard_service.get_sidebar_config(active_page)
    selected_page = render_sidebar(sidebar_config)
    st.session_state["em_active_page"] = selected_page


def _render_filters(services: _PageServices) -> FilterCriteria:
    """
    Render the filter bar and return the resulting filter criteria.

    Args:
        services: The bundle of backend services for this page.

    Returns:
        The ``FilterCriteria`` reflecting the current filter bar state,
        to be passed to every subsequent ``DashboardService`` call on
        this page.
    """
    return render_filter_bar(services.filter_service)


def _render_top_kpi_row(services: _PageServices, criteria: FilterCriteria) -> None:
    """
    Render the top row of KPI cards, one per major engineering section
    discovered from Sheet 1.

    The set of cards is fully dynamic: this function makes no
    assumption about which or how many sections exist. All card values
    are pre-computed by ``DashboardService``.

    Args:
        services: The bundle of backend services for this page.
        criteria: The current filter criteria to scope KPI values by.
    """
    kpi_cards = services.dashboard_service.get_kpi_cards(criteria)
    render_kpi_cards(kpi_cards)


def _render_summary_row(services: _PageServices, criteria: FilterCriteria) -> None:
    """
    Render the second row of configured summary cards (NPCL, CLC,
    Blast, Dunkin, Freon, Air Compressor).

    ``DashboardService`` is responsible for omitting any configured
    section that is absent from the workbook; this page performs no
    presence-checking of its own.

    Args:
        services: The bundle of backend services for this page.
        criteria: The current filter criteria to scope summary values
            by.
    """
    summary_cards = services.dashboard_service.get_summary_cards(criteria)
    render_summary_cards(summary_cards)


def _render_expandable_sections(services: _PageServices, criteria: FilterCriteria) -> None:
    """
    Render one expandable engineering section per section discovered
    by ``DashboardService``.

    The number and identity of sections is fully dynamic. Each
    section's own header, summary, charts, subsections, and metrics
    table are resolved lazily by ``render_expandable_section`` via the
    three injected services.

    Args:
        services: The bundle of backend services for this page.
        criteria: The current filter criteria used to discover the
            active set of sections.
    """
    section_keys = services.dashboard_service.get_section_keys(criteria)

    if not section_keys:
        st.info("No engineering sections were discovered in the workbook.")
        return

    for section_key in section_keys:
        render_expandable_section(
            section_key=section_key,
            dashboard_service=services.dashboard_service,
            chart_service=services.chart_service,
            section_service=services.section_service,
        )


def render_overview_page() -> None:
    """
    Assemble and render the complete Engineering Monitoring Dashboard
    homepage.

    Rendering proceeds strictly in this order:
        1. Navbar (and sidebar shell).
        2. Filter bar, producing the ``FilterCriteria`` used by every
           subsequent section on the page.
        3. Top KPI cards — one per major section discovered from
           Sheet 1.
        4. Summary cards for the configured sections (NPCL, CLC,
           Blast, Dunkin, Freon, Air Compressor).
        5. One expandable engineering section per section discovered
           by the backend.

    This function performs no calculation, parsing, filtering, or
    chart generation itself — it only instantiates the required
    services once and delegates all rendering to the existing,
    unmodified UI components, passing along the filter criteria the
    filter bar produces.

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    layout.configure_page()

    services = _build_services()

    with layout.main_container():
        _render_navbar_and_sidebar(services)

        criteria = _render_filters(services)

        _render_top_kpi_row(services, criteria)
        _render_summary_row(services, criteria)
        _render_expandable_sections(services, criteria)


render_overview_page()

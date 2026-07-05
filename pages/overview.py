"""
pages/overview.py

Engineering Monitoring Dashboard homepage.

This module is a PURE ORCHESTRATION LAYER. It renders the homepage
from a single, already-fully-resolved ``OverviewPageData`` object,
built once per session by ``app.py`` via
``DashboardService.get_overview_page_data(...)`` and shared through
``st.session_state``. This page performs:

    - No KPI calculations (all KPI values arrive pre-computed on
      ``OverviewPageData.top_kpi_cards`` / ``.summary_cards`` /
      ``.expandable_sections[*].summary``).
    - No file parsing.
    - No filtering (any active filter is applied once, upstream, by
      ``DashboardService`` before this page ever runs).
    - No chart generation (every chart on
      ``OverviewPageData.expandable_sections[*].chart`` is already a
      ready-to-render Plotly figure).
    - No duplicated business logic.

Rendering order:
    1. Header (workbook name, date range, validation status, section /
       unit counts).
    2. Top-level KPI cards, one per discovered section.
    3. Fixed homepage summary cards (whatever
       ``SummaryService`` configured and found present).
    4. One expandable panel per discovered section, each already
       carrying its own summary and chart.

Expected data source
---------------------------------------------------------------
This page does not construct ``DashboardService`` or any of its
collaborators itself — ``app.py`` already does that once per session
(cached via ``st.cache_resource``) and stores the resulting
``OverviewPageData`` in
``st.session_state["em_app__overview_page_data"]`` before dispatching
navigation to this page. This avoids re-loading, re-validating, and
re-parsing the workbook (and reconstructing ``SectionService`` /
``FilterService`` / ``KPIService`` / ``SummaryService`` /
``ChartService`` a second time) on every page switch.

If ``OverviewPageData`` is not yet present in session state (for
example if this page is somehow reached before ``app.py``'s startup
sequence completes), this page shows a neutral informational message
rather than failing or attempting to load data itself, since data
loading is not this page's responsibility.
"""

from __future__ import annotations

import streamlit as st

from services.dashboard_service import OverviewPageData

__all__ = ["render_overview_page"]

_SESSION_KEY_PAGE_DATA = "em_app__overview_page_data"


def _render_header(page_data: OverviewPageData) -> None:
    """
    Render the Overview page's header block from pre-computed data.

    Args:
        page_data: The fully resolved page data supplied by
            ``DashboardService.get_overview_page_data``.
    """
    header = page_data.header
    st.title(header.workbook_name)

    subtitle_parts = [f"Validation: {header.validation_status.value}"]
    if header.date_range and header.date_range.start and header.date_range.end:
        subtitle_parts.append(
            f"{header.date_range.start:%Y-%m-%d} → {header.date_range.end:%Y-%m-%d}"
        )
    subtitle_parts.append(f"{header.section_count} sections")
    subtitle_parts.append(f"{header.unit_count} units")
    st.caption(" · ".join(subtitle_parts))


def _render_top_kpi_row(page_data: OverviewPageData) -> None:
    """
    Render the top row of KPI cards, one per discovered section.

    All values are already computed by ``KPIService`` inside
    ``DashboardService``; this function only arranges and displays
    them.

    Args:
        page_data: The fully resolved page data supplied by
            ``DashboardService.get_overview_page_data``.
    """
    if not page_data.top_kpi_cards:
        return

    st.subheader("Section KPIs")
    columns = st.columns(min(4, len(page_data.top_kpi_cards)))
    for index, summary in enumerate(page_data.top_kpi_cards):
        with columns[index % len(columns)]:
            st.metric(
                label=getattr(summary, "display_name", getattr(summary, "name", "")),
                value=f"{getattr(summary, 'total', 0):,.2f} {getattr(summary, 'unit', '')}".strip(),
            )


def _render_summary_row(page_data: OverviewPageData) -> None:
    """
    Render the fixed homepage summary cards.

    ``SummaryService`` (inside ``DashboardService``) is responsible
    for omitting any configured section absent from the workbook; this
    page performs no presence-checking of its own.

    Args:
        page_data: The fully resolved page data supplied by
            ``DashboardService.get_overview_page_data``.
    """
    if not page_data.summary_cards:
        st.info("No summary sections available.")
        return

    st.subheader("Summary")
    columns = st.columns(min(3, len(page_data.summary_cards)))
    for index, card in enumerate(page_data.summary_cards):
        with columns[index % len(columns)]:
            with st.container(border=True):
                st.markdown(f"**{getattr(card, 'section_name', getattr(card, 'display_name', ''))}**")
                for label in ("total", "average", "last_registered_value"):
                    value = getattr(card, label, None)
                    if value is not None:
                        st.write(f"{label.replace('_', ' ').title()}: {value:,.2f} {getattr(card, 'unit', '')}".strip())


def _render_expandable_sections(page_data: OverviewPageData) -> None:
    """
    Render one expandable panel per discovered section, using the
    already-resolved summary and chart carried on each
    ``ExpandableSection`` entry.

    No further data fetching, filtering, or chart generation happens
    here — every value was already produced upstream by
    ``DashboardService.get_overview_page_data``.

    Args:
        page_data: The fully resolved page data supplied by
            ``DashboardService.get_overview_page_data``.
    """
    if not page_data.expandable_sections:
        st.info("No engineering sections were discovered in the workbook.")
        return

    st.subheader("Sections")
    for entry in page_data.expandable_sections:
        with st.expander(entry.section.display_name):
            summary = entry.summary
            metric_columns = st.columns(3)
            with metric_columns[0]:
                st.metric("Total", f"{getattr(summary, 'total', 0):,.2f}")
            with metric_columns[1]:
                st.metric("Average", f"{getattr(summary, 'average', 0):,.2f}")
            with metric_columns[2]:
                st.metric(
                    "Last Registered",
                    f"{getattr(summary, 'last_value', getattr(summary, 'last_registered_value', 0)):,.2f}",
                )

            if entry.chart is not None:
                st.plotly_chart(
                    entry.chart,
                    use_container_width=True,
                    key=f"em_overview_chart_{entry.section.name}",
                )


def render_overview_page() -> None:
    """
    Render the complete Engineering Monitoring Dashboard homepage from
    the ``OverviewPageData`` already built and cached by ``app.py``.

    This function performs no calculation, parsing, filtering, or
    chart generation itself — it only reads the pre-resolved page data
    out of ``st.session_state`` and delegates to the render helpers
    above.

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    page_data: OverviewPageData | None = st.session_state.get(_SESSION_KEY_PAGE_DATA)

    if page_data is None:
        st.info("Workbook data is not yet available. Please wait for the app to finish loading.")
        return

    _render_header(page_data)
    _render_top_kpi_row(page_data)
    _render_summary_row(page_data)
    _render_expandable_sections(page_data)


render_overview_page()

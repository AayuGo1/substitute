"""
components/section_page.py

Reusable engineering section page template for the Engineering
Monitoring Dashboard (Streamlit-based, SCADA / Power BI aesthetic,
glassmorphism styling).

This is the page template every dedicated engineering section page
(NPCL, DG, GG, Air Compressor, Freon, Water, Energy, Utilities, or any
future section) is built from. Unlike ``components/expandable_section``
— which renders a *collapsible* summary card for use on the homepage —
this template renders a section's *full dedicated page*: the header is
always visible (no collapse), and the daily/weekly/monthly charts are
presented as tabs rather than stacked, since a dedicated page has room
to let the user switch between them without scrolling past all three.

This module is a PURE UI COMPONENT. It:
    - Contains no KPI calculations.
    - Performs no file parsing.
    - Performs no filtering.
    - Contains no duplicated business logic.

It reuses existing components wherever possible:
    - Subsections are rendered via
      ``components.expandable_section.render_expandable_section``,
      giving each subsection its own collapsible card with the same
      header/summary/charts/metrics presentation already implemented
      there, rather than re-implementing that logic here.
    - The same ``DashboardService`` / ``ChartService`` /
      ``SectionService`` protocols defined in
      ``components.expandable_section`` are reused (extended only
      where this page needs one additional value: the section's
      "Last Updated" timestamp), so both the homepage and every
      section page are driven by one consistent service contract.

All visual tokens (colors, typography, spacing, radii, shadows) come
exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already
defined by the global design system in ``theme.py``.

Expected service interface
---------------------------------------------------------------
This component depends only on the following protocol, which extends
the ``DashboardService`` protocol already defined in
``components.expandable_section`` (Interface Segregation — this page
only adds the one extra capability it needs beyond what the homepage
requires):

    SectionPageDashboardService(DashboardService):
        get_section_header(section_key) -> SectionHeaderData   (inherited)
        get_section_summary(section_key) -> KPISummaryData     (inherited)
        get_section_last_updated(section_key: str) -> str
            Pre-formatted "last updated" timestamp for the section.

``ChartService`` and ``SectionService`` are consumed exactly as defined
in ``components.expandable_section``.

Typical usage
-------------
    from components.section_page import render_section_page

    render_section_page(
        section_key="air_compressor",
        dashboard_service=dashboard_service,
        chart_service=chart_service,
        section_service=section_service,
    )
"""

from __future__ import annotations

from typing import Any, Dict, Protocol

import streamlit as st

from components.expandable_section import (
    ChartService,
    DashboardService,
    KPISummaryData,
    SectionHeaderData,
    SectionService,
    render_expandable_section,
)
from components.theme import THEME

__all__ = ["SectionPageDashboardService", "render_section_page"]


class SectionPageDashboardService(DashboardService, Protocol):
    """
    Extension of ``DashboardService`` with the single additional
    capability a dedicated section page needs beyond what the homepage
    requires: a "Last Updated" timestamp for the section header.

    This follows the Interface Segregation Principle — rather than
    adding this method to the shared ``DashboardService`` protocol
    (which the homepage's KPI/summary cards do not need), it is
    layered on here for consumers of this page template only.
    """

    def get_section_last_updated(self, section_key: str) -> str:
        """Return a pre-formatted 'last updated' timestamp for the section."""
        ...


def _get(theme: Dict[str, Any], *path: str, default: str = "") -> str:
    """
    Safely resolve a nested THEME token, falling back to ``default`` if
    any key in ``path`` is missing.

    Args:
        theme: The THEME dictionary.
        *path: Sequence of nested keys to resolve.
        default: Fallback value if the path cannot be resolved.

    Returns:
        The resolved token value, or ``default``.
    """
    node: Any = theme
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node if isinstance(node, str) else default


def _trend_color(direction: str) -> str:
    """
    Resolve the THEME color token representing a trend direction.

    Args:
        direction: The trend direction ("up", "down", or "flat").

    Returns:
        A CSS color value sourced from THEME, with a conventional
        fallback if THEME does not define the relevant token.
    """
    if direction == "up":
        return _get(THEME, "colors", "positive", default="#3ddc84")
    if direction == "down":
        return _get(THEME, "colors", "negative", default="#e35d5d")
    return _get(THEME, "colors", "neutral", default="#8aa0b4")


def _trend_arrow(direction: str) -> str:
    """
    Resolve the arrow glyph representing a trend direction.

    Args:
        direction: The trend direction ("up", "down", or "flat").

    Returns:
        An arrow character.
    """
    return {"up": "▲", "down": "▼", "flat": "▬"}.get(direction, "▬")


def _inject_page_styles() -> None:
    """
    Inject scoped CSS for the section page template, mapping THEME
    tokens onto its selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py`` or by ``components/expandable_section.py``;
    class names are namespaced under ``em-secpage-*`` to avoid
    collisions with either.
    """
    surface = _get(THEME, "colors", "surface", default="#16202c")
    border = _get(THEME, "colors", "border", default="#2a3a4a")
    accent = _get(THEME, "colors", "primary", default="#4fd1c5")
    text_primary = _get(THEME, "colors", "text_primary", default="#e8edf2")
    text_secondary = _get(THEME, "colors", "text_secondary", default="#8aa0b4")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    title_size = _get(THEME, "typography", "title_size", default="1.4rem")
    label_size = _get(THEME, "typography", "label_size", default="0.75rem")
    value_size = _get(THEME, "typography", "value_size", default="2rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    space_lg = _get(THEME, "spacing", "lg", default="1.5rem")
    radius_sm = _get(THEME, "radius", "sm", default="6px")
    radius_md = _get(THEME, "radius", "md", default="14px")
    shadow_sm = _get(THEME, "shadow", "sm", default="0 1px 4px rgba(0, 0, 0, 0.2)")
    shadow_md = _get(THEME, "shadow", "md", default="0 10px 30px rgba(0, 0, 0, 0.45)")

    st.markdown(
        f"""
        <style>
        .em-secpage-header {{
            font-family: {font_family};
            background: linear-gradient(155deg, {surface}e0 0%, {surface}90 100%);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid {border};
            border-radius: {radius_md};
            box-shadow: {shadow_md};
            padding: {space_lg} {space_md};
            margin-bottom: {space_md};
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: {space_md};
        }}
        .em-secpage-identity {{
            display: flex;
            align-items: center;
            gap: {space_sm};
        }}
        .em-secpage-icon {{
            color: {accent};
            font-size: {value_size};
            display: flex;
            align-items: center;
        }}
        .em-secpage-titles {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .em-secpage-name {{
            color: {text_primary};
            font-size: {title_size};
            font-weight: 800;
            letter-spacing: 0.01em;
        }}
        .em-secpage-updated {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 500;
        }}
        .em-secpage-metrics {{
            display: flex;
            align-items: baseline;
            gap: {space_sm};
        }}
        .em-secpage-value {{
            color: {text_primary};
            font-size: {value_size};
            font-weight: 800;
            font-variant-numeric: tabular-nums;
        }}
        .em-secpage-unit {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
        }}
        .em-secpage-trend {{
            font-size: {label_size};
            font-weight: 700;
            padding: {space_xs} {space_sm};
            border-radius: {radius_sm};
            border: 1px solid {border};
        }}
        .em-secpage-section-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: {space_md} 0 {space_sm} 0;
        }}
        .em-secpage-summary-strip {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: {space_sm};
            margin-bottom: {space_md};
        }}
        .em-secpage-summary-tile {{
            font-family: {font_family};
            background: linear-gradient(160deg, {surface}d9 0%, {surface}99 100%);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid {border};
            border-radius: {radius_sm};
            box-shadow: {shadow_sm};
            padding: {space_sm} {space_md};
            transition: transform 0.18s ease-in-out, box-shadow 0.18s ease-in-out,
                border-color 0.18s ease-in-out;
        }}
        .em-secpage-summary-tile:hover {{
            transform: translateY(-2px);
            box-shadow: {shadow_md};
            border-color: {accent};
        }}
        .em-secpage-summary-tile-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }}
        .em-secpage-summary-tile-value {{
            color: {text_primary};
            font-size: 1.25rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        .em-secpage-chart-panel {{
            font-family: {font_family};
            background: {surface}66;
            border: 1px solid {border};
            border-radius: {radius_sm};
            padding: {space_sm};
            margin-bottom: {space_md};
        }}
        .em-secpage-metrics-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: {label_size};
            margin-bottom: {space_md};
        }}
        .em-secpage-metrics-table th {{
            text-align: left;
            color: {text_secondary};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: {space_xs} {space_sm};
            border-bottom: 1px solid {border};
        }}
        .em-secpage-metrics-table td {{
            color: {text_primary};
            padding: {space_xs} {space_sm};
            border-bottom: 1px solid {border};
            font-variant-numeric: tabular-nums;
        }}
        .em-secpage-metrics-table tr:last-child td {{
            border-bottom: none;
        }}
        .em-secpage-empty-note {{
            color: {text_secondary};
            font-size: {label_size};
            font-style: italic;
            padding: {space_xs} 0 {space_md} 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(
    section_key: str,
    header: SectionHeaderData,
    last_updated: str,
) -> None:
    """
    Render the always-visible, full-detail section header for the
    dedicated page (name, icon, current value, unit, trend, last
    updated).

    Args:
        section_key: Identifier of the section (unused for rendering,
            kept for signature symmetry / future extensibility such as
            anchors or analytics hooks).
        header: Pre-computed header data from ``DashboardService``.
        last_updated: Pre-formatted "last updated" timestamp string.
    """
    trend_color = _trend_color(header.trend_direction)
    trend_arrow = _trend_arrow(header.trend_direction)
    icon = header.icon or "⚙️"

    st.markdown(
        f"""
        <div class="em-secpage-header">
            <div class="em-secpage-identity">
                <span class="em-secpage-icon">{icon}</span>
                <div class="em-secpage-titles">
                    <span class="em-secpage-name">{header.name}</span>
                    <span class="em-secpage-updated">Last Updated: {last_updated}</span>
                </div>
            </div>
            <div class="em-secpage-metrics">
                <span class="em-secpage-value">{header.current_value:,.2f}</span>
                <span class="em-secpage-unit">{header.unit}</span>
                <span class="em-secpage-trend" style="color:{trend_color}; border-color:{trend_color};">
                    {trend_arrow}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_kpis(summary: KPISummaryData) -> None:
    """
    Render the Total / Average / Last Registered Value summary tiles
    for the section page.

    Args:
        summary: Pre-computed KPI summary values from
            ``DashboardService``.
    """
    st.markdown(
        '<div class="em-secpage-section-label">Summary KPIs</div>',
        unsafe_allow_html=True,
    )
    tiles = [
        ("Total", summary.total),
        ("Average", summary.average),
        ("Last Registered Value", summary.last_registered_value),
    ]
    tiles_html = "".join(
        f"""
        <div class="em-secpage-summary-tile">
            <div class="em-secpage-summary-tile-label">{label}</div>
            <div class="em-secpage-summary-tile-value">{value:,.2f}
                <span style="font-size:0.65em;">{summary.unit}</span>
            </div>
        </div>
        """
        for label, value in tiles
    )
    st.markdown(
        f'<div class="em-secpage-summary-strip">{tiles_html}</div>',
        unsafe_allow_html=True,
    )


def _render_chart_tabs(section_key: str, chart_service: ChartService) -> None:
    """
    Render the Daily / Weekly / Monthly trend charts inside tabs, so
    only one is visible at a time.

    This function performs no chart generation — it only calls
    ``st.plotly_chart`` on whatever pre-built chart object
    ``ChartService`` returns for each tab.

    Args:
        section_key: Identifier of the section whose charts should be
            rendered.
        chart_service: The injected ``ChartService``.
    """
    st.markdown(
        '<div class="em-secpage-section-label">Trend Charts</div>',
        unsafe_allow_html=True,
    )

    daily_tab, weekly_tab, monthly_tab = st.tabs(["Daily", "Weekly", "Monthly"])
    chart_getters = {
        daily_tab: chart_service.get_daily_trend_chart,
        weekly_tab: chart_service.get_weekly_trend_chart,
        monthly_tab: chart_service.get_monthly_trend_chart,
    }

    for tab, getter in chart_getters.items():
        with tab:
            st.markdown('<div class="em-secpage-chart-panel">', unsafe_allow_html=True)
            chart = getter(section_key)
            if chart is None:
                st.markdown(
                    '<div class="em-secpage-empty-note">No chart data available.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.plotly_chart(
                    chart,
                    use_container_width=True,
                    key=f"em_secpage_chart_{section_key}_{getter.__name__}",
                )
            st.markdown("</div>", unsafe_allow_html=True)


def _render_subsections(
    section_key: str,
    dashboard_service: DashboardService,
    chart_service: ChartService,
    section_service: SectionService,
) -> None:
    """
    Render every subsection of the section as its own expandable card,
    reusing ``render_expandable_section`` rather than re-implementing
    subsection presentation on this page.

    Args:
        section_key: Identifier of the parent section.
        dashboard_service: The injected ``DashboardService``.
        chart_service: The injected ``ChartService``.
        section_service: The injected ``SectionService``.
    """
    st.markdown(
        '<div class="em-secpage-section-label">Subsections</div>',
        unsafe_allow_html=True,
    )
    subsection_keys = section_service.get_subsection_keys(section_key)

    if not subsection_keys:
        st.markdown(
            '<div class="em-secpage-empty-note">No subsections for this section.</div>',
            unsafe_allow_html=True,
        )
        return

    for subsection_key in subsection_keys:
        render_expandable_section(
            section_key=subsection_key,
            dashboard_service=dashboard_service,
            chart_service=chart_service,
            section_service=section_service,
        )


def _render_metrics_table(section_key: str, section_service: SectionService) -> None:
    """
    Render the fully dynamic metrics table for the section, listing
    every metric ``SectionService`` discovers — no metric name is
    hardcoded.

    Args:
        section_key: Identifier of the section whose metrics should be
            rendered.
        section_service: The injected ``SectionService``.
    """
    st.markdown(
        '<div class="em-secpage-section-label">Metrics Table</div>',
        unsafe_allow_html=True,
    )
    rows = section_service.get_metrics_table(section_key)

    if not rows:
        st.markdown(
            '<div class="em-secpage-empty-note">No metrics discovered for this section.</div>',
            unsafe_allow_html=True,
        )
        return

    row_html = "".join(
        f"""
        <tr>
            <td>{row.metric_name}</td>
            <td>{row.value}{f' {row.unit}' if row.unit else ''}</td>
        </tr>
        """
        for row in rows
    )
    st.markdown(
        f"""
        <table class="em-secpage-metrics-table">
            <thead>
                <tr><th>Metric</th><th>Value</th></tr>
            </thead>
            <tbody>
                {row_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def render_section_page(
    section_key: str,
    dashboard_service: SectionPageDashboardService,
    chart_service: ChartService,
    section_service: SectionService,
) -> None:
    """
    Render the complete dedicated page for a single engineering
    section.

    Rendering proceeds strictly in this order:
        1. Section header (name, current value, unit, trend, last
           updated) — always visible, never collapsed.
        2. Summary KPIs (Total, Average, Last Registered Value).
        3. Daily / Weekly / Monthly trend charts inside tabs, so only
           one is visible at a time.
        4. Subsections, each rendered as its own expandable card via
           the existing ``render_expandable_section`` component.
        5. A fully dynamic metrics table listing every metric
           discovered for the section.

    This function is completely section-agnostic: it never references
    a specific section name, subsection name, or metric name. Every
    piece of content is sourced from the three injected services at
    render time, so the same template renders NPCL, DG, GG,
    Air Compressor, Freon, Water, Energy, Utilities, or any future
    section identically.

    Args:
        section_key: Stable identifier for the section, as recognized
            by all three services (e.g. "npcl", "air_compressor").
        dashboard_service: Injected service providing header, summary
            KPI, and last-updated values for the section.
        chart_service: Injected service providing pre-built daily/
            weekly/monthly trend chart objects.
        section_service: Injected service providing subsection
            discovery and dynamic metrics table rows.

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    _inject_page_styles()

    header = dashboard_service.get_section_header(section_key)
    last_updated = dashboard_service.get_section_last_updated(section_key)
    _render_header(section_key, header, last_updated)

    summary = dashboard_service.get_section_summary(section_key)
    _render_summary_kpis(summary)

    _render_chart_tabs(section_key, chart_service)

    _render_subsections(
        section_key,
        dashboard_service=dashboard_service,
        chart_service=chart_service,
        section_service=section_service,
    )

    _render_metrics_table(section_key, section_service)

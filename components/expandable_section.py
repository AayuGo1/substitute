"""
components/expandable_section.py

Core expandable engineering section component for the Engineering
Monitoring Dashboard (Streamlit-based, SCADA / Power BI aesthetic,
glassmorphism styling).

This is the central building block of the dashboard: every engineering
section discovered from the workbook (e.g. NPCL, DG, GG, PNG,
Air Compressor, Freon, Water, Utility, or any future section) is
rendered through this single, fully dynamic component. No section or
subsection name is ever hardcoded here.

This module is a PURE UI COMPONENT. It:
    - Contains no KPI calculations.
    - Performs no file parsing.
    - Performs no filtering.
    - Contains no duplicated business logic.
    - Contains no Streamlit page routing logic.

It orchestrates three injected services (Dependency Inversion):
    - ``DashboardService``: section identity, header values, KPI
      summary values.
    - ``ChartService``: pre-built daily / weekly / monthly trend
      charts (already generated — this component only renders them).
    - ``SectionService``: subsection discovery and dynamic metrics
      table rows.

All visual tokens (colors, typography, spacing, radii, shadows) come
exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already
defined by the global design system in ``theme.py``.

Expected service interfaces
---------------------------------------------------------------
This component depends only on the following protocols (Dependency
Inversion Principle). Adjust the concrete service implementations
accordingly if their real interfaces differ.

    DashboardService:
        get_section_header(section_key: str) -> SectionHeaderData
        get_section_summary(section_key: str) -> KPISummaryData

    ChartService:
        get_daily_trend_chart(section_key: str) -> Optional[Any]
        get_weekly_trend_chart(section_key: str) -> Optional[Any]
        get_monthly_trend_chart(section_key: str) -> Optional[Any]
        Each returns an already-built chart object (e.g. a Plotly
        Figure) ready to be rendered with ``st.plotly_chart``, or
        ``None`` if unavailable. This component performs no chart
        generation, only rendering of what is returned.

    SectionService:
        get_subsection_keys(section_key: str) -> List[str]
        get_metrics_table(section_key: str) -> Sequence[MetricRow]
        All discovery, aggregation, and metric extraction happens
        inside ``SectionService`` — this component only iterates over
        and displays the returned rows.

Typical usage
-------------
    from components.expandable_section import render_expandable_section

    for section_key in dashboard_service.get_section_keys():
        render_expandable_section(
            section_key=section_key,
            dashboard_service=dashboard_service,
            chart_service=chart_service,
            section_service=section_service,
        )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Protocol, Sequence

import streamlit as st

from components.theme import THEME

__all__ = [
    "SectionHeaderData",
    "KPISummaryData",
    "MetricRow",
    "DashboardService",
    "ChartService",
    "SectionService",
    "render_expandable_section",
]

TrendDirection = Literal["up", "down", "flat"]


@dataclass(frozen=True)
class SectionHeaderData:
    """
    Pre-computed header information for a section or subsection,
    shown in both the collapsed and expanded states.

    Attributes:
        name: Display name of the section (e.g. "NPCL",
            "Transformer A"). Fully dynamic — sourced from
            ``DashboardService``.
        current_value: The current value to display for this section.
        unit: Unit label for ``current_value``.
        trend_direction: Pre-determined trend direction: "up", "down",
            or "flat". This component only maps this to a color/arrow.
        icon: Optional icon glyph/emoji representing the section. If
            ``None``, a neutral engineering placeholder glyph is used.
    """

    name: str
    current_value: float
    unit: str
    trend_direction: TrendDirection
    icon: Optional[str] = None


@dataclass(frozen=True)
class KPISummaryData:
    """
    Pre-computed summary KPI values shown inside an expanded section.

    Attributes:
        total: Pre-computed total value for the section.
        average: Pre-computed average value for the section.
        last_registered_value: The most recent recorded value.
        unit: Unit label shared by all three values.
    """

    total: float
    average: float
    last_registered_value: float
    unit: str


@dataclass(frozen=True)
class MetricRow:
    """
    A single dynamically discovered metric row for the metrics table.

    Attributes:
        metric_name: Name of the metric as discovered by
            ``SectionService`` (never hardcoded by this component).
        value: The metric's value, pre-formatted or raw numeric/string.
        unit: Optional unit label for the value.
    """

    metric_name: str
    value: str
    unit: Optional[str] = None


class DashboardService(Protocol):
    """
    Protocol describing the section-level data this component needs
    from the dashboard backend.

    This component depends only on this abstraction and performs no
    calculation of any of these values itself.
    """

    def get_section_header(self, section_key: str) -> SectionHeaderData:
        """Return header data (name, value, unit, trend, icon) for a section."""
        ...

    def get_section_summary(self, section_key: str) -> KPISummaryData:
        """Return summary KPI values (total, average, last registered) for a section."""
        ...


class ChartService(Protocol):
    """
    Protocol describing the chart objects this component renders.

    All chart generation happens inside ``ChartService``; this
    component only passes the returned objects to Streamlit's chart
    renderer.
    """

    def get_daily_trend_chart(self, section_key: str) -> Optional[Any]:
        """Return an already-built daily trend chart object, or None."""
        ...

    def get_weekly_trend_chart(self, section_key: str) -> Optional[Any]:
        """Return an already-built weekly trend chart object, or None."""
        ...

    def get_monthly_trend_chart(self, section_key: str) -> Optional[Any]:
        """Return an already-built monthly trend chart object, or None."""
        ...


class SectionService(Protocol):
    """
    Protocol describing subsection discovery and metrics table data.

    All discovery and extraction logic lives inside ``SectionService``;
    this component only iterates over and displays the returned data.
    """

    def get_subsection_keys(self, section_key: str) -> List[str]:
        """Return the ordered list of subsection keys for a section, if any."""
        ...

    def get_metrics_table(self, section_key: str) -> Sequence[MetricRow]:
        """Return every dynamically discovered metric row for a section."""
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


def _trend_color(direction: TrendDirection) -> str:
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


def _trend_arrow(direction: TrendDirection) -> str:
    """
    Resolve the arrow glyph representing a trend direction.

    Args:
        direction: The trend direction ("up", "down", or "flat").

    Returns:
        An arrow character.
    """
    return {"up": "▲", "down": "▼", "flat": "▬"}.get(direction, "▬")


def _session_key(*parts: str) -> str:
    """
    Build a namespaced Streamlit session-state key.

    Args:
        *parts: Identifier segments to join.

    Returns:
        A namespaced session-state key.
    """
    return "em_expandable__" + "__".join(parts)


def _inject_styles() -> None:
    """
    Inject scoped CSS for the expandable section component, mapping
    THEME tokens onto its selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py``. A CSS keyframe animation provides a
    smooth fade/slide-in effect for expanded content.
    """
    surface = _get(THEME, "colors", "surface", default="#16202c")
    border = _get(THEME, "colors", "border", default="#2a3a4a")
    accent = _get(THEME, "colors", "primary", default="#4fd1c5")
    text_primary = _get(THEME, "colors", "text_primary", default="#e8edf2")
    text_secondary = _get(THEME, "colors", "text_secondary", default="#8aa0b4")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    title_size = _get(THEME, "typography", "title_size", default="1rem")
    label_size = _get(THEME, "typography", "label_size", default="0.72rem")
    value_size = _get(THEME, "typography", "value_size", default="1.3rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    space_lg = _get(THEME, "spacing", "lg", default="1.5rem")
    radius_sm = _get(THEME, "radius", "sm", default="6px")
    radius_md = _get(THEME, "radius", "md", default="12px")
    shadow_sm = _get(THEME, "shadow", "sm", default="0 1px 4px rgba(0, 0, 0, 0.2)")
    shadow_md = _get(THEME, "shadow", "md", default="0 10px 30px rgba(0, 0, 0, 0.45)")

    st.markdown(
        f"""
        <style>
        @keyframes em-expand-fade-in {{
            from {{ opacity: 0; transform: translateY(-6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .em-section {{
            font-family: {font_family};
            background: linear-gradient(160deg, {surface}d9 0%, {surface}99 100%);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid {border};
            border-radius: {radius_md};
            box-shadow: {shadow_sm};
            margin-bottom: {space_md};
            transition: box-shadow 0.18s ease-in-out, border-color 0.18s ease-in-out;
            overflow: hidden;
        }}
        .em-section:hover {{
            box-shadow: {shadow_md};
            border-color: {accent};
        }}
        .em-section-subsection {{
            border-radius: {radius_sm};
            margin-bottom: {space_sm};
        }}
        .em-section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: {space_md};
        }}
        .em-section-identity {{
            display: flex;
            align-items: center;
            gap: {space_sm};
        }}
        .em-section-icon {{
            color: {accent};
            font-size: {value_size};
            display: flex;
            align-items: center;
        }}
        .em-section-name {{
            color: {text_primary};
            font-size: {title_size};
            font-weight: 700;
            letter-spacing: 0.01em;
        }}
        .em-section-metrics {{
            display: flex;
            align-items: baseline;
            gap: {space_md};
        }}
        .em-section-value {{
            color: {text_primary};
            font-size: {value_size};
            font-weight: 800;
            font-variant-numeric: tabular-nums;
        }}
        .em-section-unit {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
        }}
        .em-section-trend {{
            font-size: {label_size};
            font-weight: 700;
        }}
        .em-section-body {{
            padding: 0 {space_md} {space_md} {space_md};
            border-top: 1px solid {border};
            animation: em-expand-fade-in 0.22s ease-out;
        }}
        .em-section-block-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: {space_md} 0 {space_sm} 0;
        }}
        .em-summary-strip {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: {space_sm};
        }}
        .em-summary-tile {{
            background: {surface}66;
            border: 1px solid {border};
            border-radius: {radius_sm};
            padding: {space_sm};
        }}
        .em-summary-tile-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }}
        .em-summary-tile-value {{
            color: {text_primary};
            font-size: {value_size};
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        .em-chart-tabs-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            letter-spacing: 0.04em;
        }}
        .em-metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: {space_xs};
            font-size: {label_size};
        }}
        .em-metrics-table th {{
            text-align: left;
            color: {text_secondary};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: {space_xs} {space_sm};
            border-bottom: 1px solid {border};
        }}
        .em-metrics-table td {{
            color: {text_primary};
            padding: {space_xs} {space_sm};
            border-bottom: 1px solid {border};
            font-variant-numeric: tabular-nums;
        }}
        .em-metrics-table tr:last-child td {{
            border-bottom: none;
        }}
        .em-empty-note {{
            color: {text_secondary};
            font-size: {label_size};
            font-style: italic;
            padding: {space_xs} 0;
        }}
        div[data-testid="stButton"] button.em-toggle {{
            background: transparent;
            border: 1px solid {border};
            color: {accent};
            border-radius: {radius_sm};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header_html(header: SectionHeaderData) -> str:
    """
    Build the HTML markup for a section/subsection header row shown in
    both collapsed and expanded states.

    Args:
        header: Pre-computed header data.

    Returns:
        An HTML string for the header row.
    """
    trend_color = _trend_color(header.trend_direction)
    trend_arrow = _trend_arrow(header.trend_direction)
    icon = header.icon or "⚙️"

    return f"""
        <div class="em-section-header">
            <div class="em-section-identity">
                <span class="em-section-icon">{icon}</span>
                <span class="em-section-name">{header.name}</span>
            </div>
            <div class="em-section-metrics">
                <span class="em-section-value">{header.current_value:,.2f}</span>
                <span class="em-section-unit">{header.unit}</span>
                <span class="em-section-trend" style="color:{trend_color};">
                    {trend_arrow}
                </span>
            </div>
        </div>
    """


def _render_summary_strip(summary: KPISummaryData) -> None:
    """
    Render the Total / Average / Last Registered Value summary tiles.

    Args:
        summary: Pre-computed KPI summary values.
    """
    st.markdown(
        '<div class="em-section-block-label">Summary KPIs</div>',
        unsafe_allow_html=True,
    )
    tiles = [
        ("Total", summary.total),
        ("Average", summary.average),
        ("Last Registered", summary.last_registered_value),
    ]
    tiles_html = "".join(
        f"""
        <div class="em-summary-tile">
            <div class="em-summary-tile-label">{label}</div>
            <div class="em-summary-tile-value">{value:,.2f}
                <span style="font-size:0.7em;">{summary.unit}</span>
            </div>
        </div>
        """
        for label, value in tiles
    )
    st.markdown(f'<div class="em-summary-strip">{tiles_html}</div>', unsafe_allow_html=True)


def _render_trend_charts(section_key: str, chart_service: ChartService) -> None:
    """
    Render the daily, weekly, and monthly trend charts for a section,
    using pre-built chart objects from ``ChartService``.

    This function performs no chart generation — it only calls
    ``st.plotly_chart`` (or falls back to a note) on whatever object
    ``ChartService`` returns.

    Args:
        section_key: Identifier of the section/subsection whose charts
            should be rendered.
        chart_service: The injected ``ChartService``.
    """
    chart_definitions = [
        ("Daily Trend", chart_service.get_daily_trend_chart(section_key)),
        ("Weekly Trend", chart_service.get_weekly_trend_chart(section_key)),
        ("Monthly Trend", chart_service.get_monthly_trend_chart(section_key)),
    ]

    for label, chart in chart_definitions:
        st.markdown(
            f'<div class="em-section-block-label">{label}</div>',
            unsafe_allow_html=True,
        )
        if chart is None:
            st.markdown(
                '<div class="em-empty-note">No chart data available.</div>',
                unsafe_allow_html=True,
            )
            continue
        st.plotly_chart(chart, use_container_width=True, key=_session_key("chart", section_key, label))


def _render_metrics_table(section_key: str, section_service: SectionService) -> None:
    """
    Render the dynamic metrics table for a section, listing every
    metric ``SectionService`` discovers — no metric name is hardcoded.

    Args:
        section_key: Identifier of the section/subsection whose
            metrics should be rendered.
        section_service: The injected ``SectionService``.
    """
    st.markdown(
        '<div class="em-section-block-label">Metrics Table</div>',
        unsafe_allow_html=True,
    )
    rows = section_service.get_metrics_table(section_key)

    if not rows:
        st.markdown(
            '<div class="em-empty-note">No metrics discovered for this section.</div>',
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
        <table class="em-metrics-table">
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


def _render_subsection(
    subsection_key: str,
    dashboard_service: DashboardService,
    chart_service: ChartService,
    section_service: SectionService,
) -> None:
    """
    Render a single subsection as its own collapsible card, reusing the
    same header/summary/charts/metrics presentation as a top-level
    section.

    Args:
        subsection_key: Identifier of the subsection (e.g.
            "Transformer A").
        dashboard_service: The injected ``DashboardService``.
        chart_service: The injected ``ChartService``.
        section_service: The injected ``SectionService``.
    """
    toggle_key = _session_key("expanded", subsection_key)
    expanded = st.session_state.get(toggle_key, False)

    header = dashboard_service.get_section_header(subsection_key)

    st.markdown('<div class="em-section em-section-subsection">', unsafe_allow_html=True)
    st.markdown(_render_header_html(header), unsafe_allow_html=True)

    toggle_label = "Collapse ▲" if expanded else "Expand ▼"
    if st.button(toggle_label, key=_session_key("btn", subsection_key), use_container_width=True):
        expanded = not expanded
        st.session_state[toggle_key] = expanded

    if expanded:
        st.markdown('<div class="em-section-body">', unsafe_allow_html=True)
        summary = dashboard_service.get_section_summary(subsection_key)
        _render_summary_strip(summary)
        _render_trend_charts(subsection_key, chart_service)
        _render_metrics_table(subsection_key, section_service)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_expandable_section(
    section_key: str,
    dashboard_service: DashboardService,
    chart_service: ChartService,
    section_service: SectionService,
) -> None:
    """
    Render a single top-level expandable engineering section.

    Collapsed state shows: section name, current value, unit, trend,
    and an expand affordance. Expanded state additionally shows the
    summary KPIs (Total, Average, Last Registered Value), daily/
    weekly/monthly trend charts, an arbitrary number of subsections
    (each rendered as its own collapsible card via the same
    presentation), and a fully dynamic metrics table.

    This function is completely section-agnostic: it never references
    a specific section name, subsection name, or metric name. Every
    piece of content is sourced from the three injected services at
    render time, so it works identically for NPCL, DG, GG, PNG,
    Air Compressor, Freon, Water, Utility, or any future section
    discovered by the backend.

    Args:
        section_key: Stable identifier for the section, as recognized
            by all three services (e.g. "npcl", "air_compressor").
        dashboard_service: Injected service providing header and
            summary KPI values.
        chart_service: Injected service providing pre-built daily/
            weekly/monthly trend chart objects.
        section_service: Injected service providing subsection
            discovery and dynamic metrics table rows.

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    _inject_styles()

    toggle_key = _session_key("expanded", section_key)
    expanded = st.session_state.get(toggle_key, False)

    header = dashboard_service.get_section_header(section_key)

    st.markdown('<div class="em-section">', unsafe_allow_html=True)
    st.markdown(_render_header_html(header), unsafe_allow_html=True)

    toggle_label = "Collapse ▲" if expanded else "Expand ▼"
    if st.button(toggle_label, key=_session_key("btn", section_key), use_container_width=True):
        expanded = not expanded
        st.session_state[toggle_key] = expanded

    if expanded:
        st.markdown('<div class="em-section-body">', unsafe_allow_html=True)

        summary = dashboard_service.get_section_summary(section_key)
        _render_summary_strip(summary)

        _render_trend_charts(section_key, chart_service)

        subsection_keys = section_service.get_subsection_keys(section_key)
        st.markdown(
            '<div class="em-section-block-label">Subsections</div>',
            unsafe_allow_html=True,
        )
        if subsection_keys:
            for subsection_key in subsection_keys:
                _render_subsection(
                    subsection_key,
                    dashboard_service=dashboard_service,
                    chart_service=chart_service,
                    section_service=section_service,
                )
        else:
            st.markdown(
                '<div class="em-empty-note">No subsections for this section.</div>',
                unsafe_allow_html=True,
            )

        _render_metrics_table(section_key, section_service)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

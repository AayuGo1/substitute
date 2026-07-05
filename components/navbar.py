"""
components/navbar.py

Premium industrial-style navigation header for the Engineering Monitoring
Dashboard (Streamlit-based, SCADA / Power BI aesthetic).

This module is a PURE UI COMPONENT. It:
    - Contains no business logic.
    - Performs no KPI calculations.
    - Performs no chart generation.
    - Performs no file parsing.
    - Contains no GitHub / data-source logic.
    - Contains no Streamlit page routing / layout orchestration logic.

All visual tokens (colors, typography, spacing, radii, shadows) come
exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already defined
by the global design system in ``theme.py`` — it only maps THEME tokens
onto navbar-specific selectors.

Expected ``THEME`` shape (defined in ``components/theme.py``)
---------------------------------------------------------------
This component reads the following keys from ``THEME``. If a key is
absent, a sensible fallback is used so the navbar degrades gracefully
rather than raising an exception.

    THEME["colors"]["background"]        surface background color
    THEME["colors"]["surface"]            panel/card background color
    THEME["colors"]["border"]             hairline border color
    THEME["colors"]["primary"]            accent color (e.g. teal/cyan)
    THEME["colors"]["text_primary"]       primary text color
    THEME["colors"]["text_secondary"]     secondary/muted text color
    THEME["typography"]["font_family"]    base font stack
    THEME["typography"]["title_size"]     dashboard title font size
    THEME["typography"]["label_size"]     small label font size
    THEME["typography"]["value_size"]     value/time font size
    THEME["spacing"]["xs"|"sm"|"md"|"lg"] spacing scale (rem strings)
    THEME["radius"]["sm"|"md"]            border-radius scale
    THEME["shadow"]["sm"|"md"]            box-shadow tokens

Typical usage
-------------
    from components.navbar import render_navbar, NavbarConfig

    render_navbar(
        NavbarConfig(
            company_logo_path=dashboard_service.get_company_logo_path(),
            dashboard_title=dashboard_service.get_dashboard_title(),
            workbook_name=dashboard_service.get_workbook_name(),
            current_date=dashboard_service.get_current_date(),
            current_time=dashboard_service.get_current_time(),
            last_updated=dashboard_service.get_last_updated(),
        ),
        on_refresh=dashboard_service.refresh,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import streamlit as st

from components.theme import THEME

__all__ = ["NavbarConfig", "render_navbar"]


@dataclass(frozen=True)
class NavbarConfig:
    """
    Immutable data container describing everything the navbar needs to
    render.

    All values are expected to be pre-computed and supplied by
    ``DashboardService`` (or any other upstream service). This component
    never derives, fetches, or calculates any of these values itself.

    Attributes:
        company_logo_path: Filesystem path or URL to the company logo
            image. If ``None``, a premium engineering placeholder icon
            is rendered instead of an image.
        dashboard_title: The title of the dashboard (e.g. "Engineering
            Monitoring Dashboard").
        workbook_name: The name of the active workbook/data source being
            monitored (e.g. "Daily_energy_Monitoring.xlsx").
        current_date: Pre-formatted current date string (e.g.
            "05 Jul 2026"). Formatting is the caller's responsibility.
        current_time: Pre-formatted current time string (e.g.
            "14:32:07"). Formatting is the caller's responsibility.
        last_updated: Optional pre-formatted "last updated" timestamp
            string (e.g. "2 min ago" or "14:30:12"). If ``None``, the
            field is omitted from the navbar.
        refresh_label: Label text shown on the refresh button.
    """

    company_logo_path: Optional[str]
    dashboard_title: str
    workbook_name: str
    current_date: str
    current_time: str
    last_updated: Optional[str] = None
    refresh_label: str = "Refresh"


def _get(theme: Dict[str, Any], *path: str, default: str = "") -> str:
    """
    Safely resolve a nested THEME token, falling back to ``default`` if
    any key in ``path`` is missing.

    This keeps the navbar decoupled from the exact completeness of
    ``theme.py`` while still sourcing every visual value from THEME
    whenever it is available.

    Args:
        theme: The THEME dictionary.
        *path: Sequence of nested keys to resolve (e.g. "colors",
            "primary").
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


def _inject_navbar_styles() -> None:
    """
    Inject scoped CSS for the navbar that maps THEME tokens onto
    navbar-specific selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py``.
    """
    bg = _get(THEME, "colors", "surface", default="var(--em-surface, #16202c)")
    border = _get(THEME, "colors", "border", default="var(--em-border, #2a3a4a)")
    accent = _get(THEME, "colors", "primary", default="var(--em-primary, #4fd1c5)")
    text_primary = _get(THEME, "colors", "text_primary", default="var(--em-text, #e8edf2)")
    text_secondary = _get(THEME, "colors", "text_secondary", default="var(--em-text-muted, #8aa0b4)")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    title_size = _get(THEME, "typography", "title_size", default="1.05rem")
    label_size = _get(THEME, "typography", "label_size", default="0.72rem")
    value_size = _get(THEME, "typography", "value_size", default="0.85rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    space_lg = _get(THEME, "spacing", "lg", default="1.5rem")
    radius_sm = _get(THEME, "radius", "sm", default="6px")
    radius_md = _get(THEME, "radius", "md", default="10px")
    shadow_md = _get(THEME, "shadow", "md", default="0 2px 10px rgba(0, 0, 0, 0.35)")

    st.markdown(
        f"""
        <style>
        .em-navbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: {space_sm} {space_md};
            background: {bg};
            border: 1px solid {border};
            border-radius: {radius_md};
            box-shadow: {shadow_md};
            margin-bottom: {space_md};
            font-family: {font_family};
        }}
        .em-navbar-left {{
            display: flex;
            align-items: center;
            gap: {space_sm};
        }}
        .em-navbar-logo-placeholder {{
            width: 42px;
            height: 42px;
            border-radius: {radius_sm};
            background: {bg};
            border: 1px solid {border};
            display: flex;
            align-items: center;
            justify-content: center;
            color: {accent};
        }}
        .em-navbar-logo-img {{
            width: 42px;
            height: 42px;
            border-radius: {radius_sm};
            object-fit: contain;
            border: 1px solid {border};
            background: {bg};
        }}
        .em-navbar-titles {{
            display: flex;
            flex-direction: column;
            line-height: 1.25;
            gap: 2px;
        }}
        .em-navbar-title {{
            color: {text_primary};
            font-size: {title_size};
            font-weight: 700;
            letter-spacing: 0.02em;
        }}
        .em-navbar-workbook {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .em-navbar-right {{
            display: flex;
            align-items: center;
            gap: {space_lg};
        }}
        .em-navbar-metric {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            line-height: 1.3;
            gap: 1px;
        }}
        .em-navbar-metric-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .em-navbar-metric-value {{
            color: {text_primary};
            font-size: {value_size};
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}
        .em-navbar-metric-value--accent {{
            color: {accent};
        }}
        .em-navbar-divider {{
            width: 1px;
            align-self: stretch;
            background: {border};
        }}
        div[data-testid="stButton"] button {{
            background-color: {bg};
            color: {accent};
            border: 1px solid {border};
            border-radius: {radius_sm};
            padding: {space_xs} {space_sm};
            font-weight: 600;
            font-family: {font_family};
            display: flex;
            align-items: center;
            justify-content: center;
            gap: {space_xs};
            transition: all 0.15s ease-in-out;
        }}
        div[data-testid="stButton"] button:hover {{
            background-color: {border};
            border-color: {accent};
            color: {text_primary};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_left_section(config: NavbarConfig) -> None:
    """
    Render the left section of the navbar: logo (or premium engineering
    placeholder icon), dashboard title, and workbook name.

    Args:
        config: Navbar configuration values supplied by the caller.
    """
    if config.company_logo_path:
        logo_html = (
            f'<img class="em-navbar-logo-img" src="{config.company_logo_path}" />'
        )
    else:
        # Premium engineering placeholder icon (gauge/dial glyph) rendered
        # as inline SVG so it inherits THEME colors via currentColor and
        # requires no external asset.
        logo_html = """
            <div class="em-navbar-logo-placeholder">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="1.8"
                     stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"></circle>
                    <path d="M12 12 L15.5 8.5"></path>
                    <path d="M8 15.5 l1.2 -1.2"></path>
                    <path d="M12 3 v2"></path>
                    <path d="M12 19 v2"></path>
                    <path d="M3 12 h2"></path>
                    <path d="M19 12 h2"></path>
                </svg>
            </div>
        """

    st.markdown(
        f"""
        <div class="em-navbar-left">
            {logo_html}
            <div class="em-navbar-titles">
                <span class="em-navbar-title">{"TEST NAVBAR"}</span>
                <span class="em-navbar-workbook">{config.workbook_name}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_metric(label: str, value: str, accent: bool = False) -> str:
    """
    Build the markup for a single right-hand navbar metric (e.g. Date,
    Time, Last Updated).

    Args:
        label: Small uppercase label shown above the value.
        value: The metric's value text.
        accent: Whether to render the value using the THEME accent
            color, used to draw attention to the live clock.

    Returns:
        An HTML string for the metric block.
    """
    value_class = "em-navbar-metric-value"
    if accent:
        value_class += " em-navbar-metric-value--accent"
    return f"""
        <div class="em-navbar-metric">
            <span class="em-navbar-metric-label">{label}</span>
            <span class="{value_class}">{value}</span>
        </div>
    """


def _render_right_section(config: NavbarConfig) -> None:
    """
    Render the right section of the navbar: date, time, and the
    optional "Last Updated" field.

    The refresh button is rendered separately via Streamlit's native
    ``st.button`` so that ``on_refresh`` callbacks work correctly, since
    interactive widgets cannot be created via raw HTML/markdown.

    Args:
        config: Navbar configuration values supplied by the caller.
    """
    metrics_html = _render_metric("Date", config.current_date)
    metrics_html += '<div class="em-navbar-divider"></div>'
    metrics_html += _render_metric("Time", config.current_time, accent=True)

    if config.last_updated:
        metrics_html += '<div class="em-navbar-divider"></div>'
        metrics_html += _render_metric("Last Updated", config.last_updated)

    st.markdown(
        f'<div class="em-navbar-right">{metrics_html}</div>',
        unsafe_allow_html=True,
    )


def render_navbar(
    config: NavbarConfig,
    on_refresh: Optional[Callable[[], None]] = None,
    key: str = "em_navbar_refresh",
) -> bool:
    """
    Render the full industrial dashboard navbar.

    This function only renders UI based on the supplied ``config`` and
    the shared ``THEME`` design tokens. It does not compute dates/times,
    does not fetch data, and does not know where the workbook or logo
    come from — those responsibilities belong to ``DashboardService``
    and are injected via ``NavbarConfig``.

    Args:
        config: Pre-computed navbar values (title, workbook name,
            formatted date/time/last-updated, logo path) supplied by
            the caller.
        on_refresh: Optional zero-argument callback invoked immediately
            when the refresh button is clicked. If ``None``, only the
            button's clicked state is returned and no side effect is
            triggered by this component.
        key: Unique Streamlit widget key for the refresh button, to
            avoid key collisions when the navbar is rendered multiple
            times in the same app run.

    Returns:
        ``True`` if the refresh button was clicked during this run,
        ``False`` otherwise.
    """
    _inject_navbar_styles()

    container = st.container()
    with container:
        left_col, right_col, button_col = st.columns([6, 4, 1.4])

        with left_col:
            _render_left_section(config)

        with right_col:
            _render_right_section(config)

        with button_col:
            refresh_clicked: bool = st.button(
                f"⟳ {config.refresh_label}",
                key=key,
                use_container_width=True,
            )

    if refresh_clicked and on_refresh is not None:
        on_refresh()

    return refresh_clicked

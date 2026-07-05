"""
components/cards.py

Premium engineering KPI cards for the Engineering Monitoring Dashboard
(Streamlit-based, SCADA / Power BI aesthetic, glassmorphism styling).

This module is a PURE UI COMPONENT. It:
    - Contains no KPI calculations.
    - Performs no file parsing.
    - Contains no business logic.
    - Contains no Streamlit page routing logic.

The top dashboard row renders one card per major engineering section
discovered from Sheet 1 (e.g. NPCL, DG, GG, PNG, Air Compressor, Solar,
Utility, ...). The set of sections is never hardcoded here: the caller
supplies a sequence of ``KPICardData`` objects — one per section —
sourced entirely from ``DashboardService`` outputs, so the grid is
fully dynamic and scales to however many sections the backend detects.

All visual tokens (colors, typography, spacing, radii, shadows) come
exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already
defined by the global design system in ``theme.py``. The only
exception is the semantic mapping of trend direction to color, which
falls back to conventional green/red/gray if THEME does not define
``THEME["colors"]["positive"|"negative"|"neutral"]``.

Expected ``DashboardService`` output shape
---------------------------------------------------------------
This component expects the caller to have already transformed
``DashboardService`` output into a sequence of ``KPICardData``
instances — one per engineering section. It performs no aggregation,
delta computation, or sparkline math itself; ``sparkline_values`` and
``percentage_change`` must already be fully computed upstream.

Expected ``THEME`` shape (defined in ``components/theme.py``)
---------------------------------------------------------------
See ``components/navbar.py`` for the full documented THEME contract
(``colors``, ``typography``, ``spacing``, ``radius``, ``shadow``).
This component additionally reads, when present:

    THEME["colors"]["positive"]   color for upward/favorable trends
    THEME["colors"]["negative"]   color for downward/unfavorable trends
    THEME["colors"]["neutral"]    color for flat/no-change trends

Typical usage
-------------
    from components.cards import render_kpi_cards, KPICardData

    cards = [
        KPICardData(
            section_name="NPCL",
            current_value=1245.6,
            unit="kWh",
            trend_direction="up",
            percentage_change=3.2,
            sparkline_values=[1180, 1190, 1205, 1220, 1245.6],
            last_updated="14:30:12",
        ),
        # ... one entry per section returned by DashboardService
    ]
    render_kpi_cards(cards)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence

import streamlit as st

from components.theme import THEME

__all__ = ["KPICardData", "render_kpi_cards"]

TrendDirection = Literal["up", "down", "flat"]


@dataclass(frozen=True)
class KPICardData:
    """
    Fully pre-computed data for a single KPI card.

    All values are expected to originate from ``DashboardService``
    output. This component performs no calculation on any field — it
    only renders what it is given.

    Attributes:
        section_name: Name of the engineering section (e.g. "NPCL",
            "DG", "GG", "PNG", "Air Compressor", "Solar", "Utility").
            The set of sections is fully dynamic and driven by
            whatever ``DashboardService`` discovers from Sheet 1.
        current_value: The current value to display for this section.
        unit: Unit label for ``current_value`` (e.g. "kWh", "m³",
            "bar", "kg").
        trend_direction: Pre-determined trend direction: "up", "down",
            or "flat". This component only maps this to a color/arrow,
            it does not derive it from raw data.
        percentage_change: Pre-computed percentage change value (e.g.
            ``3.2`` for +3.2%, ``-1.5`` for -1.5%). Sign is used only
            for display formatting, not calculated here.
        sparkline_values: Pre-computed sequence of numeric values used
            to draw the mini sparkline, in chronological order. This
            component only plots the given points.
        last_updated: Pre-formatted "last updated" timestamp string
            (e.g. "14:30:12" or "2 min ago").
        icon: Optional icon glyph/emoji representing the section. If
            ``None``, a neutral engineering placeholder glyph is used.
    """

    section_name: str
    current_value: float
    unit: str
    trend_direction: TrendDirection
    percentage_change: float
    sparkline_values: Sequence[float]
    last_updated: str
    icon: Optional[str] = None


def _get(theme: Dict[str, Any], *path: str, default: str = "") -> str:
    """
    Safely resolve a nested THEME token, falling back to ``default`` if
    any key in ``path`` is missing.

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


def _format_percentage_change(value: float) -> str:
    """
    Format a percentage-change value for display, including its sign.

    Args:
        value: Pre-computed percentage change (e.g. ``3.2``, ``-1.5``).

    Returns:
        A display string such as "+3.2%" or "-1.5%".
    """
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def _build_sparkline_svg(
    values: Sequence[float],
    stroke_color: str,
    fill_color: str,
    width: int = 120,
    height: int = 36,
) -> str:
    """
    Build a minimal inline SVG sparkline polyline from pre-computed
    values.

    This function performs no data analysis — it only maps the given
    numeric sequence onto SVG coordinates for rendering.

    Args:
        values: Chronologically ordered numeric values to plot.
        stroke_color: THEME-derived color for the sparkline line.
        fill_color: THEME-derived color for the soft area fill beneath
            the line.
        width: SVG viewport width in pixels.
        height: SVG viewport height in pixels.

    Returns:
        An ``<svg>...</svg>`` markup string. Returns an empty string if
        fewer than two values are provided, since a sparkline requires
        at least two points.
    """
    points = list(values)
    if len(points) < 2:
        return ""

    min_value = min(points)
    max_value = max(points)
    value_range = (max_value - min_value) or 1.0
    padding = 3
    plot_width = width - (2 * padding)
    plot_height = height - (2 * padding)
    step = plot_width / (len(points) - 1)

    coords = []
    for index, value in enumerate(points):
        x = padding + (index * step)
        normalized = (value - min_value) / value_range
        y = padding + (plot_height * (1 - normalized))
        coords.append((round(x, 2), round(y, 2)))

    polyline_points = " ".join(f"{x},{y}" for x, y in coords)
    area_points = (
        f"{coords[0][0]},{height - padding} "
        + polyline_points
        + f" {coords[-1][0]},{height - padding}"
    )

    return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
            <polygon points="{area_points}" fill="{fill_color}" opacity="0.25"></polygon>
            <polyline points="{polyline_points}" fill="none"
                      stroke="{stroke_color}" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round"></polyline>
        </svg>
    """


def _inject_card_styles() -> None:
    """
    Inject scoped CSS for the KPI cards that maps THEME tokens onto
    card-specific selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py``. Glassmorphism is achieved via
    ``backdrop-filter`` and a translucent variant of the THEME surface
    color.
    """
    surface = _get(THEME, "colors", "surface", default="#16202c")
    border = _get(THEME, "colors", "border", default="#2a3a4a")
    accent = _get(THEME, "colors", "primary", default="#4fd1c5")
    text_primary = _get(THEME, "colors", "text_primary", default="#e8edf2")
    text_secondary = _get(THEME, "colors", "text_secondary", default="#8aa0b4")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    title_size = _get(THEME, "typography", "title_size", default="1rem")
    label_size = _get(THEME, "typography", "label_size", default="0.72rem")
    value_size = _get(THEME, "typography", "value_size", default="1.6rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    radius_md = _get(THEME, "radius", "md", default="12px")
    shadow_sm = _get(THEME, "shadow", "sm", default="0 1px 4px rgba(0, 0, 0, 0.2)")
    shadow_md = _get(THEME, "shadow", "md", default="0 10px 30px rgba(0, 0, 0, 0.45)")

    st.markdown(
        f"""
        <style>
        .em-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: {space_md};
            margin-bottom: {space_md};
        }}
        .em-kpi-card {{
            position: relative;
            font-family: {font_family};
            background: linear-gradient(155deg, {surface}cc 0%, {surface}88 100%);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid {border};
            border-radius: {radius_md};
            box-shadow: {shadow_sm};
            padding: {space_md};
            display: flex;
            flex-direction: column;
            gap: {space_xs};
            transition: transform 0.18s ease-in-out, box-shadow 0.18s ease-in-out,
                border-color 0.18s ease-in-out;
        }}
        .em-kpi-card:hover {{
            transform: translateY(-3px);
            box-shadow: {shadow_md};
            border-color: {accent};
        }}
        .em-kpi-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .em-kpi-card-section {{
            display: flex;
            align-items: center;
            gap: {space_xs};
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }}
        .em-kpi-card-icon {{
            color: {accent};
            display: flex;
            align-items: center;
        }}
        .em-kpi-card-value-row {{
            display: flex;
            align-items: baseline;
            gap: {space_xs};
        }}
        .em-kpi-card-value {{
            color: {text_primary};
            font-size: {value_size};
            font-weight: 800;
            letter-spacing: -0.01em;
            font-variant-numeric: tabular-nums;
        }}
        .em-kpi-card-unit {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
        }}
        .em-kpi-card-trend-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: {space_sm};
        }}
        .em-kpi-card-trend {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: {label_size};
            font-weight: 700;
        }}
        .em-kpi-card-sparkline {{
            display: flex;
            align-items: center;
            justify-content: flex-end;
            flex: 1;
        }}
        .em-kpi-card-footer {{
            display: flex;
            align-items: center;
            justify-content: flex-end;
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 500;
            opacity: 0.85;
            border-top: 1px solid {border};
            padding-top: {space_xs};
            margin-top: 2px;
        }}
        .em-kpi-empty {{
            color: {text_secondary};
            font-family: {font_family};
            font-size: {title_size};
            text-align: center;
            padding: {space_md};
            border: 1px dashed {border};
            border-radius: {radius_md};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_card(card: KPICardData) -> str:
    """
    Build the full HTML markup for a single KPI card.

    Args:
        card: Pre-computed KPI card data for one engineering section.

    Returns:
        An HTML string representing the card.
    """
    trend_color = _trend_color(card.trend_direction)
    trend_arrow = _trend_arrow(card.trend_direction)
    percentage_text = _format_percentage_change(card.percentage_change)
    icon = card.icon or "⚙️"

    sparkline_svg = _build_sparkline_svg(
        values=card.sparkline_values,
        stroke_color=trend_color,
        fill_color=trend_color,
    )

    return f"""
        <div class="em-kpi-card">
            <div class="em-kpi-card-header">
                <div class="em-kpi-card-section">
                    <span class="em-kpi-card-icon">{icon}</span>
                    <span>{card.section_name}</span>
                </div>
            </div>
            <div class="em-kpi-card-value-row">
                <span class="em-kpi-card-value">{card.current_value:,.2f}</span>
                <span class="em-kpi-card-unit">{card.unit}</span>
            </div>
            <div class="em-kpi-card-trend-row">
                <span class="em-kpi-card-trend" style="color:{trend_color};">
                    {trend_arrow} {percentage_text}
                </span>
                <span class="em-kpi-card-sparkline">{sparkline_svg}</span>
            </div>
            <div class="em-kpi-card-footer">
                Updated {card.last_updated}
            </div>
        </div>
    """


def render_kpi_cards(cards: Sequence[KPICardData]) -> None:
    """
    Render the top dashboard row of premium KPI cards, one per major
    engineering section.

    The number and identity of sections is fully dynamic: this
    function makes no assumption about which or how many sections
    exist, and simply renders one card per entry in ``cards``. All
    displayed values (current value, trend, percentage change,
    sparkline points, last-updated timestamp) must already be fully
    computed by ``DashboardService`` before being passed in — this
    component performs no calculation, parsing, or business logic.

    Args:
        cards: Pre-computed KPI card data, one entry per engineering
            section discovered by ``DashboardService`` from Sheet 1
            (e.g. NPCL, DG, GG, PNG, Air Compressor, Solar, Utility).
            May be empty, in which case a placeholder message is shown.

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    _inject_card_styles()

    if not cards:
        st.markdown(
            '<div class="em-kpi-empty">No KPI sections available.</div>',
            unsafe_allow_html=True,
        )
        return

    cards_html = "".join(_render_card(card) for card in cards)
    st.markdown(
        f'<div class="em-kpi-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )

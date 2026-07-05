"""
components/summary_cards.py

Premium engineering summary cards for the Engineering Monitoring
Dashboard homepage (Streamlit-based, SCADA / Power BI aesthetic,
glassmorphism styling).

This module is the second-row counterpart to ``components/cards.py``.
Where the top KPI cards represent live, single-value engineering
metrics, these summary cards represent per-section aggregates (total,
average, last registered value) and are deliberately styled
differently — a left-edge accent strip, stacked stat rows, and a more
compact information-dense layout — so the two rows are visually
distinguishable at a glance.

This module is a PURE UI COMPONENT. It:
    - Contains no KPI calculations.
    - Performs no file parsing.
    - Performs no filtering.
    - Contains no business logic.
    - Contains no Streamlit page routing logic.

The default dashboard layout is configured with these sections: NPCL,
CLC, Blast, Dunkin, Freon, Air Compressor. This component does not
hardcode that list — it renders exactly one card per
``SummaryCardData`` entry it receives from the caller. If a configured
section is missing from the workbook, ``SummaryService`` simply omits
it from its output and no card is rendered for it; this component
performs no presence-checking or fallback logic of its own.

All visual tokens (colors, typography, spacing, radii, shadows) come
exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already
defined by the global design system in ``theme.py``.

Expected ``SummaryService`` output shape
---------------------------------------------------------------
This component expects the caller to have already transformed
``SummaryService`` output into a sequence of ``SummaryCardData``
instances — one per configured section that is present in the
workbook. It performs no aggregation, averaging, or totals math
itself; ``total``, ``average``, and ``last_registered_value`` must
already be fully computed upstream.

Expected ``THEME`` shape (defined in ``components/theme.py``)
---------------------------------------------------------------
See ``components/navbar.py`` for the full documented THEME contract
(``colors``, ``typography``, ``spacing``, ``radius``, ``shadow``).

Typical usage
-------------
    from components.summary_cards import (
        render_summary_cards,
        SummaryCardData,
    )

    cards = [
        SummaryCardData(
            section_name="NPCL",
            total=45210.5,
            average=1506.8,
            last_registered_value=1522.3,
            unit="kWh",
            last_updated="14:30:12",
        ),
        # ... one entry per configured section present in the workbook
    ]
    render_summary_cards(cards)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import streamlit as st

from components.theme import THEME

__all__ = ["SummaryCardData", "render_summary_cards"]


@dataclass(frozen=True)
class SummaryCardData:
    """
    Fully pre-computed data for a single section summary card.

    All values are expected to originate from ``SummaryService``
    output. This component performs no calculation on any field — it
    only renders what it is given.

    Attributes:
        section_name: Name of the configured engineering section
            (e.g. "NPCL", "CLC", "Blast", "Dunkin", "Freon",
            "Air Compressor"). The set of sections rendered is fully
            driven by whichever entries ``SummaryService`` returns.
        total: Pre-computed total value for the section.
        average: Pre-computed average value for the section.
        last_registered_value: The most recent recorded value for the
            section.
        unit: Unit label shared by ``total``, ``average``, and
            ``last_registered_value`` (e.g. "kWh", "m³", "bar").
        last_updated: Pre-formatted "last updated" timestamp string
            (e.g. "14:30:12" or "2 min ago").
        icon: Optional icon glyph/emoji representing the section. If
            ``None``, a neutral engineering placeholder glyph is used.
        accent_key: Optional semantic key ("positive", "negative",
            "neutral", or ``None``) used to color the left-edge accent
            strip. If ``None``, the strip uses the THEME primary/accent
            color rather than a trend-based color, since summary cards
            represent aggregates rather than live trend indicators.
    """

    section_name: str
    total: float
    average: float
    last_registered_value: float
    unit: str
    last_updated: str
    icon: Optional[str] = None
    accent_key: Optional[str] = None


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


def _accent_color(accent_key: Optional[str]) -> str:
    """
    Resolve the THEME color token used for a summary card's left-edge
    accent strip.

    Args:
        accent_key: One of "positive", "negative", "neutral", or
            ``None``. When ``None``, the THEME primary/accent color is
            used, since summary cards are not inherently trend-based.

    Returns:
        A CSS color value sourced from THEME, with a conventional
        fallback if THEME does not define the relevant token.
    """
    if accent_key == "positive":
        return _get(THEME, "colors", "positive", default="#3ddc84")
    if accent_key == "negative":
        return _get(THEME, "colors", "negative", default="#e35d5d")
    if accent_key == "neutral":
        return _get(THEME, "colors", "neutral", default="#8aa0b4")
    return _get(THEME, "colors", "primary", default="#4fd1c5")


def _format_value(value: float) -> str:
    """
    Format a numeric value for display with thousands separators and
    two decimal places.

    Args:
        value: The numeric value to format.

    Returns:
        A formatted display string (e.g. "45,210.50").
    """
    return f"{value:,.2f}"


def _inject_summary_card_styles() -> None:
    """
    Inject scoped CSS for the summary cards that maps THEME tokens onto
    summary-card-specific selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py``, and its class names (``em-summary-*``)
    are namespaced separately from the top KPI cards
    (``em-kpi-*``) so both rows can coexist with distinct appearances.

    Design distinction from top KPI cards:
        - Stacked label/value stat rows instead of one large hero value.
        - A left-edge vertical accent strip instead of a top icon-only
          header.
        - Slightly more angular corners and a denser information
          layout to signal "aggregate summary" rather than "live KPI".
    """
    surface = _get(THEME, "colors", "surface", default="#16202c")
    border = _get(THEME, "colors", "border", default="#2a3a4a")
    accent = _get(THEME, "colors", "primary", default="#4fd1c5")
    text_primary = _get(THEME, "colors", "text_primary", default="#e8edf2")
    text_secondary = _get(THEME, "colors", "text_secondary", default="#8aa0b4")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    title_size = _get(THEME, "typography", "title_size", default="1rem")
    label_size = _get(THEME, "typography", "label_size", default="0.72rem")
    value_size = _get(THEME, "typography", "value_size", default="1.05rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    radius_sm = _get(THEME, "radius", "sm", default="6px")
    radius_md = _get(THEME, "radius", "md", default="10px")
    shadow_sm = _get(THEME, "shadow", "sm", default="0 1px 4px rgba(0, 0, 0, 0.2)")
    shadow_md = _get(THEME, "shadow", "md", default="0 8px 24px rgba(0, 0, 0, 0.4)")

    st.markdown(
        f"""
        <style>
        .em-summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: {space_md};
            margin-bottom: {space_md};
            align-items: stretch;
        }}
        .em-summary-card {{
            position: relative;
            height: 100%;
            font-family: {font_family};
            background: linear-gradient(160deg, {surface}d9 0%, {surface}99 100%);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid {border};
            border-radius: {radius_sm};
            box-shadow: {shadow_sm};
            padding: {space_md} {space_md} {space_sm} calc({space_md} + 4px);
            display: flex;
            flex-direction: column;
            gap: {space_sm};
            overflow: hidden;
            transition: transform 0.18s ease-in-out, box-shadow 0.18s ease-in-out,
                border-color 0.18s ease-in-out;
        }}
        .em-summary-card::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--em-summary-accent, {accent});
        }}
        .em-summary-card:hover {{
            transform: translateY(-2px);
            box-shadow: {shadow_md};
            border-color: var(--em-summary-accent, {accent});
        }}
        .em-summary-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .em-summary-card-title {{
            display: flex;
            align-items: center;
            gap: {space_xs};
            color: {text_primary};
            font-size: {title_size};
            font-weight: 700;
            letter-spacing: 0.01em;
        }}
        .em-summary-card-icon {{
            color: var(--em-summary-accent, {accent});
            display: flex;
            align-items: center;
        }}
        .em-summary-card-stats {{
            display: flex;
            flex-direction: column;
            gap: {space_xs};
        }}
        .em-summary-stat-row {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            padding-bottom: {space_xs};
            border-bottom: 1px solid {border};
        }}
        .em-summary-stat-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .em-summary-stat-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .em-summary-stat-value {{
            color: {text_primary};
            font-size: {value_size};
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            text-align: right;
        }}
        .em-summary-stat-unit {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            margin-left: 4px;
        }}
        .em-summary-card-footer {{
            display: flex;
            align-items: center;
            justify-content: flex-end;
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 500;
            opacity: 0.85;
            margin-top: 2px;
        }}
        .em-summary-empty {{
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


def _render_stat_row(label: str, value: str, unit: Optional[str] = None) -> str:
    """
    Build the markup for a single labeled stat row within a summary
    card.

    Args:
        label: The stat's display label (e.g. "Total", "Average").
        value: The pre-formatted value string.
        unit: Optional unit label appended after the value.

    Returns:
        An HTML string for the stat row.
    """
    unit_html = f'<span class="em-summary-stat-unit">{unit}</span>' if unit else ""
    return f"""
        <div class="em-summary-stat-row">
            <span class="em-summary-stat-label">{label}</span>
            <span class="em-summary-stat-value">{value}{unit_html}</span>
        </div>
    """


def _render_card(card: SummaryCardData) -> str:
    """
    Build the full HTML markup for a single section summary card.

    Args:
        card: Pre-computed summary data for one configured section.

    Returns:
        An HTML string representing the card.
    """
    accent_color = _accent_color(card.accent_key)
    icon = card.icon or "📋"

    stats_html = "".join(
        [
            _render_stat_row("Total", _format_value(card.total), card.unit),
            _render_stat_row("Average", _format_value(card.average), card.unit),
            _render_stat_row(
                "Last Registered",
                _format_value(card.last_registered_value),
                card.unit,
            ),
        ]
    )

    return f"""
        <div class="em-summary-card" style="--em-summary-accent: {accent_color};">
            <div class="em-summary-card-header">
                <div class="em-summary-card-title">
                    <span class="em-summary-card-icon">{icon}</span>
                    <span>{card.section_name}</span>
                </div>
            </div>
            <div class="em-summary-card-stats">
                {stats_html}
            </div>
            <div class="em-summary-card-footer">
                Updated {card.last_updated}
            </div>
        </div>
    """


def render_summary_cards(cards: Sequence[SummaryCardData]) -> None:
    """
    Render the second dashboard row of premium section summary cards.

    Exactly one card is rendered per entry in ``cards``. If a
    configured section (e.g. NPCL, CLC, Blast, Dunkin, Freon,
    Air Compressor) is missing from the workbook, ``SummaryService``
    is expected to have already omitted it from its output; this
    component performs no presence-checking, filtering, or fallback
    logic of its own — it purely renders whatever it is given.

    Args:
        cards: Pre-computed summary card data, one entry per configured
            section present in the workbook, as produced by
            ``SummaryService``. May be empty, in which case a
            placeholder message is shown.

    Returns:
        None. This function renders directly into the current
        Streamlit app context.
    """
    _inject_summary_card_styles()

    if not cards:
        st.markdown(
            '<div class="em-summary-empty">No summary sections available.</div>',
            unsafe_allow_html=True,
        )
        return

    cards_html = "".join(_render_card(card) for card in cards)
    st.markdown(
        f'<div class="em-summary-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )

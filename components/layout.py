"""Reusable layout helpers for the engineering monitoring dashboard.

This module provides small, composable functions for arranging the
dashboard's UI: page containers, responsive column grids, card grids,
section containers, header layout, KPI layout, summary card layout, and
expandable section layout. Every helper renders using the design tokens
defined in :mod:`components.theme`.

This module contains:

* No business logic (no KPI math, no filtering, no data access).
* No Streamlit *page* code (no ``st.set_page_config``, no navigation).

Each helper accepts already-computed display data (strings, numbers,
lists of simple values) and is responsible only for arranging and
styling that data on the page.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List, Optional, Sequence

import streamlit as st

from components.theme import THEME, get_status_color, get_trend_color


# ----------------------------------------------------------------------
# Page-level containers
# ----------------------------------------------------------------------

def configure_page(title: str, icon: str = "\U0001F3ED") -> None:
    """Configures Streamlit's page settings for a wide, dark dashboard.

    Should be called once, as the first Streamlit call on a page.

    Args:
        title: The browser tab title.
        icon: The browser tab icon (an emoji or a path to an image).
    """
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_global_styles(css: str) -> None:
    """Injects the dashboard's global CSS block into the current page.

    Args:
        css: The CSS block to inject, typically the output of
            :func:`components.theme.get_global_css`.
    """
    st.markdown(css, unsafe_allow_html=True)


@contextmanager
def page_container() -> Iterator[None]:
    """Opens a top-level page container for consistent outer spacing.

    Usage::

        with page_container():
            ... page content ...

    Yields:
        ``None``. The container is closed automatically on exit.
    """
    st.markdown('<div class="emd-page-container">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def render_divider() -> None:
    """Renders a themed horizontal divider between page sections."""
    st.markdown('<hr class="emd-divider" />', unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Responsive columns / card grids
# ----------------------------------------------------------------------

def responsive_columns(count: int, gap: str = "medium") -> List:
    """Creates an evenly weighted row of Streamlit columns.

    Args:
        count: The number of columns to create. Values below 1 are
            clamped to 1.
        gap: The gap size between columns, passed through to
            ``st.columns`` (``"small"``, ``"medium"``, or ``"large"``).

    Returns:
        The list of column objects returned by ``st.columns``.
    """
    safe_count = max(1, count)
    return st.columns(safe_count, gap=gap)


def card_grid(item_count: int, max_columns: int = 4, gap: str = "medium") -> List:
    """Creates a card grid with a sensible column count for the item count.

    Chooses a number of columns that keeps cards a comfortable width:
    never more columns than items, and never more than ``max_columns``,
    which keeps the grid readable on the dashboard's wide, full-width
    layout without producing awkwardly narrow cards when there are only
    a few items.

    Args:
        item_count: The number of cards that will be placed in the grid.
        max_columns: The maximum number of columns to use, regardless of
            ``item_count``. Defaults to ``4``.
        gap: The gap size between columns.

    Returns:
        The list of column objects to place cards into, one item per
        column, wrapping row by row as the caller iterates.
    """
    if item_count <= 0:
        return []
    column_count = min(max_columns, item_count)
    return responsive_columns(column_count, gap=gap)


@contextmanager
def card(compact: bool = False) -> Iterator[None]:
    """Opens a single glassmorphic card container.

    Usage::

        with card():
            st.write("card content")

    Args:
        compact: Whether to use the card's more tightly padded variant.

    Yields:
        ``None``. The card ``div`` is closed automatically on exit.
    """
    css_class = "emd-card emd-card--compact" if compact else "emd-card"
    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Section containers
# ----------------------------------------------------------------------

@contextmanager
def section_container(heading: Optional[str] = None) -> Iterator[None]:
    """Opens a page section container with consistent vertical spacing.

    Args:
        heading: An optional section heading rendered above the
            section's content.

    Yields:
        ``None``. The section ``div`` is closed automatically on exit.
    """
    st.markdown('<div class="emd-section-container">', unsafe_allow_html=True)
    if heading:
        st.markdown(
            f'<div class="emd-section-heading">{heading}</div>',
            unsafe_allow_html=True,
        )
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Header layout
# ----------------------------------------------------------------------

def render_header(
    title: str,
    subtitle: Optional[str] = None,
    badges: Optional[Sequence[dict]] = None,
) -> None:
    """Renders the dashboard's top header bar.

    Args:
        title: The main title text (typically the workbook name).
        subtitle: An optional line of supporting text (for example the
            active date range).
        badges: An optional sequence of badge specs, each a mapping with
            ``"label"`` (str) and optionally ``"status"`` (one of
            ``"success"``, ``"warning"``, ``"danger"``, ``"info"``,
            defaulting to a neutral color when omitted). Rendered as
            small pill badges to the right of the title, for example
            validation status or last-refreshed indicators.
    """
    st.markdown('<div class="emd-header">', unsafe_allow_html=True)

    header_columns = st.columns([3, 1]) if badges else st.columns([1])
    with header_columns[0]:
        st.markdown(f'<p class="emd-title">{title}</p>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(
                f'<p class="emd-subtitle">{subtitle}</p>', unsafe_allow_html=True
            )

    if badges:
        with header_columns[1]:
            badge_html = "".join(
                _render_badge_html(badge.get("label", ""), badge.get("status"))
                for badge in badges
            )
            st.markdown(
                f'<div style="text-align:right;">{badge_html}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_badge_html(label: str, status: Optional[str]) -> str:
    """Builds the HTML for a single header badge.

    Args:
        label: The badge's display text.
        status: An optional semantic status keyword (see
            :func:`components.theme.get_status_color`).

    Returns:
        The badge's HTML fragment.
    """
    color = get_status_color(status) if status else THEME.colors.text_secondary
    return (
        f'<span class="emd-badge" style="color:{color}; '
        f'border-color:{color}44; margin-left: {THEME.spacing.sm};">{label}</span>'
    )


# ----------------------------------------------------------------------
# KPI layout
# ----------------------------------------------------------------------

def render_kpi_card(
    label: str,
    value: str,
    unit: str = "",
    trend: Optional[str] = None,
    delta_text: Optional[str] = None,
) -> None:
    """Renders a single KPI card inside the current layout context.

    Intended to be called once per column produced by
    :func:`card_grid` or :func:`responsive_columns`.

    Args:
        label: The KPI's label (for example ``"Total Energy"``).
        value: The KPI's already-formatted headline value (for example
            ``"1,204.5"``). Formatting numbers is the caller's
            responsibility; this helper only arranges and styles them.
        unit: An optional unit suffix shown next to the value (for
            example ``"kWh"``).
        trend: An optional trend direction keyword (``"increasing"``,
            ``"decreasing"``, ``"stable"``), used to color
            ``delta_text``.
        delta_text: An optional already-formatted delta string (for
            example ``"+4.2%"``), shown below the value.
    """
    with card(compact=True):
        st.markdown(f'<div class="emd-kpi-label">{label}</div>', unsafe_allow_html=True)
        unit_html = f'<span class="emd-kpi-unit">{unit}</span>' if unit else ""
        st.markdown(
            f'<div class="emd-kpi-value">{value}{unit_html}</div>',
            unsafe_allow_html=True,
        )
        if delta_text:
            color = get_trend_color(trend) if trend else THEME.colors.text_secondary
            st.markdown(
                f'<div style="color:{color}; font-size:{THEME.typography.size_small}; '
                f'margin-top:{THEME.spacing.xs};">{delta_text}</div>',
                unsafe_allow_html=True,
            )


def render_kpi_row(kpis: Sequence[dict], max_columns: int = 4) -> None:
    """Renders a full row of KPI cards from plain data.

    Args:
        kpis: A sequence of KPI specs, each a mapping accepted as
            keyword arguments by :func:`render_kpi_card` (``"label"``,
            ``"value"``, and optionally ``"unit"``, ``"trend"``,
            ``"delta_text"``).
        max_columns: The maximum number of columns in the row.
    """
    if not kpis:
        return
    columns = card_grid(len(kpis), max_columns=max_columns)
    for column, kpi in zip(columns, kpis):
        with column:
            render_kpi_card(
                label=kpi.get("label", ""),
                value=kpi.get("value", ""),
                unit=kpi.get("unit", ""),
                trend=kpi.get("trend"),
                delta_text=kpi.get("delta_text"),
            )


# ----------------------------------------------------------------------
# Summary card layout
# ----------------------------------------------------------------------

def render_summary_card(
    title: str,
    metrics: Sequence[dict],
    status: Optional[str] = None,
) -> None:
    """Renders a single homepage summary card for one section.

    Args:
        title: The section's display name (for example ``"NPCL"``).
        metrics: A sequence of small metric specs to show inside the
            card, each a mapping with ``"label"`` and ``"value"`` (and
            optionally ``"unit"``).
        status: An optional semantic status keyword used to color a
            small indicator dot next to the title (see
            :func:`components.theme.get_status_color`).
    """
    with card():
        indicator_html = ""
        if status:
            color = get_status_color(status)
            indicator_html = (
                f'<span style="display:inline-block; width:8px; height:8px; '
                f'border-radius:50%; background:{color}; '
                f'margin-right:{THEME.spacing.sm};"></span>'
            )
        st.markdown(
            f'<div class="emd-panel-heading">{indicator_html}{title}</div>',
            unsafe_allow_html=True,
        )
        for metric in metrics:
            label = metric.get("label", "")
            value = metric.get("value", "")
            unit = metric.get("unit", "")
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; '
                f'padding:{THEME.spacing.xs} 0; '
                f'border-bottom:1px solid {THEME.colors.border};">'
                f'<span style="color:{THEME.colors.text_secondary}; '
                f'font-size:{THEME.typography.size_small};">{label}</span>'
                f'<span style="color:{THEME.colors.text_primary}; '
                f'font-family:{THEME.typography.font_family_mono}; '
                f'font-weight:{THEME.typography.weight_medium};">{value} '
                f'<span style="color:{THEME.colors.text_muted}; '
                f'font-size:{THEME.typography.size_small};">{unit}</span></span>'
                f"</div>",
                unsafe_allow_html=True,
            )


def render_summary_card_grid(cards: Sequence[dict], max_columns: int = 3) -> None:
    """Renders the homepage's fixed grid of summary cards.

    Args:
        cards: A sequence of summary card specs, each a mapping accepted
            as keyword arguments by :func:`render_summary_card`
            (``"title"``, ``"metrics"``, and optionally ``"status"``).
        max_columns: The maximum number of columns in the grid.
    """
    if not cards:
        return
    columns = card_grid(len(cards), max_columns=max_columns)
    for index, spec in enumerate(cards):
        with columns[index % len(columns)]:
            render_summary_card(
                title=spec.get("title", ""),
                metrics=spec.get("metrics", []),
                status=spec.get("status"),
            )


# ----------------------------------------------------------------------
# Expandable section layout
# ----------------------------------------------------------------------

@contextmanager
def expandable_section(title: str, expanded: bool = False) -> Iterator[None]:
    """Opens a themed expandable panel for one engineering section.

    Usage::

        with expandable_section("Air Compressor"):
            render_kpi_row(kpis)
            st.plotly_chart(figure, use_container_width=True)

    Args:
        title: The section's display name, shown as the expander's
            label.
        expanded: Whether the panel should start expanded.

    Yields:
        ``None``. Content written inside the ``with`` block is placed
        inside the expander, itself wrapped in a themed card.
    """
    with st.expander(title, expanded=expanded):
        with card():
            yield


def render_expandable_sections(sections: Sequence[dict]) -> None:
    """Renders a sequence of expandable sections from plain data.

    Each section's inner content is provided as a zero-argument
    callable, so this helper stays free of any business logic about
    *what* to render — it only arranges the expanders.

    Args:
        sections: A sequence of section specs, each a mapping with
            ``"title"`` (str), ``"render"`` (a zero-argument callable
            that renders the section's body using other layout/UI
            helpers), and optionally ``"expanded"`` (bool).
    """
    for spec in sections:
        with expandable_section(
            title=spec.get("title", ""), expanded=spec.get("expanded", False)
        ):
            render_fn = spec.get("render")
            if callable(render_fn):
                render_fn()

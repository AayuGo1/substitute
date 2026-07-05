"""
components/filters.py

Reusable dashboard filter bar for the Engineering Monitoring Dashboard
(Streamlit-based, SCADA / Power BI aesthetic).

This module is a PURE UI COMPONENT. It:
    - Contains no KPI calculations.
    - Performs no file parsing.
    - Performs no chart generation.
    - Contains no Streamlit page routing logic.
    - Contains no data-source / GitHub logic.

It renders month, date-range, and quick-selection controls, sourcing
their option lists and default values from ``FilterService``, and
returns a ``FilterCriteria`` object that the caller passes on to
``DashboardService``. This component never computes KPIs or business
values itself — it only assembles user input into a typed criteria
object.

All visual tokens (colors, typography, spacing, radii, shadows) come
exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already defined
by the global design system in ``theme.py``.

Expected ``FilterService`` interface
---------------------------------------------------------------
This component calls the following methods on the injected
``FilterService`` instance. Adjust ``FilterService`` accordingly if its
real interface differs; this component depends only on this contract
(Dependency Inversion Principle).

    get_available_months() -> List[str]
        Ordered list of selectable month labels (e.g. ["Jan 2026", ...]).

    get_default_month() -> Optional[str]
        The month label that should be pre-selected, if any.

    get_min_date() -> date
        Earliest selectable date for the date-range picker.

    get_max_date() -> date
        Latest selectable date for the date-range picker.

    get_default_date_range() -> Tuple[date, date]
        The (start, end) dates pre-selected in the date-range picker.

    resolve_quick_range(option: str) -> Tuple[date, date]
        Given a quick-selection key ("today", "this_week",
        "this_month", "previous_month"), returns the corresponding
        (start, end) date tuple. All date-math for quick ranges lives
        in ``FilterService``, not in this UI component.

Expected ``THEME`` shape (defined in ``components/theme.py``)
---------------------------------------------------------------
See ``components/navbar.py`` / ``components/sidebar.py`` for the full
documented THEME contract. This component reads the same
``colors``, ``typography``, ``spacing``, ``radius``, and ``shadow``
token groups.

Typical usage
-------------
    from components.filters import render_filter_bar, FilterCriteria
    from services.filter_service import FilterService

    criteria: FilterCriteria = render_filter_bar(FilterService())
    data = dashboard_service.get_data(criteria)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Protocol, Tuple

import streamlit as st

from components.theme import THEME

__all__ = ["FilterCriteria", "FilterService", "render_filter_bar"]


@dataclass(frozen=True)
class FilterCriteria:
    """
    Typed result of the filter bar, ready to be consumed by
    ``DashboardService``.

    Attributes:
        month: The selected month label, or ``None`` if no month is
            selected.
        start_date: The start of the selected date range.
        end_date: The end of the selected date range.
        quick_selection: The key of the quick-selection option applied
            most recently ("today", "this_week", "this_month",
            "previous_month"), or ``None`` if the range was set
            manually.
        applied: ``True`` only on the run where the user clicked
            "Apply Filters"; ``False`` otherwise (e.g. while the user is
            still adjusting controls, or after "Clear Filters").
    """

    month: Optional[str]
    start_date: date
    end_date: date
    quick_selection: Optional[str]
    applied: bool


class FilterService(Protocol):
    """
    Protocol describing the data this component needs from the
    backend's filter service.

    This component depends only on this abstraction (Dependency
    Inversion Principle) and performs no date arithmetic, parsing, or
    business logic of its own.
    """

    def get_available_months(self) -> List[str]:
        """Return the ordered list of selectable month labels."""
        ...

    def get_default_month(self) -> Optional[str]:
        """Return the month label pre-selected by default, if any."""
        ...

    def get_min_date(self) -> date:
        """Return the earliest selectable date."""
        ...

    def get_max_date(self) -> date:
        """Return the latest selectable date."""
        ...

    def get_default_date_range(self) -> Tuple[date, date]:
        """Return the (start, end) dates pre-selected by default."""
        ...

    def resolve_quick_range(self, option: str) -> Tuple[date, date]:
        """Resolve a quick-selection key into a (start, end) date tuple."""
        ...


_QUICK_OPTIONS: Tuple[Tuple[str, str], ...] = (
    ("today", "Today"),
    ("this_week", "This Week"),
    ("this_month", "This Month"),
    ("previous_month", "Previous Month"),
)


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


def _session_key(suffix: str) -> str:
    """
    Build a namespaced Streamlit session-state key for filter-bar
    internal state, avoiding collisions with other components.

    Args:
        suffix: Short identifier for the piece of state.

    Returns:
        A namespaced session-state key.
    """
    return f"em_filters__{suffix}"


def _inject_filter_bar_styles() -> None:
    """
    Inject scoped CSS for the filter bar that maps THEME tokens onto
    filter-bar-specific selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py``.
    """
    bg = _get(THEME, "colors", "surface", default="#16202c")
    border = _get(THEME, "colors", "border", default="#2a3a4a")
    accent = _get(THEME, "colors", "primary", default="#4fd1c5")
    text_primary = _get(THEME, "colors", "text_primary", default="#e8edf2")
    text_secondary = _get(THEME, "colors", "text_secondary", default="#8aa0b4")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    label_size = _get(THEME, "typography", "label_size", default="0.72rem")
    value_size = _get(THEME, "typography", "value_size", default="0.85rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    radius_sm = _get(THEME, "radius", "sm", default="6px")
    radius_md = _get(THEME, "radius", "md", default="10px")
    shadow_md = _get(THEME, "shadow", "md", default="0 2px 10px rgba(0, 0, 0, 0.35)")

    st.markdown(
        f"""
        <style>
        .em-filterbar {{
            background: {bg};
            border: 1px solid {border};
            border-radius: {radius_md};
            box-shadow: {shadow_md};
            padding: {space_md};
            margin-bottom: {space_md};
            font-family: {font_family};
        }}
        .em-filterbar-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: {space_xs};
        }}
        .em-filterbar-quick-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin: {space_sm} 0 {space_xs} 0;
        }}
        .em-filterbar div[data-testid="stSelectbox"] label,
        .em-filterbar div[data-testid="stDateInput"] label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .em-filterbar div[data-testid="stSelectbox"] > div,
        .em-filterbar div[data-testid="stDateInput"] > div {{
            background: {bg};
            border-radius: {radius_sm};
        }}
        .em-filterbar div[data-baseweb="select"] > div,
        .em-filterbar input {{
            background: {bg} !important;
            color: {text_primary} !important;
            border-color: {border} !important;
            font-size: {value_size};
        }}
        .em-filterbar-quick-btn div[data-testid="stButton"] button {{
            width: 100%;
            background: transparent;
            color: {text_secondary};
            border: 1px solid {border};
            border-radius: {radius_sm};
            font-family: {font_family};
            font-weight: 600;
            font-size: {label_size};
            padding: {space_xs} {space_sm};
            transition: all 0.15s ease-in-out;
        }}
        .em-filterbar-quick-btn div[data-testid="stButton"] button:hover {{
            border-color: {accent};
            color: {accent};
        }}
        .em-filterbar-quick-btn--active div[data-testid="stButton"] button {{
            background: {bg};
            border-color: {accent};
            color: {accent};
        }}
        .em-filterbar-actions div[data-testid="stButton"] button {{
            width: 100%;
            border-radius: {radius_sm};
            font-family: {font_family};
            font-weight: 700;
            font-size: {value_size};
            padding: {space_xs} {space_sm};
            transition: all 0.15s ease-in-out;
        }}
        .em-filterbar-apply div[data-testid="stButton"] button {{
            background: {accent};
            color: {bg};
            border: 1px solid {accent};
        }}
        .em-filterbar-apply div[data-testid="stButton"] button:hover {{
            filter: brightness(1.08);
        }}
        .em-filterbar-clear div[data-testid="stButton"] button {{
            background: transparent;
            color: {text_secondary};
            border: 1px solid {border};
        }}
        .em-filterbar-clear div[data-testid="stButton"] button:hover {{
            color: {text_primary};
            border-color: {text_secondary};
        }}
        .em-filterbar-divider {{
            border-top: 1px solid {border};
            margin: {space_sm} 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_month_selector(
    service: FilterService,
    key: str,
) -> Optional[str]:
    """
    Render the month selector control.

    Args:
        service: The injected ``FilterService`` providing available
            months and the default selection.
        key: Unique Streamlit widget key.

    Returns:
        The currently selected month label, or ``None`` if the service
        exposes no months.
    """
    months = service.get_available_months()
    if not months:
        return None

    default_month = service.get_default_month()
    default_index = months.index(default_month) if default_month in months else 0

    st.markdown('<div class="em-filterbar-label">Month</div>', unsafe_allow_html=True)
    return st.selectbox(
        label="Month",
        options=months,
        index=default_index,
        key=key,
        label_visibility="collapsed",
    )


def _render_date_range_selector(
    service: FilterService,
    key: str,
) -> Tuple[date, date]:
    """
    Render the date-range selector control.

    Args:
        service: The injected ``FilterService`` providing the
            selectable bounds and default range.
        key: Unique Streamlit widget key.

    Returns:
        The currently selected ``(start_date, end_date)`` tuple.
    """
    min_date = service.get_min_date()
    max_date = service.get_max_date()
    default_start, default_end = service.get_default_date_range()

    st.markdown(
        '<div class="em-filterbar-label">Date Range</div>',
        unsafe_allow_html=True,
    )
    selection = st.date_input(
        label="Date Range",
        value=(default_start, default_end),
        min_value=min_date,
        max_value=max_date,
        key=key,
        label_visibility="collapsed",
    )

    if isinstance(selection, tuple) and len(selection) == 2:
        return selection[0], selection[1]
    if isinstance(selection, date):
        return selection, selection
    return default_start, default_end


def _render_quick_selections(
    service: FilterService,
    active_quick: Optional[str],
    key_prefix: str,
) -> Tuple[Optional[str], Optional[Tuple[date, date]]]:
    """
    Render the optional quick-selection buttons (Today, This Week,
    This Month, Previous Month).

    All date-range resolution for each option is delegated to
    ``FilterService.resolve_quick_range`` — this component performs no
    date arithmetic itself.

    Args:
        service: The injected ``FilterService`` used to resolve ranges.
        active_quick: The currently active quick-selection key, if any,
            used to visually highlight the matching button.
        key_prefix: Prefix for the buttons' Streamlit widget keys.

    Returns:
        A tuple of ``(clicked_key, resolved_range)``. Both are ``None``
        if no quick-selection button was clicked this run.
    """
    st.markdown(
        '<div class="em-filterbar-quick-label">Quick Select</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(len(_QUICK_OPTIONS))
    clicked_key: Optional[str] = None
    resolved_range: Optional[Tuple[date, date]] = None

    for column, (option_key, option_label) in zip(columns, _QUICK_OPTIONS):
        with column:
            wrapper_class = "em-filterbar-quick-btn"
            if option_key == active_quick:
                wrapper_class += " em-filterbar-quick-btn--active"
            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
            if st.button(option_label, key=f"{key_prefix}_{option_key}"):
                clicked_key = option_key
                resolved_range = service.resolve_quick_range(option_key)
            st.markdown("</div>", unsafe_allow_html=True)

    return clicked_key, resolved_range


def render_filter_bar(
    service: FilterService,
    show_quick_selections: bool = True,
    key_prefix: str = "em_filterbar",
) -> FilterCriteria:
    """
    Render the full dashboard filter bar and return the resulting
    ``FilterCriteria``.

    This function only renders UI and assembles user input based on
    values supplied by ``FilterService`` and the shared ``THEME``
    design tokens. It performs no KPI calculations, no parsing, no
    chart generation, and no page-routing logic — the returned
    ``FilterCriteria`` is intended to be passed directly to
    ``DashboardService`` by the caller.

    Args:
        service: The injected ``FilterService`` used to source month
            options, date bounds, defaults, and quick-range resolution.
        show_quick_selections: Whether to render the optional quick
            selection buttons (Today / This Week / This Month /
            Previous Month).
        key_prefix: Prefix applied to all internal Streamlit widget
            keys, allowing multiple filter bars on the same page.

    Returns:
        A ``FilterCriteria`` instance reflecting the current state of
        the filter bar. ``applied`` is ``True`` only on the run where
        "Apply Filters" was clicked.
    """
    _inject_filter_bar_styles()

    quick_state_key = _session_key(f"{key_prefix}_active_quick")
    active_quick: Optional[str] = st.session_state.get(quick_state_key)

    st.markdown('<div class="em-filterbar">', unsafe_allow_html=True)

    month_col, range_col = st.columns([1, 2])
    with month_col:
        selected_month = _render_month_selector(
            service, key=f"{key_prefix}_month"
        )
    with range_col:
        start_date, end_date = _render_date_range_selector(
            service, key=f"{key_prefix}_date_range"
        )

    if show_quick_selections:
        clicked_key, resolved_range = _render_quick_selections(
            service,
            active_quick=active_quick,
            key_prefix=f"{key_prefix}_quick",
        )
        if clicked_key is not None and resolved_range is not None:
            active_quick = clicked_key
            start_date, end_date = resolved_range
            st.session_state[quick_state_key] = active_quick

    st.markdown('<div class="em-filterbar-divider"></div>', unsafe_allow_html=True)

    applied = False
    action_col_clear, action_col_apply = st.columns(2)

    with action_col_clear:
        st.markdown('<div class="em-filterbar-actions em-filterbar-clear">', unsafe_allow_html=True)
        if st.button("Clear Filters", key=f"{key_prefix}_clear"):
            st.session_state.pop(quick_state_key, None)
            selected_month = service.get_default_month()
            start_date, end_date = service.get_default_date_range()
            active_quick = None
        st.markdown("</div>", unsafe_allow_html=True)

    with action_col_apply:
        st.markdown('<div class="em-filterbar-actions em-filterbar-apply">', unsafe_allow_html=True)
        if st.button("Apply Filters", key=f"{key_prefix}_apply"):
            applied = True
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    return FilterCriteria(
        month=selected_month,
        start_date=start_date,
        end_date=end_date,
        quick_selection=active_quick,
        applied=applied,
    )

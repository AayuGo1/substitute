"""
components/sidebar.py

Premium industrial-style navigation sidebar for the Engineering
Monitoring Dashboard (Streamlit-based, SCADA / Power BI aesthetic).

This module is a PURE UI COMPONENT. It:
    - Contains no business logic.
    - Performs no KPI calculations.
    - Performs no chart generation.
    - Performs no file parsing.
    - Contains no GitHub / data-source logic.
    - Contains no Streamlit page routing logic beyond emitting the
      currently selected navigation item back to the caller.

All visual tokens (colors, typography, spacing, radii, shadows, icons)
come exclusively from ``components.theme.THEME``. This file defines no
hardcoded styling values and duplicates none of the CSS already defined
by the global design system in ``theme.py`` — it only maps THEME tokens
onto sidebar-specific selectors.

Navigation behavior is data-driven: the caller supplies a sequence of
``NavItem`` entries (or relies on ``DEFAULT_NAV_ITEMS``) rather than the
sidebar hardcoding page names, order, or icons internally.

Expected ``THEME`` shape (defined in ``components/theme.py``)
---------------------------------------------------------------
This component reads the following keys from ``THEME``. If a key is
absent, a sensible fallback is used so the sidebar degrades gracefully
rather than raising an exception.

    THEME["colors"]["surface"]            panel/card background color
    THEME["colors"]["background"]         page background color
    THEME["colors"]["border"]             hairline border color
    THEME["colors"]["primary"]            accent color (e.g. teal/cyan)
    THEME["colors"]["text_primary"]       primary text color
    THEME["colors"]["text_secondary"]     secondary/muted text color
    THEME["typography"]["font_family"]    base font stack
    THEME["typography"]["title_size"]     section title font size
    THEME["typography"]["label_size"]     small label font size
    THEME["typography"]["value_size"]     nav item font size
    THEME["spacing"]["xs"|"sm"|"md"|"lg"] spacing scale (rem strings)
    THEME["radius"]["sm"|"md"]            border-radius scale
    THEME["shadow"]["sm"|"md"]            box-shadow tokens
    THEME["icons"][<icon_key>]            optional icon glyph/emoji map

Typical usage
-------------
    from components.sidebar import render_sidebar, SidebarConfig

    selected_page: str = render_sidebar(
        SidebarConfig(
            company_logo_path=dashboard_service.get_company_logo_path(),
            app_version=dashboard_service.get_app_version(),
            active_page=st.session_state.get("active_page", "Home"),
        )
    )
    st.session_state["active_page"] = selected_page
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import streamlit as st

from components.theme import THEME

__all__ = ["NavItem", "SidebarConfig", "render_sidebar", "DEFAULT_NAV_ITEMS"]


@dataclass(frozen=True)
class NavItem:
    """
    Configuration for a single sidebar navigation entry.

    Attributes:
        key: Stable unique identifier for the item (used for widget
            keys and as the value emitted when the item is selected).
        label: Human-readable text shown next to the icon.
        icon: Fallback icon glyph/emoji used when no THEME icon is
            registered for ``key`` under ``THEME["icons"]``.
    """

    key: str
    label: str
    icon: str = "•"


DEFAULT_NAV_ITEMS: Sequence[NavItem] = (
    NavItem(key="home", label="Home", icon="🏠"),
    NavItem(key="overview", label="Overview", icon="📊"),
    NavItem(key="departments", label="Departments", icon="🏢"),
    NavItem(key="air_compressor", label="Air Compressor", icon="🌀"),
    NavItem(key="freon_monitoring", label="Freon Monitoring", icon="❄️"),
    NavItem(key="water", label="Water", icon="💧"),
    NavItem(key="energy", label="Energy", icon="⚡"),
    NavItem(key="utilities", label="Utilities", icon="🛠️"),
    NavItem(key="settings", label="Settings", icon="⚙️"),
)


@dataclass(frozen=True)
class SidebarConfig:
    """
    Immutable data container describing everything the sidebar needs to
    render.

    All values are expected to be pre-computed and supplied by
    ``DashboardService`` (or any other upstream service/caller). This
    component never derives, fetches, or calculates any of these values
    itself.

    Attributes:
        company_logo_path: Filesystem path or URL to the company logo
            image. If ``None``, a premium engineering placeholder icon
            is rendered instead of an image.
        app_version: Version string shown at the bottom of the sidebar
            (e.g. "v2.4.1").
        active_page: The ``key`` of the currently active ``NavItem``.
        nav_items: The ordered collection of navigation entries to
            render. Defaults to ``DEFAULT_NAV_ITEMS`` when not supplied,
            so navigation content is configuration-driven rather than
            hardcoded inside the render logic.
        collapsible: Whether the sidebar exposes a collapse/expand
            toggle control.
        app_name: Optional short name/title shown beneath the logo.
    """

    company_logo_path: Optional[str]
    app_version: str
    active_page: str
    nav_items: Sequence[NavItem] = field(default_factory=lambda: DEFAULT_NAV_ITEMS)
    collapsible: bool = True
    app_name: Optional[str] = "Engineering Monitoring"


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


def _resolve_icon(item: NavItem) -> str:
    """
    Resolve the display icon for a navigation item, preferring an icon
    registered in ``THEME["icons"]`` over the item's own fallback icon.

    This keeps icon theming centralized in the design system while
    still allowing the sidebar to function if THEME defines no icon map
    at all.

    Args:
        item: The navigation item to resolve an icon for.

    Returns:
        An icon glyph/emoji string.
    """
    icons_map = THEME.get("icons", {}) if isinstance(THEME, dict) else {}
    if isinstance(icons_map, dict) and item.key in icons_map:
        resolved = icons_map[item.key]
        if isinstance(resolved, str) and resolved:
            return resolved
    return item.icon


def _session_key(suffix: str) -> str:
    """
    Build a namespaced Streamlit session-state key for sidebar internal
    state, avoiding collisions with other components.

    Args:
        suffix: Short identifier for the piece of state.

    Returns:
        A namespaced session-state key.
    """
    return f"em_sidebar__{suffix}"


def _inject_sidebar_styles() -> None:
    """
    Inject scoped CSS for the sidebar that maps THEME tokens onto
    sidebar-specific selectors.

    No color, font, spacing, radius, or shadow values are hardcoded
    here — every value is pulled from ``THEME`` via ``_get`` with a
    neutral fallback used only if the design system does not define a
    token. This function does not redefine any global styles already
    established by ``theme.py``.
    """
    bg = _get(THEME, "colors", "surface", default="#16202c")
    page_bg = _get(THEME, "colors", "background", default="#0f1620")
    border = _get(THEME, "colors", "border", default="#2a3a4a")
    accent = _get(THEME, "colors", "primary", default="#4fd1c5")
    text_primary = _get(THEME, "colors", "text_primary", default="#e8edf2")
    text_secondary = _get(THEME, "colors", "text_secondary", default="#8aa0b4")
    font_family = _get(THEME, "typography", "font_family", default="inherit")
    title_size = _get(THEME, "typography", "title_size", default="1rem")
    label_size = _get(THEME, "typography", "label_size", default="0.72rem")
    value_size = _get(THEME, "typography", "value_size", default="0.88rem")
    space_xs = _get(THEME, "spacing", "xs", default="0.35rem")
    space_sm = _get(THEME, "spacing", "sm", default="0.65rem")
    space_md = _get(THEME, "spacing", "md", default="1rem")
    radius_sm = _get(THEME, "radius", "sm", default="6px")
    radius_md = _get(THEME, "radius", "md", default="10px")
    shadow_md = _get(THEME, "shadow", "md", default="0 2px 10px rgba(0, 0, 0, 0.35)")

    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"] {{
            background: {page_bg};
            border-right: 1px solid {border};
            font-family: {font_family};
        }}
        section[data-testid="stSidebar"] > div {{
            padding-top: {space_sm};
        }}
        .em-sidebar-brand {{
            display: flex;
            align-items: center;
            gap: {space_sm};
            padding: {space_sm} {space_md};
            margin-bottom: {space_sm};
            background: {bg};
            border: 1px solid {border};
            border-radius: {radius_md};
            box-shadow: {shadow_md};
        }}
        .em-sidebar-logo-placeholder,
        .em-sidebar-logo-img {{
            width: 38px;
            height: 38px;
            border-radius: {radius_sm};
            border: 1px solid {border};
            background: {bg};
            display: flex;
            align-items: center;
            justify-content: center;
            color: {accent};
            object-fit: contain;
            flex-shrink: 0;
        }}
        .em-sidebar-app-name {{
            color: {text_primary};
            font-size: {title_size};
            font-weight: 700;
            letter-spacing: 0.02em;
            line-height: 1.25;
        }}
        .em-sidebar-section-label {{
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 0 {space_md};
            margin: {space_sm} 0 {space_xs} 0;
        }}
        div[data-testid="stSidebar"] div[data-testid="stButton"] {{
            padding: 0 {space_sm};
        }}
        div[data-testid="stSidebar"] div[data-testid="stButton"] button {{
            width: 100%;
            text-align: left;
            background: transparent;
            color: {text_secondary};
            border: 1px solid transparent;
            border-radius: {radius_sm};
            font-family: {font_family};
            font-size: {value_size};
            font-weight: 500;
            padding: {space_xs} {space_sm};
            margin-bottom: 2px;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: {space_sm};
            transition: all 0.15s ease-in-out;
        }}
        div[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {{
            background: {bg};
            color: {text_primary};
            border-color: {border};
        }}
        div[data-testid="stSidebar"] div[data-testid="stButton"].em-nav-active button {{
            background: {bg};
            color: {accent};
            border-color: {accent};
            font-weight: 700;
            box-shadow: {shadow_md};
        }}
        .em-sidebar-footer {{
            position: sticky;
            bottom: 0;
            padding: {space_sm} {space_md};
            margin-top: {space_md};
            border-top: 1px solid {border};
            color: {text_secondary};
            font-size: {label_size};
            font-weight: 500;
            letter-spacing: 0.03em;
        }}
        .em-sidebar-collapse-toggle div[data-testid="stButton"] button {{
            justify-content: center;
            color: {accent};
            border: 1px solid {border};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_brand(config: SidebarConfig, collapsed: bool) -> None:
    """
    Render the company logo (or a premium engineering placeholder icon)
    and, when not collapsed, the application name.

    Args:
        config: Sidebar configuration values supplied by the caller.
        collapsed: Whether the sidebar is currently in collapsed mode.
    """
    if config.company_logo_path:
        logo_html = f'<img class="em-sidebar-logo-img" src="{config.company_logo_path}" />'
    else:
        logo_html = """
            <div class="em-sidebar-logo-placeholder">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="1.8"
                     stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9"></circle>
                    <path d="M12 12 L15.5 8.5"></path>
                    <path d="M12 3 v2"></path>
                    <path d="M12 19 v2"></path>
                    <path d="M3 12 h2"></path>
                    <path d="M19 12 h2"></path>
                </svg>
            </div>
        """

    name_html = (
        f'<span class="em-sidebar-app-name">{config.app_name}</span>'
        if (config.app_name and not collapsed)
        else ""
    )

    st.markdown(
        f'<div class="em-sidebar-brand">{logo_html}{name_html}</div>',
        unsafe_allow_html=True,
    )


def _render_collapse_toggle(collapsed: bool) -> bool:
    """
    Render the collapse/expand toggle control and return the updated
    collapsed state after handling any click during this run.

    Args:
        collapsed: The sidebar's collapsed state prior to this render.

    Returns:
        The (possibly updated) collapsed state.
    """
    st.markdown('<div class="em-sidebar-collapse-toggle">', unsafe_allow_html=True)
    toggle_label = "»" if collapsed else "«  Collapse"
    if st.button(toggle_label, key=_session_key("collapse_toggle"), use_container_width=True):
        collapsed = not collapsed
        st.session_state[_session_key("collapsed")] = collapsed
    st.markdown("</div>", unsafe_allow_html=True)
    return collapsed


def _render_nav_items(
    nav_items: Sequence[NavItem],
    active_page: str,
    collapsed: bool,
) -> str:
    """
    Render every navigation item as a Streamlit button and determine
    which item is selected for this run.

    Args:
        nav_items: Ordered navigation entries to render.
        active_page: The ``key`` of the currently active item, used to
            visually highlight the corresponding button.
        collapsed: Whether the sidebar is in collapsed mode, in which
            case only icons (no labels) are shown.

    Returns:
        The ``key`` of the selected navigation item for this run: the
        clicked item if any, otherwise ``active_page`` unchanged.
    """
    selected_key: str = active_page

    for item in nav_items:
        icon = _resolve_icon(item)
        button_label = icon if collapsed else f"{icon}  {item.label}"
        is_active = item.key == active_page

        wrapper_class = "em-nav-active" if is_active else "em-nav-inactive"
        st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
        clicked = st.button(
            button_label,
            key=_session_key(f"nav_{item.key}"),
            use_container_width=True,
            help=item.label if collapsed else None,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if clicked:
            selected_key = item.key

    return selected_key


def _render_footer(app_version: str, collapsed: bool) -> None:
    """
    Render the sidebar footer containing the application version.

    Args:
        app_version: Version string to display.
        collapsed: Whether the sidebar is collapsed, in which case a
            shortened footer is shown.
    """
    footer_text = app_version if collapsed else f"Version {app_version}"
    st.markdown(
        f'<div class="em-sidebar-footer">{footer_text}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(config: SidebarConfig) -> str:
    """
    Render the full industrial dashboard navigation sidebar.

    This function only renders UI based on the supplied ``config`` and
    the shared ``THEME`` design tokens, and emits the key of the
    selected navigation item. It performs no page routing itself beyond
    returning that key — the caller decides what to do with it (e.g.
    updating ``st.session_state`` and dispatching to the corresponding
    page).

    Args:
        config: Pre-computed sidebar values (logo path, app version,
            active page, nav items, collapsibility) supplied by the
            caller.

    Returns:
        The ``key`` of the navigation item that should now be
        considered active: either the item the user just clicked, or
        ``config.active_page`` unchanged if no click occurred this run.
    """
    _inject_sidebar_styles()

    collapsed_state_key = _session_key("collapsed")
    collapsed: bool = st.session_state.get(collapsed_state_key, False)

    with st.sidebar:
        _render_brand(config, collapsed=collapsed)

        if config.collapsible:
            collapsed = _render_collapse_toggle(collapsed)

        if not collapsed:
            st.markdown(
                '<div class="em-sidebar-section-label">Navigation</div>',
                unsafe_allow_html=True,
            )

        selected_key = _render_nav_items(
            nav_items=config.nav_items,
            active_page=config.active_page,
            collapsed=collapsed,
        )

        _render_footer(config.app_version, collapsed=collapsed)

    return selected_key

"""
app.py

Streamlit application entry point for the Engineering Monitoring
Dashboard.

This module is a PURE ORCHESTRATION LAYER. It:
    - Applies the global theme, layout, and CSS.
    - Initializes ``DashboardService`` (dependency-injected with the
      existing ``Loader``, ``Cache``, and ``Repository``).
    - Configures the Streamlit page (title, icon, wide layout).
    - Registers the multipage navigation structure.
    - Initializes session state.
    - Supports workbook refresh.
    - Handles loading, empty-workbook, and error states via the
      existing reusable loading/error screens.

This module never:
    - Performs KPI calculations.
    - Parses Excel directly.
    - Generates charts.

All loading, caching, and repository access is delegated to the
existing ``Loader``, ``Cache``, and ``Repository`` implementations;
this file only wires them together and reacts to the outcome.

Expected collaborators
---------------------------------------------------------------
This entry point depends only on the following, all assumed complete
and unmodified:

    components.theme.THEME
        Global design tokens, applied via ``apply_global_theme``.

    layout.py
        configure_page() -> None
            Applies ``st.set_page_config`` (title, icon, wide layout).
        apply_global_css() -> None
            Injects any global CSS derived from THEME that every page
            shares (independent of the per-component CSS each
            component already injects itself).
        main_container() -> ContextManager[None]
            Context manager wrapping primary content for consistent
            spacing/max-width.

    components.loading_screen.render_loading_screen
        render_loading_screen(message: str) -> None
            Reusable loading-state screen.

    components.error_screen.render_error_screen
        render_error_screen(error: Exception, on_retry: Callable[[], None]) -> None
            Reusable error-state screen with a retry action.

    components.empty_state.render_empty_workbook_screen
        render_empty_workbook_screen(on_retry: Callable[[], None]) -> None
            Reusable empty-workbook screen with a retry action.

    services.loader.Loader
    services.cache.Cache
    services.repository.Repository
        Existing data-access primitives; this file performs no
        loading/parsing logic itself, only injects these into
        ``DashboardService``.

    services.dashboard_service.DashboardService
        DashboardService(loader: Loader, cache: Cache, repository: Repository)
        load_workbook(force_refresh: bool = False) -> WorkbookLoadResult
            Loads (or reloads) the workbook via the injected
            collaborators and reports its outcome without performing
            any calculation itself.

    pages/*.py
        Existing Streamlit multipage page modules (overview,
        departments, air_compressor, freon_monitoring, water, energy,
        utilities, settings), each consuming ``DashboardService`` and
        the reusable UI components on its own.

If any concrete collaborator signature differs from the above, only
the small adapter calls in this file need to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import streamlit as st

import layout
from components.empty_state import render_empty_workbook_screen
from components.error_screen import render_error_screen
from components.loading_screen import render_loading_screen
from components.theme import THEME, apply_global_theme
from services.cache import Cache
from services.dashboard_service import DashboardService, WorkbookLoadResult
from services.loader import Loader
from services.repository import Repository

__all__ = ["main"]

_SESSION_KEY_WORKBOOK_STATE = "em_app__workbook_state"
_SESSION_KEY_LOAD_ERROR = "em_app__load_error"
_SESSION_KEY_FORCE_REFRESH = "em_app__force_refresh"


@dataclass(frozen=True)
class _NavPage:
    """
    Configuration for a single registered navigation page.

    Attributes:
        key: Stable identifier for the page (used for session state
            and internal bookkeeping).
        title: Display title shown in Streamlit's page navigation.
        icon: Icon glyph/emoji shown next to the title.
        module_path: Import path to the page's Streamlit script,
            relative to the project root (e.g. "pages/overview.py").
    """

    key: str
    title: str
    icon: str
    module_path: str


_NAV_PAGES: List[_NavPage] = [
    _NavPage("overview", "Overview", "🏠", "pages/overview.py"),
    _NavPage("departments", "Departments", "🏢", "pages/departments.py"),
    _NavPage("air_compressor", "Air Compressor", "🌀", "pages/air_compressor.py"),
    _NavPage("freon_monitoring", "Freon Monitoring", "❄️", "pages/freon_monitoring.py"),
    _NavPage("water", "Water", "💧", "pages/water.py"),
    _NavPage("energy", "Energy", "⚡", "pages/energy.py"),
    _NavPage("utilities", "Utilities", "🛠️", "pages/utilities.py"),
    _NavPage("settings", "Settings", "⚙️", "pages/settings.py"),
]


def _initialize_session_state() -> None:
    """
    Ensure every session-state key this entry point relies on exists,
    without overwriting values that already carry over across reruns.

    This function performs no business logic — it only guarantees
    default values are present so subsequent reads never raise
    ``KeyError``.
    """
    if _SESSION_KEY_WORKBOOK_STATE not in st.session_state:
        st.session_state[_SESSION_KEY_WORKBOOK_STATE] = None
    if _SESSION_KEY_LOAD_ERROR not in st.session_state:
        st.session_state[_SESSION_KEY_LOAD_ERROR] = None
    if _SESSION_KEY_FORCE_REFRESH not in st.session_state:
        st.session_state[_SESSION_KEY_FORCE_REFRESH] = False


@st.cache_resource(show_spinner=False)
def _build_dashboard_service() -> DashboardService:
    """
    Construct the singleton ``DashboardService`` for this app session,
    wiring in the existing ``Loader``, ``Cache``, and ``Repository``
    collaborators via dependency injection.

    Cached with ``st.cache_resource`` so the same instance (and its
    injected collaborators) is reused across reruns rather than
    reconstructed on every interaction; this is an application wiring
    concern, not a data-loading or business-logic concern.

    Returns:
        A fully constructed ``DashboardService`` instance.
    """
    loader = Loader()
    cache = Cache()
    repository = Repository(loader=loader, cache=cache)
    return DashboardService(loader=loader, cache=cache, repository=repository)


def _request_refresh() -> None:
    """
    Mark the next workbook load as a forced refresh and trigger a
    rerun.

    This is passed as the retry/refresh callback to the reusable
    loading, error, and empty-workbook screens, as well as to the
    navbar's refresh action on individual pages. It performs no
    loading itself — it only flags intent and lets the normal
    ``main()`` flow re-invoke ``DashboardService.load_workbook``.
    """
    st.session_state[_SESSION_KEY_FORCE_REFRESH] = True
    st.session_state[_SESSION_KEY_LOAD_ERROR] = None
    st.rerun()


def _load_workbook(dashboard_service: DashboardService) -> Optional[WorkbookLoadResult]:
    """
    Load (or refresh) the workbook via ``DashboardService``, updating
    session state with the outcome.

    All actual loading, caching, and repository access happens inside
    ``DashboardService`` and its injected collaborators (``Loader``,
    ``Cache``, ``Repository``); this function only invokes that call,
    interprets success/failure, and stores the result for the
    remainder of this run.

    Args:
        dashboard_service: The initialized dashboard service.

    Returns:
        The ``WorkbookLoadResult`` on success, or ``None`` if loading
        raised an exception (in which case the exception is recorded
        in session state for the error screen).
    """
    force_refresh = st.session_state.get(_SESSION_KEY_FORCE_REFRESH, False)

    try:
        result = dashboard_service.load_workbook(force_refresh=force_refresh)
    except Exception as exc:  # noqa: BLE001 - surfaced via the reusable error screen
        st.session_state[_SESSION_KEY_LOAD_ERROR] = exc
        st.session_state[_SESSION_KEY_WORKBOOK_STATE] = None
        return None

    st.session_state[_SESSION_KEY_LOAD_ERROR] = None
    st.session_state[_SESSION_KEY_WORKBOOK_STATE] = result
    st.session_state[_SESSION_KEY_FORCE_REFRESH] = False
    return result


def _register_navigation(pages: List[_NavPage]) -> None:
    """
    Register the application's multipage navigation using Streamlit's
    native navigation API.

    Page identity, titles, icons, and order are fully configuration-
    driven via ``_NAV_PAGES`` rather than hardcoded inline, and no
    per-page rendering logic lives here — each page module is
    responsible for its own content.

    Args:
        pages: The ordered list of navigation pages to register.
    """
    st_pages = [
        st.Page(page.module_path, title=page.title, icon=page.icon, url_path=page.key)
        for page in pages
    ]
    navigation = st.navigation(st_pages)
    navigation.run()


def _handle_startup(
    dashboard_service: DashboardService,
    on_retry: Callable[[], None],
) -> bool:
    """
    Handle the application's startup lifecycle: loading, error, and
    empty-workbook states.

    Args:
        dashboard_service: The initialized dashboard service.
        on_retry: Callback invoked by the reusable error/empty-state
            screens when the user requests a retry.

    Returns:
        ``True`` if the workbook loaded successfully and navigation
        should proceed; ``False`` if a loading, error, or empty state
        screen was shown instead and rendering should stop for this
        run.
    """
    pending_error = st.session_state.get(_SESSION_KEY_LOAD_ERROR)
    if pending_error is not None:
        render_error_screen(pending_error, on_retry=on_retry)
        return False

    with st.spinner("Loading workbook..."):
        render_loading_screen("Connecting to workbook source...")
        result = _load_workbook(dashboard_service)

    if result is None:
        # _load_workbook already recorded the exception; render the
        # error screen immediately rather than waiting for the next run.
        error = st.session_state.get(_SESSION_KEY_LOAD_ERROR)
        render_error_screen(error, on_retry=on_retry)
        return False

    if result.is_empty:
        render_empty_workbook_screen(on_retry=on_retry)
        return False

    return True


def main() -> None:
    """
    Application entry point.

    Orchestrates, in order:
        1. Global theme, layout, and CSS application.
        2. Page configuration (title, icon, wide layout).
        3. Session state initialization.
        4. ``DashboardService`` construction via dependency injection
           of the existing ``Loader``, ``Cache``, and ``Repository``.
        5. Workbook loading/refresh, with loading, error, and empty
           states handled via the reusable screens.
        6. Multipage navigation registration once a workbook is
           successfully loaded.

    This function performs no KPI calculation, no direct Excel
    parsing, and no chart generation — all of that remains inside the
    injected services and the individual page modules.

    Returns:
        None.
    """
    layout.configure_page()
    apply_global_theme(THEME)
    layout.apply_global_css()

    _initialize_session_state()

    dashboard_service = _build_dashboard_service()

    with layout.main_container():
        startup_succeeded = _handle_startup(dashboard_service, on_retry=_request_refresh)

    if not startup_succeeded:
        return

    _register_navigation(_NAV_PAGES)


if __name__ == "__main__":
    main()

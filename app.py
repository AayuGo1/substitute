"""
app.py

Streamlit application entry point for the Engineering Monitoring
Dashboard.

This module is a PURE ORCHESTRATION LAYER. It:
    - Applies the global theme, layout, and CSS.
    - Initializes the real ``DashboardService`` (dependency-injected
      with ``WorkbookService``, ``SectionService``, ``FilterService``,
      ``KPIService``, ``SummaryService``, and ``ChartService``).
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

Data access is delegated entirely to ``WorkbookService`` /
``WorkbookRepository`` / the GitHub loader; this file only wires them
together and reacts to the outcome.

Collaborators actually used (matching the real, shipped contracts)
---------------------------------------------------------------
    components.theme.THEME / get_global_css()
        The dashboard's design-system dataclass and the function that
        derives its global CSS block (there is no
        ``apply_global_theme`` helper in ``components.theme``).

    components.layout
        configure_page(title, icon) -> None
        inject_global_styles(css) -> None
        page_container() -> ContextManager[None]
        (There is no project-root ``layout`` module distinct from
        ``components.layout`` in the shipped codebase; these are the
        only layout helpers that actually exist.)

    components.loading_screen.render_loading_screen
    components.error_screen.render_error_screen
    components.empty_state.render_empty_workbook_screen
        Reusable loading/error/empty-state screens (unchanged).

    data.github_loader.load_workbook_from_github
        The only concrete workbook-loading primitive that exists.
        Returns a raw ``openpyxl.Workbook`` given a ``GitHubConfig``.
        It does not satisfy ``LoaderLike`` on its own (no
        ``.load(source_path)``, no ``.raw_workbook``/``.success``/
        ``.error``/``.metadata`` attributes), so it is wrapped here by
        a minimal structural adapter — not a new service class, just
        the "small adapter calls" this file was always meant to own.

    data.repository.WorkbookRepository(loader, validator, parser_service)
        The real repository contract. ``validator`` must satisfy
        ``ValidatorLike``; since no validator implementation exists
        yet in the project, a trivial pass-through adapter (structural,
        not a new class) is used here, reporting every load as valid
        with no re-discovered structure. This should be replaced with
        the real validator as soon as ``data/validator.py`` exists —
        flagged, not silently invented.

    services.parser_service.ParserService
        The real, unmodified parser used to build ``WorkbookRepository``.

    services.workbook_service.WorkbookService(repository)
        The real façade ``DashboardService`` depends on.

    services.section_service.SectionService
    services.filter_service.FilterService
    services.kpi_service.KPIService
    services.summary_service.SummaryService
    services.chart_service.ChartService
        Constructed exactly as ``pages/overview.py`` already imports
        them (``from services.<name> import <Name>``), since that is
        the only existing reference to their concrete location.

    services.dashboard_service.DashboardService
        The real, 6-collaborator-injected service. Its entry point is
        ``get_overview_page_data(source_path, ...)``, not
        ``load_workbook(force_refresh=...)``.

    config.github.get_github_config
        Supplies the ``GitHubConfig`` used both as the loader's source
        and as the nominal ``source_path`` identity for this workbook.

If any concrete collaborator signature differs from the above, only
the small adapter calls in this file need to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable, List, Optional

import streamlit as st

from components.layout import configure_page, inject_global_styles, page_container

from components.error_screen import render_error_screen
from components.loading_screen import render_loading_screen
from components.theme import THEME, get_global_css

from config.github import get_github_config

from data.github_loader import load_workbook_from_github
from data.repository import WorkbookRepository

from services.chart_service import ChartService
from services.dashboard_service import DashboardService, OverviewPageData
from services.filter_service import FilterService
from services.kpi_service import KPIService
from services.parser_service import ParserService
from services.section_service import SectionService
from services.summary_service import SummaryService
from services.workbook_service import WorkbookService

__all__ = ["main"]

_SESSION_KEY_PAGE_DATA = "em_app__overview_page_data"
_SESSION_KEY_LOAD_ERROR = "em_app__load_error"
_SESSION_KEY_FORCE_REFRESH = "em_app__force_refresh"

_DASHBOARD_TITLE = "Engineering Monitoring Dashboard"
_DASHBOARD_ICON = "\U0001F3ED"

# Nominal, stable identifier for the single GitHub-backed workbook this
# app serves. The real loader (data.github_loader) resolves the actual
# source location from config.github.get_github_config(), so this value
# is only used as WorkbookService/WorkbookRepository's "source_path"
# bookkeeping key and cache identity — never as a file path.
_WORKBOOK_SOURCE_PATH = "github-workbook"


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
    if _SESSION_KEY_PAGE_DATA not in st.session_state:
        st.session_state[_SESSION_KEY_PAGE_DATA] = None
    if _SESSION_KEY_LOAD_ERROR not in st.session_state:
        st.session_state[_SESSION_KEY_LOAD_ERROR] = None
    if _SESSION_KEY_FORCE_REFRESH not in st.session_state:
        st.session_state[_SESSION_KEY_FORCE_REFRESH] = False


def _github_loader_adapter() -> object:
    """
    Build a ``LoaderLike``-satisfying object around the real
    ``load_workbook_from_github`` function.

    ``data.github_loader`` exposes a bare function returning an
    ``openpyxl.Workbook``, not an object with ``.raw_workbook``,
    ``.source_path``, ``.metadata``, ``.success``, ``.error`` as
    ``WorkbookRepository`` requires. This wraps it structurally,
    without introducing any new business-logic class — the download,
    caching, and TTL behavior all remain entirely inside
    ``data.github_loader``, unmodified.

    Returns:
        An object exposing ``.load(source_path) -> SimpleNamespace``
        satisfying ``data.repository.SupportsRawWorkbook``.
    """

    def _load(source_path: str) -> SimpleNamespace:
        try:
            raw_workbook = load_workbook_from_github(get_github_config())
        except Exception as exc:  # noqa: BLE001 - normalized by WorkbookRepository
            return SimpleNamespace(
                raw_workbook=None,
                source_path=source_path,
                metadata=None,
                success=False,
                error=str(exc),
            )
        return SimpleNamespace(
            raw_workbook=raw_workbook,
            source_path=source_path,
            metadata=None,
            success=True,
            error=None,
        )

    return SimpleNamespace(load=_load)


def _passthrough_validator_adapter() -> object:
    """
    Build a ``ValidatorLike``-satisfying object that reports every
    loaded workbook as valid, with no pre-discovered structure.

    No validator implementation exists yet anywhere in the project
    (``data/validator.py`` is referenced by ``WorkbookRepository`` but
    was never supplied). Rather than inventing real validation logic —
    which would be a new architectural component — this adapter is a
    deliberately inert stand-in: it lets ``ParserService`` perform its
    own structure discovery (since ``structure`` is ``None``) and
    raises no validation errors of its own. It should be replaced with
    the real validator as soon as one exists.

    Returns:
        An object exposing ``.validate(raw_workbook) -> SimpleNamespace``
        satisfying ``data.repository.SupportsValidationResult``.
    """

    def _validate(raw_workbook: object) -> SimpleNamespace:
        return SimpleNamespace(is_valid=True, structure=None, errors=[], warnings=[])

    return SimpleNamespace(validate=_validate)


@st.cache_resource(show_spinner=False)
def _build_dashboard_service() -> DashboardService:
    """
    Construct the singleton ``DashboardService`` for this app session,
    wiring in the real ``WorkbookService`` (backed by
    ``WorkbookRepository``) plus ``SectionService``, ``FilterService``,
    ``KPIService``, ``SummaryService``, and ``ChartService``.

    Cached with ``st.cache_resource`` so the same instance (and its
    injected collaborators) is reused across reruns rather than
    reconstructed on every interaction; this is an application wiring
    concern, not a data-loading or business-logic concern.

    Returns:
        A fully constructed ``DashboardService`` instance.
    """
    repository = WorkbookRepository(
        loader=_github_loader_adapter(),
        validator=_passthrough_validator_adapter(),
        parser_service=ParserService(),
    )
    workbook_service = WorkbookService(repository=repository)

    return DashboardService(
        workbook_service=workbook_service,
        section_service=SectionService(),
        filter_service=FilterService(),
        kpi_service=KPIService(),
        summary_service=SummaryService(),
        chart_service=ChartService(),
    )


def _request_refresh() -> None:
    """
    Mark the next workbook load as a forced refresh and trigger a
    rerun.

    This is passed as the retry/refresh callback to the reusable
    loading, error, and empty-workbook screens. It performs no loading
    itself — it only flags intent and lets the normal ``main()`` flow
    re-invoke ``DashboardService.get_overview_page_data``.
    """
    st.session_state[_SESSION_KEY_FORCE_REFRESH] = True
    st.session_state[_SESSION_KEY_LOAD_ERROR] = None
    st.session_state[_SESSION_KEY_PAGE_DATA] = None
    st.rerun()


def _load_overview_page_data(
    dashboard_service: DashboardService,
) -> Optional[OverviewPageData]:
    """
    Load the Overview page's full data set via ``DashboardService``,
    updating session state with the outcome.

    All actual loading, validation, parsing, and aggregation happens
    inside ``DashboardService`` and its injected collaborators; this
    function only invokes ``get_overview_page_data``, interprets
    success/failure, and stores the result for the remainder of this
    run.

    Args:
        dashboard_service: The initialized dashboard service.

    Returns:
        The ``OverviewPageData`` on success, or ``None`` if loading
        raised an exception (in which case the exception is recorded
        in session state for the error screen).
    """
    try:
        result = dashboard_service.get_overview_page_data(
            source_path=_WORKBOOK_SOURCE_PATH
        )
    except Exception as exc:  # noqa: BLE001 - surfaced via the reusable error screen
        st.session_state[_SESSION_KEY_LOAD_ERROR] = exc
        st.session_state[_SESSION_KEY_PAGE_DATA] = None
        return None

    st.session_state[_SESSION_KEY_LOAD_ERROR] = None
    st.session_state[_SESSION_KEY_PAGE_DATA] = result
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
        result = _load_overview_page_data(dashboard_service)

    if result is None:
        # _load_overview_page_data already recorded the exception;
        # render the error screen immediately rather than waiting for
        # the next run.
        error = st.session_state.get(_SESSION_KEY_LOAD_ERROR)
        render_error_screen(error, on_retry=on_retry)
        return False
if not result.expandable_sections:
    st.warning(
        "No engineering sections were found in the workbook. "
        "Please verify the workbook contains valid data."
    )

    if st.button("Retry Loading"):
        on_retry()

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
           of the real ``WorkbookService``, ``SectionService``,
           ``FilterService``, ``KPIService``, ``SummaryService``, and
           ``ChartService``.
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
    configure_page(_DASHBOARD_TITLE, _DASHBOARD_ICON)
    inject_global_styles(get_global_css())

    _initialize_session_state()

    dashboard_service = _build_dashboard_service()

    with page_container():
        startup_succeeded = _handle_startup(dashboard_service, on_retry=_request_refresh)

    if not startup_succeeded:
        return

    _register_navigation(_NAV_PAGES)


if __name__ == "__main__":
    main()

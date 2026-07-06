"""
app.py

Streamlit application entry point for the Engineering Monitoring
Dashboard.

Pure orchestration layer: configures the page, applies the global
theme, wires dependency injection for the Loader -> Validator ->
Parser -> WorkbookRepository -> WorkbookService -> DashboardService
chain, and registers Streamlit's multipage navigation. No business
logic, KPI calculation, Excel parsing, validation logic, chart
generation, or CSS/HTML lives here.

Structural adapter note
------------------------
No uploaded module provides a concrete implementation of
``data.repository.LoaderLike`` or ``data.repository.ValidatorLike``:

* ``data.github_loader.load_workbook_from_github()`` is a bare function
  returning a ``BytesIO`` stream, not an object with a ``.load(source_path)``
  method.
* ``data.validator.WorkbookValidator.validate()`` expects a filesystem
  path and returns a ``WorkbookValidationReport``, not the
  ``is_valid``/``structure``/``errors``/``warnings`` shape
  ``WorkbookRepository`` requires, and this workbook is never written
  to disk.

Two minimal, structural (``SimpleNamespace``) adapters are therefore
required to satisfy ``WorkbookRepository``'s declared Protocols. These
are not new services or classes; they only convert the existing public
functions into the shapes the repository's own contracts demand.
"""
from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import List

import streamlit as st
from openpyxl import load_workbook as load_openpyxl_workbook

from components.layout import configure_page, inject_global_styles, page_container
from components.theme import get_global_css

from data.github_loader import load_workbook_from_github
from data.repository import WorkbookRepository

from services.chart_service import ChartService
from services.dashboard_service import DashboardService
from services.filter_service import FilterService
from services.kpi_service import KPIService
from services.parser_service import ParserService
from services.section_service import SectionService
from services.summary_service import SummaryService
from services.workbook_service import WorkbookService

__all__ = ["main"]

_DASHBOARD_TITLE = "Engineering Monitoring Dashboard"
_DASHBOARD_ICON = "\U0001F3ED"

# Nominal, stable identifier for the single GitHub-backed workbook this
# app serves. data.github_loader resolves the actual source location
# internally via config.github.get_github_config(); this value is only
# used as WorkbookRepository/WorkbookService's source-path bookkeeping
# key, never as a real file path.
_WORKBOOK_SOURCE_PATH = "github-workbook"

_NAV_PAGES = [
    st.Page("pages/overview.py", title="Overview", icon="🏠", url_path="overview"),
]


def _github_loader_adapter() -> object:
    """Wrap ``load_workbook_from_github`` to satisfy ``LoaderLike``.

    ``load_workbook_from_github`` takes no arguments and returns a raw
    ``BytesIO`` stream. This adapter supplies the ``.load(source_path)``
    method signature ``WorkbookRepository`` requires, converts the
    downloaded bytes into an ``openpyxl.Workbook`` (required by
    ``ParserService``), and reports the result via the
    ``SupportsRawWorkbook`` attribute shape.
    """

    def _load(source_path: str) -> SimpleNamespace:
        stream: BytesIO = load_workbook_from_github()
        stream.seek(0)
        raw_workbook = load_openpyxl_workbook(filename=stream, data_only=True)
        return SimpleNamespace(
            raw_workbook=raw_workbook,
            source_path=source_path,
            metadata=None,
            success=True,
            error=None,
        )

    return SimpleNamespace(load=_load)


def _passthrough_validator_adapter() -> object:
    """Stand in for ``ValidatorLike`` until a real validator exists.

    ``data.validator.WorkbookValidator`` validates a file path, not an
    in-memory ``raw_workbook``, and returns a report shape
    (``sheet_reports``/``warnings``) that does not satisfy
    ``SupportsValidationResult``. This adapter reports every load as
    valid with no pre-discovered structure, so ``ParserService``
    performs its own structure discovery. Replace with a real
    ``ValidatorLike`` implementation once one accepts an in-memory
    workbook.
    """

    def _validate(raw_workbook: object) -> SimpleNamespace:
        return SimpleNamespace(is_valid=True, structure=None, errors=[], warnings=[])

    return SimpleNamespace(validate=_validate)


@st.cache_resource(show_spinner=False)
def _build_dashboard_service() -> DashboardService:
    """Construct the singleton `DashboardService`, wiring the full DI chain.

    Loader -> Validator -> Parser -> WorkbookRepository ->
    WorkbookService -> SectionService -> FilterService -> KPIService ->
    (SummaryService, ChartService) -> DashboardService.

    Cached with ``st.cache_resource`` so the same instance is reused
    across Streamlit reruns.
    """
    repository = WorkbookRepository(
        loader=_github_loader_adapter(),
        validator=_passthrough_validator_adapter(),
        parser_service=ParserService(),
    )

    workbook_service = WorkbookService(repository=repository)
    section_service = SectionService(workbook_service=workbook_service)
    filter_service = FilterService()
    kpi_service = KPIService(section_service=section_service)
    summary_service = SummaryService(
        workbook_service=workbook_service,
        section_service=section_service,
        filter_service=filter_service,
        kpi_service=kpi_service,
    )
    chart_service = ChartService(
        section_service=section_service,
        filter_service=filter_service,
    )

    return DashboardService(
        workbook_service=workbook_service,
        section_service=section_service,
        filter_service=filter_service,
        kpi_service=kpi_service,
        summary_service=summary_service,
        chart_service=chart_service,
    )


def _register_navigation(pages: List[st.Page]) -> None:
    """Register the application's multipage navigation."""
    st.navigation(pages).run()


def main() -> None:
    """Application entry point: configure, wire, and launch."""
    configure_page(_DASHBOARD_TITLE, _DASHBOARD_ICON)
    inject_global_styles(get_global_css())

    if "dashboard_service" not in st.session_state:
        st.session_state["dashboard_service"] = _build_dashboard_service()
    if "workbook_source_path" not in st.session_state:
        st.session_state["workbook_source_path"] = _WORKBOOK_SOURCE_PATH

    with page_container():
        _register_navigation(_NAV_PAGES)


if __name__ == "__main__":
    main()

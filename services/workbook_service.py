"""Primary business logic entry point for the engineering monitoring dashboard.

This module exposes :class:`WorkbookService`, a thin façade over
:class:`~data.repository.WorkbookRepository` that gives the rest of the
application (dashboard pages, in particular) a single, focused place to
obtain a parsed workbook and answer simple questions about it.

This service deliberately contains:

* No KPI calculations.
* No chart generation.
* No Streamlit or any other UI code.
* No duplication of the repository's load/validate/parse orchestration
  logic — it calls the repository once per workbook and derives every
  helper from the resulting :class:`~models.workbook.Workbook`.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from models.section import DateRange, Section
from models.workbook import Workbook, WorkbookMetadata, ValidationStatus


@runtime_checkable
class WorkbookRepositoryLike(Protocol):
    """Structural interface required of an injected repository.

    :class:`WorkbookService` depends on this narrow interface rather than
    the concrete ``WorkbookRepository`` class, keeping it decoupled from
    the repository's implementation (Dependency Inversion Principle) and
    straightforward to test with fakes.
    """

    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook:
        """Loads, validates, and parses a workbook into a typed model.

        Args:
            source_path: Path or identifier of the workbook to load.
            workbook_name: Optional human-friendly name for the
                workbook.
            strict: Whether a validation failure should raise instead of
                producing a flagged workbook.

        Returns:
            A fully populated :class:`~models.workbook.Workbook`.
        """
        ...


class WorkbookService:
    """Business logic façade for obtaining and inspecting workbooks.

    :class:`WorkbookService` is the entry point dashboard pages should
    use to get a parsed :class:`~models.workbook.Workbook` and to answer
    simple, structural questions about it (its metadata, sheets,
    sections, units, date range, and validation status). It does not
    perform any KPI math or chart construction; those belong to
    dedicated KPI and chart-building services that consume the
    :class:`~models.workbook.Workbook` this service returns.

    Attributes:
        repository: The injected repository used to load, validate, and
            parse workbooks.
    """

    def __init__(self, repository: WorkbookRepositoryLike) -> None:
        """Initializes the service with its repository dependency.

        Args:
            repository: An object satisfying
                :class:`WorkbookRepositoryLike`.
        """
        self.repository = repository

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook:
        """Retrieves the fully parsed Workbook model for a source path.

        This delegates entirely to the injected repository; no
        additional loading, validation, or parsing logic is performed
        here.

        Args:
            source_path: Path or identifier of the workbook to load.
            workbook_name: Optional human-friendly name for the
                workbook.
            strict: Whether a validation failure should raise instead of
                producing a validation-flagged workbook.

        Returns:
            A fully populated :class:`~models.workbook.Workbook`.

        Raises:
            data.repository.WorkbookRepositoryError: If the repository
                cannot produce a workbook (propagated unchanged).
        """
        return self.repository.get_workbook(
            source_path=source_path,
            workbook_name=workbook_name,
            strict=strict,
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, workbook: Workbook) -> Optional[WorkbookMetadata]:
        """Returns a workbook's descriptive file metadata.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The workbook's :class:`~models.workbook.WorkbookMetadata`,
            or ``None`` if none was recorded.
        """
        return workbook.metadata

    # ------------------------------------------------------------------
    # Sheets
    # ------------------------------------------------------------------

    def list_available_sheets(self, workbook: Workbook) -> List[str]:
        """Lists every sheet name discovered in the source workbook file.

        This includes sheets that could not be parsed into a
        :class:`~models.section.Section` (for example, sheets skipped
        for lacking a detectable header row); use
        :meth:`list_sections` to see only the sheets that yielded usable
        data.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The available sheet names, in workbook order.
        """
        return list(workbook.available_sheets)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def list_sections(self, workbook: Workbook) -> List[Section]:
        """Lists every section successfully discovered in the workbook.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The workbook's top-level :class:`~models.section.Section`
            instances, in discovery order.
        """
        return list(workbook.sections)

    def get_section(self, workbook: Workbook, name: str) -> Optional[Section]:
        """Finds a single section by its normalized ``name``.

        Args:
            workbook: The parsed workbook to inspect.
            name: The section's normalized (slugified) name to match.

        Returns:
            The matching :class:`~models.section.Section`, or ``None``
            if no section with that name was found.
        """
        for section in workbook.sections:
            if section.name == name:
                return section
        return None

    # ------------------------------------------------------------------
    # Units
    # ------------------------------------------------------------------

    def list_units(self, workbook: Workbook) -> List[str]:
        """Lists every distinct unit of measure used across the workbook.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The distinct units encountered anywhere in the workbook, in
            first-seen order.
        """
        return list(workbook.units)

    # ------------------------------------------------------------------
    # Date range
    # ------------------------------------------------------------------

    def get_date_range(self, workbook: Workbook) -> Optional[DateRange]:
        """Returns the overall date range covered by the workbook.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The workbook's overall :class:`~models.section.DateRange`,
            or ``None`` if no section carried timestamp data.
        """
        return workbook.date_range

    # ------------------------------------------------------------------
    # Validation status
    # ------------------------------------------------------------------

    def get_validation_status(self, workbook: Workbook) -> ValidationStatus:
        """Returns the workbook's overall validation status.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The workbook's :class:`~models.workbook.ValidationStatus`.
        """
        return workbook.validation_status

    def is_valid(self, workbook: Workbook) -> bool:
        """Whether the workbook is valid, with or without warnings.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            ``True`` if the workbook's status is ``VALID`` or
            ``VALID_WITH_WARNINGS``; ``False`` otherwise.
        """
        return workbook.validation_status in (
            ValidationStatus.VALID,
            ValidationStatus.VALID_WITH_WARNINGS,
        )

    def get_warnings(self, workbook: Workbook) -> List[str]:
        """Lists the non-fatal warnings raised while loading the workbook.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The accumulated warning messages, in the order they were
            raised.
        """
        return list(workbook.warnings)

    def get_errors(self, workbook: Workbook) -> List[str]:
        """Lists the fatal errors raised while loading the workbook.

        Args:
            workbook: The parsed workbook to inspect.

        Returns:
            The accumulated error messages, in the order they were
            raised.
        """
        return list(workbook.errors)

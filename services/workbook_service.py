"""
services/workbook_service.py — INSTRUMENTED FOR RUNTIME HANG DIAGNOSIS
(TEMPORARY LOGGING)

All original business logic and return values are unchanged. Only
ENTER/EXIT/BEFORE/AFTER debug logging has been added. Remove all lines
marked "# DEBUG" once the hang is diagnosed.
"""

from __future__ import annotations

import sys
import traceback
from typing import List, Optional, Protocol, runtime_checkable

from models.section import DateRange, Section
from models.workbook import Workbook, WorkbookMetadata, ValidationStatus


# ---------------------------------------------------------------------
# DEBUG: logging helper (temporary)
# ---------------------------------------------------------------------
def _dbg(msg: str) -> None:  # DEBUG
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)  # DEBUG


@runtime_checkable
class WorkbookRepositoryLike(Protocol):
    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook: ...


class WorkbookService:
    """Business logic façade for obtaining and inspecting workbooks."""

    def __init__(self, repository: WorkbookRepositoryLike) -> None:
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
        _dbg("ENTER services.workbook_service.WorkbookService.get_workbook")  # DEBUG
        try:
            _dbg("BEFORE repository.get_workbook()")  # DEBUG
            workbook = self.repository.get_workbook(
                source_path=source_path,
                workbook_name=workbook_name,
                strict=strict,
            )
            _dbg("AFTER repository.get_workbook()")  # DEBUG
            _dbg("EXIT services.workbook_service.WorkbookService.get_workbook (success)")  # DEBUG
            return workbook
        except Exception:
            _dbg("EXCEPTION in WorkbookService.get_workbook")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, workbook: Workbook) -> Optional[WorkbookMetadata]:
        _dbg("ENTER WorkbookService.get_metadata")  # DEBUG
        result = workbook.metadata
        _dbg("EXIT WorkbookService.get_metadata")  # DEBUG
        return result

    # ------------------------------------------------------------------
    # Sheets
    # ------------------------------------------------------------------

    def list_available_sheets(self, workbook: Workbook) -> List[str]:
        _dbg("ENTER WorkbookService.list_available_sheets")  # DEBUG
        result = list(workbook.available_sheets)
        _dbg("EXIT WorkbookService.list_available_sheets")  # DEBUG
        return result

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def list_sections(self, workbook: Workbook) -> List[Section]:
        _dbg("ENTER WorkbookService.list_sections")  # DEBUG
        result = list(workbook.sections)
        _dbg("EXIT WorkbookService.list_sections")  # DEBUG
        return result

    def get_section(self, workbook: Workbook, name: str) -> Optional[Section]:
        _dbg("ENTER WorkbookService.get_section")  # DEBUG
        for section in workbook.sections:
            if section.name == name:
                _dbg("EXIT WorkbookService.get_section (found)")  # DEBUG
                return section
        _dbg("EXIT WorkbookService.get_section (not found)")  # DEBUG
        return None

    # ------------------------------------------------------------------
    # Units
    # ------------------------------------------------------------------

    def list_units(self, workbook: Workbook) -> List[str]:
        _dbg("ENTER WorkbookService.list_units")  # DEBUG
        result = list(workbook.units)
        _dbg("EXIT WorkbookService.list_units")  # DEBUG
        return result

    # ------------------------------------------------------------------
    # Date range
    # ------------------------------------------------------------------

    def get_date_range(self, workbook: Workbook) -> Optional[DateRange]:
        _dbg("ENTER WorkbookService.get_date_range")  # DEBUG
        result = workbook.date_range
        _dbg("EXIT WorkbookService.get_date_range")  # DEBUG
        return result

    # ------------------------------------------------------------------
    # Validation status
    # ------------------------------------------------------------------

    def get_validation_status(self, workbook: Workbook) -> ValidationStatus:
        _dbg("ENTER WorkbookService.get_validation_status")  # DEBUG
        result = workbook.validation_status
        _dbg("EXIT WorkbookService.get_validation_status")  # DEBUG
        return result

    def is_valid(self, workbook: Workbook) -> bool:
        _dbg("ENTER WorkbookService.is_valid")  # DEBUG
        result = workbook.validation_status in (
            ValidationStatus.VALID,
            ValidationStatus.VALID_WITH_WARNINGS,
        )
        _dbg("EXIT WorkbookService.is_valid")  # DEBUG
        return result

    def get_warnings(self, workbook: Workbook) -> List[str]:
        _dbg("ENTER WorkbookService.get_warnings")  # DEBUG
        result = list(workbook.warnings)
        _dbg("EXIT WorkbookService.get_warnings")  # DEBUG
        return result

    def get_errors(self, workbook: Workbook) -> List[str]:
        _dbg("ENTER WorkbookService.get_errors")  # DEBUG
        result = list(workbook.errors)
        _dbg("EXIT WorkbookService.get_errors")  # DEBUG
        return result

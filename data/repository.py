"""
data/repository.py — INSTRUMENTED FOR RUNTIME HANG DIAGNOSIS
(TEMPORARY LOGGING)

All original business logic, models, and return values are unchanged.
Only ENTER/EXIT/BEFORE/AFTER debug logging has been added. Remove all
lines marked "# DEBUG" once the hang is diagnosed.
"""

from __future__ import annotations

import sys
import traceback
from typing import Optional, Protocol, runtime_checkable

from models.workbook import Workbook, WorkbookMetadata


# ---------------------------------------------------------------------
# DEBUG: logging helper (temporary)
# ---------------------------------------------------------------------
def _dbg(msg: str) -> None:  # DEBUG
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)  # DEBUG


@runtime_checkable
class SupportsRawWorkbook(Protocol):
    raw_workbook: object
    source_path: str
    metadata: Optional[WorkbookMetadata]
    success: bool
    error: Optional[str]


@runtime_checkable
class SupportsValidationResult(Protocol):
    is_valid: bool
    structure: Optional[object]
    errors: list
    warnings: list


@runtime_checkable
class LoaderLike(Protocol):
    def load(self, source_path: str) -> SupportsRawWorkbook: ...


@runtime_checkable
class ValidatorLike(Protocol):
    def validate(self, raw_workbook: object) -> SupportsValidationResult: ...


@runtime_checkable
class ParserServiceLike(Protocol):
    def parse(
        self,
        raw_workbook: object,
        workbook_name: Optional[str] = None,
        structure: Optional[object] = None,
        metadata: Optional[WorkbookMetadata] = None,
    ) -> Workbook: ...


class WorkbookRepositoryError(Exception):
    """Raised when the repository cannot produce a Workbook model."""


class WorkbookLoadError(WorkbookRepositoryError):
    """Raised when the Loader fails to load a workbook from its source."""


class WorkbookValidationError(WorkbookRepositoryError):
    """Raised when a loaded workbook fails validation."""


class WorkbookRepository:
    """Coordinates Loader, Validator, and ParserService for the app."""

    def __init__(
        self,
        loader: LoaderLike,
        validator: ValidatorLike,
        parser_service: ParserServiceLike,
    ) -> None:
        self.loader = loader
        self.validator = validator
        self.parser_service = parser_service

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def get_workbook(
        self,
        source_path: str,
        workbook_name: Optional[str] = None,
        strict: bool = False,
    ) -> Workbook:
        _dbg("ENTER data.repository.WorkbookRepository.get_workbook")  # DEBUG
        try:
            _dbg("BEFORE self._load()")  # DEBUG
            load_result = self._load(source_path)
            _dbg("AFTER self._load()")  # DEBUG

            _dbg("BEFORE self._validate()")  # DEBUG
            validation_result = self._validate(load_result.raw_workbook)
            _dbg("AFTER self._validate()")  # DEBUG
            _dbg(f"Validator result: is_valid={validation_result.is_valid}, "
                 f"errors={getattr(validation_result, 'errors', None)}, "
                 f"warnings={getattr(validation_result, 'warnings', None)}")  # DEBUG

            if strict and not validation_result.is_valid:
                _dbg("Strict mode and workbook invalid -> raising WorkbookValidationError")  # DEBUG
                raise WorkbookValidationError(
                    self._format_validation_errors(source_path, validation_result)
                )

            resolved_name = workbook_name or getattr(
                load_result, "source_path", source_path
            )
            resolved_metadata = getattr(load_result, "metadata", None)
            reusable_structure = getattr(validation_result, "structure", None)

            _dbg("BEFORE self._parse()")  # DEBUG
            workbook = self._parse(
                raw_workbook=load_result.raw_workbook,
                workbook_name=resolved_name,
                structure=reusable_structure,
                metadata=resolved_metadata,
            )
            _dbg("AFTER self._parse()")  # DEBUG
            _dbg(f"Parser result: sections_count={len(workbook.sections)}, "
                 f"validation_status={workbook.validation_status}, "
                 f"warnings={workbook.warnings}, errors={workbook.errors}")  # DEBUG

            self._merge_validation_feedback(workbook, validation_result)
            _dbg("EXIT data.repository.WorkbookRepository.get_workbook (success)")  # DEBUG
            return workbook
        except Exception:
            _dbg("EXCEPTION in WorkbookRepository.get_workbook")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------

    def _load(self, source_path: str) -> SupportsRawWorkbook:
        _dbg("ENTER WorkbookRepository._load")  # DEBUG
        try:
            _dbg("BEFORE loader.load()")  # DEBUG
            load_result = self.loader.load(source_path)
            _dbg("AFTER loader.load()")  # DEBUG
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
            _dbg("EXCEPTION raised by loader.load()")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise WorkbookLoadError(
                f"Failed to load workbook from '{source_path}': {exc}"
            ) from exc

        success = getattr(load_result, "success", True)
        _dbg(f"Loader success flag: {success}")  # DEBUG
        if not success:
            error_message = getattr(load_result, "error", "unknown error")
            _dbg(f"Loader reported failure: {error_message}")  # DEBUG
            raise WorkbookLoadError(
                f"Failed to load workbook from '{source_path}': {error_message}"
            )

        raw_workbook = getattr(load_result, "raw_workbook", None)
        if raw_workbook is None:
            _dbg("Loader returned no raw_workbook")  # DEBUG
            raise WorkbookLoadError(
                f"Loader returned no workbook for '{source_path}'."
            )

        _dbg("EXIT WorkbookRepository._load (success)")  # DEBUG
        return load_result

    def _validate(self, raw_workbook: object) -> SupportsValidationResult:
        _dbg("ENTER WorkbookRepository._validate")  # DEBUG
        try:
            _dbg("BEFORE validator.validate()")  # DEBUG
            result = self.validator.validate(raw_workbook)
            _dbg("AFTER validator.validate()")  # DEBUG
            _dbg("EXIT WorkbookRepository._validate (success)")  # DEBUG
            return result
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
            _dbg("EXCEPTION raised by validator.validate()")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise WorkbookRepositoryError(
                f"Failed to validate workbook: {exc}"
            ) from exc

    def _parse(
        self,
        raw_workbook: object,
        workbook_name: Optional[str],
        structure: Optional[object],
        metadata: Optional[WorkbookMetadata],
    ) -> Workbook:
        _dbg("ENTER WorkbookRepository._parse")  # DEBUG
        try:
            _dbg("BEFORE parser_service.parse()")  # DEBUG
            result = self.parser_service.parse(
                raw_workbook,
                workbook_name=workbook_name,
                structure=structure,
                metadata=metadata,
            )
            _dbg("AFTER parser_service.parse()")  # DEBUG
            _dbg("EXIT WorkbookRepository._parse (success)")  # DEBUG
            return result
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
            _dbg("EXCEPTION raised by parser_service.parse()")  # DEBUG
            _dbg(traceback.format_exc())  # DEBUG
            raise WorkbookRepositoryError(
                f"Failed to parse workbook '{workbook_name}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Result merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_validation_feedback(
        workbook: Workbook, validation_result: SupportsValidationResult
    ) -> None:
        _dbg("ENTER WorkbookRepository._merge_validation_feedback")  # DEBUG
        validation_errors = list(getattr(validation_result, "errors", []) or [])
        validation_warnings = list(getattr(validation_result, "warnings", []) or [])

        for error in validation_errors:
            if error not in workbook.errors:
                workbook.errors.append(error)

        for warning in validation_warnings:
            if warning not in workbook.warnings:
                workbook.warnings.append(warning)
        _dbg("EXIT WorkbookRepository._merge_validation_feedback")  # DEBUG

    @staticmethod
    def _format_validation_errors(
        source_path: str, validation_result: SupportsValidationResult
    ) -> str:
        _dbg("ENTER WorkbookRepository._format_validation_errors")  # DEBUG
        errors = list(getattr(validation_result, "errors", []) or [])
        if not errors:
            _dbg("EXIT WorkbookRepository._format_validation_errors (no errors)")  # DEBUG
            return f"Workbook '{source_path}' failed validation."
        joined = "; ".join(str(error) for error in errors)
        _dbg("EXIT WorkbookRepository._format_validation_errors")  # DEBUG
        return f"Workbook '{source_path}' failed validation: {joined}"

"""Single data access layer for the engineering monitoring dashboard.

This module exposes :class:`WorkbookRepository`, the only component in
the application that is allowed to coordinate loading, validating, and
parsing a workbook into the strongly typed
:class:`~models.workbook.Workbook` object graph consumed by the rest of
the dashboard.

Responsibilities are strictly limited to *data access orchestration*:

* Ask a :class:`~services.loader_service.LoaderService` (or equivalent)
  to load a workbook from its source (file path, cache, GitHub, etc.).
* Ask a validator to check that the loaded workbook is structurally
  sound, reusing whatever structure the validator already discovered
  instead of re-discovering it.
* Hand the loaded workbook — and, when available, the validator's
  already-discovered structure — to a
  :class:`~services.parser_service.ParserService` to build the final
  :class:`~models.workbook.Workbook` model.

This module deliberately contains:

* No KPI calculations.
* No chart generation.
* No Streamlit or any other UI code.

Loader, Validator, and Parser are all supplied via constructor
dependency injection, so this repository has no hardcoded knowledge of
*how* a workbook is loaded, validated, or parsed — only of the order in
which those three steps happen and how their outputs are threaded
together.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from models.workbook import Workbook, WorkbookMetadata


# ----------------------------------------------------------------------
# Collaborator protocols
# ----------------------------------------------------------------------
# The repository depends only on these narrow, structural interfaces
# rather than on concrete Loader/Validator/Parser classes. This keeps
# the repository decoupled from their implementations (per the
# Dependency Inversion Principle) and makes it straightforward to inject
# fakes/mocks in tests. Concrete collaborators only need to satisfy the
# shape described here; they need not literally subclass these
# protocols.

@runtime_checkable
class SupportsRawWorkbook(Protocol):
    """Structural interface for whatever a Loader hands back.

    Concrete loaders are free to return a richer dataclass (for example
    one also carrying cache-hit information or a content SHA); the
    repository only relies on the attributes declared here.

    Attributes:
        raw_workbook: The already-open ``openpyxl`` workbook object.
        source_path: The path or identifier the workbook was loaded
            from, used for diagnostics and as a fallback workbook name.
        metadata: Descriptive metadata about the loaded workbook file.
        success: Whether loading completed without a fatal error.
        error: A human-readable description of the load failure, if
            ``success`` is ``False``.
    """

    raw_workbook: object
    source_path: str
    metadata: Optional[WorkbookMetadata]
    success: bool
    error: Optional[str]


@runtime_checkable
class SupportsValidationResult(Protocol):
    """Structural interface for whatever a Validator hands back.

    Attributes:
        is_valid: Whether the workbook passed validation.
        structure: The workbook structure the validator discovered while
            validating, if any. When present, the repository passes this
            straight into the parser so structure is never discovered
            twice.
        errors: Fatal validation error messages.
        warnings: Non-fatal validation warning messages.
    """

    is_valid: bool
    structure: Optional[object]
    errors: list
    warnings: list


@runtime_checkable
class LoaderLike(Protocol):
    """Structural interface required of an injected Loader."""

    def load(self, source_path: str) -> SupportsRawWorkbook:
        """Loads a workbook from its source.

        Args:
            source_path: Path or identifier of the workbook to load.

        Returns:
            An object satisfying :class:`SupportsRawWorkbook`.
        """
        ...


@runtime_checkable
class ValidatorLike(Protocol):
    """Structural interface required of an injected Validator."""

    def validate(self, raw_workbook: object) -> SupportsValidationResult:
        """Validates an already-loaded workbook.

        Args:
            raw_workbook: The already-open ``openpyxl`` workbook to
                validate.

        Returns:
            An object satisfying :class:`SupportsValidationResult`.
        """
        ...


@runtime_checkable
class ParserServiceLike(Protocol):
    """Structural interface required of an injected ParserService."""

    def parse(
        self,
        raw_workbook: object,
        workbook_name: Optional[str] = None,
        structure: Optional[object] = None,
        metadata: Optional[WorkbookMetadata] = None,
    ) -> Workbook:
        """Parses an already-loaded workbook into a typed Workbook.

        Args:
            raw_workbook: The already-open ``openpyxl`` workbook.
            workbook_name: A human-friendly name for the workbook.
            structure: A previously discovered workbook structure to
                reuse, if available.
            metadata: Descriptive metadata about the workbook file.

        Returns:
            A populated :class:`~models.workbook.Workbook`.
        """
        ...


# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------

class WorkbookRepositoryError(Exception):
    """Raised when the repository cannot produce a Workbook model.

    This wraps and normalizes failures from any of the three
    collaborators (Loader, Validator, ParserService) into a single,
    meaningful exception type so callers only need to handle one error
    class regardless of which stage failed.
    """


class WorkbookLoadError(WorkbookRepositoryError):
    """Raised when the Loader fails to load a workbook from its source."""


class WorkbookValidationError(WorkbookRepositoryError):
    """Raised when a loaded workbook fails validation.

    Only raised when the caller has not opted in to receiving a parsed
    (but validation-flagged) workbook via ``strict=False``.
    """


# ----------------------------------------------------------------------
# Repository
# ----------------------------------------------------------------------

class WorkbookRepository:
    """Coordinates Loader, Validator, and ParserService for the app.

    This is the single point through which the rest of the application
    (services, pages) obtains a fully populated
    :class:`~models.workbook.Workbook`. It performs no data
    transformation of its own beyond threading the outputs of one
    collaborator into the inputs of the next.

    Attributes:
        loader: Loads a raw workbook from its source (file path, cache,
            remote store, etc.).
        validator: Validates a raw workbook and discovers its structure.
        parser_service: Builds the final :class:`Workbook` model from a
            raw workbook and, when available, an already-discovered
            structure.
    """

    def __init__(
        self,
        loader: LoaderLike,
        validator: ValidatorLike,
        parser_service: ParserServiceLike,
    ) -> None:
        """Initializes the repository with its three collaborators.

        Args:
            loader: An object satisfying :class:`LoaderLike`.
            validator: An object satisfying :class:`ValidatorLike`.
            parser_service: An object satisfying :class:`ParserServiceLike`.
        """
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
        """Loads, validates, and parses a workbook into a typed model.

        Args:
            source_path: Path or identifier of the workbook to load.
            workbook_name: Optional human-friendly name for the
                workbook. Defaults to ``source_path`` when omitted.
            strict: When ``True``, a workbook that fails validation
                raises :class:`WorkbookValidationError` instead of being
                parsed. When ``False`` (the default), validation
                warnings and errors are still recorded on the returned
                :class:`Workbook`, but parsing proceeds regardless, so
                the caller can decide how to react to a partially valid
                workbook.

        Returns:
            A fully populated :class:`~models.workbook.Workbook`.

        Raises:
            WorkbookLoadError: If the Loader could not produce a raw
                workbook from ``source_path``.
            WorkbookValidationError: If ``strict`` is ``True`` and the
                workbook fails validation.
            WorkbookRepositoryError: If parsing fails for any other
                reason.
        """
"""Single data access layer for the engineering monitoring dashboard.

This module exposes :class:`WorkbookRepository`, the only component in
the application that is allowed to coordinate loading, validating, and
parsing a workbook into the strongly typed
:class:`~models.workbook.Workbook` object graph consumed by the rest of
the dashboard.

Responsibilities are strictly limited to *data access orchestration*:

* Ask a :class:`~services.loader_service.LoaderService` (or equivalent)
  to load a workbook from its source (file path, cache, GitHub, etc.).
* Ask a validator to check that the loaded workbook is structurally
  sound, reusing whatever structure the validator already discovered
  instead of re-discovering it.
* Hand the loaded workbook — and, when available, the validator's
  already-discovered structure — to a
  :class:`~services.parser_service.ParserService` to build the final
  :class:`~models.workbook.Workbook` model.

This module deliberately contains:

* No KPI calculations.
* No chart generation.
* No Streamlit or any other UI code.

Loader, Validator, and Parser are all supplied via constructor
dependency injection, so this repository has no hardcoded knowledge of
*how* a workbook is loaded, validated, or parsed — only of the order in
which those three steps happen and how their outputs are threaded
together.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from models.workbook import Workbook, WorkbookMetadata


# ----------------------------------------------------------------------
# Collaborator protocols
# ----------------------------------------------------------------------
# The repository depends only on these narrow, structural interfaces
# rather than on concrete Loader/Validator/Parser classes. This keeps
# the repository decoupled from their implementations (per the
# Dependency Inversion Principle) and makes it straightforward to inject
# fakes/mocks in tests. Concrete collaborators only need to satisfy the
# shape described here; they need not literally subclass these
# protocols.

@runtime_checkable
class SupportsRawWorkbook(Protocol):
    """Structural interface for whatever a Loader hands back.

    Concrete loaders are free to return a richer dataclass (for example
    one also carrying cache-hit information or a content SHA); the
    repository only relies on the attributes declared here.

    Attributes:
        raw_workbook: The already-open ``openpyxl`` workbook object.
        source_path: The path or identifier the workbook was loaded
            from, used for diagnostics and as a fallback workbook name.
        metadata: Descriptive metadata about the loaded workbook file.
        success: Whether loading completed without a fatal error.
        error: A human-readable description of the load failure, if
            ``success`` is ``False``.
    """

    raw_workbook: object
    source_path: str
    metadata: Optional[WorkbookMetadata]
    success: bool
    error: Optional[str]


@runtime_checkable
class SupportsValidationResult(Protocol):
    """Structural interface for whatever a Validator hands back.

    Attributes:
        is_valid: Whether the workbook passed validation.
        structure: The workbook structure the validator discovered while
            validating, if any. When present, the repository passes this
            straight into the parser so structure is never discovered
            twice.
        errors: Fatal validation error messages.
        warnings: Non-fatal validation warning messages.
    """

    is_valid: bool
    structure: Optional[object]
    errors: list
    warnings: list


@runtime_checkable
class LoaderLike(Protocol):
    """Structural interface required of an injected Loader."""

    def load(self, source_path: str) -> SupportsRawWorkbook:
        """Loads a workbook from its source.

        Args:
            source_path: Path or identifier of the workbook to load.

        Returns:
            An object satisfying :class:`SupportsRawWorkbook`.
        """
        ...


@runtime_checkable
class ValidatorLike(Protocol):
    """Structural interface required of an injected Validator."""

    def validate(self, raw_workbook: object) -> SupportsValidationResult:
        """Validates an already-loaded workbook.

        Args:
            raw_workbook: The already-open ``openpyxl`` workbook to
                validate.

        Returns:
            An object satisfying :class:`SupportsValidationResult`.
        """
        ...


@runtime_checkable
class ParserServiceLike(Protocol):
    """Structural interface required of an injected ParserService."""

    def parse(
        self,
        raw_workbook: object,
        workbook_name: Optional[str] = None,
        structure: Optional[object] = None,
        metadata: Optional[WorkbookMetadata] = None,
    ) -> Workbook:
        """Parses an already-loaded workbook into a typed Workbook.

        Args:
            raw_workbook: The already-open ``openpyxl`` workbook.
            workbook_name: A human-friendly name for the workbook.
            structure: A previously discovered workbook structure to
                reuse, if available.
            metadata: Descriptive metadata about the workbook file.

        Returns:
            A populated :class:`~models.workbook.Workbook`.
        """
        ...


# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------

class WorkbookRepositoryError(Exception):
    """Raised when the repository cannot produce a Workbook model.

    This wraps and normalizes failures from any of the three
    collaborators (Loader, Validator, ParserService) into a single,
    meaningful exception type so callers only need to handle one error
    class regardless of which stage failed.
    """


class WorkbookLoadError(WorkbookRepositoryError):
    """Raised when the Loader fails to load a workbook from its source."""


class WorkbookValidationError(WorkbookRepositoryError):
    """Raised when a loaded workbook fails validation.

    Only raised when the caller has not opted in to receiving a parsed
    (but validation-flagged) workbook via ``strict=False``.
    """


# ----------------------------------------------------------------------
# Repository
# ----------------------------------------------------------------------

class WorkbookRepository:
    """Coordinates Loader, Validator, and ParserService for the app.

    This is the single point through which the rest of the application
    (services, pages) obtains a fully populated
    :class:`~models.workbook.Workbook`. It performs no data
    transformation of its own beyond threading the outputs of one
    collaborator into the inputs of the next.

    Attributes:
        loader: Loads a raw workbook from its source (file path, cache,
            remote store, etc.).
        validator: Validates a raw workbook and discovers its structure.
        parser_service: Builds the final :class:`Workbook` model from a
            raw workbook and, when available, an already-discovered
            structure.
    """

    def __init__(
        self,
        loader: LoaderLike,
        validator: ValidatorLike,
        parser_service: ParserServiceLike,
    ) -> None:
        """Initializes the repository with its three collaborators.

        Args:
            loader: An object satisfying :class:`LoaderLike`.
            validator: An object satisfying :class:`ValidatorLike`.
            parser_service: An object satisfying :class:`ParserServiceLike`.
        """
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
        """Loads, validates, and parses a workbook into a typed model.

        Args:
            source_path: Path or identifier of the workbook to load.
            workbook_name: Optional human-friendly name for the
                workbook. Defaults to ``source_path`` when omitted.
            strict: When ``True``, a workbook that fails validation
                raises :class:`WorkbookValidationError` instead of being
                parsed. When ``False`` (the default), validation
                warnings and errors are still recorded on the returned
                :class:`Workbook`, but parsing proceeds regardless, so
                the caller can decide how to react to a partially valid
                workbook.

        Returns:
            A fully populated :class:`~models.workbook.Workbook`.

        Raises:
            WorkbookLoadError: If the Loader could not produce a raw
                workbook from ``source_path``.
            WorkbookValidationError: If ``strict`` is ``True`` and the
                workbook fails validation.
            WorkbookRepositoryError: If parsing fails for any other
                reason.
        """
        load_result = self._load(source_path)
        validation_result = self._validate(load_result.raw_workbook)

        if strict and not validation_result.is_valid:
            raise WorkbookValidationError(
                self._format_validation_errors(source_path, validation_result)
            )

        resolved_name = workbook_name or getattr(
            load_result, "source_path", source_path
        )
        resolved_metadata = getattr(load_result, "metadata", None)
        reusable_structure = getattr(validation_result, "structure", None)

        workbook = self._parse(
            raw_workbook=load_result.raw_workbook,
            workbook_name=resolved_name,
            structure=reusable_structure,
            metadata=resolved_metadata,
        )

        self._merge_validation_feedback(workbook, validation_result)
        return workbook

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------

    def _load(self, source_path: str) -> SupportsRawWorkbook:
        """Loads a workbook from its source via the injected Loader.

        Args:
            source_path: Path or identifier of the workbook to load.

        Returns:
            The Loader's result, satisfying :class:`SupportsRawWorkbook`.

        Raises:
            WorkbookLoadError: If loading raises an unexpected exception
                or reports failure via ``success``/``error``.
        """
        try:
            load_result = self.loader.load(source_path)
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
            raise WorkbookLoadError(
                f"Failed to load workbook from '{source_path}': {exc}"
            ) from exc

        success = getattr(load_result, "success", True)
        if not success:
            error_message = getattr(load_result, "error", "unknown error")
            raise WorkbookLoadError(
                f"Failed to load workbook from '{source_path}': {error_message}"
            )

        raw_workbook = getattr(load_result, "raw_workbook", None)
        if raw_workbook is None:
            raise WorkbookLoadError(
                f"Loader returned no workbook for '{source_path}'."
            )

        return load_result

    def _validate(self, raw_workbook: object) -> SupportsValidationResult:
        """Validates a raw workbook via the injected Validator.

        Args:
            raw_workbook: The already-open workbook to validate.

        Returns:
            The Validator's result, satisfying
            :class:`SupportsValidationResult`.

        Raises:
            WorkbookRepositoryError: If validation raises an unexpected
                exception.
        """
        try:
            return self.validator.validate(raw_workbook)
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
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
        """Parses a raw workbook via the injected ParserService.

        Reuses ``structure`` (typically produced by the Validator) so
        the workbook's layout is never discovered more than once.

        Args:
            raw_workbook: The already-open workbook to parse.
            workbook_name: The resolved human-friendly workbook name.
            structure: A previously discovered workbook structure to
                reuse, if the validator produced one.
            metadata: Descriptive metadata about the workbook file.

        Returns:
            A populated :class:`~models.workbook.Workbook`.

        Raises:
            WorkbookRepositoryError: If parsing raises an unexpected
                exception.
        """
        try:
            return self.parser_service.parse(
                raw_workbook,
                workbook_name=workbook_name,
                structure=structure,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
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
        """Folds validator warnings/errors into the parsed Workbook.

        Parsing may surface its own warnings and errors independently of
        validation; this appends the validator's findings rather than
        overwriting them, so no diagnostic information from either stage
        is lost.

        Args:
            workbook: The parsed workbook to update in place.
            validation_result: The validator's result for the same
                workbook.
        """
        validation_errors = list(getattr(validation_result, "errors", []) or [])
        validation_warnings = list(getattr(validation_result, "warnings", []) or [])

        for error in validation_errors:
            if error not in workbook.errors:
                workbook.errors.append(error)

        for warning in validation_warnings:
            if warning not in workbook.warnings:
                workbook.warnings.append(warning)

    @staticmethod
    def _format_validation_errors(
        source_path: str, validation_result: SupportsValidationResult
    ) -> str:
        """Builds a human-readable message describing validation failures.

        Args:
            source_path: The workbook source path, for context.
            validation_result: The failed validation result.

        Returns:
            A single formatted message summarizing all validation
            errors.
        """
        errors = list(getattr(validation_result, "errors", []) or [])
        if not errors:
            return f"Workbook '{source_path}' failed validation."
        joined = "; ".join(str(error) for error in errors)
        return f"Workbook '{source_path}' failed validation: {joined}"

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------

    def _load(self, source_path: str) -> SupportsRawWorkbook:
        """Loads a workbook from its source via the injected Loader.

        Args:
            source_path: Path or identifier of the workbook to load.

        Returns:
            The Loader's result, satisfying :class:`SupportsRawWorkbook`.

        Raises:
            WorkbookLoadError: If loading raises an unexpected exception
                or reports failure via ``success``/``error``.
        """
        try:
            load_result = self.loader.load(source_path)
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
            raise WorkbookLoadError(
                f"Failed to load workbook from '{source_path}': {exc}"
            ) from exc

        success = getattr(load_result, "success", True)
        if not success:
            error_message = getattr(load_result, "error", "unknown error")
            raise WorkbookLoadError(
                f"Failed to load workbook from '{source_path}': {error_message}"
            )

        raw_workbook = getattr(load_result, "raw_workbook", None)
        if raw_workbook is None:
            raise WorkbookLoadError(
                f"Loader returned no workbook for '{source_path}'."
            )

        return load_result

    def _validate(self, raw_workbook: object) -> SupportsValidationResult:
        """Validates a raw workbook via the injected Validator.

        Args:
            raw_workbook: The already-open workbook to validate.

        Returns:
            The Validator's result, satisfying
            :class:`SupportsValidationResult`.

        Raises:
            WorkbookRepositoryError: If validation raises an unexpected
                exception.
        """
        try:
            return self.validator.validate(raw_workbook)
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
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
        """Parses a raw workbook via the injected ParserService.

        Reuses ``structure`` (typically produced by the Validator) so
        the workbook's layout is never discovered more than once.

        Args:
            raw_workbook: The already-open workbook to parse.
            workbook_name: The resolved human-friendly workbook name.
            structure: A previously discovered workbook structure to
                reuse, if the validator produced one.
            metadata: Descriptive metadata about the workbook file.

        Returns:
            A populated :class:`~models.workbook.Workbook`.

        Raises:
            WorkbookRepositoryError: If parsing raises an unexpected
                exception.
        """
        try:
            return self.parser_service.parse(
                raw_workbook,
                workbook_name=workbook_name,
                structure=structure,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001 - normalized into one error type
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
        """Folds validator warnings/errors into the parsed Workbook.

        Parsing may surface its own warnings and errors independently of
        validation; this appends the validator's findings rather than
        overwriting them, so no diagnostic information from either stage
        is lost.

        Args:
            workbook: The parsed workbook to update in place.
            validation_result: The validator's result for the same
                workbook.
        """
        validation_errors = list(getattr(validation_result, "errors", []) or [])
        validation_warnings = list(getattr(validation_result, "warnings", []) or [])

        for error in validation_errors:
            if error not in workbook.errors:
                workbook.errors.append(error)

        for warning in validation_warnings:
            if warning not in workbook.warnings:
                workbook.warnings.append(warning)

    @staticmethod
    def _format_validation_errors(
        source_path: str, validation_result: SupportsValidationResult
    ) -> str:
        """Builds a human-readable message describing validation failures.

        Args:
            source_path: The workbook source path, for context.
            validation_result: The failed validation result.

        Returns:
            A single formatted message summarizing all validation
            errors.
        """
        errors = list(getattr(validation_result, "errors", []) or [])
        if not errors:
            return f"Workbook '{source_path}' failed validation."
        joined = "; ".join(str(error) for error in errors)
        return f"Workbook '{source_path}' failed validation: {joined}"

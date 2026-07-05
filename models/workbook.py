"""Top-level workbook data model for the engineering monitoring dashboard.

A :class:`Workbook` is the root container for everything discovered in a
single uploaded monthly workbook: its metadata, the sheets it contains,
its validation outcome, the date range it covers, and the hierarchy of
sections found inside it. Nothing in this module names or assumes any
particular sheet, section, or department; all of that content is supplied
by whatever discovers it at runtime, so a workbook with a different
internal layout can be represented without any change here.

This module contains data containers only: no parsing, no calculations,
and no Excel or Streamlit dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from models.section import DateRange, Section


class ValidationStatus(str, Enum):
    """The outcome of validating a workbook.

    Attributes:
        NOT_VALIDATED: The workbook has not yet been validated.
        VALID: The workbook passed validation with no issues.
        VALID_WITH_WARNINGS: The workbook passed validation but produced
            non-fatal warnings.
        INVALID: The workbook failed validation.
    """

    NOT_VALIDATED = "not_validated"
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"


@dataclass
class WorkbookMetadata:
    """Descriptive, non-business metadata about a workbook file.

    Attributes:
        source_path: The file system path or original filename the
            workbook was loaded from, if known.
        file_size_bytes: The size of the workbook file in bytes, if known.
        loaded_at: The point in time the workbook was loaded.
        additional_properties: Arbitrary additional descriptive
            information about the workbook file, keyed by name, so new
            metadata attributes never require a schema change.
    """

    source_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    loaded_at: Optional[datetime] = None
    additional_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workbook:
    """The root model representing an entire engineering monitoring workbook.

    Attributes:
        name: The human-friendly name of the workbook (for example its
            original filename without extension).
        metadata: Descriptive metadata about the workbook file itself.
        available_sheets: The names of every worksheet present in the
            workbook, in workbook order.
        validation_status: The outcome of validating this workbook.
        date_range: The overall span of dates covered by the workbook's
            data, if known.
        sections: The top-level :class:`Section` instances discovered in
            the workbook, in the order discovered.
        units: The distinct units of measurement used anywhere in the
            workbook.
        warnings: Non-fatal, human-readable messages produced while
            loading or validating the workbook.
        errors: Fatal, human-readable messages produced while loading or
            validating the workbook.
        metadata_extra: Arbitrary additional information about the
            workbook as a whole, keyed by name, so new descriptive
            attributes never require a schema change.
    """

    name: str
    metadata: WorkbookMetadata = field(default_factory=WorkbookMetadata)
    available_sheets: List[str] = field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.NOT_VALIDATED
    date_range: Optional[DateRange] = None
    sections: List[Section] = field(default_factory=list, repr=False)
    units: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list, repr=False)
    errors: List[str] = field(default_factory=list, repr=False)
    metadata_extra: Dict[str, Any] = field(default_factory=dict)

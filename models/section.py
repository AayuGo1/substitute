"""Section and sub-section data models for the engineering monitoring dashboard.

A workbook is organized into an arbitrary, workbook-defined hierarchy of
sections and sub-sections (for example a department block, a plant area,
or any grouping the source workbook happens to use). Nothing in this
module names, counts, or assumes any particular section or sub-section;
the hierarchy is populated entirely by whatever discovers it at runtime.

This module contains data containers only: no parsing, no calculations,
and no Excel or Streamlit dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.metric import Metric


@dataclass
class DateRange:
    """A closed interval of dates covered by a set of workbook data.

    Attributes:
        start: The earliest date covered by the data.
        end: The latest date covered by the data.
    """

    start: Optional[datetime] = None
    end: Optional[datetime] = None


@dataclass
class SectionBase:
    """Fields shared by every level of the section hierarchy.

    This base exists purely to avoid duplicating the same field
    declarations between :class:`SubSection` and :class:`Section`; it is
    not intended to be instantiated directly.

    Attributes:
        name: The stable, internal identifier for this section or
            sub-section (for example a normalized version of its source
            label).
        display_name: The human-friendly label to show in the dashboard.
        description: An optional free-text explanation of what this
            section or sub-section represents.
        metrics: The metrics that belong directly to this section or
            sub-section.
        units: The distinct units of measurement used by the metrics
            contained in this section or sub-section.
        date_range: The span of dates covered by this section's data, if
            known.
        metadata: Arbitrary additional information about this section or
            sub-section, keyed by name, so new descriptive attributes
            never require a schema change.
    """

    name: str
    display_name: str
    description: str = ""
    metrics: List[Metric] = field(default_factory=list, repr=False)
    units: List[str] = field(default_factory=list)
    date_range: Optional[DateRange] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubSection(SectionBase):
    """A leaf-level grouping of metrics beneath a parent :class:`Section`.

    Inherits ``name``, ``display_name``, ``description``, ``metrics``,
    ``units``, ``date_range``, and ``metadata`` from :class:`SectionBase`.
    """


@dataclass
class Section(SectionBase):
    """A top-level grouping of metrics and sub-sections within a workbook.

    Inherits ``name``, ``display_name``, ``description``, ``metrics``,
    ``units``, ``date_range``, and ``metadata`` from :class:`SectionBase`,
    and additionally supports nested sub-sections.

    Attributes:
        subsections: The child :class:`SubSection` instances that belong
            to this section, in the order discovered.
    """

    subsections: List[SubSection] = field(default_factory=list, repr=False)

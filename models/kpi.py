"""Key Performance Indicator (KPI) data models for the monitoring dashboard.

These models describe the shape of a KPI (its total, average, last
registered value, maximum, minimum, trend, percentage change, unit, and
timestamp) without computing any of those values. Populating a
:class:`KPI` instance is the responsibility of a separate business-logic
layer; this module only defines what a KPI looks like once computed.

This module contains data containers only: no parsing, no calculations,
and no Excel or Streamlit dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TrendDirection(str, Enum):
    """The qualitative direction a KPI's value has moved over its period.

    Attributes:
        UP: The value has increased.
        DOWN: The value has decreased.
        FLAT: The value has stayed effectively unchanged.
        UNKNOWN: The direction has not been determined.
    """

    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    UNKNOWN = "unknown"


@dataclass
class KPI:
    """A single, generically typed key performance indicator.

    A ``KPI`` only models the fields a computed indicator can have; it
    never derives, aggregates, or recalculates values itself. Any of the
    numeric fields may be ``None`` when a value is not applicable or has
    not yet been supplied.

    Attributes:
        name: The stable, internal identifier for this KPI.
        display_name: The human-friendly label to show in the dashboard.
        unit: The unit of measurement the KPI's values are expressed in.
        total: The total value for the KPI's period, if applicable.
        average: The average value for the KPI's period, if applicable.
        last_value: The most recently registered value for this KPI.
        maximum: The maximum value observed for this KPI's period.
        minimum: The minimum value observed for this KPI's period.
        trend: The qualitative direction of change for this KPI.
        percentage_change: The percentage change over the KPI's period.
        timestamp: The point in time this KPI was last evaluated.
        metadata: Arbitrary additional information about this KPI, keyed
            by name, so new descriptive attributes never require a
            schema change.
    """

    name: str
    display_name: str
    unit: str
    total: Optional[float] = None
    average: Optional[float] = None
    last_value: Optional[float] = None
    maximum: Optional[float] = None
    minimum: Optional[float] = None
    trend: Optional[TrendDirection] = None
    percentage_change: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KPICollection:
    """A named group of related KPIs, for example all KPIs for one section.

    Attributes:
        name: The stable, internal identifier for this collection.
        display_name: The human-friendly label to show in the dashboard.
        kpis: The individual :class:`KPI` instances belonging to this
            collection, in the order supplied by the caller.
        metadata: Arbitrary additional information about this collection,
            keyed by name.
    """

    name: str
    display_name: str
    kpis: List[KPI] = field(default_factory=list, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

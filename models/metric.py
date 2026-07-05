"""Generic metric data models for the engineering monitoring dashboard.

A :class:`Metric` represents a single named quantity read from the
workbook (for example an NPCL reading, a DG running-hour count, an Air
Compressor pressure value, a Freon meter reading, a water consumption
figure, or an energy total). The model carries no knowledge of what kind
of metric it represents; that meaning lives entirely in the data supplied
by the caller, so new metric types can be introduced without any change
to this module.

This module contains data containers only: no parsing, no calculations,
and no Excel or Streamlit dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MetricDataPoint:
    """A single timestamped observation belonging to a metric's history.

    Attributes:
        timestamp: The point in time the observation was recorded.
        value: The observed numeric value, or ``None`` if the workbook
            recorded no usable value for this point in time.
        metadata: Arbitrary additional information about this specific
            observation (for example a data quality flag), keyed by name.
    """

    timestamp: datetime
    value: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """A single, generically typed measurable quantity from the workbook.

    A ``Metric`` is intentionally agnostic about domain meaning. Whether it
    represents an NPCL reading, a DG running-hour count, an Air Compressor
    pressure, a Freon meter value, a water figure, or any metric added to
    a future monthly workbook, the shape of this model never changes.

    Attributes:
        name: The stable, internal identifier for this metric (for example
            a normalized version of its source column header).
        display_name: The human-friendly label to show in the dashboard.
        unit: The unit of measurement for the metric's values (for example
            "kWh", "hours", "bar"). Left as a plain string so any unit
            encountered in any workbook can be represented.
        current_value: The most recently known value for this metric.
        timestamp: The point in time ``current_value`` was recorded.
        historical_values: The metric's full history of observations,
            ordered as supplied by the caller.
        metadata: Arbitrary additional information about this metric
            (for example its source sheet or column position), keyed by
            name, so new descriptive attributes never require a schema
            change.
    """

    name: str
    display_name: str
    unit: str
    current_value: Optional[float] = None
    timestamp: Optional[datetime] = None
    historical_values: List[MetricDataPoint] = field(
        default_factory=list, repr=False
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

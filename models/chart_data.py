"""Reusable chart data models for the engineering monitoring dashboard.

These models describe the shape of chart-ready data (axes, series, and
labels) in plain Python types so they can be handed directly to a
charting library's plotting calls (for example Plotly's ``x=``, ``y=``,
and ``name=`` arguments). No charting library is imported here; this
module only defines the data shape, leaving rendering to the UI layer.

This module contains data containers only: no parsing, no calculations,
and no Excel or Streamlit dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TrendPeriod(str, Enum):
    """The time granularity a trend chart's data points represent.

    Attributes:
        DAILY: Each data point represents one day.
        WEEKLY: Each data point represents one week.
        MONTHLY: Each data point represents one month.
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ChartAxis:
    """A single chart axis and the values plotted along it.

    Attributes:
        label: The human-friendly axis title.
        unit: The unit of measurement for the axis's values, if
            applicable.
        values: The values plotted along this axis, in plot order. Left
            untyped beyond ``Any`` so an axis can carry dates, numbers,
            or category labels without this model changing.
    """

    label: str
    unit: Optional[str] = None
    values: List[Any] = field(default_factory=list, repr=False)


@dataclass
class ChartSeries:
    """A single named series of values to be plotted against a shared axis.

    Attributes:
        name: The human-friendly label for this series (for example a
            metric's display name), used as a chart legend entry.
        values: The series' plotted values, in the same order as the
            chart's x-axis values.
        unit: The unit of measurement for this series' values, if
            applicable.
        metadata: Arbitrary additional information about this series,
            keyed by name (for example a suggested colour or line style).
    """

    name: str
    values: List[Any] = field(default_factory=list, repr=False)
    unit: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartData:
    """A complete, charting-library-agnostic chart definition.

    Attributes:
        title: The human-friendly chart title.
        x_axis: The chart's shared horizontal axis.
        y_axis: The chart's shared vertical axis.
        series: The one or more data series plotted on this chart.
        labels: Optional discrete labels associated with the chart's data
            points (for example category names), separate from the axis
            values themselves.
        metadata: Arbitrary additional information about this chart,
            keyed by name.
    """

    title: str
    x_axis: ChartAxis
    y_axis: ChartAxis
    series: List[ChartSeries] = field(default_factory=list, repr=False)
    labels: List[str] = field(default_factory=list, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendChartData:
    """A chart definition associated with a specific trend granularity.

    Composes a :class:`ChartData` with a :class:`TrendPeriod` rather than
    duplicating axis and series fields for daily, weekly, and monthly
    variants.

    Attributes:
        period: The time granularity this chart's data points represent.
        chart: The underlying chart definition.
        metadata: Arbitrary additional information about this trend
            chart, keyed by name.
    """

    period: TrendPeriod
    chart: ChartData
    metadata: Dict[str, Any] = field(default_factory=dict)

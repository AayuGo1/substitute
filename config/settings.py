"""
config/settings.py

Central application configuration for the Engineering Monitoring
Dashboard.

This module is the single source of truth for global, application-wide
constants: display metadata (title, version, icon), layout defaults,
refresh/cache timing, date/time formatting, timezone, chart defaults,
and reusable string constants used across the UI layer.

This module contains:
    - No business logic.
    - No Streamlit code (no ``st.*`` calls).
    - No Excel parsing.
    - No GitHub / data-source logic.
    - No hardcoded workbook-specific values (no sheet names, section
      names, department names, or metric names). Anything specific to
      a particular workbook's structure belongs to the discovery and
      parsing layer, never here.

Every other module that needs an application-wide constant should
import it from here rather than redeclaring it inline, so the app's
global configuration can be changed in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


# ----------------------------------------------------------------------
# Application identity
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class AppIdentity:
    """Identity and branding metadata for the application.

    Attributes:
        title: The dashboard's display title, shown in the browser tab
            and in navigation headers.
        version: The application's current version string, following
            semantic versioning (``MAJOR.MINOR.PATCH``).
        icon: The default page icon (an emoji glyph or a path/URL to an
            image), used for the browser tab and as a UI fallback where
            no workbook-specific icon is available.
        description: A short, human-readable description of the
            application's purpose.
    """

    title: str = "Engineering Monitoring Dashboard"
    version: str = "1.0.0"
    icon: str = "\U0001F3ED"
    description: str = (
        "A unified monitoring dashboard for engineering department "
        "workbooks, covering KPIs, trends, and summary reporting."
    )


# ----------------------------------------------------------------------
# Page / layout defaults
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class LayoutSettings:
    """Default Streamlit page-layout configuration values.

    Attributes:
        page_layout: The default page layout mode (``"wide"`` or
            ``"centered"``), as accepted by ``st.set_page_config``.
        initial_sidebar_state: The sidebar's initial state
            (``"expanded"``, ``"collapsed"``, or ``"auto"``), as
            accepted by ``st.set_page_config``.
        max_content_width_percent: The maximum width, as a percentage
            of the viewport, that the main content area should occupy
            on wide layouts.
        default_kpi_columns: The default maximum number of columns to
            use when arranging KPI card grids.
        default_summary_columns: The default maximum number of columns
            to use when arranging summary card grids.
    """

    page_layout: str = "wide"
    initial_sidebar_state: str = "expanded"
    max_content_width_percent: int = 100
    default_kpi_columns: int = 4
    default_summary_columns: int = 3


# ----------------------------------------------------------------------
# Refresh / caching
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class CacheSettings:
    """Default caching and refresh timing configuration.

    All durations are expressed in seconds unless otherwise noted.

    Attributes:
        workbook_cache_ttl_seconds: How long a loaded workbook may be
            served from cache before being reloaded from its source.
        auto_refresh_interval_seconds: How frequently the dashboard
            should automatically attempt to refresh its data, if
            auto-refresh is enabled by the caller.
        request_timeout_seconds: Default timeout applied to outbound
            network requests (for example downloading a workbook file)
            when no more specific timeout is configured.
        resource_cache_ttl_seconds: Default time-to-live for cached,
            expensive-to-construct resources (for example service
            instances), independent of workbook content caching.
    """

    workbook_cache_ttl_seconds: int = 300
    auto_refresh_interval_seconds: int = 300
    request_timeout_seconds: float = 15.0
    resource_cache_ttl_seconds: int = 3600


# ----------------------------------------------------------------------
# Date / time formatting
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class DateTimeSettings:
    """Default date, time, and timezone formatting configuration.

    These formats govern only how already-resolved date/time values are
    *displayed*; they are not used to hardcode any assumption about a
    specific workbook's date layout, which remains fully dynamic and is
    discovered at parse time.

    Attributes:
        date_format: The default ``strftime``-compatible format string
            used to display dates (e.g. "05 Jul 2026").
        time_format: The default ``strftime``-compatible format string
            used to display times (e.g. "14:32:07").
        datetime_format: The default ``strftime``-compatible format
            string used to display combined date and time values.
        timezone: The default IANA timezone identifier used when
            rendering timestamps, if the application needs to localize
            times for display. Defaults to UTC to avoid making any
            assumption about the deployment environment's local
            timezone.
    """

    date_format: str = "%d %b %Y"
    time_format: str = "%H:%M:%S"
    datetime_format: str = "%d %b %Y %H:%M:%S"
    timezone: str = "UTC"


# ----------------------------------------------------------------------
# Chart defaults
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ChartSettings:
    """Default chart configuration values.

    These are generic, chart-engine-level defaults only; they carry no
    knowledge of any specific metric, section, or workbook content.

    Attributes:
        default_chart_type: The default chart type used when a caller
            does not specify one explicitly (e.g. "line").
        default_aggregation: The default trend aggregation applied when
            a caller does not specify one explicitly (e.g. "none").
        sparkline_point_limit: The maximum number of points to include
            in a compact sparkline visualization, to keep it readable
            at a small size.
        default_chart_height_px: The default height, in pixels, used
            for standard trend charts.
        default_line_width: The default line width, in points, used for
            chart trend lines.
    """

    default_chart_type: str = "line"
    default_aggregation: str = "none"
    sparkline_point_limit: int = 30
    default_chart_height_px: int = 320
    default_line_width: float = 2.0


# ----------------------------------------------------------------------
# Reusable string constants
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class UIStrings:
    """Reusable, generic UI string constants shared across components.

    These strings are intentionally generic (loading/error/empty
    states, button labels) and carry no workbook-specific wording.

    Attributes:
        loading_message: Default message shown while data is loading.
        error_title: Default heading shown on the error screen.
        empty_workbook_message: Default message shown when no usable
            data was discovered in a loaded workbook.
        refresh_button_label: Default label for refresh/reload actions.
        retry_button_label: Default label for retry actions on error or
            empty states.
        no_data_placeholder: Default placeholder text used wherever a
            value is unavailable.
    """

    loading_message: str = "Loading workbook..."
    error_title: str = "Something went wrong"
    empty_workbook_message: str = (
        "No engineering sections were discovered in the workbook."
    )
    refresh_button_label: str = "Refresh"
    retry_button_label: str = "Retry"
    no_data_placeholder: str = "\u2014"


# ----------------------------------------------------------------------
# Aggregate settings container
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """The complete, application-wide configuration container.

    A single :data:`SETTINGS` instance is the canonical source every
    module should read global configuration from, mirroring the
    existing single-source-of-truth pattern used by
    ``components.theme.THEME``.

    Attributes:
        identity: Application identity and branding metadata.
        layout: Default page-layout configuration values.
        cache: Default caching and refresh timing configuration.
        datetime: Default date, time, and timezone formatting
            configuration.
        chart: Default chart configuration values.
        strings: Reusable, generic UI string constants.
        supported_locales: The ordered tuple of locale identifiers the
            application is prepared to support for display formatting.
            Empty by default, indicating locale-invariant defaults only.
    """

    identity: AppIdentity = field(default_factory=AppIdentity)
    layout: LayoutSettings = field(default_factory=LayoutSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    datetime: DateTimeSettings = field(default_factory=DateTimeSettings)
    chart: ChartSettings = field(default_factory=ChartSettings)
    strings: UIStrings = field(default_factory=UIStrings)
    supported_locales: Tuple[str, ...] = field(default_factory=tuple)


SETTINGS = Settings()
"""The application's single, shared global configuration instance."""

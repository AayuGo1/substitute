"""
config/theme.py

Central visual design-system configuration for the Engineering
Monitoring Dashboard.

This module is the single source of truth for global, application-wide
visual tokens: color palette, typography, spacing, and the structured
styling defaults for cards, navbar, sidebar, and charts. It mirrors the
same dataclass-based, single-aggregate-object pattern used by
``config/settings.py``.

This module contains:
    - No Streamlit code (no ``st.*`` calls).
    - No CSS injection (no ``<style>`` strings, no ``st.markdown`` with
      ``unsafe_allow_html``). Injecting CSS from these tokens remains
      the responsibility of the individual UI components.
    - No business logic.
    - No Excel parsing or workbook-specific values.

Every module that needs a global visual token should import it from
here (or from the equivalent ``components.theme.THEME`` values it is
intended to stay aligned with) rather than redeclaring it inline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


# ----------------------------------------------------------------------
# Color palette
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ColorPalette:
    """The dashboard's complete color palette.

    Attributes:
        primary: The dominant brand/action color, used for primary
            buttons, active navigation items, and highlights.
        primary_light: A lighter tint of ``primary``, used for hover
            states and subtle accents.
        primary_dark: A darker shade of ``primary``, used for pressed
            states and gradients.
        secondary: The dashboard's accent color, used to differentiate
            secondary data series and accents.
        positive: Color used for favorable/upward trend indicators and
            healthy status.
        negative: Color used for unfavorable/downward trend indicators
            and critical alerts.
        neutral: Color used for flat/no-change trend indicators and
            neutral status.
        warning: Color used for cautionary states.
        info: Color used for neutral, informational highlights.
        background: The page's base background color.
        surface: The base surface color behind panels and cards.
        border: The default border color for cards, panels, and
            dividers.
        border_strong: A more visible border color, used for emphasis
            or focus states.
        text_primary: The default, high-emphasis text color.
        text_secondary: Medium-emphasis text, used for labels and
            secondary copy.
        text_muted: Low-emphasis text, used for captions and hints.
        text_on_primary: Text color used on top of ``primary``-colored
            surfaces (buttons, badges).
        chart_series: An ordered palette of colors for multi-series
            charts, chosen for readability against the background.
    """

    primary: str = "#4fd1c5"
    primary_light: str = "#7ee8dc"
    primary_dark: str = "#2fa89c"

    secondary: str = "#3B82F6"

    positive: str = "#3ddc84"
    negative: str = "#e35d5d"
    neutral: str = "#8aa0b4"
    warning: str = "#F59E0B"
    info: str = "#818CF8"

    background: str = "#0f1620"
    surface: str = "#16202c"

    border: str = "#2a3a4a"
    border_strong: str = "#3d5266"

    text_primary: str = "#e8edf2"
    text_secondary: str = "#8aa0b4"
    text_muted: str = "#5f7285"
    text_on_primary: str = "#0f1620"

    chart_series: Tuple[str, ...] = (
        "#4fd1c5",
        "#3B82F6",
        "#A78BFA",
        "#3ddc84",
        "#F59E0B",
        "#F472B6",
        "#60A5FA",
        "#FB923C",
    )


# ----------------------------------------------------------------------
# Typography
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Typography:
    """The dashboard's typographic scale.

    Attributes:
        font_family: The primary font stack.
        font_family_mono: A monospace font stack, used for numeric
            readouts where fixed-width digits improve scanability.
        title_size: Font size for panel/section titles.
        label_size: Font size for small, uppercase labels.
        value_size: Font size for standard readout values.
        display_size: Font size for the page's largest headline.
        body_size: Font size for standard body text.
        small_size: Font size for secondary/caption text.
        weight_regular: Standard font weight.
        weight_medium: Medium-emphasis font weight.
        weight_bold: High-emphasis font weight, used for headlines and
            KPI values.
    """

    font_family: str = (
        "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"
    )
    font_family_mono: str = "'JetBrains Mono', 'Consolas', monospace"

    title_size: str = "1rem"
    label_size: str = "0.72rem"
    value_size: str = "1.3rem"
    display_size: str = "1.85rem"
    body_size: str = "0.9rem"
    small_size: str = "0.78rem"

    weight_regular: int = 400
    weight_medium: int = 500
    weight_bold: int = 700


# ----------------------------------------------------------------------
# Spacing, radius, shadow
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Spacing:
    """The dashboard's spacing scale, in rem units.

    Attributes:
        xs: Extra-small spacing, for tight groupings (icon-to-label).
        sm: Small spacing, for internal padding on compact elements.
        md: Medium spacing, the default gap between related elements.
        lg: Large spacing, the default card padding.
        xl: Extra-large spacing, between major page sections.
    """

    xs: str = "0.35rem"
    sm: str = "0.65rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"


@dataclass(frozen=True)
class Radius:
    """The dashboard's corner-rounding scale.

    Attributes:
        sm: Subtle rounding, for small chips and badges.
        md: Standard rounding, for buttons, inputs, and cards.
        lg: The default rounding for larger panels and headers.
        pill: Fully rounded, for pill-shaped badges and tags.
    """

    sm: str = "6px"
    md: str = "12px"
    lg: str = "16px"
    pill: str = "999px"


@dataclass(frozen=True)
class Shadow:
    """The dashboard's elevation (box-shadow) scale.

    Attributes:
        sm: A subtle shadow for resting cards.
        md: A more pronounced shadow for hovered or featured cards.
    """

    sm: str = "0 1px 4px rgba(0, 0, 0, 0.2)"
    md: str = "0 10px 30px rgba(0, 0, 0, 0.45)"


# ----------------------------------------------------------------------
# Card styling
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class CardTheme:
    """Structured styling defaults specific to card-style components.

    Attributes:
        background_opacity_start: Opacity (0.0-1.0) of the surface
            color at the start of a card's background gradient.
        background_opacity_end: Opacity (0.0-1.0) of the surface color
            at the end of a card's background gradient.
        blur_strength: The backdrop-filter blur radius used for
            glassmorphic card surfaces.
        hover_lift_px: The vertical translation, in pixels, applied to
            a card on hover to create a "lift" effect.
        min_column_width_px: The minimum width, in pixels, a card grid
            column should shrink to before wrapping to a new row.
    """

    background_opacity_start: float = 0.85
    background_opacity_end: float = 0.6
    blur_strength: str = "10px"
    hover_lift_px: int = 3
    min_column_width_px: int = 220


# ----------------------------------------------------------------------
# Navbar styling
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class NavbarTheme:
    """Structured styling defaults specific to the navigation header.

    Attributes:
        height_px: The navbar's target height, in pixels.
        logo_size_px: The width and height, in pixels, of the logo or
            logo placeholder.
        blur_strength: The backdrop-filter blur radius used for the
            navbar's glassmorphic background.
        divider_width_px: The width, in pixels, of vertical dividers
            separating navbar metrics.
    """

    height_px: int = 64
    logo_size_px: int = 42
    blur_strength: str = "12px"
    divider_width_px: int = 1


# ----------------------------------------------------------------------
# Sidebar styling
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class SidebarTheme:
    """Structured styling defaults specific to the navigation sidebar.

    Attributes:
        expanded_width_px: The sidebar's target width, in pixels, when
            fully expanded.
        collapsed_width_px: The sidebar's target width, in pixels, when
            collapsed to icons only.
        logo_size_px: The width and height, in pixels, of the sidebar
            logo or logo placeholder.
        blur_strength: The backdrop-filter blur radius used for the
            sidebar's glassmorphic background.
    """

    expanded_width_px: int = 260
    collapsed_width_px: int = 72
    logo_size_px: int = 38
    blur_strength: str = "16px"


# ----------------------------------------------------------------------
# Chart theme
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ChartTheme:
    """Structured styling defaults specific to chart rendering.

    These are purely visual/presentational defaults; they carry no
    knowledge of any specific metric, section, or workbook content.

    Attributes:
        gridline_color: Color used for chart gridlines.
        axis_color: Color used for chart axis lines and tick labels.
        background_color: Background color used behind chart plot
            areas.
        legend_font_size: Font size used for chart legends.
        hover_background_color: Background color used for hover
            tooltips.
        colorway: The ordered sequence of colors used for multi-series
            charts, mirroring :attr:`ColorPalette.chart_series`.
    """

    gridline_color: str = "#2a3a4a"
    axis_color: str = "#8aa0b4"
    background_color: str = "rgba(0, 0, 0, 0)"
    legend_font_size: str = "0.75rem"
    hover_background_color: str = "#16202c"
    colorway: Tuple[str, ...] = (
        "#4fd1c5",
        "#3B82F6",
        "#A78BFA",
        "#3ddc84",
        "#F59E0B",
        "#F472B6",
        "#60A5FA",
        "#FB923C",
    )


# ----------------------------------------------------------------------
# Aggregate theme container
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ThemeConfig:
    """The complete, application-wide visual design-system container.

    A single :data:`THEME` instance is the canonical source every
    module should read global visual configuration from, following the
    same aggregate-object pattern as ``config.settings.SETTINGS``.

    Attributes:
        colors: The color palette.
        typography: The typographic scale.
        spacing: The spacing scale.
        radius: The corner-rounding scale.
        shadow: The elevation scale.
        card: Structured styling defaults for card-style components.
        navbar: Structured styling defaults for the navigation header.
        sidebar: Structured styling defaults for the navigation
            sidebar.
        chart: Structured styling defaults for chart rendering.
    """

    colors: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    spacing: Spacing = field(default_factory=Spacing)
    radius: Radius = field(default_factory=Radius)
    shadow: Shadow = field(default_factory=Shadow)
    card: CardTheme = field(default_factory=CardTheme)
    navbar: NavbarTheme = field(default_factory=NavbarTheme)
    sidebar: SidebarTheme = field(default_factory=SidebarTheme)
    chart: ChartTheme = field(default_factory=ChartTheme)


THEME = ThemeConfig()
"""The application's single, shared visual design-system instance."""

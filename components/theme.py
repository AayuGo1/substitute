"""Design system constants for the engineering monitoring dashboard.

This module defines the single source of truth for the dashboard's
visual identity: a dark, glassmorphic, industrial-SCADA-inspired theme
in the spirit of premium Power BI dashboards. Every color, spacing,
radius, shadow, and typography value used anywhere in the UI should be
imported from here rather than re-declared inline, so the look of the
dashboard can be changed in one place.

This module contains:

* No business logic.
* No KPI calculations.
* No Streamlit page code (no ``st.set_page_config``, no widgets).

It is pure, static configuration plus small pure functions for deriving
CSS from that configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ----------------------------------------------------------------------
# Color palette
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ColorPalette:
    """The dashboard's complete color palette.

    Attributes:
        primary: The dominant brand/action color (electric blue),
            used for primary buttons, active nav items, and highlights.
        primary_light: A lighter tint of ``primary``, used for hover
            states and subtle accents.
        primary_dark: A darker shade of ``primary``, used for pressed
            states and gradients.
        secondary: The dashboard's accent color (cyan/teal), used to
            differentiate secondary data series and accents.
        success: Color used for positive KPI movement, healthy status,
            and "good" states.
        warning: Color used for cautionary KPI movement and "attention
            needed" states.
        danger: Color used for negative KPI movement, critical alerts,
            and error states.
        info: Color used for neutral, informational highlights.
        background: The page's base background color.
        background_gradient_start: Start color for the page's subtle
            background gradient.
        background_gradient_end: End color for the page's subtle
            background gradient.
        surface: The base surface color behind glass panels, slightly
            lighter than ``background``.
        card_background: The translucent background color for glass
            cards, intended to be used with ``card_border`` and a
            backdrop blur.
        card_background_hover: The card background color on hover,
            slightly brighter than ``card_background``.
        sidebar_background: The sidebar's background color.
        header_background: The top header bar's background color.
        border: The default border color for cards and dividers.
        border_strong: A more visible border color, used for emphasis or
            focus states.
        text_primary: The default, high-emphasis text color.
        text_secondary: Medium-emphasis text, used for labels and
            secondary copy.
        text_muted: Low-emphasis text, used for captions and hints.
        text_on_primary: Text color used on top of ``primary``-colored
            surfaces (buttons, badges).
        chart_series: An ordered palette of colors for multi-series
            charts, chosen for readability against the dark background.
        shadow_color: The base color used to build box-shadows.
    """

    primary: str = "#3B82F6"
    primary_light: str = "#60A5FA"
    primary_dark: str = "#1D4ED8"

    secondary: str = "#22D3EE"

    success: str = "#22C55E"
    warning: str = "#F59E0B"
    danger: str = "#EF4444"
    info: str = "#818CF8"

    background: str = "#0B0F19"
    background_gradient_start: str = "#0B0F19"
    background_gradient_end: str = "#111827"
    surface: str = "#111827"

    card_background: str = "rgba(255, 255, 255, 0.04)"
    card_background_hover: str = "rgba(255, 255, 255, 0.07)"

    sidebar_background: str = "rgba(17, 24, 39, 0.85)"
    header_background: str = "rgba(11, 15, 25, 0.75)"

    border: str = "rgba(255, 255, 255, 0.08)"
    border_strong: str = "rgba(255, 255, 255, 0.16)"

    text_primary: str = "#F3F4F6"
    text_secondary: str = "#9CA3AF"
    text_muted: str = "#6B7280"
    text_on_primary: str = "#FFFFFF"

    chart_series: Tuple[str, ...] = (
        "#3B82F6",
        "#22D3EE",
        "#A78BFA",
        "#34D399",
        "#F59E0B",
        "#F472B6",
        "#60A5FA",
        "#FB923C",
    )

    shadow_color: str = "rgba(0, 0, 0, 0.45)"


# ----------------------------------------------------------------------
# Typography
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Typography:
    """The dashboard's typographic scale.

    Attributes:
        font_family: The primary font stack, favoring clean, technical
            sans-serifs appropriate for a SCADA-style instrument panel.
        font_family_mono: A monospace font stack, used for numeric
            readouts where fixed-width digits improve scanability.
        size_display: Font size for the page's largest headline (for
            example the workbook name in the header).
        size_h1: Font size for top-level section headings.
        size_h2: Font size for card/panel titles.
        size_h3: Font size for sub-panel titles.
        size_body: Font size for standard body text.
        size_small: Font size for secondary/caption text.
        size_kpi_value: Font size for a KPI card's headline number.
        size_kpi_label: Font size for a KPI card's label.
        weight_regular: Standard font weight.
        weight_medium: Medium-emphasis font weight.
        weight_bold: High-emphasis font weight, used for headlines and
            KPI values.
    """

    font_family: str = (
        "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"
    )
    font_family_mono: str = "'JetBrains Mono', 'Consolas', monospace"

    size_display: str = "1.85rem"
    size_h1: str = "1.5rem"
    size_h2: str = "1.15rem"
    size_h3: str = "1rem"
    size_body: str = "0.9rem"
    size_small: str = "0.78rem"
    size_kpi_value: str = "1.9rem"
    size_kpi_label: str = "0.78rem"

    weight_regular: int = 400
    weight_medium: int = 500
    weight_bold: int = 700


# ----------------------------------------------------------------------
# Spacing, radius, shadow, and layout scales
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Spacing:
    """The dashboard's spacing scale, in rem units.

    Attributes:
        xs: Extra-small spacing, for tight groupings (icon-to-label).
        sm: Small spacing, for internal card padding on compact cards.
        md: Medium spacing, the default gap between related elements.
        lg: Large spacing, the default card padding.
        xl: Extra-large spacing, between major page sections.
        xxl: Maximum spacing, around the page's outer edges.
    """

    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"
    xxl: str = "3rem"


@dataclass(frozen=True)
class Radius:
    """The dashboard's corner-rounding scale.

    Attributes:
        sm: Subtle rounding, for small chips and badges.
        md: Standard rounding, for buttons and inputs.
        lg: The default rounding for cards and panels.
        xl: Extra rounding, for hero/header containers.
        pill: Fully rounded, for pill-shaped badges and tags.
    """

    sm: str = "8px"
    md: str = "12px"
    lg: str = "16px"
    xl: str = "22px"
    pill: str = "999px"


@dataclass(frozen=True)
class Shadow:
    """The dashboard's elevation (box-shadow) scale.

    Attributes:
        soft: A subtle shadow for resting cards.
        medium: A more pronounced shadow for hovered or featured cards.
        glow_primary: A soft, colored glow used to highlight the active
            or most important element on a panel.
    """

    soft: str = "0 4px 24px rgba(0, 0, 0, 0.35)"
    medium: str = "0 8px 32px rgba(0, 0, 0, 0.45)"
    glow_primary: str = "0 0 24px rgba(59, 130, 246, 0.25)"


@dataclass(frozen=True)
class Breakpoints:
    """The dashboard's responsive breakpoints, in pixels.

    Attributes:
        tablet: Viewport width below which the layout switches to a
            tablet-friendly (fewer columns) arrangement.
        mobile: Viewport width below which the layout switches to a
            single-column, mobile-friendly arrangement.
        wide: Viewport width above which the layout may use its widest
            grid configuration (the dashboard's primary target).
    """

    tablet: int = 1024
    mobile: int = 640
    wide: int = 1440


@dataclass(frozen=True)
class Theme:
    """The complete design system: colors, type, spacing, and elevation.

    A single :data:`THEME` instance is the canonical source every UI
    helper and page should read from.

    Attributes:
        colors: The color palette.
        typography: The typographic scale.
        spacing: The spacing scale.
        radius: The corner-rounding scale.
        shadow: The elevation scale.
        breakpoints: The responsive breakpoints.
        blur_strength: The backdrop-filter blur radius used for
            glassmorphic surfaces (cards, sidebar, header).
        transition: The default CSS transition timing used for hover and
            focus effects.
    """

    colors: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    spacing: Spacing = field(default_factory=Spacing)
    radius: Radius = field(default_factory=Radius)
    shadow: Shadow = field(default_factory=Shadow)
    breakpoints: Breakpoints = field(default_factory=Breakpoints)
    blur_strength: str = "16px"
    transition: str = "all 0.2s ease-in-out"


THEME = Theme()
"""The dashboard's single, shared design system instance."""


# ----------------------------------------------------------------------
# Semantic helpers
# ----------------------------------------------------------------------

def get_status_color(status: str) -> str:
    """Maps a semantic status keyword to its theme color.

    Args:
        status: One of ``"success"``, ``"warning"``, ``"danger"``,
            ``"info"``, or any other value (which falls back to
            ``text_secondary``).

    Returns:
        The hex or ``rgba`` color string for the given status.
    """
    mapping: Dict[str, str] = {
        "success": THEME.colors.success,
        "warning": THEME.colors.warning,
        "danger": THEME.colors.danger,
        "info": THEME.colors.info,
    }
    return mapping.get(status.lower(), THEME.colors.text_secondary)


def get_trend_color(trend: str) -> str:
    """Maps a trend direction keyword to its semantic theme color.

    Args:
        trend: One of ``"increasing"``, ``"decreasing"``, ``"stable"``,
            or ``"unknown"`` (matching
            :class:`services.kpi_service.TrendDirection`).

    Returns:
        A color string: ``success`` for increasing, ``danger`` for
        decreasing, ``text_secondary`` for stable or unrecognized
        values.
    """
    mapping: Dict[str, str] = {
        "increasing": THEME.colors.success,
        "decreasing": THEME.colors.danger,
        "stable": THEME.colors.text_secondary,
    }
    return mapping.get(trend.lower(), THEME.colors.text_muted)


def get_chart_color(index: int) -> str:
    """Returns a chart series color for the given series index.

    Cycles through :attr:`ColorPalette.chart_series` so any number of
    series gets a deterministic, distinct-looking color.

    Args:
        index: The zero-based index of the series being colored.

    Returns:
        A color string from the chart palette.
    """
    palette = THEME.colors.chart_series
    return palette[index % len(palette)]


def get_chart_colorway() -> List[str]:
    """Returns the full chart color sequence, for Plotly's ``colorway``.

    Returns:
        The chart series palette as a plain list, suitable for passing
        directly to ``fig.update_layout(colorway=...)``.
    """
    return list(THEME.colors.chart_series)


# ----------------------------------------------------------------------
# Global CSS
# ----------------------------------------------------------------------

def get_global_css() -> str:
    """Builds the dashboard's global CSS block.

    Intended to be injected once per page (for example via
    ``st.markdown(get_global_css(), unsafe_allow_html=True)`` at the top
    of a Streamlit page). Defines the glassmorphic card, header, and
    sidebar treatments, base typography, and a wide, full-width page
    layout, all driven by :data:`THEME`.

    Returns:
        A ``<style>...</style>`` string ready to be injected into the
        page.
    """
    c = THEME.colors
    t = THEME.typography
    s = THEME.spacing
    r = THEME.radius
    sh = THEME.shadow
    b = THEME.breakpoints

    return f"""
<style>
:root {{
    --color-primary: {c.primary};
    --color-primary-light: {c.primary_light};
    --color-primary-dark: {c.primary_dark};
    --color-secondary: {c.secondary};
    --color-success: {c.success};
    --color-warning: {c.warning};
    --color-danger: {c.danger};
    --color-info: {c.info};
    --color-background: {c.background};
    --color-surface: {c.surface};
    --color-card-bg: {c.card_background};
    --color-card-bg-hover: {c.card_background_hover};
    --color-sidebar-bg: {c.sidebar_background};
    --color-header-bg: {c.header_background};
    --color-border: {c.border};
    --color-border-strong: {c.border_strong};
    --color-text-primary: {c.text_primary};
    --color-text-secondary: {c.text_secondary};
    --color-text-muted: {c.text_muted};
    --font-family: {t.font_family};
    --font-family-mono: {t.font_family_mono};
    --radius-sm: {r.sm};
    --radius-md: {r.md};
    --radius-lg: {r.lg};
    --radius-xl: {r.xl};
    --radius-pill: {r.pill};
    --shadow-soft: {sh.soft};
    --shadow-medium: {sh.medium};
    --shadow-glow: {sh.glow_primary};
    --blur-strength: {THEME.blur_strength};
    --transition-default: {THEME.transition};
    --space-xs: {s.xs};
    --space-sm: {s.sm};
    --space-md: {s.md};
    --space-lg: {s.lg};
    --space-xl: {s.xl};
    --space-xxl: {s.xxl};
}}

html, body, [class*="css"] {{
    font-family: var(--font-family);
    color: var(--color-text-primary);
}}

.stApp {{
    background: linear-gradient(
        160deg,
        {c.background_gradient_start} 0%,
        {c.background_gradient_end} 100%
    );
    background-attachment: fixed;
}}

.block-container {{
    max-width: 100% !important;
    padding-left: var(--space-xl) !important;
    padding-right: var(--space-xl) !important;
    padding-top: var(--space-lg) !important;
}}

section[data-testid="stSidebar"] {{
    background: var(--color-sidebar-bg);
    backdrop-filter: blur(var(--blur-strength));
    -webkit-backdrop-filter: blur(var(--blur-strength));
    border-right: 1px solid var(--color-border);
}}

.emd-header {{
    background: var(--color-header-bg);
    backdrop-filter: blur(var(--blur-strength));
    -webkit-backdrop-filter: blur(var(--blur-strength));
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-soft);
    padding: var(--space-lg) var(--space-xl);
    margin-bottom: var(--space-lg);
}}

.emd-card {{
    background: var(--color-card-bg);
    backdrop-filter: blur(var(--blur-strength));
    -webkit-backdrop-filter: blur(var(--blur-strength));
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-soft);
    padding: var(--space-lg);
    transition: var(--transition-default);
    height: 100%;
}}

.emd-card:hover {{
    background: var(--color-card-bg-hover);
    border-color: var(--color-border-strong);
    box-shadow: var(--shadow-medium);
}}

.emd-card--compact {{
    padding: var(--space-md);
}}

.emd-section-container {{
    margin-bottom: var(--space-xl);
}}

.emd-kpi-label {{
    font-size: {t.size_kpi_label};
    font-weight: {t.weight_medium};
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: var(--space-xs);
}}

.emd-kpi-value {{
    font-family: var(--font-family-mono);
    font-size: {t.size_kpi_value};
    font-weight: {t.weight_bold};
    color: var(--color-text-primary);
    line-height: 1.2;
}}

.emd-kpi-unit {{
    font-size: {t.size_small};
    color: var(--color-text-muted);
    margin-left: var(--space-xs);
}}

.emd-badge {{
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    padding: 2px 10px;
    border-radius: var(--radius-pill);
    font-size: {t.size_small};
    font-weight: {t.weight_medium};
    border: 1px solid var(--color-border);
}}

.emd-title {{
    font-size: {t.size_display};
    font-weight: {t.weight_bold};
    color: var(--color-text-primary);
    margin: 0;
}}

.emd-subtitle {{
    font-size: {t.size_body};
    color: var(--color-text-secondary);
    margin: 0;
}}

.emd-section-heading {{
    font-size: {t.size_h1};
    font-weight: {t.weight_bold};
    color: var(--color-text-primary);
    margin-bottom: var(--space-md);
}}

.emd-panel-heading {{
    font-size: {t.size_h2};
    font-weight: {t.weight_medium};
    color: var(--color-text-primary);
    margin-bottom: var(--space-sm);
}}

.emd-divider {{
    border: none;
    border-top: 1px solid var(--color-border);
    margin: var(--space-lg) 0;
}}

@media (max-width: {b.tablet}px) {{
    .block-container {{
        padding-left: var(--space-md) !important;
        padding-right: var(--space-md) !important;
    }}
}}
</style>
"""

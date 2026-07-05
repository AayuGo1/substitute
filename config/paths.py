"""
config/paths.py

Central path management for the Engineering Monitoring Dashboard.

This module is the single source of truth for resolving the
application's file-system layout: the project root and the standard
subdirectories derived from it (assets, CSS, icons, fonts, temporary
files). It mirrors the same dataclass-based, single-source-of-truth
pattern used by ``config/settings.py``, ``config/theme.py``, and
``config/github.py``.

This module contains:
    - No Streamlit code.
    - No business logic.
    - No GitHub logic.
    - No Excel loading or parsing.
    - No caching.

The project root is determined dynamically from this file's own
location on disk, so no absolute path is ever hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# This file lives at ``<project_root>/config/paths.py``, so the
# project root is exactly one directory above this file's parent.
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent


@dataclass(frozen=True)
class ProjectPaths:
    """Immutable description of the application's standard directories.

    Every path is derived from :data:`_PROJECT_ROOT`, which is itself
    computed from this module's own location on disk, so the same
    configuration resolves correctly regardless of the current working
    directory the application happens to be launched from.

    Attributes:
        project_root: The absolute path to the project's root
            directory.
        assets_directory: The absolute path to the project's static
            assets directory.
        css_directory: The absolute path to the project's CSS assets
            directory.
        icons_directory: The absolute path to the project's icon
            assets directory.
        fonts_directory: The absolute path to the project's font
            assets directory.
        temp_directory: The absolute path to the project's temporary
            working-file directory.
    """

    project_root: Path = field(default_factory=lambda: _PROJECT_ROOT)
    assets_directory: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "assets"
    )
    css_directory: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "assets" / "css"
    )
    icons_directory: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "assets" / "icons"
    )
    fonts_directory: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "assets" / "fonts"
    )
    temp_directory: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "temp"
    )


def get_project_root() -> Path:
    """Returns the absolute path to the project's root directory.

    Returns:
        The project root directory, resolved from this module's own
        location on disk.
    """
    return PATHS.project_root


def get_assets_path() -> Path:
    """Returns the absolute path to the project's static assets
    directory.

    Returns:
        The assets directory path.
    """
    return PATHS.assets_directory


def get_css_path() -> Path:
    """Returns the absolute path to the project's CSS assets directory.

    Returns:
        The CSS assets directory path.
    """
    return PATHS.css_directory


def get_icons_path() -> Path:
    """Returns the absolute path to the project's icon assets
    directory.

    Returns:
        The icons directory path.
    """
    return PATHS.icons_directory


def get_fonts_path() -> Path:
    """Returns the absolute path to the project's font assets
    directory.

    Returns:
        The fonts directory path.
    """
    return PATHS.fonts_directory


def get_temp_path() -> Path:
    """Returns the absolute path to the project's temporary working-file
    directory.

    Returns:
        The temporary directory path.
    """
    return PATHS.temp_directory


def resolve_relative_path(relative_path: str) -> Path:
    """Resolves a path relative to the project root into an absolute
    path.

    Args:
        relative_path: A path, expressed relative to the project root
            (for example ``"assets/icons/logo.png"``), using either
            forward slashes or the current platform's separator.

    Returns:
        The absolute :class:`~pathlib.Path` corresponding to
        ``relative_path`` under the project root.
    """
    return (PATHS.project_root / relative_path).resolve()


PATHS = ProjectPaths()
"""The application's single, shared project-paths instance."""

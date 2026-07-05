"""
config

Public API for the Engineering Monitoring Dashboard's configuration
package.

This package aggregates the individually maintained configuration
modules — application settings, visual theme, GitHub repository
location, and file-system paths — into a single, convenient import
surface. This module performs no configuration logic of its own; it
only re-exports the public objects already defined in
``config.settings``, ``config.theme``, ``config.github``, and
``config.paths``.
"""

from __future__ import annotations

from config.github import GitHubConfig, get_github_config
from config.paths import (
    PATHS,
    ProjectPaths,
    get_assets_path,
    get_css_path,
    get_fonts_path,
    get_icons_path,
    get_project_root,
    get_temp_path,
    resolve_relative_path,
)
from config.settings import SETTINGS
from config.theme import THEME

__all__ = [
    "SETTINGS",
    "THEME",
    "PATHS",
    "GitHubConfig",
    "get_github_config",
    "ProjectPaths",
    "get_project_root",
    "get_assets_path",
    "get_css_path",
    "get_icons_path",
    "get_fonts_path",
    "get_temp_path",
    "resolve_relative_path",
]

"""
config/github.py

Central GitHub repository configuration for the Engineering Monitoring
Dashboard.

This module is the single source of truth for identifying where the
dashboard's workbook lives on GitHub: repository owner, repository
name, branch, workbook filename, and the base URL used to resolve raw
file content. It mirrors the same dataclass-based, single-source-of-
truth pattern used by ``config/settings.py`` and ``config/theme.py``.

This module contains:
    - No Streamlit code.
    - No HTTP client usage (no ``requests``, no downloading).
    - No Excel loading or parsing.
    - No business logic beyond resolving and validating configuration
      values.
    - No hardcoded workbook structure (no sheet names, section names,
      department names, or metric names).

Every module that needs to know where the workbook is hosted should
call :func:`get_github_config` rather than hardcoding repository
details inline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubConfig:
    """Immutable configuration describing the workbook's GitHub source.

    Attributes:
        repository_owner: The GitHub account or organization that owns
            the repository hosting the workbook.
        repository_name: The name of the repository hosting the
            workbook.
        branch: The branch to read the workbook from.
        workbook_filename: The path to the workbook file within the
            repository, relative to the repository root.
        raw_base_url: The base host used to resolve raw file content
            (for example ``"raw.githubusercontent.com"``), without a
            scheme or trailing slash.
        request_timeout_seconds: How long, in seconds, a caller should
            wait for a download of this workbook before giving up. This
            module performs no downloading itself; it only carries the
            configured timeout value for the loader to use.
    """
       repository_owner: str = "aayugo1"
       repository_name: str = "substitute"
       branch: str = "main"
       workbook_filename: str = "Daily energy Monitoring.xlsx"
       raw_base_url: str = "raw.githubusercontent.com"
       request_timeout_seconds: float = 15.0

    def build_raw_file_url(self) -> str:
        """Builds the raw file URL for this configuration's workbook.

        Returns:
            The fully qualified ``https://`` URL from which the
            configured workbook's raw content can be retrieved.
        """
        return (
            f"https://{self.raw_base_url}/"
            f"{self.repository_owner}/"
            f"{self.repository_name}/"
            f"{self.branch}/"
            f"{self.workbook_filename}"
        )

    def validate(self) -> None:
        """Validates that this configuration is complete and usable.

        Checks that every field required to resolve a raw file URL is
        present and non-empty, and that ``request_timeout_seconds`` is
        a positive number. This method performs no network access; it
        only inspects the configuration's own field values.

        Raises:
            ValueError: If any required field is missing, empty, or
                otherwise invalid.
        """
        required_string_fields = {
            "repository_owner": self.repository_owner,
            "repository_name": self.repository_name,
            "branch": self.branch,
            "workbook_filename": self.workbook_filename,
            "raw_base_url": self.raw_base_url,
        }
        for field_name, value in required_string_fields.items():
            if not value or not value.strip():
                raise ValueError(
                    f"GitHubConfig.{field_name} must be a non-empty string."
                )

        if self.request_timeout_seconds <= 0:
            raise ValueError(
                "GitHubConfig.request_timeout_seconds must be a positive "
                f"number; got {self.request_timeout_seconds!r}."
            )


def _resolve_field(env_var_name: str, default_value: str) -> str:
    """Resolves a single configuration field, optionally from the
    environment.

    Environment-variable overrides are entirely optional: if the named
    variable is unset or empty, ``default_value`` is used unchanged.
    This keeps the dataclass's own defaults authoritative while still
    allowing deployment-specific overrides where desired.

    Args:
        env_var_name: The name of the environment variable that may
            override the default value.
        default_value: The value to use when the environment variable
            is unset or empty.

    Returns:
        The resolved configuration value.
    """
    override = os.environ.get(env_var_name)
    if override is not None and override.strip():
        return override
    return default_value


def get_github_config() -> GitHubConfig:
    """Returns the active GitHub configuration for the dashboard.

    Field values default to :class:`GitHubConfig`'s own declared
    defaults, and may each be optionally overridden by a corresponding
    environment variable, so that a deployment can point the dashboard
    at a different repository, branch, or workbook filename without
    any code change.

    Recognized optional environment variables:
        ``EM_GITHUB_REPOSITORY_OWNER``
        ``EM_GITHUB_REPOSITORY_NAME``
        ``EM_GITHUB_BRANCH``
        ``EM_GITHUB_WORKBOOK_FILENAME``
        ``EM_GITHUB_RAW_BASE_URL``
        ``EM_GITHUB_REQUEST_TIMEOUT_SECONDS``

    Returns:
        A validated :class:`GitHubConfig` instance.

    Raises:
        ValueError: If the resolved configuration fails validation.
    """
    defaults = GitHubConfig()

    timeout_override = os.environ.get("EM_GITHUB_REQUEST_TIMEOUT_SECONDS")
    if timeout_override is not None and timeout_override.strip():
        try:
            request_timeout_seconds = float(timeout_override)
        except ValueError:
            request_timeout_seconds = defaults.request_timeout_seconds
    else:
        request_timeout_seconds = defaults.request_timeout_seconds

    config = GitHubConfig(
        repository_owner=_resolve_field(
            "EM_GITHUB_REPOSITORY_OWNER", defaults.repository_owner
        ),
        repository_name=_resolve_field(
            "EM_GITHUB_REPOSITORY_NAME", defaults.repository_name
        ),
        branch=_resolve_field("EM_GITHUB_BRANCH", defaults.branch),
        workbook_filename=_resolve_field(
            "EM_GITHUB_WORKBOOK_FILENAME", defaults.workbook_filename
        ),
        raw_base_url=_resolve_field(
            "EM_GITHUB_RAW_BASE_URL", defaults.raw_base_url
        ),
        request_timeout_seconds=request_timeout_seconds,
    )
    config.validate()
    return config

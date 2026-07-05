"""
data/github_loader.py

Download-only loader for the Engineering Monitoring Dashboard's
workbook, sourced from GitHub.

This module is responsible for exactly one thing: retrieving the
raw bytes of the configured workbook file from GitHub and returning
them as an in-memory :class:`io.BytesIO` stream. It performs no
parsing, no validation of workbook contents, and no caching.

This module contains:
    - No Excel parsing (no ``openpyxl``, no ``pandas``).
    - No workbook structure validation.
    - No caching.
    - No Streamlit code.
    - No business logic beyond resolving the configured URL and
      performing the HTTP download.

Configuration is sourced entirely from ``config.github``, via
``get_github_config()``; this module never hardcodes a repository
owner, repository name, branch, or workbook filename.
"""

from __future__ import annotations

from io import BytesIO

import requests

from config.github import GitHubConfig, get_github_config


class GitHubDownloadError(Exception):
    """Raised when the configured workbook cannot be downloaded from
    GitHub.

    This is a single, normalized exception type covering configuration
    resolution failures, network errors, non-success HTTP status
    codes, and empty response bodies, so callers only need to handle
    one error class regardless of which stage failed.
    """


def _resolve_and_validate_config() -> GitHubConfig:
    """Resolves the active GitHub configuration and validates it.

    Returns:
        A validated :class:`~config.github.GitHubConfig` instance.

    Raises:
        GitHubDownloadError: If the configuration cannot be resolved or
            fails validation.
    """
    try:
        config = get_github_config()
    except Exception as exc:  # noqa: BLE001 - normalized into one error type
        raise GitHubDownloadError(
            f"Failed to resolve GitHub configuration: {exc}"
        ) from exc

    try:
        config.validate()
    except ValueError as exc:
        raise GitHubDownloadError(
            f"GitHub configuration is invalid: {exc}"
        ) from exc

    return config


def _download_bytes(url: str, timeout_seconds: float) -> bytes:
    """Downloads raw content from a URL and validates the response.

    Args:
        url: The fully qualified URL to download from.
        timeout_seconds: How long to wait for the request before
            giving up.

    Returns:
        The downloaded response body as raw bytes.

    Raises:
        GitHubDownloadError: If the request times out, fails for any
            network or HTTP reason, or returns an empty body.
    """
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.exceptions.Timeout as exc:
        raise GitHubDownloadError(
            f"Timed out after {timeout_seconds}s downloading workbook "
            f"from '{url}'."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise GitHubDownloadError(
            f"Failed to download workbook from '{url}': {exc}"
        ) from exc

    if response.status_code != requests.codes.ok:
        raise GitHubDownloadError(
            f"GitHub returned HTTP {response.status_code} when "
            f"downloading workbook from '{url}'."
        )

    if not response.content:
        raise GitHubDownloadError(
            f"Downloaded workbook from '{url}' is empty."
        )

    return response.content


def load_workbook_from_github() -> BytesIO:
    """Downloads the configured workbook from GitHub as an in-memory
    stream.

    This is the only function other modules should call to obtain the
    workbook's raw bytes. It resolves the active configuration via
    ``config.github.get_github_config()``, builds the raw file URL via
    ``GitHubConfig.build_raw_file_url()``, downloads the file, and
    validates the HTTP response. No Excel parsing, workbook structure
    validation, or caching is performed here.

    Returns:
        An in-memory :class:`io.BytesIO` stream positioned at the start
        of the downloaded workbook's raw bytes.

    Raises:
        GitHubDownloadError: If the configuration cannot be resolved or
            validated, the download fails for any network or HTTP
            reason, or the downloaded content is empty.
    """
    config = _resolve_and_validate_config()
    url = config.build_raw_file_url()
    content = _download_bytes(url, config.request_timeout_seconds)
    return BytesIO(content)

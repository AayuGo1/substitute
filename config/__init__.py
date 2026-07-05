"""Configuration package."""

from .github import GitHubConfig, get_github_config

__all__ = [
    "GitHubConfig",
    "get_github_config",
]

"""Configuration management for repo-cli.

Handles loading, saving, and validating the YAML configuration file.
Parses GitHub URLs to extract owner/repo slugs.
"""

from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".repo-cli" / "config.yaml"


def load_config() -> dict[str, Any]:
    """Load configuration from YAML file."""
    # TODO: Implement YAML loading
    raise NotImplementedError("load_config not yet implemented")


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to YAML file."""
    # TODO: Implement YAML saving
    raise NotImplementedError("save_config not yet implemented")


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner/repo slug.

    Args:
        url: GitHub URL in SSH or HTTPS format

    Returns:
        Tuple of (full_url, owner_repo_slug)

    Examples:
        git@github.com:owner/repo.git -> owner/repo
        https://github.com/owner/repo.git -> owner/repo
    """
    # TODO: Implement URL parsing
    raise NotImplementedError("parse_github_url not yet implemented")

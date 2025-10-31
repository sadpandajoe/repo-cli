"""Configuration management for repo-cli.

Handles loading, saving, and validating the YAML configuration file.
Parses GitHub URLs to extract owner/repo slugs.
"""

import re
import yaml
from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".repo-cli" / "config.yaml"


def load_config() -> dict[str, Any]:
    """Load configuration from YAML file.

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to YAML file.

    Creates config directory if it doesn't exist.

    Args:
        config: Configuration dictionary to save
    """
    config_path = get_config_path()

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write YAML
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def parse_github_url(url: str) -> str:
    """Parse GitHub URL to extract owner/repo slug.

    Args:
        url: GitHub URL in SSH or HTTPS format

    Returns:
        owner/repo slug

    Examples:
        git@github.com:owner/repo.git -> owner/repo
        https://github.com/owner/repo.git -> owner/repo

    Raises:
        ValueError: If URL is not a valid GitHub URL
    """
    # SSH format: git@github.com:owner/repo.git
    ssh_pattern = r"git@github\.com:([^/]+/[^/]+?)(\.git)?$"
    ssh_match = re.match(ssh_pattern, url)
    if ssh_match:
        return ssh_match.group(1)

    # HTTPS format: https://github.com/owner/repo.git
    https_pattern = r"https://github\.com/([^/]+/[^/]+?)(\.git)?$"
    https_match = re.match(https_pattern, url)
    if https_match:
        return https_match.group(1)

    # If no pattern matched, raise error
    raise ValueError(f"Invalid GitHub URL: {url}")

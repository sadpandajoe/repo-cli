"""Configuration management for repo-cli.

Handles loading, saving, and validating the YAML configuration file.
Parses GitHub URLs to extract owner/repo slugs.
"""

import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".repo-cli" / "config.yaml"


def migrate_config(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Migrate old config format to current format.

    Detects and converts worktree keys from old format (repo-branch) to
    new format (repo::branch). This migration is necessary because the
    old format had collision issues (e.g., 'api-core-feature' could be
    'api' + 'core-feature' OR 'api-core' + 'feature').

    Args:
        config: Configuration dictionary to migrate

    Returns:
        Tuple of (migrated config, changed) where changed indicates if migration occurred
    """
    worktrees = config.get("worktrees", {})
    if not worktrees:
        return config, False

    new_worktrees = {}
    migrated_count = 0

    for key, value in worktrees.items():
        # Skip if already in new format (contains ::)
        if "::" in key:
            new_worktrees[key] = value
            continue

        # Old format: {repo}-{branch}
        # Use metadata to reconstruct the correct key
        if isinstance(value, dict) and "repo" in value and "branch" in value:
            repo = value["repo"]
            branch = value["branch"]
            new_key = f"{repo}::{branch}"
            new_worktrees[new_key] = value
            migrated_count += 1
        else:
            # Malformed entry, keep as-is
            new_worktrees[key] = value

    if migrated_count > 0:
        config["worktrees"] = new_worktrees
        # Add version field to track migrations
        config.setdefault("version", "0.1.0")
        return config, True

    return config, False


def migrate_worktree_paths(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Migrate worktree directory paths from __ encoding to percent-encoding.

    Old format used __ to replace / in branch names (feature/foo -> feature__foo).
    New format uses percent-encoding (feature/foo -> feature%2Ffoo).
    Uses git worktree move to update both the filesystem and Git's internal metadata.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (config, changed) where changed indicates if migrations occurred
    """
    base_dir_str = config.get("base_dir")
    if not base_dir_str:
        return config, False

    base_dir = Path(base_dir_str).expanduser().resolve()
    worktrees = config.get("worktrees", {})
    changed = False

    for _key, value in worktrees.items():
        if not isinstance(value, dict) or "repo" not in value or "branch" not in value:
            continue

        repo = value["repo"]
        branch = value["branch"]

        # Calculate old path (__ replacement) and new path (percent-encoding)
        old_safe_branch = branch.replace("/", "__")
        new_safe_branch = quote(branch, safe="")

        # Skip if no encoding needed (no special characters)
        if old_safe_branch == new_safe_branch:
            continue

        old_path = base_dir / f"{repo}-{old_safe_branch}"
        new_path = base_dir / f"{repo}-{new_safe_branch}"
        bare_repo_path = base_dir / f"{repo}.git"

        # Migrate: use git worktree move if old exists and new doesn't
        if old_path.exists() and not new_path.exists() and bare_repo_path.exists():
            # Use git worktree move to update both filesystem and Git metadata
            # If it fails (permissions, locked worktree, etc.), skip silently
            # The worktree will need to be manually migrated or recreated
            try:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(bare_repo_path),
                        "worktree",
                        "move",
                        str(old_path),
                        str(new_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                changed = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                # FileNotFoundError: git command not found
                # CalledProcessError: git worktree move failed
                pass

    return config, changed


def load_config() -> dict[str, Any]:
    """Load configuration from YAML file.

    Automatically migrates old config formats to current format.

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is empty or invalid
    """
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

        # Guard against empty/blank YAML files
        if data is None:
            raise ValueError(f"Config file is empty or invalid: {config_path}")

        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a YAML dictionary: {config_path}")

        # Migrate config if needed
        data, config_changed = migrate_config(data)

        # Migrate worktree paths from __ to percent-encoding
        data, paths_changed = migrate_worktree_paths(data)

        # Only save if migrations actually changed something
        if config_changed or paths_changed:
            save_config(data)

        return data


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to YAML file with atomic write.

    Uses atomic write (temp file + os.replace) to prevent corruption.
    Creates config directory if it doesn't exist.

    Args:
        config: Configuration dictionary to save
    """
    import os
    import tempfile

    config_path = get_config_path()

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (ensures same filesystem for atomic replace)
    fd, temp_path = tempfile.mkstemp(
        dir=config_path.parent, prefix=".config.", suffix=".yaml.tmp", text=True
    )

    try:
        # Write YAML to temp file
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic replace (POSIX guarantees atomicity)
        os.replace(temp_path, config_path)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise


def parse_github_url(url: str, require_github: bool = False) -> str | None:
    """Extract owner/repo from git URL for GitHub/GHE.

    Supports GitHub.com, GitHub Enterprise, and graceful degradation for non-GitHub URLs.

    Args:
        url: Git URL in SSH or HTTPS format
        require_github: If True, raises ValueError for non-GitHub URLs.
                       If False, returns None for non-GitHub URLs (graceful degradation).

    Returns:
        owner/repo slug if GitHub/GHE URL, None if non-GitHub (when require_github=False)

    Examples:
        git@github.com:user/repo.git -> "user/repo" (GitHub)
        git@github.enterprise.com:user/repo.git -> "user/repo" (GHE)
        git@gitlab.com:user/repo.git -> None (GitLab, graceful)
        https://github.com/user/repo.git -> "user/repo" (GitHub)

    Raises:
        ValueError: Only if require_github=True and URL is not GitHub
                   OR if URL format is invalid
    """
    # SSH format: git@{host}:{owner}/{repo}.git
    ssh_pattern = r"git@([^:]+):([^/]+/[^/]+?)(\.git)?$"
    ssh_match = re.match(ssh_pattern, url)
    if ssh_match:
        host, owner_repo = ssh_match.group(1), ssh_match.group(2)
        # Accept any GitHub hostname (github.com, github.enterprise.com, etc.)
        if "github" in host.lower():
            return owner_repo
        elif not require_github:
            return None  # Non-GitHub, but that's OK (PR features will be disabled)
        else:
            raise ValueError(f"URL is not a GitHub URL: {url}")

    # HTTPS format: https://{host}/{owner}/{repo}.git
    https_pattern = r"https://([^/]+)/([^/]+/[^/]+?)(\.git)?$"
    https_match = re.match(https_pattern, url)
    if https_match:
        host, owner_repo = https_match.group(1), https_match.group(2)
        if "github" in host.lower():
            return owner_repo
        elif not require_github:
            return None
        else:
            raise ValueError(f"URL is not a GitHub URL: {url}")

    # No pattern matched - invalid URL format
    if require_github:
        raise ValueError(f"Invalid GitHub URL format: {url}")
    raise ValueError(f"Invalid git URL format: {url}")

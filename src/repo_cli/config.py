"""Configuration management for repo-cli.

Handles loading, saving, and validating the YAML configuration file.
Parses GitHub URLs to extract owner/repo slugs.
"""

import datetime
import re
import shutil
import subprocess
import sys
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


def migrate_to_nested_layout(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Migrate from flat directory layout to nested layout.

    Old layout: base_dir/repo.git, base_dir/repo-branch
    New layout: base_dir/repo/.bare, base_dir/repo/branch

    Algorithm per repo:
    1. Create repo parent dir
    2. Move worktrees via 'git worktree move' (bare repo still at old location, links valid)
    3. Move bare repo via shutil.move
    4. Fix worktree .git files to point to new bare repo location

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (config, changed) where changed indicates if migration occurred
    """
    base_dir_str = config.get("base_dir")
    if not base_dir_str:
        return config, False

    # Skip if already at version 0.2.0+
    version = config.get("version", "")
    if version >= "0.2.0":
        return config, False

    base_dir = Path(base_dir_str).expanduser().resolve()
    if not base_dir.exists():
        return config, False

    worktrees = config.get("worktrees", {})
    repos = config.get("repos", {})

    # Collect unique repo names from both repos and worktrees
    repo_names: set[str] = set(repos.keys())
    for value in worktrees.values():
        if isinstance(value, dict) and "repo" in value:
            repo_names.add(value["repo"])

    # Check if any repo actually needs migration (old bare repo exists)
    repos_to_migrate = []
    for repo_name in repo_names:
        old_bare = base_dir / f"{repo_name}.git"
        if old_bare.exists():
            repos_to_migrate.append(repo_name)

    if not repos_to_migrate:
        # No old-layout repos found; just stamp version
        config["version"] = "0.2.0"
        return config, True

    # Back up config before migration
    config_path = get_config_path()
    if config_path.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_suffix(f".yaml.backup.{timestamp}")
        shutil.copy2(config_path, backup_path)

    # Migrate each repo
    for repo_name in repos_to_migrate:
        old_bare = base_dir / f"{repo_name}.git"
        new_repo_dir = base_dir / repo_name
        new_bare = new_repo_dir / ".bare"

        try:
            # Collision check: if repo dir exists and is NOT ours, skip
            if new_repo_dir.exists() and not new_bare.exists():
                print(
                    f"⚠ Warning: '{new_repo_dir}' already exists and is not a repo-cli directory. "
                    f"Skipping migration for '{repo_name}'.",
                    file=sys.stderr,
                )
                continue

            # Step 1: Create repo parent dir
            new_repo_dir.mkdir(parents=True, exist_ok=True)

            # Step 2: Move worktrees FIRST (bare repo still at old location, git links valid)
            for _key, wt_value in worktrees.items():
                if not isinstance(wt_value, dict) or wt_value.get("repo") != repo_name:
                    continue

                branch = wt_value.get("branch")
                if not branch:
                    continue

                safe_branch = quote(branch, safe="")
                old_wt = base_dir / f"{repo_name}-{safe_branch}"
                new_wt = new_repo_dir / safe_branch

                if old_wt.exists() and not new_wt.exists():
                    try:
                        subprocess.run(
                            [
                                "git",
                                "-C",
                                str(old_bare),
                                "worktree",
                                "move",
                                str(old_wt),
                                str(new_wt),
                            ],
                            check=True,
                            capture_output=True,
                            text=True,
                        )

                        # CWD warning
                        try:
                            cwd = Path.cwd()
                            if cwd == old_wt or old_wt in cwd.parents:
                                print(
                                    f"⚠ Your shell is in a moved worktree. Run:  cd {new_wt}",
                                    file=sys.stderr,
                                )
                        except OSError:
                            pass

                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pass

            # Step 3: Move bare repo
            if not new_bare.exists():
                shutil.move(str(old_bare), str(new_bare))

            # Step 4: Fix worktree .git files to point to new bare repo location
            # Runs unconditionally when new_bare exists — handles both fresh moves
            # and recovery from a previous partial migration.
            # Each worktree has a .git file containing: gitdir: /path/to/bare/worktrees/<name>
            worktrees_meta_dir = new_bare / "worktrees"
            if worktrees_meta_dir.exists():
                old_bare_str = str(old_bare)
                new_bare_str = str(new_bare)
                for wt_meta in worktrees_meta_dir.iterdir():
                    if not wt_meta.is_dir():
                        continue
                    gitdir_file = wt_meta / "gitdir"
                    if gitdir_file.exists():
                        wt_path_str = gitdir_file.read_text().strip()
                        wt_path = Path(wt_path_str)
                        git_file = wt_path / ".git"
                        if git_file.exists():
                            content = git_file.read_text()
                            if old_bare_str in content:
                                git_file.write_text(content.replace(old_bare_str, new_bare_str))

        except Exception:
            # Per-repo error handling: one repo failing doesn't block others
            print(
                f"⚠ Warning: Migration failed for '{repo_name}'. It will be retried on next run.",
                file=sys.stderr,
            )
            continue

    config["version"] = "0.2.0"
    return config, True


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

        # Migrate from flat to nested directory layout
        data, nested_changed = migrate_to_nested_layout(data)

        # Only save if migrations actually changed something
        if config_changed or paths_changed or nested_changed:
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

        # Fsync parent directory to ensure rename metadata is durable after power loss
        dir_fd = os.open(str(config_path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise


def parse_github_url(
    url: str,
    require_github: bool = False,
    enterprise_hosts: list[str] | None = None,
) -> str | None:
    """Extract owner/repo from git URL for GitHub/GHE.

    Supports GitHub.com, GitHub Enterprise, and graceful degradation for non-GitHub URLs.

    Args:
        url: Git URL in SSH or HTTPS format
        require_github: If True, raises ValueError for non-GitHub URLs.
                       If False, returns None for non-GitHub URLs (graceful degradation).
        enterprise_hosts: Optional list of GitHub Enterprise hostnames to recognize
                         (e.g., ["ghe.company.com", "github-internal.corp.net"])

    Returns:
        owner/repo slug if GitHub/GHE URL, None if non-GitHub (when require_github=False)

    Examples:
        git@github.com:user/repo.git -> "user/repo" (GitHub)
        git@github.enterprise.com:user/repo.git -> "user/repo" (GHE)
        git@ghe.company.com:user/repo.git -> "user/repo" (GHE with allowlist)
        git@gitlab.com:user/repo.git -> None (GitLab, graceful)
        https://github.com/user/repo.git -> "user/repo" (GitHub)

    Raises:
        ValueError: Only if require_github=True and URL is not GitHub
                   OR if URL format is invalid
    """
    # Normalize enterprise hosts for case-insensitive matching
    ghe_hosts = {h.lower() for h in (enterprise_hosts or [])}

    def is_github_host(host: str) -> bool:
        """Check if host is GitHub.com, GHE, or in enterprise allowlist."""
        host_lower = host.lower()
        return host_lower == "github.com" or host_lower in ghe_hosts

    # SSH format: git@{host}:{owner}/{repo}.git
    ssh_pattern = r"git@([^:]+):([^/]+/[^/]+?)(\.git)?$"
    ssh_match = re.match(ssh_pattern, url)
    if ssh_match:
        host, owner_repo = ssh_match.group(1), ssh_match.group(2)
        # Accept any GitHub hostname or allowlisted enterprise host
        if is_github_host(host):
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
        if is_github_host(host):
            return owner_repo
        elif not require_github:
            return None
        else:
            raise ValueError(f"URL is not a GitHub URL: {url}")

    # No pattern matched - invalid URL format
    if require_github:
        raise ValueError(f"Invalid GitHub URL format: {url}")
    raise ValueError(f"Invalid git URL format: {url}")

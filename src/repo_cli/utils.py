"""Utility functions for repo-cli.

Provides path helpers, validation functions, and common utilities.
"""

import re
from pathlib import Path
from urllib.parse import quote


def expand_path(path: str) -> Path:
    """Expand and resolve a path with ~ expansion.

    Args:
        path: Path string to expand

    Returns:
        Resolved Path object
    """
    return Path(path).expanduser().resolve()


def validate_repo_alias(alias: str) -> None:
    """Validate that a string is safe to use as a repository alias.

    Prevents path traversal attacks by ensuring aliases only contain
    alphanumeric characters, dots, hyphens, and underscores (no slashes).

    Args:
        alias: Repository alias to validate

    Raises:
        ValueError: If alias contains invalid characters or patterns
    """
    if not alias:
        raise ValueError("Invalid repo alias: cannot be empty")

    # Check for :: delimiter first (specific error message for config key collision prevention)
    if "::" in alias:
        raise ValueError(f"Invalid repo alias '{alias}': cannot contain '::'")

    # Strict: no slashes for repo aliases (prevents path traversal)
    pattern = r"^[A-Za-z0-9._-]+$"

    if not re.match(pattern, alias):
        raise ValueError(
            f"Invalid repo alias '{alias}': must contain only letters, numbers, "
            "dots, hyphens, and underscores"
        )

    # Additional check: reject if it's only dots (., .., ...)
    if alias.replace(".", "") == "":
        raise ValueError(f"Invalid repo alias '{alias}': cannot consist only of dots")


def validate_branch_name(branch: str) -> None:
    """Validate that a string is a valid Git branch name.

    Follows Git's branch naming rules (git check-ref-format) while preventing
    dangerous patterns. Allows slashes for hierarchical grouping.

    Args:
        branch: Branch name to validate

    Raises:
        ValueError: If branch name violates Git's rules
    """
    if not branch:
        raise ValueError("Invalid branch name: cannot be empty")

    # Git allows: alphanumeric, dots, hyphens, underscores, slashes, @
    # Git prohibits: control chars, spaces, ~, ^, :, ?, *, [, \, @{, .., ending with dot

    # Check for prohibited characters
    if re.search(r"[\x00-\x1f\x7f \~\^:\?\*\[\\\]]", branch):
        raise ValueError(
            f"Invalid branch name '{branch}': contains prohibited characters "
            "(spaces, ~, ^, :, ?, *, [, \\, or control characters)"
        )

    # Check for prohibited sequences and patterns
    if branch == "@":
        raise ValueError("Invalid branch name: cannot be single '@' character")

    if "@{" in branch:
        raise ValueError(f"Invalid branch name '{branch}': cannot contain '@{{'")

    if ".." in branch:
        raise ValueError(f"Invalid branch name '{branch}': cannot contain '..'")

    if branch.endswith("."):
        raise ValueError(f"Invalid branch name '{branch}': cannot end with '.'")

    if branch.startswith("/") or branch.endswith("/"):
        raise ValueError(f"Invalid branch name '{branch}': cannot start or end with '/'")

    if "//" in branch:
        raise ValueError(f"Invalid branch name '{branch}': cannot contain consecutive slashes")

    # Validate each slash-separated component
    for component in branch.split("/"):
        if component.startswith("."):
            raise ValueError(
                f"Invalid branch name '{branch}': component '{component}' cannot start with '.'"
            )
        if component.endswith(".lock"):
            raise ValueError(
                f"Invalid branch name '{branch}': component '{component}' cannot end with '.lock'"
            )


def validate_path_safety(path: Path, base_dir: Path) -> None:
    """Validate that a path is safely contained within the base directory.

    Prevents path traversal attacks by ensuring the resolved path is a
    subdirectory of base_dir, including protection against symlink escapes.

    Args:
        path: Path to validate
        base_dir: Base directory that should contain the path

    Raises:
        ValueError: If path is outside base directory or escapes via symlink
    """
    try:
        # Resolve both paths to handle symlinks and relative components
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()

        # Check if path is relative to base directory
        if not resolved_path.is_relative_to(resolved_base):
            raise ValueError(f"Path is outside base directory: {path} not within {base_dir}")
    except (OSError, RuntimeError) as e:
        # Handle cases where path resolution fails
        raise ValueError(f"Cannot validate path safety: {e}") from e


def validate_git_url(url: str) -> bool:
    """Validate that a string is a valid git URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid git URL, False otherwise
    """
    # TODO: Implement URL validation for SSH and HTTPS formats
    raise NotImplementedError("validate_git_url not yet implemented")


def get_worktree_path(base_dir: Path, repo: str, branch: str) -> Path:
    """Get the path for a worktree.

    Args:
        base_dir: Base directory for all worktrees
        repo: Repository alias
        branch: Branch name

    Returns:
        Path to the worktree

    Raises:
        ValueError: If repo or branch contains invalid characters
    """
    # Validate inputs to prevent path traversal
    validate_repo_alias(repo)
    validate_branch_name(branch)

    # Percent-encode branch name for filesystem safety (bijective encoding)
    # This allows all valid Git branch names while ensuring unique paths
    # Example: feature/foo -> feature%2Ffoo
    safe_branch = quote(branch, safe="")

    path = base_dir / f"{repo}-{safe_branch}"

    # Additional safety check
    validate_path_safety(path, base_dir)

    return path


def get_bare_repo_path(base_dir: Path, repo: str) -> Path:
    """Get the path for a bare repository.

    Args:
        base_dir: Base directory
        repo: Repository alias

    Returns:
        Path to the bare repository

    Raises:
        ValueError: If repo contains invalid characters
    """
    # Validate input to prevent path traversal
    validate_repo_alias(repo)

    path = base_dir / f"{repo}.git"

    # Additional safety check
    validate_path_safety(path, base_dir)

    return path

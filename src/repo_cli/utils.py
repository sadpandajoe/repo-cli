"""Utility functions for repo-cli.

Provides path helpers, validation functions, and common utilities.
"""

import re
from pathlib import Path


def expand_path(path: str) -> Path:
    """Expand and resolve a path with ~ expansion.

    Args:
        path: Path string to expand

    Returns:
        Resolved Path object
    """
    return Path(path).expanduser().resolve()


def validate_identifier(name: str) -> None:
    """Validate that a string is safe to use as a repo alias or branch name.

    Prevents path traversal attacks by ensuring identifiers only contain
    alphanumeric characters, dots, hyphens, and underscores.

    Args:
        name: Identifier to validate (repo alias or branch name)

    Raises:
        ValueError: If identifier contains invalid characters or patterns
    """
    if not name:
        raise ValueError("Invalid identifier: cannot be empty")

    # Allow only alphanumeric, dots, hyphens, underscores
    # This prevents: /, \, .., parent directory references, spaces, special chars
    pattern = r"^[A-Za-z0-9._-]+$"

    if not re.match(pattern, name):
        raise ValueError(
            f"Invalid identifier '{name}': must contain only letters, numbers, "
            "dots, hyphens, and underscores"
        )

    # Additional check: reject if it's only dots (., .., ...)
    if name.replace(".", "") == "":
        raise ValueError(f"Invalid identifier '{name}': cannot consist only of dots")


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
    validate_identifier(repo)
    validate_identifier(branch)

    path = base_dir / f"{repo}-{branch}"

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
    validate_identifier(repo)

    path = base_dir / f"{repo}.git"

    # Additional safety check
    validate_path_safety(path, base_dir)

    return path

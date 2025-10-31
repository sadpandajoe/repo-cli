"""Utility functions for repo-cli.

Provides path helpers, validation functions, and common utilities.
"""

from pathlib import Path


def expand_path(path: str) -> Path:
    """Expand and resolve a path with ~ and environment variables.

    Args:
        path: Path string to expand

    Returns:
        Resolved Path object
    """
    return Path(path).expanduser().resolve()


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
    """
    return base_dir / f"{repo}-{branch}"


def get_bare_repo_path(base_dir: Path, repo: str) -> Path:
    """Get the path for a bare repository.

    Args:
        base_dir: Base directory
        repo: Repository alias

    Returns:
        Path to the bare repository
    """
    return base_dir / f"{repo}.git"

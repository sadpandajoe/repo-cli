"""Git operations wrapper for repo-cli.

Provides high-level interfaces for git commands:
- Clone repositories as bare
- Create and remove worktrees
- Initialize submodules
"""

import subprocess
from pathlib import Path


class GitOperationError(Exception):
    """Base exception for git operation failures."""

    pass


def clone_bare(url: str, target_path: Path) -> None:
    """Clone a repository as bare.

    Args:
        url: Git repository URL
        target_path: Path where to create the bare repository

    Raises:
        GitOperationError: If clone fails (bad URL, network issues, etc.)
    """
    try:
        subprocess.run(
            ["git", "clone", "--bare", url, str(target_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to clone repository: {stderr}") from e


def create_worktree(
    repo_path: Path, worktree_path: Path, branch: str, start_point: str = "origin/HEAD"
) -> None:
    """Create a new worktree.

    Args:
        repo_path: Path to the bare repository
        worktree_path: Path where to create the worktree
        branch: Name of the branch to create
        start_point: Starting point (branch, tag, or commit)

    Raises:
        GitOperationError: If worktree creation fails (branch exists, bad start point, etc.)
    """
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "worktree",
                "add",
                str(worktree_path),
                "-b",
                branch,
                start_point,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to create worktree: {stderr}") from e


def remove_worktree(repo_path: Path, worktree_path: Path) -> None:
    """Remove a worktree.

    Args:
        repo_path: Path to the bare repository (for context)
        worktree_path: Path to the worktree to remove

    Raises:
        GitOperationError: If removal fails (worktree doesn't exist, uncommitted changes, etc.)
    """
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "worktree", "remove", str(worktree_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to remove worktree: {stderr}") from e


def init_submodules(worktree_path: Path) -> int:
    """Initialize submodules in a worktree.

    Args:
        worktree_path: Path to the worktree

    Returns:
        Number of submodules present (whether newly initialized or already initialized)

    Raises:
        GitOperationError: If submodule initialization fails
    """
    # Check if .gitmodules exists to determine if there are any submodules
    gitmodules_path = worktree_path / ".gitmodules"
    if not gitmodules_path.exists():
        return 0

    # Initialize submodules (idempotent - safe to run multiple times)
    try:
        subprocess.run(
            ["git", "-C", str(worktree_path), "submodule", "update", "--init", "--recursive"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to initialize submodules: {stderr}") from e

    # Count submodules by parsing .gitmodules for [submodule sections
    try:
        content = gitmodules_path.read_text()
        return content.count("[submodule")
    except Exception:
        return 0

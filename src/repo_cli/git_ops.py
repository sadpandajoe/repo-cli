"""Git operations wrapper for repo-cli.

Provides high-level interfaces for git commands:
- Clone repositories as bare
- Create and remove worktrees
- Initialize submodules
"""

import subprocess
from pathlib import Path


def clone_bare(url: str, target_path: Path) -> None:
    """Clone a repository as bare.

    Args:
        url: Git repository URL
        target_path: Path where to create the bare repository
    """
    subprocess.run(
        ["git", "clone", "--bare", url, str(target_path)],
        check=True,
        capture_output=True,
        text=True
    )


def create_worktree(
    repo_path: Path, worktree_path: Path, branch: str, start_point: str = "origin/HEAD"
) -> None:
    """Create a new worktree.

    Args:
        repo_path: Path to the bare repository
        worktree_path: Path where to create the worktree
        branch: Name of the branch to create
        start_point: Starting point (branch, tag, or commit)
    """
    subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "add", str(worktree_path), "-b", branch, start_point],
        check=True,
        capture_output=True,
        text=True
    )


def remove_worktree(worktree_path: Path) -> None:
    """Remove a worktree.

    Args:
        worktree_path: Path to the worktree to remove
    """
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path)],
        check=True,
        capture_output=True,
        text=True
    )


def init_submodules(worktree_path: Path) -> int:
    """Initialize submodules in a worktree.

    Args:
        worktree_path: Path to the worktree

    Returns:
        Number of submodules initialized
    """
    result = subprocess.run(
        ["git", "-C", str(worktree_path), "submodule", "update", "--init", "--recursive"],
        check=True,
        capture_output=True,
        text=True
    )

    # Count "Submodule" occurrences in stdout to determine how many were initialized
    return result.stdout.count("Submodule")

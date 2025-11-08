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


def get_default_branch(repo_path: Path) -> str:
    """Get the default branch for the repository.

    Args:
        repo_path: Path to the bare repository

    Returns:
        Name of the default branch (e.g., 'master', 'main')
    """
    try:
        # Read HEAD to find default branch
        result = subprocess.run(
            ["git", "-C", str(repo_path), "symbolic-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        # Output is like "refs/heads/master"
        ref = result.stdout.strip()
        # Extract branch name
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/") :]
        return ref
    except subprocess.CalledProcessError:
        # Fallback to main/master
        # Check if main exists
        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "show-ref", "--verify", "refs/heads/main"],
                check=True,
                capture_output=True,
                text=True,
            )
            return "main"
        except subprocess.CalledProcessError:
            # Default to master
            return "master"


def branch_exists(repo_path: Path, branch: str) -> bool:
    """Check if a branch exists in the repository.

    Args:
        repo_path: Path to the bare repository
        branch: Name of the branch to check

    Returns:
        True if branch exists (locally or as remote), False otherwise
    """
    # Check for remote branch (most common case for bare repos)
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "show-ref", "--verify", f"refs/remotes/origin/{branch}"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        pass

    # Check for local branch (bare repos store branches here)
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "show-ref", "--verify", f"refs/heads/{branch}"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        pass

    return False


def create_worktree(
    repo_path: Path, worktree_path: Path, branch: str, start_point: str = "origin/HEAD"
) -> tuple[None, bool]:
    """Create a new worktree.

    Args:
        repo_path: Path to the bare repository
        worktree_path: Path where to create the worktree
        branch: Name of the branch to create or checkout
        start_point: Starting point (branch, tag, or commit) - only used for new branches

    Returns:
        Tuple of (None, is_new_branch) where is_new_branch indicates if a new branch was created

    Raises:
        GitOperationError: If worktree creation fails
    """
    # Check if branch already exists
    existing = branch_exists(repo_path, branch)

    try:
        if existing:
            # Checkout existing branch (try remote first, then local)
            branch_ref = f"origin/{branch}"
            # Check if remote branch exists, otherwise use local
            try:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "show-ref",
                        "--verify",
                        f"refs/remotes/origin/{branch}",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError:
                branch_ref = branch

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "worktree",
                    "add",
                    str(worktree_path),
                    branch_ref,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return None, False
        else:
            # Create new branch
            # Resolve origin/HEAD to actual default branch for bare repos
            resolved_start = start_point
            if start_point == "origin/HEAD":
                # For bare repos, use the default branch directly
                resolved_start = get_default_branch(repo_path)

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
                    resolved_start,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return None, True
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

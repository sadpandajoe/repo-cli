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


def fetch_repo(repo_path: Path) -> None:
    """Fetch latest refs from origin.

    Args:
        repo_path: Path to the bare repository

    Raises:
        GitOperationError: If fetch fails
    """
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "fetch", "--prune", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to fetch repository: {stderr}") from e


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
) -> tuple[str, bool]:
    """Create a new worktree.

    Args:
        repo_path: Path to the bare repository
        worktree_path: Path where to create the worktree
        branch: Name of the branch to create or checkout
        start_point: Starting point (branch, tag, or commit) - only used for new branches

    Returns:
        Tuple of (actual_ref_used, is_new_branch) where actual_ref_used is the ref that was checked out

    Raises:
        GitOperationError: If worktree creation fails
    """
    # Check if branch already exists
    existing = branch_exists(repo_path, branch)

    try:
        if existing:
            # Check if local branch exists
            has_local = False
            try:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "show-ref",
                        "--verify",
                        f"refs/heads/{branch}",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                has_local = True
            except subprocess.CalledProcessError:
                pass

            if has_local:
                # Local branch exists, checkout directly
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "worktree",
                        "add",
                        str(worktree_path),
                        branch,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return branch, False
            else:
                # Remote-only branch, create local tracking branch
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
                        f"origin/{branch}",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return f"origin/{branch}", False
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
            return resolved_start, True
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
    """Initialize submodules in a worktree, excluding .github submodules.

    Args:
        worktree_path: Path to the worktree

    Returns:
        Number of non-.github submodules initialized

    Raises:
        GitOperationError: If submodule initialization fails
    """
    # Check if .gitmodules exists to determine if there are any submodules
    gitmodules_path = worktree_path / ".gitmodules"
    if not gitmodules_path.exists():
        return 0

    # Parse .gitmodules to find non-.github submodules
    try:
        content = gitmodules_path.read_text()
    except (OSError, PermissionError, UnicodeDecodeError) as e:
        raise GitOperationError(
            f"Failed to read .gitmodules file: {e}. "
            "This may indicate a corrupt file, permission issue, or encoding problem."
        ) from e

    # Extract submodule paths (simple regex-free parsing)
    submodule_paths = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("path ="):
            path = line.split("=", 1)[1].strip()
            # Skip .github submodules (CI/CD actions, not needed for local dev)
            if not path.startswith(".github/"):
                submodule_paths.append(path)

    # If no non-.github submodules, return early
    if not submodule_paths:
        return 0

    # Initialize each non-.github submodule individually
    try:
        for path in submodule_paths:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(worktree_path),
                    "submodule",
                    "update",
                    "--init",
                    "--recursive",
                    path,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to initialize submodules: {stderr}") from e

    return len(submodule_paths)


def get_remote_url(repo_path: Path, remote: str = "origin") -> str:
    """Get the URL for a remote.

    Args:
        repo_path: Path to the repository (can be bare or regular)
        remote: Name of the remote (default: origin)

    Returns:
        URL of the remote

    Raises:
        GitOperationError: If remote doesn't exist or command fails
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", remote],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to get remote URL: {stderr}") from e


def set_remote_url(repo_path: Path, url: str, remote: str = "origin") -> None:
    """Set the URL for a remote.

    Args:
        repo_path: Path to the repository (can be bare or regular)
        url: New URL for the remote
        remote: Name of the remote (default: origin)

    Raises:
        GitOperationError: If operation fails
    """
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "remote", "set-url", remote, url],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to set remote URL: {stderr}") from e


def get_latest_tag(repo_path: Path, remote: str = "origin") -> str | None:
    """Get the latest semver tag from the remote.

    Args:
        repo_path: Path to the git repository
        remote: Name of the remote (default: origin)

    Returns:
        Latest tag string (e.g., "v0.1.0") or None if no tags found

    Raises:
        GitOperationError: If git operation fails
    """
    try:
        # Fetch tags from remote
        subprocess.run(
            ["git", "-C", str(repo_path), "fetch", remote, "--tags"],
            check=True,
            capture_output=True,
            text=True,
        )

        # Get latest tag sorted by version
        result = subprocess.run(
            ["git", "-C", str(repo_path), "tag", "--list", "--sort=-v:refname"],
            check=True,
            capture_output=True,
            text=True,
        )

        tags = result.stdout.strip().split("\n")
        return tags[0] if tags and tags[0] else None

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to get latest tag: {stderr}") from e


def get_current_branch(repo_path: Path) -> str:
    """Get the current branch name.

    Args:
        repo_path: Path to the git repository

    Returns:
        Current branch name

    Raises:
        GitOperationError: If git operation fails
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to get current branch: {stderr}") from e


def has_uncommitted_changes(repo_path: Path) -> bool:
    """Check if repository has uncommitted changes.

    Args:
        repo_path: Path to the git repository

    Returns:
        True if there are uncommitted changes, False otherwise

    Raises:
        GitOperationError: If git operation fails
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to check git status: {stderr}") from e


def pull_latest(repo_path: Path, remote: str = "origin", branch: str = "main") -> None:
    """Pull latest changes from remote.

    Args:
        repo_path: Path to the git repository
        remote: Name of the remote (default: origin)
        branch: Branch to pull (default: main)

    Raises:
        GitOperationError: If git operation fails
    """
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "pull", remote, branch],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to pull latest changes: {stderr}") from e

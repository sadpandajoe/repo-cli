"""Git operations wrapper for repo-cli.

Provides high-level interfaces for git commands:
- Clone repositories as bare
- Create and remove worktrees
- Initialize submodules
"""

import contextlib
import subprocess
from pathlib import Path
from typing import Any


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
        # Configure fetch refspec so `git fetch origin` updates remote-tracking branches
        # Without this, bare clones only fetch to FETCH_HEAD, not refs/remotes/origin/*
        subprocess.run(
            [
                "git",
                "-C",
                str(target_path),
                "config",
                "remote.origin.fetch",
                "+refs/heads/*:refs/remotes/origin/*",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to clone repository: {stderr}") from e


def _ensure_fetch_refspec(repo_path: Path) -> None:
    """Ensure the fetch refspec is configured for remote-tracking branches.

    Migration for repos cloned before v0.1.2 that are missing the refspec.
    Without this config, `git fetch origin` only updates FETCH_HEAD.

    Only sets the refspec if it's missing/empty. Does NOT overwrite existing
    custom configurations to avoid clobbering user settings.

    Args:
        repo_path: Path to the bare repository
    """
    try:
        # Check current refspec
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.fetch"],
            capture_output=True,
            text=True,
            check=False,  # Don't raise if config doesn't exist
        )
        current_refspec = result.stdout.strip()

        # Only set if missing/empty - don't overwrite custom user configurations
        if not current_refspec:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "config",
                    "remote.origin.fetch",
                    "+refs/heads/*:refs/remotes/origin/*",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
    except subprocess.CalledProcessError:
        # Non-fatal: if we can't fix the refspec, fetch will still work (just to FETCH_HEAD)
        pass


def fetch_repo(repo_path: Path) -> None:
    """Fetch latest refs from origin.

    Automatically migrates repos cloned before v0.1.2 to use proper refspec.

    Args:
        repo_path: Path to the bare repository

    Raises:
        GitOperationError: If fetch fails
    """
    # Migration: ensure refspec is configured (for pre-v0.1.2 repos)
    _ensure_fetch_refspec(repo_path)

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

    # Clean up stale local branches (migration for bare clones)
    _cleanup_stale_local_branches(repo_path)


def get_default_branch(repo_path: Path) -> str:
    """Get the default branch for the repository.

    Args:
        repo_path: Path to the bare repository

    Returns:
        Name of the default branch (e.g., 'master', 'main')

    Raises:
        GitOperationError: If no default branch can be determined
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

        # Extract branch name - ONLY if in expected format
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/") :]

        # Handle remote HEAD (e.g., refs/remotes/origin/HEAD)
        if ref.startswith("refs/remotes/"):
            try:
                # Resolve remote HEAD to actual target branch
                resolved = subprocess.run(
                    ["git", "-C", str(repo_path), "symbolic-ref", ref],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                resolved_ref = resolved.stdout.strip()
                # Extract branch name from refs/remotes/origin/develop → develop
                # Handle slashes in branch names: refs/remotes/origin/release/2026 → release/2026
                if resolved_ref.startswith("refs/remotes/"):
                    # Strip refs/remotes/origin/ prefix (4 components)
                    parts = resolved_ref.split("/")
                    if len(parts) >= 4:  # refs/remotes/origin/branch[/...]
                        return "/".join(parts[3:])
            except subprocess.CalledProcessError:
                # Resolution failed, fall through to fallback
                pass

        # If unexpected format, raise to trigger fallback logic
        raise ValueError(f"Unexpected ref format: {ref}")

    except (subprocess.CalledProcessError, ValueError):
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
            pass

        # Check if master exists
        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "show-ref", "--verify", "refs/heads/master"],
                check=True,
                capture_output=True,
                text=True,
            )
            return "master"
        except subprocess.CalledProcessError:
            pass

        # Neither main nor master exists
        raise GitOperationError(
            "Could not determine default branch. Repository has neither 'main' nor 'master' branch."
        ) from None


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


def _set_upstream_tracking(repo_path: Path, branch: str) -> None:
    """Configure upstream tracking so `git pull` works in worktrees.

    Sets branch.<name>.remote and branch.<name>.merge in the bare repo config.
    Only sets tracking if a remote-tracking branch exists (origin/<branch>).

    Args:
        repo_path: Path to the bare repository
        branch: Name of the local branch to configure
    """
    # Check if remote-tracking branch exists
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
        return  # No remote branch to track

    # Set upstream tracking config
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "config",
                f"branch.{branch}.remote",
                "origin",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "config",
                f"branch.{branch}.merge",
                f"refs/heads/{branch}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )


def _cleanup_stale_local_branches(repo_path: Path) -> None:
    """Maintain local branch hygiene in bare repos.

    Fast-forwards the HEAD branch to match its remote, then removes stale
    local refs. In a repo-cli bare repo, the only local branches that should
    exist are the HEAD branch and branches checked out in worktrees.
    Everything else under refs/heads/* is a stale artifact from bare clone.
    """
    # Get HEAD ref to protect it
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "symbolic-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        head_ref = result.stdout.strip()
    except subprocess.CalledProcessError:
        return

    # Fast-forward HEAD branch to match remote — _try_fast_forward_branch is
    # internally safe (no exceptions propagate), but wrap defensively so
    # cleanup always proceeds even if something unexpected happens.
    head_branch = head_ref.removeprefix("refs/heads/")
    with contextlib.suppress(Exception):
        _try_fast_forward_branch(repo_path, head_branch)

    # Get branches checked out in worktrees
    checked_out: set[str] = set()
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "worktree", "list", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.split("\n"):
            if line.startswith("branch "):
                checked_out.add(line.split(" ", 1)[1])
    except subprocess.CalledProcessError:
        return

    # Get all local branch refs
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "for-each-ref",
                "--format=%(refname)",
                "refs/heads/",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return

    # Delete any local branch that's not HEAD and not checked out in a worktree
    for line in result.stdout.strip().split("\n"):
        ref = line.strip()
        if not ref:
            continue
        if ref == head_ref or ref in checked_out:
            continue
        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(
                ["git", "-C", str(repo_path), "update-ref", "-d", ref],
                check=True,
                capture_output=True,
                text=True,
            )


def _try_fast_forward_branch(repo_path: Path, branch: str) -> None:
    """Attempt to fast-forward a local branch to match its remote-tracking branch.

    Safe: only updates when local is strictly behind remote (ancestor check).
    Effectively no-op when: no remote branch exists, branches have diverged,
    or local is already up-to-date (update-ref writes same SHA).

    Args:
        repo_path: Path to the bare repository
        branch: Name of the local branch to fast-forward
    """
    # Step 1: Check if remote-tracking branch exists
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
        return  # No remote branch — nothing to fast-forward to

    # Step 2: Check if fast-forward is possible (local is ancestor of remote)
    # merge-base --is-ancestor returns: 0 = ancestor (or equal), 1 = not ancestor, 128 = error
    # Any non-zero means we should skip fast-forward (diverged or error)
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_path),
            "merge-base",
            "--is-ancestor",
            f"refs/heads/{branch}",
            f"refs/remotes/origin/{branch}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return  # Not a clean fast-forward (diverged or git error) — preserve local branch

    # Step 3: Fast-forward local ref to match remote
    # update-ref with a ref name as new-value: git resolves it to SHA at call time
    # Suppress failures (disk full, permissions, etc.) — proceed with stale branch
    with contextlib.suppress(subprocess.CalledProcessError):
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "update-ref",
                f"refs/heads/{branch}",
                f"refs/remotes/origin/{branch}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )


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
            # Check if local branch exists (refs/heads/<branch>)
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
                # Fast-forward local branch to match remote if possible
                _try_fast_forward_branch(repo_path, branch)

                # Create worktree from (now possibly updated) local branch
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
                _set_upstream_tracking(repo_path, branch)
                return branch, False

            # No local branch - check if remote-tracking branch exists
            has_remote = False
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
                has_remote = True
            except subprocess.CalledProcessError:
                pass

            if has_remote:
                # Only remote exists - create local branch from remote using -B
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "worktree",
                        "add",
                        str(worktree_path),
                        "-B",
                        branch,
                        f"origin/{branch}",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                _set_upstream_tracking(repo_path, branch)
                return f"origin/{branch}", False
            # Race condition: branch_exists() returned True but neither local nor remote
            # ref could be verified (transient state). Raise rather than return None.
            raise GitOperationError(
                f"Branch '{branch}' was detected but could not be resolved. "
                "This may be a transient state — try again."
            )
        else:
            # Create new branch
            # Resolve origin/HEAD to actual default branch for bare repos
            resolved_start = start_point
            if start_point == "origin/HEAD":
                # Resolve to remote ref so we get current state, not stale local
                default_branch = get_default_branch(repo_path)
                resolved_start = f"origin/{default_branch}"

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


def remove_worktree(
    repo_path: Path, worktree_path: Path, console: Any = None, *, force: bool = False
) -> None:
    """Remove worktree, handling submodules if present.

    Strategy:
    1. Try normal removal first (fast path), or --force if requested
    2. On submodule error, deinit and retry with --force
    3. Provide clear feedback at each step (if console provided)

    Args:
        repo_path: Path to the bare repository (for context)
        worktree_path: Path to the worktree to remove
        console: Optional Rich console for user feedback (for interactive mode)
        force: If True, pass --force to git worktree remove (removes dirty worktrees)

    Raises:
        GitOperationError: If removal fails

    Note:
        Uses dependency injection to avoid circular import (git_ops → main).
        Console parameter is optional - works in both interactive and programmatic contexts.
    """
    try:
        # Try removal (with --force if requested)
        cmd = ["git", "-C", str(repo_path), "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(str(worktree_path))
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # Check if error is submodule-related
        if e.stderr and "submodule" in e.stderr.lower():
            # Provide feedback only if console is available
            if console:
                console.print("⚠️  Worktree contains submodules, deinitializing...", style="yellow")

            try:
                # Deinitialize submodules
                # --force: Remove even if working tree has local modifications
                # --all: Apply to all submodules
                subprocess.run(
                    ["git", "-C", str(worktree_path), "submodule", "deinit", "--all", "--force"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Retry removal with --force
                # --force: Remove even if worktree is dirty (after deinit, git may still think it's modified)
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "worktree",
                        "remove",
                        "--force",
                        str(worktree_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                if console:
                    console.print("✓ Submodules deinitialized", style="green")

            except subprocess.CalledProcessError as submodule_error:
                # Provide context-specific error message
                stderr = (
                    submodule_error.stderr.strip() if submodule_error.stderr else "Unknown error"
                )
                raise GitOperationError(
                    f"Failed to remove worktree with submodules: {stderr}"
                ) from submodule_error
        else:
            # Re-raise with better error message
            stderr = e.stderr.strip() if e.stderr else "Unknown error"
            raise GitOperationError(f"Failed to remove worktree: {stderr}") from e


def init_submodules(worktree_path: Path, *, remote: bool = True) -> int:
    """Initialize submodules in a worktree, excluding .github submodules.

    Args:
        worktree_path: Path to the worktree
        remote: If True, fetch latest from tracking branch instead of pinned
            commit. Default True for convenience; set False for reproducible builds.

    Returns:
        Number of non-.github submodules initialized

    Raises:
        GitOperationError: If submodule initialization fails
    """
    # Check if .gitmodules exists to determine if there are any submodules
    gitmodules_path = worktree_path / ".gitmodules"
    if not gitmodules_path.exists():
        return 0

    # Parse .gitmodules using git config (handles all valid formatting variants)
    try:
        result = subprocess.run(
            [
                "git",
                "config",
                "-f",
                str(gitmodules_path),
                "--get-regexp",
                r"submodule\..*\.path",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            # No matches found (empty .gitmodules or no path entries)
            return 0
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Failed to parse .gitmodules: {stderr}") from e

    # Output format: "submodule.name.path value\n" per line
    submodule_paths = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Split "submodule.foo.path bar/baz" into key and value
        parts = line.split(None, 1)  # Split on whitespace, max 2 parts
        if len(parts) == 2:
            path = parts[1]
            # Skip .github submodules (CI/CD actions, not needed for local dev)
            if not path.startswith(".github/"):
                submodule_paths.append(path)

    # If no non-.github submodules, return early
    if not submodule_paths:
        return 0

    # Initialize each non-.github submodule individually
    try:
        for path in submodule_paths:
            cmd = [
                "git",
                "-C",
                str(worktree_path),
                "submodule",
                "update",
                "--init",
                "--recursive",
            ]
            if remote:
                cmd.append("--remote")
            cmd.append(path)
            subprocess.run(cmd, check=True, capture_output=True, text=True)
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


def rebase_onto(worktree_path: Path, upstream: str) -> None:
    """Rebase the current branch in a worktree onto an upstream ref.

    Args:
        worktree_path: Path to the worktree
        upstream: Upstream ref to rebase onto (e.g. 'origin/main')

    Raises:
        GitOperationError: If rebase fails (conflicts, detached HEAD, etc.)
    """
    try:
        subprocess.run(
            ["git", "-C", str(worktree_path), "rebase", upstream],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        # Abort the rebase so the worktree isn't left in a broken state
        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(
                ["git", "-C", str(worktree_path), "rebase", "--abort"],
                check=True,
                capture_output=True,
                text=True,
            )
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitOperationError(f"Rebase failed: {stderr}") from e

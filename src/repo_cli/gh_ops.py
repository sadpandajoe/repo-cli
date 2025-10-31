"""GitHub CLI operations wrapper for repo-cli.

Provides interfaces for querying PR status using gh CLI.
Handles graceful fallback when gh is unavailable.
"""


def is_gh_available() -> bool:
    """Check if gh CLI is installed and available."""
    # TODO: Implement using shutil.which('gh')
    raise NotImplementedError("is_gh_available not yet implemented")


def get_pr_status(pr_number: int, owner_repo: str) -> str | None:
    """Get PR status from GitHub.

    Args:
        pr_number: Pull request number
        owner_repo: Repository in owner/repo format

    Returns:
        PR status string (e.g., "Open", "Merged", "Closed") or None if unavailable
    """
    # TODO: Implement gh pr view <pr#> --repo <owner_repo> --json state
    # TODO: Handle errors gracefully (offline, not installed, etc.)
    raise NotImplementedError("get_pr_status not yet implemented")


def validate_pr_exists(pr_number: int, owner_repo: str) -> bool:
    """Validate that a PR exists.

    Args:
        pr_number: Pull request number
        owner_repo: Repository in owner/repo format

    Returns:
        True if PR exists, False otherwise
    """
    # TODO: Implement gh pr view validation
    raise NotImplementedError("validate_pr_exists not yet implemented")

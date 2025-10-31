"""GitHub CLI operations wrapper for repo-cli.

Provides interfaces for querying PR status using gh CLI.
Handles graceful fallback when gh is unavailable.
"""

import json
import shutil
import subprocess


def is_gh_available() -> bool:
    """Check if gh CLI is installed and available."""
    return shutil.which("gh") is not None


def get_pr_status(pr_number: int, owner_repo: str) -> str | None:
    """Get PR status from GitHub.

    Args:
        pr_number: Pull request number
        owner_repo: Repository in owner/repo format

    Returns:
        PR status string (e.g., "Open", "Merged", "Closed") or None if unavailable
    """
    if not is_gh_available():
        return None

    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--repo", owner_repo, "--json", "state"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        state = data.get("state", "").upper()

        # Map GitHub states to user-friendly strings
        state_map = {
            "OPEN": "Open",
            "CLOSED": "Closed",
            "MERGED": "Merged"
        }

        return state_map.get(state)

    except (json.JSONDecodeError, KeyError, Exception):
        return None


def validate_pr_exists(pr_number: int, owner_repo: str) -> bool:
    """Validate that a PR exists.

    Args:
        pr_number: Pull request number
        owner_repo: Repository in owner/repo format

    Returns:
        True if PR exists, False otherwise
    """
    if not is_gh_available():
        return False

    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--repo", owner_repo],
            capture_output=True,
            text=True,
            check=False
        )

        return result.returncode == 0

    except Exception:
        return False

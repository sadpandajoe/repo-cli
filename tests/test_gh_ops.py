"""Tests for gh_ops module."""

from unittest.mock import MagicMock, patch

from repo_cli.gh_ops import get_pr_status, is_gh_available, validate_pr_exists


class TestIsGhAvailable:
    """Tests for is_gh_available function."""

    @patch("repo_cli.gh_ops.shutil.which")
    def test_gh_available(self, mock_which):
        """Should return True when gh CLI is found."""
        mock_which.return_value = "/usr/local/bin/gh"

        assert is_gh_available() is True
        mock_which.assert_called_once_with("gh")

    @patch("repo_cli.gh_ops.shutil.which")
    def test_gh_not_available(self, mock_which):
        """Should return False when gh CLI is not found."""
        mock_which.return_value = None

        assert is_gh_available() is False


class TestGetPrStatus:
    """Tests for get_pr_status function."""

    @patch("repo_cli.gh_ops.subprocess.run")
    @patch("repo_cli.gh_ops.is_gh_available")
    def test_get_pr_status_success(self, mock_is_available, mock_run):
        """Should return PR status when gh CLI works."""
        mock_is_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout='{"state":"OPEN"}\n')

        status = get_pr_status(4567, "owner/repo")

        assert status == "Open"
        mock_run.assert_called_once_with(
            ["gh", "pr", "view", "4567", "--repo", "owner/repo", "--json", "state"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("repo_cli.gh_ops.subprocess.run")
    @patch("repo_cli.gh_ops.is_gh_available")
    def test_get_pr_status_merged(self, mock_is_available, mock_run):
        """Should return Merged status."""
        mock_is_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout='{"state":"MERGED"}\n')

        status = get_pr_status(123, "owner/repo")

        assert status == "Merged"

    @patch("repo_cli.gh_ops.subprocess.run")
    @patch("repo_cli.gh_ops.is_gh_available")
    def test_get_pr_status_closed(self, mock_is_available, mock_run):
        """Should return Closed status."""
        mock_is_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout='{"state":"CLOSED"}\n')

        status = get_pr_status(456, "owner/repo")

        assert status == "Closed"

    @patch("repo_cli.gh_ops.is_gh_available")
    def test_get_pr_status_gh_not_available(self, mock_is_available):
        """Should return None when gh CLI not available."""
        mock_is_available.return_value = False

        status = get_pr_status(123, "owner/repo")

        assert status is None

    @patch("repo_cli.gh_ops.subprocess.run")
    @patch("repo_cli.gh_ops.is_gh_available")
    def test_get_pr_status_command_fails(self, mock_is_available, mock_run):
        """Should return None when command fails."""
        mock_is_available.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        status = get_pr_status(999, "owner/repo")

        assert status is None


class TestValidatePrExists:
    """Tests for validate_pr_exists function."""

    @patch("repo_cli.gh_ops.subprocess.run")
    @patch("repo_cli.gh_ops.is_gh_available")
    def test_validate_pr_exists_true(self, mock_is_available, mock_run):
        """Should return True when PR exists."""
        mock_is_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        assert validate_pr_exists(123, "owner/repo") is True

    @patch("repo_cli.gh_ops.subprocess.run")
    @patch("repo_cli.gh_ops.is_gh_available")
    def test_validate_pr_exists_false(self, mock_is_available, mock_run):
        """Should return False when PR doesn't exist."""
        mock_is_available.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        assert validate_pr_exists(999, "owner/repo") is False

    @patch("repo_cli.gh_ops.is_gh_available")
    def test_validate_pr_gh_not_available(self, mock_is_available):
        """Should return False when gh CLI not available."""
        mock_is_available.return_value = False

        assert validate_pr_exists(123, "owner/repo") is False

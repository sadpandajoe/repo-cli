"""Tests for git_ops module."""

import pytest
from unittest.mock import patch, call, MagicMock
from pathlib import Path
from repo_cli.git_ops import clone_bare, create_worktree, remove_worktree, init_submodules


class TestCloneBare:
    """Tests for clone_bare function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_success(self, mock_run):
        """Should run git clone --bare command."""
        mock_run.return_value = MagicMock(returncode=0)

        url = "git@github.com:owner/repo.git"
        target_path = Path("/tmp/test/repo.git")

        clone_bare(url, target_path)

        mock_run.assert_called_once_with(
            ["git", "clone", "--bare", url, str(target_path)],
            check=True,
            capture_output=True,
            text=True
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_command_failure(self, mock_run):
        """Should raise exception on git command failure."""
        mock_run.side_effect = Exception("git clone failed")

        with pytest.raises(Exception):
            clone_bare("invalid-url", Path("/tmp/test"))


class TestCreateWorktree:
    """Tests for create_worktree function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_with_default_start_point(self, mock_run):
        """Should create worktree with default start point."""
        mock_run.return_value = MagicMock(returncode=0)

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-branch")
        branch = "feature-123"

        create_worktree(repo_path, worktree_path, branch)

        mock_run.assert_called_once_with(
            ["git", "-C", str(repo_path), "worktree", "add", str(worktree_path), "-b", branch, "origin/HEAD"],
            check=True,
            capture_output=True,
            text=True
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_with_custom_start_point(self, mock_run):
        """Should create worktree with custom start point."""
        mock_run.return_value = MagicMock(returncode=0)

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-hotfix")
        branch = "hotfix-456"
        start_point = "v2.1.0"

        create_worktree(repo_path, worktree_path, branch, start_point)

        mock_run.assert_called_once_with(
            ["git", "-C", str(repo_path), "worktree", "add", str(worktree_path), "-b", branch, start_point],
            check=True,
            capture_output=True,
            text=True
        )


class TestRemoveWorktree:
    """Tests for remove_worktree function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_remove_worktree_success(self, mock_run):
        """Should run git worktree remove command."""
        mock_run.return_value = MagicMock(returncode=0)

        worktree_path = Path("/tmp/test/repo-branch")

        remove_worktree(worktree_path)

        mock_run.assert_called_once_with(
            ["git", "worktree", "remove", str(worktree_path)],
            check=True,
            capture_output=True,
            text=True
        )


class TestInitSubmodules:
    """Tests for init_submodules function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_init_submodules_with_submodules_present(self, mock_run):
        """Should initialize submodules and return count."""
        # Mock subprocess to return output indicating 3 submodules
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Submodule 'sub1' registered\nSubmodule 'sub2' registered\nSubmodule 'sub3' registered\n"
        )

        worktree_path = Path("/tmp/test/repo-branch")

        count = init_submodules(worktree_path)

        assert count == 3
        mock_run.assert_called_once_with(
            ["git", "-C", str(worktree_path), "submodule", "update", "--init", "--recursive"],
            check=True,
            capture_output=True,
            text=True
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_init_submodules_with_no_submodules(self, mock_run):
        """Should return 0 when no submodules present."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        worktree_path = Path("/tmp/test/repo-branch")

        count = init_submodules(worktree_path)

        assert count == 0

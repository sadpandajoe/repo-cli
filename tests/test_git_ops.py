"""Tests for git_ops module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cli.git_ops import (
    GitOperationError,
    branch_exists,
    clone_bare,
    create_worktree,
    get_default_branch,
    init_submodules,
    remove_worktree,
)


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
            text=True,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_command_failure(self, mock_run):
        """Should raise GitOperationError on git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "clone"], stderr="fatal: repository not found"
        )

        with pytest.raises(GitOperationError, match="Failed to clone repository"):
            clone_bare("invalid-url", Path("/tmp/test"))


class TestGetDefaultBranch:
    """Tests for get_default_branch function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_from_head(self, mock_run):
        """Should return default branch from HEAD symref."""
        mock_run.return_value = MagicMock(returncode=0, stdout="refs/heads/master\n")

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "master"
        mock_run.assert_called_once_with(
            ["git", "-C", str(repo_path), "symbolic-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_fallback_to_main(self, mock_run):
        """Should fallback to 'main' if HEAD check fails and main exists."""
        # First call (symbolic-ref) fails, second call (check main) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "main"
        assert mock_run.call_count == 2

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_fallback_to_master(self, mock_run):
        """Should fallback to 'master' if HEAD and main checks fail."""
        # All checks fail
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),
            subprocess.CalledProcessError(1, ["git"]),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "master"
        assert mock_run.call_count == 2

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_handles_head_literal(self, mock_run):
        """Should fallback when symbolic-ref returns 'HEAD' literal."""
        # First call returns "HEAD" (unexpected format)
        # Second call checks for main (succeeds)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="HEAD\n"),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "main"
        assert mock_run.call_count == 2

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_handles_remote_ref(self, mock_run):
        """Should fallback when symbolic-ref returns remote ref."""
        # First call returns "refs/remotes/origin/HEAD" (unexpected format)
        # Second call checks for main (succeeds)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="refs/remotes/origin/HEAD\n"),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "main"
        assert mock_run.call_count == 2

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_handles_custom_ref(self, mock_run):
        """Should fallback when symbolic-ref returns custom ref format."""
        # First call returns custom ref (unexpected format)
        # Second call checks for main (fails)
        # Third call defaults to master
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="refs/custom/foo\n"),
            subprocess.CalledProcessError(1, ["git"]),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "master"
        assert mock_run.call_count == 2


class TestBranchExists:
    """Tests for branch_exists function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_branch_exists_remote(self, mock_run):
        """Should return True when remote branch exists."""
        mock_run.return_value = MagicMock(returncode=0)

        repo_path = Path("/tmp/test/repo.git")
        branch = "6.0"

        result = branch_exists(repo_path, branch)

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "-C", str(repo_path), "show-ref", "--verify", "refs/remotes/origin/6.0"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_branch_exists_local(self, mock_run):
        """Should return True when local branch exists."""
        # First call (remote check) fails, second call (local check) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        branch = "main"

        result = branch_exists(repo_path, branch)

        assert result is True
        assert mock_run.call_count == 2

    @patch("repo_cli.git_ops.subprocess.run")
    def test_branch_does_not_exist(self, mock_run):
        """Should return False when branch doesn't exist."""
        # Both remote and local checks fail
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),
            subprocess.CalledProcessError(1, ["git"]),
        ]

        repo_path = Path("/tmp/test/repo.git")
        branch = "nonexistent"

        result = branch_exists(repo_path, branch)

        assert result is False
        assert mock_run.call_count == 2


class TestCreateWorktree:
    """Tests for create_worktree function."""

    @patch("repo_cli.git_ops.get_default_branch")
    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_new_branch_default_start_point(
        self, mock_run, mock_branch_exists, mock_get_default
    ):
        """Should create new worktree with default branch when using origin/HEAD."""
        mock_branch_exists.return_value = False
        mock_get_default.return_value = "master"
        mock_run.return_value = MagicMock(returncode=0)

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-branch")
        branch = "feature-123"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch)

        assert is_new is True
        assert actual_ref == "master"
        mock_branch_exists.assert_called_once_with(repo_path, branch)
        mock_get_default.assert_called_once_with(repo_path)
        mock_run.assert_called_once_with(
            [
                "git",
                "-C",
                str(repo_path),
                "worktree",
                "add",
                str(worktree_path),
                "-b",
                branch,
                "master",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("repo_cli.git_ops.get_default_branch")
    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_new_branch_custom_start_point(
        self, mock_run, mock_branch_exists, mock_get_default
    ):
        """Should create new worktree with custom start point when branch doesn't exist."""
        mock_branch_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-hotfix")
        branch = "hotfix-456"
        start_point = "v2.1.0"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch, start_point)

        assert is_new is True
        assert actual_ref == "v2.1.0"
        # get_default_branch should not be called when using custom start point
        mock_get_default.assert_not_called()
        mock_run.assert_called_once_with(
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

    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_existing_remote_only_branch(self, mock_run, mock_branch_exists):
        """Should create local tracking branch for remote-only branch."""
        mock_branch_exists.return_value = True
        # First call checks for local branch (fails), second creates worktree
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),  # No local branch
            MagicMock(returncode=0),  # Worktree creation succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-6.0")
        branch = "6.0"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch)

        assert is_new is False
        assert actual_ref == "origin/6.0"
        mock_branch_exists.assert_called_once_with(repo_path, branch)
        assert mock_run.call_count == 2
        # Last call should create local tracking branch with -b flag
        last_call = mock_run.call_args_list[-1]
        assert last_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "-b",
            "6.0",
            "origin/6.0",
        ]

    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_existing_local_branch(self, mock_run, mock_branch_exists):
        """Should checkout existing local branch directly."""
        mock_branch_exists.return_value = True
        # First call checks for local branch (succeeds), second creates worktree
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Local branch exists
            MagicMock(returncode=0),  # Worktree creation succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-main")
        branch = "main"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch)

        assert is_new is False
        assert actual_ref == "main"
        # Last call should checkout local branch directly
        last_call = mock_run.call_args_list[-1]
        assert last_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "main",
        ]


class TestRemoveWorktree:
    """Tests for remove_worktree function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_remove_worktree_success(self, mock_run):
        """Should run git worktree remove command with repo context."""
        mock_run.return_value = MagicMock(returncode=0)

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-branch")

        remove_worktree(repo_path, worktree_path)

        mock_run.assert_called_once_with(
            ["git", "-C", str(repo_path), "worktree", "remove", str(worktree_path)],
            check=True,
            capture_output=True,
            text=True,
        )


class TestInitSubmodules:
    """Tests for init_submodules function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_init_submodules_with_submodules_present(self, mock_run, tmp_path):
        """Should initialize non-.github submodules individually."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create a mock .gitmodules file with 3 submodules
        worktree_path = tmp_path / "repo-branch"
        worktree_path.mkdir()
        gitmodules = worktree_path / ".gitmodules"
        gitmodules.write_text("""[submodule "sub1"]
    path = sub1
    url = https://github.com/owner/sub1.git
[submodule "sub2"]
    path = sub2
    url = https://github.com/owner/sub2.git
[submodule "sub3"]
    path = sub3
    url = https://github.com/owner/sub3.git
""")

        count = init_submodules(worktree_path)

        assert count == 3
        # Should be called once per submodule
        assert mock_run.call_count == 3
        # Check that each submodule was initialized individually
        mock_run.assert_any_call(
            [
                "git",
                "-C",
                str(worktree_path),
                "submodule",
                "update",
                "--init",
                "--recursive",
                "sub1",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_run.assert_any_call(
            [
                "git",
                "-C",
                str(worktree_path),
                "submodule",
                "update",
                "--init",
                "--recursive",
                "sub2",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_run.assert_any_call(
            [
                "git",
                "-C",
                str(worktree_path),
                "submodule",
                "update",
                "--init",
                "--recursive",
                "sub3",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_init_submodules_skips_github_submodules(self, mock_run, tmp_path):
        """Should skip .github submodules (CI/CD actions)."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create .gitmodules with mix of regular and .github submodules
        worktree_path = tmp_path / "repo-branch"
        worktree_path.mkdir()
        gitmodules = worktree_path / ".gitmodules"
        gitmodules.write_text("""[submodule "vendor/lib"]
    path = vendor/lib
    url = https://github.com/owner/lib.git
[submodule ".github/actions/setup"]
    path = .github/actions/setup
    url = https://github.com/owner/setup.git
[submodule "core/engine"]
    path = core/engine
    url = https://github.com/owner/engine.git
[submodule ".github/actions/test"]
    path = .github/actions/test
    url = https://github.com/owner/test.git
""")

        count = init_submodules(worktree_path)

        # Should only count non-.github submodules
        assert count == 2
        # Should only initialize non-.github submodules
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            [
                "git",
                "-C",
                str(worktree_path),
                "submodule",
                "update",
                "--init",
                "--recursive",
                "vendor/lib",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_run.assert_any_call(
            [
                "git",
                "-C",
                str(worktree_path),
                "submodule",
                "update",
                "--init",
                "--recursive",
                "core/engine",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_init_submodules_with_only_github_submodules(self, tmp_path):
        """Should return 0 when only .github submodules exist."""
        worktree_path = tmp_path / "repo-branch"
        worktree_path.mkdir()
        gitmodules = worktree_path / ".gitmodules"
        gitmodules.write_text("""[submodule ".github/actions/setup"]
    path = .github/actions/setup
    url = https://github.com/owner/setup.git
[submodule ".github/actions/test"]
    path = .github/actions/test
    url = https://github.com/owner/test.git
""")

        count = init_submodules(worktree_path)

        # Should return 0 since all submodules are in .github
        assert count == 0

    def test_init_submodules_with_no_gitmodules(self, tmp_path):
        """Should return 0 when .gitmodules doesn't exist."""
        worktree_path = tmp_path / "repo-branch"
        worktree_path.mkdir()

        count = init_submodules(worktree_path)

        assert count == 0

    def test_init_submodules_fails_on_unreadable_gitmodules(self, tmp_path):
        """Should raise GitOperationError when .gitmodules is unreadable."""
        worktree_path = tmp_path / "repo-branch"
        worktree_path.mkdir()

        # Create .gitmodules but make it unreadable
        gitmodules_path = worktree_path / ".gitmodules"
        gitmodules_path.write_bytes(b"\xff\xfe")  # Invalid UTF-8

        with pytest.raises(GitOperationError, match="Failed to read .gitmodules"):
            init_submodules(worktree_path)

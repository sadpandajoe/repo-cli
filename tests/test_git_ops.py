"""Tests for git_ops module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_cli.git_ops import (
    GitOperationError,
    _ensure_fetch_refspec,
    branch_exists,
    clone_bare,
    create_worktree,
    fetch_repo,
    get_default_branch,
    init_submodules,
    remove_worktree,
)


class TestCloneBare:
    """Tests for clone_bare function."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_success(self, mock_run):
        """Should run git clone --bare command and configure refspec."""
        mock_run.return_value = MagicMock(returncode=0)

        url = "git@github.com:owner/repo.git"
        target_path = Path("/tmp/test/repo.git")

        clone_bare(url, target_path)

        # Should call clone and then configure refspec
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "clone", "--bare", url, str(target_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_run.assert_any_call(
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

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_command_failure(self, mock_run):
        """Should raise GitOperationError on git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "clone"], stderr="fatal: repository not found"
        )

        with pytest.raises(GitOperationError, match="Failed to clone repository"):
            clone_bare("invalid-url", Path("/tmp/test"))

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_config_failure_after_clone(self, mock_run):
        """Should raise GitOperationError if config fails after successful clone."""
        # Clone succeeds, but config fails
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Clone succeeds
            subprocess.CalledProcessError(
                1, ["git", "config"], stderr="error: could not lock config file"
            ),
        ]

        with pytest.raises(GitOperationError, match="Failed to clone repository"):
            clone_bare("git@github.com:owner/repo.git", Path("/tmp/test/repo.git"))

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_clone_fails_no_config_attempted(self, mock_run):
        """Should not attempt config if clone fails (call count = 1)."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "clone"], stderr="fatal: repository not found"
        )

        with pytest.raises(GitOperationError):
            clone_bare("invalid-url", Path("/tmp/test"))

        # Only clone was attempted, not config
        assert mock_run.call_count == 1

    @patch("repo_cli.git_ops.subprocess.run")
    def test_clone_bare_unknown_stderr_fallback(self, mock_run):
        """Should show 'Unknown error' when clone fails with no stderr."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "clone"], stderr=None)

        with pytest.raises(GitOperationError, match="Unknown error"):
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
        # First call (symbolic-ref HEAD) fails
        # Second call (check main) fails
        # Third call (check master) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),
            subprocess.CalledProcessError(1, ["git"]),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "master"
        assert mock_run.call_count == 3

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
        """Should resolve remote HEAD to actual target branch."""
        # First call returns "refs/remotes/origin/HEAD" (remote ref)
        # Second call resolves remote HEAD to "refs/remotes/origin/develop"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="refs/remotes/origin/HEAD\n"),
            MagicMock(returncode=0, stdout="refs/remotes/origin/develop\n"),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "develop"
        assert mock_run.call_count == 2
        # Verify second call resolves the remote HEAD
        assert mock_run.call_args_list[1][0][0] == [
            "git",
            "-C",
            str(repo_path),
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
        ]

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_handles_remote_ref_resolution_failure(self, mock_run):
        """Should fallback to main/master when remote HEAD resolution fails."""
        # First call returns "refs/remotes/origin/HEAD"
        # Second call fails to resolve it
        # Third call checks for main (succeeds)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="refs/remotes/origin/HEAD\n"),
            subprocess.CalledProcessError(1, ["git"]),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "main"
        assert mock_run.call_count == 3

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_handles_custom_ref(self, mock_run):
        """Should fallback when symbolic-ref returns custom ref format."""
        # First call returns custom ref (unexpected format)
        # Second call checks for main (fails)
        # Third call checks for master (succeeds)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="refs/custom/foo\n"),
            subprocess.CalledProcessError(1, ["git"]),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        result = get_default_branch(repo_path)

        assert result == "master"
        assert mock_run.call_count == 3

    @patch("repo_cli.git_ops.subprocess.run")
    def test_get_default_branch_raises_when_no_branches_exist(self, mock_run):
        """Should raise clear error when neither main nor master exists."""
        # First call fails (symbolic-ref fails)
        # Second call checks for main (fails)
        # Third call checks for master (fails)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),
            subprocess.CalledProcessError(1, ["git"]),
            subprocess.CalledProcessError(1, ["git"]),
        ]

        repo_path = Path("/tmp/test/repo.git")

        with pytest.raises(GitOperationError) as exc_info:
            get_default_branch(repo_path)

        assert "Could not determine default branch" in str(exc_info.value)
        assert "main" in str(exc_info.value)
        assert "master" in str(exc_info.value)


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
        """Should create local branch from remote using -B when no local exists."""
        mock_branch_exists.return_value = True
        # 1. Check local branch (fails - doesn't exist)
        # 2. Check remote branch (succeeds)
        # 3. Worktree add with -B
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),  # No local branch
            MagicMock(returncode=0),  # Remote branch exists
            MagicMock(returncode=0),  # Worktree creation succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-6.0")
        branch = "6.0"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch)

        assert is_new is False
        assert actual_ref == "origin/6.0"
        mock_branch_exists.assert_called_once_with(repo_path, branch)
        assert mock_run.call_count == 3
        # First call should check for local branch
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "show-ref",
            "--verify",
            "refs/heads/6.0",
        ]
        # Second call should check for remote-tracking branch
        second_call = mock_run.call_args_list[1]
        assert second_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "show-ref",
            "--verify",
            "refs/remotes/origin/6.0",
        ]
        # Last call should use -B to create local branch from remote
        last_call = mock_run.call_args_list[-1]
        assert last_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "-B",
            "6.0",
            "origin/6.0",
        ]

    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_existing_local_only_branch(self, mock_run, mock_branch_exists):
        """Should checkout local branch directly to preserve unpushed commits."""
        mock_branch_exists.return_value = True
        # 1. Check local branch (succeeds - exists)
        # 2. Worktree add (uses local branch directly)
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Local branch exists
            MagicMock(returncode=0),  # Worktree creation succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-local-feature")
        branch = "local-feature"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch)

        assert is_new is False
        assert actual_ref == "local-feature"
        assert mock_run.call_count == 2
        # First call should check for local branch
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "show-ref",
            "--verify",
            "refs/heads/local-feature",
        ]
        # Last call should checkout local branch directly (preserves any unpushed commits)
        last_call = mock_run.call_args_list[-1]
        assert last_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "local-feature",
        ]

    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_remote_branch_worktree_add_fails(self, mock_run, mock_branch_exists):
        """Should raise GitOperationError when worktree add -B fails for remote branch."""
        mock_branch_exists.return_value = True
        # 1. Check local branch (fails - doesn't exist)
        # 2. Check remote branch (succeeds)
        # 3. Worktree add with -B (fails)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["git"]),  # No local branch
            MagicMock(returncode=0),  # Remote branch exists
            subprocess.CalledProcessError(
                1, ["git"], stderr="fatal: 'feature' is already checked out"
            ),
        ]

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-feature")
        branch = "feature"

        with pytest.raises(GitOperationError, match="Failed to create worktree"):
            create_worktree(repo_path, worktree_path, branch)

    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_both_local_and_remote_uses_local(self, mock_run, mock_branch_exists):
        """Should use local branch when both local and remote exist to preserve unpushed commits."""
        mock_branch_exists.return_value = True
        # 1. Check local branch (succeeds - exists)
        # 2. Worktree add (uses local branch directly, NOT -B with remote)
        # Note: remote check is never made because we early-return after finding local
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Local branch exists
            MagicMock(returncode=0),  # Worktree creation succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-feature")
        branch = "feature"

        actual_ref, is_new = create_worktree(repo_path, worktree_path, branch)

        assert is_new is False
        # Key assertion: returns local branch name, NOT origin/feature
        assert actual_ref == "feature"
        assert mock_run.call_count == 2
        # Last call should use local branch WITHOUT -B flag
        last_call = mock_run.call_args_list[-1]
        assert last_call[0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "add",
            str(worktree_path),
            "feature",
        ]
        # Verify -B is NOT in the command (critical - prevents data loss)
        assert "-B" not in last_call[0][0]

    @patch("repo_cli.git_ops.get_default_branch")
    @patch("repo_cli.git_ops.branch_exists")
    @patch("repo_cli.git_ops.subprocess.run")
    def test_create_worktree_new_branch_worktree_add_fails(
        self, mock_run, mock_branch_exists, mock_get_default
    ):
        """Should raise GitOperationError when worktree add -b fails for new branch."""
        mock_branch_exists.return_value = False
        mock_get_default.return_value = "main"
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git"], stderr="fatal: invalid reference: main"
        )

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-new-feature")
        branch = "new-feature"

        with pytest.raises(GitOperationError, match="Failed to create worktree"):
            create_worktree(repo_path, worktree_path, branch)

    @patch("repo_cli.git_ops.get_default_branch")
    @patch("repo_cli.git_ops.branch_exists")
    def test_create_worktree_default_branch_resolution_fails(
        self, mock_branch_exists, mock_get_default
    ):
        """Should propagate GitOperationError when get_default_branch fails."""
        mock_branch_exists.return_value = False
        mock_get_default.side_effect = GitOperationError("Could not determine default branch")

        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-new-feature")
        branch = "new-feature"

        with pytest.raises(GitOperationError, match="Could not determine default branch"):
            create_worktree(repo_path, worktree_path, branch)


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

    @patch("repo_cli.git_ops.subprocess.run")
    def test_remove_worktree_with_submodules(self, mock_run):
        """Should deinit submodules and retry with --force when submodule error occurs."""
        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-branch")

        # First call (normal remove) fails with submodule error
        # Second call (deinit) succeeds
        # Third call (remove with --force) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(
                1,
                ["git"],
                stderr="fatal: working trees containing submodules cannot be moved or removed",
            ),
            MagicMock(returncode=0),  # deinit succeeds
            MagicMock(returncode=0),  # remove --force succeeds
        ]

        remove_worktree(repo_path, worktree_path)

        # Verify all three calls
        assert mock_run.call_count == 3

        # First call: normal remove
        assert mock_run.call_args_list[0][0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "remove",
            str(worktree_path),
        ]

        # Second call: submodule deinit
        assert mock_run.call_args_list[1][0][0] == [
            "git",
            "-C",
            str(worktree_path),
            "submodule",
            "deinit",
            "--all",
            "--force",
        ]

        # Third call: remove with --force
        assert mock_run.call_args_list[2][0][0] == [
            "git",
            "-C",
            str(repo_path),
            "worktree",
            "remove",
            "--force",
            str(worktree_path),
        ]

    @patch("repo_cli.git_ops.subprocess.run")
    def test_remove_worktree_with_console_feedback(self, mock_run):
        """Should provide console feedback when submodules need deinit."""
        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-branch")

        # Mock console
        mock_console = MagicMock()

        # Setup submodule error scenario
        mock_run.side_effect = [
            subprocess.CalledProcessError(
                1,
                ["git"],
                stderr="fatal: working trees containing submodules cannot be moved or removed",
            ),
            MagicMock(returncode=0),  # deinit succeeds
            MagicMock(returncode=0),  # remove --force succeeds
        ]

        remove_worktree(repo_path, worktree_path, console=mock_console)

        # Verify console feedback
        assert mock_console.print.call_count == 2
        # First call: warning
        assert "Worktree contains submodules" in str(mock_console.print.call_args_list[0])
        # Second call: success
        assert "Submodules deinitialized" in str(mock_console.print.call_args_list[1])

    @patch("repo_cli.git_ops.subprocess.run")
    def test_remove_worktree_non_submodule_error(self, mock_run):
        """Should propagate non-submodule errors immediately."""
        repo_path = Path("/tmp/test/repo.git")
        worktree_path = Path("/tmp/test/repo-branch")

        # Fail with non-submodule error
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git"], stderr="fatal: worktree does not exist"
        )

        with pytest.raises(GitOperationError) as exc_info:
            remove_worktree(repo_path, worktree_path)

        assert "worktree does not exist" in str(exc_info.value)
        # Should only try once (no fallback for non-submodule errors)
        assert mock_run.call_count == 1


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


class TestFetchRepo:
    """Tests for fetch_repo function and refspec migration."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_fetch_repo_success(self, mock_run):
        """Should fetch and ensure refspec is configured."""
        # First call: check refspec (returns correct value)
        # Second call: fetch
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="+refs/heads/*:refs/remotes/origin/*\n"),
            MagicMock(returncode=0),
        ]

        repo_path = Path("/tmp/test/repo.git")
        fetch_repo(repo_path)

        assert mock_run.call_count == 2
        # First call checks refspec
        mock_run.assert_any_call(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.fetch"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Second call does the fetch
        mock_run.assert_any_call(
            ["git", "-C", str(repo_path), "fetch", "--prune", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_fetch_repo_migrates_missing_refspec(self, mock_run):
        """Should configure refspec if missing (pre-v0.1.2 repos)."""
        # First call: check refspec (empty/missing)
        # Second call: set refspec
        # Third call: fetch
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # No refspec configured
            MagicMock(returncode=0),  # Set refspec succeeds
            MagicMock(returncode=0),  # Fetch succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        fetch_repo(repo_path)

        assert mock_run.call_count == 3
        # Should have set the refspec
        mock_run.assert_any_call(
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

    @patch("repo_cli.git_ops.subprocess.run")
    def test_fetch_repo_failure(self, mock_run):
        """Should raise GitOperationError on fetch failure."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="+refs/heads/*:refs/remotes/origin/*\n"),
            subprocess.CalledProcessError(1, ["git"], stderr="network error"),
        ]

        with pytest.raises(GitOperationError, match="Failed to fetch repository"):
            fetch_repo(Path("/tmp/test/repo.git"))

    @patch("repo_cli.git_ops.subprocess.run")
    def test_fetch_repo_migration_fails_but_fetch_proceeds(self, mock_run):
        """Should still fetch even if migration config set fails."""
        # First call: check refspec (empty)
        # Second call: set refspec FAILS
        # Third call: fetch succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # No refspec configured
            subprocess.CalledProcessError(1, ["git"], stderr="permission denied"),  # Set fails
            MagicMock(returncode=0),  # Fetch still succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        # Should not raise - migration failure is non-fatal
        fetch_repo(repo_path)

        assert mock_run.call_count == 3
        # Fetch should still have been called
        mock_run.assert_any_call(
            ["git", "-C", str(repo_path), "fetch", "--prune", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_fetch_repo_failure_unknown_stderr(self, mock_run):
        """Should show 'Unknown error' when fetch fails with no stderr."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="+refs/heads/*:refs/remotes/origin/*\n"),
            subprocess.CalledProcessError(1, ["git"], stderr=None),
        ]

        with pytest.raises(GitOperationError, match="Unknown error"):
            fetch_repo(Path("/tmp/test/repo.git"))


class TestEnsureFetchRefspec:
    """Tests for _ensure_fetch_refspec migration helper."""

    @patch("repo_cli.git_ops.subprocess.run")
    def test_refspec_already_correct(self, mock_run):
        """Should not update if refspec is already correct."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="+refs/heads/*:refs/remotes/origin/*\n"
        )

        repo_path = Path("/tmp/test/repo.git")
        _ensure_fetch_refspec(repo_path)

        # Only one call to check, no call to set
        mock_run.assert_called_once_with(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.fetch"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("repo_cli.git_ops.subprocess.run")
    def test_refspec_missing_gets_configured(self, mock_run):
        """Should configure refspec if missing."""
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # No refspec
            MagicMock(returncode=0),  # Set succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        _ensure_fetch_refspec(repo_path)

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
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

    @patch("repo_cli.git_ops.subprocess.run")
    def test_refspec_custom_not_overwritten(self, mock_run):
        """Should NOT overwrite custom refspec (e.g., single branch)."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="+refs/heads/main:refs/remotes/origin/main\n"
        )

        repo_path = Path("/tmp/test/repo.git")
        _ensure_fetch_refspec(repo_path)

        # Only one call to check - no call to set (respects user's custom config)
        mock_run.assert_called_once()

    @patch("repo_cli.git_ops.subprocess.run")
    def test_refspec_config_failure_is_nonfatal(self, mock_run):
        """Should not raise if setting refspec fails."""
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),
            subprocess.CalledProcessError(1, ["git"], stderr="permission denied"),
        ]

        repo_path = Path("/tmp/test/repo.git")
        # Should not raise
        _ensure_fetch_refspec(repo_path)

    @patch("repo_cli.git_ops.subprocess.run")
    def test_refspec_whitespace_treated_as_missing(self, mock_run):
        """Should configure refspec if stdout is only whitespace."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="   \n"),  # Whitespace only
            MagicMock(returncode=0),  # Set succeeds
        ]

        repo_path = Path("/tmp/test/repo.git")
        _ensure_fetch_refspec(repo_path)

        # Should have called set because whitespace is treated as empty
        assert mock_run.call_count == 2

    @patch("repo_cli.git_ops.subprocess.run")
    def test_refspec_get_config_failure_is_nonfatal(self, mock_run):
        """Should not raise if get-config itself fails."""
        # CalledProcessError on the get-config call (check=False but still raises)
        mock_run.side_effect = subprocess.CalledProcessError(
            128, ["git"], stderr="fatal: not in a git directory"
        )

        repo_path = Path("/tmp/test/repo.git")
        # Should not raise - entire function is non-fatal
        _ensure_fetch_refspec(repo_path)
        assert mock_run.call_count == 1

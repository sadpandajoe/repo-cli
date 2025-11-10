"""Integration tests for CLI commands using Typer's CliRunner."""

from unittest.mock import patch

from typer.testing import CliRunner

from repo_cli import config
from repo_cli.main import app, complete_branch, complete_repo

runner = CliRunner()


class TestCliInit:
    """Integration tests for repo init command."""

    def test_init_creates_config(self, tmp_path, monkeypatch):
        """Should create config file and base directory."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        result = runner.invoke(app, ["init", "--base-dir", str(base_dir)])

        assert result.exit_code == 0
        assert "Created config at" in result.stdout
        assert "Created base directory" in result.stdout
        assert config_file.exists()
        assert base_dir.exists()

    def test_init_refuses_to_overwrite_without_force(self, tmp_path, monkeypatch):
        """Should refuse to overwrite existing config without --force."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("base_dir: ~/code\nrepos: {}\nworktrees: {}\n")

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "Config already exists" in result.stdout
        assert "--force" in result.stdout

    def test_init_with_force_overwrites(self, tmp_path, monkeypatch):
        """Should overwrite config when --force is used."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("base_dir: ~/old\nrepos: {}\nworktrees: {}\n")

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        result = runner.invoke(app, ["init", "--force"])

        assert result.exit_code == 0
        assert "Overwrote config" in result.stdout


class TestCliRegister:
    """Integration tests for repo register command."""

    def test_register_success(self, tmp_path, monkeypatch):
        """Should register a repository alias."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Register repo
        result = runner.invoke(app, ["register", "test", "git@github.com:owner/repo.git"])

        assert result.exit_code == 0
        assert "Registered 'test'" in result.stdout
        assert "GitHub repo: owner/repo" in result.stdout

    def test_register_invalid_url(self, tmp_path, monkeypatch):
        """Should reject invalid GitHub URLs."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Try to register with invalid URL
        result = runner.invoke(app, ["register", "test", "not-a-valid-url"])

        assert result.exit_code == 1
        assert "Invalid GitHub URL" in result.stdout

    def test_register_path_traversal_blocked(self, tmp_path, monkeypatch):
        """Should block path traversal attempts in alias."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Try to register with path traversal alias
        result = runner.invoke(app, ["register", "../prod", "git@github.com:owner/repo.git"])

        assert result.exit_code == 1
        assert "Invalid identifier" in result.stdout

    def test_register_duplicate_without_force_blocked(self, tmp_path, monkeypatch):
        """Should block duplicate registration without --force."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Register repo
        runner.invoke(app, ["register", "test", "git@github.com:owner/repo.git"])

        # Try to register again with different URL
        result = runner.invoke(app, ["register", "test", "git@github.com:owner/other.git"])

        assert result.exit_code == 1
        assert "already registered" in result.stdout
        assert "--force" in result.stdout

    def test_register_duplicate_with_force_allowed(self, tmp_path, monkeypatch):
        """Should allow duplicate registration with --force."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Register repo
        runner.invoke(app, ["register", "test", "git@github.com:owner/repo.git"])

        # Register again with --force
        result = runner.invoke(
            app, ["register", "test", "git@github.com:owner/other.git", "--force"]
        )

        assert result.exit_code == 0
        assert "Overwriting" in result.stdout
        assert "Registered 'test'" in result.stdout

        # Verify the URL was updated
        cfg = config.load_config()
        assert cfg["repos"]["test"]["url"] == "git@github.com:owner/other.git"


class TestCliCreate:
    """Integration tests for repo create command."""

    def test_create_prompts_on_fetch_failure_and_cancels(self, tmp_path, monkeypatch):
        """Should prompt user when fetch fails and allow cancellation."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize and register repo
        runner.invoke(app, ["init", "--base-dir", str(base_dir)])
        runner.invoke(app, ["register", "test", "git@github.com:owner/repo.git"])

        # Create bare repo directory to simulate existing repo
        bare_repo = base_dir / "test.git"
        bare_repo.mkdir(parents=True)

        # Mock fetch_repo to raise GitOperationError
        from repo_cli.git_ops import GitOperationError

        with patch("repo_cli.git_ops.fetch_repo") as mock_fetch:
            mock_fetch.side_effect = GitOperationError("Network timeout")

            # User responds "no" to prompt
            result = runner.invoke(app, ["create", "test", "feature-123"], input="n\n")

            assert result.exit_code == 0
            assert "Failed to fetch from remote" in result.stdout
            assert "Branch information may be stale" in result.stdout
            assert "diverged branch" in result.stdout
            assert "Cancelled" in result.stdout

    def test_create_prompts_on_fetch_failure_and_continues(self, tmp_path, monkeypatch):
        """Should prompt user when fetch fails and allow continuation."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize and register repo
        runner.invoke(app, ["init", "--base-dir", str(base_dir)])
        runner.invoke(app, ["register", "test", "git@github.com:owner/repo.git"])

        # Create bare repo directory to simulate existing repo
        bare_repo = base_dir / "test.git"
        bare_repo.mkdir(parents=True)

        # Mock git operations
        from repo_cli.git_ops import GitOperationError

        with (
            patch("repo_cli.git_ops.fetch_repo") as mock_fetch,
            patch("repo_cli.git_ops.create_worktree") as mock_create,
            patch("repo_cli.git_ops.init_submodules") as mock_submodules,
        ):
            mock_fetch.side_effect = GitOperationError("Network timeout")
            mock_create.return_value = ("origin/HEAD", True)
            mock_submodules.return_value = 0

            # User responds "yes" to prompt
            result = runner.invoke(app, ["create", "test", "feature-123"], input="y\n")

            assert result.exit_code == 0
            assert "Failed to fetch from remote" in result.stdout
            assert "Do you want to create the branch anyway?" in result.stdout
            assert "Created worktree" in result.stdout


class TestCliList:
    """Integration tests for repo list command."""

    def test_list_empty_shows_helpful_message(self, tmp_path, monkeypatch):
        """Should show helpful message when no worktrees exist."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize
        runner.invoke(app, ["init"])

        # List (should be empty)
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No worktrees found" in result.stdout
        assert "repo create" in result.stdout

    def test_list_with_filter_no_matches(self, tmp_path, monkeypatch):
        """Should show friendly message when filtered list is empty."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize
        runner.invoke(app, ["init"])

        # Manually add a worktree to config
        import yaml

        with open(config_file) as f:
            cfg = yaml.safe_load(f)

        cfg["worktrees"] = {
            "preset-feature-123": {
                "repo": "preset",
                "branch": "feature-123",
                "pr": None,
                "start_point": "origin/HEAD",
            }
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(cfg, f)

        # List with filter that doesn't match
        result = runner.invoke(app, ["list", "nonexistent"])

        assert result.exit_code == 0
        assert "No worktrees found for 'nonexistent'" in result.stdout


class TestCliPrLink:
    """Integration tests for repo pr link command."""

    @patch("repo_cli.gh_ops.is_gh_available")
    def test_pr_link_success(self, mock_gh_available, tmp_path, monkeypatch):
        """Should link PR to worktree."""
        mock_gh_available.return_value = False  # Avoid actual gh calls
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize
        runner.invoke(app, ["init"])

        # Manually add a worktree to config
        import yaml

        with open(config_file) as f:
            cfg = yaml.safe_load(f)

        cfg["repos"] = {
            "test": {"url": "git@github.com:owner/repo.git", "owner_repo": "owner/repo"}
        }
        cfg["worktrees"] = {
            "test-feature": {
                "repo": "test",
                "branch": "feature",
                "pr": None,
                "start_point": "origin/HEAD",
            }
        }

        with open(config_file, "w") as f:
            yaml.safe_dump(cfg, f)

        # Link PR
        result = runner.invoke(app, ["pr", "link", "test", "feature", "123"])

        assert result.exit_code == 0
        assert "Linked PR #123 to test-feature" in result.stdout

    def test_pr_link_worktree_not_found(self, tmp_path, monkeypatch):
        """Should error when worktree doesn't exist."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize
        runner.invoke(app, ["init"])

        # Try to link PR to non-existent worktree
        result = runner.invoke(app, ["pr", "link", "test", "feature", "123"])

        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestAutoComplete:
    """Tests for auto-complete functionality."""

    def test_complete_repo_returns_all_repos(self, tmp_path, monkeypatch):
        """Should return all registered repo aliases."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with repos
        cfg = {
            "base_dir": "~/code",
            "repos": {
                "preset": {
                    "url": "git@github.com:preset-io/preset.git",
                    "owner_repo": "preset-io/preset",
                },
                "superset": {
                    "url": "git@github.com:apache/superset.git",
                    "owner_repo": "apache/superset",
                },
                "manager": {
                    "url": "git@github.com:preset-io/manager.git",
                    "owner_repo": "preset-io/manager",
                },
            },
            "worktrees": {},
        }
        config.save_config(cfg)

        # Get completions
        completions = complete_repo()

        assert completions == ["preset", "superset", "manager"]

    def test_complete_repo_filters_by_incomplete(self, tmp_path, monkeypatch):
        """Should filter repos by incomplete string."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with repos
        cfg = {
            "base_dir": "~/code",
            "repos": {
                "preset": {
                    "url": "git@github.com:preset-io/preset.git",
                    "owner_repo": "preset-io/preset",
                },
                "preset-manager": {
                    "url": "git@github.com:preset-io/manager.git",
                    "owner_repo": "preset-io/manager",
                },
                "superset": {
                    "url": "git@github.com:apache/superset.git",
                    "owner_repo": "apache/superset",
                },
            },
            "worktrees": {},
        }
        config.save_config(cfg)

        # Get completions for "pre"
        completions = complete_repo(incomplete="pre")

        assert "preset" in completions
        assert "preset-manager" in completions
        assert "superset" not in completions

    def test_complete_repo_returns_empty_when_no_config(self, tmp_path, monkeypatch):
        """Should return empty list when config doesn't exist."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # No config exists
        completions = complete_repo()

        assert completions == []

    def test_complete_branch_returns_all_branches(self, tmp_path, monkeypatch):
        """Should return all branch names."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with worktrees
        cfg = {
            "base_dir": "~/code",
            "repos": {},
            "worktrees": {
                "preset-feature-123": {
                    "repo": "preset",
                    "branch": "feature-123",
                    "pr": None,
                    "start_point": "origin/HEAD",
                },
                "preset-bugfix-456": {
                    "repo": "preset",
                    "branch": "bugfix-456",
                    "pr": None,
                    "start_point": "origin/HEAD",
                },
                "superset-main": {
                    "repo": "superset",
                    "branch": "main",
                    "pr": None,
                    "start_point": "origin/HEAD",
                },
            },
        }
        config.save_config(cfg)

        # Get completions - returns all branches
        completions = complete_branch()

        assert "feature-123" in completions
        assert "bugfix-456" in completions
        assert "main" in completions

    def test_complete_branch_filters_by_incomplete(self, tmp_path, monkeypatch):
        """Should filter branches by incomplete string."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with worktrees
        cfg = {
            "base_dir": "~/code",
            "repos": {},
            "worktrees": {
                "preset-feature-123": {
                    "repo": "preset",
                    "branch": "feature-123",
                    "pr": None,
                    "start_point": "origin/HEAD",
                },
                "preset-feature-456": {
                    "repo": "preset",
                    "branch": "feature-456",
                    "pr": None,
                    "start_point": "origin/HEAD",
                },
                "preset-bugfix-789": {
                    "repo": "preset",
                    "branch": "bugfix-789",
                    "pr": None,
                    "start_point": "origin/HEAD",
                },
            },
        }
        config.save_config(cfg)

        # Get completions for "feat"
        completions = complete_branch(incomplete="feat")

        assert "feature-123" in completions
        assert "feature-456" in completions
        assert "bugfix-789" not in completions

    def test_complete_branch_returns_empty_when_no_config(self, tmp_path, monkeypatch):
        """Should return empty list when config doesn't exist."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # No config exists
        completions = complete_branch()

        assert completions == []

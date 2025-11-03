"""Integration tests for CLI commands using Typer's CliRunner."""

from unittest.mock import patch

from typer.testing import CliRunner

from repo_cli.main import app

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

        cfg["repos"] = {"test": {"url": "git@github.com:owner/repo.git", "owner_repo": "owner/repo"}}
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

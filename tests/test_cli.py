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
        """Should reject invalid git URLs."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Try to register with invalid URL
        result = runner.invoke(app, ["register", "test", "not-a-valid-url"])

        assert result.exit_code == 1
        assert "Invalid git URL format" in result.stdout

    def test_register_path_traversal_blocked(self, tmp_path, monkeypatch):
        """Should block path traversal attempts in alias."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Initialize first
        runner.invoke(app, ["init"])

        # Try to register with path traversal alias
        result = runner.invoke(app, ["register", "../prod", "git@github.com:owner/repo.git"])

        assert result.exit_code == 1
        assert "Invalid repo alias" in result.stdout

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
            "test::feature": {
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
        assert "Linked PR #123 to test/feature" in result.stdout

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


class TestCliActivate:
    """Tests for repo activate command."""

    def test_activate_normal_mode(self, tmp_path, monkeypatch):
        """Should show formatted output with cd hint."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"
        worktree_path = base_dir / "myrepo-main"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with worktree
        cfg = {
            "base_dir": str(base_dir),
            "repos": {},
            "worktrees": {
                "myrepo::main": {
                    "repo": "myrepo",
                    "branch": "main",
                    "pr": None,
                    "start_point": "origin/HEAD",
                }
            },
        }
        config.save_config(cfg)

        # Create worktree directory
        worktree_path.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(app, ["activate", "myrepo", "main"])

        assert result.exit_code == 0
        assert "Worktree path:" in result.stdout
        assert "main" in result.stdout  # Check path component is present

    def test_activate_print_mode(self, tmp_path, monkeypatch):
        """Should print path only for shell integration."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"
        worktree_path = base_dir / "myrepo-feature"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with worktree
        cfg = {
            "base_dir": str(base_dir),
            "repos": {},
            "worktrees": {
                "myrepo::feature": {
                    "repo": "myrepo",
                    "branch": "feature",
                    "pr": None,
                    "start_point": "origin/HEAD",
                }
            },
        }
        config.save_config(cfg)

        # Create worktree directory
        worktree_path.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(app, ["activate", "myrepo", "feature", "--print"])

        assert result.exit_code == 0
        assert "myrepo-feature" in result.stdout
        assert "Worktree path:" not in result.stdout  # Should be plain output

    def test_activate_worktree_not_found(self, tmp_path, monkeypatch):
        """Should error when worktree doesn't exist in config."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config without worktree
        cfg = {"base_dir": str(base_dir), "repos": {}, "worktrees": {}}
        config.save_config(cfg)

        result = runner.invoke(app, ["activate", "myrepo", "main"])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_activate_directory_missing(self, tmp_path, monkeypatch):
        """Should error when worktree directory doesn't exist on filesystem."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config with worktree but don't create directory
        cfg = {
            "base_dir": str(base_dir),
            "repos": {},
            "worktrees": {
                "myrepo::main": {
                    "repo": "myrepo",
                    "branch": "main",
                    "pr": None,
                    "start_point": "origin/HEAD",
                }
            },
        }
        config.save_config(cfg)

        result = runner.invoke(app, ["activate", "myrepo", "main"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestCliDoctor:
    """Tests for repo doctor command."""

    def test_doctor_with_valid_config(self, tmp_path, monkeypatch):
        """Should pass all checks with valid config."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Create config and base directory
        cfg = {"base_dir": str(base_dir), "repos": {}, "worktrees": {}}
        config.save_config(cfg)
        base_dir.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "repo-cli Doctor" in result.stdout
        assert "Checking Git version" in result.stdout

    def test_doctor_without_config(self, tmp_path, monkeypatch):
        """Should still run checks even without config."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # No config exists
        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "repo-cli Doctor" in result.stdout
        assert "Checking Git version" in result.stdout


class TestCliUpgradeCheck:
    """Tests for repo upgrade-check command."""

    def test_upgrade_check_not_git_repo(self, tmp_path, monkeypatch):
        """Should error when not installed from git."""
        # Mock __file__ to point to a non-git directory
        import repo_cli

        fake_install = tmp_path / "fake-install" / "repo_cli" / "__init__.py"
        fake_install.parent.mkdir(parents=True)
        fake_install.touch()

        monkeypatch.setattr(repo_cli, "__file__", str(fake_install))

        result = runner.invoke(app, ["upgrade-check"])

        assert result.exit_code == 1
        assert "Not installed from git" in result.stdout

    def test_upgrade_check_with_git_repo(self, tmp_path, monkeypatch):
        """Should check for updates in git repo."""
        import repo_cli

        # Create fake git installation
        fake_install = tmp_path / "fake-install"
        fake_git = fake_install / ".git"
        fake_git.mkdir(parents=True)

        fake_module = fake_install / "src" / "repo_cli" / "__init__.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.touch()

        monkeypatch.setattr(repo_cli, "__file__", str(fake_module))

        # Mock git operations
        with (
            patch("repo_cli.git_ops.get_current_branch") as mock_branch,
            patch("repo_cli.git_ops.has_uncommitted_changes") as mock_changes,
            patch("repo_cli.git_ops.get_latest_tag") as mock_tag,
        ):
            mock_branch.return_value = "main"
            mock_changes.return_value = False
            mock_tag.return_value = None  # No tags

            result = runner.invoke(app, ["upgrade-check"])

            assert result.exit_code == 0
            assert "Checking for updates" in result.stdout
            assert "No version tags found" in result.stdout


class TestE2EWorkflow:
    """End-to-end workflow test simulating fresh installation."""

    def test_complete_workflow_from_fresh_install(self, tmp_path, monkeypatch):
        """Test complete workflow: init -> register -> create -> list -> activate -> delete."""
        # Setup paths
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"
        bare_repo_path = base_dir / "testapp.git"
        worktree_path = base_dir / "testapp-feature-100"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Step 1: Initialize (fresh install)
        result = runner.invoke(app, ["init", "--base-dir", str(base_dir)])
        assert result.exit_code == 0
        assert "Created config at" in result.stdout
        assert config_file.exists()
        assert base_dir.exists()

        # Step 2: Register a repository
        result = runner.invoke(app, ["register", "testapp", "git@github.com:user/testapp.git"])
        assert result.exit_code == 0
        assert "Registered 'testapp'" in result.stdout

        # Step 3: Create a worktree (this clones the bare repo if needed)
        with (
            patch("repo_cli.git_ops.clone_bare") as mock_clone,
            patch("repo_cli.git_ops.get_default_branch") as mock_default,
            patch("repo_cli.git_ops.branch_exists") as mock_exists,
            patch("repo_cli.git_ops.create_worktree") as mock_create,
            patch("repo_cli.git_ops.init_submodules") as mock_submodules,
            patch("repo_cli.git_ops.fetch_repo") as mock_fetch,
        ):
            mock_clone.return_value = None
            mock_default.return_value = "main"
            mock_exists.return_value = False
            mock_create.return_value = ("origin/main", True)  # (actual_ref, is_new_branch)
            mock_submodules.return_value = None
            mock_fetch.return_value = None
            bare_repo_path.mkdir(parents=True, exist_ok=True)
            worktree_path.mkdir(parents=True, exist_ok=True)

            result = runner.invoke(app, ["create", "testapp", "feature-100"])
            assert result.exit_code == 0
            assert "Created worktree:" in result.stdout
            assert "feature-100" in result.stdout

        # Verify worktree was added to config
        cfg = config.load_config()
        assert "testapp::feature-100" in cfg.get("worktrees", {})

        # Step 4: List worktrees
        with (
            patch("repo_cli.gh_ops.is_gh_available") as mock_gh_available,
            patch("repo_cli.gh_ops.get_pr_status") as mock_pr_status,
        ):
            mock_gh_available.return_value = False
            mock_pr_status.return_value = "open"

            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "testapp" in result.stdout
            assert "feature-100" in result.stdout

        # Step 5: Activate worktree (test both modes)
        # Test normal mode
        result = runner.invoke(app, ["activate", "testapp", "feature-100"])
        assert result.exit_code == 0
        assert "Worktree path:" in result.stdout
        # Check that worktree path components appear (removing newlines for Rich formatting)
        output_normalized = result.stdout.replace("\n", "")
        assert "testapp" in output_normalized
        assert "feature-100" in output_normalized

        # Test print-only mode
        result = runner.invoke(app, ["activate", "testapp", "feature-100", "--print"])
        assert result.exit_code == 0
        # For --print mode, output should be plain path (may still have newlines in CI)
        output_normalized = result.stdout.replace("\n", "")
        assert "testapp" in output_normalized
        assert "feature-100" in output_normalized
        assert "Worktree path:" not in result.stdout  # Should be plain output

        # Step 6: Link a PR
        with (
            patch("repo_cli.gh_ops.is_gh_available") as mock_gh_available,
            patch("repo_cli.gh_ops.validate_pr_exists") as mock_validate,
            patch("repo_cli.gh_ops.get_pr_status") as mock_pr_status,
        ):
            mock_gh_available.return_value = True
            mock_validate.return_value = True
            mock_pr_status.return_value = "open"

            result = runner.invoke(app, ["pr", "link", "testapp", "feature-100", "123"])
            assert result.exit_code == 0
            assert "Linked PR #123" in result.stdout

        # Step 7: Verify PR appears in list
        with (
            patch("repo_cli.gh_ops.is_gh_available") as mock_gh_available,
            patch("repo_cli.gh_ops.get_pr_status") as mock_pr_status,
        ):
            mock_gh_available.return_value = True
            mock_pr_status.return_value = "open"

            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "123" in result.stdout

        # Step 8: Delete worktree
        with patch("repo_cli.git_ops.remove_worktree") as mock_remove:
            mock_remove.return_value = None

            result = runner.invoke(app, ["delete", "testapp", "feature-100", "--force"])
            assert result.exit_code == 0
            assert "Removed worktree:" in result.stdout

        # Step 9: Verify worktree is gone
        with (
            patch("repo_cli.gh_ops.is_gh_available") as mock_gh_available,
            patch("repo_cli.gh_ops.get_pr_status") as mock_pr_status,
        ):
            mock_gh_available.return_value = False
            mock_pr_status.return_value = "open"

            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            # Should show helpful message when empty
            assert "No worktrees" in result.stdout or "testapp" not in result.stdout

    def test_version_and_doctor_commands(self, tmp_path, monkeypatch):
        """Test diagnostic commands work correctly."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        base_dir = tmp_path / "code"

        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Test --version flag
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "repo-cli version" in result.stdout

        # Test doctor command (without full config)
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "repo-cli Doctor" in result.stdout
        assert "Checking Git version" in result.stdout

        # Initialize config first
        result = runner.invoke(app, ["init", "--base-dir", str(base_dir)])
        assert result.exit_code == 0

        # Test doctor with config
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Config found at" in result.stdout

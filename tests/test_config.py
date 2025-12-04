"""Tests for config module."""

import os
import tempfile
from pathlib import Path

import pytest

from repo_cli.config import load_config, migrate_config, parse_github_url, save_config


class TestParseGitHubUrl:
    """Tests for parse_github_url function."""

    def test_parse_ssh_url(self):
        """Should parse SSH format git URLs."""
        url = "git@github.com:owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo == "owner/repo"

    def test_parse_https_url(self):
        """Should parse HTTPS format git URLs."""
        url = "https://github.com/owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo == "owner/repo"

    def test_parse_ssh_url_without_git_extension(self):
        """Should parse SSH URLs without .git extension."""
        url = "git@github.com:owner/repo"
        owner_repo = parse_github_url(url)
        assert owner_repo == "owner/repo"

    def test_parse_https_url_without_git_extension(self):
        """Should parse HTTPS URLs without .git extension."""
        url = "https://github.com/owner/repo"
        owner_repo = parse_github_url(url)
        assert owner_repo == "owner/repo"

    def test_parse_url_with_hyphens_and_underscores(self):
        """Should handle repo names with hyphens and underscores."""
        url = "git@github.com:my-org/my_repo-name.git"
        owner_repo = parse_github_url(url)
        assert owner_repo == "my-org/my_repo-name"

    def test_parse_invalid_url_raises_error(self):
        """Should raise ValueError for invalid URLs."""
        with pytest.raises(ValueError, match="Invalid git URL format"):
            parse_github_url("not-a-valid-url")

    def test_parse_github_enterprise_ssh(self):
        """Should parse GitHub Enterprise SSH URLs."""
        url = "git@github.enterprise.com:owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo == "owner/repo"

    def test_parse_github_enterprise_https(self):
        """Should parse GitHub Enterprise HTTPS URLs."""
        url = "https://github.mycompany.com/owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo == "owner/repo"

    def test_parse_gitlab_url_graceful_degradation(self):
        """Should return None for GitLab URLs (graceful degradation)."""
        url = "https://gitlab.com/owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo is None

    def test_parse_bitbucket_url_graceful_degradation(self):
        """Should return None for Bitbucket URLs (graceful degradation)."""
        url = "git@bitbucket.org:owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo is None

    def test_parse_self_hosted_url_graceful_degradation(self):
        """Should return None for self-hosted git URLs (graceful degradation)."""
        url = "git@git.mycompany.com:owner/repo.git"
        owner_repo = parse_github_url(url)
        assert owner_repo is None

    def test_parse_non_github_url_with_require_github_raises(self):
        """Should raise ValueError for non-GitHub URLs when require_github=True."""
        with pytest.raises(ValueError, match="URL is not a GitHub URL"):
            parse_github_url("https://gitlab.com/owner/repo.git", require_github=True)

    def test_parse_invalid_url_with_require_github_raises(self):
        """Should raise ValueError for invalid URLs when require_github=True."""
        with pytest.raises(ValueError, match="Invalid GitHub URL format"):
            parse_github_url("not-a-valid-url", require_github=True)


class TestConfigLoadSave:
    """Tests for load_config and save_config functions."""

    def test_save_config_creates_directory(self, tmp_path, monkeypatch):
        """Should create config directory if it doesn't exist."""
        config_dir = tmp_path / ".repo-cli"
        config_file = config_dir / "config.yaml"

        # Mock get_config_path to use temp directory
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}
        save_config(config)

        assert config_dir.exists()
        assert config_file.exists()

    def test_save_and_load_config_roundtrip(self, tmp_path, monkeypatch):
        """Should save and load config correctly."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        original_config = {
            "base_dir": "~/code",
            "repos": {
                "preset": {
                    "url": "git@github.com:preset-io/preset.git",
                    "owner_repo": "preset-io/preset",
                }
            },
            "worktrees": {
                "preset::feature-123": {"repo": "preset", "branch": "feature-123", "pr": 4567}
            },
        }

        save_config(original_config)
        loaded_config = load_config()

        assert loaded_config == original_config

    def test_load_config_missing_file_raises_error(self, tmp_path, monkeypatch):
        """Should raise FileNotFoundError when config doesn't exist."""
        config_file = tmp_path / "nonexistent" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        with pytest.raises(FileNotFoundError):
            load_config()

    def test_save_config_with_nested_structures(self, tmp_path, monkeypatch):
        """Should handle nested dictionaries and lists."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        config = {
            "base_dir": "~/code",
            "repos": {
                "test": {
                    "url": "https://github.com/test/repo.git",
                    "owner_repo": "test/repo",
                    "metadata": {"tags": ["python", "cli"], "stars": 100},
                }
            },
        }

        save_config(config)
        loaded = load_config()

        assert loaded["repos"]["test"]["metadata"]["tags"] == ["python", "cli"]
        assert loaded["repos"]["test"]["metadata"]["stars"] == 100


class TestAtomicConfigWrites:
    """Tests for atomic config write operations."""

    def test_save_config_uses_atomic_write(self, tmp_path, monkeypatch):
        """Should use temp file + os.replace for atomic writes."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}

        # Track calls to os.replace
        replace_calls = []
        original_replace = os.replace

        def mock_replace(src, dst):
            replace_calls.append((src, dst))
            return original_replace(src, dst)

        monkeypatch.setattr("os.replace", mock_replace)

        save_config(config)

        # Verify atomic write happened
        assert len(replace_calls) == 1
        src, dst = replace_calls[0]
        assert str(dst) == str(config_file)  # Handle both Path and str
        assert str(src) != str(config_file)  # Temp file, not direct write
        assert ".config." in str(src)  # Temp file prefix
        assert ".yaml.tmp" in str(src)  # Temp file suffix

    def test_save_config_cleans_up_temp_file_on_error(self, tmp_path, monkeypatch):
        """Should remove temp file if write fails."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}

        # Make yaml.safe_dump fail
        def mock_dump(*args, **kwargs):
            raise ValueError("Simulated write error")

        monkeypatch.setattr("yaml.safe_dump", mock_dump)

        # Should raise error
        with pytest.raises(ValueError):
            save_config(config)

        # Verify no temp files left behind
        temp_files = list(config_file.parent.glob(".config.*.yaml.tmp"))
        assert len(temp_files) == 0

    def test_save_config_calls_fsync(self, tmp_path, monkeypatch):
        """Should call fsync to ensure data written to disk."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}

        # Track fsync calls
        fsync_calls = []
        original_fsync = os.fsync

        def mock_fsync(fd):
            fsync_calls.append(fd)
            return original_fsync(fd)

        monkeypatch.setattr("os.fsync", mock_fsync)

        save_config(config)

        # Verify fsync was called
        assert len(fsync_calls) == 1

    def test_save_config_temp_file_in_same_directory(self, tmp_path, monkeypatch):
        """Should create temp file in same directory as target (required for atomic replace)."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}

        # Track temp file location
        temp_file_paths = []
        original_mkstemp = tempfile.mkstemp

        def mock_mkstemp(*args, **kwargs):
            result = original_mkstemp(*args, **kwargs)
            temp_file_paths.append(result[1])
            return result

        monkeypatch.setattr("tempfile.mkstemp", mock_mkstemp)

        save_config(config)

        # Verify temp file was in same directory as config
        assert len(temp_file_paths) == 1
        temp_path = Path(temp_file_paths[0])
        assert temp_path.parent == config_file.parent


class TestMigrateConfig:
    """Tests for migrate_config function."""

    def test_migrate_old_format_to_new(self):
        """Should migrate worktree keys from old format (repo-branch) to new (repo::branch)."""
        old_config = {
            "base_dir": "~/code",
            "repos": {"superset": {"url": "https://github.com/apache/superset.git"}},
            "worktrees": {
                "superset-6.0": {"repo": "superset", "branch": "6.0", "pr": None},
                "superset-test-feature": {"repo": "superset", "branch": "test-feature", "pr": 123},
            },
        }

        migrated, changed = migrate_config(old_config)

        # Should have new format keys
        assert "superset::6.0" in migrated["worktrees"]
        assert "superset::test-feature" in migrated["worktrees"]

        # Old keys should be replaced
        assert "superset-6.0" not in migrated["worktrees"]
        assert "superset-test-feature" not in migrated["worktrees"]

        # Data should be preserved
        assert migrated["worktrees"]["superset::6.0"]["repo"] == "superset"
        assert migrated["worktrees"]["superset::6.0"]["branch"] == "6.0"
        assert migrated["worktrees"]["superset::test-feature"]["pr"] == 123

        # Version should be added
        assert migrated["version"] == "0.1.0"

        # Should report change
        assert changed is True

    def test_migrate_already_new_format(self):
        """Should leave new format keys unchanged."""
        new_config = {
            "base_dir": "~/code",
            "repos": {"preset": {"url": "git@github.com:preset-io/preset.git"}},
            "worktrees": {
                "preset::feature-123": {"repo": "preset", "branch": "feature-123", "pr": 4567}
            },
        }

        migrated, changed = migrate_config(new_config)

        # Should keep new format
        assert "preset::feature-123" in migrated["worktrees"]
        assert migrated["worktrees"]["preset::feature-123"]["pr"] == 4567

        # No version added (already in correct format)
        assert "version" not in migrated

        # Should not report change
        assert changed is False

    def test_migrate_mixed_formats(self):
        """Should handle mix of old and new format keys."""
        mixed_config = {
            "base_dir": "~/code",
            "repos": {},
            "worktrees": {
                "superset-6.0": {"repo": "superset", "branch": "6.0", "pr": None},
                "preset::feature-123": {"repo": "preset", "branch": "feature-123", "pr": 4567},
            },
        }

        migrated, changed = migrate_config(mixed_config)

        # Old format should be migrated
        assert "superset::6.0" in migrated["worktrees"]
        assert "superset-6.0" not in migrated["worktrees"]

        # New format should be preserved
        assert "preset::feature-123" in migrated["worktrees"]

        # Version should be added (migration occurred)
        assert migrated["version"] == "0.1.0"

        # Should report change
        assert changed is True

    def test_migrate_empty_worktrees(self):
        """Should handle config with no worktrees."""
        empty_config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}

        migrated, changed = migrate_config(empty_config)

        assert migrated["worktrees"] == {}
        assert "version" not in migrated
        assert changed is False

    def test_migrate_no_worktrees_key(self):
        """Should handle config without worktrees key."""
        minimal_config = {"base_dir": "~/code", "repos": {}}

        migrated, changed = migrate_config(minimal_config)

        # Should not add worktrees or version if not present
        assert "worktrees" not in migrated
        assert "version" not in migrated
        assert changed is False

    def test_migrate_malformed_entry(self):
        """Should preserve malformed entries as-is."""
        malformed_config = {
            "base_dir": "~/code",
            "repos": {},
            "worktrees": {
                "invalid-entry": "not a dict",  # Malformed
                "superset-6.0": {"repo": "superset", "branch": "6.0", "pr": None},
            },
        }

        migrated, changed = migrate_config(malformed_config)

        # Malformed entry should be kept as-is
        assert "invalid-entry" in migrated["worktrees"]
        assert migrated["worktrees"]["invalid-entry"] == "not a dict"

        # Valid entry should be migrated
        assert "superset::6.0" in migrated["worktrees"]
        assert "superset-6.0" not in migrated["worktrees"]

        # Should report change (valid entry was migrated)
        assert changed is True

    def test_migrate_preserves_version(self):
        """Should preserve existing version field."""
        config_with_version = {
            "base_dir": "~/code",
            "repos": {},
            "worktrees": {"superset-6.0": {"repo": "superset", "branch": "6.0", "pr": None}},
            "version": "0.0.9",  # Existing version
        }

        migrated, changed = migrate_config(config_with_version)

        # Version should be preserved (setdefault doesn't override)
        assert migrated["version"] == "0.0.9"

        # Should report change
        assert changed is True

    def test_load_config_triggers_migration(self, tmp_path, monkeypatch):
        """Should automatically migrate config when loading."""
        config_file = tmp_path / ".repo-cli" / "config.yaml"
        monkeypatch.setattr("repo_cli.config.get_config_path", lambda: config_file)

        # Save old format config
        old_config = {
            "base_dir": "~/code",
            "repos": {"superset": {"url": "https://github.com/apache/superset.git"}},
            "worktrees": {
                "superset-6.0": {"repo": "superset", "branch": "6.0", "pr": None},
            },
        }
        save_config(old_config)

        # Load should trigger migration
        loaded = load_config()

        # Should have migrated format
        assert "superset::6.0" in loaded["worktrees"]
        assert "superset-6.0" not in loaded["worktrees"]
        assert loaded["version"] == "0.1.0"

        # Migration should be persisted to disk
        reloaded = load_config()
        assert "superset::6.0" in reloaded["worktrees"]
        assert reloaded["version"] == "0.1.0"


class TestMigrateWorktreePaths:
    """Test worktree path migration from __ to percent-encoding."""

    def test_migrate_slash_to_percent_encoding(self, tmp_path):
        """Should rename directories from __ format to percent-encoding."""
        base_dir = tmp_path / "code"
        base_dir.mkdir(parents=True)

        config = {
            "base_dir": str(base_dir),
            "worktrees": {
                "preset::feature/JIRA-123": {
                    "repo": "preset",
                    "branch": "feature/JIRA-123",
                    "pr": None,
                },
            },
        }

        from repo_cli.config import migrate_worktree_paths

        # Create bare repo for git worktree move to work
        bare_repo = base_dir / "preset.git"
        bare_repo.mkdir()
        # Initialize as bare git repo
        import subprocess

        subprocess.run(["git", "init", "--bare", str(bare_repo)], check=True, capture_output=True)
        # Create initial commit (required for worktree operations)
        temp_clone = base_dir / "temp"
        subprocess.run(
            ["git", "clone", str(bare_repo), str(temp_clone)], check=True, capture_output=True
        )
        # Configure git identity for CI
        subprocess.run(
            ["git", "-C", str(temp_clone), "config", "user.name", "Test User"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(temp_clone), "config", "user.email", "test@example.com"],
            check=True,
            capture_output=True,
        )
        (temp_clone / "README.md").write_text("test")
        subprocess.run(["git", "-C", str(temp_clone), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(temp_clone), "commit", "-m", "init"], check=True, capture_output=True
        )
        subprocess.run(["git", "-C", str(temp_clone), "push"], check=True, capture_output=True)
        # Create old-format worktree using git
        old_path = base_dir / "preset-feature__JIRA-123"
        subprocess.run(
            ["git", "-C", str(bare_repo), "worktree", "add", str(old_path), "--detach"],
            check=True,
            capture_output=True,
        )
        # Add test file to the worktree
        (old_path / "test.txt").write_text("test content")

        migrated, changed = migrate_worktree_paths(config)

        # Old path should be renamed to new path
        new_path = base_dir / "preset-feature%2FJIRA-123"
        assert new_path.exists()
        assert not old_path.exists()
        assert (new_path / "test.txt").read_text() == "test content"

        # Config should be unchanged
        assert migrated == config

        # Should report change
        assert changed is True

    def test_migrate_no_special_chars(self, tmp_path):
        """Should skip branches without special characters."""
        base_dir = tmp_path / "code"
        base_dir.mkdir(parents=True)

        # Create directory with no special chars
        simple_path = base_dir / "preset-main"
        simple_path.mkdir()

        config = {
            "base_dir": str(base_dir),
            "worktrees": {
                "preset::main": {
                    "repo": "preset",
                    "branch": "main",
                    "pr": None,
                },
            },
        }

        from repo_cli.config import migrate_worktree_paths

        migrate_worktree_paths(config)

        # Path should remain unchanged
        assert simple_path.exists()

    def test_migrate_multiple_worktrees(self, tmp_path):
        """Should migrate multiple worktrees."""
        base_dir = tmp_path / "code"
        base_dir.mkdir(parents=True)

        # Create bare repos and old-format worktrees
        import subprocess

        old_paths = []
        for repo_name, branch in [("preset", "feature/foo"), ("superset", "bugfix/bar")]:
            bare_repo = base_dir / f"{repo_name}.git"
            bare_repo.mkdir()
            subprocess.run(
                ["git", "init", "--bare", str(bare_repo)], check=True, capture_output=True
            )
            # Create initial commit
            temp_clone = base_dir / f"temp-{repo_name}"
            subprocess.run(
                ["git", "clone", str(bare_repo), str(temp_clone)], check=True, capture_output=True
            )
            # Configure git identity for CI
            subprocess.run(
                ["git", "-C", str(temp_clone), "config", "user.name", "Test User"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(temp_clone), "config", "user.email", "test@example.com"],
                check=True,
                capture_output=True,
            )
            (temp_clone / "README.md").write_text("test")
            subprocess.run(
                ["git", "-C", str(temp_clone), "add", "."], check=True, capture_output=True
            )
            subprocess.run(
                ["git", "-C", str(temp_clone), "commit", "-m", "init"],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "-C", str(temp_clone), "push"], check=True, capture_output=True)
            # Create old-format worktree using git
            old_branch = branch.replace("/", "__")
            old_path = base_dir / f"{repo_name}-{old_branch}"
            subprocess.run(
                ["git", "-C", str(bare_repo), "worktree", "add", str(old_path), "--detach"],
                check=True,
                capture_output=True,
            )
            old_paths.append(old_path)

        old1, old2 = old_paths

        config = {
            "base_dir": str(base_dir),
            "worktrees": {
                "preset::feature/foo": {"repo": "preset", "branch": "feature/foo", "pr": None},
                "superset::bugfix/bar": {"repo": "superset", "branch": "bugfix/bar", "pr": None},
            },
        }

        from repo_cli.config import migrate_worktree_paths

        _, changed = migrate_worktree_paths(config)

        # Both should be migrated
        assert (base_dir / "preset-feature%2Ffoo").exists()
        assert (base_dir / "superset-bugfix%2Fbar").exists()
        assert not old1.exists()
        assert not old2.exists()

        # Should report change
        assert changed is True

    def test_migrate_skip_if_new_exists(self, tmp_path):
        """Should not migrate if new path already exists."""
        base_dir = tmp_path / "code"
        base_dir.mkdir(parents=True)

        # Create both old and new paths
        old_path = base_dir / "preset-feature__foo"
        new_path = base_dir / "preset-feature%2Ffoo"
        old_path.mkdir()
        new_path.mkdir()
        (old_path / "old.txt").write_text("old")
        (new_path / "new.txt").write_text("new")

        config = {
            "base_dir": str(base_dir),
            "worktrees": {
                "preset::feature/foo": {"repo": "preset", "branch": "feature/foo", "pr": None},
            },
        }

        from repo_cli.config import migrate_worktree_paths

        _, changed = migrate_worktree_paths(config)

        # Both should still exist (no migration)
        assert old_path.exists()
        assert new_path.exists()
        assert (old_path / "old.txt").exists()
        assert (new_path / "new.txt").exists()

        # Should not report change (migration skipped)
        assert changed is False

    def test_migrate_no_base_dir(self):
        """Should handle config without base_dir gracefully."""
        config = {
            "worktrees": {
                "preset::feature/foo": {"repo": "preset", "branch": "feature/foo", "pr": None},
            },
        }

        from repo_cli.config import migrate_worktree_paths

        result, changed = migrate_worktree_paths(config)

        # Should return config unchanged
        assert result == config

        # Should not report change (no base_dir)
        assert changed is False

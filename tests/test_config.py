"""Tests for config module."""

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
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_github_url("not-a-valid-url")

    def test_parse_non_github_url_raises_error(self):
        """Should raise ValueError for non-GitHub URLs."""
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_github_url("https://gitlab.com/owner/repo.git")


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

        migrated = migrate_config(old_config)

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

    def test_migrate_already_new_format(self):
        """Should leave new format keys unchanged."""
        new_config = {
            "base_dir": "~/code",
            "repos": {"preset": {"url": "git@github.com:preset-io/preset.git"}},
            "worktrees": {
                "preset::feature-123": {"repo": "preset", "branch": "feature-123", "pr": 4567}
            },
        }

        migrated = migrate_config(new_config)

        # Should keep new format
        assert "preset::feature-123" in migrated["worktrees"]
        assert migrated["worktrees"]["preset::feature-123"]["pr"] == 4567

        # No version added (already in correct format)
        assert "version" not in migrated

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

        migrated = migrate_config(mixed_config)

        # Old format should be migrated
        assert "superset::6.0" in migrated["worktrees"]
        assert "superset-6.0" not in migrated["worktrees"]

        # New format should be preserved
        assert "preset::feature-123" in migrated["worktrees"]

        # Version should be added (migration occurred)
        assert migrated["version"] == "0.1.0"

    def test_migrate_empty_worktrees(self):
        """Should handle config with no worktrees."""
        empty_config = {"base_dir": "~/code", "repos": {}, "worktrees": {}}

        migrated = migrate_config(empty_config)

        assert migrated["worktrees"] == {}
        assert "version" not in migrated

    def test_migrate_no_worktrees_key(self):
        """Should handle config without worktrees key."""
        minimal_config = {"base_dir": "~/code", "repos": {}}

        migrated = migrate_config(minimal_config)

        # Should not add worktrees or version if not present
        assert "worktrees" not in migrated
        assert "version" not in migrated

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

        migrated = migrate_config(malformed_config)

        # Malformed entry should be kept as-is
        assert "invalid-entry" in migrated["worktrees"]
        assert migrated["worktrees"]["invalid-entry"] == "not a dict"

        # Valid entry should be migrated
        assert "superset::6.0" in migrated["worktrees"]
        assert "superset-6.0" not in migrated["worktrees"]

    def test_migrate_preserves_version(self):
        """Should preserve existing version field."""
        config_with_version = {
            "base_dir": "~/code",
            "repos": {},
            "worktrees": {"superset-6.0": {"repo": "superset", "branch": "6.0", "pr": None}},
            "version": "0.0.9",  # Existing version
        }

        migrated = migrate_config(config_with_version)

        # Version should be preserved (setdefault doesn't override)
        assert migrated["version"] == "0.0.9"

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

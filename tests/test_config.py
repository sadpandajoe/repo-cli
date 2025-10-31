"""Tests for config module."""

import pytest
import tempfile
from pathlib import Path
from repo_cli.config import parse_github_url, load_config, save_config, get_config_path


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
                    "owner_repo": "preset-io/preset"
                }
            },
            "worktrees": {
                "preset-feature-123": {
                    "repo": "preset",
                    "branch": "feature-123",
                    "pr": 4567
                }
            }
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
                    "metadata": {
                        "tags": ["python", "cli"],
                        "stars": 100
                    }
                }
            }
        }

        save_config(config)
        loaded = load_config()

        assert loaded["repos"]["test"]["metadata"]["tags"] == ["python", "cli"]
        assert loaded["repos"]["test"]["metadata"]["stars"] == 100

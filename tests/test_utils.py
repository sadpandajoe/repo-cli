"""Tests for utils module."""

import pytest

from repo_cli.utils import (
    expand_path,
    get_bare_repo_path,
    get_worktree_path,
    validate_identifier,
    validate_path_safety,
)


class TestValidateIdentifier:
    """Tests for validate_identifier function."""

    def test_valid_simple_name(self):
        """Should accept simple alphanumeric names."""
        assert validate_identifier("myrepo") is None
        assert validate_identifier("feature123") is None

    def test_valid_name_with_hyphens(self):
        """Should accept names with hyphens."""
        assert validate_identifier("my-repo") is None
        assert validate_identifier("feature-123") is None

    def test_valid_name_with_underscores(self):
        """Should accept names with underscores."""
        assert validate_identifier("my_repo") is None
        assert validate_identifier("feature_123") is None

    def test_valid_name_with_dots(self):
        """Should accept names with dots."""
        assert validate_identifier("my.repo") is None
        assert validate_identifier("v1.0.0") is None

    def test_valid_mixed_characters(self):
        """Should accept mixed valid characters."""
        assert validate_identifier("my-repo_v1.0") is None
        assert validate_identifier("api-core-v2") is None

    def test_invalid_path_traversal_parent(self):
        """Should reject path traversal with parent directory."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("../prod")

    def test_invalid_path_traversal_relative(self):
        """Should reject relative path components."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("../../etc")

    def test_invalid_absolute_path(self):
        """Should reject absolute paths."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("/etc/passwd")

    def test_invalid_forward_slash(self):
        """Should reject names with forward slashes."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("my/repo")

    def test_invalid_backslash(self):
        """Should reject names with backslashes."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("my\\repo")

    def test_invalid_special_characters(self):
        """Should reject names with special characters."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("my@repo")
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("my$repo")
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("my repo")  # space

    def test_invalid_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("")

    def test_invalid_only_dots(self):
        """Should reject strings with only dots."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier(".")
        with pytest.raises(ValueError, match="Invalid identifier"):
            validate_identifier("..")


class TestValidatePathSafety:
    """Tests for validate_path_safety function."""

    def test_valid_path_inside_base(self, tmp_path):
        """Should accept paths inside base directory."""
        base_dir = tmp_path / "code"
        base_dir.mkdir()
        target_path = base_dir / "repo-branch"
        target_path.mkdir()

        # Should not raise
        validate_path_safety(target_path, base_dir)

    def test_invalid_path_outside_base(self, tmp_path):
        """Should reject paths outside base directory."""
        base_dir = tmp_path / "code"
        base_dir.mkdir()
        outside_path = tmp_path / "outside"
        outside_path.mkdir()

        with pytest.raises(ValueError, match="Path is outside base directory"):
            validate_path_safety(outside_path, base_dir)

    def test_invalid_symlink_escape(self, tmp_path):
        """Should reject symlinks that escape base directory."""
        base_dir = tmp_path / "code"
        base_dir.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        # Create symlink inside base_dir pointing outside
        symlink = base_dir / "evil-link"
        symlink.symlink_to(outside)

        with pytest.raises(ValueError, match="Path is outside base directory"):
            validate_path_safety(symlink, base_dir)

    def test_valid_path_not_yet_exists(self, tmp_path):
        """Should accept paths that don't exist yet (for creation)."""
        base_dir = tmp_path / "code"
        base_dir.mkdir()
        future_path = base_dir / "new-repo-branch"

        # Should not raise even though path doesn't exist yet
        validate_path_safety(future_path, base_dir)


class TestGetWorktreePath:
    """Tests for get_worktree_path with validation."""

    def test_get_worktree_path_with_valid_names(self, tmp_path):
        """Should return path for valid repo and branch names."""
        base_dir = tmp_path / "code"
        path = get_worktree_path(base_dir, "myrepo", "feature-123")
        assert path == base_dir / "myrepo-feature-123"

    def test_get_worktree_path_rejects_invalid_repo(self, tmp_path):
        """Should raise error for invalid repo name."""
        base_dir = tmp_path / "code"
        with pytest.raises(ValueError, match="Invalid identifier"):
            get_worktree_path(base_dir, "../prod", "main")

    def test_get_worktree_path_rejects_invalid_branch(self, tmp_path):
        """Should raise error for invalid branch name."""
        base_dir = tmp_path / "code"
        with pytest.raises(ValueError, match="Invalid identifier"):
            get_worktree_path(base_dir, "myrepo", "../../etc")


class TestGetBareRepoPath:
    """Tests for get_bare_repo_path with validation."""

    def test_get_bare_repo_path_with_valid_name(self, tmp_path):
        """Should return path for valid repo name."""
        base_dir = tmp_path / "code"
        path = get_bare_repo_path(base_dir, "myrepo")
        assert path == base_dir / "myrepo.git"

    def test_get_bare_repo_path_rejects_invalid_repo(self, tmp_path):
        """Should raise error for invalid repo name."""
        base_dir = tmp_path / "code"
        with pytest.raises(ValueError, match="Invalid identifier"):
            get_bare_repo_path(base_dir, "../prod")


class TestExpandPath:
    """Tests for expand_path function."""

    def test_expand_tilde(self):
        """Should expand ~ to home directory."""
        path = expand_path("~/code")
        assert "~" not in str(path)
        assert path.is_absolute()

    def test_expand_relative_path(self, tmp_path, monkeypatch):
        """Should resolve relative paths."""
        monkeypatch.chdir(tmp_path)
        path = expand_path("./code")
        assert path.is_absolute()
        assert path == tmp_path / "code"

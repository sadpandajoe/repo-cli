"""Tests for utils module."""

import pytest

from repo_cli.utils import (
    expand_path,
    get_bare_repo_path,
    get_worktree_path,
    validate_branch_name,
    validate_path_safety,
    validate_repo_alias,
)


class TestValidateRepoAlias:
    """Tests for validate_repo_alias function."""

    def test_valid_simple_name(self):
        """Should accept simple alphanumeric names."""
        assert validate_repo_alias("myrepo") is None
        assert validate_repo_alias("feature123") is None

    def test_valid_name_with_hyphens(self):
        """Should accept names with hyphens."""
        assert validate_repo_alias("my-repo") is None
        assert validate_repo_alias("feature-123") is None

    def test_valid_name_with_underscores(self):
        """Should accept names with underscores."""
        assert validate_repo_alias("my_repo") is None
        assert validate_repo_alias("feature_123") is None

    def test_valid_name_with_dots(self):
        """Should accept names with dots."""
        assert validate_repo_alias("my.repo") is None
        assert validate_repo_alias("v1.0.0") is None

    def test_valid_mixed_characters(self):
        """Should accept mixed valid characters."""
        assert validate_repo_alias("my-repo_v1.0") is None
        assert validate_repo_alias("api-core-v2") is None

    def test_invalid_path_traversal_parent(self):
        """Should reject path traversal with parent directory."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("../prod")

    def test_invalid_path_traversal_relative(self):
        """Should reject relative path components."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("../../etc")

    def test_invalid_absolute_path(self):
        """Should reject absolute paths."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("/etc/passwd")

    def test_invalid_forward_slash(self):
        """Should reject names with forward slashes."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("my/repo")

    def test_invalid_backslash(self):
        """Should reject names with backslashes."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("my\\repo")

    def test_invalid_special_characters(self):
        """Should reject names with special characters."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("my@repo")
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("my$repo")
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("my repo")  # space

    def test_invalid_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("")

    def test_invalid_only_dots(self):
        """Should reject strings with only dots."""
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias(".")
        with pytest.raises(ValueError, match="Invalid repo alias"):
            validate_repo_alias("..")

    def test_invalid_double_colon(self):
        """Should reject names with :: delimiter."""
        with pytest.raises(ValueError, match="cannot contain '::'"):
            validate_repo_alias("repo::name")
        with pytest.raises(ValueError, match="cannot contain '::'"):
            validate_repo_alias("my::repo::alias")


class TestValidateBranchName:
    """Tests for validate_branch_name function."""

    # Valid branch names
    def test_valid_simple_branch(self):
        """Should accept simple branch names."""
        assert validate_branch_name("main") is None
        assert validate_branch_name("master") is None
        assert validate_branch_name("develop") is None

    def test_valid_branch_with_slashes(self):
        """Should accept branch names with slashes (hierarchical)."""
        assert validate_branch_name("feature/JIRA-123") is None
        assert validate_branch_name("bugfix/foo@bar") is None
        assert validate_branch_name("user/joe/feature") is None
        assert validate_branch_name("release/v1.2.3") is None

    def test_valid_branch_with_hyphens(self):
        """Should accept branch names with hyphens."""
        assert validate_branch_name("feature-123") is None
        assert validate_branch_name("my-branch") is None

    def test_valid_branch_with_underscores(self):
        """Should accept branch names with single underscores."""
        assert validate_branch_name("feature_123") is None
        assert validate_branch_name("my_branch") is None

    def test_valid_branch_with_dots(self):
        """Should accept branch names with dots."""
        assert validate_branch_name("v1.0.0") is None
        assert validate_branch_name("release-1.2") is None

    def test_valid_branch_with_at_sign(self):
        """Should accept branch names with @ sign (but not @{)."""
        assert validate_branch_name("user@hostname") is None
        assert validate_branch_name("feature@v2") is None

    # Invalid branch names - double underscores (reserved for sanitization)
    def test_invalid_double_underscore(self):
        """Should reject branch names with double underscores."""
        with pytest.raises(ValueError, match="cannot contain '__'"):
            validate_branch_name("feature__foo")

    def test_invalid_double_underscore_multiple(self):
        """Should reject branch names with multiple double underscores."""
        with pytest.raises(ValueError, match="cannot contain '__'"):
            validate_branch_name("user__joe__feature")

    def test_invalid_double_underscore_with_slash(self):
        """Should reject mixed slash and double underscore."""
        with pytest.raises(ValueError, match="cannot contain '__'"):
            validate_branch_name("feature/foo__bar")

    # Invalid branch names - prohibited characters
    def test_invalid_space(self):
        """Should reject branch names with spaces."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("my branch")

    def test_invalid_tilde(self):
        """Should reject branch names with tilde."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch~1")

    def test_invalid_caret(self):
        """Should reject branch names with caret."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch^2")

    def test_invalid_colon(self):
        """Should reject branch names with colon."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch:name")

    def test_invalid_question_mark(self):
        """Should reject branch names with question mark."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch?")

    def test_invalid_asterisk(self):
        """Should reject branch names with asterisk."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch*")

    def test_invalid_bracket(self):
        """Should reject branch names with brackets."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch[0]")

    def test_invalid_backslash(self):
        """Should reject branch names with backslash."""
        with pytest.raises(ValueError, match="prohibited characters"):
            validate_branch_name("branch\\name")

    # Invalid branch names - prohibited sequences
    def test_invalid_at_brace(self):
        """Should reject branch names with @{ sequence."""
        with pytest.raises(ValueError, match="cannot contain '@\\{'"):
            validate_branch_name("branch@{0}")

    def test_invalid_double_dot(self):
        """Should reject branch names with .. sequence."""
        with pytest.raises(ValueError, match="cannot contain '..'"):
            validate_branch_name("feature..bug")

    def test_invalid_ending_with_dot(self):
        """Should reject branch names ending with dot."""
        with pytest.raises(ValueError, match="cannot end with '.'"):
            validate_branch_name("branch.")

    def test_invalid_leading_slash(self):
        """Should reject branch names starting with slash."""
        with pytest.raises(ValueError, match="cannot start or end with '/'"):
            validate_branch_name("/feature")

    def test_invalid_trailing_slash(self):
        """Should reject branch names ending with slash."""
        with pytest.raises(ValueError, match="cannot start or end with '/'"):
            validate_branch_name("feature/")

    def test_invalid_consecutive_slashes(self):
        """Should reject branch names with consecutive slashes."""
        with pytest.raises(ValueError, match="cannot contain consecutive slashes"):
            validate_branch_name("feature//bug")

    def test_invalid_component_starting_with_dot(self):
        """Should reject slash components starting with dot."""
        with pytest.raises(ValueError, match="cannot start with '.'"):
            validate_branch_name("feature/.hidden")

    def test_invalid_component_ending_with_lock(self):
        """Should reject slash components ending with .lock."""
        with pytest.raises(ValueError, match="cannot end with '.lock'"):
            validate_branch_name("feature/file.lock")

    def test_invalid_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValueError, match="Invalid branch name"):
            validate_branch_name("")

    def test_invalid_single_at_sign(self):
        """Should reject single @ character."""
        with pytest.raises(ValueError, match="cannot be single '@' character"):
            validate_branch_name("@")


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

    def test_get_worktree_path_with_branch_slashes(self, tmp_path):
        """Should sanitize slashes in branch names for filesystem."""
        base_dir = tmp_path / "code"
        # Slashes in branch names are replaced with __
        path = get_worktree_path(base_dir, "myrepo", "feature/JIRA-123")
        assert path == base_dir / "myrepo-feature__JIRA-123"

    def test_get_worktree_path_rejects_invalid_repo(self, tmp_path):
        """Should raise error for invalid repo name."""
        base_dir = tmp_path / "code"
        with pytest.raises(ValueError, match="Invalid repo alias"):
            get_worktree_path(base_dir, "../prod", "main")

    def test_get_worktree_path_rejects_invalid_branch(self, tmp_path):
        """Should raise error for invalid branch name."""
        base_dir = tmp_path / "code"
        with pytest.raises(ValueError, match="Invalid branch name"):
            get_worktree_path(base_dir, "myrepo", "branch with spaces")


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
        with pytest.raises(ValueError, match="Invalid repo alias"):
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

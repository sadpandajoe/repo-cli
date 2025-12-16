# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-12-16

### Fixed
- **Bare Clone Fetch Refspec** - Configure `remote.origin.fetch` on bare clone so `git fetch origin` updates remote-tracking branches instead of just FETCH_HEAD
- **Stale Local Branches** - `create_worktree` now prefers remote-tracking branches over potentially stale local refs, using `-B` to reset local branch from `origin/<branch>`
- **Version Mismatch** - Synced `__init__.py` and `pyproject.toml` versions

### Added
- **Migration Helper** - `_ensure_fetch_refspec()` automatically migrates pre-v0.1.2 repos on first fetch (only sets if missing, preserves custom configs)
- **9 new tests** for refspec configuration, migration, and worktree creation failure paths

### Testing
- **175 passing tests** (up from 140)
- Verified on Python 3.11

## [0.1.1] - 2025-12-03

### Fixed
- **HEAD Branch Creation Bug** - `get_default_branch()` now validates ref format, preventing branches named "HEAD" or "refs/remotes/origin/HEAD"
- **Remote HEAD Resolution** - Properly resolves `refs/remotes/origin/HEAD` to actual target branch (develop, trunk, etc.)
- **Master Fallback Validation** - Verifies master branch exists before returning as fallback, with clear error if neither main nor master exists

### Testing
- **140 passing tests** (up from 135)
- 5 new tests for edge cases in default branch detection

## [0.1.0] - 2025-11-12

### Added

#### Core Commands
- `repo init` - Initialize configuration with base directory
- `repo register` - Register repository aliases with GitHub URL parsing
- `repo create` - Create git worktrees with automatic branch detection
- `repo list` - Display all worktrees with PR status in rich tables
- `repo delete` - Remove worktrees with safety confirmations
- `repo activate` - Navigate to worktrees with cd hints
- `repo pr link` - Link GitHub PRs to worktrees for status tracking

#### Diagnostic & Upgrade Commands
- `repo --version` - Display current version
- `repo doctor` - Run comprehensive health checks (Git, gh CLI, config, dependencies)
- `repo upgrade-check` - Check for newer versions via git tags
- `repo upgrade` - Automatic upgrade with safety checks (--force flag available)

#### Features
- **Bare Repository Architecture** - Stores repos as bare at `~/code/{repo}.git/`
- **Worktree Management** - Automatic worktree creation at `~/code/{repo}-{branch}/`
- **Branch Support** - Handles both new and existing branches (local + remote)
- **Slash Support** - Full support for hierarchical branch names (e.g., `feature/foo`)
- **Percent Encoding** - Bijective path encoding for branch names with special characters
- **PR Integration** - GitHub PR status display with graceful fallback
- **Shell Auto-complete** - Tab completion for repos and branches
- **Rich Console Output** - Colors, tables, and progress indicators
- **Configuration Management** - YAML-based config at `~/.repo-cli/config.yaml`
- **Automatic Migrations** - Seamless config format upgrades

#### Shell Integration
- `repo activate --print` - Plain path output for command substitution
- Example: `cd $(repo activate myrepo branch --print)`

#### Security
- Input validation for repo aliases and branch names
- Path traversal protection
- Safe subprocess execution
- Percent-encoding prevents path collisions

### Fixed
- **Version Comparison** - Now uses `packaging.version` for proper semver comparison (fixes 0.9.0 > 0.10.0 bug)
- **Activate Command** - Fixed Path conversion bug causing TypeError
- **Fetch Failures** - Improved error handling with user prompts
- **Config Collisions** - Changed delimiter from `-` to `::` to prevent key collisions
- **CI Tests** - Added git user identity configuration for migration tests
- **Path Encoding** - Migrated to percent-encoding for bijective path mapping
- **Git Metadata** - Use `git worktree move` instead of `Path.rename()` for migrations
- **Config Saves** - Only save when migrations actually modify data (prevents race conditions)
- **Remote URLs** - Check and update bare repo remote URLs on registration

### Dependencies
- Python >= 3.11
- Git >= 2.17 (for `git worktree move` support)
- typer >= 0.12.0
- rich >= 13.7.0
- pyyaml >= 6.0.1
- packaging >= 24.0
- gh CLI (optional, for PR features)

### Testing
- **135 passing tests** with comprehensive coverage
- Unit tests for all core functionality
- E2E workflow tests simulating fresh installation
- Security tests for input validation
- Migration tests for config upgrades
- CI/CD with GitHub Actions (Python 3.11 and 3.12)

### Documentation
- Comprehensive README with usage examples
- Installation instructions (uv and pip)
- Upgrade documentation (automatic and manual)
- Shell integration examples
- Naming rules for repos and branches
- Known limitations documented

### Development
- Ruff linting and formatting
- Pre-commit hooks for code quality
- pytest with coverage reporting
- Editable installation for contributors

### Migration Notes
- No breaking changes - all migrations are automatic
- Existing worktrees automatically migrate to new path encoding
- Config format upgrades happen transparently on first run
- Safe to upgrade from any development version

### Known Limitations
- Upgrade commands depend on user's git/gh/uv environment
- Full upgrade workflow not covered by automated tests (requires manual testing)
- Tested primarily on macOS (Git 2.40.0, gh 2.60.1)

[0.1.2]: https://github.com/sadpandajoe/repo-cli/releases/tag/v0.1.2
[0.1.1]: https://github.com/sadpandajoe/repo-cli/releases/tag/v0.1.1
[0.1.0]: https://github.com/sadpandajoe/repo-cli/releases/tag/v0.1.0

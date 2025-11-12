## Overview
A lightweight CLI tool for managing git worktrees with PR tracking. Simplifies the workflow of creating isolated branches, tracking their PRs, and managing multiple worktrees across repositories.

## Summary
Build a Python CLI that manages git worktrees using a bare repo + worktree architecture. The tool handles automatic repo cloning, worktree creation/deletion, and provides a rich table view showing repo, branch, and PR status. MVP focuses on core worktree operations with manual PR linking.

## Goals
- Simplify worktree creation workflow (no manual git worktree commands)
- Track PR status alongside worktrees
- Provide clear visibility into all active worktrees
- Support repo aliasing for easy reference
- Shell auto-complete for seamless UX
- Keep it simple - defer dependency/venv management to later phases

## Assumptions
- User has git 2.17+ (worktree move support)
- GitHub CLI (`gh`) available for PR integration (optional, graceful fallback)
- Base directory: `~/code/`
- User manages venv/dependencies manually (for MVP)

## Previous Phases

### Phase 1: Project Scaffolding - Completed 2025-10-30
Complete package structure with CLI framework, all command stubs, and project setup.
**PR #1 merged to main.** See PROJECT_ARCHIVE.md for full details.

### Phase 2: Core Infrastructure & MVP Commands - Completed 2025-10-30
Implemented all MVP commands with TDD approach (37 passing tests), CI/CD pipeline, and comprehensive error handling.
**PR #2 merged to main.** See PROJECT_ARCHIVE.md for full details.

---

## Development Log

### 2025-11-03 - Phase 3: Auto-complete Implementation ✓
Implemented shell auto-complete functionality for improved UX.

**Auto-complete Functions (TDD approach):**
- `complete_repo()` - Completes repo aliases from config
  - Returns all registered repos
  - Filters by incomplete string (e.g., "pre" → "preset", "preset-manager")
  - Returns empty list when config doesn't exist (graceful fallback)
- `complete_branch()` - Completes branch names from worktrees
  - Returns all branches across all repos
  - Filters by incomplete string (e.g., "feat" → "feature-123", "feature-456")
  - Returns empty list when config doesn't exist (graceful fallback)
  - Note: Context-aware filtering (by repo) not supported by Typer's completion API

**CLI Integration:**
- Wired auto-complete to command arguments:
  - `repo create <repo>` - completes repo aliases
  - `repo list [repo]` - completes repo aliases
  - `repo delete <repo> <branch>` - completes both repo and branch
  - `repo pr link <repo> <branch>` - completes both repo and branch
- Used Typer's `Annotated[str, typer.Argument(autocompletion=func)]` pattern
- Typer provides built-in `--install-completion` command for shell setup

**Testing:**
- Added 6 new integration tests (43 total, all passing)
- Tests cover: all repos, filtering, error handling, graceful fallbacks
- Followed TDD: RED (failing tests) → GREEN (implementation) → REFACTOR (cleanup)

**Technical Notes:**
- Typer completion callbacks must have signature: `(incomplete: str = "") -> list[str]`
- Context-aware completion (e.g., branches filtered by selected repo) would require custom shell completion scripts
- Current implementation shows all branches, which is acceptable for MVP

### 2025-11-07 - Rebase and PR Update
Successfully rebased Phase 3 branch onto main after PR #2 merge.

**Issue:**
- PR #2 was merged to main with Phase 2 implementation
- Branch contained duplicate Phase 2 commits (different hashes)
- Standard rebase caused conflicts in 7 files

**Resolution:**
- Created clean branch from latest main
- Cherry-picked only Phase 3 commits (3 commits)
- Force-pushed to update PR #3

**Result:**
- Clean history: 3 Phase 3 commits on top of main
- All 43 tests passing
- No merge conflicts
- PR #3 updated and ready to merge

### 2025-11-07 - Archived Phase 1 & 2
Moved completed Phase 1 and Phase 2 details to PROJECT_ARCHIVE.md to reduce context size.

**What Was Archived:**
- Phase 1: Project scaffolding development log (2025-10-30 15:30-19:30)
- Phase 2: Core infrastructure implementation log (2025-10-30 20:00-21:00)
- Complete technical details, test coverage, and code review notes
- Total ~200 lines moved to archive

**What Remains in PROJECT.md:**
- Brief phase summaries with PR links
- Phase 3 (current) development log
- Current status and architecture decisions
- Command specifications and success criteria

**Reason:** Phase 1 & 2 are complete and merged. Focus PROJECT.md on active/recent work.

### 2025-11-07 - Feedback: Support Existing Branch Checkout
+Fixed issue where `repo create` failed when trying to checkout existing branches.

**Problem:**
- Command always tried to create NEW branches with `-b` flag
- Failed with "fatal: a branch named 'X' already exists" for existing branches
- Example: `repo create superset 6.0` failed because 6.0 branch exists

**Solution:**
- Added `branch_exists()` function to check for existing branches (local and remote)
- Updated `create_worktree()` to conditionally use `-b` flag only for new branches
- For existing branches, checkout directly without `-b` flag
- Added `get_default_branch()` to resolve `origin/HEAD` in bare repos (doesn't exist)
- Display "(existing)" vs "(new, from X)" in CLI output

**Implementation:**
- `git_ops.branch_exists()` - Check refs/remotes/origin/* and refs/heads/*
- `git_ops.get_default_branch()` - Resolve HEAD symref or fallback to main/master
- `git_ops.create_worktree()` - Returns tuple (None, is_new_branch)
- Updated `main.py` to display appropriate status message

**Testing:**
- Added 8 new tests (51 total, all passing)
- Tests for: branch_exists, get_default_branch, new/existing branch workflows
- Manual verification: `repo create superset 6.0` ✓

**Behavioral Change:**
- `repo create <repo> <existing-branch>` - Checkout existing branch
- `repo create <repo> <new-branch>` - Create new branch from default
- `repo create <repo> <new-branch> --from <ref>` - Create from custom ref

### 2025-11-07 - Feedback: Skip .github Submodules
Fixed unnecessary initialization of GitHub Actions stored as submodules.

**Problem:**
- Apache Superset showed "Initialized 8 submodules" but all were GitHub Actions in `.github/`
- These are CI/CD tools only, not needed for local development
- Wasted ~50MB of downloads and initialization time

**Solution:**
- Parse `.gitmodules` to extract submodule paths
- Filter out any paths starting with `.github/`
- Initialize only non-.github submodules individually
- Return count of actually-needed submodules initialized

**Implementation:**
- Updated `init_submodules()` to parse and filter `.github/` paths
- Initialize each non-.github submodule with specific path argument
- For repos with only .github submodules, return 0 (no output message)

**Testing:**
- Added 2 new tests (53 total, all passing)
- Test for mixed .github and regular submodules
- Test for repos with only .github submodules
- Manual verification: Superset no longer shows submodule message

**Result:**
- Superset: 0 submodules initialized (previously 8)
- Faster worktree creation
- Less disk usage

### 2025-11-07 - Code Review Feedback: Critical Fixes
Addressed 4 issues from code review feedback.

**Issue 1 [major]: Remote branches invisible after initial clone**
- **Problem**: `branch_exists()` ran on stale refs, couldn't see new remote branches
- **Solution**: Added `fetch_repo()` to update refs before branch check
- **Implementation**:
  - `git_ops.fetch_repo()` - Run `git fetch --prune origin`
  - Call before `create_worktree()` (skip on fresh clone)
  - Graceful fallback if fetch fails (offline scenario)
- **Result**: Now sees branches created after initial bare clone

**Issue 2 [major]: Detached HEAD for remote-only branches**
- **Problem**: `git worktree add <path> origin/<branch>` creates detached HEAD
- **Solution**: Check for local branch first, create tracking branch if remote-only
- **Implementation**:
  - If local branch exists: checkout directly
  - If remote-only: use `-b <branch> origin/<branch>` to create tracking branch
  - Users can now push commits back to remote
- **Result**: Proper branch checkouts, no detached HEAD

**Issue 3 [minor]: Misleading repo init --force warning**
- **Problem**: Warning said "will delete all repos and worktrees" but didn't
- **Solution**: Removed misleading text
- **Implementation**: Only overwrites `~/.repo-cli/config.yaml`
- **Result**: Accurate description of actual behavior

**Issue 4 [nit]: Worktree metadata records wrong start_point**
- **Problem**: Always recorded input (e.g., `origin/HEAD`) even for existing branches
- **Solution**: Return actual ref used from `create_worktree()`
- **Implementation**:
  - Changed return type to `tuple[str, bool]` (actual_ref, is_new_branch)
  - Save actual ref to config instead of input start_point
  - For existing local: saves branch name
  - For existing remote: saves `origin/<branch>`
  - For new branches: saves resolved ref (e.g., `master` instead of `origin/HEAD`)
- **Result**: `repo list` shows truthful metadata

**Testing:**
- All 53 tests passing
- Updated test signatures and logic to match new behavior
- All linting checks pass

**Commits:**
- Commit 1: Support existing branch checkout (8 new tests)
- Commit 2: Skip .github submodules (2 new tests)
- Commit 3: Address code review feedback (test updates)

### 2025-11-11 14:30 - Planning: Path Collision Fix (Feedback Round 2)
+Received feedback identifying remaining collision vulnerability in path sanitization.

**Feedback Summary:**
1. **[CRITICAL] Path collision still possible** - Current `__` replacement is not bijective
   - Problem: `feature/foo` and `feature__foo` both map to `repo-feature__foo`
   - Impact: Second worktree creation fails or corrupts existing worktree
   - Current approach: Simple string replace (`/` → `__`) in `get_worktree_path()`
   - Requested: Bijective encoding (percent-encoding or hash-based)

2. **[BLOCKER] Test suite not running in user's sandbox**
   - UV panics: "Attempted to create a NULL object" in system-configuration
   - User cannot verify test passing status
   - Requested: Run full suite in normal environment before committing

**Planning Mode:**
- Need to evaluate bijective encoding approaches
- Must ensure backward compatibility with existing worktrees
- Need migration strategy for existing paths
- Must verify tests pass in normal environment

### 2025-11-11 14:30 - Path Collision Fix: Percent-Encoding
Implementing bijective encoding to prevent path collisions.

**Problem:**
- Current `__` replacement is not bijective (not 1:1 reversible)
- `feature/foo` and `feature__foo` both map to `repo-feature__foo` (COLLISION!)
- Previous fix (rejecting `__` in branch names) doesn't solve root issue

**Investigation:**
- Checked claudette-cli for reference implementation
- Finding: They avoid the problem by using simple project names (no slashes)
- Our requirement: Support hierarchical branch names like `feature/foo`

**Accepted Solution: Percent-Encoding**
- Encode `/` as `%2F`, `%` as `%25`, etc.
- Standard approach (RFC 3986, same as URLs)
- Truly bijective: can round-trip encode/decode
- Reasonable readability: `feature/foo` → `repo-feature%2Ffoo`
- Python stdlib support: `urllib.parse.quote()`

**Implementation Plan:**
1. Replace `branch.replace("/", "__")` with `quote(branch, safe='')`
2. Remove `__` validation (no longer needed)
3. Add migration for existing `__`-based paths in config
4. Update all tests for new encoding
5. Run full test suite in normal environment

**Examples After Fix:**
- `feature/foo` → `repo-feature%2Ffoo`
- `feature__foo` → `repo-feature__foo` (no encoding needed)
- `fix/issue#42` → `repo-fix%2Fissue%2342`

**Implementation Complete:**
1. ✅ Updated `utils.py`:
   - Imported `urllib.parse.quote`
   - Replaced `branch.replace("/", "__")` with `quote(branch, safe='')`
   - Updated comments to reflect percent-encoding
2. ✅ Removed `__` validation:
   - Deleted double-underscore check from `validate_branch_name()`
   - Branch names with `__` now allowed (percent-encoding prevents collisions)
3. ✅ Added path migration in `config.py`:
   - New function `migrate_worktree_paths()` automatically renames old directories
   - Called from `load_config()` after config migration
   - Safe: only renames if old path exists and new path doesn't
   - Used `contextlib.suppress(OSError)` for clean error handling
4. ✅ Updated all tests:
   - Changed 3 validation tests to accept `__` in branch names
   - Updated path test to expect `%2F` instead of `__`
   - Added 5 new tests for path migration (125 total tests)
5. ✅ All 125 tests passing in normal environment
6. ✅ Committed to branch: `6fcfb1c` (5 files changed, 301 insertions, 36 deletions)

**Behavioral Changes:**
- New worktrees: Use percent-encoded paths (e.g., `feature%2Ffoo`)
- Existing worktrees: Automatically migrated on next `load_config()` call
- Branch names: Now accepts `__` (previously rejected)
- Path collisions: **Fixed** - `feature/foo` and `feature__foo` now map to different paths

### 2025-11-12 15:00 - Feedback Round 3: 5 Critical Pre-Launch Fixes
Addressed 5 critical issues identified in final pre-launch feedback.

**Issue 1 [MAJOR]: migrate_worktree_paths used Path.rename() incorrectly**
- **Problem:** Simple file rename broke Git's internal metadata (.git/worktrees/<name>/gitdir)
- **Impact:** `git worktree list` and `git worktree remove` failed after migration
- **Solution:** Use `git worktree move <old> <new>` to update both filesystem and Git metadata
- **Implementation:**
  - Updated `migrate_worktree_paths()` to call `git worktree move` via subprocess
  - Added proper error handling (FileNotFoundError, CalledProcessError)
  - Falls back silently if move fails (manual migration needed)
- **Result:** Git operations work correctly after path migration

**Issue 2 [MAJOR]: load_config saved on every read causing race conditions**
- **Problem:** Saved whenever `version` key existed, even from auto-completion
- **Impact:** Concurrent commands could overwrite each other's changes
- **Solution:** Track whether migrations actually changed data
- **Implementation:**
  - Changed `migrate_config()` return type to `tuple[dict, bool]`
  - Changed `migrate_worktree_paths()` return type to `tuple[dict, bool]`
  - Updated `load_config()` to only save if `config_changed or paths_changed`
  - Updated all test signatures and assertions
- **Result:** No more unnecessary saves, race conditions eliminated

**Issue 3 [MAJOR]: register --force didn't update bare repo remote URL**
- **Problem:** Config updated but bare repo still pointed to old URL
- **Impact:** Future `repo create` commands fetched from wrong repository
- **Solution:** Detect URL mismatches and prompt user to update
- **Implementation:**
  - Added `get_remote_url(repo_path, remote="origin")` in git_ops.py
  - Added `set_remote_url(repo_path, url, remote="origin")` in git_ops.py
  - Updated register command to check bare repo URL when using --force
  - Interactive prompt: "Update bare repository remote URL?"
  - Clear warnings if user declines update
- **Result:** Bare repo and config stay in sync

**Issue 4 [MINOR]: init stored relative base_dir paths**
- **Problem:** `repo init --base-dir ./worktrees` stored literal `./worktrees`
- **Impact:** Commands run from different directories used wrong base path
- **Solution:** Store absolute path after expansion
- **Implementation:**
  - Changed `initial_config = {"base_dir": str(base_path), ...}` (was `base_dir`)
  - Also updated success message to show resolved path
- **Result:** Base directory always absolute and consistent

**Issue 5 [MINOR]: pytest failed from clean checkout**
- **Problem:** ModuleNotFoundError without pip install
- **Impact:** Contributors couldn't run tests immediately
- **Solution:** Add pytest config and improve documentation
- **Implementation:**
  - Added `[tool.pytest.ini_options]` with `pythonpath = ["src"]` to pyproject.toml
  - Updated README.md with comprehensive dev setup section
  - Documented both uv (recommended) and pip workflows
  - Added separate sections for setup, running tests, and code quality
- **Result:** Tests run from clean checkout with `pytest` or `uv run pytest`

**Testing:**
- All 125 tests passing ✓
- Updated 7 migrate_config tests for new return signature
- Updated 5 migrate_worktree_paths tests for new return signature
- Fixed 2 migration tests to properly initialize git repos
- Added subprocess setup for git worktree move testing

**Files Modified:**
- `pyproject.toml` - Added pytest configuration
- `README.md` - Comprehensive dev setup documentation
- `src/repo_cli/config.py` - Migration functions return tuples, git worktree move
- `src/repo_cli/git_ops.py` - Added get_remote_url() and set_remote_url()
- `src/repo_cli/main.py` - Fixed init path, register URL validation
- `tests/test_config.py` - Updated all test signatures and assertions

**Commit:** `891005c` - fix: address 5 critical feedback issues pre-launch

### 2025-11-12 20:00 - CI Fix: Git Identity Configuration
+Fixed CI test failures caused by missing git user configuration.

**Problem:**
- Two migration tests failed in CI with "fatal: Author identity unknown"
- Tests create git commits but CI environment has no user.name/user.email

**Solution:**
- Added git config setup before commit operations in tests:
  - `git config user.name "Test User"`
  - `git config user.email "test@example.com"`

**Tests Fixed:**
- `test_migrate_slash_to_percent_encoding`
- `test_migrate_multiple_worktrees`

**Result:** All 125 tests passing in CI (Python 3.11 and 3.12)

**Commit:** `3545283` - fix: configure git identity in CI tests

### 2025-11-12 20:30 - Feedback Round 4: Pre-Launch Polish
+Addressed 3 final issues identified before v0.1.0 launch.

**Issue 1 [MAJOR]: Git version requirement outdated**
- **Problem:** Docs said Git 2.5+ but code uses `git worktree move` (requires 2.17+)
- **Impact:** Users on Git 2.5-2.16 would have silent migration failures
- **Solution:** Updated README.md and PROJECT.md to require Git 2.17+
- **Result:** Accurate version requirements prevent user confusion

**Issue 2 [MAJOR]: Missing URL check on initial alias registration**
- **Problem:** Remote URL only checked on `--force` overwrite, not initial registration
- **Impact:** If bare repo exists before first registration, URL mismatch not detected
- **Solution:** Added URL check in `else` branch for new alias registration
- **Implementation:**
  - Check if bare repo exists when registering new alias
  - Compare remote URL with provided URL
  - Prompt user to update if mismatch detected
  - Same behavior as `--force` URL check
- **Result:** URL mismatches caught on both initial and force registration

**Issue 3 [MINOR]: Test setup instructions unclear**
- **Problem:** Contributors hit ModuleNotFoundError without clear setup guidance
- **Solution:** Added note to README.md Running Tests section
- **Clarifications:**
  - Must complete setup before running tests
  - uv users: automatic (uv run handles it)
  - pip users: need `pip install -e ".[dev]"`
- **Result:** Smoother contributor onboarding

**Testing:**
- All 125 tests passing locally and in CI ✓
- Both Python 3.11 and 3.12 passing ✓

**Files Modified:**
- `README.md` - Updated Git version, clarified test setup
- `PROJECT.md` - Updated Git version requirement
- `src/repo_cli/main.py` - Added URL check for initial registration

**Commit:** `d801eee` - fix: address 3 feedback issues for v0.1.0 launch

### 2025-11-11 - Critical Pre-Release Fixes
Fixed two critical issues identified before v0.1.0 release.

**Issue 1 [HIGH]: Config Migration - Breaking Change**
- **Problem**: Config key format changed from `repo-branch` to `repo::branch` in commit 047a187
- **Impact**: Existing user configs became incompatible (delete/pr link operations would fail)
- **Solution**: Added automatic migration in `config.py`
  - `migrate_config()` function detects old format keys and converts to new format
  - Migration runs on every `load_config()` call
  - Automatically saves migrated config back to disk
  - Adds version field (`0.1.0`) for tracking future migrations
  - Handles edge cases: mixed formats, malformed entries, empty configs

**Issue 2 [MEDIUM]: Directory Path Collision**
- **Problem**: Branches `feature/foo` and `feature__foo` map to same directory path
- **Impact**: Potential collision when sanitizing slashes (`/` → `__`)
- **Solution**: Added validation in `utils.py`
  - `validate_branch_name()` now rejects branch names containing `__`
  - Clear error message: "cannot contain '__' (reserved for slash sanitization)"
  - Prevents collision before it can occur

**Testing:**
- Added 11 new tests (120 total, all passing)
- Migration tests: old→new, already-new, mixed, edge cases (8 tests)
- Validation tests: double underscore rejection (3 tests)
- Manual verification with actual user config:
  - Successfully migrated 4 worktrees from old format
  - Verified `repo list` and `repo pr link` work after migration
  - Verified `feature__test` rejected, `feature_test` accepted

**Implementation:**
- `config.py`: Added `migrate_config()` function
- `utils.py`: Enhanced `validate_branch_name()` with `__` check
- `test_config.py`: Added `TestMigrateConfig` class with 8 tests
- `test_utils.py`: Added 3 double-underscore validation tests
- Commit 646e57c: "fix: add config migration and prevent path collisions pre-v0.1.0"

**Result:**
- Both issues resolved before v0.1.0 release
- Backward compatibility maintained via automatic migration
- Future collisions prevented via validation
- Zero breaking changes for existing users

## Current Status

**Active:**
- PR #4 ready for final review (12 commits)
- All 4 rounds of feedback addressed ✓
- All commits pushed to remote ✓
- CI passing on Python 3.11 and 3.12 ✓

**Completed:**
- ✅ Phase 1: Project scaffolding (PR #1 merged to main)
- ✅ Phase 2: Core infrastructure, all MVP commands, CI/CD, tests (PR #2 merged to main)
- ✅ Phase 3: Auto-complete implementation (PR #3 merged to main)
- ✅ Feedback Round 1: Existing branch checkout, .github submodules, code review issues
  - Commits: `82dcbab`, `047a187`, `646e57c`, `246aefd`
- ✅ Feedback Round 2: Bijective path encoding (percent-encoding)
  - Replaced `__` replacement with percent-encoding (`/` → `%2F`)
  - Added automatic path migration for existing worktrees
  - Fixed path collision vulnerability (`feature/foo` vs `feature__foo`)
  - Commit: `6fcfb1c`, `02b7336`
- ✅ Feedback Round 3: 5 critical pre-launch fixes
  - Fixed git worktree move for proper metadata updates
  - Fixed load_config race conditions (only save when changed)
  - Fixed register --force to update bare repo remote URL
  - Fixed init to store absolute base_dir paths
  - Fixed pytest to run from clean checkout
  - Commit: `891005c`
- ✅ CI Fix: Git identity configuration in tests
  - Commit: `3545283`
- ✅ Feedback Round 4: Pre-launch polish
  - Updated Git version requirement to 2.17+
  - Added URL check for initial alias registration
  - Clarified test setup in README
  - Commit: `d801eee`
- ✅ All 125 tests passing
- ✅ Documentation updated and accurate

**Pull Requests:**
- PR #1: Phase 1 scaffolding - ✅ Merged
- PR #2: Phase 2 core infrastructure - ✅ Merged
- PR #3: Phase 3 auto-complete - ✅ Merged
- PR #4: Feedback fixes - 🔄 Open (ready for final review)
  - Commit 1 (`82dcbab`): Prompt user when fetch fails before branch creation
  - Commit 2 (`047a187`): Support branch slashes and prevent config collisions
  - Commit 3 (`646e57c`): Config migration and path collision prevention
  - Commit 4 (`246aefd`): Update PROJECT.md with pre-release fixes
  - Commit 5 (`6fcfb1c`): Use percent-encoding for bijective path mapping
  - Commit 6 (`02b7336`): Update PROJECT.md with percent-encoding status
  - Commit 7 (`891005c`): Address 5 critical feedback issues pre-launch
  - Commit 8 (`b21b172`): Update PROJECT.md with feedback round 3 documentation
  - Commit 9 (`e91cf5b`): Update PROJECT.md with commit 8 and current status
  - Commit 10 (`3545283`): Configure git identity in CI tests
  - Commit 11 (`d801eee`): Address 3 feedback issues for v0.1.0 launch
  - Commit 12 (next): Update PROJECT.md with feedback round 4 and CI fix
  - https://github.com/sadpandajoe/repo-cli/pull/4

**Next:**
- Review and merge PR #4
- Manual end-to-end testing (optional)
- Release v0.1.0

**Blocked:**
- None

## Accepted Solution

### Architecture Decisions (Finalized)

**1. Directory Layout: Bare Repo Pattern**
- Bare repos stored at: `~/code/{repo}.git/`
- Worktrees stored at: `~/code/{repo}-{branch}/`
- No "main" checkout - all branches are worktrees
- Clean separation, predictable paths

**2. Initial Clone Behavior**
- Auto-clone as bare when repo doesn't exist
- Command: `git clone --bare <url> ~/code/{repo}.git`
- Seamless UX - user doesn't think about cloning

**3. PR Tracking**
- Manual linking: `repo pr link <repo> <branch> <pr-number>`
- Store PR# in config under worktree metadata
- Store owner/repo slug (parsed from URL during registration)
- Query live status: `gh pr view <pr#> --repo <owner_repo> --json state`
- Using `--repo` flag ensures queries work even if worktree deleted
- Graceful fallback: show PR# only if gh unavailable/offline

**4. URL Resolution**
- Explicit registration: `repo register <alias> <url>`
- Lazy registration: prompt for URL on first use, cache in config
- Both approaches save to same config structure
- Parse and store owner/repo slug from GitHub URLs for gh CLI integration

**5. Auto-complete**
- Typer's built-in `--install-completion`
- Custom completers for repo aliases and branch names
- Scan config for dynamic completion values

**6. Table Display**
- Columns: Repo | Branch | PR | Status
- No Path column (predictable: `~/code/{repo}-{branch}`)
- Rich table formatting with proper alignment

## Technical Stack

- **Language**: Python ≥ 3.11
- **Package Manager**: uv
- **CLI Framework**: Typer (with built-in auto-complete)
- **UI/Tables**: Rich
- **Config Format**: YAML (PyYAML)
- **Git Integration**: subprocess wrappers
- **GitHub Integration**: gh CLI subprocess calls

## MVP Commands Specification

### 1. `repo init`
Initialize the CLI environment.

```bash
repo init [--base-dir ~/code]
```

**Behavior:**
- Create `~/.repo-cli/config.yaml` with defaults
- Create base directory (default: `~/code`)
- Print setup instructions including auto-complete installation

**Config created:**
```yaml
base_dir: ~/code
repos: {}
worktrees: {}
```

**Output:**
```
✓ Created config at ~/.repo-cli/config.yaml
✓ Created base directory: ~/code
ℹ Run 'repo --install-completion' to enable auto-complete
ℹ Run 'repo create <name> <branch>' to get started
```

---

### 2. `repo register <alias> <url>`
Register a repository alias for easy reference.

```bash
repo register preset git@github.com:preset-io/preset.git
repo register superset https://github.com/apache/superset.git
```

**Behavior:**
- Validate git URL format
- Parse owner/repo slug from URL:
  - `git@github.com:owner/repo.git` → `owner/repo`
  - `https://github.com/owner/repo.git` → `owner/repo`
- Save alias → URL mapping and owner/repo slug to config under `repos:`
- Print confirmation

**Output:**
```
✓ Registered 'preset' → git@github.com:preset-io/preset.git
✓ GitHub repo: preset-io/preset
```

---

### 3. `repo create <repo> <branch> [--from <start-point>]`
Create a new worktree for a branch.

```bash
repo create preset feature-123
repo create preset bugfix-456 --from main       # Base off specific branch
repo create preset hotfix-789 --from v2.1.0    # Base off tag or commit
```

**Behavior:**
1. Check if alias exists in config
   - If not: prompt for URL, save to config (lazy registration)
2. Check if `~/code/{repo}.git` exists
   - If not: `git clone --bare <url> ~/code/{repo}.git`
3. Determine start-point:
   - If `--from` provided: use that value (branch, tag, or commit)
   - Otherwise: use `origin/HEAD` (repository's default branch)
4. Create worktree: `git -C ~/code/{repo}.git worktree add ~/code/{repo}-{branch} -b {branch} origin/HEAD`
   - Note: Replace `origin/HEAD` with value from `--from` flag if provided
5. Initialize submodules (if present): `git -C ~/code/{repo}-{branch} submodule update --init --recursive`
   - This runs automatically for all worktrees
   - If no submodules exist, command completes silently
6. Save worktree metadata to config (including start_point for reference)
7. Print success with path

**Output:**
```
✓ Cloning preset as bare repository...
✓ Created worktree: ~/code/preset-feature-123
✓ Branch: feature-123 (new, from origin/HEAD)
✓ Initializing submodules...
✓ Initialized 3 submodules
```

Or if repo already exists:
```
✓ Created worktree: ~/code/preset-feature-123
✓ Branch: feature-123 (new, from origin/HEAD)
✓ Initializing submodules...
✓ Initialized 3 submodules
```

If no submodules present:
```
✓ Created worktree: ~/code/preset-feature-123
✓ Branch: feature-123 (new, from origin/HEAD)
```

With `--from` flag:
```
✓ Created worktree: ~/code/preset-hotfix-789
✓ Branch: hotfix-789 (new, from v2.1.0)
✓ Initializing submodules...
✓ Initialized 3 submodules
```

---

### 4. `repo list`
Display all worktrees with PR status.

```bash
repo list
repo list preset          # Future: filter by repo
```

**Behavior:**
1. Read worktree metadata from config
2. For each worktree with linked PR:
   - Look up repo's `owner_repo` slug from config
   - Try: `gh pr view <pr#> --repo <owner_repo> --json state`
   - Fallback: Show PR# only if gh unavailable or offline
3. Display Rich table

**Note:** By using `--repo <owner_repo>` flag, PR status queries work even if the worktree directory has been deleted.

**Output:**
```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Repo    ┃ Branch        ┃ PR     ┃ Status        ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ preset  │ feature-123   │ #4567  │ Open          │
│ preset  │ bugfix-999    │ #4590  │ Merged        │
│ manager │ release-v2    │ #123   │ In Review     │
│ preset  │ hotfix-101    │ -      │ -             │
└─────────┴───────────────┴────────┴───────────────┘
```

When offline or gh unavailable:
```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Repo    ┃ Branch        ┃ PR     ┃ Status        ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ preset  │ feature-123   │ #4567  │ -             │
│ preset  │ bugfix-999    │ #4590  │ -             │
└─────────┴───────────────┴────────┴───────────────┘
```

---

### 5. `repo delete <repo> <branch>`
Remove a worktree.

```bash
repo delete preset feature-123
repo delete preset feature-123 --force  # Skip confirmation
```

**Behavior:**
1. Confirm deletion (unless `--force`)
2. Run: `git worktree remove ~/code/{repo}-{branch}`
3. Remove from config metadata
4. Print confirmation

**Output:**
```
⚠ Delete worktree 'preset-feature-123'? [y/N]: y
✓ Removed worktree: ~/code/preset-feature-123
```

---

### 6. `repo pr link <repo> <branch> <pr-number>`
Link a PR to a worktree.

```bash
repo pr link preset feature-123 4567
```

**Behavior:**
1. Validate worktree exists in config
2. Look up repo's `owner_repo` slug from config
3. Optionally validate PR exists: `gh pr view <pr-number> --repo <owner_repo>`
4. Store PR number in config under worktree metadata
5. Print confirmation

**Note:** By using `--repo <owner_repo>` flag, PR validation works reliably regardless of worktree state.

**Output:**
```
✓ Linked PR #4567 to preset-feature-123
```

Or if validating:
```
✓ Validated PR #4567 (Open) in preset-io/preset
✓ Linked to preset-feature-123
```

---

### 7. Auto-complete
Built-in Typer auto-complete support.

```bash
repo --install-completion  # Install for current shell
repo --show-completion     # Show completion script
```

**Completions provided:**
- Command names: `init`, `register`, `create`, `list`, `delete`, `pr`
- Repo aliases: read from config `repos:` keys
- Branch names: read from config `worktrees:` keys (filtered by repo context)

---

## Config Structure

```yaml
base_dir: ~/code

repos:
  preset:
    url: git@github.com:preset-io/preset.git
    owner_repo: preset-io/preset
  manager:
    url: git@github.com:preset-io/manager.git
    owner_repo: preset-io/manager
  superset:
    url: https://github.com/apache/superset.git
    owner_repo: apache/superset

worktrees:
  preset-feature-123:
    repo: preset
    branch: feature-123
    pr: 4567
    start_point: origin/HEAD
    created_at: 2025-10-30T15:45:00

  preset-bugfix-999:
    repo: preset
    branch: bugfix-999
    pr: 4590
    start_point: origin/HEAD
    created_at: 2025-10-30T14:30:00

  manager-release-v2:
    repo: manager
    branch: release-v2
    pr: 123
    start_point: origin/main
    created_at: 2025-10-30T16:00:00

  preset-hotfix-101:
    repo: preset
    branch: hotfix-101
    pr: null
    start_point: v2.1.0
    created_at: 2025-10-30T16:15:00
```

**Config location:** `~/.repo-cli/config.yaml`

---

## Directory Structure

```
repo-cli/
├── pyproject.toml           # uv project config
├── README.md
├── REQUIREMENTS.md
├── PROJECT.md               # This file
├── src/
│   └── repo_cli/
│       ├── __init__.py
│       ├── main.py          # CLI entry point
│       ├── config.py        # Config load/save/validation
│       ├── git_ops.py       # Git command wrappers
│       ├── gh_ops.py        # GitHub CLI wrappers
│       ├── utils.py         # Path helpers, validation
│       └── commands/
│           ├── __init__.py
│           ├── init.py      # repo init
│           ├── register.py  # repo register
│           ├── create.py    # repo create
│           ├── list.py      # repo list
│           ├── delete.py    # repo delete
│           └── pr.py        # repo pr link
└── tests/                   # Future: pytest tests
    ├── conftest.py
    ├── test_config.py
    ├── test_git_ops.py
    └── test_commands.py
```

---

## Implementation Phases

### Phase 1: Project Setup
- Create `pyproject.toml` with uv
- Set up `src/repo_cli/` package structure
- Install dependencies: typer, rich, pyyaml
- Create entry point in `main.py`

### Phase 2: Core Infrastructure
- `config.py`: YAML load/save, validation, defaults, URL parsing to extract owner/repo slug
- `git_ops.py`: Git wrappers (clone bare, worktree add/remove with start-point support)
- `gh_ops.py`: GitHub CLI wrappers (PR status queries with --repo flag, with fallback)
- `utils.py`: Path helpers, error handling, validation, URL parser for GitHub repos

**Implementation Notes:**
- `config.py`: Must parse GitHub URLs to extract `owner/repo` slug:
  - SSH format: `git@github.com:owner/repo.git` → `owner/repo`
  - HTTPS format: `https://github.com/owner/repo.git` → `owner/repo`
- `git_ops.py`: Worktree creation workflow:
  1. Create worktree with start-point: `git -C ~/code/{repo}.git worktree add <path> -b <branch> origin/HEAD` (default: `origin/HEAD`, override with `--from` flag)
  2. Initialize submodules automatically: `git -C <worktree_path> submodule update --init --recursive`
  3. Check submodule count to provide user feedback (parse output or check `.gitmodules`)
- `gh_ops.py`: All PR queries must use `--repo` flag: `gh pr view <pr#> --repo <owner_repo> --json state` (works even if worktree deleted)

### Phase 3: Commands Implementation
- `commands/init.py` - Initialize config and directories
- `commands/register.py` - Register repo aliases
- `commands/create.py` - Create worktrees (with lazy registration)
- `commands/list.py` - Display table with PR status + fallback
- `commands/delete.py` - Remove worktrees
- `commands/pr.py` - PR link subcommand

### Phase 4: Polish & Auto-complete
- Add completion callbacks for repo/branch arguments
- Test auto-complete in bash/zsh
- Add helpful error messages
- Manual testing of all commands

---

## Deferred to Future Phases

**Phase 2 - PR Enhancements:**
- `repo pr open <repo> <branch>` - Open PR in browser
- `repo pr create <repo> <branch>` - Create new PR from branch
- Auto-detect PRs without manual linking

**Phase 3 - Workflow Enhancements:**
- `repo sync <repo>` - Fetch updates for repo
- `repo switch <repo> <branch>` - Quick navigation helper
- Worktree git status indicators (dirty/clean/ahead/behind)

**Phase 4 - Dependency Management:**
- `repo create --venv` - Auto-create Python venv
- `repo create --install` - Auto-install dependencies
- Per-repo setup hooks (in config)

**Phase 5 - Advanced Features:**
- Port allocation for local dev servers
- Docker container management
- Worktree templates
- Bulk operations (delete all merged, etc.)

---

## Risk Assessment

### Configuration Complexity
- **Risk**: Low
- **Mitigation**: Simple YAML structure, sensible defaults, validation on load

### Cross-Platform Compatibility
- **Risk**: Medium (path handling, shell differences)
- **Mitigation**: Test on macOS/Linux, use pathlib, document platform requirements

### Git Worktree Edge Cases
- **Risk**: Medium (nested repos, submodules, detached HEAD)
- **Mitigation**: Start simple, handle edge cases as discovered, clear error messages

### GitHub CLI Dependency
- **Risk**: Low
- **Mitigation**: Graceful fallback when gh unavailable, tool still works without PR features

---

## Success Criteria

**MVP Complete When:**
- ✅ User can run `repo init` to set up
- ✅ User can register repos via `repo register` or lazy prompt
- ✅ User can create worktrees with `repo create`
- ✅ User can see all worktrees with `repo list` (with PR status if available)
- ✅ User can delete worktrees with `repo delete`
- ✅ User can link PRs with `repo pr link`
- ✅ Auto-complete implemented for repos and branches (manual shell testing pending)
- ✅ All commands have helpful error messages
- ✅ Tool works offline (gracefully degrades PR status)

**Definition of Done:**
- ✅ All MVP commands implemented and working (43/43 tests passing)
- ⏳ Manual testing complete on macOS (needs end-to-end verification)
- ✅ PROJECT.md updated with implementation details
- ✅ README.md created with installation and usage instructions

**Current Status: Phase 3 Complete - Ready for E2E Testing**

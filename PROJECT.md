## Overview
A lightweight CLI tool for managing git worktrees with PR tracking. Simplifies the workflow of creating isolated branches, tracking their PRs, and managing multiple worktrees across repositories.

## Current Status

**v0.1.2 Released** - 2025-12-16
- https://github.com/sadpandajoe/repo-cli/releases/tag/v0.1.2

### Previous Releases

**v0.1.2** - 2025-12-16
- Fix bare clone fetch refspec for remote-tracking branches
- Migration helper `_ensure_fetch_refspec` for pre-v0.1.2 repos
- `create_worktree` preserves local branches with unpushed commits
- 176 passing tests (36 new)
- See PROJECT_v0.1.2.md for details

**v0.1.1** - 2025-12-03
- HEAD branch creation bug fix
- 140 passing tests
- See PROJECT_v0.1.1.md for details

**v0.1.0** - 2025-11-12
- Core commands: init, register, create, list, delete, activate, pr link
- Diagnostic tools: --version, doctor, upgrade-check, upgrade
- Shell integration with --print flag
- 135 comprehensive tests
- See PROJECT_ARCHIVE.md for complete development history

---

## Active Work

**Current Focus**: v0.1.3 - Bug Fixes

### v0.1.3 Scope

Three fixes before v0.2.0 breaking change:

1. **Atomic config writes** (CRITICAL - data corruption risk)
   - Current: `save_config` writes directly to YAML file
   - Risk: Process crash mid-write → corrupt/empty config → CLI unusable
   - Fix: temp file + fsync + os.replace

2. **Submodule deletion failure**
   - Error: "fatal: working trees containing submodules cannot be moved or removed"
   - Fix: Reactive deinit fallback (detect error → deinit → retry with --force)

3. **Stale worktrees on create** (NEW)
   - Symptom: `repo create superset-shell master` produces worktree with master way behind origin, submodules on old commits
   - Root cause: local `master` branch in bare repo never fast-forwarded after fetch
   - Fix: Fast-forward local tracking branches after fetch, before worktree creation

---

## v0.1.3 Implementation Plans

### 3. Fast-forward local tracking branches on create (NEW)

**Problem**: When `repo create superset-shell master` is run, the worktree gets a stale `master` that's far behind `origin/master`. Submodules are also old because they're pinned to commits in the stale parent.

**Root Cause Analysis**:

When the bare repo already exists, the `create` command calls `fetch_repo()` (line 314, main.py) which updates `refs/remotes/origin/*`. But `create_worktree()` (git_ops.py, `has_local` path at lines 287-303) checks for a local branch first:

```python
if has_local:
    # Local branch exists - use it directly to preserve any unpushed commits
    subprocess.run(["git", "worktree", "add", worktree_path, branch], ...)
    return branch, False
```

This was designed to preserve unpushed commits on feature branches, but it causes `master`/`main` to be stale because those branches are never fast-forwarded. The fetch updated `origin/master` but the local `refs/heads/master` stays wherever it was.

**How claudette-cli solves it**: Uses a regular (non-bare) clone and runs `git pull origin master --ff-only` before creating worktrees. This ensures the base is always current.

**Accepted Solution**: Fast-forward local branches in `create_worktree()` when safe

The fix goes in `create_worktree()` in the `has_local` path (git_ops.py, lines 287-303, inside the outer `try` block at the same indentation level). Before checking out the local branch, attempt to fast-forward it to `origin/<branch>` if:
1. A remote-tracking branch `origin/<branch>` exists
2. The local branch is an ancestor of the remote (i.e., fast-forward is possible)

**Note on "checked out elsewhere"**: We do NOT need to guard against the branch being checked out in another worktree. `git worktree add` on line 296 will fail with "already checked out" if the branch is in use — git enforces this constraint for us. The fast-forward via `update-ref` before `worktree add` is safe even if the branch IS checked out elsewhere because: (a) `worktree add` will fail anyway, and (b) `update-ref` on a checked-out branch in a bare repo context only updates the ref, which is the correct behavior (the other worktree's HEAD symlink still points at the same ref name).

If fast-forward isn't possible (diverged commits), leave the local branch as-is — this preserves the existing safety behavior for feature branches with unpushed work.

**Implementation** — new helper function + updated `has_local` block (git_ops.py):

```python
def _try_fast_forward_branch(repo_path: Path, branch: str) -> None:
    """Attempt to fast-forward a local branch to match its remote-tracking branch.

    Safe: only updates when local is strictly behind remote (ancestor check).
    Effectively no-op when: no remote branch exists, branches have diverged,
    or local is already up-to-date (update-ref writes same SHA).

    Args:
        repo_path: Path to the bare repository
        branch: Name of the local branch to fast-forward
    """
    # Step 1: Check if remote-tracking branch exists
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "show-ref", "--verify",
             f"refs/remotes/origin/{branch}"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError:
        return  # No remote branch — nothing to fast-forward to

    # Step 2: Check if fast-forward is possible (local is ancestor of remote)
    # merge-base --is-ancestor returns: 0 = ancestor (or equal), 1 = not ancestor, 128 = error
    # Any non-zero means we should skip fast-forward (diverged or error)
    result = subprocess.run(
        ["git", "-C", str(repo_path), "merge-base", "--is-ancestor",
         f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return  # Diverged — preserve local commits

    # Step 3: Fast-forward local ref to match remote
    # update-ref with a ref name as new-value: git resolves it to SHA at call time
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "update-ref",
             f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError:
        pass  # update-ref failed (disk full, permissions, etc.) — proceed with stale branch
```

Then in `create_worktree()`, the `has_local` block becomes:

```python
if has_local:
    # Fast-forward local branch to match remote if possible
    _try_fast_forward_branch(repo_path, branch)

    # Create worktree from (now possibly updated) local branch
    subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "add",
         str(worktree_path), branch],
        check=True, capture_output=True, text=True,
    )
    return branch, False
```

**Why this approach**:
- **Safe**: `merge-base --is-ancestor` ensures we only update when local is strictly behind remote — no diverged commits are lost
- **Correct for bare repos**: `update-ref` works on bare repos (no working tree to update)
- **No new flags**: Always does the right thing — no `--pull` or `--fresh` opt-in needed
- **Submodule issue resolves itself**: If master is current, submodule pins are current too, so `init_submodules` checks out the right commits
- **Separated error handling**: `show-ref` failure (expected: no remote) is distinct from `update-ref` failure (unexpected: disk/permissions). Only `update-ref` failures are silently swallowed; `show-ref` returns early explicitly
- **Extracted helper**: `_try_fast_forward_branch` is independently testable, keeps `create_worktree` clean

**Why NOT other approaches**:
- **Option: Always use `-B` with remote**: Destructive — overwrites local-only commits on feature branches
- **Option: `--fresh` flag**: Adds complexity, user has to remember to use it, default behavior is still broken
- **Option: Only fast-forward default branch**: Too narrow — same issue affects any tracking branch (e.g., `develop`, `release/*`)

**Tests needed** (test_git_ops.py):

New tests for `_try_fast_forward_branch`:
1. Remote exists, local behind → `update-ref` called (fast-forward)
2. Remote exists, local diverged → `update-ref` NOT called
3. No remote-tracking branch → early return, no `merge-base` call
4. `update-ref` fails → exception swallowed, no re-raise
5. Local already up-to-date → `update-ref` called (harmless no-op)

Updated existing tests for `create_worktree` — patch `_try_fast_forward_branch` directly:
6. `test_create_worktree_existing_local_only_branch` — add `@patch("repo_cli.git_ops._try_fast_forward_branch")` to avoid coupling to helper internals. Keep existing `mock_run` side_effects (2 calls: show-ref local + worktree add). Assert helper was called with `(repo_path, branch)`.
7. `test_create_worktree_both_local_and_remote_uses_local` — same approach: patch helper, keep existing 2-call mock sequence, assert helper called.

**Placement**: `_try_fast_forward_branch` goes immediately before `create_worktree` (following the pattern of `_ensure_fetch_refspec` before `fetch_repo`).

**Files**: `git_ops.py`, `test_git_ops.py`

---

### 1. Atomic config writes (CRITICAL)

**Problem**: Direct write to YAML means any crash/power loss during save → corrupt config → CLI broken

**Implementation** (config.py):
```python
import os
import tempfile

def save_config(config: dict[str, Any]) -> None:
    """Save config with atomic write to prevent corruption."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (ensures same filesystem)
    fd, temp_path = tempfile.mkstemp(
        dir=config_path.parent,
        prefix=".config.",
        suffix=".yaml.tmp",
        text=True
    )

    try:
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic replace (POSIX guarantees atomicity)
        os.replace(temp_path, config_path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise
```

**Tests needed** (test_config.py):
- Test successful atomic write
- Test cleanup on write error
- Test fsync called

**Files**: `config.py`, `test_config.py`

---

### 2. Fix submodule removal error

**Approach**: Reactive with deinit fallback (simplified based on user insight)

**User insight**: "If we're deleting the worktree, just make git succeed" - no need for caching/proactive checks

**Implementation** (git_ops.py:246-265):
```python
from typing import Optional, Any

def remove_worktree(
    repo_path: Path,
    worktree_path: Path,
    console: Optional[Any] = None  # Rich Console or None (dependency injection)
) -> None:
    """Remove worktree, handling submodules if present.

    Strategy:
    1. Try normal removal first (fast path)
    2. On submodule error, deinit and retry with --force
    3. Provide clear feedback at each step (if console provided)

    Args:
        repo_path: Path to the bare repository
        worktree_path: Path to the worktree to remove
        console: Optional Rich console for user feedback (for interactive mode)

    Raises:
        GitOperationError: If removal fails

    Note:
        Uses dependency injection to avoid circular import (git_ops → main).
        Console parameter is optional - works in both interactive and programmatic contexts.
    """
    try:
        # Try normal removal first
        subprocess.run(
            ["git", "-C", str(repo_path), "worktree", "remove", str(worktree_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # Check if error is submodule-related
        if "submodule" in e.stderr.lower():
            # Provide feedback only if console is available
            if console:
                console.print("⚠️  Worktree contains submodules, deinitializing...", style="yellow")

            try:
                # Deinitialize submodules
                # --force: Remove even if working tree has local modifications
                # --all: Apply to all submodules
                subprocess.run(
                    ["git", "-C", str(worktree_path), "submodule", "deinit", "--all", "--force"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Retry removal with --force
                # --force: Remove even if worktree is dirty (after deinit, git may still think it's modified)
                subprocess.run(
                    ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(worktree_path)],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if console:
                    console.print("✓ Submodules deinitialized", style="green")

            except subprocess.CalledProcessError as submodule_error:
                # Provide context-specific error message
                raise GitOperationError(
                    f"Failed to remove worktree with submodules: {submodule_error.stderr}"
                ) from submodule_error
        else:
            # Re-raise with better error message
            raise GitOperationError(f"Failed to remove worktree: {e.stderr}") from e


# In main.py delete command, call with console parameter:
git_ops.remove_worktree(bare_repo_path, worktree_path, console=console)
```

**Why reactive approach:**
- Only pays cost when actually needed (most worktrees don't have submodules)
- Simpler than caching or proactive `.gitmodules` checks
- User doesn't care about performance when deleting
- No state management complexity

**Error scenarios handled:**
1. Normal removal works → Fast path, no output
2. Submodule blocks removal → User sees warning, then success message
3. Deinit succeeds but force removal fails → Clear error with context
4. Non-submodule error → Raised immediately with git's error message

**Why --force flags:**
- `submodule deinit --force`: Removes submodule even with uncommitted changes (user is deleting worktree anyway, local changes don't matter)
- `worktree remove --force`: Removes even if git detects "dirty" state (after deinit, git may still think worktree is modified)

**Tests needed** (test_git_ops.py):
- Test normal removal (no submodules)
- Test submodule fallback path
- Test non-submodule errors propagate

**Files**: `git_ops.py`, `test_git_ops.py`

---

## Deferred to v0.2.0

The following enhancements are deferred to v0.2.0 (bundled with directory restructure):

- `activate --shell` - Launch new shell in worktree
- `delete --delete-branch/--delete-remote` - Branch cleanup flags
- GitHub Enterprise / non-GitHub URL support
- `create --url` flag for automation
- Upgrade helper test coverage
- `repo pr open` - Open PR in browser

See PROJECT_v0.1.1.md for detailed implementation plans.

---

## Architecture

### Directory Layout
- Bare repos: `~/code/{repo}.git/`
- Worktrees: `~/code/{repo}-{branch}/` (percent-encoded)
- Config: `~/.repo-cli/config.yaml`

### Key Design Decisions
1. **Bare repo pattern** - No "main" checkout, all branches are worktrees
2. **Percent-encoding** - Bijective path encoding for branch names with special chars
3. **Auto-upgrade** - Self-update via git for easy maintenance
4. **Graceful degradation** - Works offline (PR status optional)
5. **Config migrations** - Automatic, transparent upgrades

### Config Structure
```yaml
version: "0.1.0"
base_dir: ~/code

repos:
  myrepo:
    url: git@github.com:user/repo.git
    owner_repo: user/repo

worktrees:
  myrepo::feature-123:
    repo: myrepo
    branch: feature-123
    pr: 4567
    start_point: origin/main
    created_at: 2025-11-12T10:00:00
```

---

## Commands Reference

### Core Commands
- `repo init` - Initialize configuration
- `repo register <alias> <url>` - Register repository
- `repo create <repo> <branch>` - Create worktree
- `repo list [repo]` - Display worktrees with PR status
- `repo delete <repo> <branch>` - Remove worktree
- `repo activate <repo> <branch>` - Navigate to worktree
- `repo pr link <repo> <branch> <pr#>` - Link PR

### Diagnostic Commands
- `repo --version` - Show version
- `repo doctor` - Run health checks
- `repo upgrade-check` - Check for updates
- `repo upgrade` - Auto-upgrade installation

### Shell Integration
```bash
# Jump to worktree
cd $(repo activate myrepo branch --print)

# Shell alias
alias ra='cd $(repo activate "$@" --print)'
```

---

## Technical Stack

- **Language**: Python ≥ 3.11
- **CLI Framework**: Typer (with auto-complete)
- **UI**: Rich (tables, colors)
- **Config**: YAML (PyYAML)
- **Git Integration**: subprocess wrappers
- **GitHub**: gh CLI integration (optional)
- **Dependencies**: typer, rich, pyyaml, packaging

---

## Roadmap

### v0.1.3 - Bug Fixes (Next)

Three fixes:
- ⏳ Atomic config writes - Prevent data corruption
- ⏳ Submodule deletion fix - Handle worktrees with submodules
- ⏳ Stale worktree fix - Fast-forward local branches on create

### v0.2.0 - Enhancements + Directory Structure Migration

**Enhancements** (deferred from v0.1.x):
- `activate --shell` - Launch new shell in worktree
- `delete --delete-branch/--delete-remote` - Branch cleanup flags
- GitHub Enterprise / non-GitHub URL support
- `create --url` flag for automation
- Upgrade helper test coverage
- `repo pr open` - Open PR in browser

**Breaking Change**: Migrate to nested directory structure (like claudette-cli)

**Current structure (flat):**
```
~/code/
├── superset.git/
├── superset-feature-123/
├── superset-bugfix-456/
├── preset.git/
└── preset-feature-789/
```

**New structure (nested):**
```
~/code/
├── superset/
│   ├── .bare/              # Bare repo (hidden)
│   ├── feature-123/        # Worktree
│   ├── bugfix-456/         # Worktree
│   └── main/               # Worktree
└── preset/
    ├── .bare/
    └── feature-789/
```

**Benefits:**
- Worktrees grouped by repo
- Cleaner base directory
- Natural hierarchy (repo contains branches)
- Shorter paths

**Migration plan with rollback support:**

```python
def migrate_directory_structure(config: dict[str, Any]) -> dict[str, Any]:
    """Migrate to new directory structure with rollback support.

    Old: base_dir/repo.git + base_dir/repo-branch/
    New: base_dir/repo/.bare/ + base_dir/repo/branch/

    5-step strategy:
    1. Backup config first
    2. Build migration plan (all worktrees to move)
    3. Execute moves one by one with logging
    4. On error: attempt rollback from backup
    5. Log all operations to migrations.log
    """
    import logging

    logger = logging.getLogger(__name__)
    config_path = get_config_path()
    base_dir = Path(config["base_dir"])

    # STEP 1: Create timestamped backup
    backup_path = config_path.with_suffix(f".yaml.backup.{int(time.time())}")
    if config_path.exists():
        shutil.copy2(config_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

    # STEP 2: Build migration plan
    migration_plan = []
    for worktree_key, worktree_data in config.get("worktrees", {}).items():
        repo, branch = worktree_key.split("::")
        old_path = Path(worktree_data["path"])
        new_path = base_dir / repo / branch

        if old_path.exists() and old_path != new_path:
            migration_plan.append({
                "key": worktree_key,
                "old": old_path,
                "new": new_path,
                "repo": repo,
                "branch": branch,
            })

    if not migration_plan:
        logger.info("No worktrees to migrate")
        return config

    logger.info(f"Planning to migrate {len(migration_plan)} worktrees")

    # STEP 3: Execute migrations with tracking
    migrated = []
    try:
        for item in migration_plan:
            logger.info(f"Migrating {item['key']}: {item['old']} -> {item['new']}")

            bare_repo = base_dir / f"{item['repo']}.git"
            item['new'].parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ["git", "-C", str(bare_repo), "worktree", "move",
                 str(item['old']), str(item['new'])],
                capture_output=True,
                text=True,
                check=True,
            )

            config["worktrees"][item['key']]["path"] = str(item['new'])
            migrated.append(item)
            logger.info(f"✓ Migrated {item['key']}")

    except subprocess.CalledProcessError as e:
        # STEP 4: Rollback on error
        logger.error(f"Migration failed: {e.stderr}")
        logger.warning(f"Attempting rollback of {len(migrated)} completed migrations...")

        rollback_failures = []
        for item in reversed(migrated):
            try:
                bare_repo = base_dir / f"{item['repo']}.git"
                subprocess.run(
                    ["git", "-C", str(bare_repo), "worktree", "move",
                     str(item['new']), str(item['old'])],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                logger.info(f"✓ Rolled back {item['key']}")
            except Exception as rollback_error:
                rollback_failures.append(item['key'])
                logger.error(f"✗ Failed to rollback {item['key']}: {rollback_error}")

        # Restore config from backup
        if backup_path.exists():
            shutil.copy2(backup_path, config_path)
            logger.info("Restored config from backup")

        if rollback_failures:
            raise Exception(
                f"Migration failed and rollback partially failed. "
                f"Manual intervention required for: {', '.join(rollback_failures)}. "
                f"Config backup available at: {backup_path}"
            )
        else:
            raise Exception(
                f"Migration failed but rollback succeeded. Original error: {e.stderr}"
            )

    # STEP 5: Save updated config (using atomic write from v0.1.1)
    save_config(config)
    logger.info(f"Migration complete. Backup retained at: {backup_path}")

    return config

# Logging setup
def setup_migration_logging() -> None:
    """Configure logging for migration operations."""
    log_path = get_config_path().parent / "migrations.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()  # Also print to console
        ]
    )
```

**Safety features:**
- ✅ Timestamped backup before any changes
- ✅ All operations logged to `~/.repo-cli/migrations.log`
- ✅ Automatic rollback on any failure
- ✅ Partial migration recovery (rolls back completed moves)
- ✅ Clear error messages for manual intervention if needed
- ✅ Backup retained for 30+ days (user can manually delete)
- ✅ Uses atomic config writes from v0.1.1

**Backward compatibility:**
- Detects old structure automatically (flat paths)
- Migrates transparently on first run after v0.2.0 upgrade
- Version bump to v0.2.0 (breaking change for manual scripts)

### v0.3.0 - Enhanced Workflows
- `repo pr create/open` - PR creation/opening
- `repo sync` - Fetch updates for repo
- Worktree git status indicators
- `repo upgrade --dry-run` - Preview changes
- Integration tests with real git operations

### v0.4.0 - Dependency Management
- `repo create --venv` - Auto-create Python venv
- `repo create --install` - Auto-install dependencies
- Per-repo setup hooks

### v0.5.0+ - Advanced Features
- Port allocation for dev servers
- Worktree templates
- Bulk operations (delete all merged)
- Cross-platform testing (Windows)
- Docker integration

---

## Known Limitations

### v0.1.0 Known Issues
- Upgrade commands depend on user environment (git, gh, uv)
- Full upgrade workflow not covered by automated tests
- Tested primarily on macOS (Git 2.40.0, gh 2.60.1)
- Real-world upgrade failures may vary by platform

### Monitoring Plan
Watch for:
1. Upgrade failures on different platforms
2. Issues with older Git versions (< 2.20)
3. Problems with pip vs uv installations
4. Network/firewall issues in upgrade-check

---

## Development

### Quick Start
```bash
# Clone and install
gh repo clone sadpandajoe/repo-cli
cd repo-cli
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Install globally
python3.11 -m pip install --user -e .
```

### Testing
- **135 tests** - All passing
- Unit tests for all modules
- E2E workflow tests
- Security/validation tests
- CI/CD with GitHub Actions

### Code Quality
- Ruff linting and formatting
- Pre-commit hooks
- Type hints throughout
- Comprehensive error handling

---

## Previous Work

All MVP development phases (Phase 1, 2, 3, Feedback Rounds 1-4, MVP polish) archived to **PROJECT_ARCHIVE.md**.

See archive for:
- Complete development timeline
- Technical implementation details
- All bug fixes and iterations
- Test development history
- Code review feedback

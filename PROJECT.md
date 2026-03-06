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

Fixes before v0.2.0 breaking change:

1. **Atomic config writes** (DONE - commit 658c3e1)
   - Dir fsync after os.replace for full crash durability

2. **Submodule deletion failure** (DONE - commit 658c3e1)
   - Reactive deinit fallback: detect error → deinit --all --force → retry remove --force
   - Console parameter for user feedback (dependency injection)

3. **Stale worktrees on create** (DONE - commit 9789283)
   - `_try_fast_forward_branch()` helper with 3-step safety (show-ref → merge-base → update-ref)

4. **Submodule init uses --remote** (DONE - commit 2cea31e)
   - Submodules now fetch latest from tracking branch instead of pinned commit

5. **Four bugs from code review** (DONE - commit 658c3e1)
   - Default-branch parsing with slashes (`release/2026` no longer truncated)
   - Race condition in `create_worktree` now raises instead of returning None
   - GitHub host detection: exact `github.com` match (no longer matches `notgithub.com`)
   - Dir fsync after `os.replace` for full crash durability

6. **Upstream tracking for worktrees** (DONE - uncommitted)
   - `_set_upstream_tracking()` sets `branch.<name>.remote/merge` after worktree creation
   - `git pull` now works without manual `--set-upstream-to`

7. **Stale local branches from bare clone** (DONE - uncommitted)
   - `_cleanup_stale_local_branches()` removes `refs/heads/*` duplicating `refs/remotes/origin/*`
   - Runs after every fetch; protects HEAD, worktree branches, diverged branches
   - `git branch` now shows only relevant branches instead of every remote branch

8. **Robust .gitmodules parsing** (DONE - uncommitted)
   - Replaced fragile line-based `path =` matching with `git config -f --get-regexp`
   - Handles all valid git config formatting (no spaces, tabs, etc.)

9. **Configurable --remote for submodules** (DONE - uncommitted)
   - `init_submodules()` now accepts `remote: bool = True` parameter
   - Callers can opt out with `remote=False` for reproducible/pinned builds

10. **Non-interactive TTY guards** (DONE - uncommitted)
    - `_confirm_or_fail()` helper: auto-accept with `--yes`, prompt on TTY, fail-fast on non-TTY
    - `--yes`/`-y` flag added to `register`, `create`, `delete`, `upgrade` commands
    - All 6 `typer.confirm()` call sites replaced with TTY-safe helper
    - 8 new tests for non-interactive paths (204 total tests)

---

## v0.1.3 Implementation Details

### Completed

**Fast-forward local tracking branches** (commit 9789283)
- `_try_fast_forward_branch()` helper in git_ops.py with 3-step safety: show-ref → merge-base --is-ancestor → update-ref
- Called in `create_worktree()` `has_local` path before `worktree add`
- Diverged branches preserved as-is; no "checked out elsewhere" guard needed (git enforces)

**Submodule init with --remote** (commit 2cea31e)
- `init_submodules()` now uses `--remote` flag to fetch latest from tracking branch
- Made configurable via `remote: bool = True` parameter (default preserves existing behavior)

**Robust .gitmodules parsing** (uncommitted)
- Replaced manual `path =` line matching with `git config -f .gitmodules --get-regexp`
- Handles all valid git config formatting variants (no spaces, tabs, mixed indentation)
- Error handling: exit code 1 (no matches) → return 0, other errors → `GitOperationError`

**Non-interactive TTY guards** (uncommitted)
- `_is_interactive()` + `_confirm_or_fail(message, yes)` helpers in main.py
- `--yes`/`-y` flag added to `register`, `create`, `delete`, `upgrade` commands
- Logic: `--yes` → auto-accept, TTY → prompt, non-TTY → fail-fast with guidance
- All 6 `typer.confirm()` calls replaced; existing `--force` flags unchanged

**Code review fixes** (commit 658c3e1)
- Default-branch slash parsing: `"/".join(parts[3:])` instead of `parts[-1]`
- Race condition guard: explicit `GitOperationError` when branch exists but neither ref resolves
- GitHub host detection: `host == "github.com"` instead of `"github" in host`
- Dir fsync after `os.replace()` in `save_config()`

**Upstream tracking** (uncommitted)
- `_set_upstream_tracking()` helper sets `branch.<name>.remote` and `branch.<name>.merge`
- Called in `create_worktree()` for both `has_local` and `has_remote` paths
- Skips when no remote-tracking branch exists (local-only branches)

**Stale branch cleanup** (uncommitted)
- `_cleanup_stale_local_branches()` helper in git_ops.py
- Compares `refs/heads/*` SHAs against `refs/remotes/origin/*` — deletes exact matches
- Protects: HEAD, worktree-checked-out branches, diverged branches, local-only branches
- Called from `fetch_repo()` after fetch (migration for existing repos + ongoing cleanup)
- Efficient: 4 git commands total (O(n) regardless of branch count)

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

- ✅ Stale worktree fix - Fast-forward local branches on create
- ✅ Submodule init --remote - Fetch latest tracking branch (now configurable)
- ✅ Slash branch names, race condition, GitHub host detection, dir fsync
- ✅ Submodule deletion fix - Handle worktrees with submodules
- ✅ Upstream tracking - `git pull` works in worktrees without manual setup
- ✅ Stale branch cleanup - `git branch` only shows relevant branches
- ✅ Robust .gitmodules parsing - `git config -f` instead of line matching
- ✅ Non-interactive TTY guards - `--yes` flag, fail-fast on non-TTY

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
- **204 tests** - All passing
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

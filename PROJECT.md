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
- User has git 2.5+ (worktree support)
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

## Current Status

**Active:**
- PR #3 ready to merge
- All code complete, rebased, and tested ✓

**Completed:**
- ✅ Phase 1: Project scaffolding (PR #1 merged to main)
- ✅ Phase 2: Core infrastructure, all MVP commands, CI/CD, tests (PR #2 merged to main)
- ✅ Phase 3: Auto-complete implementation, docs fixes, CI fixes (PR #3 created)
- ✅ All 43 tests passing
- ✅ Documentation updated and accurate
- ✅ Branch rebased successfully

**Pull Requests:**
- PR #1: Phase 1 scaffolding - ✅ Merged
- PR #2: Phase 2 core infrastructure - ✅ Merged
- PR #3: Phase 3 auto-complete - 🔄 Open (rebased, ready to merge)
  - 3 clean commits on top of main
  - https://github.com/sadpandajoe/repo-cli/pull/3

**Next:**
- Merge PR #3
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

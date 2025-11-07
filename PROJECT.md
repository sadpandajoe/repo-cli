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

## Development Log

### 2025-10-30 15:30 - Session Start: MVP Planning
User clarified scope into clear MVP after initial over-engineering discussion.

**Initial scope creep avoided:**
- No AI context management (out of scope - users manage their own files)
- No dependency management in MVP (can add later)
- No navigation helpers (paths are predictable)

**Architecture decisions finalized:**
1. **Directory Layout**: Bare repos at `~/code/{repo}.git/`, worktrees at `~/code/{repo}-{branch}/`
2. **Initial Clone**: Auto-clone as bare when repo doesn't exist
3. **PR Tracking**: Manual linking via `repo pr link`, store PR# in config, query status live (fallback to PR# only if offline)
4. **URL Resolution**: `repo register` command + lazy prompt fallback (both explicit and implicit registration)
5. **Auto-complete**: Included in MVP (Typer built-in support)
6. **Table display**: Repo | Branch | PR | Status (no Path column - predictable from repo+branch)

### 2025-10-30 16:00 - Planning Complete
All architectural decisions finalized. Ready to implement.

### 2025-10-30 17:30 - Documentation Fixes: Critical Issues Resolved
Fixed two critical bugs in the PROJECT.md specification before implementation:

**Issue 1 - Bare-repo worktree creation (High Priority):**
- **Problem**: `git worktree add ~/code/{repo}-{branch} -b {branch}` would fail on bare repos (no local HEAD to branch from)
- **Solution**: Use explicit start-point with `-C` flag: `git -C ~/code/{repo}.git worktree add <path> -b <branch> origin/HEAD`
- **Default behavior**: Use `origin/HEAD` (repo's default branch) as start-point
- **Flexibility**: Added `--from <start-point>` flag for custom base (tags, commits, branches - useful for hotfixes)
- **Config tracking**: Store `start_point` field in worktree metadata for reference
- **Command format**: Shows concrete example with `origin/HEAD`, note explains `--from` override

**Issue 2 - gh pr view repository context (Medium Priority):**
- **Problem**: `gh pr view <pr#>` can't infer repository context outside of a worktree directory
- **Initial approach**: Execute from worktree directory - REJECTED (fails if worktree deleted)
- **Final solution**: Parse and store `owner/repo` slug, use `gh pr view <pr#> --repo <owner_repo> --json state`
- **URL parsing**: Extract slug during `repo register`:
  - SSH: `git@github.com:owner/repo.git` → `owner/repo`
  - HTTPS: `https://github.com/owner/repo.git` → `owner/repo`
- **Benefit**: PR queries work even if worktree deleted, more reliable and explicit
- **Config changes**: Store `owner_repo` field for each repo in config

**Files updated:**
- PROJECT.md sections: `repo register`, `repo create`, `repo list`, `repo pr link` commands
- Phase 2 infrastructure documentation with explicit implementation requirements
- Config structure with `owner_repo` and `start_point` fields

### 2025-10-30 18:00 - Submodule Support Added to MVP
User identified that repositories with submodules need special handling.

**Decision: Automatic submodule initialization (included in MVP)**
- **Approach**: After creating worktree, automatically run `git -C <worktree_path> submodule update --init --recursive`
- **Rationale**: Submodules are common in real-world repos; manual initialization creates friction
- **Behavior**: Always automatic, no flag needed
- **User feedback**: Display count of initialized submodules (or omit message if none present)
- **Config tracking**: Not tracked - submodules are git's responsibility, not config concern
- **Performance note**: May be slow for repos with many/large submodules, but user expectation is that worktree is "ready to use"

**Implementation changes:**
- Added step 5 to `repo create` workflow: submodule initialization
- Updated output examples to show submodule initialization messages
- Enhanced `git_ops.py` implementation notes with submodule workflow
- No config schema changes needed (not tracked)

### 2025-10-30 19:00 - Phase 1: Project Scaffolding Started
Starting implementation of package structure following universal guidelines.

**Approach:**
- Following TDD principles from CLAUDE.implementation.md and CLAUDE.testing.md
- Creating minimal scaffolding first, then iterating
- Using uv for package management (modern Python tool)
- Typer for CLI framework (built-in auto-complete support)

### 2025-10-30 19:30 - Phase 1: Project Scaffolding Complete ✓
Successfully created complete package scaffolding with working CLI.

**Created:**
- `pyproject.toml` - Package configuration with dependencies (typer, rich, pyyaml)
  - Fixed deprecated `tool.uv.dev-dependencies` → `dependency-groups.dev`
  - No `gh` CLI as dependency (it's external system tool, not Python package)
- `README.md` - Comprehensive installation and usage guide
- `src/repo_cli/__init__.py` - Package initialization
- `src/repo_cli/main.py` - Typer CLI entry point with all commands
  - Commands: init, register, create, list, delete
  - Subcommand: pr link
  - All help text working correctly
- `src/repo_cli/commands/__init__.py` - Commands package structure
- `src/repo_cli/config.py` - Config management stubs with URL parsing
- `src/repo_cli/git_ops.py` - Git operations stubs (clone, worktree, submodules)
- `src/repo_cli/gh_ops.py` - GitHub CLI operations stubs (PR status)
- `src/repo_cli/utils.py` - Utility functions (path helpers, validation)

**Verified:**
- Package installs successfully with `uv pip install -e .`
- CLI runs: `repo --help` shows all commands
- All command help text displays correctly
- Typer auto-complete support included (--install-completion)
- Stub responses work ("🚧 Coming soon" messages)

**Technical Notes:**
- GitHub `owner/repo` slug will be parsed from URLs during registration
- `gh` CLI availability checked at runtime via `shutil.which('gh')`
- Graceful fallback when `gh` unavailable (show PR# only, no status)
- All git/gh operations via subprocess (no Python wrappers needed)

### 2025-10-30 20:00 - Phase 2: Core Infrastructure Implementation Complete ✓
Implemented all core infrastructure modules using TDD (RED → GREEN → REFACTOR).

**Core Modules Implemented:**

**config.py** - Configuration management (11 tests passing)
- `parse_github_url()` - Extract owner/repo slug from SSH/HTTPS URLs with validation
- `load_config()` - Load YAML with error handling (guards against None/invalid data)
- `save_config()` - Save YAML with automatic directory creation
- Guards against yaml.safe_load returning None or non-dict values

**git_ops.py** - Git subprocess wrappers (7 tests passing)
- `GitOperationError` exception class for user-friendly error messages
- `clone_bare()` - Clone repository as bare with error handling
- `create_worktree()` - Create worktree with configurable start point
- `remove_worktree()` - Remove worktree (requires repo_path for context)
- `init_submodules()` - Initialize submodules, count via .gitmodules parsing
- All functions wrap subprocess calls with CalledProcessError handling
- Surface git stderr in error messages instead of raw stack traces

**gh_ops.py** - GitHub CLI integration (10 tests passing)
- `is_gh_available()` - Check gh CLI via shutil.which
- `get_pr_status()` - Query PR status (Open/Merged/Closed) with --repo flag
- `validate_pr_exists()` - Validate PR existence
- Graceful fallback when gh unavailable/offline
- All PR queries use `--repo owner/repo` flag (works even if worktree deleted)

**main.py** - All MVP commands implemented
- `repo init` - Create config/directory with --force protection against overwrite
- `repo register` - Register repo aliases with URL validation
- `repo create` - Create worktrees with lazy registration, auto-clone, submodule init
- `repo list` - Display rich table with live PR status
- `repo delete` - Remove worktrees with confirmation prompt
- `repo pr link` - Link PRs with validation
- Rich console output (colors, tables, symbols)
- User-friendly error messages (no raw exceptions)
- Path objects converted to strings in output

**Code Review Fixes:**
- Data loss prevention: `repo init` won't overwrite without `--force`
- Config validation: Guards against empty/invalid YAML files
- Git error handling: GitOperationError with actionable messages
- UX polish: Clean output matching PROJECT.md examples
- Docstring accuracy: Fixed utils.py expand_path documentation

**Test Coverage:**
- 37/37 tests passing (28 unit + 9 integration)
- Unit tests: All core infrastructure with mocked subprocess
- Integration tests: End-to-end CLI testing with CliRunner
- Error handling verified with GitOperationError
- Edge cases covered (empty configs, offline scenarios, invalid URLs, filtered results)

**Technical Decisions:**
- Used subprocess.run for all git/gh operations (no third-party wrappers)
- Error handling catches CalledProcessError and raises GitOperationError
- Config file validated on load (must be dict, not None)
- Submodule count by parsing .gitmodules (reliable, works when already initialized)
- remove_worktree requires repo_path parameter for git context

### 2025-10-30 21:00 - CI/CD, Integration Tests, and Final Polish ✓
Added automated testing infrastructure and final UX improvements.

**CI/CD (GitHub Actions):**
- Created .github/workflows/ci.yml
- Tests on Python 3.11 and 3.12 (ubuntu-latest)
- Runs ruff linter and formatter checks
- Runs pytest with coverage reporting
- Verifies package builds successfully
- Triggers on every push/PR to main

**Ruff Linter:**
- Added ruff>=0.8.0 to dev dependencies
- Configured with sensible defaults (line-length 100, py311 target)
- Auto-formatted entire codebase (imports sorted, style consistent)
- Fixed all linting issues (unused imports, exception chaining, etc.)

**Integration Tests (9 new tests):**
Using typer.testing.CliRunner for end-to-end testing:
- repo init: Config creation, overwrite protection, --force flag
- repo register: URL parsing and validation
- repo list: Empty state, filtered empty state
- repo pr link: Success and error paths
- Tests run without touching git/gh (mocked or config-only)

**Final UX Polish:**
- repo init: Prevents accidental config overwrite without --force flag
- repo list: Shows friendly message when filtered results are empty
- repo create: Only shows submodule messages when .gitmodules exists
- All Path objects converted to strings in output (clean UX)

**Total Test Coverage: 37 passing tests**
- 11 tests: config.py (URL parsing, YAML I/O, validation)
- 7 tests: git_ops.py (git commands with error handling)
- 10 tests: gh_ops.py (gh CLI integration with fallback)
- 9 tests: CLI integration (end-to-end command orchestration)

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

## Current Status

**Active:**
- Phase 3 auto-complete complete ✓
- Ready for manual end-to-end testing

**Completed:**
- ✅ Phase 1: Project scaffolding (PR #1 merged)
- ✅ Phase 2: Core infrastructure, all MVP commands, CI/CD, tests (37 tests passing)
- ✅ Phase 3: Auto-complete implementation (43 tests passing)

**Next:**
- Commit Phase 3 changes
- Manual end-to-end testing of complete workflows
- Create PR for Phase 2+3 combined

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

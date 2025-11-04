# 🧱 REQUIREMENTS.md — Repo CLI MVP

## 📘 Overview

**Project:** `repo-cli`
**Purpose:** A lightweight CLI tool for managing git worktrees with PR tracking.
Simplifies the workflow of creating isolated branches, tracking their PRs, and managing multiple worktrees across repositories.

---

## 🧭 Goals

- **Simple worktree management:** No manual git worktree commands
- **PR tracking:** Link and view PR status alongside worktrees
- **Clean UX:** Rich table output, helpful error messages
- **Offline-friendly:** Gracefully degrades when GitHub CLI unavailable
- **Shell integration:** Auto-complete for repos and branches

---

## ⚙️ Technical Stack

| Component | Choice | Purpose |
|-----------|--------|---------|
| Language | Python ≥ 3.11 | Modern typing + pattern matching |
| CLI Framework | [Typer](https://typer.tiangolo.com/) | Built-in auto-complete, elegant API |
| UI / Tables | [Rich](https://rich.readthedocs.io/) | Console tables, colors, symbols |
| Config Format | YAML | Human-editable config |
| Package Manager | [uv](https://docs.astral.sh/uv/) | Fast install + dependency management |
| Testing | pytest + pytest-cov | Unit and integration testing |
| Git Integration | subprocess wrappers | No extra deps, full control |
| GitHub Integration | gh CLI | Optional PR status queries |

---

## 🧩 Directory Structure

```
repo-cli/
├── pyproject.toml           # Package config (uv + dependency-groups)
├── README.md                # User-facing docs
├── REQUIREMENTS.md          # This file
├── PROJECT.md               # Development log and decisions
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI
├── .pre-commit-config.yaml  # Pre-commit hooks
├── src/
│   └── repo_cli/
│       ├── __init__.py
│       ├── main.py          # CLI entry point + commands
│       ├── config.py        # YAML config management
│       ├── git_ops.py       # Git subprocess wrappers
│       ├── gh_ops.py        # GitHub CLI wrappers
│       └── utils.py         # Path helpers, validation
└── tests/
    ├── test_cli.py          # Integration tests (CliRunner)
    ├── test_config.py       # Config unit tests
    ├── test_git_ops.py      # Git operations unit tests
    └── test_gh_ops.py       # GitHub CLI unit tests
```

---

## ⚙️ Configuration

### Config File
```
~/.repo-cli/config.yaml
```

### Structure
```yaml
base_dir: ~/code

repos:
  preset:
    url: git@github.com:preset-io/preset.git
    owner_repo: preset-io/preset
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
  preset-bugfix-456:
    repo: preset
    branch: bugfix-456
    pr: null
    start_point: main
    created_at: 2025-10-30T16:00:00
```

### Auto-Creation Behavior
- `repo init` creates `~/.repo-cli/config.yaml` and base directory
- Refuses to overwrite existing config without `--force` flag

---

## 🧱 MVP Commands

### 🧭 Setup & Config

#### `repo init [--base-dir <path>] [--force]`
Initialize the CLI environment.

**Behavior:**
- Create `~/.repo-cli/config.yaml` with defaults
- Create base directory (default: `~/code`)
- Print setup instructions including auto-complete

**Output:**
```
✓ Created config at ~/.repo-cli/config.yaml
✓ Created base directory: ~/code
ℹ Run 'repo --install-completion' to enable auto-complete
ℹ Run 'repo create <name> <branch>' to get started
```

---

#### `repo register <alias> <url>`
Register a repository alias for easy reference.

**Behavior:**
- Validate git URL format (SSH or HTTPS)
- Parse owner/repo slug from GitHub URLs
- Save alias → URL mapping to config

**Output:**
```
✓ Registered 'preset' → git@github.com:preset-io/preset.git
✓ GitHub repo: preset-io/preset
```

---

### 🧩 Worktree Management

#### `repo create <repo> <branch> [--from <start-point>]`
Create a new worktree for a branch.

**Behavior:**
1. Check if alias exists (prompt for URL if not - lazy registration)
2. Clone bare repo if doesn't exist: `~/code/{repo}.git/`
3. Create worktree: `~/code/{repo}-{branch}/`
4. Initialize submodules automatically (if present)
5. Save worktree metadata to config

**Output:**
```
✓ Cloning preset as bare repository...
✓ Created worktree: ~/code/preset-feature-123
✓ Branch: feature-123 (new, from origin/HEAD)
✓ Initializing submodules...
✓ Initialized 3 submodules
```

---

#### `repo list [repo]`
Display all worktrees with PR status.

**Behavior:**
- Read worktree metadata from config
- Query PR status via `gh pr view <pr#> --repo <owner_repo> --json state`
- Graceful fallback when gh unavailable or offline
- Filter by repo if specified

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

---

#### `repo delete <repo> <branch> [--force]`
Remove a worktree.

**Behavior:**
- Confirm deletion (unless `--force`)
- Run: `git worktree remove ~/code/{repo}-{branch}`
- Remove from config metadata

**Output:**
```
⚠ Delete worktree 'preset-feature-123'? [y/N]: y
✓ Removed worktree: ~/code/preset-feature-123
```

---

### 🌐 GitHub Integration

#### `repo pr link <repo> <branch> <pr-number>`
Link a PR to a worktree.

**Behavior:**
- Validate worktree exists in config
- Optionally validate PR exists via `gh pr view <pr-number> --repo <owner_repo>`
- Store PR number in config

**Output:**
```
✓ Validated PR #4567 (Open) in preset-io/preset
✓ Linked to preset-feature-123
```

---

### 🛠️ Auto-complete

Built-in shell auto-complete support via Typer.

#### Installation
```bash
repo --install-completion  # Install for current shell
repo --show-completion     # Show completion script
```

#### Completions Provided
- Command names: `init`, `register`, `create`, `list`, `delete`, `pr`
- Repo aliases: read from config `repos:` keys
- Branch names: read from config `worktrees:` (all branches across repos)

---

## 🧪 Testing Requirements

### Test Coverage
- **43 passing tests** (28 unit + 15 integration)
- All core modules tested: config, git_ops, gh_ops, CLI commands
- Tests run in < 1 second

### Test Structure
```
tests/
├── test_cli.py         # Integration tests (Typer CliRunner)
├── test_config.py      # Config load/save/parse/validate
├── test_git_ops.py     # Git subprocess wrappers
└── test_gh_ops.py      # GitHub CLI integration
```

### CI/CD
- GitHub Actions workflow on push/PR
- Tests on Python 3.11 and 3.12
- Ruff linting and formatting checks
- Package build verification

---

## ✅ MVP Acceptance Criteria

**All Implemented:**
- ✅ User can run `repo init` to set up
- ✅ User can register repos via `repo register` or lazy prompt
- ✅ User can create worktrees with `repo create`
- ✅ User can see all worktrees with `repo list` (with PR status if available)
- ✅ User can delete worktrees with `repo delete`
- ✅ User can link PRs with `repo pr link`
- ✅ Auto-complete works for repos and branches
- ✅ All commands have helpful error messages
- ✅ Tool works offline (gracefully degrades PR status)
- ✅ 43 passing tests with CI/CD
- ✅ Ruff linting and formatting

---

## 🚀 Future Enhancements (Deferred)

**Phase 2 - PR Enhancements:**
- `repo pr open <repo> <branch>` - Open PR in browser
- `repo pr create <repo> <branch>` - Create new PR from branch
- Auto-detect PRs without manual linking

**Phase 3 - Workflow Enhancements:**
- `repo sync <repo>` - Fetch updates for repo
- Worktree git status indicators (dirty/clean/ahead/behind)

**Phase 4 - Dependency Management:**
- `repo create --venv` - Auto-create Python venv
- `repo create --install` - Auto-install dependencies
- Per-repo setup hooks (in config)

---

## 🧾 License
MIT License (2025)

## Overview
A lightweight CLI tool for managing git worktrees with PR tracking. Simplifies the workflow of creating isolated branches, tracking their PRs, and managing multiple worktrees across repositories.

## Current Status

**On `main`** — all work through PR #16 merged (2026-03-27)
- v0.2.0 nested directory structure (breaking change)
- PR open, link improvements, clickable PR links
- 220+ tests passing, lint clean

---

## Architecture

### Directory Layout (v0.2.0 nested)
- Repo parent: `~/code/{repo}/`
- Bare repos: `~/code/{repo}/.bare/`
- Worktrees: `~/code/{repo}/{branch}/` (percent-encoded)
- Config: `~/.repo-cli/config.yaml`

### Key Design Decisions
1. **Bare repo pattern** - No "main" checkout, all branches are worktrees
2. **Percent-encoding** - Bijective path encoding for branch names with special chars
3. **Auto-upgrade** - Self-update via git for easy maintenance
4. **Graceful degradation** - Works offline (PR status optional)
5. **Config migrations** - Automatic, transparent upgrades

### Config Structure
```yaml
version: "0.2.0"
base_dir: ~/code

repos:
  myrepo:
    url: git@github.com:user/repo.git
    owner_repo: user/repo
    setup:
      - npm ci
      - npm run build

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
- `repo sync [repo]` - Fetch latest from origin
- `repo setup add/remove/list <repo>` - Manage setup commands
- `repo pr link <repo> <branch> <pr#>` - Link PR
- `repo pr open <repo> <branch>` - Open PR in browser

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

### v0.3.0 - Enhanced Workflows
- ✅ `repo pr open` - Open PR in browser
- ✅ `repo sync` - Fetch updates for repo
- Worktree git status indicators
- `repo upgrade --dry-run` - Preview changes
- Integration tests with real git operations

### v0.4.0 - Dependency Management
- ✅ Per-repo setup commands (`repo setup add/remove/list`)
- ✅ `repo create` runs setup by default (skip with `--no-setup`)
- `repo create --venv` - Auto-create Python venv

### v0.5.0+ - Advanced Features
- Port allocation for dev servers
- Worktree templates
- Bulk operations (delete all merged)
- Cross-platform testing (Windows)
- Docker integration

---

## Known Limitations

- Upgrade commands depend on user environment (git, gh, uv)
- Full upgrade workflow not covered by automated tests
- Tested primarily on macOS (Git 2.40.0, gh 2.60.1)
- Real-world upgrade failures may vary by platform

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
- **257 tests** - All passing
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

All development from v0.1.0 through v0.2.0+ (PR #16) archived to **PROJECT_ARCHIVE.md**.

See archive for:
- Complete release history (v0.1.0–v0.2.0)
- Technical implementation details for all versions
- Bug fixes, investigations, and iterations
- Test development history
- Key decisions and lessons learned

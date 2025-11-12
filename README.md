# repo-cli

A lightweight CLI tool for managing git worktrees with PR tracking.

Simplifies the workflow of creating isolated branches using git worktrees, tracking their PRs, and managing multiple worktrees across repositories.

## Features (Planned)

- **Worktree Management**: Create and delete worktrees without manual git commands
- **Bare Repo Architecture**: Stores repos as bare at `~/code/{repo}.git/`, worktrees at `~/code/{repo}-{branch}/`
- **PR Tracking**: Link and view GitHub PR status alongside worktrees
- **Repo Aliasing**: Use short aliases instead of full URLs
- **Rich Table Display**: See all worktrees, branches, and PR status at a glance
- **Shell Auto-complete**: Tab completion for repos, branches, and commands

## Installation

### Prerequisites

- Python 3.11+
- Git 2.17+ (for worktree move support)
- `gh` CLI (optional, for PR features)

### Install from source

```bash
# Clone the repository
gh repo clone sadpandajoe/repo-cli
cd repo-cli

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Verify installation

```bash
repo --help
```

You should see the CLI help with available commands.

## Current Status

**✅ MVP Complete - Fully Functional**

All MVP commands are implemented and tested. Ready for production use.

### Features
- ✅ All commands working (init, register, create, list, delete, pr link)
- ✅ Shell auto-complete for repos and branches
- ✅ Configuration management with YAML persistence
- ✅ Git worktree operations via subprocess
- ✅ GitHub PR status integration (with graceful fallback)
- ✅ Rich console output (colors, tables, symbols)
- ✅ Comprehensive error handling (user-friendly messages)
- ✅ Security: Input validation, path traversal protection, safe alias management
- ✅ 81 passing tests with full security coverage
- ✅ CI/CD with GitHub Actions
- ✅ Ruff linting and formatting

## Usage

```bash
# Initialize configuration
repo init

# Register a repository
repo register myrepo git@github.com:user/repo.git

# Create a worktree for a branch
repo create myrepo feature-123

# List all worktrees
repo list

# Link a PR to a worktree
repo pr link myrepo feature-123 4567

# Delete a worktree
repo delete myrepo feature-123
```

## Naming Rules

### Branch Names

Branch names follow Git's official rules and support hierarchical grouping with slashes:

**Allowed:**
- Alphanumeric characters, dots, hyphens, underscores
- Forward slashes for hierarchical grouping (e.g., `feature/JIRA-123`, `bugfix/auth`)
- `@` symbol (except the sequence `@{`)

**Examples of valid branch names:**
```bash
repo create myrepo main
repo create myrepo feature/JIRA-123
repo create myrepo bugfix/foo@bar
repo create myrepo user/joe/feature
repo create myrepo release/v1.2.3
```

**Prohibited:**
- Cannot start or end with `/`
- Cannot contain consecutive slashes `//`
- Cannot contain `..` or `@{`
- Cannot end with `.`
- Slash-separated components cannot start with `.` or end with `.lock`
- Cannot contain spaces, `~`, `^`, `:`, `?`, `*`, `[`, `\`

### Repository Aliases

Repository aliases have stricter rules to prevent path traversal attacks:

**Allowed:**
- Alphanumeric characters, dots, hyphens, underscores only
- No slashes (path traversal protection)
- Cannot contain `::` (internal delimiter)

**Examples:**
```bash
repo register myrepo git@github.com:user/repo.git          # Valid
repo register api-core git@github.com:company/api-core.git # Valid
repo register my.repo git@github.com:user/my.repo.git      # Valid
```

**Invalid examples:**
```bash
repo register my/repo ...     # Error: slashes not allowed
repo register ../prod ...     # Error: path traversal blocked
repo register repo::name ...  # Error: :: is internal delimiter
```

## Known Limitations

### Config Key Collision (Fixed in v0.1.0)

**Status**: ✅ **FIXED** - Config keys now use `::` delimiter instead of `-`.

**Previous Issue**: Keys like `f"{repo}-{branch}"` could collide (e.g., `api-core` + `feature` vs `api` + `core-feature`).

**Fix**: Changed to `f"{repo}::{branch}"` format, which cannot collide because `::` is prohibited in repo aliases.

**Migration**: No migration needed - v0.1.0 uses new format from the start.

**Future**: v0.2.0 will implement nested dict structure (`worktrees[repo][branch]`) with automatic migration for any v0.1.0 configs.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/sadpandajoe/repo-cli.git
cd repo-cli

# Option 1: Using uv (recommended)
uv sync --dev

# Option 2: Using pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

**Note:** Complete the setup steps above before running tests. The package must be installed in development mode for tests to import the `repo_cli` module.

```bash
# With uv (recommended - handles installation automatically)
uv run pytest tests/ -v

# With pip (requires editable install: pip install -e ".[dev]")
pytest tests/ -v

# With coverage
uv run pytest tests/ -v --cov=repo_cli --cov-report=term-missing
```

### Code Quality

```bash
# Install pre-commit hooks (recommended)
pre-commit install

# Run linting
uv run ruff check src/ tests/

# Run formatting
uv run ruff format src/ tests/

# Run pre-commit on all files
pre-commit run --all-files
```

### Pre-commit Hooks

The project uses pre-commit to automatically check code quality before commits:
- **ruff** - Linting with auto-fix
- **ruff-format** - Code formatting
- **trailing-whitespace** - Remove trailing whitespace
- **end-of-file-fixer** - Ensure files end with newline
- **check-yaml** - Validate YAML files
- **check-added-large-files** - Prevent large files

After installing (`pre-commit install`), these checks run automatically on every commit.

## Architecture

- **Base Directory**: `~/code/`
- **Bare Repos**: `~/code/{repo}.git/`
- **Worktrees**: `~/code/{repo}-{branch}/`
- **Config**: `~/.repo-cli/config.yaml`

## License

MIT

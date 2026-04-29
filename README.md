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
repo --version  # Check installed version
```

You should see the CLI help with available commands.

## Upgrading

### Automatic Upgrade (Recommended)

Check for updates and upgrade automatically:

```bash
# Check if newer version is available
repo upgrade-check

# Upgrade to the latest version
repo upgrade

# Skip safety checks (use with caution)
repo upgrade --force
```

The upgrade command will:
- Auto-detect your installation directory
- Check for uncommitted changes and warn you
- Pull latest changes from your current branch
- Reinstall dependencies (using uv or pip)
- Provide clear progress indicators

### Manual Upgrade

If you prefer manual control:

```bash
# If installed with uv
cd /path/to/repo-cli
git pull origin main
uv sync --dev

# If installed with pip
cd /path/to/repo-cli
git pull origin main
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### After Upgrading

Verify the new version:

```bash
repo --version
```

If you encounter any issues, run diagnostics:

```bash
repo doctor
```

## Current Status

**✅ MVP Complete - Fully Functional**

All MVP commands are implemented and tested. Ready for production use.

### Features
- ✅ All core commands (init, register, unregister, create, list, delete, activate, pr link)
- ✅ Diagnostic tools (--version, doctor, upgrade-check)
- ✅ Automatic upgrades (upgrade command with safety checks)
- ✅ Shell auto-complete for repos and branches
- ✅ Configuration management with YAML persistence
- ✅ Git worktree operations via subprocess
- ✅ GitHub PR status integration (with graceful fallback)
- ✅ Rich console output (colors, tables, symbols)
- ✅ Comprehensive error handling (user-friendly messages)
- ✅ Security: Input validation, path traversal protection, safe alias management
- ✅ 127 passing tests with full E2E coverage
- ✅ CI/CD with GitHub Actions
- ✅ Ruff linting and formatting

## Usage

### Basic Commands

```bash
# Initialize configuration
repo init

# Check version
repo --version

# Run diagnostics
repo doctor

# Check for updates
repo upgrade-check

# Upgrade to latest version
repo upgrade

# Register a repository
repo register myrepo git@github.com:user/repo.git

# Create a worktree for a branch
repo create myrepo feature-123

# List all worktrees
repo list

# Navigate to a worktree (prints path with cd hint)
repo activate myrepo feature-123

# Link a PR to a worktree
repo pr link myrepo feature-123 4567

# Delete a worktree
repo delete myrepo feature-123

# Unregister a repository alias (errors if worktrees exist; --force overrides)
repo unregister myrepo
repo unregister myrepo --force --remove-data --yes
```

### Shell Integration

For quick navigation, use the `--print` flag with shell command substitution:

```bash
# Jump directly to a worktree
cd $(repo activate myrepo feature-123 --print)

# Or create an alias in your .bashrc/.zshrc
alias repoa='cd $(repo activate "$@" --print)'
repoa myrepo feature-123
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

## Unregistering a Repository

Use `repo unregister` to remove a repo alias from your config. It is the inverse of `repo register`.

```bash
# Unregister an alias with no active worktrees (interactive confirmation)
repo unregister myrepo

# Skip the confirmation prompt
repo unregister myrepo --yes
```

By default, `unregister` refuses to remove an alias that still has worktrees. Delete the worktrees first with `repo delete`, or pass `--force` to also remove their config entries:

```bash
# Drop config entries for any remaining worktrees too
repo unregister myrepo --force --yes
```

`--force` only updates the config. The bare repo and worktree directories on disk are left intact unless you also pass `--remove-data`:

```bash
# Also rmtree the on-disk bare repo and worktree directories
repo unregister myrepo --force --remove-data --yes
```

`--remove-data` only deletes paths it positively recognizes as repo-cli-managed:

- nested layout (v0.2.0+): `<base_dir>/<alias>/.bare`
- legacy flat layout: `<base_dir>/<alias>.git` and `<base_dir>/<alias>-<branch>`

A directory at `<base_dir>/<alias>` without a `.bare` child is treated as unrelated user data and left untouched, with a warning.

In an interactive shell, `repo unregister` will also offer to delete on-disk data if you didn't pass `--remove-data` — answer `y` at the follow-up prompt. With `--yes` (or in a non-interactive context), data is left on disk if `--remove-data` wasn't explicitly passed; run `repo doctor` to surface orphaned directories or `rm -rf` them manually.

### Finding Orphaned Data

`repo doctor` scans `<base_dir>` for repo directories whose alias isn't registered (e.g. left behind after `repo unregister` without `--remove-data`, or moved manually) and lists them so you can adopt them with `repo register` or remove them with `rm -rf`.

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

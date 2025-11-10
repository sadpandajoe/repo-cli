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
- Git 2.5+ (for worktree support)
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

## Known Limitations

### Config Key Collision (Fixed in v0.2.0)

**Issue**: Worktree config keys use the format `f"{repo}-{branch}"`, which can collide in edge cases.

**Example Collision**:
- Repo `api-core` with branch `feature-123` → key: `api-core-feature-123`
- Repo `api` with branch `core-feature-123` → key: `api-core-feature-123` (same!)

**Impact**: Creating the second worktree would silently overwrite the first entry in config, causing commands like `list`, `delete`, and `pr link` to operate on the wrong worktree.

**Workaround**: Avoid using repo aliases that could create ambiguous keys:
- Don't use repo aliases ending with `-X` where X is another registered repo name
- Example: If you have repo `api`, avoid registering `api-core` or `my-api`

**Status**: This will be fixed in v0.2.0 with a nested dict structure (`worktrees[repo][branch]`) and automatic config migration.

**Why Deferred?**
- Pre-v0.1.0 release with no production users
- Collision is unlikely in typical usage patterns
- More critical security issues (path traversal, silent overwrites) fixed first
- Proper structural fix requires config migration logic

## Development

```bash
# Install with dev dependencies
uv sync --dev

# Install pre-commit hooks (recommended)
pre-commit install

# Run tests
uv run pytest tests/ -v

# Run linting
uv run ruff check src/ tests/

# Run formatting
uv run ruff format src/ tests/

# Run pre-commit on all files
pre-commit run --all-files

# Check current structure
find src -name "*.py" | sort
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

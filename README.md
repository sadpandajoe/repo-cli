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

**🚧 Under Active Development - MVP Phase**

The package structure is complete with command stubs. Core functionality is being implemented.

### Working
- CLI scaffolding with Typer
- Command structure (init, register, create, list, delete, pr link)

### In Progress
- Core infrastructure (config management, git operations, gh integration)

### Not Yet Implemented
- Actual command implementations
- Configuration file handling
- Git worktree operations
- PR status integration

## Usage (Planned)

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

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests (when implemented)
pytest

# Check current structure
tree src/
```

## Architecture

- **Base Directory**: `~/code/`
- **Bare Repos**: `~/code/{repo}.git/`
- **Worktrees**: `~/code/{repo}-{branch}/`
- **Config**: `~/.repo-cli/config.yaml`

## License

MIT

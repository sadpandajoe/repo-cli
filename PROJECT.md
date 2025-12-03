## Overview
A lightweight CLI tool for managing git worktrees with PR tracking. Simplifies the workflow of creating isolated branches, tracking their PRs, and managing multiple worktrees across repositories.

## Current Status

**v0.1.1 In Progress** - 2025-12-03

Post-release improvements and bug fixes.

- ✅ 140 passing tests (5 new)
- ✅ Phase 0 complete: HEAD branch creation bug fix
- ⏳ Phase 1-4: 8 improvements remaining
- 🎯 Next: Atomic config writes (Phase 1)

**v0.1.0 Released** - 2025-11-12

Production-ready MVP with all core functionality complete.

- ✅ 135 passing tests
- ✅ CI/CD green (Python 3.11 and 3.12)
- ✅ Complete documentation (README, CHANGELOG)
- ✅ GitHub release: https://github.com/sadpandajoe/repo-cli/releases/tag/v0.1.0

### Previous Releases

**v0.1.0** - 2025-11-12
- Core commands: init, register, create, list, delete, activate, pr link
- Diagnostic tools: --version, doctor, upgrade-check, upgrade
- Shell integration with --print flag
- 135 comprehensive tests
- See PROJECT_ARCHIVE.md for complete development history

---

## Active Work

**Current Focus**: Post-release improvements (v0.1.1 - EXPANDED SCOPE)

### 2025-12-03 - Implementation: HEAD Branch Creation Bug Fix (COMPLETED)

**Session Summary**: Implemented and improved HEAD branch creation bug fix with code review feedback.

**Implementation Phase 1 - Initial Fix** (Commit: 9817414):
- Followed TDD: RED → GREEN → REFACTOR
- Added 3 failing tests for edge cases (HEAD literal, remote ref, custom ref)
- Implemented validation: raise ValueError for non-`refs/heads/*` formats
- Modified exception handler to catch both CalledProcessError and ValueError
- All 138 tests passing (3 new tests added)

**Code Review & Improvements** (Commit: 1386f12):
Addressed 3 critical issues identified in code review:

1. **Remote HEAD Resolution** (Issue #1):
   - Problem: `refs/remotes/origin/HEAD` dropped straight to main/master fallback
   - Impact: Repos with develop/trunk default branches would fail
   - Fix: Resolve remote HEAD to actual target branch via `git symbolic-ref`
   - Extract branch name from `refs/remotes/origin/develop` → `develop`
   - Gracefully fallback if resolution fails

2. **Master Existence Check** (Issue #2):
   - Problem: Final fallback returned "master" without verification
   - Impact: Confusing "invalid ref" errors from git worktree add
   - Fix: Verify master exists before returning it
   - Raise clear GitOperationError if neither main nor master exists
   - Error message: "Could not determine default branch. Repository has neither 'main' nor 'master' branch."

3. **Test Accuracy** (Issue #3):
   - Updated remote HEAD test to expect resolution (not fallback)
   - Added test for remote HEAD resolution failure
   - Added test for missing main/master branches with proper error
   - Updated fallback test for new call count (3 instead of 2)

**Final Results**:
- ✅ All 140 tests passing (5 new tests total)
- ✅ Pre-commit hooks pass (ruff, ruff-format)
- ✅ Handles repos with develop, trunk, or other non-standard defaults
- ✅ Clear error messages for edge cases
- ✅ No breaking changes

**Commits**:
- 9817414: fix: prevent invalid branch names in get_default_branch
- 1386f12: fix: improve get_default_branch edge case handling

**Files Modified**:
- src/repo_cli/git_ops.py: 52 lines added (45 + 7)
- tests/test_git_ops.py: 116 lines added (49 + 67)

**Status**: ✅ COMPLETE - Ready for next v0.1.1 improvement

---

### 2025-11-19 - Investigation: HEAD Branch Creation Bug (ARCHIVED)

**The Problem**:
- `get_default_branch()` can return invalid branch names like "HEAD" or "refs/remotes/origin/HEAD"
- Creates branches with invalid names, breaks git workflows

**Root Cause**:
- Location: src/repo_cli/git_ops.py:82-84
- If `symbolic-ref HEAD` returns anything except `refs/heads/X`, raw value was returned

**Investigation Timeline**:
- 14:30: User reported issue
- 14:35: Found bug
- 14:45: Root cause identified

**Resolution**: See 2025-12-03 implementation above

---

### 2025-11-13 - Development Log

**Session Start**: Validated comprehensive code review feedback, expanded v0.1.1 scope from 3 to 8 improvements.

**Planning Phase Complete**: All five code review items validated as legitimate issues with accurate severity ratings.

**Critical Planning Flaws Fixed**: Fixed 4 critical implementation bugs in planning documentation before any code was written:

1. **Shell activation broken** - Added `-i` flag for interactive mode (prevents immediate exit), added `shlex.quote()` for shell escaping (prevents injection on branches with spaces/quotes), fixed "other shells" fallback to actually source temp script
2. **Circular dependency** - Changed `remove_worktree()` to use dependency injection for console parameter (prevents `git_ops → main → git_ops` circular import)
3. **GHE scope clarified** - Using graceful degradation instead of explicit GHE support (accepts all git URLs, disables PR features for non-GitHub, no commitment to test GHE)
4. **Branch merge validation** - Added `--format=%(refname:short)` for exact matching (prevents "fix" matching "hotfix"), added `into_branch` parameter (removes HEAD dependency), works correctly in bare repos

All fixes applied to PROJECT.md planning documentation. v0.1.0 codebase remains clean (these issues were caught before implementation).

---

### v0.1.1 Scope: Nine Improvements (3 Original + 5 Code Review + 1 Bug Fix)

#### Critical Bug Fix (Completed 2025-12-03) ✅
1. **HEAD branch creation bug** (git_ops.py:62-142) - COMPLETE
   - ✅ Validates ref format, raises ValueError for non-`refs/heads/*`
   - ✅ Resolves remote HEAD refs to actual target branch (develop, trunk, etc.)
   - ✅ Verifies master exists before returning as fallback
   - ✅ Clear error if neither main nor master exists
   - ✅ 5 new tests, all 140 tests passing
   - Commits: 9817414, 1386f12

#### Original User Feedback (3 items)
1. Activate command should launch a new shell (like claudette-cli), not just print path
2. Delete command should offer to delete the branch (local and remote), not just worktree
3. Submodule removal failing: "fatal: working trees containing submodules cannot be moved or removed"

#### Code Review Feedback (5 items - ALL VALIDATED)

**High Priority (Critical Fixes)**
1. **Config corruption risk** (config.py:177-193)
   - Current: `save_config` writes directly to YAML file
   - Risk: Process crash mid-write → corrupt/empty config → CLI unusable
   - Impact: Config written in init, register, create, delete, pr link, migrations
   - Fix: Atomic writes (temp file + os.replace + fsync)

2. **Submodule deletion failure** (git_ops.py:246, main.py:428) - *Already planned*
   - Current: Single `git worktree remove`, fails on initialized submodules
   - Fix: Reactive deinit fallback (detect error → deinit → retry with --force)

**Medium Priority (User Experience)**
3. **GitHub Enterprise blocked** (config.py:195-224)
   - Current: `parse_github_url` hardcodes github.com regex patterns
   - Impact: Corporate GitHub Enterprise hosts rejected, other git hosts (GitLab, etc.) blocked
   - Fix: Make hostname configurable OR accept arbitrary git URLs

4. **Automation hangs** (main.py:258-273)
   - Current: `typer.prompt` blocks in CI/scripted environments when repo not registered
   - Fix: Add `--url` flag + stdin interactivity check

**Low Priority (Testing/Polish)**
5. **Upgrade helpers untested** (git_ops.py:333-491, test_git_ops.py)
   - Current: 6 upgrade functions (get_remote_url, set_remote_url, get_latest_tag, get_current_branch, has_uncommitted_changes, pull_latest) have zero tests
   - Risk: Regressions in upgrade flow (tag parsing, detached HEAD handling) slip through CI
   - Fix: Add unit tests with mocked subprocess.run

**Summary**: All 5 code review items validated with evidence from codebase. Severity ratings accurate. Implementation plans documented below.

---

## Refined Implementations

### 0. Fix HEAD branch creation bug (CRITICAL)

**Approach**: Validate ref format and use existing fallback logic

**Problem**: `get_default_branch()` returns raw ref value when `symbolic-ref HEAD` returns unexpected formats, causing branches named "HEAD" or "refs/remotes/origin/HEAD" to be created.

**Implementation** (git_ops.py:62-98):

```python
def get_default_branch(repo_path: Path) -> str:
    """Get the default branch for the repository.

    Args:
        repo_path: Path to the bare repository

    Returns:
        Name of the default branch (e.g., 'master', 'main')
    """
    try:
        # Read HEAD to find default branch
        result = subprocess.run(
            ["git", "-C", str(repo_path), "symbolic-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        # Output is like "refs/heads/master"
        ref = result.stdout.strip()

        # Extract branch name - ONLY if in expected format
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/") :]

        # FIXED: If unexpected format, fall through to fallback logic
        # instead of returning raw ref
        raise ValueError(f"Unexpected ref format: {ref}")

    except (subprocess.CalledProcessError, ValueError):
        # Fallback to main/master
        # Check if main exists
        try:
            subprocess.run(
                ["git", "-C", str(repo_path), "show-ref", "--verify", "refs/heads/main"],
                check=True,
                capture_output=True,
                text=True,
            )
            return "main"
        except subprocess.CalledProcessError:
            # Default to master
            return "master"
```

**Why this approach:**
- Minimal change to existing code
- Reuses existing fallback logic (main/master checking)
- Prevents any invalid ref from being used as a branch name
- ValueError triggers fallback path safely
- No new dependencies or complexity

**Edge cases handled:**
1. `symbolic-ref HEAD` returns "HEAD" → fallback to main/master
2. Returns "refs/remotes/origin/HEAD" → fallback to main/master
3. Returns corrupted/custom ref → fallback to main/master
4. Normal case "refs/heads/main" → works as before

**Files**: `git_ops.py`, `test_git_ops.py`

**Tests needed:**
- Test unexpected ref format triggers fallback
- Test "HEAD" literal triggers fallback
- Test "refs/remotes/origin/HEAD" triggers fallback
- Test normal case still works

---

### 1. Add `--shell` flag to activate command

**Approach**: Follow claudette-cli pattern (researched from https://github.com/mistercrunch/claudette-cli)

**Key learnings from claudette:**
- Uses `subprocess.run()` WITHOUT PTY module (delegates terminal I/O to spawned shell)
- Creates temporary activation script that sources user's RC file
- Shell-specific invocation: bash uses `--rcfile`, zsh needs wrapper script
- Cleans up temp files in `finally` block
- No need for `pty`, `termios`, `tty`, or `signal` modules

**Implementation** (main.py:481-543):

```python
import shlex  # For shell-safe variable escaping
import tempfile
from pathlib import Path

# Add --shell parameter
shell: Annotated[bool, typer.Option("--shell", "-s", help="Launch new shell in worktree")] = False

# Validate mutual exclusivity
if shell and print_only:
    console.print("Error: --shell and --print are mutually exclusive", style="red")
    sys.exit(1)

# Launch shell if requested
if shell:
    # Robust shell fallback chain
    shell_path = os.environ.get('SHELL')
    if not shell_path or not Path(shell_path).exists():
        # Try common shells in order
        for fallback in ['/bin/bash', '/bin/zsh', '/bin/sh']:
            if Path(fallback).exists():
                shell_path = fallback
                break
        else:
            console.print("Error: No shell found. Set $SHELL environment variable.", style="red")
            sys.exit(1)

    shell_name = Path(shell_path).name

    # Shell-escape variables to prevent injection
    # CRITICAL: Branches can contain spaces, quotes, or special chars
    safe_repo = shlex.quote(repo)
    safe_branch = shlex.quote(branch)
    safe_worktree = shlex.quote(str(worktree_path))

    # Determine RC file based on shell
    if shell_name == "zsh":
        user_rc = "~/.zshrc"
    elif shell_name == "fish":
        user_rc = "~/.config/fish/config.fish"
    else:
        user_rc = "~/.bashrc"

    # Create activation script (using escaped variables)
    activate_script = f"""
# Source user's rc file first
source {user_rc} 2>/dev/null || true

# Modify prompt if supported (using shell-escaped values)
if [ -n "$PS1" ] && ([ -n "$BASH_VERSION" ] || [ -n "$ZSH_VERSION" ]); then
    PS1="(repo:{safe_repo}:{safe_branch}) $PS1"
fi

# Show entry message (using shell-escaped values)
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Worktree {safe_repo}:{safe_branch} activated"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "✓ Directory: {safe_worktree}"
echo
echo "💡 This is a nested shell session. Press Ctrl+D to exit."
echo
"""

    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(activate_script)
        temp_script = f.name

    try:
        if shell_name == "bash":
            # Bash: use --rcfile flag (not -l login shell)
            # Why --rcfile instead of -l?
            # - Login shells reload entire environment (can interfere with current session)
            # - --rcfile just loads user customizations
            # - User is already in a logged-in session
            # CRITICAL: -i flag required for interactive mode, otherwise bash exits immediately
            subprocess.run(
                ["bash", "-i", "--rcfile", temp_script],
                cwd=str(worktree_path),
                check=False,
            )
        elif shell_name == "zsh":
            # Zsh: needs wrapper script (no --rcfile support)
            wrapper_script = f"""#!/bin/zsh
source ~/.zshrc 2>/dev/null || true
source {shlex.quote(temp_script)}
"""
            temp_wrapper = temp_script + "_wrapper.zsh"
            with Path(temp_wrapper).open("w") as f:
                f.write(wrapper_script)
            os.chmod(temp_wrapper, 0o755)

            # CRITICAL: -i flag required for interactive mode
            subprocess.run(
                ["zsh", "-i", temp_wrapper],
                cwd=str(worktree_path),
                check=False,
            )
            Path(temp_wrapper).unlink(missing_ok=True)
        else:
            # Other shells: source script then exec interactive shell
            # CRITICAL: Must actually source the temp script for PS1/banner to appear
            subprocess.run(
                [shell_path, "-c", f"source {shlex.quote(temp_script)}; exec {shell_path} -i"],
                cwd=str(worktree_path),
                check=False,
            )
    finally:
        # Clean up temp script
        Path(temp_script).unlink(missing_ok=True)

    console.print(f"Exited {repo}:{branch}", style="yellow")
    return
```

**Why this approach:**
- Proven pattern from claudette-cli (handles bash, zsh, fish correctly)
- No PTY complexity (shell handles terminal I/O natively)
- Loads login/rc files via shell's native mechanisms
- TTY/signal handling: subprocess.run() inherits parent's TTY by default
  - Ctrl+C, Ctrl+D, and job control signals work automatically
  - No need for manual signal handlers or pty.spawn()
  - Shell's built-in signal handling takes over
- Robust fallback chain prevents "no shell found" errors
- Simple cleanup with try/finally

**Files**: `main.py` (activate command), `test_cli.py`

---

### 2. Add branch deletion to delete command

**Approach**: Centralized via BranchDeletionPlan dataclass (addresses feedback about flag drift)

**New structure** (git_ops.py):
```python
from dataclasses import dataclass

@dataclass
class BranchDeletionPlan:
    """Centralized plan for branch deletion operations."""
    delete_local: bool
    delete_remote: bool
    force: bool
    remote_name: str = "origin"

    @classmethod
    def from_flags(
        cls,
        delete_branch: bool,
        delete_remote: bool,
        force: bool,
        repo_path: Path,
        branch: str
    ) -> "BranchDeletionPlan":
        """Create plan from CLI flags with validation."""
        # Validate: --delete-remote requires --delete-branch
        if delete_remote and not delete_branch:
            raise ValueError("--delete-remote requires --delete-branch")

        # Detect upstream remote
        remote = "origin"
        if delete_remote:
            upstream_remote = get_upstream_remote(repo_path, branch)
            if upstream_remote:
                remote = upstream_remote

        return cls(
            delete_local=delete_branch,
            delete_remote=delete_remote,
            force=force,
            remote_name=remote
        )

    def describe(self) -> list[str]:
        """Return list of operations for confirmation prompt."""
        operations = ["Remove worktree"]
        if self.delete_local:
            operations.append(f"Delete local branch{' (forced)' if self.force else ''}")
        if self.delete_remote:
            operations.append(f"Delete remote branch on {self.remote_name}")
        return operations

# Example instantiation:
# plan = BranchDeletionPlan(
#     delete_local=True,
#     delete_remote=True,
#     force=False,
#     remote_name="upstream"
# )
# plan.describe() → ['Remove worktree', 'Delete local branch', 'Delete remote branch on upstream']
```

**New git operations** (git_ops.py):
```python
def is_branch_merged(repo_path: Path, branch: str, into_branch: str = "main") -> bool:
    """Check if a branch has been merged into another branch.

    Args:
        repo_path: Path to the repository (bare or regular)
        branch: Branch name to check
        into_branch: Target branch to check against (default: "main")

    Returns:
        True if branch has been merged into into_branch

    Note:
        Uses git branch --merged with --format for exact name matching.
        Works correctly in bare repositories without HEAD dependency.

    Examples:
        is_branch_merged(repo, "fix", "main") -> False if "hotfix" merged but "fix" not
        is_branch_merged(repo, "feature-123", "develop") -> True if merged into develop
    """
    try:
        result = subprocess.run(
            [
                "git", "-C", str(repo_path),
                "branch",
                "--merged", into_branch,  # Explicitly specify target branch (no HEAD dependency)
                "--format=%(refname:short)",  # Output just branch names, one per line (no decoration)
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output: each line is exactly one branch name
        merged_branches = {line.strip() for line in result.stdout.splitlines() if line.strip()}

        # Exact match only (not suffix matching)
        return branch in merged_branches

    except subprocess.CalledProcessError as e:
        # Handle case where into_branch doesn't exist
        if "does not point to a commit" in e.stderr or "not a valid" in e.stderr:
            # Target branch doesn't exist - branch can't be merged into it
            return False
        raise GitOperationError(f"Failed to check merge status: {e.stderr}") from e

def get_upstream_remote(repo_path: Path, branch: str) -> str | None:
    """Get upstream remote via git rev-parse --abbrev-ref @{upstream}."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Extract remote from "origin/branch-name" format
        upstream = result.stdout.strip()
        return upstream.split("/")[0] if "/" in upstream else None
    except subprocess.CalledProcessError:
        return None

def delete_local_branch(repo_path: Path, branch: str, force: bool = False) -> None:
    """Delete local branch. Use -D if force, -d otherwise."""
    flag = "-D" if force else "-d"
    subprocess.run(
        ["git", "-C", str(repo_path), "branch", flag, branch],
        capture_output=True,
        text=True,
        check=True,
    )

def delete_remote_branch(repo_path: Path, branch: str, remote: str = "origin") -> None:
    """Delete remote branch with git push --delete."""
    subprocess.run(
        ["git", "-C", str(repo_path), "push", remote, "--delete", branch],
        capture_output=True,
        text=True,
        check=True,
    )
```

**Delete command flow** (main.py:429-477):
```python
# Add new flags
# NOTE: Changed from --force to --yes to avoid conflict with existing --force flag
# in v0.1.0 which skips confirmation prompts. Using --yes/-y is industry standard
# (apt-get, npm, cargo) for confirmation skip.
yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
force: bool = typer.Option(False, "--force", "-f", help="Force deletion of unmerged branch")
delete_branch: bool = typer.Option(False, "--delete-branch", help="Delete local branch")
delete_remote: bool = typer.Option(False, "--delete-remote", help="Delete remote branch")

# Load worktree metadata (needed for PR warnings)
worktree_key = f"{repo}::{branch}"
worktree_meta = config["worktrees"].get(worktree_key, {})
bare_repo_path = base_dir / f"{repo}.git"

# Create deletion plan (validates flags)
try:
    plan = BranchDeletionPlan.from_flags(
        delete_branch=delete_branch,
        delete_remote=delete_remote,
        force=force,
        repo_path=bare_repo_path,
        branch=branch
    )
except ValueError as e:
    console.print(f"Error: {e}", style="red")
    sys.exit(1)

# VALIDATION PHASE: Check merge status BEFORE showing plan
# This prevents user from confirming an operation that will fail
if plan.delete_local and not plan.force:
    # Check if merged into the configured base branch (usually "main" or "develop")
    base_branch = config["repos"][repo].get("base_branch", "main")
    if not is_branch_merged(bare_repo_path, branch, into_branch=base_branch):
        console.print(
            f"Error: Branch '{branch}' is not merged into {base_branch}. Use --force to delete anyway.",
            style="red"
        )
        sys.exit(1)

# CONFIRMATION PHASE: Build and show deletion plan
operations = plan.describe()
if worktree_meta.get("pr") and plan.delete_remote:
    operations.append(f"⚠️  PR #{worktree_meta['pr']} will remain on GitHub")

confirmation = "\n".join(f"  • {op}" for op in operations)
console.print(f"This will:\n{confirmation}\n")

# Skip confirmation if --yes flag provided
if not yes:
    if not typer.confirm(f"Delete worktree {repo}:{branch}?"):
        console.print("Cancelled", style="yellow")
        return

# Execute deletions
remove_worktree(repo_path, worktree_path)  # includes submodule fix

if plan.delete_local:
    delete_local_branch(repo_path, branch, force=plan.force)
    console.print(f"✓ Deleted local branch '{branch}'", style="green")

if plan.delete_remote:
    delete_remote_branch(repo_path, branch, remote=plan.remote_name)
    console.print(f"✓ Deleted remote branch '{branch}' on {plan.remote_name}", style="green")

# Update config
del config["worktrees"][worktree_key]
save_config(config)
```

**Why centralized approach:**
- Single source of truth for deletion logic (prevents CLI/git ops drift)
- Easy to add `--all` shortcut flag later: `BranchDeletionPlan(True, True, False)`
- Validation happens in one place (from_flags method)
- Confirmation prompt auto-updates via `describe()` method
- Tests can verify plan construction separately from execution

**Files**: `main.py` (delete command), `git_ops.py`, `test_git_ops.py`, `test_cli.py`

---

### 3. Fix submodule removal error

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

**Files**: `git_ops.py` (remove_worktree function), `test_git_ops.py`

---

### 4. Atomic config writes (CRITICAL - data corruption risk)

**Approach**: Standard atomic write pattern (temp file + replace)

**Problem**: Direct write to YAML means any crash/power loss during save → corrupt config → CLI broken

**Implementation** (config.py:177-192):
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
        # Write YAML to temp file
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic replace (POSIX guarantees atomicity)
        os.replace(temp_path, config_path)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise
```

**Why this approach:**
- Atomic on POSIX (macOS, Linux) via `os.replace`
- Temp file in same directory ensures same filesystem (required for atomic replace)
- `fsync` ensures data written to disk before replace
- Cleanup on error prevents temp file accumulation
- Zero risk of corrupting existing config

**Bonus: Backup before migrations** (config.py:165-172):
```python
def migrate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Migrate config with backup before changes."""
    config_path = get_config_path()

    # Create backup before migration
    backup_path = config_path.with_suffix(f".yaml.backup.{int(time.time())}")
    if config_path.exists():
        shutil.copy2(config_path, backup_path)

    # ... existing migration logic ...

    # Save migrated config (now with atomic write)
    save_config(migrated_config)
    return migrated_config
```

**Files**: `config.py`, `test_config.py`

---

### 5. Support GitHub Enterprise and non-GitHub remotes (graceful degradation)

**Approach**: Accept all git URLs, use graceful degradation for non-GitHub

**Problem**: Hardcoded github.com rejects valid git URLs (GHE, GitLab, Bitbucket, self-hosted)

**Scope clarification**:
- Primary supported platform: GitHub.com (no change)
- Secondary support: GitHub Enterprise (any host with "github" in name)
- Graceful degradation: Other git hosts accepted, but PR features disabled

**Implementation** (config.py:195-224):
```python
def parse_github_url(url: str, require_github: bool = False) -> str | None:
    """
    Extract owner/repo from git URL for GitHub/GHE.

    Args:
        url: Git URL (SSH or HTTPS format)
        require_github: If True, raises ValueError for non-GitHub URLs.
                       If False, returns None for non-GitHub URLs (graceful degradation).

    Returns:
        owner/repo slug if GitHub/GHE URL, None if non-GitHub

    Examples:
        git@github.com:user/repo.git -> "user/repo" (GitHub)
        git@github.enterprise.com:user/repo.git -> "user/repo" (GHE)
        git@gitlab.com:user/repo.git -> None (GitLab, graceful)
        https://github.com/user/repo.git -> "user/repo" (GitHub)

    Raises:
        ValueError: Only if require_github=True and URL is not GitHub
                   OR if URL format is invalid
    """
    # SSH format: git@{host}:{owner}/{repo}.git
    ssh_pattern = r"git@([^:]+):([^/]+/[^/]+?)(\.git)?$"
    ssh_match = re.match(ssh_pattern, url)
    if ssh_match:
        host, owner_repo = ssh_match.group(1), ssh_match.group(2)
        # Accept any GitHub hostname (github.com, github.enterprise.com, etc.)
        if "github" in host.lower():
            return owner_repo
        elif not require_github:
            return None  # Non-GitHub, but that's OK (PR features will be disabled)
        else:
            raise ValueError(f"URL is not a GitHub URL: {url}")

    # HTTPS format: https://{host}/{owner}/{repo}.git
    https_pattern = r"https://([^/]+)/([^/]+/[^/]+?)(\.git)?$"
    https_match = re.match(https_pattern, url)
    if https_match:
        host, owner_repo = https_match.group(1), https_match.group(2)
        if "github" in host.lower():
            return owner_repo
        elif not require_github:
            return None
        else:
            raise ValueError(f"URL is not a GitHub URL: {url}")

    # No pattern matched - invalid URL format
    if require_github:
        raise ValueError(f"Invalid GitHub URL format: {url}")
    raise ValueError(f"Invalid git URL format: {url}")
```

**Update callers** (main.py register/create):
```python
# In register command
try:
    owner_repo = config.parse_github_url(url, require_github=False)
    cfg["repos"][alias] = {
        "url": url,
        "owner_repo": owner_repo  # May be None for non-GitHub
    }

    if owner_repo is None:
        console.print(
            f"ℹ️  Non-GitHub remote detected - PR features will be unavailable",
            style="yellow"
        )
    else:
        console.print(f"✓ Registered {alias} ({owner_repo})", style="green")
except ValueError as e:
    console.print(f"✗ Error: {e}", style="red")
    sys.exit(1)

# In list command, check if owner_repo exists before calling gh CLI
repo_data = cfg["repos"].get(repo, {})
if repo_data.get("owner_repo"):
    # Fetch PR status from GitHub using gh CLI
    pr_status = fetch_pr_status(owner_repo)
else:
    # Skip PR status for non-GitHub repos
    pr_status = {}
```

**Why graceful degradation:**
- ✓ Backward compatible (github.com works unchanged)
- ✓ Accepts GitHub Enterprise (any host with "github" in name)
- ✓ Accepts any git URL (GitLab, Bitbucket, self-hosted)
- ✓ PR features automatically disabled for non-GitHub
- ✓ git operations still work for all remotes
- ✓ No explicit GHE feature commitment - just stops blocking valid URLs
- ✓ No testing burden for non-GitHub platforms

**Files**: `config.py`, `main.py` (register, create), `test_config.py`

---

### 6. Add --url flag to repo create (prevent automation hangs)

**Approach**: Add optional --url flag + stdin interactivity check

**Problem**: `typer.prompt` blocks in CI/scripted environments

**Implementation** (main.py:258-273):
```python
@app.command()
def create(
    repo: Annotated[str, typer.Argument(autocompletion=complete_repo)],
    branch: str,
    from_ref: Annotated[str | None, typer.Option("--from", help="...")] = None,
    url: Annotated[str | None, typer.Option("--url", help="Repository URL (for lazy registration)")] = None,
):
    """Create worktree for branch."""
    cfg = config.load_config()

    # Check if repo exists in config
    if repo not in cfg.get("repos", {}):
        console.print(f"Repository '{repo}' not registered.", style="yellow")

        # Use --url flag if provided
        if url:
            repo_url = url
        elif sys.stdin.isatty():
            # Interactive mode: prompt for URL
            repo_url = typer.prompt("Enter repository URL")
        else:
            # Non-interactive mode: fail fast
            console.print(
                f"✗ Error: Repository '{repo}' not registered.\n"
                f"  Run 'repo register {repo} <url>' first, or use --url flag.",
                style="red"
            )
            sys.exit(1)

        # Register repo
        try:
            owner_repo = config.parse_github_url(repo_url, require_github=False)
            # ... rest of registration logic ...
```

**Why this approach:**
- `--url` flag provides non-interactive option
- `sys.stdin.isatty()` detects CI/scripted environments
- Fail fast with clear instructions in automation
- Backward compatible: interactive mode still works
- Standard pattern in CLI tools (git, gh, etc.)

**Files**: `main.py` (create command), `test_cli.py`

---

### 7. Add tests for upgrade helper functions

**Approach**: Unit tests with mocked subprocess.run

**Problem**: 6 upgrade functions have zero test coverage

**Functions to test** (git_ops.py:333-491):
1. `get_remote_url` - Extract remote URL
2. `set_remote_url` - Update remote URL
3. `get_latest_tag` - Parse latest git tag
4. `get_current_branch` - Handle detached HEAD
5. `has_uncommitted_changes` - Detect dirty working tree
6. `pull_latest` - Pull with error handling

**Test structure** (test_git_ops.py):
```python
class TestUpgradeHelpers:
    """Tests for upgrade-related git operations."""

    def test_get_remote_url_success(self, mock_subprocess):
        """get_remote_url extracts URL from git remote -v output."""
        mock_subprocess.return_value.stdout = "origin\tgit@github.com:user/repo.git (fetch)\n"

        url = git_ops.get_remote_url(Path("/fake/repo"), "origin")

        assert url == "git@github.com:user/repo.git"
        mock_subprocess.assert_called_once_with(
            ["git", "-C", "/fake/repo", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )

    def test_get_current_branch_detached_head(self, mock_subprocess):
        """get_current_branch returns None for detached HEAD."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(128, "git", stderr="HEAD")

        branch = git_ops.get_current_branch(Path("/fake/repo"))

        assert branch is None

    # ... similar tests for each function + edge cases ...
```

**Coverage targets**:
- Happy path for each function
- Error handling (CalledProcessError, parse failures)
- Edge cases (detached HEAD, no tags, merge conflicts)
- Return value parsing/formatting

**Files**: `test_git_ops.py`

---

## Implementation Order (Revised)

### Phase 0: Critical Bug Fix ✅ COMPLETE (45 min actual)
0. **HEAD branch creation bug** - ✅ COMPLETE
   - Implementation: 15 min
   - Code review improvements: 30 min
   - Commits: 9817414, 1386f12

### Phase 1: Critical Fixes (~1 hour) ⏳ NEXT
1. **Atomic config writes** - Prevents data loss (45 min)
2. **Submodule deletion fix** - Already planned (15 min)

### Phase 2: User Experience (~50 min)
3. **GitHub Enterprise support** - Unblock corporate users (30 min)
4. **Automation --url flag** - Prevent hangs (20 min)

### Phase 3: Original Features (~2.5 hours)
5. **Branch deletion flags** - User feature (1 hour)
6. **Activate --shell** - Most complex (1.5 hours)

### Phase 4: Polish (~1 hour)
7. **Upgrade helper tests** - Coverage (1 hour)

**Total estimated effort**: ~5.25 hours (9 improvements)
**Actual progress**: 0.75 hours (Phase 0 complete)
**Remaining**: ~4.5 hours (8 improvements)
**Each item**: implementation → tests → manual verification → commit

---

## Testing Strategy (Expanded for 9 improvements)

**New unit tests needed:**
0. **HEAD branch creation bug** (test_git_ops.py) ✅ COMPLETE
   - ✅ Test get_default_branch with "HEAD" literal (triggers fallback)
   - ✅ Test get_default_branch with "refs/remotes/origin/HEAD" (resolves to target)
   - ✅ Test get_default_branch with remote HEAD resolution failure (fallback)
   - ✅ Test get_default_branch with unexpected format "refs/custom/foo" (triggers fallback)
   - ✅ Test get_default_branch raises error when no main/master exists
   - ✅ Updated existing fallback tests for new call counts
   - All 140 tests passing (5 new tests added)

1. **Atomic config writes** (test_config.py)
   - Test successful atomic write (verify file contents)
   - Test cleanup on write error (temp file removed)
   - Test fsync called (mock os.fsync)
   - Test same-directory temp file (ensures atomic replace works)

2. **Submodule removal** (test_git_ops.py)
   - Test normal path (no submodules, direct removal succeeds)
   - Test fallback (submodule error → deinit → retry with --force)
   - Test non-submodule errors propagate correctly

3. **GitHub Enterprise support** (test_config.py)
   - Test github.com URLs (backward compatibility)
   - Test GitHub Enterprise URLs (github.enterprise.com)
   - Test non-GitHub URLs (GitLab, Bitbucket)
   - Test require_github flag behavior
   - Test graceful degradation (None owner_repo)

4. **Automation --url flag** (test_cli.py)
   - Test --url flag bypasses prompt
   - Test interactive mode with tty (prompt shown)
   - Test non-interactive mode without --url (fails fast)
   - Test error message clarity

5. **Branch deletion** (test_git_ops.py, test_cli.py)
   - Test BranchDeletionPlan.from_flags validation
   - Test describe() output for different flag combinations
   - Test merge checking (is_branch_merged)
   - Test remote detection (get_upstream_remote)
   - Test delete operations (local and remote)

6. **Activate --shell** (test_cli.py)
   - Mock subprocess.run, verify temp script generation
   - Test bash invocation (--rcfile flag)
   - Test zsh invocation (wrapper script)
   - Test cleanup (temp files removed in finally)
   - Test mutual exclusivity (--shell and --print)

7. **Upgrade helpers** (test_git_ops.py)
   - Test all 6 functions with mocked subprocess.run
   - Test error handling (CalledProcessError)
   - Test edge cases (detached HEAD, no tags, etc.)
   - Test return value parsing

7. **Upgrade helpers** (test_git_ops.py)
   - Test all 6 functions with mocked subprocess.run
   - Test error handling (CalledProcessError)
   - Test edge cases (detached HEAD, no tags, etc.)
   - Test return value parsing

**New tests for critical fixes:**
8. **Shell escaping** (test_cli.py)
   - Test activate --shell with branch containing spaces ("my feature")
   - Test activate --shell with branch containing quotes ('my"feature')
   - Test activate --shell with branch containing special chars ($, `, etc.)
   - Verify shlex.quote() properly escapes all inputs

9. **Circular dependency prevention** (test_git_ops.py)
   - Test remove_worktree without console parameter (programmatic use)
   - Test remove_worktree with console parameter (interactive use)
   - Verify no import errors when importing git_ops standalone

10. **Branch merge validation** (test_git_ops.py)
   - Test is_branch_merged with similar branch names ("fix" vs "hotfix", "main" vs "domain-main")
   - Test is_branch_merged with explicit into_branch parameter
   - Test is_branch_merged when target branch doesn't exist
   - Verify --format=%(refname:short) output parsing

11. **Non-GitHub URL handling** (test_config.py)
   - Test parse_github_url with GitLab URL (returns None)
   - Test parse_github_url with Bitbucket URL (returns None)
   - Test parse_github_url with GHE URL (returns owner/repo)
   - Verify graceful degradation in register/list commands

**Manual testing checklist:**
- [ ] Test atomic config write under load (rapid saves)
- [ ] Test config recovery from backup after failed migration
- [ ] Test GitHub Enterprise URL registration
- [ ] Test non-GitHub URL (GitLab/Bitbucket)
- [ ] Test repo create --url in script (non-interactive)
- [ ] Test activate --shell with bash (verify -i flag works, doesn't exit immediately)
- [ ] Test activate --shell with zsh (verify -i flag works)
- [ ] Test activate --shell with branch name containing spaces
- [ ] Verify PS1 modification appears in prompt
- [ ] Test branch deletion with merged branch
- [ ] Test branch deletion with unmerged branch (should fail without --force)
- [ ] Test --delete-remote without --delete-branch (should error)
- [ ] Test worktree with real submodules (create, then delete, verify console feedback)
- [ ] Test remove_worktree called from Python code without console parameter
- [ ] Test branch merge detection with "fix" branch when "hotfix" exists (should not match)
- [ ] Test upgrade flow end-to-end (with new tests passing)

**Status**: Phase 0 complete (HEAD branch bug), Phase 1 ready to implement

**Monitoring:**
- Watch for upgrade command issues across platforms
- Track user reports for environment-specific failures
- Monitor CI for any flaky tests

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

### v0.1.1 - Post-Release Improvements (In Progress - EXPANDED SCOPE)

**Critical Bug Fix (Completed 2025-12-03)** ✅
- ✅ HEAD branch creation bug - Prevent invalid branch names, resolve remote HEAD, verify fallback branches exist
  - Commits: 9817414, 1386f12
  - Tests: 140 passing (5 new)

**Critical Fixes (High Priority)** ⏳ Next
- ⏳ Atomic config writes - Prevent data corruption (temp file + fsync + os.replace)
- ⏳ Fix submodule removal error - Reactive deinit fallback

**User Experience (Medium Priority)**
- Support GitHub Enterprise and non-GitHub remotes - Flexible URL parsing
- `repo create --url` flag - Prevent automation hangs (+ stdin interactivity check)
- `repo delete --delete-branch/--delete-remote` - Clean up branches with BranchDeletionPlan

**Features (Original User Requests)**
- `repo activate --shell` - Launch new shell in worktree (claudette-cli pattern)

**Testing/Polish (Low Priority)**
- Add tests for upgrade helper functions - Coverage for 6 untested functions

**Estimated effort**: ~5.25 hours (9 improvements) | **Target**: v0.1.1 release

### v0.2.0 - Directory Structure Migration
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

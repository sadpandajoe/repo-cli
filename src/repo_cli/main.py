"""Main CLI entry point for repo-cli."""

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from repo_cli import __version__, config, gh_ops, git_ops, utils

app = typer.Typer(
    name="repo",
    help="A lightweight CLI tool for managing git worktrees with PR tracking",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"repo-cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
):
    """repo-cli: A lightweight CLI tool for managing git worktrees with PR tracking."""
    pass


# Auto-complete functions
def complete_repo(incomplete: str = "") -> list[str]:
    """Auto-complete function for repo aliases."""
    try:
        cfg = config.load_config()
        repos = cfg.get("repos", {}).keys()
        # Filter by incomplete string
        return [repo for repo in repos if repo.startswith(incomplete)]
    except (FileNotFoundError, Exception):
        # Return empty list if config doesn't exist or has errors
        return []


def complete_branch(incomplete: str = "") -> list[str]:
    """Auto-complete function for branch names."""
    try:
        cfg = config.load_config()
        worktrees = cfg.get("worktrees", {})

        # Extract all branches (context-aware filtering is complex in Typer)
        branches = []
        for wt_info in worktrees.values():
            branch = wt_info.get("branch")
            if branch and branch.startswith(incomplete):
                branches.append(branch)

        return branches
    except (FileNotFoundError, Exception):
        # Return empty list if config doesn't exist or has errors
        return []


@app.command()
def init(
    base_dir: Annotated[str, typer.Option(help="Base directory for repositories")] = "~/code",
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing config")] = False,
):
    """Initialize the CLI environment."""
    try:
        config_path = config.get_config_path()

        # Check if config already exists
        if config_path.exists() and not force:
            console.print(f"✗ Error: Config already exists at {config_path}", style="red")
            console.print(
                "ℹ Use --force to overwrite existing config",
                style="yellow",
            )
            sys.exit(1)

        # Expand path
        base_path = utils.expand_path(base_dir)

        # Create base directory
        base_path.mkdir(parents=True, exist_ok=True)

        # Create config with absolute path
        initial_config = {"base_dir": str(base_path), "repos": {}, "worktrees": {}}
        config.save_config(initial_config)

        if force:
            console.print(f"✓ Overwrote config at {config_path}", style="green")
        else:
            console.print(f"✓ Created config at {config_path}", style="green")
        console.print(f"✓ Created base directory: {base_path}", style="green")
        console.print("ℹ Run 'repo --install-completion' to enable auto-complete", style="blue")
        console.print("ℹ Run 'repo create <name> <branch>' to get started", style="blue")

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def register(
    alias: str,
    url: str,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing alias")] = False,
):
    """Register a repository alias for easy reference."""
    try:
        # Validate alias name to prevent path traversal
        utils.validate_repo_alias(alias)

        # Parse GitHub URL to extract owner/repo
        owner_repo = config.parse_github_url(url)

        # Load config
        cfg = config.load_config()

        # Check if alias already exists
        if "repos" not in cfg:
            cfg["repos"] = {}
        elif alias in cfg["repos"] and not force:
            existing_url = cfg["repos"][alias]["url"]
            console.print(
                f"✗ Error: Alias '{alias}' already registered to {existing_url}", style="red"
            )
            console.print("ℹ Use --force to overwrite existing alias", style="yellow")
            console.print(
                "⚠ Warning: Overwriting will affect all existing worktrees using this alias",
                style="yellow",
            )
            sys.exit(1)

        # Add or update repo
        if alias in cfg["repos"] and force:
            old_url = cfg["repos"][alias]["url"]
            console.print(f"⚠ Overwriting '{alias}' (was: {old_url})", style="yellow")

            # Check if bare repo exists and has different URL
            base_dir = utils.expand_path(cfg["base_dir"])
            bare_repo_path = utils.get_bare_repo_path(base_dir, alias)

            if bare_repo_path.exists() and old_url != url:
                try:
                    current_url = git_ops.get_remote_url(bare_repo_path)
                    if current_url != url:
                        console.print(
                            "⚠ Bare repository remote URL mismatch:",
                            style="yellow",
                        )
                        console.print(f"  Current: {current_url}", style="yellow")
                        console.print(f"  New:     {url}", style="yellow")

                        if typer.confirm("Update bare repository remote URL?"):
                            git_ops.set_remote_url(bare_repo_path, url)
                            console.print("✓ Updated bare repository remote URL", style="green")
                        else:
                            console.print(
                                "⚠ Warning: Bare repo URL not updated. "
                                "Future operations may fetch from wrong repository.",
                                style="yellow",
                            )
                except git_ops.GitOperationError as e:
                    console.print(f"⚠ Warning: Could not check bare repo URL: {e}", style="yellow")
        else:
            # New alias registration - check if bare repo already exists with different URL
            base_dir = utils.expand_path(cfg["base_dir"])
            bare_repo_path = utils.get_bare_repo_path(base_dir, alias)

            if bare_repo_path.exists():
                try:
                    current_url = git_ops.get_remote_url(bare_repo_path)
                    if current_url != url:
                        console.print(
                            "⚠ Bare repository already exists with different URL:",
                            style="yellow",
                        )
                        console.print(f"  Current: {current_url}", style="yellow")
                        console.print(f"  New:     {url}", style="yellow")

                        if typer.confirm("Update bare repository remote URL?"):
                            git_ops.set_remote_url(bare_repo_path, url)
                            console.print("✓ Updated bare repository remote URL", style="green")
                        else:
                            console.print(
                                "⚠ Warning: Bare repo URL not updated. "
                                "Future operations may fetch from wrong repository.",
                                style="yellow",
                            )
                except git_ops.GitOperationError as e:
                    console.print(f"⚠ Warning: Could not check bare repo URL: {e}", style="yellow")

        cfg["repos"][alias] = {"url": url, "owner_repo": owner_repo}

        # Save config
        config.save_config(cfg)

        console.print(f"✓ Registered '{alias}' → {url}", style="green")
        console.print(f"✓ GitHub repo: {owner_repo}", style="green")

    except ValueError as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)
    except FileNotFoundError:
        console.print("✗ Error: Config not found. Run 'repo init' first", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def create(
    repo: Annotated[str, typer.Argument(autocompletion=complete_repo)],
    branch: str,
    from_ref: Annotated[
        str | None, typer.Option("--from", help="Start point (branch, tag, or commit)")
    ] = None,
):
    """Create a new worktree for a branch."""
    try:
        # Validate inputs to prevent path traversal
        try:
            utils.validate_repo_alias(repo)
            utils.validate_branch_name(branch)
        except ValueError as e:
            console.print(f"✗ Error: {e}", style="red")
            sys.exit(1)

        # Load config
        try:
            cfg = config.load_config()
        except FileNotFoundError:
            console.print("✗ Error: Config not found. Run 'repo init' first", style="red")
            sys.exit(1)

        base_dir = utils.expand_path(cfg["base_dir"])

        # Check if repo exists in config, if not prompt for URL (lazy registration)
        if repo not in cfg.get("repos", {}):
            console.print(f"Repository '{repo}' not registered.", style="yellow")
            url = typer.prompt("Enter repository URL")

            try:
                owner_repo = config.parse_github_url(url)
                if "repos" not in cfg:
                    cfg["repos"] = {}
                cfg["repos"][repo] = {"url": url, "owner_repo": owner_repo}
                config.save_config(cfg)
                console.print(f"✓ Registered '{repo}' → {url}", style="green")
            except ValueError as e:
                console.print(f"✗ Error: {e}", style="red")
                sys.exit(1)

        repo_info = cfg["repos"][repo]
        repo_url = repo_info["url"]

        # Paths
        bare_repo_path = utils.get_bare_repo_path(base_dir, repo)
        worktree_path = utils.get_worktree_path(base_dir, repo, branch)

        # Clone bare repo if it doesn't exist
        if not bare_repo_path.exists():
            console.print(f"✓ Cloning {repo} as bare repository...", style="cyan")
            try:
                git_ops.clone_bare(repo_url, bare_repo_path)
            except git_ops.GitOperationError as e:
                console.print(f"✗ {e}", style="red")
                sys.exit(1)
        else:
            # Fetch latest refs so we can see new remote branches
            try:
                git_ops.fetch_repo(bare_repo_path)
            except git_ops.GitOperationError as e:
                console.print(f"⚠ Warning: Failed to fetch from remote: {e}", style="yellow")
                console.print(
                    "⚠ Branch information may be stale. If the branch exists on remote,",
                    style="yellow",
                )
                console.print(
                    "   creating it now will result in a diverged branch.",
                    style="yellow",
                )
                # Prompt user to continue with potentially stale refs
                if not typer.confirm("Do you want to create the branch anyway?"):
                    console.print("Cancelled", style="yellow")
                    sys.exit(0)

        # Determine start point
        start_point = from_ref if from_ref else "origin/HEAD"

        # Create worktree
        console.print(f"✓ Creating worktree: {str(worktree_path)}", style="cyan")
        try:
            actual_ref, is_new_branch = git_ops.create_worktree(
                bare_repo_path, worktree_path, branch, start_point
            )
        except git_ops.GitOperationError as e:
            console.print(f"✗ {e}", style="red")
            sys.exit(1)

        console.print(f"✓ Created worktree: {str(worktree_path)}", style="green")
        if is_new_branch:
            console.print(f"✓ Branch: {branch} (new, from {actual_ref})", style="green")
        else:
            console.print(f"✓ Branch: {branch} (existing)", style="green")

        # Show navigation hint
        console.print("")
        console.print(f"  cd {str(worktree_path)}", style="cyan bold")
        console.print("")

        # Initialize submodules (only if .gitmodules exists)
        gitmodules_path = worktree_path / ".gitmodules"
        if gitmodules_path.exists():
            try:
                console.print("✓ Initializing submodules...", style="cyan")
                submodule_count = git_ops.init_submodules(worktree_path)
                if submodule_count > 0:
                    console.print(f"✓ Initialized {submodule_count} submodules", style="green")
            except git_ops.GitOperationError as e:
                console.print(f"⚠ Warning: {e}", style="yellow")

        # Save worktree metadata (use :: delimiter to prevent collisions)
        worktree_key = f"{repo}::{branch}"
        if "worktrees" not in cfg:
            cfg["worktrees"] = {}
        cfg["worktrees"][worktree_key] = {
            "repo": repo,
            "branch": branch,
            "pr": None,
            "start_point": actual_ref,  # Use actual ref that was checked out
            "created_at": datetime.now().isoformat(),
        }
        config.save_config(cfg)

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def list(repo: Annotated[str | None, typer.Argument(autocompletion=complete_repo)] = None):
    """Display all worktrees with PR status."""
    try:
        # Load config
        try:
            cfg = config.load_config()
        except FileNotFoundError:
            console.print("✗ Error: Config not found. Run 'repo init' first", style="red")
            sys.exit(1)

        worktrees = cfg.get("worktrees", {})
        repos = cfg.get("repos", {})

        if not worktrees:
            console.print(
                "No worktrees found. Create one with 'repo create <repo> <branch>'", style="yellow"
            )
            return

        # Create rich table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Repo")
        table.add_column("Branch")
        table.add_column("PR")
        table.add_column("Status")

        # Add rows
        rows_added = 0
        for _wt_key, wt_info in worktrees.items():
            wt_repo = wt_info["repo"]

            # Filter by repo if specified
            if repo and wt_repo != repo:
                continue

            wt_branch = wt_info["branch"]
            pr_num = wt_info.get("pr")

            if pr_num:
                # Get PR status
                owner_repo = repos.get(wt_repo, {}).get("owner_repo")
                if owner_repo:
                    status = gh_ops.get_pr_status(pr_num, owner_repo)
                    pr_display = f"#{pr_num}"
                    status_display = status if status else "-"
                else:
                    pr_display = f"#{pr_num}"
                    status_display = "-"
            else:
                pr_display = "-"
                status_display = "-"

            table.add_row(wt_repo, wt_branch, pr_display, status_display)
            rows_added += 1

        # Show table or helpful message if filtered and empty
        if rows_added == 0 and repo:
            console.print(f"No worktrees found for '{repo}'", style="yellow")
        elif rows_added > 0:
            console.print(table)

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def delete(
    repo: Annotated[str, typer.Argument(autocompletion=complete_repo)],
    branch: Annotated[str, typer.Argument(autocompletion=complete_branch)],
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation")] = False,
):
    """Remove a worktree."""
    try:
        # Load config
        try:
            cfg = config.load_config()
        except FileNotFoundError:
            console.print("✗ Error: Config not found. Run 'repo init' first", style="red")
            sys.exit(1)

        base_dir = utils.expand_path(cfg["base_dir"])
        worktree_key = f"{repo}::{branch}"

        # Check if worktree exists in config
        if worktree_key not in cfg.get("worktrees", {}):
            console.print(f"✗ Error: Worktree '{repo}/{branch}' not found in config", style="red")
            sys.exit(1)

        # Confirm deletion unless --force
        if not force:
            confirm = typer.confirm(f"⚠ Delete worktree '{repo}/{branch}'?")
            if not confirm:
                console.print("Cancelled", style="yellow")
                return

        # Paths
        bare_repo_path = utils.get_bare_repo_path(base_dir, repo)
        worktree_path = utils.get_worktree_path(base_dir, repo, branch)

        # Remove worktree
        try:
            git_ops.remove_worktree(bare_repo_path, worktree_path)
        except git_ops.GitOperationError as e:
            console.print(f"✗ {e}", style="red")
            sys.exit(1)

        # Remove from config
        del cfg["worktrees"][worktree_key]
        config.save_config(cfg)

        console.print(f"✓ Removed worktree: {str(worktree_path)}", style="green")

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def activate(
    repo: Annotated[str, typer.Argument(autocompletion=complete_repo)],
    branch: Annotated[str, typer.Argument(autocompletion=complete_branch)],
    print_only: Annotated[
        bool,
        typer.Option(
            "--print",
            "-p",
            help="Print path only (for shell integration)",
        ),
    ] = False,
):
    """Print the path to a worktree for navigation.

    Use with shell integration:
        cd $(repo activate myrepo feature-123 --print)
    """
    try:
        # Load config
        try:
            cfg = config.load_config()
        except FileNotFoundError:
            console.print("✗ Error: Config not found. Run 'repo init' first", style="red")
            sys.exit(1)

        base_dir = cfg.get("base_dir")
        if not base_dir:
            console.print("✗ Error: base_dir not configured", style="red")
            sys.exit(1)

        # Expand base_dir to Path
        base_dir = utils.expand_path(base_dir)

        worktree_key = f"{repo}::{branch}"

        # Check if worktree exists in config
        if worktree_key not in cfg.get("worktrees", {}):
            console.print(f"✗ Error: Worktree '{repo}/{branch}' not found", style="red")
            sys.exit(1)

        # Get worktree path
        worktree_path = utils.get_worktree_path(base_dir, repo, branch)

        # Verify worktree exists on filesystem
        if not worktree_path.exists():
            console.print(f"✗ Error: Worktree directory not found: {worktree_path}", style="red")
            console.print("   Run 'repo list' to see available worktrees", style="yellow")
            sys.exit(1)

        # Output based on mode
        if print_only:
            # Print path only for shell integration
            print(str(worktree_path))
        else:
            # Rich formatted output
            console.print("📂 Worktree path:", style="bold")
            console.print("")
            console.print(f"  cd {str(worktree_path)}", style="cyan bold")
            console.print("")

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


# PR subcommand group
pr_app = typer.Typer(help="Manage pull requests", no_args_is_help=True)
app.add_typer(pr_app, name="pr")


@pr_app.command("link")
def pr_link(
    repo: Annotated[str, typer.Argument(autocompletion=complete_repo)],
    branch: Annotated[str, typer.Argument(autocompletion=complete_branch)],
    pr_number: int,
):
    """Link a PR to a worktree."""
    try:
        # Load config
        try:
            cfg = config.load_config()
        except FileNotFoundError:
            console.print("✗ Error: Config not found. Run 'repo init' first", style="red")
            sys.exit(1)

        worktree_key = f"{repo}::{branch}"

        # Check if worktree exists
        if worktree_key not in cfg.get("worktrees", {}):
            console.print(f"✗ Error: Worktree '{repo}/{branch}' not found", style="red")
            sys.exit(1)

        # Get owner/repo for validation
        owner_repo = cfg.get("repos", {}).get(repo, {}).get("owner_repo")

        # Optionally validate PR exists
        if owner_repo and gh_ops.is_gh_available():
            if gh_ops.validate_pr_exists(pr_number, owner_repo):
                status = gh_ops.get_pr_status(pr_number, owner_repo)
                console.print(
                    f"✓ Validated PR #{pr_number} ({status}) in {owner_repo}", style="green"
                )
            else:
                console.print(f"⚠ Warning: Could not validate PR #{pr_number}", style="yellow")

        # Link PR
        cfg["worktrees"][worktree_key]["pr"] = pr_number
        config.save_config(cfg)

        console.print(f"✓ Linked PR #{pr_number} to {repo}/{branch}", style="green")

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def doctor():
    """Run diagnostic checks on your repo-cli installation."""
    console.print("[bold cyan]repo-cli Doctor[/bold cyan]")
    console.print()

    all_checks_passed = True

    # Check 1: Git version
    console.print("[bold]1. Checking Git version...[/bold]")
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        git_version = result.stdout.strip()
        console.print(f"   ✓ {git_version}", style="green")

        # Parse version and check if >= 2.17
        version_parts = git_version.split()
        if len(version_parts) >= 3:
            version_num = version_parts[2]
            major, minor = map(int, version_num.split(".")[:2])
            if major < 2 or (major == 2 and minor < 17):
                console.print(
                    f"   ⚠ Warning: Git 2.17+ required, found {version_num}", style="yellow"
                )
                all_checks_passed = False
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("   ✗ Git not found", style="red")
        all_checks_passed = False

    # Check 2: gh CLI availability
    console.print("[bold]2. Checking gh CLI...[/bold]")
    if gh_ops.is_gh_available():
        try:
            result = subprocess.run(["gh", "--version"], capture_output=True, text=True, check=True)
            gh_version = result.stdout.split("\n")[0].strip()
            console.print(f"   ✓ {gh_version}", style="green")
        except Exception:
            console.print("   ⚠ gh CLI found but version check failed", style="yellow")
    else:
        console.print("   ⚠ gh CLI not found (PR features will be limited)", style="yellow")

    # Check 3: Config file
    console.print("[bold]3. Checking configuration...[/bold]")
    try:
        cfg = config.load_config()
        config_path = config.get_config_path()
        console.print(f"   ✓ Config found at {config_path}", style="green")

        # Validate config schema
        required_keys = ["base_dir", "repos", "worktrees"]
        missing_keys = [key for key in required_keys if key not in cfg]
        if missing_keys:
            console.print(f"   ⚠ Missing config keys: {', '.join(missing_keys)}", style="yellow")
            all_checks_passed = False
        else:
            console.print("   ✓ Config schema valid", style="green")

        # Check base_dir
        base_dir = utils.expand_path(cfg["base_dir"])
        if base_dir.exists():
            console.print(f"   ✓ Base directory exists: {base_dir}", style="green")

            # Check permissions
            if not base_dir.is_dir():
                console.print(f"   ✗ Base path is not a directory: {base_dir}", style="red")
                all_checks_passed = False
            else:
                # Test write permissions
                test_file = base_dir / ".repo-cli-test"
                try:
                    test_file.touch()
                    test_file.unlink()
                    console.print("   ✓ Base directory is writable", style="green")
                except Exception as e:
                    console.print(f"   ✗ Base directory not writable: {e}", style="red")
                    all_checks_passed = False
        else:
            console.print(f"   ⚠ Base directory does not exist: {base_dir}", style="yellow")
            all_checks_passed = False

    except FileNotFoundError:
        console.print("   ⚠ Config not found. Run 'repo init' first", style="yellow")
        all_checks_passed = False
    except Exception as e:
        console.print(f"   ✗ Config error: {e}", style="red")
        all_checks_passed = False

    # Check 4: Python environment
    console.print("[bold]4. Checking Python environment...[/bold]")
    console.print(f"   • Python: {sys.version.split()[0]}", style="cyan")
    console.print(f"   • Platform: {platform.system()} {platform.release()}", style="cyan")
    console.print(f"   • repo-cli: {__version__}", style="cyan")

    # Check 5: Dependencies
    console.print("[bold]5. Checking dependencies...[/bold]")
    try:
        from importlib.metadata import version as get_version

        console.print(f"   ✓ typer: {get_version('typer')}", style="green")
        console.print(f"   ✓ rich: {get_version('rich')}", style="green")
        console.print(f"   ✓ pyyaml: {get_version('pyyaml')}", style="green")
    except Exception as e:
        console.print(f"   ✗ Error checking dependencies: {e}", style="red")
        all_checks_passed = False

    # Summary
    console.print()
    if all_checks_passed:
        console.print("[bold green]✓ All checks passed! Your installation is healthy.[/bold green]")
    else:
        console.print("[bold yellow]⚠ Some checks failed. See above for details.[/bold yellow]")
        console.print()
        console.print("Troubleshooting tips:", style="cyan")
        console.print("  • Update Git: https://git-scm.com/downloads")
        console.print("  • Install gh: https://cli.github.com/")
        console.print("  • Run: repo init --base-dir ~/code")


@app.command(name="upgrade-check")
def upgrade_check():
    """Check if a newer version of repo-cli is available."""
    try:
        import repo_cli

        # Get installation directory
        install_dir = Path(repo_cli.__file__).parent.parent.parent

        console.print("[bold cyan]Checking for updates...[/bold cyan]")
        console.print()

        # Verify it's a git repository
        git_dir = install_dir / ".git"
        if not git_dir.exists():
            console.print("✗ Not installed from git. Unable to check for updates.", style="red")
            console.print(f"  Installation directory: {install_dir}", style="yellow")
            sys.exit(1)

        console.print(f"📂 Installation: {install_dir}", style="cyan")

        # Get current version
        from repo_cli import __version__

        current_version = __version__
        console.print(f"📌 Current version: {current_version}")

        # Get current branch
        try:
            current_branch = git_ops.get_current_branch(install_dir)
            console.print(f"🌿 Current branch: {current_branch}")
        except git_ops.GitOperationError as e:
            console.print(f"⚠ Warning: {e}", style="yellow")
            current_branch = "unknown"

        # Check for uncommitted changes
        try:
            if git_ops.has_uncommitted_changes(install_dir):
                console.print(
                    "⚠ Warning: You have uncommitted changes in the installation directory",
                    style="yellow",
                )
        except git_ops.GitOperationError:
            pass

        # Get latest tag from remote
        console.print()
        console.print("Fetching latest version from remote...", style="cyan")
        try:
            latest_tag = git_ops.get_latest_tag(install_dir)

            if not latest_tag:
                console.print("ℹ No version tags found on remote", style="yellow")
                console.print("  You may be on the latest development version")
            else:
                # Remove 'v' prefix if present for comparison
                latest_version = latest_tag.lstrip("v")
                console.print(f"📦 Latest version: {latest_version}")

                if latest_version > current_version:
                    console.print()
                    console.print(
                        f"[bold green]✓ Update available: {current_version} → {latest_version}[/bold green]"
                    )
                    console.print()
                    console.print("Run 'repo upgrade' to update", style="cyan bold")
                elif latest_version == current_version:
                    console.print()
                    console.print("[bold green]✓ You are on the latest version![/bold green]")
                else:
                    console.print()
                    console.print(
                        f"ℹ You are ahead of the latest release ({current_version} > {latest_version})",
                        style="yellow",
                    )
                    console.print("  You may be on a development branch")

        except git_ops.GitOperationError as e:
            console.print(f"✗ Failed to check for updates: {e}", style="red")
            sys.exit(1)

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


@app.command()
def upgrade(force: Annotated[bool, typer.Option("--force", help="Skip safety checks")] = False):
    """Upgrade repo-cli to the latest version."""
    try:
        import shutil

        import repo_cli

        # Get installation directory
        install_dir = Path(repo_cli.__file__).parent.parent.parent

        console.print("[bold cyan]Upgrading repo-cli...[/bold cyan]")
        console.print()

        # Verify it's a git repository
        git_dir = install_dir / ".git"
        if not git_dir.exists():
            console.print("✗ Not installed from git. Unable to upgrade automatically.", style="red")
            console.print(f"  Installation directory: {install_dir}", style="yellow")
            sys.exit(1)

        console.print(f"📂 Installation: {install_dir}", style="cyan")

        # Get current version
        from repo_cli import __version__

        current_version = __version__
        console.print(f"📌 Current version: {current_version}")

        # Safety checks (unless --force)
        if not force:
            # Check for uncommitted changes
            try:
                if git_ops.has_uncommitted_changes(install_dir):
                    console.print()
                    console.print(
                        "⚠ Warning: You have uncommitted changes in the installation directory",
                        style="yellow",
                    )
                    if not typer.confirm("Continue anyway?"):
                        console.print("Cancelled", style="yellow")
                        sys.exit(0)
            except git_ops.GitOperationError as e:
                console.print(f"⚠ Warning: Could not check git status: {e}", style="yellow")

            # Check current branch
            try:
                current_branch = git_ops.get_current_branch(install_dir)
                if current_branch not in ["main", "master"]:
                    console.print()
                    console.print(
                        f"⚠ Warning: You are on branch '{current_branch}' (not main/master)",
                        style="yellow",
                    )
                    if not typer.confirm("Continue anyway?"):
                        console.print("Cancelled", style="yellow")
                        sys.exit(0)
            except git_ops.GitOperationError as e:
                console.print(f"⚠ Warning: Could not check branch: {e}", style="yellow")

        # Pull latest changes
        console.print()
        console.print("Pulling latest changes from remote...", style="cyan")
        try:
            current_branch = git_ops.get_current_branch(install_dir)
            git_ops.pull_latest(install_dir, branch=current_branch)
            console.print("✓ Pulled latest changes", style="green")
        except git_ops.GitOperationError as e:
            console.print(f"✗ Failed to pull changes: {e}", style="red")
            sys.exit(1)

        # Reinstall dependencies
        console.print()
        console.print("Reinstalling dependencies...", style="cyan")

        # Check if uv is available
        if shutil.which("uv"):
            try:
                subprocess.run(
                    ["uv", "sync"],
                    cwd=install_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print("✓ Dependencies updated (uv sync)", style="green")
            except subprocess.CalledProcessError as e:
                console.print(f"✗ Failed to update dependencies: {e.stderr}", style="red")
                sys.exit(1)
        else:
            # Fallback to pip
            console.print("ℹ uv not found, using pip", style="yellow")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", "."],
                    cwd=install_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print("✓ Dependencies updated (pip install)", style="green")
            except subprocess.CalledProcessError as e:
                console.print(f"✗ Failed to update dependencies: {e.stderr}", style="red")
                sys.exit(1)

        # Reload version to show new version
        console.print()
        console.print("[bold green]✓ Upgrade complete![/bold green]")
        console.print()
        console.print("Run 'repo --version' to verify the new version", style="cyan")

    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    app()

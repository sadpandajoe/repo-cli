"""Main CLI entry point for repo-cli."""

import typer
from typing_extensions import Annotated

app = typer.Typer(
    name="repo",
    help="A lightweight CLI tool for managing git worktrees with PR tracking",
    no_args_is_help=True,
)


@app.command()
def init(
    base_dir: Annotated[
        str, typer.Option(help="Base directory for repositories")
    ] = "~/code",
):
    """Initialize the CLI environment."""
    typer.echo("🚧 repo init - Coming soon")


@app.command()
def register(alias: str, url: str):
    """Register a repository alias for easy reference."""
    typer.echo("🚧 repo register - Coming soon")


@app.command()
def create(
    repo: str,
    branch: str,
    from_ref: Annotated[
        str | None, typer.Option("--from", help="Start point (branch, tag, or commit)")
    ] = None,
):
    """Create a new worktree for a branch."""
    typer.echo("🚧 repo create - Coming soon")


@app.command()
def list(repo: Annotated[str | None, typer.Argument()] = None):
    """Display all worktrees with PR status."""
    typer.echo("🚧 repo list - Coming soon")


@app.command()
def delete(
    repo: str,
    branch: str,
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation")] = False,
):
    """Remove a worktree."""
    typer.echo("🚧 repo delete - Coming soon")


# PR subcommand group
pr_app = typer.Typer(help="Manage pull requests", no_args_is_help=True)
app.add_typer(pr_app, name="pr")


@pr_app.command("link")
def pr_link(repo: str, branch: str, pr_number: int):
    """Link a PR to a worktree."""
    typer.echo("🚧 repo pr link - Coming soon")


if __name__ == "__main__":
    app()

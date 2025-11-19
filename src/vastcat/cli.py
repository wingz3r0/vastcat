"""Typer CLI for Vastcat."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import shlex

import typer
from rich.console import Console

from .assets import ASSET_LIBRARY, AssetManager, list_assets
from .config import ensure_config
from .deployment import render_hashcat_command, render_startup_script
from .hashcat import HashcatRunner
from .notifier import Notifier
from .theme import cat_say
from .wizard import Wizard

app = typer.Typer(help="Cat-themed hashcat orchestrator")
assets_app = typer.Typer(help="Manage wordlists and rules")
app.add_typer(assets_app, name="assets")


@assets_app.command("list")
def assets_list(category: Optional[str] = typer.Option(None, "--category", "-c")) -> None:
    console = Console()
    manager = AssetManager()
    names = list_assets(category)
    if not names:
        console.print("No assets found.")
        return
    for key in names:
        asset = ASSET_LIBRARY[key]
        console.print(f"[bold]{key}[/bold]: {asset.description or asset.name} -> {manager.resolved_paths([key])[0]}")


@assets_app.command("sync")
def assets_sync(
    names: List[str] = typer.Argument(None),
    force: bool = typer.Option(False, "--force", help="Re-download assets"),
) -> None:
    manager = AssetManager()
    targets = names or None
    paths = manager.sync(targets, force=force)
    console = Console()
    for path in paths:
        console.print(cat_say(f"Ready: {path}"))


@app.command()
def run(
    hash_file: Path = typer.Argument(..., help="File containing hashes"),
    hash_mode: str = typer.Option("0", "--mode", "-m"),
    attack_mode: str = typer.Option("0", "--attack", "-a"),
    wordlists: List[Path] = typer.Option(..., "--wordlist", "-w"),
    rules: List[Path] = typer.Option([], "--rule", "-r"),
    extra: str = typer.Option("--status --status-timer=60", help="Additional hashcat flags"),
    dry_run: bool = typer.Option(False, help="Only print the command"),
) -> None:
    command = render_hashcat_command(
        hash_path=str(hash_file),
        hash_mode=hash_mode,
        attack_mode=attack_mode,
        wordlists=[str(path) for path in wordlists],
        rules=[str(path) for path in rules],
        extra_args=extra,
    )
    runner = HashcatRunner(notifier=Notifier(ensure_config().get("discord_webhook")))
    runner.run(shlex.split(command)[1:], dry_run=dry_run)


@app.command()
def wizard() -> None:
    Wizard(Console()).run()


@app.command(name="install-hashcat")
def install_hashcat() -> None:
    """Display instructions for installing hashcat."""
    console = Console()
    console.print("\n[bold cyan]Hashcat Installation Instructions[/bold cyan]\n")

    console.print("[bold]Option 1: Package Manager (Recommended)[/bold]")
    console.print("  Ubuntu/Debian: [cyan]sudo apt update && sudo apt install -y hashcat[/cyan]")
    console.print("  Fedora/RHEL:   [cyan]sudo dnf install -y hashcat[/cyan]")
    console.print("  Arch Linux:    [cyan]sudo pacman -S hashcat[/cyan]")
    console.print("  macOS:         [cyan]brew install hashcat[/cyan]")

    console.print("\n[bold]Option 2: From Source (Latest Version)[/bold]")
    console.print("  1. Download:  [cyan]wget https://hashcat.net/files/hashcat-7.1.2.tar.gz[/cyan]")
    console.print("  2. Extract:   [cyan]tar -xzf hashcat-7.1.2.tar.gz[/cyan]")
    console.print("  3. Build:     [cyan]cd hashcat-7.1.2 && make[/cyan]")
    console.print("  4. Install:   [cyan]sudo make install[/cyan]")
    console.print("  Or symlink:   [cyan]sudo ln -s $(pwd)/hashcat /usr/local/bin/hashcat[/cyan]")

    console.print("\n[bold]Verify Installation:[/bold]")
    console.print("  [cyan]hashcat --version[/cyan]")

    console.print("\n[dim]After installation, run 'vastcat wizard' to start cracking![/dim]\n")

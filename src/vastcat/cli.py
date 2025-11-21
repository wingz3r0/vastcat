"""Typer CLI for Vastcat."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import os
import shlex
import shutil

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


def check_hashcat_with_warning(console: Console) -> bool:
    """Check if hashcat is installed and warn if not."""
    if shutil.which("hashcat"):
        return True

    # Try automatic installation
    console.print("\n[bold yellow]⚠️  Hashcat is not installed![/bold yellow]")
    console.print("[dim]Attempting automatic installation...[/dim]\n")

    try:
        from .install_hashcat import download_and_install_hashcat

        # Suppress verbose output during automatic installation
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            success = download_and_install_hashcat(verbose=False)
        finally:
            sys.stdout = old_stdout

        if success and shutil.which("hashcat"):
            console.print("[green]✓ Hashcat installed successfully![/green]\n")
            return True
        else:
            console.print("[yellow]⚠️  Automatic installation failed[/yellow]\n")
    except Exception as e:
        console.print(f"[yellow]⚠️  Automatic installation failed: {e}[/yellow]\n")

    console.print("[dim]Please install hashcat manually:[/dim]")
    console.print("  [cyan]vastcat install-hashcat[/cyan]  (for instructions)")
    console.print("\n[dim]Or install directly:[/dim]")
    console.print("  [dim]Ubuntu/Debian: sudo apt install hashcat[/dim]")
    console.print("  [dim]macOS: brew install hashcat[/dim]\n")
    return False


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
    """Run hashcat with manual parameters."""
    console = Console()
    if not check_hashcat_with_warning(console):
        raise typer.Exit(1)

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
    """Start the interactive configuration wizard."""
    console = Console()
    check_hashcat_with_warning(console)
    Wizard(console).run()


@app.command(name="doctor")
def doctor() -> None:
    """Check vastcat setup and dependencies."""
    console = Console()
    console.print("\n[bold cyan]VastCat Setup Check[/bold cyan]\n")

    # Check hashcat - try local installation first
    local_hashcat = Path.home() / ".local" / "share" / "vastcat" / "hashcat" / "hashcat"
    local_bin = Path.home() / ".local" / "bin" / "hashcat"
    system_hashcat = shutil.which("hashcat")

    hashcat_found = False
    hashcat_path = None

    if local_hashcat.exists() and os.access(local_hashcat, os.X_OK):
        hashcat_path = str(local_hashcat)
        hashcat_found = True
        console.print(f"[green]✓[/green] Hashcat (local): [dim]{hashcat_path}[/dim]")
    elif local_bin.exists() and os.access(local_bin, os.X_OK):
        hashcat_path = str(local_bin)
        hashcat_found = True
        console.print(f"[green]✓[/green] Hashcat (local): [dim]{hashcat_path}[/dim]")
    elif system_hashcat:
        hashcat_path = system_hashcat
        hashcat_found = True
        console.print(f"[green]✓[/green] Hashcat (system): [dim]{hashcat_path}[/dim]")
    else:
        console.print("[red]✗[/red] Hashcat not found")
        console.print("  [dim]Try reinstalling: pip install --force-reinstall vastcat[/dim]")
        console.print("  [dim]Or run: vastcat install-hashcat[/dim]")

    if hashcat_found and hashcat_path:
        # Try to get version
        import subprocess
        try:
            result = subprocess.run([hashcat_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                console.print(f"  [dim]Version: {version}[/dim]")
        except Exception:
            pass

    # Check name-that-hash
    try:
        from vastcat.detect import NTH_AVAILABLE
        if NTH_AVAILABLE:
            import name_that_hash
            console.print(f"[green]✓[/green] name-that-hash available: [dim]v{name_that_hash.__version__}[/dim]")
        else:
            console.print("[yellow]⚠[/yellow] name-that-hash not available (using regex fallback)")
    except Exception as e:
        console.print(f"[red]✗[/red] Error checking name-that-hash: {e}")

    # Check config
    try:
        config = ensure_config()
        config_file = Path.home() / ".config" / "vastcat" / "config.yaml"
        console.print(f"[green]✓[/green] Config file: [dim]{config_file}[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Config issue: {e}")

    # Check cache directory
    cache_dir = Path.home() / ".cache" / "vastcat"
    if cache_dir.exists():
        console.print(f"[green]✓[/green] Cache directory: [dim]{cache_dir}[/dim]")
    else:
        console.print(f"[dim]  Cache directory will be created on first use[/dim]")

    console.print("\n[bold]Status:[/bold]")
    if hashcat_path:
        console.print("  [green]Ready to crack![/green] Run [cyan]vastcat wizard[/cyan] to get started.\n")
    else:
        console.print("  [yellow]Install hashcat to begin.[/yellow] Run [cyan]vastcat install-hashcat[/cyan] for instructions.\n")


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
    console.print("  [cyan]vastcat doctor[/cyan]")

    console.print("\n[dim]After installation, run 'vastcat wizard' to start cracking![/dim]\n")

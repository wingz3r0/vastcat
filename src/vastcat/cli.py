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
from .vast import VastClient, VastError
from .wizard import Wizard

app = typer.Typer(help="Cat-themed Vast.ai hashcat orchestrator")
assets_app = typer.Typer(help="Manage wordlists and rules")
deploy_app = typer.Typer(help="Plan Vast.ai deployments")
app.add_typer(assets_app, name="assets")
app.add_typer(deploy_app, name="deploy")


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


@deploy_app.command("plan")
def deploy_plan(
    assets: List[str] = typer.Option(None, "--asset", help="Asset keys to bake into startup script"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Where to write the script"),
) -> None:
    manager = AssetManager()
    cfg = ensure_config()
    resolved = manager.resolved_paths(assets or list_assets("wordlists"))
    script = render_startup_script(resolved)
    if output:
        output.write_text(script)
        output.chmod(0o750)
        Console().print(cat_say(f"Wrote script to {output}"))
    else:
        Console().print(script)


@deploy_app.command("start")
def deploy_start(
    offer_id: int = typer.Argument(..., help="Offer ID from Vast.ai"),
    disk: int = typer.Option(60, help="Disk size in GB"),
    image: Optional[str] = typer.Option(None, help="Docker image to boot"),
    onstart: Optional[Path] = typer.Option(None, help="Path to startup script"),
    api_key: Optional[str] = typer.Option(None, help="Vast.ai API key"),
) -> None:
    cfg = ensure_config()
    client = VastClient(api_key=api_key)
    payload = client.create_instance(
        offer_id=offer_id,
        image=image or cfg.get("ubuntu_cuda_image"),
        disk_gb=disk,
        onstart=onstart.read_text() if onstart else None,
    )
    Console().print(cat_say(f"Contract created: {payload}"))


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


@app.command()
def offers(
    min_vram: int = typer.Option(12, help="Minimum GPU VRAM (GB)"),
    limit: int = typer.Option(6, help="Max offers to fetch"),
    api_key: Optional[str] = typer.Option(None, help="Vast.ai API key"),
) -> None:
    try:
        client = VastClient(api_key=api_key)
        offers = client.list_offers(min_vram=min_vram, limit=limit)
    except VastError as exc:
        Console().print(f"Error: {exc}")
        raise typer.Exit(1)
    console = Console()
    for offer in offers:
        console.print(f"{offer.id}: {offer.gpu_name} ${offer.hourly:.2f}/hr {offer.vram_gb}GB VRAM reliability {offer.reliability}")

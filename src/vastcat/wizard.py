"""Interactive wizard for Vastcat."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import os
import shlex

from rich.console import Console
import questionary
from questionary import Choice

from .assets import ASSET_LIBRARY, AssetManager, list_assets
from .config import ensure_config
from .deployment import render_hashcat_command, render_startup_script
from .detect import HashGuess, detect_hash_modes, sample_from_file
from .hashcat import HashcatRunner
from .notifier import Notifier
from .theme import CAT_ASCII, cat_say
from .vast import VastClient, VastError, Offer


ATTACK_MODES = {
    "Straight (mode 0)": "0",
    "Combinator (mode 1)": "1",
    "Mask / Brute-force (mode 3)": "3",
    "Hybrid Wordlist + Mask (mode 6)": "6",
}


class Wizard:
    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.config = ensure_config()
        self.asset_manager = AssetManager(self.config)

    def run(self) -> None:
        self.console.print(CAT_ASCII)
        self.console.print(cat_say("Welcome to Vastcat's cuddle-free wizard."))

        # Select and sync wordlists (required)
        wordlist_keys = self._pick_assets("wordlists")
        if not wordlist_keys:
            self.console.print(cat_say("No wordlists selected. Hashcat requires at least one wordlist."))
            if questionary.confirm("Try again?", default=True).ask():
                wordlist_keys = self._pick_assets("wordlists")
            if not wordlist_keys:
                self.console.print(cat_say("Still no wordlists selected. Exiting."))
                return
        self.asset_manager.sync(wordlist_keys)

        # Select and sync rules (optional)
        self.console.print(cat_say("Rules are optional but highly recommended for better cracking results."))
        rule_keys = self._pick_assets("rules")
        if rule_keys:
            self.asset_manager.sync(rule_keys)
        else:
            self.console.print(cat_say("No rules selected. Proceeding with straight wordlist attack."))

        # Optional: Configure notifications
        webhook = self._prompt_discord()
        notifier = Notifier(webhook)

        # Get and validate hash file
        while True:
            hash_path = questionary.text("Path to your hash file", default="~/hashes/hash.txt").ask()
            expanded_path = Path(hash_path).expanduser()
            if expanded_path.exists():
                break
            self.console.print(cat_say(f"File not found: {expanded_path}. Please try again."))
            if not questionary.confirm("Try another path?", default=True).ask():
                self.console.print(cat_say("Cannot proceed without a hash file. Exiting."))
                return

        hash_mode = self._determine_hash_mode(hash_path)
        attack_choice = questionary.select("Choose attack mode", choices=list(ATTACK_MODES.keys())).ask()
        attack_mode = ATTACK_MODES[attack_choice]

        # Optional: Configure Vast.ai deployment
        use_vast = questionary.confirm("Deploy to Vast.ai?", default=False).ask()
        vast_offer = None
        if use_vast:
            api_key = self._prompt_api_key()
            if api_key:
                vast_offer = self._select_offer(api_key)
        wordlist_paths = self.asset_manager.resolved_paths(wordlist_keys)
        rule_paths = self.asset_manager.resolved_paths(rule_keys)
        command = render_hashcat_command(
            hash_path=hash_path,
            hash_mode=hash_mode,
            attack_mode=attack_mode,
            wordlists=self._only_files(wordlist_paths, "wordlist"),
            rules=self._only_files(rule_paths, "rule"),
        )
        script = render_startup_script(wordlist_paths + rule_paths)

        # Show configuration summary
        self.console.rule(cat_say("Configuration Summary"))
        self.console.print(f"[bold]Hash file:[/bold] {hash_path}")
        self.console.print(f"[bold]Hash mode:[/bold] {hash_mode}")
        self.console.print(f"[bold]Attack mode:[/bold] {attack_mode}")
        self.console.print(f"[bold]Wordlists:[/bold] {', '.join([p.name for p in wordlist_paths])}")
        if rule_paths:
            self.console.print(f"[bold]Rules:[/bold] {', '.join([p.name for p in rule_paths])}")
        else:
            self.console.print(f"[bold]Rules:[/bold] None (straight attack)")

        self.console.rule(cat_say("Deployment Plan"))
        if vast_offer:
            self.console.print(
                f"Vast.ai Offer {vast_offer.id}: {vast_offer.gpu_name} ${vast_offer.hourly:.2f}/hr {vast_offer.vram_gb}GB VRAM"
            )
        else:
            self.console.print(cat_say("Running locally (no Vast.ai deployment)."))
        self.console.print(f"\n[bold]Hashcat command:[/bold]\n[italic]{command}[/italic]")
        if questionary.confirm("Save startup script to file?", default=True).ask():
            path = Path(questionary.text("Path to save script", default="vastcat-startup.sh").ask())
            path.write_text(script)
            os.chmod(path, 0o750)
            self.console.print(cat_say(f"Script written to {path}"))
        self.console.print(cat_say("Ready to run hashcat."))
        if questionary.confirm("Run hashcat locally now?", default=False).ask():
            # Check for HASHCAT_BINARY environment variable
            hashcat_binary = os.environ.get("HASHCAT_BINARY")
            runner = HashcatRunner(binary=hashcat_binary, notifier=notifier)
            try:
                runner.ensure_binary()
                runner.run(shlex.split(command)[1:])
            except FileNotFoundError as exc:
                self.console.print(f"[red]{exc}[/red]")
            except PermissionError as exc:
                self.console.print(f"[red]Error:[/red] {exc}")
                self.console.print(cat_say("Make sure hashcat binary has execute permissions."))

    def _pick_assets(self, category: str) -> List[str]:
        """Pick assets using a numbered menu (more reliable than arrow keys)."""
        keys = list_assets(category)
        if not keys:
            return []

        # Display available options
        self.console.print(f"\n[bold]Available {category}:[/bold]")
        for idx, key in enumerate(keys, 1):
            asset = ASSET_LIBRARY[key]
            self.console.print(f"  [cyan]{idx}[/cyan]. {key}: [dim]{asset.description}[/dim]")

        # Get selection
        self.console.print(f"\n[bold]Enter numbers to select {category}:[/bold]")
        self.console.print("[dim]Examples: '1' (single), '1,2' (multiple), '1-3' (range), 'all' (select all)[/dim]")

        selection = questionary.text(
            f"Select {category}",
            default="all" if category == "wordlists" else ""
        ).ask()

        if not selection or selection.strip() == "":
            return []

        # Parse selection
        try:
            selected_indices = self._parse_selection(selection.strip(), len(keys))
            selected_keys = [keys[i] for i in selected_indices]

            if selected_keys:
                self.console.print(f"[green]✓[/green] Selected {len(selected_keys)} {category}: {', '.join(selected_keys)}")
            return selected_keys
        except ValueError as e:
            self.console.print(f"[red]Invalid selection:[/red] {e}")
            return []

    def _parse_selection(self, selection: str, max_items: int) -> List[int]:
        """Parse user selection string into list of indices.

        Supports:
        - Single: "1"
        - Multiple: "1,2,3"
        - Range: "1-3"
        - All: "all"
        - Mixed: "1,3-5,7"

        Returns 0-based indices.
        """
        if selection.lower() == "all":
            return list(range(max_items))

        indices = set()
        parts = selection.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                # Range: "1-3"
                try:
                    start, end = part.split("-")
                    start_idx = int(start.strip()) - 1
                    end_idx = int(end.strip()) - 1

                    if start_idx < 0 or end_idx >= max_items or start_idx > end_idx:
                        raise ValueError(f"Range {part} is invalid (valid: 1-{max_items})")

                    indices.update(range(start_idx, end_idx + 1))
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Invalid range format: {part}")
                    raise
            else:
                # Single number
                try:
                    idx = int(part) - 1
                    if idx < 0 or idx >= max_items:
                        raise ValueError(f"Number {part} is out of range (valid: 1-{max_items})")
                    indices.add(idx)
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Invalid number: {part}")
                    raise

        return sorted(list(indices))

    def _prompt_api_key(self) -> str:
        default = os.environ.get("VAST_API_KEY", "")
        api_key = questionary.text("Vast.ai API key", default=default).ask()
        if api_key:
            os.environ["VAST_API_KEY"] = api_key
        return api_key

    def _prompt_discord(self) -> Optional[str]:
        default = self.config.get("discord_webhook")
        webhook = questionary.text("Discord webhook (optional)", default=default or "").ask()
        if webhook:
            self.config.set("discord_webhook", webhook)
        return webhook

    def _select_offer(self, api_key: str) -> Optional[Offer]:
        if not api_key:
            self.console.print(cat_say("Skipping Vast.ai lookup (no API key)."))
            return None
        try:
            client = VastClient(api_key=api_key)
            offers = client.list_offers()
        except VastError as exc:
            self.console.print(cat_say(f"Vast.ai query failed: {exc}"))
            return None
        if not offers:
            self.console.print(cat_say("No offers returned."))
            return None
        choice = questionary.select(
            "Choose a GPU offer",
            choices=[Choice(title=f"{o.id} | {o.gpu_name} | ${o.hourly:.2f}/hr", value=o.id) for o in offers],
        ).ask()
        for offer in offers:
            if offer.id == choice:
                return offer
        return None

    def _only_files(self, paths: List[Path], label: str) -> List[str]:
        files: List[str] = []
        for path in paths:
            if path.is_file():
                files.append(str(path))
            else:
                self.console.print(cat_say(f"Skipping {label} target {path} (not a file)."))
        return files

    def _determine_hash_mode(self, hash_path: str) -> str:
        sample = sample_from_file(hash_path)
        if not sample:
            self.console.print(cat_say("Could not read a hash sample; please enter the mode manually."))
            return self._manual_hash_mode()
        guesses = detect_hash_modes(sample)
        if not guesses:
            self.console.print(cat_say("No matching hash types detected. Falling back to manual entry."))
            return self._manual_hash_mode()
        self.console.print(cat_say(f"Sample hash snippet: {sample[:24]}..."))
        choices = [
            Choice(
                title=f"{guess.name} (mode {guess.mode}) — {guess.reason}",
                value=guess.mode,
            )
            for guess in guesses
        ]
        choices.append(Choice(title="Enter manually", value="__manual__"))
        selection = questionary.select(
            "Detected hash types (confirm or pick manually)",
            choices=choices,
        ).ask()
        if selection == "__manual__":
            return self._manual_hash_mode()
        chosen = self._guess_from_mode(guesses, selection)
        if chosen:
            self.console.print(cat_say(f"Using {chosen.name} (mode {chosen.mode})."))
        return selection

    def _manual_hash_mode(self, default: str = "0") -> str:
        return questionary.text("Hashcat hash mode", default=default).ask()

    def _guess_from_mode(self, guesses: List[HashGuess], mode: str) -> Optional[HashGuess]:
        for guess in guesses:
            if guess.mode == mode:
                return guess
        return None

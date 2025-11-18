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
        sync_targets = self._prompt_asset_sync()
        if sync_targets:
            self.console.print(cat_say("Fetching requested assets..."))
            self.asset_manager.sync(sync_targets)
        wordlist_keys = self._pick_assets("wordlists")
        rule_keys = self._pick_assets("rules")
        # ensure selected assets exist
        self.asset_manager.sync(wordlist_keys + rule_keys)
        api_key = self._prompt_api_key()
        webhook = self._prompt_discord()
        notifier = Notifier(webhook)
        hash_path = questionary.text("Path to your hash file", default="~/hashes/hash.txt").ask()
        hash_mode = self._determine_hash_mode(hash_path)
        attack_choice = questionary.select("Choose attack mode", choices=list(ATTACK_MODES.keys())).ask()
        attack_mode = ATTACK_MODES[attack_choice]
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
        self.console.rule(cat_say("Deployment plan"))
        if vast_offer:
            self.console.print(
                f"Offer {vast_offer.id}: {vast_offer.gpu_name} ${vast_offer.hourly:.2f}/hr {vast_offer.vram_gb}GB VRAM"
            )
        else:
            self.console.print(cat_say("No offer selected. You'll need to launch manually."))
        self.console.print(f"Hashcat command:\n[italic]{command}[/italic]")
        if questionary.confirm("Save startup script to file?", default=True).ask():
            path = Path(questionary.text("Path to save script", default="vastcat-startup.sh").ask())
            path.write_text(script)
            os.chmod(path, 0o750)
            self.console.print(cat_say(f"Script written to {path}"))
        self.console.print(cat_say("Ready to run hashcat."))
        if questionary.confirm("Run hashcat locally now?", default=False).ask():
            runner = HashcatRunner(notifier=notifier)
            runner.run(shlex.split(command)[1:])

    def _prompt_asset_sync(self) -> List[str]:
        choices = [
            Choice(title=f"{key}: {asset.description}", value=key)
            for key, asset in ASSET_LIBRARY.items()
        ]
        if not choices:
            return []
        return questionary.checkbox(
            "Pick assets to sync now (space to toggle)",
            choices=choices,
        ).ask()

    def _pick_assets(self, category: str) -> List[str]:
        keys = list_assets(category)
        if not keys:
            return []
        choices = [Choice(title=f"{key}: {ASSET_LIBRARY[key].description}", value=key) for key in keys]
        selected = questionary.checkbox(
            f"Select {category}",
            choices=choices,
            instruction="space to toggle",
        ).ask()
        if not selected:
            self.console.print(cat_say(f"No {category} selected; skipping {category} sync."))
            return []
        return selected

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

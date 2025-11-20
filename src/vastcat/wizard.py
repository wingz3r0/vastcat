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
        self.console.print(cat_say("Welcome to Vastcat's wizard."))

        # Collect all configuration
        config = self._collect_configuration()
        if not config:
            return

        # Review and edit loop
        while True:
            self._show_configuration_summary(config)

            action = questionary.select(
                "What would you like to do?",
                choices=[
                    "Proceed with these settings",
                    "Edit a parameter",
                    "Start over",
                    "Cancel"
                ]
            ).ask()

            if action == "Proceed with these settings":
                break
            elif action == "Edit a parameter":
                if not self._edit_configuration(config):
                    continue
            elif action == "Start over":
                config = self._collect_configuration()
                if not config:
                    return
            else:  # Cancel
                self.console.print(cat_say("Wizard cancelled."))
                return

        # Generate command and proceed
        self._execute_configuration(config)

    def _collect_configuration(self) -> Optional[dict]:
        """Collect all configuration parameters from user with step-by-step navigation."""
        config = {}

        # Define wizard steps
        steps = [
            ("Select Wordlists", self._step_select_wordlists),
            ("Select Rules", self._step_select_rules),
            ("Configure Notifications", self._step_configure_webhook),
            ("Specify Hash File", self._step_get_hash_file),
            ("Detect Hash Mode", self._step_determine_hash_mode),
            ("Choose Attack Mode", self._step_choose_attack_mode),
        ]

        current_step = 0

        while current_step < len(steps):
            step_name, step_func = steps[current_step]
            self.console.print(f"\n[bold cyan]Step {current_step + 1}/{len(steps)}: {step_name}[/bold cyan]")

            result = step_func(config, can_go_back=(current_step > 0))

            if result == "back":
                current_step -= 1
            elif result == "cancel":
                self.console.print(cat_say("Wizard cancelled."))
                return None
            elif result == "next":
                current_step += 1
            else:
                # Should not happen, but handle gracefully
                current_step += 1

        return config

    def _step_select_wordlists(self, config: dict, can_go_back: bool) -> str:
        """Step 1: Select wordlists."""
        wordlist_keys = self._pick_assets_with_back("wordlists", can_go_back)

        if wordlist_keys == "back":
            return "back"
        elif wordlist_keys == "cancel":
            return "cancel"
        elif not wordlist_keys:
            self.console.print(cat_say("No wordlists selected. Hashcat requires at least one wordlist."))
            if questionary.confirm("Try again?", default=True).ask():
                return self._step_select_wordlists(config, can_go_back)
            else:
                return "cancel"

        self.asset_manager.sync(wordlist_keys)
        config['wordlist_keys'] = wordlist_keys
        return "next"

    def _step_select_rules(self, config: dict, can_go_back: bool) -> str:
        """Step 2: Select rules."""
        self.console.print(cat_say("Rules are optional but highly recommended for better cracking results."))
        rule_keys = self._pick_assets_with_back("rules", can_go_back)

        if rule_keys == "back":
            return "back"
        elif rule_keys == "cancel":
            return "cancel"
        elif not rule_keys:
            self.console.print(cat_say("No rules selected. Proceeding with straight wordlist attack."))
        else:
            self.asset_manager.sync(rule_keys)

        config['rule_keys'] = rule_keys if rule_keys not in ["back", "cancel"] else []
        return "next"

    def _step_configure_webhook(self, config: dict, can_go_back: bool) -> str:
        """Step 3: Configure Discord webhook."""
        webhook = self._prompt_discord_with_back(can_go_back)

        if webhook == "back":
            return "back"
        elif webhook == "cancel":
            return "cancel"

        config['webhook'] = webhook
        return "next"

    def _step_get_hash_file(self, config: dict, can_go_back: bool) -> str:
        """Step 4: Get hash file path."""
        hashes_dir = self.config.hashes_dir
        self.console.print(cat_say(f"Upload your hash files to: {hashes_dir}"))

        default_hash_path = str(hashes_dir / "hash.txt")

        while True:
            prompt_text = "Path to your hash file (or 'back' to go back)"
            hash_path = questionary.text(prompt_text, default=default_hash_path).ask()

            if hash_path and hash_path.lower() == "back" and can_go_back:
                return "back"

            expanded_path = Path(hash_path).expanduser()
            if expanded_path.exists():
                config['hash_path'] = hash_path
                return "next"

            self.console.print(cat_say(f"File not found: {expanded_path}. Please try again."))
            if not questionary.confirm("Try another path?", default=True).ask():
                if can_go_back and questionary.confirm("Go back to previous step?", default=False).ask():
                    return "back"
                return "cancel"

    def _step_determine_hash_mode(self, config: dict, can_go_back: bool) -> str:
        """Step 5: Determine hash mode."""
        hash_mode = self._determine_hash_mode_with_back(config['hash_path'], can_go_back)

        if hash_mode == "back":
            return "back"
        elif hash_mode == "cancel":
            return "cancel"

        config['hash_mode'] = hash_mode
        return "next"

    def _step_choose_attack_mode(self, config: dict, can_go_back: bool) -> str:
        """Step 6: Choose attack mode."""
        choices = list(ATTACK_MODES.keys())
        if can_go_back:
            choices.append("← Go back")

        attack_choice = questionary.select("Choose attack mode", choices=choices).ask()

        if attack_choice == "← Go back":
            return "back"

        config['attack_mode'] = ATTACK_MODES[attack_choice]
        config['attack_choice'] = attack_choice
        return "next"

    def _pick_assets_with_back(self, category: str, can_go_back: bool):
        """Pick assets with back navigation support."""
        keys = list_assets(category)
        if not keys:
            return []

        # Display available options
        self.console.print(f"\n[bold]Available {category}:[/bold]")

        # For rules, add a "no rules" option at index 0
        if category == "rules":
            self.console.print(f"  [cyan]0[/cyan]. No rules (straight wordlist attack)")

        for idx, key in enumerate(keys, 1):
            asset = ASSET_LIBRARY[key]
            self.console.print(f"  [cyan]{idx}[/cyan]. {key}: [dim]{asset.description}[/dim]")

        # Get selection
        self.console.print(f"\n[bold]Enter numbers to select {category}:[/bold]")
        if category == "rules":
            examples = "'0' (no rules), '1' (single), '1,2' (multiple), '1-3' (range), 'all' (select all)"
        else:
            examples = "'1' (single), '1,2' (multiple), '1-3' (range), 'all' (select all)"

        if can_go_back:
            examples += ", 'back' (go back)"

        self.console.print(f"[dim]Examples: {examples}[/dim]")

        selection = questionary.text(
            f"Select {category}",
            default="all" if category == "wordlists" else ""
        ).ask()

        if not selection or selection.strip() == "":
            return []

        # Check for back command
        if selection.strip().lower() == "back" and can_go_back:
            return "back"

        # Handle "0" for no rules
        if category == "rules" and selection.strip() == "0":
            self.console.print(f"[green]✓[/green] No rules selected (straight wordlist attack)")
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

    def _prompt_discord_with_back(self, can_go_back: bool):
        """Prompt for Discord webhook with back navigation support."""
        default = self.config.get("discord_webhook")
        prompt_text = "Discord webhook (optional, or 'back' to go back)" if can_go_back else "Discord webhook (optional)"
        webhook = questionary.text(prompt_text, default=default or "").ask()

        if webhook and webhook.lower() == "back" and can_go_back:
            return "back"

        if webhook:
            self.config.set("discord_webhook", webhook)

        return webhook

    def _determine_hash_mode_with_back(self, hash_path: str, can_go_back: bool):
        """Determine hash mode with back navigation support."""
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

        if can_go_back:
            choices.append(Choice(title="← Go back", value="__back__"))

        selection = questionary.select(
            "Detected hash types (confirm or pick manually)",
            choices=choices,
        ).ask()

        if selection == "__back__":
            return "back"
        elif selection == "__manual__":
            return self._manual_hash_mode()

        chosen = self._guess_from_mode(guesses, selection)
        if chosen:
            self.console.print(cat_say(f"Using {chosen.name} (mode {chosen.mode})."))
        return selection

    def _show_configuration_summary(self, config: dict) -> None:
        """Display current configuration to user."""
        wordlist_paths = self.asset_manager.resolved_paths(config['wordlist_keys'])
        rule_paths = self.asset_manager.resolved_paths(config['rule_keys'])

        self.console.rule(cat_say("Configuration Summary"))
        self.console.print(f"[bold]1. Hash file:[/bold] {config['hash_path']}")
        self.console.print(f"[bold]2. Hash mode:[/bold] {config['hash_mode']}")
        self.console.print(f"[bold]3. Attack mode:[/bold] {config['attack_choice']}")
        self.console.print(f"[bold]4. Wordlists:[/bold] {', '.join([p.name for p in wordlist_paths])}")
        if rule_paths:
            self.console.print(f"[bold]5. Rules:[/bold] {', '.join([p.name for p in rule_paths])}")
        else:
            self.console.print(f"[bold]5. Rules:[/bold] None (straight attack)")
        self.console.print(f"[bold]6. Discord webhook:[/bold] {'Configured' if config['webhook'] else 'Not configured'}\n")

    def _edit_configuration(self, config: dict) -> bool:
        """Allow user to edit a specific parameter. Returns True if edit was made."""
        edit_choices = [
            "1. Hash file path",
            "2. Hash mode",
            "3. Attack mode",
            "4. Wordlists",
            "5. Rules",
            "6. Discord webhook",
            "Back to summary"
        ]

        choice = questionary.select("Which parameter would you like to edit?", choices=edit_choices).ask()

        if choice == "Back to summary":
            return False
        elif choice.startswith("1"):
            # Edit hash file
            while True:
                hash_path = questionary.text("Path to your hash file", default=config['hash_path']).ask()
                expanded_path = Path(hash_path).expanduser()
                if expanded_path.exists():
                    config['hash_path'] = hash_path
                    # Re-detect hash mode
                    config['hash_mode'] = self._determine_hash_mode(hash_path)
                    break
                self.console.print(cat_say(f"File not found: {expanded_path}. Please try again."))
        elif choice.startswith("2"):
            # Edit hash mode
            config['hash_mode'] = self._manual_hash_mode(default=config['hash_mode'])
        elif choice.startswith("3"):
            # Edit attack mode
            attack_choice = questionary.select("Choose attack mode", choices=list(ATTACK_MODES.keys()),
                                             default=config['attack_choice']).ask()
            config['attack_mode'] = ATTACK_MODES[attack_choice]
            config['attack_choice'] = attack_choice
        elif choice.startswith("4"):
            # Edit wordlists
            wordlist_keys = self._pick_assets("wordlists")
            if wordlist_keys:
                self.asset_manager.sync(wordlist_keys)
                config['wordlist_keys'] = wordlist_keys
        elif choice.startswith("5"):
            # Edit rules
            rule_keys = self._pick_assets("rules")
            self.asset_manager.sync(rule_keys)
            config['rule_keys'] = rule_keys
        elif choice.startswith("6"):
            # Edit webhook
            config['webhook'] = self._prompt_discord()

        return True

    def _execute_configuration(self, config: dict) -> None:
        """Execute hashcat with the configured parameters."""
        wordlist_paths = self.asset_manager.resolved_paths(config['wordlist_keys'])
        rule_paths = self.asset_manager.resolved_paths(config['rule_keys'])
        notifier = Notifier(config['webhook'])

        command = render_hashcat_command(
            hash_path=config['hash_path'],
            hash_mode=config['hash_mode'],
            attack_mode=config['attack_mode'],
            wordlists=self._only_files(wordlist_paths, "wordlist"),
            rules=self._only_files(rule_paths, "rule"),
        )
        script = render_startup_script(wordlist_paths + rule_paths)

        self.console.rule(cat_say("Hashcat Command"))
        self.console.print(f"\n[bold]Command:[/bold]\n[italic]{command}[/italic]")

        if questionary.confirm("Save startup script to file?", default=True).ask():
            path = Path(questionary.text("Path to save script", default="vastcat-startup.sh").ask())
            path.write_text(script)
            os.chmod(path, 0o750)
            self.console.print(cat_say(f"Script written to {path}"))

        self.console.print(cat_say("Ready to run hashcat."))
        if questionary.confirm("Run hashcat locally now?", default=False).ask():
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

        # For rules, add a "no rules" option at index 0
        if category == "rules":
            self.console.print(f"  [cyan]0[/cyan]. No rules (straight wordlist attack)")

        for idx, key in enumerate(keys, 1):
            asset = ASSET_LIBRARY[key]
            self.console.print(f"  [cyan]{idx}[/cyan]. {key}: [dim]{asset.description}[/dim]")

        # Get selection
        self.console.print(f"\n[bold]Enter numbers to select {category}:[/bold]")
        if category == "rules":
            self.console.print("[dim]Examples: '0' (no rules), '1' (single), '1,2' (multiple), '1-3' (range), 'all' (select all)[/dim]")
        else:
            self.console.print("[dim]Examples: '1' (single), '1,2' (multiple), '1-3' (range), 'all' (select all)[/dim]")

        selection = questionary.text(
            f"Select {category}",
            default="all" if category == "wordlists" else ""
        ).ask()

        if not selection or selection.strip() == "":
            return []

        # Handle "0" for no rules
        if category == "rules" and selection.strip() == "0":
            self.console.print(f"[green]✓[/green] No rules selected (straight wordlist attack)")
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

    def _prompt_discord(self) -> Optional[str]:
        default = self.config.get("discord_webhook")
        webhook = questionary.text("Discord webhook (optional)", default=default or "").ask()
        if webhook:
            self.config.set("discord_webhook", webhook)
        return webhook

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

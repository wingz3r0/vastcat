# Vastcat

Vastcat is a cat-themed (:3) interactive wizard for configuring and running [hashcat](https://hashcat.net/hashcat/) password cracking jobs. It automates wordlist/ruleset management, hash type detection, and provides an intuitive step-by-step interface with optional Discord notifications.

## Features
- **Automatic hashcat installation** during vastcat setup (detects your platform and installs via package manager).
- **Interactive wizard** with 6-step configuration flow and back navigation.
- **Automatic hash type detection** for common formats (MD5, SHA, NTLM, bcrypt, etc.).
- Fetches popular wordlists and rules: RockYou, WeakPass, Seclists, Dive, Kaonashi, OneRuleToRuleThemAll, and more.
- Generates reproducible hashcat commands and deployment scripts.
- Sends run status updates to Discord via webhook.
- Provides reusable config stored in `~/.config/vastcat/config.yaml`.

## Quick start

### 1. Install Vastcat
```bash
pip install -e .
```

**Hashcat will be automatically installed** during the installation process. The installer will detect your platform (Ubuntu, Fedora, Arch, macOS) and use the appropriate package manager.

If automatic installation fails, run `vastcat install-hashcat` for manual installation instructions.

### 2. Run the Wizard
```bash
vastcat wizard
```

The wizard will guide you through 6 steps:
1. **Select Wordlists** - Choose from popular wordlists (RockYou, WeakPass, SecLists).
2. **Select Rules** - Optional rule sets for transformation attacks.
3. **Configure Notifications** - Set up Discord webhooks for status updates.
4. **Specify Hash File** - Point to your hash file (stored in `~/vastcat/hashes/`).
5. **Detect Hash Mode** - Automatic detection with manual override option.
6. **Choose Attack Mode** - Straight, combinator, mask, or hybrid attacks.

After configuration, review your settings and run hashcat locally or save a deployment script.

## Commands
- `vastcat wizard` — Interactive guided flow (recommended).
- `vastcat install-hashcat` — Show hashcat installation instructions.
- `vastcat assets sync` — Download/update configured wordlists and rules.
- `vastcat assets list` — List all available assets.
- `vastcat run` — Run hashcat with manual parameters (advanced users).

## Configuration
The first run creates `~/.config/vastcat/config.yaml` and sets up directories:
- **Cache directory** (`~/.cache/vastcat/`) - Downloaded wordlists and rules
- **Hashes directory** (`~/vastcat/hashes/`) - Upload your hash files here

You can edit the config to control:
- Cache and hashes directory locations
- Hashcat binary path and tuning flags
- Discord webhook URL for alerts
- Asset download preferences

## Security
Review all downloaded assets and generated scripts before running them on production data. Vastcat does not store hashes or cracked output; they remain on your instance.

## License
MIT

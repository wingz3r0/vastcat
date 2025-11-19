# Vastcat

Vastcat is a cat-themed (:3) deployment wizard for launching [hashcat](https://hashcat.net/hashcat/) workloads on [Vast.ai](https://vast.ai/). It automates wordlist/ruleset collection, instance provisioning, and job orchestration with optional Discord notifications.

## Features
- **Automatic hashcat installation** during vastcat setup (detects your platform and installs via package manager).
- Fetches popular wordlists and rules: RockYou, WeakPass, Seclists, Dive, Kaonashi, OneRuleToRuleThemAll, and more.
- Guides you through Vast.ai offer selection, storage layout, and hashcat attack planning via an interactive wizard.
- Generates reproducible deployment manifests and shell scripts to bootstrap Ubuntu+CUDA base images.
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

The wizard will:
1. Download requested wordlists/rules to your cache directory.
2. Detect your hash type automatically.
3. Let you choose attack mode and configure the cracking job.
4. Optionally deploy to Vast.ai GPU instances or run locally.
5. Send Discord webhook notifications if configured.

## Commands
- `vastcat wizard` — friendly guided flow that ties everything together.
- `vastcat install-hashcat` — show hashcat installation instructions.
- `vastcat assets sync` — download/update configured assets.
- `vastcat deploy plan` — print a cloud-init script to bootstrap a new instance.
- `vastcat deploy start` — call the Vast.ai API to spin up an instance with the plan.
- `vastcat run` — run hashcat locally.
- `vastcat offers` — list available Vast.ai GPU offers.

## Configuration
The first run creates `~/.config/vastcat/config.yaml`. You can edit it to control:
- Cache directory for assets.
- Default Vast.ai image (Ubuntu + CUDA).
- Hashcat tuning flags (workload profile, power limits, etc.).
- Discord webhook URL for alerts.

## Security
Review all downloaded assets and generated scripts before running them on production data. Vastcat does not store hashes or cracked output; they remain on your instance.

## License
MIT

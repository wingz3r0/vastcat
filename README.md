# Vastcat

Vastcat is a cat-themed (but not furry) deployment wizard for launching [hashcat](https://hashcat.net/hashcat/) workloads on [Vast.ai](https://vast.ai/). It automates wordlist/ruleset collection, instance provisioning, and job orchestration with optional Discord notifications.

## Features
- Fetches popular wordlists and rules: RockYou, WeakPass, Seclists, Dive, Kaonashi, OneRuleToRuleThemAll, and more.
- Guides you through Vast.ai offer selection, storage layout, and hashcat attack planning via an interactive wizard.
- Generates reproducible deployment manifests and shell scripts to bootstrap Ubuntu+CUDA base images.
- Sends run status updates to Discord via webhook.
- Provides reusable config stored in `~/.config/vastcat/config.yaml`.

## Quick start
```bash
pip install -e .
vastcat wizard
```

The wizard will:
1. Ensure your cache directory has the requested wordlists/rules.
2. Ask for your Vast.ai API key (`VAST_API_KEY`) and suggest GPU offers based on hashcat needs.
3. Generate a deployment plan (cloud-init/bash script) and optionally call the Vast.ai API for you.
4. Launch hashcat with the selected attack mode, rules, and wordlists, with Discord webhook notifications if configured.

## Commands
- `vastcat assets sync` — download/update configured assets.
- `vastcat deploy plan` — print a cloud-init script to bootstrap a new instance.
- `vastcat deploy start` — call the Vast.ai API to spin up an instance with the plan.
- `vastcat run` — run hashcat locally on the instance.
- `vastcat wizard` — friendly guided flow that ties everything together.

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

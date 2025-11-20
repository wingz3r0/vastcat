# Vastcat

Vastcat is an interactive wizard for configuring and running [hashcat](https://hashcat.net/hashcat/) password cracking jobs. It handles wordlist and ruleset management, hash type detection, and provides a step-by-step configuration interface.

## Features

- Automatic hashcat installation during setup (supports Ubuntu, Debian, Fedora, RHEL, Arch, and macOS)
- Interactive 6-step wizard with back navigation for correcting mistakes
- Hash type detection for 300+ formats using name-that-hash library
- Automated download and management of popular wordlists and rulesets
- Support for multiple wordlists: RockYou, WeakPass, SecLists, Hashes.org, and more
- Support for multiple rulesets: dive, OneRuleToRuleThemAll, Kaonashi, and more
- Optional Discord webhook notifications for job status updates
- Configuration stored in `~/.config/vastcat/config.yaml`
- Generates hashcat command scripts for local execution or manual deployment

## Installation

### Install from source
```bash
pip install -e .
```

The installer will attempt to automatically install hashcat using your system's package manager. If automatic installation fails, run `vastcat install-hashcat` for platform-specific instructions.

### Install dependencies
Vastcat requires Python 3.9 or later. The following dependencies will be installed automatically:
- typer (CLI framework)
- questionary (interactive prompts)
- requests (HTTP client)
- PyYAML (config management)
- tqdm (progress bars)
- name-that-hash (hash type detection)

For 7z wordlist extraction (e.g., WeakPass), install p7zip:
```bash
# Ubuntu/Debian
sudo apt install p7zip-full

# Fedora/RHEL
sudo dnf install p7zip

# macOS
brew install p7zip
```

## Usage

### Run the wizard
```bash
vastcat wizard
```

The wizard guides you through 6 configuration steps:

1. **Select Wordlists** - Choose one or more wordlists to download and use
2. **Select Rules** - Choose rulesets for transformation attacks, or select "No rules"
3. **Configure Notifications** - Optionally set up Discord webhook for status updates
4. **Specify Hash File** - Provide path to your hash file (default location: `~/vastcat/hashes/`)
5. **Detect Hash Mode** - Automatic detection using name-that-hash, with manual override option
6. **Choose Attack Mode** - Select attack type: straight, combinator, mask, or hybrid

After completing the wizard, you can review your configuration, make edits, and generate the hashcat command. The wizard produces a shell script that can be run locally or copied to another machine.

### Navigating the wizard
The wizard supports back navigation:
- Type `back` at any text input prompt to return to the previous step
- Select "Go back" from menu options to return to the previous step
- After completing all steps, you can review and edit any configuration before running

## Available Commands

- `vastcat wizard` - Start the interactive configuration wizard (recommended)
- `vastcat install-hashcat` - Display platform-specific hashcat installation instructions
- `vastcat assets sync` - Download and update configured wordlists and rulesets
- `vastcat assets list` - List all available wordlists and rulesets
- `vastcat run` - Run hashcat with manual parameters (for advanced users)

## Configuration

On first run, Vastcat creates `~/.config/vastcat/config.yaml` and sets up two directories:
- `~/.cache/vastcat/` - Storage for downloaded wordlists and rulesets
- `~/vastcat/hashes/` - Default location for hash files

You can edit `config.yaml` to customize:
- Cache and hashes directory locations
- Hashcat binary path
- Default Discord webhook URL
- Asset download behavior
- Hashcat tuning flags

## Hash Type Detection

Vastcat uses the name-that-hash library to automatically detect hash types. It can identify over 300 different hash formats including:
- Simple hashes: MD5, SHA-1, SHA-256, SHA-512
- Unix hashes: bcrypt, md5crypt, sha256crypt, sha512crypt
- Windows hashes: NTLM, NetNTLMv1, NetNTLMv2
- Kerberos: TGS-REP tickets
- And many more

When automatic detection is uncertain or incorrect, you can manually specify the hashcat mode number.

## Security Notes

- Review all downloaded wordlists and rulesets before use
- Examine generated scripts before execution
- Vastcat does not store or transmit hash data or cracked passwords
- All processing occurs on your local machine or deployment target

## License
MIT

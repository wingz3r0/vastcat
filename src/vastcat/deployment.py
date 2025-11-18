"""Deployment helpers for provisioning Ubuntu CUDA instances."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import Iterable, List

HASHCAT_URL = "https://hashcat.net/files/hashcat-7.1.2.tar.gz"


def render_startup_script(asset_paths: Iterable[Path], install_dir: str = "/opt/hashcat") -> str:
    files = " ".join(str(path) for path in asset_paths)
    return dedent(
        f"""
        #!/bin/bash
        set -euxo pipefail
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        apt-get install -y build-essential wget curl p7zip-full git python3 python3-venv jq
        mkdir -p {install_dir}
        cd /tmp
        wget -q {HASHCAT_URL} -O hashcat.tar.gz
        tar -xzf hashcat.tar.gz
        rsync -a hashcat-*/* {install_dir}/
        ln -sf {install_dir}/hashcat /usr/local/bin/hashcat
        mkdir -p /opt/vastcat/assets
        # Placeholder for syncing assets that have been pre-fetched
        for file in {files}; do
            echo "$file" >> /opt/vastcat/assets/.manifest
        done
        echo "Vastcat bootstrap complete"
        """.strip()
    )


def render_hashcat_command(
    hash_path: str,
    hash_mode: str,
    attack_mode: str,
    wordlists: List[str],
    rules: List[str],
    extra_args: str = "--status --status-timer=60",
) -> str:
    words = " ".join(wordlists)
    rules_flags = " ".join(f"-r {rule}" for rule in rules)
    return f"hashcat -m {hash_mode} -a {attack_mode} {extra_args} {hash_path} {words} {rules_flags}".strip()

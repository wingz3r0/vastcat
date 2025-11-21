"""Hashcat command helpers."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import os
import shlex
import shutil
import subprocess

from .notifier import Notifier


class HashcatRunner:
    def __init__(self, binary: Optional[str] = None, notifier: Optional[Notifier] = None) -> None:
        self.binary = binary or self._find_hashcat_binary()
        self.notifier = notifier or Notifier()

    def _find_hashcat_binary(self) -> str:
        """Find hashcat binary in PATH or common locations."""
        # First, check our local installation (installed by setup.py)
        local_install = Path.home() / ".local" / "share" / "vastcat" / "hashcat" / "hashcat"
        if local_install.exists() and os.access(local_install, os.X_OK):
            return str(local_install)

        # Check ~/.local/bin (symlink location)
        local_bin = Path.home() / ".local" / "bin" / "hashcat"
        if local_bin.exists() and os.access(local_bin, os.X_OK):
            return str(local_bin)

        # Check if hashcat is in PATH
        hashcat_path = shutil.which("hashcat")
        if hashcat_path:
            return hashcat_path

        # Fall back to common installation locations
        common_paths = [
            "/opt/hashcat/hashcat",
            "/usr/bin/hashcat",
            "/usr/local/bin/hashcat",
            str(Path.home() / "hashcat" / "hashcat"),
        ]

        for path_str in common_paths:
            path = Path(path_str)
            if path.exists() and os.access(path, os.X_OK):
                return str(path)

        # Return default and let ensure_binary() raise the error with instructions
        return "hashcat"

    def ensure_binary(self) -> None:
        # If binary is just "hashcat", try to find it in PATH again
        if self.binary == "hashcat":
            path_binary = shutil.which("hashcat")
            if path_binary:
                self.binary = path_binary
                return

        path = Path(self.binary)
        if not path.exists():
            raise FileNotFoundError(
                f"Cannot find hashcat binary at {path}.\n\n"
                f"Install hashcat:\n"
                f"  Ubuntu/Debian: sudo apt install hashcat\n"
                f"  Fedora/RHEL:   sudo dnf install hashcat\n"
                f"  Arch:          sudo pacman -S hashcat\n"
                f"  macOS:         brew install hashcat\n"
                f"  From source:   https://hashcat.net/hashcat/\n\n"
                f"Or set HASHCAT_BINARY environment variable to your hashcat location."
            )
        if not os.access(path, os.X_OK):
            raise PermissionError(f"Hashcat binary {path} is not executable")

    def run(self, args: List[str], dry_run: bool = False) -> int:
        self.ensure_binary()
        cmd = [self.binary] + args
        cmd_display = " ".join(shlex.quote(part) for part in cmd)
        if dry_run:
            print(f"[dry-run] {cmd_display}")
            return 0
        self.notifier.notify("Hashcat started", cmd_display)
        process = subprocess.Popen(cmd)
        code = process.wait()
        status = "completed" if code == 0 else f"failed ({code})"
        self.notifier.notify("Hashcat status", f"Run {status}")
        return code

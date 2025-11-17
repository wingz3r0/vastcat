"""Hashcat command helpers."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import os
import shlex
import subprocess

from .notifier import Notifier


class HashcatRunner:
    def __init__(self, binary: Optional[str] = None, notifier: Optional[Notifier] = None) -> None:
        self.binary = binary or "/opt/hashcat/hashcat"
        self.notifier = notifier or Notifier()

    def ensure_binary(self) -> None:
        path = Path(self.binary)
        if not path.exists():
            raise FileNotFoundError(f"Cannot find hashcat binary at {path}")
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

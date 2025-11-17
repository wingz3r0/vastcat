"""Hash type detection helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import re


@dataclass
class HashGuess:
    name: str
    mode: str
    confidence: float
    reason: str


_PATTERNS: List[HashGuess] = [
    HashGuess("MD5", "0", 0.85, "32 hex chars"),
    HashGuess("SHA-1", "100", 0.8, "40 hex chars"),
    HashGuess("SHA-224", "1300", 0.7, "56 hex chars"),
    HashGuess("SHA-256", "1400", 0.8, "64 hex chars"),
    HashGuess("SHA-384", "10800", 0.6, "96 hex chars"),
    HashGuess("SHA-512", "1700", 0.8, "128 hex chars"),
]

_REGEXES = {
    "0": re.compile(r"^[a-fA-F0-9]{32}$"),
    "100": re.compile(r"^[a-fA-F0-9]{40}$"),
    "1300": re.compile(r"^[a-fA-F0-9]{56}$"),
    "1400": re.compile(r"^[a-fA-F0-9]{64}$"),
    "10800": re.compile(r"^[a-fA-F0-9]{96}$"),
    "1700": re.compile(r"^[a-fA-F0-9]{128}$"),
    "3200": re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$"),
    "500": re.compile(r"^\$1\$[./A-Za-z0-9]{1,8}\$[./A-Za-z0-9]{22}$"),
    "7400": re.compile(r"^\$5\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{43}$"),
    "1800": re.compile(r"^\$6\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{86}$"),
}

_NAMED_SPECIALS = {
    "3200": HashGuess("bcrypt", "3200", 0.95, "starts with $2*$"),
    "500": HashGuess("md5crypt", "500", 0.85, "starts with $1$"),
    "7400": HashGuess("sha256crypt", "7400", 0.85, "starts with $5$"),
    "1800": HashGuess("sha512crypt", "1800", 0.85, "starts with $6$"),
}


def detect_hash_modes(sample: str) -> List[HashGuess]:
    """Return best-guess hash modes matching the provided sample."""
    sample = sample.strip()
    matches: List[HashGuess] = []
    if not sample:
        return matches
    for guess in _PATTERNS:
        pattern = _REGEXES.get(guess.mode)
        if pattern and pattern.match(sample):
            matches.append(guess)
    for mode, guess in _NAMED_SPECIALS.items():
        pattern = _REGEXES[mode]
        if pattern.match(sample):
            matches.append(guess)
    # Remove duplicates while preserving order
    deduped: List[HashGuess] = []
    seen = set()
    for guess in matches:
        if guess.mode in seen:
            continue
        deduped.append(guess)
        seen.add(guess.mode)
    return deduped


def sample_from_file(path: str) -> Optional[str]:
    """Grab a representative hash entry from the provided file."""
    file_path = Path(path).expanduser()
    if not file_path.exists():
        return None
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                candidate = _extract_candidate(line)
                if candidate:
                    return candidate
    except OSError:
        return None
    return None


def _extract_candidate(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    # pick the longest colon-separated field since it usually holds the hash
    fields = [field.strip() for field in stripped.split(":") if field.strip()]
    if not fields:
        return None
    return max(fields, key=len)


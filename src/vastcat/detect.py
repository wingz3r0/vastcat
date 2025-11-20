"""Hash type detection helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import re

try:
    from name_that_hash import runner as nth_runner
    NTH_AVAILABLE = True
except ImportError:
    NTH_AVAILABLE = False


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
    # Simple hashes
    "0": re.compile(r"^[a-fA-F0-9]{32}$"),
    "100": re.compile(r"^[a-fA-F0-9]{40}$"),
    "1300": re.compile(r"^[a-fA-F0-9]{56}$"),
    "1400": re.compile(r"^[a-fA-F0-9]{64}$"),
    "10800": re.compile(r"^[a-fA-F0-9]{96}$"),
    "1700": re.compile(r"^[a-fA-F0-9]{128}$"),
    # Unix hashes
    "3200": re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$"),
    "500": re.compile(r"^\$1\$[./A-Za-z0-9]{1,8}\$[./A-Za-z0-9]{22}$"),
    "7400": re.compile(r"^\$5\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{43}$"),
    "1800": re.compile(r"^\$6\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{86}$"),
    # Windows/Domain hashes
    "1000": re.compile(r"^[a-fA-F0-9]{32}:[a-fA-F0-9]{32}$"),  # NTLM (with LM)
    "3000": re.compile(r"^[a-fA-F0-9]{32}$"),  # LM
    "5500": re.compile(r"^[^:]+::[^:]+:[a-fA-F0-9]{16}:[a-fA-F0-9]{32}:[a-fA-F0-9]+$"),  # NetNTLMv1
    "5600": re.compile(r"^[^:]+::[^:]+:[a-fA-F0-9]{16}:[a-fA-F0-9]{32}:[a-fA-F0-9]+$"),  # NetNTLMv2
    "13100": re.compile(r"^\$krb5tgs\$23\$.*"),  # Kerberos TGS
    # Other common formats
    "900": re.compile(r"^\{[A-Z0-9]+\}[a-fA-F0-9]{32}$"),  # MD4
    "1100": re.compile(r"^\{[A-Z0-9]+\}[a-fA-F0-9]{40}$"),  # Domain Cached Credentials (DCC)
}

_NAMED_SPECIALS = {
    "3200": HashGuess("bcrypt", "3200", 0.95, "starts with $2*$"),
    "500": HashGuess("md5crypt", "500", 0.85, "starts with $1$"),
    "7400": HashGuess("sha256crypt", "7400", 0.85, "starts with $5$"),
    "1800": HashGuess("sha512crypt", "1800", 0.85, "starts with $6$"),
    "1000": HashGuess("NTLM", "1000", 0.9, "LM:NTLM format"),
    "3000": HashGuess("LM", "3000", 0.8, "32 hex (could be MD5 or LM)"),
    "5500": HashGuess("NetNTLMv1", "5500", 0.9, "user::domain:challenge:response format"),
    "5600": HashGuess("NetNTLMv2", "5600", 0.95, "user::domain:challenge:response format"),
    "13100": HashGuess("Kerberos TGS-REP", "13100", 0.95, "starts with $krb5tgs$"),
    "900": HashGuess("MD4", "900", 0.8, "{hash} format"),
    "1100": HashGuess("Domain Cached Credentials", "1100", 0.85, "{hash} format"),
}


def detect_hash_modes(sample: str) -> List[HashGuess]:
    """Return best-guess hash modes matching the provided sample.

    Uses name-that-hash library when available (300+ hash types).
    Falls back to regex-based detection if library is not installed.
    """
    sample = sample.strip()
    if not sample:
        return []

    # Use name-that-hash if available (much better detection)
    if NTH_AVAILABLE:
        return _detect_with_name_that_hash(sample)

    # Fallback to regex-based detection
    return _detect_with_regex(sample)


def _detect_with_name_that_hash(sample: str) -> List[HashGuess]:
    """Detect hash type using name-that-hash library."""
    try:
        # Use full detection for comprehensive hash type coverage
        result = nth_runner.api_return_hashes_as_dict([sample], {})

        if not result or sample not in result:
            return []

        matches: List[HashGuess] = []
        hash_results = result[sample]

        # Convert name-that-hash results to HashGuess objects
        for idx, match in enumerate(hash_results[:10]):  # Limit to top 10
            name = match.get("name", "Unknown")
            hashcat_mode = match.get("hashcat")
            description = match.get("description", "")

            # Skip if no hashcat mode
            if hashcat_mode is None:
                continue

            # Calculate confidence based on position (first match is most likely)
            # name-that-hash orders by popularity/likelihood
            confidence = 0.95 - (idx * 0.05)  # 0.95, 0.90, 0.85, ...
            confidence = max(confidence, 0.5)  # Floor at 0.5

            # Build reason string
            reason = description if description else f"Detected as {name}"

            matches.append(HashGuess(
                name=name,
                mode=str(hashcat_mode),
                confidence=confidence,
                reason=reason
            ))

        return matches

    except Exception:
        # If name-that-hash fails, fall back to regex
        return _detect_with_regex(sample)


def _detect_with_regex(sample: str) -> List[HashGuess]:
    """Fallback regex-based hash detection.

    Checks more specific formats first (NetNTLM, bcrypt, etc.)
    before falling back to simple hex hashes.
    """
    matches: List[HashGuess] = []

    # Check named/special formats FIRST (more specific)
    for mode, guess in _NAMED_SPECIALS.items():
        pattern = _REGEXES.get(mode)
        if pattern and pattern.match(sample):
            matches.append(guess)

    # Then check simple patterns (less specific, many false positives)
    # Only add if not already matched by a named special
    matched_modes = {g.mode for g in matches}
    for guess in _PATTERNS:
        if guess.mode in matched_modes:
            continue
        pattern = _REGEXES.get(guess.mode)
        if pattern and pattern.match(sample):
            matches.append(guess)

    # Sort by confidence (highest first)
    matches.sort(key=lambda g: g.confidence, reverse=True)

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


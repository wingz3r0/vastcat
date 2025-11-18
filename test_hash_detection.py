#!/usr/bin/env python3
"""Test hash detection improvements."""

import sys
sys.path.insert(0, '/opt/vastcat')

from src.vastcat.detect import detect_hash_modes

# Test cases: (hash_sample, expected_mode, description)
test_cases = [
    # Simple hashes
    ("5f4dcc3b5aa765d61d8327deb882cf99", "0", "MD5"),
    ("356a192b7913b04c54574d18c28d46e6395428ab", "100", "SHA-1"),
    ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "1400", "SHA-256"),

    # Unix hashes
    ("$1$salt$qJH7.N4xYta3aEG/dfqo/0", "500", "md5crypt"),
    ("$2a$05$LhayLxezLhK1LhWvKxCyLOj0j1u.Kj0jZ0pEmm134uzrQlFvQJLF6", "3200", "bcrypt"),
    ("$5$rounds=5000$saltsalt$xyz", "7400", "sha256crypt"),
    ("$6$rounds=5000$saltsalt$xyz", "1800", "sha512crypt"),

    # Windows/Domain hashes
    ("admin::DOMAIN:1122334455667788:b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0:0102030405060708", "5600", "NetNTLMv2"),
    ("user::LAB:122334455667788:abcdef1234567890abcdef1234567890:0102030405", "5500", "NetNTLMv1"),
    ("aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117ad06bdd830b7586c", "1000", "NTLM"),

    # Kerberos
    ("$krb5tgs$23$*user$DOMAIN.COM$service/host*$abc", "13100", "Kerberos TGS"),
]

print("=== Testing Hash Detection ===\n")

passed = 0
failed = 0

for hash_sample, expected_mode, description in test_cases:
    detected = detect_hash_modes(hash_sample)

    if not detected:
        print(f"✗ {description:20} | No matches found")
        print(f"  Sample: {hash_sample[:60]}...")
        failed += 1
        continue

    # Check if expected mode is in the detected modes
    detected_modes = [g.mode for g in detected]

    if expected_mode in detected_modes:
        # Find the guess
        guess = next((g for g in detected if g.mode == expected_mode), None)
        if detected_modes[0] == expected_mode:
            print(f"✓ {description:20} | Mode: {expected_mode:5} | {guess.name:25} | Confidence: {guess.confidence}")
        else:
            print(f"⚠ {description:20} | Mode: {expected_mode:5} | {guess.name:25} | NOT first choice (got {detected[0].mode})")
        passed += 1
    else:
        print(f"✗ {description:20} | Expected {expected_mode}, got {detected_modes}")
        print(f"  Sample: {hash_sample[:60]}...")
        for g in detected:
            print(f"    - {g.mode}: {g.name} ({g.confidence})")
        failed += 1

print(f"\n{'='*80}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*80}")

sys.exit(0 if failed == 0 else 1)

#!/usr/bin/env python3
"""Test the numbered menu selection parser."""

import sys
sys.path.insert(0, '/opt/vastcat')

from src.vastcat.wizard import Wizard
from rich.console import Console

def test_parse_selection():
    """Test all selection formats."""
    wizard = Wizard(Console())

    test_cases = [
        # (input, max_items, expected_indices, description)
        ("1", 5, [0], "Single item"),
        ("1,2,3", 5, [0, 1, 2], "Multiple items"),
        ("1-3", 5, [0, 1, 2], "Range"),
        ("1,3-5", 5, [0, 2, 3, 4], "Mixed (single + range)"),
        ("all", 5, [0, 1, 2, 3, 4], "All items"),
        ("5", 5, [4], "Last item"),
        ("1-5", 5, [0, 1, 2, 3, 4], "Full range"),
        (" 1 , 3 ", 5, [0, 2], "With spaces"),
        ("2-2", 5, [1], "Single item as range"),
    ]

    print("=== Testing _parse_selection ===\n")

    passed = 0
    failed = 0

    for input_str, max_items, expected, description in test_cases:
        try:
            result = wizard._parse_selection(input_str, max_items)
            if result == expected:
                print(f"✓ {description:30} | Input: {input_str:10} | Result: {result}")
                passed += 1
            else:
                print(f"✗ {description:30} | Input: {input_str:10} | Expected: {expected}, Got: {result}")
                failed += 1
        except Exception as e:
            print(f"✗ {description:30} | Input: {input_str:10} | Error: {e}")
            failed += 1

    # Test error cases
    print("\n=== Testing Error Cases ===\n")

    error_cases = [
        ("0", 5, "Number out of range (0)"),
        ("6", 5, "Number out of range (too high)"),
        ("1-10", 5, "Range too high"),
        ("5-3", 5, "Reversed range"),
        ("abc", 5, "Invalid input"),
        ("1,abc,3", 5, "Mixed valid/invalid"),
    ]

    for input_str, max_items, description in error_cases:
        try:
            result = wizard._parse_selection(input_str, max_items)
            print(f"✗ {description:30} | Input: {input_str:10} | Should have raised error, got: {result}")
            failed += 1
        except ValueError as e:
            print(f"✓ {description:30} | Input: {input_str:10} | Correctly raised: {str(e)[:40]}...")
            passed += 1
        except Exception as e:
            print(f"✗ {description:30} | Input: {input_str:10} | Wrong error type: {type(e).__name__}")
            failed += 1

    print(f"\n{'='*70}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*70}")

    return failed == 0

if __name__ == "__main__":
    success = test_parse_selection()
    sys.exit(0 if success else 1)

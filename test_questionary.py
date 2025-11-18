#!/usr/bin/env python3
"""Test questionary checkbox functionality."""

import questionary
from questionary import Choice

# Test 1: Simple checkbox
print("=== Test 1: Simple checkbox ===")
try:
    result = questionary.checkbox(
        "Select items (use arrow keys, space to toggle):",
        choices=["Item 1", "Item 2", "Item 3"]
    ).ask()
    print(f"Selected: {result}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Checkbox with Choice objects
print("\n=== Test 2: Checkbox with Choice objects ===")
try:
    result = questionary.checkbox(
        "Select items:",
        choices=[
            Choice(title="First item", value="first"),
            Choice(title="Second item", value="second"),
            Choice(title="Third item", value="third"),
        ]
    ).ask()
    print(f"Selected: {result}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 3: Simple select (fallback option)
print("\n=== Test 3: Simple select (single choice) ===")
try:
    result = questionary.select(
        "Select one item:",
        choices=["Item 1", "Item 2", "Item 3"]
    ).ask()
    print(f"Selected: {result}")
except Exception as e:
    print(f"ERROR: {e}")

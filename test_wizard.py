#!/usr/bin/env python3
"""Quick test for wizard asset selection."""

from src.vastcat.assets import ASSET_LIBRARY, list_assets
from questionary import Choice
import questionary

def test_pick_assets():
    """Test the asset selection logic."""
    category = "wordlists"
    keys = list_assets(category)

    print(f"\n=== Testing {category} selection ===")
    print(f"Available {category}: {keys}")

    if not keys:
        print("ERROR: No assets found!")
        return

    choices = [Choice(title=f"{key}: {ASSET_LIBRARY[key].description}", value=key) for key in keys]

    print(f"\nChoices created: {len(choices)}")
    for choice in choices:
        print(f"  - {choice.title} -> {choice.value}")

    print("\n[bold]Use arrow keys to navigate, SPACE to select/deselect, ENTER when done[/bold]\n")

    selected = questionary.checkbox(
        f"Select {category} for hashcat:",
        choices=choices,
    ).ask()

    print(f"\nRaw return value: {repr(selected)}")
    print(f"Type: {type(selected)}")
    print(f"Is None: {selected is None}")
    print(f"Is empty list: {selected == []}")
    print(f"Bool value: {bool(selected)}")

    if selected is None:
        print("\n❌ Selection was cancelled (Ctrl+C)")
        result = []
    elif not selected:
        print("\n⚠️  Nothing was selected (empty list)")
        result = []
    else:
        print(f"\n✅ Selected: {selected}")
        result = selected

    print(f"\nFinal result: {result}")
    return result

if __name__ == "__main__":
    test_pick_assets()

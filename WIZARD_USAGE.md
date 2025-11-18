# Vastcat Wizard Usage Guide

## How to Select Items in the Wizard

When you see prompts like this:

```
Available wordlists:
Use arrow keys to navigate, SPACE to select/deselect, ENTER when done

Select wordlists for hashcat:
  ○ rockyou: Classic rockyou list in gzip format
  ○ common_10k: 10,000 most common passwords
  ○ seclists_passwords: Full SecLists repo (large download)
```

### ✅ Correct Usage:

1. **Use ↑/↓ arrow keys** to move between options
2. **Press SPACE** to toggle selection (○ becomes ●)
3. **Press ENTER** when done selecting

### ❌ Common Mistakes:

- **Just pressing ENTER** without using SPACE = Nothing selected!
- The cursor position doesn't select automatically
- You MUST press SPACE to toggle the checkboxes

### Example Session:

```
1. Start at first option (rockyou)
2. Press SPACE → rockyou is now selected (●)
3. Press ↓ to move to common_10k
4. Press SPACE → common_10k is now selected (●)
5. Press ENTER → Both items are confirmed
```

## What You'll See After Selection:

If successful:
```
✓ Selected 2 wordlists: rockyou, common_10k
```

If nothing selected:
```
😺 No wordlists selected. Hashcat requires at least one wordlist.
😺 Remember: Use SPACE to toggle selection, then ENTER to confirm.
? Try again? (Y/n)
```

## Quick Test

Run the wizard:
```bash
vastcat wizard
```

When prompted for wordlists:
1. Press SPACE (you should see ● appear)
2. Press ENTER
3. You should see "✓ Selected 1 wordlists: ..."

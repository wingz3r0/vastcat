# Vastcat Wizard Usage Guide

## Wizard Navigation

The wizard guides you through **7 steps** to configure your hashcat job. Each step is numbered and shows your progress (e.g., "Step 2/7: Select Rules").

### Going Back to Previous Steps

You can **go back to any previous step** if you need to change something:

- **Text inputs**: Type `back` to return to the previous step
- **Select menus**: Choose `← Go back` from the menu options
- **Step 1**: Cannot go back (it's the first step)

This allows you to correct mistakes without restarting the entire wizard!

## How to Select Items in the Wizard

The wizard uses a **numbered menu** for easy, reliable selection. No arrow keys needed!

### Example Display:

```
Available wordlists:
  1. rockyou: Classic rockyou list in gzip format
  2. common_10k: 10,000 most common passwords
  3. seclists_passwords: Full SecLists repo (large download)

Enter numbers to select wordlists:
Examples: '1' (single), '1,2' (multiple), '1-3' (range), 'all' (select all)

Select wordlists: all
```

## Selection Formats

### Single Item
```
Select wordlists: 1
```
Selects only item #1 (rockyou)

### Multiple Items (Comma-Separated)
```
Select wordlists: 1,2
```
Selects items #1 and #2 (rockyou, common_10k)

### Range
```
Select wordlists: 1-3
```
Selects items #1 through #3 (all items)

### Mixed (Single + Range)
```
Select wordlists: 1,3
```
Selects items #1 and #3 (rockyou, seclists_passwords)

### Select All
```
Select wordlists: all
```
Selects all available items

### Spaces Are OK
```
Select wordlists: 1, 2, 3
Select wordlists: 1 - 3
```
Both work fine!

### Go Back
```
Select wordlists: back
```
Returns to the previous step (if not on Step 1)

## What You'll See After Selection

### Successful Selection:
```
✓ Selected 2 wordlists: rockyou, common_10k
```

### Empty Selection:
```
😺 No wordlists selected. Hashcat requires at least one wordlist.
? Try again? (Y/n)
```

### Invalid Input:
```
Invalid selection: Number 5 is out of range (valid: 1-3)
```

## Quick Examples

### Select All Wordlists (Default for wordlists)
```
Select wordlists: all
```
or just press ENTER (default is "all" for wordlists)

### Select Multiple Rules
```
Select rules: 1,2
```
Selects first two rules

### Select Range of Items
```
Select wordlists: 1-2
```
Selects first two wordlists

## Review & Edit Your Configuration

After entering all parameters, you'll see a summary:

```
═══════════════════════════ 😺  Configuration Summary ════════════════════════════
1. Hash file: /workspace/hash.txt
2. Hash mode: 5600
3. Attack mode: Straight (mode 0)
4. Wordlists: rockyou.txt
5. Rules: dive.rule
6. Discord webhook: Not configured
7. Deployment: Local

? What would you like to do?
  Proceed with these settings
  Edit a parameter
  Start over
  Cancel
```

### Editing Parameters

If you made a mistake or want to change something:

1. Select **"Edit a parameter"**
2. Choose which parameter to edit (1-7)
3. Re-enter the value
4. Review the updated summary
5. Repeat until satisfied

### Options Available

- **Proceed with these settings** - Continue to execution
- **Edit a parameter** - Change one or more settings
- **Start over** - Go through the wizard from the beginning
- **Cancel** - Exit without running hashcat

## Two Ways to Make Changes

Vastcat provides **two convenient ways** to fix mistakes:

### 1. Go Back During Wizard (Step-by-Step Navigation)

While progressing through the 7 steps, you can **immediately go back** to the previous step:

```
Step 3/7: Configure Notifications
Discord webhook (optional, or 'back' to go back): back

[Returns to Step 2/7: Select Rules]
```

**Use this when**: You realize a mistake right away and want to fix it immediately.

### 2. Review & Edit After Completion (Summary Screen)

After completing all 7 steps, you can **review everything** and edit any parameter:

```
Configuration Summary
1. Hash file: /home/user/hash.txt
2. Hash mode: 5600
...

What would you like to do?
> Edit a parameter

Which parameter would you like to edit?
> 2. Hash mode
```

**Use this when**: You want to see the complete configuration before making changes, or need to edit multiple parameters.

### Example Workflow

1. **Step 1-7**: Go through wizard, use `back` if you catch mistakes early
2. **Review Screen**: Check the complete configuration summary
3. **Edit if needed**: Use "Edit a parameter" for any final adjustments
4. **Proceed**: Run hashcat with your perfect configuration!

## Why Numbered Menu?

The numbered menu is more reliable than arrow-key checkboxes because:
- ✅ Works in any terminal (SSH, Docker, tmux, screen)
- ✅ Works over slow connections
- ✅ No terminal escape sequence issues
- ✅ Faster for users who know what they want
- ✅ Copy-paste friendly for automation

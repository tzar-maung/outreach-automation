# Google Sheets Integration Guide

## Quick Setup (5 minutes)

### Step 1: Create Your Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet
3. Add these columns in Row 1:

| username | url | niche | status |
|----------|-----|-------|--------|
| fitnessgirl1 | | fitness | |
| beautybabe2 | https://instagram.com/beautybabe2 | beauty | |
| fashionista3 | | fashion | |

**Note:** You only need `username` OR `url`, not both!

### Step 2: Make Sheet Public

1. Click the **Share** button (top right)
2. Under "General access", click "Restricted"
3. Change to **"Anyone with the link"**
4. Set role to **"Viewer"**
5. Click "Copy link"

### Step 3: Run the Bot

```cmd
python -m outreach_bot.main --sheet "YOUR_SHEET_URL" --dm --max-targets 10
```

---

## Column Reference

| Column | Required | Description |
|--------|----------|-------------|
| `username` | Yes* | Instagram username (without @) |
| `url` | Yes* | Full Instagram URL |
| `niche` | No | Content niche (fitness, beauty, etc.) |
| `status` | No | Leave blank - bot skips "sent" or "done" |
| `notes` | No | Your personal notes |
| `followers` | No | Follower count (optional) |

*You need either `username` OR `url`, not both.

---

## Example Sheet

```
username        | url                                    | niche    | status
----------------|----------------------------------------|----------|--------
fitnessgirl1    |                                        | fitness  |
beautybabe2     | https://instagram.com/beautybabe2     | beauty   |
fashionista3    |                                        | fashion  |
traveler4       |                                        | travel   | sent
skipper5        |                                        | fitness  | skip
```

The bot will:
- ✓ Process: fitnessgirl1, beautybabe2, fashionista3
- ✗ Skip: traveler4 (status=sent), skipper5 (status=skip)

---

## Command Examples

### View profiles only (safe test)
```cmd
python -m outreach_bot.main --sheet "YOUR_URL" --max-targets 5
```

### Send DMs (default 10/day limit)
```cmd
python -m outreach_bot.main --sheet "YOUR_URL" --dm --max-targets 10
```

### Send DMs with custom limit (20/day)
```cmd
python -m outreach_bot.main --sheet "YOUR_URL" --dm --daily-dms 20 --max-targets 20
```

### Follow + DM
```cmd
python -m outreach_bot.main --sheet "YOUR_URL" --dm --follow --max-targets 10
```

### Use specific message category
```cmd
python -m outreach_bot.main --sheet "YOUR_URL" --dm --category collaboration --niche fitness
```

---

## Daily DM Limits

| --daily-dms | Risk Level | Recommended For |
|-------------|------------|-----------------|
| 10 (default)| 🟢 Safe | New accounts, testing |
| 15-20 | 🟡 Medium | Accounts 3+ months old |
| 25-30 | 🟠 Risky | Aged accounts with history |
| 50+ | 🔴 High | Will likely get banned |

**Recommendation:** Start with 10-15 DMs for the first week, then gradually increase.

---

## Tips for Best Results

1. **Quality over quantity** - Curate your targets carefully
2. **Match the niche** - DM fitness influencers about fitness
3. **Space it out** - Don't send all DMs at once
4. **Vary your times** - Run at different times each day
5. **Watch for warnings** - Stop immediately if you see "Action Blocked"

---

## Troubleshooting

### "ERROR: Could not access Google Sheet"
- Make sure sheet is set to "Anyone with the link can view"
- Check that the URL is correct

### "0 targets loaded"
- Check column names (must be: username, url, niche, status)
- Make sure there's data below the header row
- Check that status column isn't all "sent" or "done"

### DMs not sending
- Check you're logged into Instagram
- Try running without --dm first to test viewing
- Check for "Action Blocked" messages

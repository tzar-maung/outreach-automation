# Quick Start Cheat Sheet
## Instagram DM Bot - One Page Guide

---

## FIRST TIME SETUP

```
1. Install Python from: python.org/downloads
   ⚠️ Check "Add Python to PATH" during install!

2. Open Command Prompt (Windows + R → type "cmd" → Enter)

3. Run: pip install selenium webdriver-manager

4. Extract outreach_bot_production.zip to Desktop
```

---

## PREPARE YOUR TARGET LIST

```
1. Create Google Sheet with column: username
2. Add Instagram usernames (without @)
3. Click Share → "Anyone with the link" → Copy link
```

---

## DAILY USAGE

```
1. CLOSE ALL CHROME WINDOWS ⚠️

2. Open Command Prompt

3. Type: cd Desktop
   Press Enter

4. Type your command (see below)
   Press Enter

5. If login appears → Login → Press Enter in Command Prompt

6. Wait for "SESSION COMPLETE"
```

---

## COMMANDS (Copy & Paste)

**Thai DMs (10 people):**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --dm --max-targets 10
```

**Japanese DMs (10 people):**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --dm --category japanese --max-targets 10
```

**More DMs (20 people):**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --dm --daily-dms 20 --max-targets 20
```

⚠️ Replace YOUR_LINK with your Google Sheets link!

---

## SAFETY LIMITS

| Account Age | Max DMs/Day |
|-------------|-------------|
| New (< 1 month) | 5-10 |
| Normal | 10-15 |
| Old (1+ year) | 20-30 |

**If you see "Action Blocked" → STOP and wait 24 hours!**

---

## COMMON PROBLEMS

| Problem | Solution |
|---------|----------|
| "Python not recognized" | Reinstall Python, check "Add to PATH" |
| Chrome won't open | Close ALL Chrome windows first |
| DM failed | User has DMs disabled, try another |

---

**Need more help? See USER_GUIDE.md**

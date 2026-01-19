# Instagram DM Bot - User Guide
### Simple Instructions for Everyone

---

## 📋 What This Bot Does

This bot automatically sends DM messages to Instagram users from your list.

**Features:**
- ✅ Sends personalized DMs in Thai or Japanese
- ✅ Reads target list from Google Sheets
- ✅ Remembers who you already messaged (no duplicates)
- ✅ Acts like a human (safe from bans)

---

## 🔧 One-Time Setup (10 minutes)

### Step 1: Install Python

1. Go to: https://www.python.org/downloads/
2. Click the big yellow **"Download Python"** button
3. Run the installer
4. **⚠️ IMPORTANT:** Check the box that says **"Add Python to PATH"**
5. Click "Install Now"

### Step 2: Install Required Programs

1. Open **Command Prompt**:
   - Press `Windows + R`
   - Type `cmd`
   - Press Enter

2. Copy and paste this command, then press Enter:
   ```
   pip install selenium webdriver-manager
   ```

3. Wait until it finishes (about 1 minute)

### Step 3: Download the Bot

1. Extract the `outreach_bot_production.zip` file to your Desktop
2. You should see a folder called `outreach_bot_production` on your Desktop

### Step 4: Prepare Google Sheets

1. Open Google Sheets: https://sheets.google.com
2. Create a new spreadsheet
3. In the first row, type these headers:

   | A | B | C |
   |---|---|---|
   | username | status | notes |

4. Add Instagram usernames (without @) in column A:

   | username | status | notes |
   |----------|--------|-------|
   | example_user1 | | |
   | example_user2 | | |

5. **Make the sheet public:**
   - Click **Share** (top right)
   - Click **"Change to anyone with the link"**
   - Make sure it says **"Viewer"**
   - Click **Copy link**

---

## 🚀 How to Use (Daily)

### Step 1: Close Chrome

**⚠️ IMPORTANT:** Close ALL Chrome browser windows before running the bot!

### Step 2: Open Command Prompt

1. Press `Windows + R`
2. Type `cmd`
3. Press Enter

### Step 3: Go to Desktop

Type this and press Enter:
```
cd Desktop
```

### Step 4: Run the Bot

Copy one of these commands, paste it, and press Enter:

**For Thai messages:**
```
python -m outreach_bot.main --sheet "YOUR_GOOGLE_SHEET_LINK" --dm --max-targets 10
```

**For Japanese messages:**
```
python -m outreach_bot.main --sheet "YOUR_GOOGLE_SHEET_LINK" --dm --category japanese --max-targets 10
```

**⚠️ Replace `YOUR_GOOGLE_SHEET_LINK` with your actual Google Sheets link!**

### Step 5: First Time Login

The first time you run the bot:
1. A Chrome window will open
2. You'll see Instagram login page
3. Log in to your Instagram account
4. Press Enter in the Command Prompt window
5. The bot will start working!

---

## 📊 Understanding the Output

When the bot runs, you'll see:

```
[OK] Loaded 10 targets from Google Sheet
[1/10] @username1
Browsing profile...
Sending DM...
[OK] DM sent!
Waiting 65s before next...
```

**What the messages mean:**

| Message | Meaning |
|---------|---------|
| `[OK] Loaded X targets` | Successfully read your Google Sheet |
| `Browsing profile...` | Looking at the profile (like a human) |
| `[OK] DM sent!` | Message sent successfully! |
| `Already DM'd - skipping` | You messaged this person before |
| `Waiting Xs...` | Waiting before next message (safety) |

---

## ⚙️ Options Explained

| Option | What it does | Example |
|--------|--------------|---------|
| `--sheet "URL"` | Your Google Sheet link | Required |
| `--dm` | Enable sending DMs | Required for DMs |
| `--max-targets 10` | How many people to message | Change number |
| `--category japanese` | Use Japanese messages | Optional |
| `--daily-dms 20` | Increase daily limit | Optional |

---

## 📝 Quick Reference Commands

**Send 5 Thai DMs:**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --dm --max-targets 5
```

**Send 10 Japanese DMs:**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --dm --category japanese --max-targets 10
```

**Send 20 DMs (increased limit):**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --dm --daily-dms 20 --max-targets 20
```

**Just view profiles (no DM):**
```
python -m outreach_bot.main --sheet "YOUR_LINK" --max-targets 10
```

---

## ⚠️ Safety Rules

To avoid getting your Instagram account banned:

| Rule | Recommendation |
|------|----------------|
| Daily DMs | Start with 10/day, max 20-30/day |
| Wait between runs | Wait 2-3 hours between sessions |
| If you see "Action Blocked" | STOP immediately, wait 24 hours |
| Account age | New accounts: only 5-10 DMs/day |

---

## 🔄 Updating Your Target List

1. Open your Google Sheet
2. Add new usernames to column A
3. To skip someone, type `skip` in their status column:

   | username | status | notes |
   |----------|--------|-------|
   | user1 | sent | messaged yesterday |
   | user2 | skip | not interested |
   | user3 | | will message |

4. Run the bot again - it will skip "sent" and "skip" users

---

## ❓ Troubleshooting

### "Python is not recognized"
- Reinstall Python
- Make sure to check "Add Python to PATH"

### "Chrome won't open"
- Close ALL Chrome windows first
- Try restarting your computer

### "Not logged in" keeps appearing
- Log in to Instagram in the bot's Chrome window
- Press Enter in Command Prompt after logging in

### "DM failed"
- The user might have DMs disabled
- Try a different user
- Wait a few hours and try again

### Bot is very slow
- This is normal! It's being slow on purpose to look human
- Each DM takes about 1-2 minutes

---

## 📞 Need Help?

If you have problems:
1. Take a screenshot of the error message
2. Note what command you used
3. Contact the technical team

---

## 🎯 Example: Complete Session

```
1. Close all Chrome windows

2. Open Command Prompt (Windows + R, type "cmd")

3. Type: cd Desktop
   Press Enter

4. Type: python -m outreach_bot.main --sheet "https://docs.google.com/spreadsheets/d/xxxxx/edit" --dm --max-targets 5
   Press Enter

5. Wait for Chrome to open

6. If asked to login, login to Instagram, then press Enter in Command Prompt

7. Watch the bot work! Don't touch the Chrome window.

8. When finished, you'll see "SESSION COMPLETE"

9. Done! Check your Instagram to see sent messages.
```

---

**Happy Outreaching! 🚀**

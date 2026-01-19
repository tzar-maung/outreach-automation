#  Outreach Bot - Production Ready

A complete, battle-tested browser automation system built for reliability.

---

## Production Features

| Feature | Status | Description |
|---------|--------|-------------|
| Error Screenshots | ✅ | Auto-capture on failures |
| CAPTCHA Detection | ✅ | Detect & pause for manual solve |
| Session Recovery | ✅ | Resume after crash |
| Robust Selectors | ✅ | Multiple fallbacks per element |
| Retry Logic | ✅ | Exponential backoff |
| Rate Limiting | ✅ | Database-backed tracking |
| Proxy Rotation | ✅ | IP rotation with health checks |
| Account Protection | ✅ | Warmup, trust score, auto-pause |

---

##  Quick Start 

### Step 1: Rename & Install

```bash
# Rename folder
mv outreach_bot_production outreach_bot

# Install dependencies
pip install selenium webdriver-manager requests
```

### Step 2: Run Tests

```bash
# Run component tests (no browser)
python tests/test_suite.py

# Run full test with browser
python -m outreach_bot.main --test
```

### Step 3: Test Selectors (Important!)

```bash
# Test Instagram selectors
python -m outreach_bot.main --test-selectors

# Test TikTok selectors  
python -m outreach_bot.main --test-selectors --platform tiktok
```

### Step 4: First Run

```bash
# Run on Instagram
python -m outreach_bot.main --platform instagram
```

---

## 📋 Step-by-Step Production Guide

### Phase 1: Validate Components

```bash
# 1. Run unit tests
python tests/test_suite.py

# Expected output:
#  imports
#  database
#  rate_limiter
#  checkpoint
#  retry_logic
#  proxy_manager
#  selectors
```

### Phase 2: Test Browser & Login

```bash
# 2. Run browser test
python -m outreach_bot.main --test

# This will:
# - Start Chrome
# - Test all components
# - Check if logged into Instagram
# - Take test screenshots
```

### Phase 3: Validate Selectors

```bash
# 3. Test selectors on real pages
python -m outreach_bot.main --test-selectors

# This will:
# - Navigate to Instagram
# - Test each selector
# - Report which ones work/broken
```

**If selectors are broken:**
1. Open `core/selectors.py`
2. Find the broken selector
3. Use browser DevTools to find new selector
4. Update primary or add fallback

### Phase 4: Configure Targets

Edit `data/targets.csv`:
```csv
url,platform,username,notes
https://www.instagram.com/user1,instagram,user1,Test
https://www.instagram.com/user2,instagram,user2,Test
```

### Phase 5: Test Run (Small Batch)

```bash
# 4. Run with limited targets
python -m outreach_bot.main --platform instagram --max-targets 5
```

### Phase 6: Production Run

```bash
# 5. Full run
python -m outreach_bot.main --platform instagram

# With proxy (recommended)
python -m outreach_bot.main --platform instagram --proxy
```

---

## 🔧 How Each Feature Works

### 1. Error Screenshots

**Location:** `debug/screenshots/`, `debug/error_logs/`

When an error occurs:
1. Screenshot is saved automatically
2. Page HTML is saved
3. Error details logged to JSON

```bash
# View debug files
ls debug/screenshots/
ls debug/error_logs/
```

### 2. CAPTCHA Detection

The bot automatically detects:
- reCAPTCHA
- hCaptcha
- Instagram "Action Blocked"
- Instagram "Verify Identity"
- TikTok slider captcha

When detected:
1. Screenshot is taken
2. Alert beep sounds
3. Bot pauses for manual solve
4. Press ENTER when done

### 3. Session Recovery

Progress is saved automatically. If the bot crashes:

```bash
# List available sessions
python -m outreach_bot.main --list-sessions

# Resume last session
python -m outreach_bot.main --resume

# Resume specific session
python -m outreach_bot.main --resume session_20250117_143022
```

**Checkpoint files:** `checkpoints/*.json`

### 4. Robust Selectors

Each element has multiple selectors:

```python
"follow_button": Selector(
    primary="//header//button[.//div[contains(text(),'Follow')]]",
    fallbacks=[
        "//button[.//text()='Follow']",
        "header button:not([class*='following'])",
    ],
)
```

**To update broken selectors:**
1. Open Instagram in Chrome
2. Right-click element → Inspect
3. Copy selector or XPath
4. Update `core/selectors.py`

### 5. Retry Logic

Automatic retry with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 4 | 8 seconds |

Rate limit errors get longer delays (10x).

### 6. Rate Limiting

**Default limits (Safe Mode):**
| Action | Daily | Hourly |
|--------|-------|--------|
| Views | 150 | - |
| Follows | 15 | 3 |
| Likes | 40 | 10 |
| DMs | 10 | 2 |

**Aggressive Mode (⚠️ Risky):**
| Action | Daily | Hourly |
|--------|-------|--------|
| Views | 400 | - |
| Follows | 40 | 8 |
| Likes | 100 | 20 |
| DMs | 50 | 5 |

```bash
# Enable aggressive mode
python -m outreach_bot.main --platform instagram --aggressive
```

---

## 📁 Directory Structure

```
outreach_bot/
├── main.py                    # CLI entry point
├── config.py                  # All configuration
│
├── core/
│   ├── browser.py             # Chrome setup
│   ├── database.py            # SQLite storage
│   ├── rate_limiter.py        # Action limits
│   ├── account_protector.py   # Ban protection
│   │
│   ├── debug_helper.py        # Screenshots & logging
│   ├── captcha_handler.py     # CAPTCHA detection
│   ├── checkpoint.py          # Session recovery
│   ├── retry_logic.py         # Retry with backoff
│   ├── selectors.py           # CSS/XPath selectors
│   │
│   ├── proxy_manager.py       # IP rotation
│   ├── scheduler.py           # Timed execution
│   ├── human_behavior.py      # Anti-detection
│   │
│   └── platform/
│       ├── instagram.py       # Instagram adapter
│       └── tiktok.py          # TikTok adapter
│
├── tests/
│   └── test_suite.py          # Unit tests
│
├── data/
│   ├── targets.csv            # Target URLs
│   └── proxies.txt            # Proxy list
│
├── checkpoints/               # Session recovery
├── debug/                     # Screenshots & logs
├── logs/                      # Application logs
└── chrome_profile/            # Persistent login
```

---

##  CLI Reference

```bash
# Help
python -m outreach_bot.main --help

# Tests
python -m outreach_bot.main --test              # Component test
python -m outreach_bot.main --test-selectors    # Selector test

# Sessions
python -m outreach_bot.main --list-sessions     # List sessions
python -m outreach_bot.main --resume            # Resume session

# Run
python -m outreach_bot.main --platform instagram
python -m outreach_bot.main --platform tiktok
python -m outreach_bot.main -p instagram --proxy
python -m outreach_bot.main -p instagram --aggressive
python -m outreach_bot.main -p instagram --max-targets 20
python -m outreach_bot.main -p instagram --headless
```

---

## Troubleshooting

### "Could not find element: follow_button"

Selectors need updating:
```bash
python -m outreach_bot.main --test-selectors
```
Then update `core/selectors.py`.

### "Not logged in"

1. Run without headless mode
2. Log in manually in browser
3. Press ENTER
4. Session saved for future runs

### "Action Blocked"

Instagram rate limited you:
1. Bot auto-pauses
2. Wait 24-48 hours
3. Reduce limits in `config.py`

### Browser crashes

Session auto-saved:
```bash
python -m outreach_bot.main --resume
```

### Screenshots not saving

Check debug directory exists:
```bash
mkdir -p debug/screenshots debug/error_logs debug/html
```

---

## 📊 Monitoring

### View Logs

```bash
# Real-time logs
tail -f logs/outreach_bot_*.log
```

### View Progress

```bash
# List sessions
python -m outreach_bot.main --list-sessions
```

### View Debug Files

```bash
# Screenshots
ls -la debug/screenshots/

# Error reports
cat debug/error_logs/*.json
```

---

## Production Checklist

Before going live:

- [ ] `python tests/test_suite.py` passes
- [ ] `python -m outreach_bot.main --test` passes
- [ ] `python -m outreach_bot.main --test-selectors` shows all ✅
- [ ] Logged into Instagram/TikTok (manual)
- [ ] `data/targets.csv` configured
- [ ] `data/proxies.txt` configured (if using proxies)
- [ ] Tested with `--max-targets 5` first
- [ ] Using SAFE mode (not aggressive) initially

---

##  Safety Tips

1. **Start with Safe Mode** - Use aggressive only with mature accounts
2. **Use Proxies** - 1 account per IP maximum
3. **Test First** - Always run `--test-selectors` before full runs
4. **Monitor Warnings** - Stop immediately if you see "Action Blocked"
5. **Backup Sessions** - Checkpoints in `checkpoints/` folder
6. **Check Screenshots** - Debug issues with `debug/screenshots/`

---

##  Recommended Workflow

### Daily Operation

```bash
# Morning: Check selector health
python -m outreach_bot.main --test-selectors

# If all green: Run bot
python -m outreach_bot.main --platform instagram

# Evening: Check progress
python -m outreach_bot.main --list-sessions
```

### Weekly Maintenance

1. Update selectors if Instagram changed
2. Review error screenshots
3. Clean old checkpoints
4. Update target list

---

##  You're Ready!

The bot is production ready. Follow the checklist above and start with small batches.

Good luck! 🚀

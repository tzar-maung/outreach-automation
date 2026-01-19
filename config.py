"""
Outreach Bot Configuration - With Account Protection

⚠️ IMPORTANT: Higher limits = Higher ban risk!
Use aggressive mode at your own risk.
"""
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).parent

# --------------------------------------------------
# Directory Paths
# --------------------------------------------------
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CHROME_PROFILE_DIR = BASE_DIR / "chrome_profile"
DATABASE_PATH = DATA_DIR / "outreach.db"
PROXY_FILE = DATA_DIR / "proxies.txt"
TARGETS_FILE = DATA_DIR / "targets.csv"
SCHEDULER_STATE_FILE = DATA_DIR / "scheduler_state.json"

# --------------------------------------------------
# Browser Settings
# --------------------------------------------------
BROWSER = {
    "headless": False,
    "window_width": 1280,
    "window_height": 900,
    "page_load_timeout": 30,
    "implicit_wait": 10,
    "user_data_dir": str(CHROME_PROFILE_DIR),
    "profile_name": "Default",
    "randomize_fingerprint": True,  # NEW: Randomize user agent, viewport
}

# --------------------------------------------------
# Human Behavior Settings (More Conservative)
# --------------------------------------------------
BEHAVIOR = {
    "min_action_delay": 2.0,     # Increased from 1.0
    "max_action_delay": 5.0,     # Increased from 3.0
    "min_typing_delay": 0.08,    # Slightly slower typing
    "max_typing_delay": 0.20,
    "scroll_pause": 1.5,
    "browse_duration": 8.0,      # Longer natural browsing
    "random_pause_chance": 0.15, # 15% chance of random long pause
    "random_pause_duration": (30, 180),  # 30s - 3min random pauses
}

# --------------------------------------------------
# Account Protection Settings
# --------------------------------------------------
PROTECTION = {
    "enabled": True,
    "aggressive_mode": False,    # Set True for 30-50 DMs (risky!)
    "enforce_warmup": True,      # Require warmup period
    "enforce_human_hours": False, # Disabled - set True to only act 7AM-11PM
    "auto_pause_on_warning": True,
    "trust_score_threshold": 30, # Pause if trust drops below this
}

# --------------------------------------------------
# Rate Limits - SAFE MODE (Recommended)
# --------------------------------------------------
RATE_LIMITS_SAFE = {
    "instagram": {
        # Daily limits (conservative)
        "daily_views": 150,
        "daily_follows": 15,
        "daily_unfollows": 10,
        "daily_likes": 40,
        "daily_comments": 8,
        "daily_dms": 10,
        # Hourly limits
        "hourly_follows": 3,
        "hourly_likes": 10,
        "hourly_dms": 2,
        # Cooldowns (seconds) - Longer for safety
        "cooldown_between_actions": 5.0,
        "cooldown_between_profiles": 15.0,
        "cooldown_after_follow": 45.0,
        "cooldown_after_like": 20.0,
        "cooldown_after_dm": 120.0,  # 2 minutes between DMs
    },
    "tiktok": {
        "daily_views": 100,
        "daily_follows": 10,
        "daily_unfollows": 8,
        "daily_likes": 30,
        "daily_comments": 5,
        "daily_dms": 5,
        "hourly_follows": 2,
        "hourly_likes": 8,
        "hourly_dms": 1,
        "cooldown_between_actions": 6.0,
        "cooldown_between_profiles": 20.0,
        "cooldown_after_follow": 60.0,
        "cooldown_after_dm": 180.0,
    },
}

# --------------------------------------------------
# Rate Limits - AGGRESSIVE MODE (Your Requested Limits)
# ⚠️ WARNING: High ban risk! Use with proxies + mature accounts only!
# --------------------------------------------------
RATE_LIMITS_AGGRESSIVE = {
    "instagram": {
        # Daily limits (aggressive - your request)
        "daily_views": 400,
        "daily_follows": 40,
        "daily_unfollows": 30,
        "daily_likes": 100,
        "daily_comments": 20,
        "daily_dms": 50,         # ⚠️ Your requested 30-50
        # Hourly limits (still enforced for burst protection)
        "hourly_follows": 8,
        "hourly_likes": 20,
        "hourly_dms": 5,         # Max 5 DMs per hour
        # Cooldowns (shorter but still present)
        "cooldown_between_actions": 3.0,
        "cooldown_between_profiles": 8.0,
        "cooldown_after_follow": 30.0,
        "cooldown_after_like": 10.0,
        "cooldown_after_dm": 60.0,  # 1 minute between DMs (minimum safe)
    },
    "tiktok": {
        "daily_views": 250,
        "daily_follows": 25,
        "daily_unfollows": 20,
        "daily_likes": 70,
        "daily_comments": 15,
        "daily_dms": 25,
        "hourly_follows": 5,
        "hourly_likes": 15,
        "hourly_dms": 3,
        "cooldown_between_actions": 4.0,
        "cooldown_between_profiles": 12.0,
        "cooldown_after_follow": 40.0,
        "cooldown_after_dm": 90.0,
    },
}

# Active rate limits (changes based on aggressive_mode)
def get_rate_limits() -> Dict:
    """Get current rate limits based on protection mode."""
    if PROTECTION["aggressive_mode"]:
        return RATE_LIMITS_AGGRESSIVE
    return RATE_LIMITS_SAFE

RATE_LIMITS = get_rate_limits()

# --------------------------------------------------
# Session Limits (per run)
# --------------------------------------------------
SESSION_SAFE = {
    "max_targets_per_session": 20,
    "max_follows_per_session": 8,
    "max_likes_per_session": 15,
    "max_dms_per_session": 5,
    "max_errors_before_stop": 3,
    "max_warnings_before_stop": 1,  # Stop on first warning
}

SESSION_AGGRESSIVE = {
    "max_targets_per_session": 50,
    "max_follows_per_session": 20,
    "max_likes_per_session": 40,
    "max_dms_per_session": 20,      # Your request for more DMs
    "max_errors_before_stop": 5,
    "max_warnings_before_stop": 2,
}

def get_session_limits() -> Dict:
    """Get current session limits based on protection mode."""
    if PROTECTION["aggressive_mode"]:
        return SESSION_AGGRESSIVE
    return SESSION_SAFE

SESSION = get_session_limits()

# --------------------------------------------------
# Proxy Settings (IMPORTANT for aggressive mode)
# --------------------------------------------------
PROXY = {
    "enabled": False,               # Enable for aggressive mode!
    "rotation_mode": "round_robin",
    "health_check_timeout": 10,
    "max_failures_before_quarantine": 3,
    "quarantine_duration_minutes": 30,
    "required_for_aggressive": True, # Force proxy in aggressive mode
}

# --------------------------------------------------
# Scheduler Settings
# --------------------------------------------------
SCHEDULER = {
    "enabled": False,
    "variation_minutes": 45,        # More variation for safety
    "active_hours_start": 8,        # Start at 8 AM
    "active_hours_end": 22,         # End at 10 PM
    "days_off": [],                 # e.g., ["sunday"] for rest days
}

DEFAULT_SCHEDULE = [
    {"time": "09:30", "platform": "instagram", "days": ["daily"]},
    {"time": "14:00", "platform": "instagram", "days": ["monday", "wednesday", "friday"]},
    {"time": "19:00", "platform": "tiktok", "days": ["daily"]},
]

# --------------------------------------------------
# DM Outreach Settings
# --------------------------------------------------
DM_OUTREACH = {
    "enabled": False,
    "mode": "mock",                 # Start with mock, then switch to real
    "skip_if_already_sent": True,
    "personalize_messages": True,
    "min_delay_between_dms": 60,    # Minimum 60 seconds
    "max_dms_per_hour": 5,          # Hard limit
}

# --------------------------------------------------
# Custom DM Limits (Overrides RATE_LIMITS if set)
# --------------------------------------------------
# Set these to customize your DM limits without enabling aggressive mode
CUSTOM_DM_LIMITS = {
    "enabled": False,               # Set True to use custom limits
    "daily_dms": 20,                # Your custom daily DM limit
    "hourly_dms": 4,                # Your custom hourly limit
    "cooldown_after_dm": 90,        # Seconds between DMs
}

# --------------------------------------------------
# Google Sheets Integration
# --------------------------------------------------
GOOGLE_SHEETS = {
    "sheet_url": "",                # Paste your Google Sheet URL here
    "credentials_file": "",         # Optional: path to service account JSON
    "sheet_name": "Sheet1",         # Tab name
}

# --------------------------------------------------
# Warning Detection (Keywords that indicate problems)
# --------------------------------------------------
WARNING_INDICATORS = {
    "action_blocked": [
        "action blocked",
        "try again later",
        "we limit how often",
        "temporarily blocked",
    ],
    "rate_limit": [
        "please wait",
        "slow down",
        "too many requests",
    ],
    "suspicious": [
        "suspicious activity",
        "confirm your identity",
        "verify your account",
        "unusual login",
    ],
    "temporary_ban": [
        "temporarily banned",
        "account suspended",
        "disabled your account",
    ],
}

# --------------------------------------------------
# Logging Settings
# --------------------------------------------------
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(message)s",
    "file_logging": True,
    "console_logging": True,
    "log_actions": True,            # Log every action
}

# --------------------------------------------------
# Platform URLs
# --------------------------------------------------
PLATFORMS = {
    "instagram": {
        "base_url": "https://www.instagram.com",
        "login_url": "https://www.instagram.com/accounts/login/",
        "dm_url": "https://www.instagram.com/direct/inbox/",
    },
    "tiktok": {
        "base_url": "https://www.tiktok.com",
        "login_url": "https://www.tiktok.com/login",
    },
}


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def enable_aggressive_mode():
    """Enable aggressive mode (higher limits, higher risk)."""
    global RATE_LIMITS, SESSION
    PROTECTION["aggressive_mode"] = True
    RATE_LIMITS = RATE_LIMITS_AGGRESSIVE
    SESSION = SESSION_AGGRESSIVE
    print("⚠️ AGGRESSIVE MODE ENABLED - Use at your own risk!")


def disable_aggressive_mode():
    """Disable aggressive mode (back to safe limits)."""
    global RATE_LIMITS, SESSION
    PROTECTION["aggressive_mode"] = False
    RATE_LIMITS = RATE_LIMITS_SAFE
    SESSION = SESSION_SAFE
    print("✅ Safe mode enabled")


def get_platform_limits(platform: str) -> Dict:
    """Get rate limits for a platform."""
    return RATE_LIMITS.get(platform, RATE_LIMITS.get("instagram"))


def get_platform_url(platform: str, url_type: str = "base_url") -> str:
    """Get a URL for a platform."""
    platform_config = PLATFORMS.get(platform, {})
    return platform_config.get(url_type, "")


def ensure_directories():
    """Create necessary directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def print_current_limits(platform: str = "instagram"):
    """Print current limits for a platform."""
    limits = get_platform_limits(platform)
    mode = "AGGRESSIVE ⚠️" if PROTECTION["aggressive_mode"] else "SAFE ✅"
    
    print(f"\n{'='*50}")
    print(f"Current Limits ({mode})")
    print(f"{'='*50}")
    print(f"Platform: {platform}")
    print(f"\nDaily Limits:")
    for key, value in limits.items():
        if key.startswith("daily_"):
            print(f"  {key}: {value}")
    print(f"\nHourly Limits:")
    for key, value in limits.items():
        if key.startswith("hourly_"):
            print(f"  {key}: {value}")
    print(f"\nCooldowns:")
    for key, value in limits.items():
        if key.startswith("cooldown_"):
            print(f"  {key}: {value}s")
    print(f"{'='*50}\n")


# Create directories on import
ensure_directories()


# --------------------------------------------------
# Safety Warning on Import
# --------------------------------------------------
if PROTECTION["aggressive_mode"]:
    print("\n" + "="*60)
    print("⚠️  WARNING: AGGRESSIVE MODE IS ENABLED")
    print("="*60)
    print("Higher limits = Higher ban risk!")
    print("Recommendations:")
    print("  1. Use with MATURE accounts (3+ months old)")
    print("  2. ALWAYS use proxies (1 account per IP)")
    print("  3. Monitor for warnings constantly")
    print("  4. Have backup accounts ready")
    print("="*60 + "\n")

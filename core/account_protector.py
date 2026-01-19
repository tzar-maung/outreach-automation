"""
Account Protection - Anti-Ban Measures

Comprehensive protection system to reduce ban risk:
- Warm-up periods for new accounts
- Action pattern randomization
- Activity windows (human hours)
- Behavior scoring
- Automatic pause on warnings
- Session fingerprint rotation

⚠️ IMPORTANT: No system can guarantee 100% protection.
Platforms constantly update their detection methods.

Usage:
    protector = AccountProtector(db, logger)
    if protector.is_safe_to_act("instagram", "dm"):
        # perform action
        protector.record_action("instagram", "dm")
"""
import random
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from outreach_bot.core.database import Database


class RiskLevel(Enum):
    """Risk levels for actions."""
    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"
    BLOCKED = "blocked"


@dataclass
class AccountProfile:
    """Profile for an account with warmup tracking."""
    username: str
    platform: str
    created_date: datetime
    warmup_complete: bool = False
    trust_score: float = 100.0  # 0-100
    total_actions: int = 0
    warnings_received: int = 0
    last_warning_date: Optional[datetime] = None
    is_paused: bool = False
    pause_until: Optional[datetime] = None


# --------------------------------------------------
# Realistic Limits Based on Account Age
# --------------------------------------------------

WARMUP_SCHEDULE = {
    # Days since account creation -> limits
    "instagram": {
        # Week 1: Very conservative (new account)
        0: {"daily_views": 30, "daily_follows": 0, "daily_likes": 5, "daily_dms": 0},
        1: {"daily_views": 40, "daily_follows": 2, "daily_likes": 8, "daily_dms": 0},
        2: {"daily_views": 50, "daily_follows": 3, "daily_likes": 10, "daily_dms": 0},
        3: {"daily_views": 60, "daily_follows": 4, "daily_likes": 12, "daily_dms": 2},
        4: {"daily_views": 70, "daily_follows": 5, "daily_likes": 15, "daily_dms": 3},
        5: {"daily_views": 80, "daily_follows": 6, "daily_likes": 18, "daily_dms": 4},
        6: {"daily_views": 90, "daily_follows": 7, "daily_likes": 20, "daily_dms": 5},
        
        # Week 2: Building trust
        7: {"daily_views": 100, "daily_follows": 8, "daily_likes": 25, "daily_dms": 6},
        14: {"daily_views": 150, "daily_follows": 12, "daily_likes": 35, "daily_dms": 8},
        
        # Week 3+: Established (still conservative)
        21: {"daily_views": 200, "daily_follows": 15, "daily_likes": 40, "daily_dms": 10},
        
        # Month 2+: Trusted account
        30: {"daily_views": 250, "daily_follows": 20, "daily_likes": 50, "daily_dms": 15},
        
        # Month 3+: Maximum safe limits
        60: {"daily_views": 300, "daily_follows": 25, "daily_likes": 60, "daily_dms": 20},
        
        # 6+ months: Mature account (your requested limits - still risky!)
        180: {"daily_views": 400, "daily_follows": 30, "daily_likes": 80, "daily_dms": 30},
    },
    "tiktok": {
        0: {"daily_views": 20, "daily_follows": 0, "daily_likes": 5, "daily_dms": 0},
        7: {"daily_views": 50, "daily_follows": 5, "daily_likes": 15, "daily_dms": 3},
        14: {"daily_views": 80, "daily_follows": 8, "daily_likes": 25, "daily_dms": 5},
        30: {"daily_views": 120, "daily_follows": 12, "daily_likes": 35, "daily_dms": 8},
        60: {"daily_views": 150, "daily_follows": 15, "daily_likes": 40, "daily_dms": 10},
    },
}

# Aggressive limits (USE AT YOUR OWN RISK)
AGGRESSIVE_LIMITS = {
    "instagram": {
        "daily_views": 500,
        "daily_follows": 40,
        "daily_likes": 100,
        "daily_dms": 50,  # Your requested 30-50
        "daily_comments": 20,
    },
    "tiktok": {
        "daily_views": 300,
        "daily_follows": 25,
        "daily_likes": 60,
        "daily_dms": 20,
    },
}


class AccountProtector:
    """
    Comprehensive account protection system.
    
    Features:
    - Warmup period management
    - Smart rate limiting based on account age
    - Activity pattern randomization
    - Human-hours enforcement
    - Warning detection and auto-pause
    - Trust score tracking
    """
    
    def __init__(self, database: Database, logger, 
                 aggressive_mode: bool = False):
        """
        Initialize account protector.
        
        Args:
            database: Database for tracking
            logger: Logger instance
            aggressive_mode: Use higher limits (risky!)
        """
        self.db = database
        self.logger = logger
        self.aggressive_mode = aggressive_mode
        
        # Account profiles (in-memory cache)
        self._profiles: Dict[str, AccountProfile] = {}
        
        # Session tracking
        self._session_actions: Dict[str, int] = {}
        self._last_action_times: Dict[str, datetime] = {}
        
        # Pattern randomization
        self._daily_patterns: Dict[str, List[Tuple[int, int]]] = {}
        
        if aggressive_mode:
            self.logger.warning("⚠️ AGGRESSIVE MODE ENABLED - Higher ban risk!")
    
    # --------------------------------------------------
    # Account Profile Management
    # --------------------------------------------------
    
    def register_account(self, username: str, platform: str,
                         created_date: datetime = None) -> AccountProfile:
        """
        Register an account for protection.
        
        Args:
            username: Account username
            platform: Platform name
            created_date: When account was created (for warmup)
        
        Returns:
            AccountProfile
        """
        key = f"{platform}:{username}"
        
        if created_date is None:
            # Assume account is new if not specified
            created_date = datetime.now()
        
        profile = AccountProfile(
            username=username,
            platform=platform,
            created_date=created_date,
        )
        
        self._profiles[key] = profile
        self.logger.info(f"Registered account: {username} on {platform}")
        
        # Generate daily activity pattern
        self._generate_daily_pattern(key)
        
        return profile
    
    def get_account_age_days(self, username: str, platform: str) -> int:
        """Get account age in days."""
        key = f"{platform}:{username}"
        profile = self._profiles.get(key)
        
        if not profile:
            return 0
        
        return (datetime.now() - profile.created_date).days
    
    def get_current_limits(self, username: str, platform: str) -> Dict[str, int]:
        """
        Get current limits based on account age and mode.
        
        Returns limits appropriate for the account's warmup stage.
        """
        if self.aggressive_mode:
            return AGGRESSIVE_LIMITS.get(platform, AGGRESSIVE_LIMITS["instagram"])
        
        age_days = self.get_account_age_days(username, platform)
        schedule = WARMUP_SCHEDULE.get(platform, WARMUP_SCHEDULE["instagram"])
        
        # Find appropriate limits for account age
        applicable_limits = None
        for day_threshold in sorted(schedule.keys()):
            if age_days >= day_threshold:
                applicable_limits = schedule[day_threshold]
        
        return applicable_limits or schedule[0]
    
    # --------------------------------------------------
    # Safety Checks
    # --------------------------------------------------
    
    def is_safe_to_act(self, platform: str, action_type: str,
                       username: str = "default") -> Tuple[bool, str]:
        """
        Check if it's safe to perform an action.
        
        Args:
            platform: Platform name
            action_type: Type of action (dm, follow, like, view)
            username: Account username
        
        Returns:
            Tuple of (is_safe, reason)
        """
        key = f"{platform}:{username}"
        profile = self._profiles.get(key)
        
        # Check 1: Account paused?
        if profile and profile.is_paused:
            if profile.pause_until and datetime.now() < profile.pause_until:
                remaining = (profile.pause_until - datetime.now()).total_seconds() / 3600
                return False, f"Account paused for {remaining:.1f} more hours"
            else:
                profile.is_paused = False
                profile.pause_until = None
        
        # Check 2: Human hours?
        if not self._is_human_hours():
            return False, "Outside active hours (sleep time)"
        
        # Check 3: Activity pattern?
        if not self._matches_daily_pattern(key):
            return False, "Outside today's activity window"
        
        # Check 4: Rate limit check
        limits = self.get_current_limits(username, platform)
        limit_key = f"daily_{action_type}s"
        daily_limit = limits.get(limit_key, 0)
        
        if daily_limit == 0:
            return False, f"{action_type} not allowed during warmup"
        
        # Check current count
        current_count = self.db.get_daily_count(platform, action_type)
        if current_count >= daily_limit:
            return False, f"Daily {action_type} limit reached ({current_count}/{daily_limit})"
        
        # Check 5: Trust score
        if profile and profile.trust_score < 20:
            return False, "Trust score too low - account at risk"
        
        # Check 6: Burst protection (hourly)
        hourly_count = self.db.get_hourly_count(platform, action_type)
        hourly_limit = self._get_hourly_limit(action_type, daily_limit)
        if hourly_count >= hourly_limit:
            return False, f"Hourly {action_type} limit reached ({hourly_count}/{hourly_limit})"
        
        # Check 7: Minimum time between same actions
        if not self._check_action_cooldown(platform, action_type):
            return False, f"Too soon since last {action_type}"
        
        return True, "Safe to proceed"
    
    def _get_hourly_limit(self, action_type: str, daily_limit: int) -> int:
        """Calculate hourly limit (spread actions across day)."""
        # Assume 12 active hours, spread evenly with some buffer
        base_hourly = max(1, daily_limit // 10)
        
        # DMs should be more spread out
        if action_type == "dm":
            return max(1, daily_limit // 15)
        
        return base_hourly
    
    def _check_action_cooldown(self, platform: str, action_type: str) -> bool:
        """Check minimum time between actions."""
        key = f"{platform}:{action_type}"
        last_time = self._last_action_times.get(key)
        
        if not last_time:
            return True
        
        # Minimum cooldowns (seconds)
        cooldowns = {
            "dm": 120,      # 2 minutes between DMs
            "follow": 60,   # 1 minute between follows
            "like": 30,     # 30 seconds between likes
            "comment": 180, # 3 minutes between comments
            "view": 3,      # 3 seconds between views (safe action)
        }
        
        min_cooldown = cooldowns.get(action_type, 30)
        elapsed = (datetime.now() - last_time).total_seconds()
        
        return elapsed >= min_cooldown
    
    # --------------------------------------------------
    # Human-like Patterns
    # --------------------------------------------------
    
    def _is_human_hours(self) -> bool:
        """Check if current time is within human active hours."""
        hour = datetime.now().hour
        
        # Active hours: 6 AM - midnight (more lenient)
        # Set to False only between midnight and 6 AM
        if hour < 6:
            return False
        
        return True
    
    def _generate_daily_pattern(self, account_key: str):
        """Generate random activity windows for the day."""
        # Create 2-4 activity bursts throughout the day
        num_windows = random.randint(2, 4)
        
        # Available hours: 8 AM - 10 PM
        available_hours = list(range(8, 22))
        random.shuffle(available_hours)
        
        windows = []
        for i in range(num_windows):
            start_hour = available_hours[i]
            duration = random.randint(1, 3)  # 1-3 hour windows
            end_hour = min(22, start_hour + duration)
            windows.append((start_hour, end_hour))
        
        # Sort by start time
        windows.sort(key=lambda x: x[0])
        self._daily_patterns[account_key] = windows
        
        self.logger.debug(f"Daily pattern for {account_key}: {windows}")
    
    def _matches_daily_pattern(self, account_key: str) -> bool:
        """Check if current time matches daily activity pattern."""
        if account_key not in self._daily_patterns:
            self._generate_daily_pattern(account_key)
        
        current_hour = datetime.now().hour
        windows = self._daily_patterns[account_key]
        
        for start, end in windows:
            if start <= current_hour < end:
                return True
        
        # 10% chance to act outside windows (humans aren't perfectly predictable)
        return random.random() < 0.1
    
    # --------------------------------------------------
    # Action Recording & Trust Score
    # --------------------------------------------------
    
    def record_action(self, platform: str, action_type: str,
                      username: str = "default", success: bool = True):
        """Record an action and update trust score."""
        key = f"{platform}:{username}"
        profile = self._profiles.get(key)
        
        # Update last action time
        self._last_action_times[f"{platform}:{action_type}"] = datetime.now()
        
        # Update session counter
        session_key = f"{platform}:{action_type}"
        self._session_actions[session_key] = self._session_actions.get(session_key, 0) + 1
        
        if profile:
            profile.total_actions += 1
            
            if success:
                # Small trust increase for successful actions
                profile.trust_score = min(100, profile.trust_score + 0.1)
            else:
                # Trust decrease for failures
                profile.trust_score = max(0, profile.trust_score - 2)
    
    def record_warning(self, platform: str, username: str = "default",
                       warning_type: str = "rate_limit"):
        """
        Record a warning (action blocked, rate limit, etc.)
        
        This significantly impacts trust score and may pause account.
        """
        key = f"{platform}:{username}"
        profile = self._profiles.get(key)
        
        if not profile:
            return
        
        profile.warnings_received += 1
        profile.last_warning_date = datetime.now()
        
        # Significant trust score penalty
        penalties = {
            "rate_limit": 15,
            "action_blocked": 25,
            "suspicious_activity": 30,
            "temporary_ban": 50,
        }
        penalty = penalties.get(warning_type, 20)
        profile.trust_score = max(0, profile.trust_score - penalty)
        
        self.logger.warning(
            f"⚠️ Warning recorded for {username}: {warning_type} "
            f"(Trust: {profile.trust_score:.1f})"
        )
        
        # Auto-pause based on severity
        if warning_type == "temporary_ban":
            self._pause_account(profile, hours=48)
        elif warning_type == "action_blocked":
            self._pause_account(profile, hours=24)
        elif warning_type == "rate_limit":
            self._pause_account(profile, hours=6)
        elif profile.warnings_received >= 3:
            self._pause_account(profile, hours=12)
    
    def _pause_account(self, profile: AccountProfile, hours: int):
        """Pause account for specified hours."""
        profile.is_paused = True
        profile.pause_until = datetime.now() + timedelta(hours=hours)
        
        self.logger.warning(
            f"🛑 Account {profile.username} paused for {hours} hours"
        )
    
    # --------------------------------------------------
    # Smart Delays
    # --------------------------------------------------
    
    def get_smart_delay(self, action_type: str) -> float:
        """
        Get a human-like delay for an action.
        
        Uses variable delays based on action type and randomization.
        """
        # Base delays (seconds)
        base_delays = {
            "view": (3, 8),
            "like": (5, 15),
            "follow": (10, 30),
            "dm": (30, 90),
            "comment": (20, 60),
        }
        
        min_delay, max_delay = base_delays.get(action_type, (5, 15))
        
        # Add randomness
        delay = random.uniform(min_delay, max_delay)
        
        # Occasionally add longer "distraction" pauses (human behavior)
        if random.random() < 0.1:  # 10% chance
            delay += random.uniform(30, 120)  # 30s - 2min extra
        
        # Very occasionally, much longer pause (bathroom break, etc.)
        if random.random() < 0.02:  # 2% chance
            delay += random.uniform(180, 600)  # 3-10 min extra
        
        return delay
    
    def wait_smart_delay(self, action_type: str):
        """Wait for a smart delay."""
        delay = self.get_smart_delay(action_type)
        self.logger.debug(f"Waiting {delay:.1f}s before {action_type}")
        time.sleep(delay)
    
    # --------------------------------------------------
    # Risk Assessment
    # --------------------------------------------------
    
    def get_risk_level(self, platform: str, 
                       username: str = "default") -> RiskLevel:
        """Assess current risk level for an account."""
        key = f"{platform}:{username}"
        profile = self._profiles.get(key)
        
        if not profile:
            return RiskLevel.CAUTION
        
        # Check trust score
        if profile.trust_score < 20:
            return RiskLevel.DANGER
        elif profile.trust_score < 40:
            return RiskLevel.WARNING
        elif profile.trust_score < 60:
            return RiskLevel.CAUTION
        
        # Check recent warnings
        if profile.last_warning_date:
            days_since_warning = (datetime.now() - profile.last_warning_date).days
            if days_since_warning < 1:
                return RiskLevel.DANGER
            elif days_since_warning < 3:
                return RiskLevel.WARNING
            elif days_since_warning < 7:
                return RiskLevel.CAUTION
        
        # Check if paused
        if profile.is_paused:
            return RiskLevel.BLOCKED
        
        return RiskLevel.SAFE
    
    def get_status_report(self, platform: str, 
                          username: str = "default") -> Dict:
        """Get comprehensive status report for an account."""
        key = f"{platform}:{username}"
        profile = self._profiles.get(key)
        
        if not profile:
            return {"error": "Account not registered"}
        
        age_days = self.get_account_age_days(username, platform)
        limits = self.get_current_limits(username, platform)
        risk = self.get_risk_level(platform, username)
        
        return {
            "username": username,
            "platform": platform,
            "account_age_days": age_days,
            "warmup_complete": age_days >= 30,
            "trust_score": profile.trust_score,
            "risk_level": risk.value,
            "warnings_received": profile.warnings_received,
            "is_paused": profile.is_paused,
            "pause_until": profile.pause_until.isoformat() if profile.pause_until else None,
            "current_limits": limits,
            "total_actions": profile.total_actions,
            "aggressive_mode": self.aggressive_mode,
        }
    
    def print_status(self, platform: str, username: str = "default"):
        """Print formatted status report."""
        report = self.get_status_report(platform, username)
        
        if "error" in report:
            print(f"❌ {report['error']}")
            return
        
        risk_icons = {
            "safe": "✅",
            "caution": "⚠️",
            "warning": "🟠",
            "danger": "🔴",
            "blocked": "⛔",
        }
        
        print(f"\n{'='*50}")
        print(f"Account Protection Status: @{username}")
        print(f"{'='*50}")
        print(f"Platform: {platform}")
        print(f"Account Age: {report['account_age_days']} days")
        print(f"Warmup Complete: {'Yes' if report['warmup_complete'] else 'No'}")
        print(f"Trust Score: {report['trust_score']:.1f}/100")
        print(f"Risk Level: {risk_icons.get(report['risk_level'], '❓')} {report['risk_level'].upper()}")
        print(f"Warnings: {report['warnings_received']}")
        
        if report['is_paused']:
            print(f"⛔ PAUSED until: {report['pause_until']}")
        
        print(f"\nCurrent Limits:")
        for action, limit in report['current_limits'].items():
            print(f"  {action}: {limit}")
        
        if report['aggressive_mode']:
            print(f"\n⚠️ AGGRESSIVE MODE - Higher risk!")
        
        print(f"{'='*50}\n")


# --------------------------------------------------
# Browser Fingerprint Randomization
# --------------------------------------------------

def get_random_user_agent() -> str:
    """Get a random realistic user agent."""
    user_agents = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    return random.choice(user_agents)


def get_random_viewport() -> Tuple[int, int]:
    """Get a random realistic viewport size."""
    viewports = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1280, 720),
        (1600, 900),
    ]
    return random.choice(viewports)


def get_random_timezone() -> str:
    """Get a random US timezone."""
    timezones = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
    ]
    return random.choice(timezones)

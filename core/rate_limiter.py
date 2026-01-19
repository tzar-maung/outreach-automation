"""
Rate Limiter - Track and Enforce Action Limits

Prevents bans by enforcing:
- Daily limits per action type
- Hourly limits for burst protection
- Cooldown periods between actions
- Platform-specific limits

Usage:
    limiter = RateLimiter(db)
    if limiter.can_follow("instagram"):
        # perform follow
        limiter.record_action("instagram", "follow", "username")
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field

from outreach_bot.core.database import Database


@dataclass
class PlatformLimits:
    """Rate limits for a specific platform."""
    # Daily limits
    daily_views: int = 200
    daily_follows: int = 20
    daily_unfollows: int = 20
    daily_likes: int = 50
    daily_comments: int = 10
    daily_dms: int = 10
    
    # Hourly limits (burst protection)
    hourly_follows: int = 5
    hourly_likes: int = 15
    hourly_dms: int = 3
    
    # Cooldowns (seconds)
    cooldown_between_actions: float = 3.0
    cooldown_between_profiles: float = 10.0
    cooldown_after_follow: float = 30.0
    cooldown_after_dm: float = 60.0


# Default limits for each platform
DEFAULT_LIMITS = {
    "instagram": PlatformLimits(
        daily_views=200,
        daily_follows=20,
        daily_unfollows=15,
        daily_likes=50,
        daily_comments=10,
        daily_dms=10,
        hourly_follows=5,
        hourly_likes=15,
        hourly_dms=3,
        cooldown_between_actions=3.0,
        cooldown_between_profiles=10.0,
        cooldown_after_follow=30.0,
        cooldown_after_dm=60.0,
    ),
    "tiktok": PlatformLimits(
        daily_views=150,
        daily_follows=15,
        daily_unfollows=10,
        daily_likes=40,
        daily_comments=5,
        daily_dms=5,
        hourly_follows=4,
        hourly_likes=12,
        hourly_dms=2,
        cooldown_between_actions=4.0,
        cooldown_between_profiles=15.0,
        cooldown_after_follow=45.0,
        cooldown_after_dm=90.0,
    ),
    "generic": PlatformLimits(
        daily_views=500,
        daily_follows=100,
        daily_unfollows=100,
        daily_likes=100,
        daily_comments=50,
        daily_dms=50,
        hourly_follows=20,
        hourly_likes=30,
        hourly_dms=10,
        cooldown_between_actions=1.0,
        cooldown_between_profiles=3.0,
        cooldown_after_follow=5.0,
        cooldown_after_dm=10.0,
    ),
}


class RateLimiter:
    """
    Rate limiter with database-backed tracking.
    
    Features:
    - Daily and hourly limits
    - Automatic cooldowns
    - Duplicate action prevention
    - Statistics and warnings
    """
    
    def __init__(self, database: Database, 
                 limits: Dict[str, PlatformLimits] = None):
        """
        Initialize rate limiter.
        
        Args:
            database: Database instance for persistence
            limits: Custom limits (optional)
        """
        self.db = database
        self.limits = limits or DEFAULT_LIMITS
        
        # Track last action times (in-memory)
        self._last_action_time: Dict[str, datetime] = {}
        self._last_action_type: Dict[str, str] = {}
        
        # Callbacks for limit warnings
        self._warning_callbacks: list = []
    
    # --------------------------------------------------
    # Limit Checking
    # --------------------------------------------------
    
    def get_limits(self, platform: str) -> PlatformLimits:
        """Get limits for a platform."""
        return self.limits.get(platform, DEFAULT_LIMITS.get("generic"))
    
    def can_perform(self, platform: str, action_type: str) -> bool:
        """
        Check if an action can be performed.
        
        Args:
            platform: Platform name
            action_type: Action type (view, follow, like, dm)
        
        Returns:
            True if action is allowed
        """
        limits = self.get_limits(platform)
        
        # Get daily limit for action type
        daily_limit_attr = f"daily_{action_type}s"
        daily_limit = getattr(limits, daily_limit_attr, 100)
        
        # Get hourly limit if exists
        hourly_limit_attr = f"hourly_{action_type}s"
        hourly_limit = getattr(limits, hourly_limit_attr, None)
        
        return self.db.can_perform_action(
            platform=platform,
            action_type=action_type,
            daily_limit=daily_limit,
            hourly_limit=hourly_limit,
        )
    
    def can_view(self, platform: str) -> bool:
        """Check if viewing is allowed."""
        return self.can_perform(platform, "view")
    
    def can_follow(self, platform: str) -> bool:
        """Check if following is allowed."""
        return self.can_perform(platform, "follow")
    
    def can_like(self, platform: str) -> bool:
        """Check if liking is allowed."""
        return self.can_perform(platform, "like")
    
    def can_dm(self, platform: str) -> bool:
        """Check if sending DMs is allowed."""
        return self.can_perform(platform, "dm")
    
    # --------------------------------------------------
    # Action Recording
    # --------------------------------------------------
    
    def record_action(self, platform: str, action_type: str,
                      username: str, target_id: int = None,
                      status: str = "success") -> int:
        """
        Record an action and update counters.
        
        Args:
            platform: Platform name
            action_type: Action type
            username: Target username
            target_id: Optional target ID
            status: success or failed
        
        Returns:
            Action log ID
        """
        # Update last action tracking
        key = f"{platform}:{action_type}"
        self._last_action_time[key] = datetime.now()
        self._last_action_type[platform] = action_type
        
        # Log to database
        action_id = self.db.log_action(
            username=username,
            platform=platform,
            action_type=action_type,
            status=status,
            target_id=target_id,
        )
        
        # Check if approaching limits
        self._check_limit_warnings(platform, action_type)
        
        return action_id
    
    # --------------------------------------------------
    # Cooldowns
    # --------------------------------------------------
    
    def get_cooldown(self, platform: str, action_type: str = None) -> float:
        """
        Get the cooldown time for the next action.
        
        Args:
            platform: Platform name
            action_type: Specific action type (optional)
        
        Returns:
            Cooldown in seconds
        """
        limits = self.get_limits(platform)
        
        # Get action-specific cooldown
        if action_type == "follow":
            return limits.cooldown_after_follow
        elif action_type == "dm":
            return limits.cooldown_after_dm
        else:
            return limits.cooldown_between_actions
    
    def wait_for_cooldown(self, platform: str, 
                          action_type: str = None) -> float:
        """
        Wait for the appropriate cooldown period.
        
        Args:
            platform: Platform name
            action_type: Type of action just performed
        
        Returns:
            Actual time waited
        """
        cooldown = self.get_cooldown(platform, action_type)
        
        # Add some randomness (±20%)
        import random
        actual_cooldown = cooldown * random.uniform(0.8, 1.2)
        
        time.sleep(actual_cooldown)
        return actual_cooldown
    
    def time_until_next_action(self, platform: str) -> float:
        """
        Get time remaining until next action is allowed.
        
        Returns:
            Seconds until next action (0 if ready)
        """
        last_action_type = self._last_action_type.get(platform)
        key = f"{platform}:{last_action_type}" if last_action_type else None
        
        if not key or key not in self._last_action_time:
            return 0
        
        last_time = self._last_action_time[key]
        cooldown = self.get_cooldown(platform, last_action_type)
        elapsed = (datetime.now() - last_time).total_seconds()
        
        remaining = cooldown - elapsed
        return max(0, remaining)
    
    # --------------------------------------------------
    # Duplicate Prevention
    # --------------------------------------------------
    
    def has_interacted(self, username: str, platform: str,
                       action_type: str = None) -> bool:
        """
        Check if we've already interacted with a user.
        
        Args:
            username: Target username
            platform: Platform name
            action_type: Specific action to check (optional)
        
        Returns:
            True if already interacted
        """
        return self.db.has_interacted_with(username, platform, action_type)
    
    def has_followed(self, username: str, platform: str) -> bool:
        """Check if we've already followed this user."""
        return self.has_interacted(username, platform, "follow")
    
    def has_liked(self, username: str, platform: str) -> bool:
        """Check if we've already liked this user's content."""
        return self.has_interacted(username, platform, "like")
    
    def has_dmed(self, username: str, platform: str) -> bool:
        """Check if we've already DM'd this user."""
        return self.has_interacted(username, platform, "dm")
    
    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------
    
    def get_daily_stats(self, platform: str) -> Dict[str, int]:
        """Get today's action counts for a platform."""
        action_types = ["view", "follow", "unfollow", "like", "comment", "dm"]
        stats = {}
        
        for action in action_types:
            stats[action] = self.db.get_daily_count(platform, action)
        
        return stats
    
    def get_remaining_limits(self, platform: str) -> Dict[str, int]:
        """Get remaining actions allowed today."""
        limits = self.get_limits(platform)
        daily_stats = self.get_daily_stats(platform)
        
        remaining = {}
        for action, count in daily_stats.items():
            limit_attr = f"daily_{action}s"
            limit = getattr(limits, limit_attr, 100)
            remaining[action] = max(0, limit - count)
        
        return remaining
    
    def get_limit_status(self, platform: str) -> Dict:
        """Get comprehensive limit status."""
        limits = self.get_limits(platform)
        daily_stats = self.get_daily_stats(platform)
        remaining = self.get_remaining_limits(platform)
        
        status = {
            "platform": platform,
            "daily_stats": daily_stats,
            "remaining": remaining,
            "limits": {
                "daily_views": limits.daily_views,
                "daily_follows": limits.daily_follows,
                "daily_likes": limits.daily_likes,
                "daily_dms": limits.daily_dms,
            },
            "warnings": [],
        }
        
        # Add warnings for low limits
        for action, count in remaining.items():
            limit_attr = f"daily_{action}s"
            limit = getattr(limits, limit_attr, 100)
            
            if count == 0:
                status["warnings"].append(f"⛔ {action}: LIMIT REACHED")
            elif count <= limit * 0.1:  # Less than 10% remaining
                status["warnings"].append(f"⚠️ {action}: Only {count} remaining")
        
        return status
    
    # --------------------------------------------------
    # Warning Callbacks
    # --------------------------------------------------
    
    def add_warning_callback(self, callback: Callable[[str, str, int], None]):
        """
        Add a callback for limit warnings.
        
        Callback signature: (platform, action_type, remaining_count)
        """
        self._warning_callbacks.append(callback)
    
    def _check_limit_warnings(self, platform: str, action_type: str):
        """Check and trigger warnings if approaching limits."""
        limits = self.get_limits(platform)
        limit_attr = f"daily_{action_type}s"
        daily_limit = getattr(limits, limit_attr, 100)
        
        current_count = self.db.get_daily_count(platform, action_type)
        remaining = daily_limit - current_count
        
        # Trigger warnings at 90%, 95%, and 100%
        if remaining <= 0 or remaining <= daily_limit * 0.1:
            for callback in self._warning_callbacks:
                try:
                    callback(platform, action_type, remaining)
                except Exception:
                    pass
    
    # --------------------------------------------------
    # Utility
    # --------------------------------------------------
    
    def reset_daily_counters(self, platform: str = None):
        """
        Reset daily counters (for testing).
        
        Note: In production, counters reset automatically at midnight.
        """
        # This would delete today's rate_limits entries
        # Left as a stub for now - not recommended for production
        pass
    
    def print_status(self, platform: str):
        """Print a formatted status report."""
        status = self.get_limit_status(platform)
        
        print(f"\n{'='*50}")
        print(f"Rate Limit Status: {platform.upper()}")
        print(f"{'='*50}")
        
        print("\nToday's Actions:")
        for action, count in status["daily_stats"].items():
            limit = status["limits"].get(f"daily_{action}s", "N/A")
            print(f"  {action}: {count}/{limit}")
        
        print("\nRemaining:")
        for action, count in status["remaining"].items():
            print(f"  {action}: {count}")
        
        if status["warnings"]:
            print("\nWarnings:")
            for warning in status["warnings"]:
                print(f"  {warning}")
        
        print(f"{'='*50}\n")

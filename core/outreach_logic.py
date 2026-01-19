"""
Outreach decision logic.
"""
import random
from outreach_bot.core.human_behavior import human_pause


# Words that indicate a target should be skipped
BLACKLIST = ["login", "signup", "privacy", "terms", "help", "support", "contact"]


def should_outreach(target: dict) -> bool:
    """
    Decide whether this target is worth interacting with.
    
    Args:
        target: Dictionary with 'text' and 'href' keys
    
    Returns:
        True if target should be engaged
    """
    text = target.get("text", "").lower()

    # Skip if contains blacklisted words
    for word in BLACKLIST:
        if word in text:
            return False

    # Add randomness to look human (skip ~30% of valid targets)
    return random.random() > 0.3


def simulate_interest():
    """Human-like pause before taking action."""
    human_pause(1.2, 2.5)


def add_to_blacklist(word: str):
    """Add a word to the blacklist."""
    BLACKLIST.append(word.lower())

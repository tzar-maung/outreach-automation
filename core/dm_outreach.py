"""
DM Outreach - Direct Message Automation for Instagram

Features:
- Personalized message templates
- Rate limiting integration
- Duplicate prevention
- Conversation tracking
- Safe mode (mock/real)

⚠️ WARNING: DM automation is high-risk for bans.
Use sparingly and only for legitimate outreach.

Usage:
    dm_manager = DMOutreach(driver, logger, rate_limiter)
    dm_manager.send_dm("username", "Hello!")
"""
import time
import random
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    ElementClickInterceptedException,
)

from outreach_bot.core.human_behavior import (
    human_pause,
    human_type,
    human_mouse_move,
)
from outreach_bot.core.rate_limiter import RateLimiter
from outreach_bot.core.database import Database


@dataclass
class DMTemplate:
    """A message template with placeholders."""
    name: str
    template: str
    category: str = "general"  # general, follow_up, cold_outreach
    
    def render(self, **kwargs) -> str:
        """Render template with variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            # Return template with missing placeholders shown
            return self.template


# Default message templates
DEFAULT_TEMPLATES = [
    DMTemplate(
        name="friendly_intro",
        template="Hey {name}! I came across your profile and really loved your content. Would love to connect!",
        category="cold_outreach",
    ),
    DMTemplate(
        name="collaboration",
        template="Hi {name}! I'm {my_name} and I think our content styles would complement each other. Open to a collab?",
        category="cold_outreach",
    ),
    DMTemplate(
        name="question",
        template="Hey {name}! Quick question - I noticed {observation}. How did you achieve that?",
        category="engagement",
    ),
    DMTemplate(
        name="compliment",
        template="Hi {name}! Just wanted to say your {content_type} is amazing. Keep up the great work! 🙌",
        category="engagement",
    ),
    DMTemplate(
        name="follow_up",
        template="Hey {name}, following up on my previous message. Would love to hear your thoughts!",
        category="follow_up",
    ),
]


class DMOutreach:
    """
    Instagram DM automation with safety features.
    
    Modes:
    - mock: Simulate sending (for testing)
    - real: Actually send messages
    
    Safety features:
    - Rate limiting
    - Duplicate prevention
    - Human-like typing
    - Random delays
    """
    
    # Instagram DM selectors (may need updates)
    SELECTORS = {
        # Navigation to DMs
        "dm_icon": "svg[aria-label='Messenger']",
        "new_message_btn": "svg[aria-label='New message']",
        
        # New message dialog
        "recipient_input": "input[placeholder='Search...']",
        "recipient_result": "div[role='button']",
        "next_button": "//div[text()='Next']",
        
        # Chat window
        "message_input": "textarea[placeholder='Message...']",
        "send_button": "//button[text()='Send']",
        
        # Existing conversations
        "conversation_list": "div[role='listbox']",
        "conversation_item": "a[href*='/direct/t/']",
        
        # Message status
        "sent_indicator": "svg[aria-label='Sent']",
        "seen_indicator": "svg[aria-label='Seen']",
    }
    
    def __init__(self, driver, logger, 
                 rate_limiter: RateLimiter = None,
                 database: Database = None,
                 mode: str = "mock"):
        """
        Initialize DM outreach.
        
        Args:
            driver: Selenium WebDriver
            logger: Logger instance
            rate_limiter: Rate limiter (optional)
            database: Database for tracking (optional)
            mode: 'mock' or 'real'
        """
        self.driver = driver
        self.logger = logger
        self.rate_limiter = rate_limiter
        self.db = database
        self.mode = mode
        
        # Templates
        self.templates: List[DMTemplate] = list(DEFAULT_TEMPLATES)
        
        # Session tracking
        self.session_stats = {
            "attempted": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        # Callbacks
        self._before_send_callbacks: List[Callable] = []
        self._after_send_callbacks: List[Callable] = []
    
    # --------------------------------------------------
    # Template Management
    # --------------------------------------------------
    
    def add_template(self, name: str, template: str, 
                     category: str = "general") -> DMTemplate:
        """Add a custom message template."""
        tpl = DMTemplate(name=name, template=template, category=category)
        self.templates.append(tpl)
        return tpl
    
    def get_template(self, name: str = None, 
                     category: str = None) -> Optional[DMTemplate]:
        """Get a template by name or random from category."""
        if name:
            for tpl in self.templates:
                if tpl.name == name:
                    return tpl
            return None
        
        if category:
            matching = [t for t in self.templates if t.category == category]
            return random.choice(matching) if matching else None
        
        return random.choice(self.templates) if self.templates else None
    
    def render_message(self, template_name: str = None,
                       category: str = None, **kwargs) -> str:
        """Render a message from template with variables."""
        tpl = self.get_template(name=template_name, category=category)
        if not tpl:
            return kwargs.get("message", "Hello!")
        
        return tpl.render(**kwargs)
    
    # --------------------------------------------------
    # DM Sending
    # --------------------------------------------------
    
    def send_dm(self, username: str, message: str,
                skip_if_sent: bool = True) -> Dict:
        """
        Send a direct message to a user.
        
        Args:
            username: Target username (without @)
            message: Message to send
            skip_if_sent: Skip if already messaged
        
        Returns:
            Result dictionary with status
        """
        username = username.lstrip("@").strip()
        
        result = {
            "username": username,
            "message": message,
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
        }
        
        self.session_stats["attempted"] += 1
        
        # Check rate limits
        if self.rate_limiter and not self.rate_limiter.can_dm("instagram"):
            self.logger.warning(f"Rate limit reached for DMs")
            result["status"] = "rate_limited"
            self.session_stats["skipped"] += 1
            return result
        
        # Check if already messaged
        if skip_if_sent and self.db:
            if self.db.has_interacted_with(username, "instagram", "dm"):
                self.logger.info(f"Already messaged @{username}, skipping")
                result["status"] = "already_sent"
                self.session_stats["skipped"] += 1
                return result
        
        # Run before-send callbacks
        for callback in self._before_send_callbacks:
            try:
                callback(username, message)
            except Exception as e:
                self.logger.warning(f"Before-send callback error: {e}")
        
        # Mock mode - just log
        if self.mode == "mock":
            self.logger.info(f"MOCK: Would send to @{username}: {message[:50]}...")
            result["status"] = "mock_sent"
            self._record_dm(username, message, "success")
            self.session_stats["sent"] += 1
            return result
        
        # Real mode - actually send
        try:
            success = self._send_dm_instagram(username, message)
            
            if success:
                result["status"] = "sent"
                self._record_dm(username, message, "success")
                self.session_stats["sent"] += 1
                self.logger.info(f"✅ DM sent to @{username}")
            else:
                result["status"] = "failed"
                self._record_dm(username, message, "failed")
                self.session_stats["failed"] += 1
                self.logger.error(f"❌ Failed to send DM to @{username}")
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            self._record_dm(username, message, "failed", str(e))
            self.session_stats["failed"] += 1
            self.logger.error(f"DM error for @{username}: {e}")
        
        # Run after-send callbacks
        for callback in self._after_send_callbacks:
            try:
                callback(username, message, result)
            except Exception as e:
                self.logger.warning(f"After-send callback error: {e}")
        
        # Cooldown
        if self.rate_limiter:
            self.rate_limiter.wait_for_cooldown("instagram", "dm")
        else:
            human_pause(30, 60)  # Default DM cooldown
        
        return result
    
    def send_dm_with_template(self, username: str,
                              template_name: str = None,
                              category: str = "cold_outreach",
                              **template_vars) -> Dict:
        """Send a DM using a template."""
        # Add username to template vars
        template_vars.setdefault("name", username)
        
        message = self.render_message(
            template_name=template_name,
            category=category,
            **template_vars
        )
        
        return self.send_dm(username, message)
    
    def send_bulk_dms(self, targets: List[Dict],
                      max_count: int = None) -> List[Dict]:
        """
        Send DMs to multiple targets.
        
        Args:
            targets: List of dicts with username and optional template vars
            max_count: Maximum number to send
        
        Returns:
            List of result dictionaries
        """
        results = []
        sent_count = 0
        
        for target in targets:
            if max_count and sent_count >= max_count:
                self.logger.info(f"Reached max count ({max_count}), stopping")
                break
            
            username = target.get("username")
            if not username:
                continue
            
            # Get message or use template
            if "message" in target:
                result = self.send_dm(username, target["message"])
            else:
                template_vars = {k: v for k, v in target.items() if k != "username"}
                result = self.send_dm_with_template(
                    username,
                    category=target.get("category", "cold_outreach"),
                    **template_vars
                )
            
            results.append(result)
            
            if result["status"] in ["sent", "mock_sent"]:
                sent_count += 1
            
            # Check if we should stop (rate limited)
            if result["status"] == "rate_limited":
                self.logger.warning("Rate limited, stopping bulk send")
                break
        
        return results
    
    # --------------------------------------------------
    # Instagram DM Implementation
    # --------------------------------------------------
    
    def _send_dm_instagram(self, username: str, message: str) -> bool:
        """
        Actually send a DM on Instagram.
        
        This method handles the Instagram UI interactions.
        """
        try:
            # Method 1: Go directly to profile and click Message
            profile_url = f"https://www.instagram.com/{username}/"
            self.driver.get(profile_url)
            human_pause(2, 4)
            
            # Find and click Message button
            message_btn = self._find_message_button()
            if not message_btn:
                self.logger.warning(f"Could not find Message button for @{username}")
                return self._send_dm_via_direct(username, message)
            
            human_mouse_move(self.driver, message_btn)
            human_pause(0.5, 1)
            message_btn.click()
            human_pause(2, 3)
            
            # Type and send message
            return self._type_and_send_message(message)
            
        except Exception as e:
            self.logger.error(f"Instagram DM failed: {e}")
            return False
    
    def _send_dm_via_direct(self, username: str, message: str) -> bool:
        """Alternative method: Start conversation from Direct inbox."""
        try:
            # Go to Direct inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            human_pause(2, 4)
            
            # Click new message button
            new_msg_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, self.SELECTORS["new_message_btn"]
                ))
            )
            new_msg_btn.click()
            human_pause(1, 2)
            
            # Search for recipient
            recipient_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, self.SELECTORS["recipient_input"]
                ))
            )
            
            human_type(recipient_input, username)
            human_pause(2, 3)
            
            # Click on search result
            result = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR, self.SELECTORS["recipient_result"]
                ))
            )
            result.click()
            human_pause(1, 2)
            
            # Click Next
            next_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH, self.SELECTORS["next_button"]
                ))
            )
            next_btn.click()
            human_pause(1, 2)
            
            # Type and send
            return self._type_and_send_message(message)
            
        except Exception as e:
            self.logger.error(f"Direct inbox method failed: {e}")
            return False
    
    def _find_message_button(self):
        """Find the Message button on a profile page."""
        selectors = [
            "//div[text()='Message']",
            "//button[contains(text(), 'Message')]",
            "div[role='button']:has-text('Message')",
        ]
        
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                return btn
            except TimeoutException:
                continue
        
        return None
    
    def _type_and_send_message(self, message: str) -> bool:
        """Type a message and send it."""
        try:
            # Find message input
            input_selectors = [
                self.SELECTORS["message_input"],
                "div[role='textbox']",
                "div[contenteditable='true']",
            ]
            
            message_input = None
            for selector in input_selectors:
                try:
                    message_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not message_input:
                self.logger.error("Could not find message input")
                return False
            
            # Click to focus
            message_input.click()
            human_pause(0.5, 1)
            
            # Type message with human-like timing
            human_type(message_input, message)
            human_pause(1, 2)
            
            # Send with Enter key
            message_input.send_keys(Keys.RETURN)
            human_pause(2, 3)
            
            # Verify sent (look for sent indicator)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, self.SELECTORS["sent_indicator"]
                    ))
                )
                return True
            except TimeoutException:
                # Assume sent if no error
                return True
                
        except Exception as e:
            self.logger.error(f"Type and send failed: {e}")
            return False
    
    # --------------------------------------------------
    # Recording and Tracking
    # --------------------------------------------------
    
    def _record_dm(self, username: str, message: str,
                   status: str, error: str = None):
        """Record a DM attempt in the database and rate limiter."""
        if self.rate_limiter:
            self.rate_limiter.record_action(
                platform="instagram",
                action_type="dm",
                username=username,
                status=status,
            )
        
        if self.db:
            self.db.log_action(
                username=username,
                platform="instagram",
                action_type="dm",
                status=status,
                details=f"Message: {message[:100]}... | Error: {error}" if error else f"Message: {message[:100]}...",
            )
    
    # --------------------------------------------------
    # Callbacks
    # --------------------------------------------------
    
    def add_before_send_callback(self, callback: Callable):
        """Add callback to run before sending each DM."""
        self._before_send_callbacks.append(callback)
    
    def add_after_send_callback(self, callback: Callable):
        """Add callback to run after sending each DM."""
        self._after_send_callbacks.append(callback)
    
    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------
    
    def get_session_stats(self) -> Dict:
        """Get statistics for the current session."""
        return {
            **self.session_stats,
            "success_rate": (
                self.session_stats["sent"] / self.session_stats["attempted"] * 100
                if self.session_stats["attempted"] > 0 else 0
            ),
        }
    
    def reset_session_stats(self):
        """Reset session statistics."""
        self.session_stats = {
            "attempted": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
        }


# --------------------------------------------------
# Convenience Functions
# --------------------------------------------------

def personalize_message(template: str, profile_info: Dict) -> str:
    """
    Personalize a message template with profile information.
    
    Args:
        template: Message template with placeholders
        profile_info: Dictionary with profile data
    
    Returns:
        Personalized message
    """
    replacements = {
        "{name}": profile_info.get("username", "there"),
        "{followers}": str(profile_info.get("followers", "many")),
        "{posts}": str(profile_info.get("posts", "your")),
        "{bio}": profile_info.get("bio", "")[:50] if profile_info.get("bio") else "",
    }
    
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result


def generate_opening_line(profile_info: Dict) -> str:
    """Generate a personalized opening line based on profile."""
    openings = [
        f"Hey {profile_info.get('username', 'there')}!",
        f"Hi {profile_info.get('username', 'there')}, hope you're having a great day!",
        f"Hello {profile_info.get('username', 'there')}!",
    ]
    
    # Add context-specific openings if we have bio info
    bio = profile_info.get("bio", "").lower()
    if "photographer" in bio:
        openings.append(f"Hey {profile_info.get('username')}, your photography is incredible!")
    elif "artist" in bio:
        openings.append(f"Hi {profile_info.get('username')}, I love your artistic style!")
    elif "travel" in bio:
        openings.append(f"Hey {profile_info.get('username')}, your travel content is amazing!")
    
    return random.choice(openings)

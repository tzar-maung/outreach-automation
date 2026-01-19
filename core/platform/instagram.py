"""
Instagram Platform Adapter

Supports view-only actions (safer) and optional outreach actions.
Uses the existing human_behavior and element_actions modules.
"""
import time
import random

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from outreach_bot.core.platform.base import BasePlatformAdapter
from outreach_bot.core.human_behavior import (
    human_pause,
    human_scroll_pattern,
    human_mouse_move,
    browse_naturally,
)
from outreach_bot.core.element_actions import (
    wait_for_element,
    scroll_until_visible,
    hover_and_click,
)


class InstagramAdapter(BasePlatformAdapter):
    """
    Instagram-specific adapter.
    
    View-only actions (SAFE):
        - view_profile()
        - view_posts()
        - get_profile_info()
    
    Outreach actions (USE WITH CAUTION):
        - follow_user()
        - like_post()
        - send_dm()
    """
    
    PLATFORM_NAME = "instagram"
    BASE_URL = "https://www.instagram.com"
    
    # CSS/XPath selectors (may need updates as Instagram changes)
    SELECTORS = {
        # Login detection
        "login_form": "input[name='username']",
        "logged_in_nav": "svg[aria-label='Home']",
        
        # Profile page
        "profile_header": "header section",
        "username_title": "header h2",
        "stats_list": "header ul li",
        "bio_section": "header section > div:nth-child(3)",
        "posts_grid": "article a[href*='/p/']",
        
        # Buttons
        "follow_button": "//button[contains(text(), 'Follow')]",
        "following_button": "//button[contains(text(), 'Following')]",
        "message_button": "//div[contains(text(), 'Message')]",
        
        # Post modal
        "like_button": "svg[aria-label='Like']",
        "unlike_button": "svg[aria-label='Unlike']",
        "close_modal": "svg[aria-label='Close']",
        
        # Popups
        "not_now_button": "//button[contains(text(), 'Not Now')]",
        "notification_popup": "//div[contains(text(), 'Turn on Notifications')]",
    }
    
    def __init__(self, driver, logger):
        super().__init__(driver, logger)
        self.session_stats = {
            "profiles_viewed": 0,
            "posts_viewed": 0,
            "follows_sent": 0,
            "likes_sent": 0,
            "dms_sent": 0,
        }
    
    # --------------------------------------------------
    # Core Methods (Required by BasePlatformAdapter)
    # --------------------------------------------------
    
    def open_target(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            self.logger.info(f"Opening: {url}")
            self.driver.get(url)
            human_pause(2.0, 4.0)
            self._dismiss_popups()
            return True
        except Exception as e:
            self.logger.error(f"Failed to open {url}: {e}")
            return False
    
    def perform_actions(self) -> dict:
        """
        Default action sequence for Instagram profiles.
        Safe, view-only by default.
        """
        result = {
            "url": self.driver.current_url,
            "platform": self.PLATFORM_NAME,
            "status": "success",
            "actions": [],
            "profile_info": None,
        }
        
        try:
            # 1. Dismiss any popups
            self._dismiss_popups()
            
            # 2. Browse naturally (looks human)
            self.logger.info("Browsing profile naturally...")
            browse_naturally(self.driver, duration_sec=5.0)
            result["actions"].append("browse")
            
            # 3. Extract profile info
            info = self.get_profile_info()
            result["profile_info"] = info
            result["actions"].append("extract_info")
            
            # 4. View a few posts
            posts_viewed = self.view_posts(count=2)
            result["actions"].append(f"viewed_{posts_viewed}_posts")
            
            # 5. Cooldown before next profile
            cooldown = random.uniform(3.0, 6.0)
            self.logger.info(f"Cooldown: {cooldown:.1f}s")
            time.sleep(cooldown)
            
            self.logger.info("Profile actions completed")
            
        except Exception as e:
            self.logger.error(f"Action error: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    # --------------------------------------------------
    # Login Detection
    # --------------------------------------------------
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in to Instagram."""
        try:
            # Go to Instagram home if not already there
            if "instagram.com" not in self.driver.current_url:
                self.driver.get(self.BASE_URL)
                human_pause(2.0, 3.0)
            
            # Look for logged-in indicator (Home icon)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.SELECTORS["logged_in_nav"])
                    )
                )
                self.logger.info("✓ Logged in to Instagram")
                return True
            except TimeoutException:
                pass
            
            # Look for login form (means NOT logged in)
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["login_form"]
                )
                self.logger.warning("✗ Not logged in to Instagram")
                return False
            except NoSuchElementException:
                # Neither found, assume logged in
                return True
                
        except Exception as e:
            self.logger.error(f"Login check failed: {e}")
            return False
    
    # --------------------------------------------------
    # View-Only Actions (SAFE)
    # --------------------------------------------------
    
    def view_profile(self, username: str) -> bool:
        """
        Navigate to and view a user's profile.
        
        Args:
            username: Instagram username (with or without @)
        
        Returns:
            True if profile loaded successfully
        """
        username = username.lstrip("@").strip()
        profile_url = f"{self.BASE_URL}/{username}/"
        
        if not self.open_target(profile_url):
            return False
        
        try:
            # Wait for profile to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "header"))
            )
            
            # Natural browsing
            browse_naturally(self.driver, duration_sec=4.0)
            
            self.session_stats["profiles_viewed"] += 1
            self.logger.info(f"✓ Viewed profile: @{username}")
            return True
            
        except TimeoutException:
            self.logger.error(f"Profile @{username} did not load (may not exist)")
            return False
    
    def view_posts(self, count: int = 3) -> int:
        """
        View posts on the current profile page.
        
        Args:
            count: Number of posts to view
        
        Returns:
            Number of posts actually viewed
        """
        viewed = 0
        
        try:
            # Scroll down to posts grid
            human_scroll_pattern(self.driver, rounds=2)
            
            # Find post links
            posts = self.driver.find_elements(
                By.CSS_SELECTOR, self.SELECTORS["posts_grid"]
            )
            
            if not posts:
                self.logger.info("No posts found on profile")
                return 0
            
            # View up to 'count' posts
            for post in posts[:count]:
                try:
                    # Click to open post
                    hover_and_click(self.driver, post)
                    human_pause(2.0, 4.0)
                    
                    # Browse the post
                    human_scroll_pattern(self.driver, rounds=1)
                    
                    # Close the modal
                    self._close_modal()
                    human_pause(1.0, 2.0)
                    
                    viewed += 1
                    self.session_stats["posts_viewed"] += 1
                    
                except Exception as e:
                    self.logger.warning(f"Could not view post: {e}")
                    self._close_modal()
            
            self.logger.info(f"Viewed {viewed} posts")
            
        except Exception as e:
            self.logger.error(f"Error viewing posts: {e}")
        
        return viewed
    
    def get_profile_info(self) -> dict:
        """
        Extract profile information from current page.
        
        Returns:
            Dictionary with username, followers, following, posts, bio
        """
        info = {
            "username": None,
            "posts": None,
            "followers": None,
            "following": None,
            "bio": None,
            "is_private": False,
        }
        
        try:
            # Get username from URL
            url = self.driver.current_url
            parts = url.rstrip("/").split("/")
            if parts:
                info["username"] = parts[-1]
            
            # Get stats (posts, followers, following)
            try:
                stats = self.driver.find_elements(
                    By.CSS_SELECTOR, self.SELECTORS["stats_list"]
                )
                if len(stats) >= 3:
                    info["posts"] = self._parse_stat(stats[0].text)
                    info["followers"] = self._parse_stat(stats[1].text)
                    info["following"] = self._parse_stat(stats[2].text)
            except Exception:
                pass
            
            # Check if private
            try:
                page_source = self.driver.page_source.lower()
                if "this account is private" in page_source:
                    info["is_private"] = True
            except Exception:
                pass
            
            self.logger.info(f"Profile info: {info}")
            
        except Exception as e:
            self.logger.error(f"Failed to extract profile info: {e}")
        
        return info
    
    # --------------------------------------------------
    # Outreach Actions (USE WITH CAUTION)
    # --------------------------------------------------
    
    def follow_user(self) -> bool:
        """
        Follow the user on the current profile page.
        
        WARNING: Use sparingly to avoid bans!
        
        Returns:
            True if follow was successful
        """
        try:
            follow_btn = wait_for_element(
                self.driver,
                By.XPATH,
                self.SELECTORS["follow_button"],
                timeout=5
            )
            
            if follow_btn:
                hover_and_click(self.driver, follow_btn)
                self.session_stats["follows_sent"] += 1
                self.logger.info("✓ Followed user")
                return True
            else:
                self.logger.info("Follow button not found (may already be following)")
                return False
                
        except Exception as e:
            self.logger.error(f"Follow failed: {e}")
            return False
    
    def like_post(self) -> bool:
        """
        Like the currently open post.
        
        WARNING: Use sparingly to avoid bans!
        
        Returns:
            True if like was successful
        """
        try:
            like_btn = wait_for_element(
                self.driver,
                By.CSS_SELECTOR,
                self.SELECTORS["like_button"],
                timeout=5
            )
            
            if like_btn:
                hover_and_click(self.driver, like_btn)
                self.session_stats["likes_sent"] += 1
                self.logger.info("✓ Liked post")
                return True
            else:
                self.logger.info("Like button not found (may already be liked)")
                return False
                
        except Exception as e:
            self.logger.error(f"Like failed: {e}")
            return False
    
    def send_dm(self, message: str) -> bool:
        """
        Send a DM to the user on the current profile page.
        
        WARNING: DMs are high-risk for bans! Use very sparingly!
        
        Args:
            message: Message text to send
        
        Returns:
            True if DM was sent successfully
        """
        from outreach_bot.core.human_behavior import human_pause
        
        try:
            # Step 1: Click Message button on profile
            self.logger.info("Looking for Message button...")
            
            message_btn = None
            message_selectors = [
                # English selectors
                (By.XPATH, "//div[text()='Message']"),
                (By.XPATH, "//button[text()='Message']"),
                (By.XPATH, "//div[contains(text(),'Message')]/ancestor::div[@role='button']"),
                (By.XPATH, "//button[contains(.,'Message')]"),
                # Role-based selectors
                (By.XPATH, "//div[@role='button'][contains(.,'Message')]"),
                (By.XPATH, "//*[@role='button'][.//text()[contains(.,'Message')]]"),
                # Thai selectors (ส่งข้อความ)
                (By.XPATH, "//div[contains(text(),'ส่งข้อความ')]"),
                (By.XPATH, "//button[contains(.,'ส่งข้อความ')]"),
                (By.XPATH, "//div[@role='button'][contains(.,'ส่งข้อความ')]"),
                # CSS selectors
                (By.CSS_SELECTOR, "div[role='button']"),
            ]
            
            for by, selector in message_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    for elem in elements:
                        text = elem.text.lower()
                        if 'message' in text or 'ส่งข้อความ' in text:
                            message_btn = elem
                            self.logger.info(f"Found button with text: {elem.text[:30]}")
                            break
                    if message_btn:
                        break
                except Exception:
                    continue
            
            # Last resort: find any button with message-like text
            if not message_btn:
                try:
                    all_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button'] | //button")
                    for btn in all_buttons:
                        text = btn.text.lower()
                        if 'message' in text or 'ส่งข้อความ' in text:
                            message_btn = btn
                            self.logger.info(f"Found button via fallback: {btn.text[:30]}")
                            break
                except Exception:
                    pass
            
            if not message_btn:
                self.logger.error("Message button not found - user may need to be followed first")
                # Debug: log available buttons
                try:
                    buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']")
                    self.logger.info(f"Available buttons on page: {len(buttons)}")
                    for i, btn in enumerate(buttons[:5]):
                        self.logger.info(f"  Button {i}: {btn.text[:40] if btn.text else '(no text)'}")
                except:
                    pass
                return False
            
            human_mouse_move(self.driver, message_btn)
            human_pause(0.3, 0.7)
            message_btn.click()
            
            self.logger.info("Clicked Message button, waiting for DM window...")
            human_pause(3.0, 5.0)  # Wait longer for DM window to load
            
            # Step 2: Find message input (Instagram uses contenteditable div)
            message_input = None
            input_selectors = [
                # Most specific: aria-label for message input
                (By.XPATH, "//div[@aria-label='Message'][@role='textbox']"),
                (By.XPATH, "//div[@aria-label='ข้อความ'][@role='textbox']"),  # Thai
                (By.XPATH, "//div[@aria-describedby][@role='textbox'][@contenteditable='true']"),
                # Generic contenteditable textbox
                (By.XPATH, "//div[@role='textbox'][@contenteditable='true']"),
                # Textarea fallback
                (By.CSS_SELECTOR, "textarea[placeholder*='Message']"),
                (By.CSS_SELECTOR, "textarea[placeholder*='ข้อความ']"),  # Thai
                # Last resort: any contenteditable
                (By.CSS_SELECTOR, "[contenteditable='true']"),
            ]
            
            for by, selector in input_selectors:
                try:
                    elements = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located((by, selector))
                    )
                    for elem in elements:
                        # Check if this looks like the message input
                        aria = elem.get_attribute('aria-label') or ''
                        role = elem.get_attribute('role') or ''
                        if 'message' in aria.lower() or 'ข้อความ' in aria or role == 'textbox':
                            message_input = elem
                            self.logger.info(f"Found message input: aria='{aria}', role='{role}'")
                            break
                    if message_input:
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            # If still not found, try the first contenteditable
            if not message_input:
                try:
                    message_input = self.driver.find_element(By.CSS_SELECTOR, "[contenteditable='true']")
                    self.logger.info("Using fallback contenteditable element")
                except:
                    pass
            
            if not message_input:
                self.logger.error("Message input not found")
                return False
            
            # Step 3: Click on input to focus using ActionChains
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            
            actions = ActionChains(self.driver)
            
            # Click to focus
            self.logger.info("Focusing on message input...")
            actions.move_to_element(message_input).click().perform()
            human_pause(1.0, 1.5)
            
            # Make sure element is focused
            self.driver.execute_script("arguments[0].focus();", message_input)
            human_pause(0.5, 1.0)
            
            # Step 4: Type message - try multiple methods
            self.logger.info("Typing message...")
            typing_success = False
            
            # Method 1: Use execCommand insertText (best for React)
            try:
                self.logger.info("Trying execCommand insertText...")
                self.driver.execute_script("""
                    var element = arguments[0];
                    var text = arguments[1];
                    
                    // Focus element
                    element.focus();
                    
                    // Select all existing content
                    var selection = window.getSelection();
                    var range = document.createRange();
                    range.selectNodeContents(element);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    // Use insertText command (triggers React properly)
                    document.execCommand('insertText', false, text);
                """, message_input, message)
                
                human_pause(1.5, 2.0)
                
                # Check if text was inserted
                content = self.driver.execute_script(
                    "return arguments[0].textContent || '';", message_input
                )
                if len(content) > 20:
                    self.logger.info(f"execCommand worked! Text length: {len(content)}")
                    typing_success = True
                else:
                    self.logger.warning(f"execCommand may have failed. Content: {content[:30] if content else 'empty'}")
                    
            except Exception as e:
                self.logger.warning(f"execCommand failed: {e}")
            
            # Method 2: Try clipboard paste if execCommand failed
            if not typing_success:
                try:
                    self.logger.info("Trying clipboard paste...")
                    import tkinter as tk
                    
                    root = tk.Tk()
                    root.withdraw()
                    root.clipboard_clear()
                    root.clipboard_append(message)
                    root.update()
                    root.destroy()
                    
                    human_pause(0.5, 1.0)
                    
                    # Use ActionChains for Ctrl+V
                    actions = ActionChains(self.driver)
                    actions.click(message_input)
                    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL)
                    actions.perform()
                    
                    human_pause(1.5, 2.0)
                    
                    content = self.driver.execute_script(
                        "return arguments[0].textContent || '';", message_input
                    )
                    if len(content) > 20:
                        self.logger.info(f"Clipboard paste worked! Text length: {len(content)}")
                        typing_success = True
                        
                except Exception as e:
                    self.logger.warning(f"Clipboard paste failed: {e}")
            
            # Method 3: If all else fails, type a simple English message
            if not typing_success:
                self.logger.warning("Thai text failed, trying simple English message...")
                try:
                    simple_msg = "Hi! I saw your profile and would love to connect. Can I share some info with you?"
                    message_input.clear()
                    message_input.send_keys(simple_msg)
                    typing_success = True
                    self.logger.info("Typed English fallback message")
                except Exception as e:
                    self.logger.error(f"All typing methods failed: {e}")
                    return False
            
            human_pause(1.0, 2.0)
            
            # Step 5: Send the message
            self.logger.info("Sending message...")
            
            # Try pressing Enter
            try:
                actions = ActionChains(self.driver)
                actions.click(message_input)
                actions.send_keys(Keys.ENTER)
                actions.perform()
                human_pause(2.0, 3.0)
                self.logger.info("Pressed Enter to send")
            except Exception as e:
                self.logger.warning(f"Enter key failed: {e}")
            
            # Also try clicking Send button as backup
            send_btn = None
            send_selectors = [
                (By.XPATH, "//*[@aria-label='Send']"),
                (By.XPATH, "//*[@aria-label='ส่ง']"),
                (By.XPATH, "//div[text()='Send']"),
                (By.XPATH, "//button[text()='Send']"),
            ]
            
            for by, selector in send_selectors:
                try:
                    send_btn = self.driver.find_element(by, selector)
                    if send_btn:
                        break
                except:
                    continue
            
            if send_btn:
                human_pause(0.3, 0.7)
                send_btn.click()
                self.logger.info("Clicked Send button!")
                human_pause(1.5, 3.0)
            
            self.logger.info("DM process completed")
            self.session_stats["dms_sent"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"DM failed: {e}")
            return False
    
    # --------------------------------------------------
    # Helper Methods
    # --------------------------------------------------
    
    def _dismiss_popups(self):
        """Dismiss notification and login popups."""
        popup_selectors = [
            (By.XPATH, self.SELECTORS["not_now_button"]),
            (By.CSS_SELECTOR, "button[class*='_a9--']"),  # Generic dismiss
        ]
        
        for by, selector in popup_selectors:
            try:
                btn = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((by, selector))
                )
                btn.click()
                self.logger.info("Dismissed popup")
                human_pause(0.5, 1.0)
            except (TimeoutException, NoSuchElementException):
                continue
    
    def _close_modal(self):
        """Close any open modal/overlay."""
        try:
            close_btn = self.driver.find_element(
                By.CSS_SELECTOR, self.SELECTORS["close_modal"]
            )
            close_btn.click()
            human_pause(0.5, 1.0)
        except NoSuchElementException:
            # Try pressing Escape
            try:
                from selenium.webdriver.common.keys import Keys
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                human_pause(0.5, 1.0)
            except Exception:
                pass
    
    def _parse_stat(self, text: str) -> int:
        """Parse follower/following counts (handles K, M suffixes)."""
        try:
            # Extract just the number part
            text = text.split()[0].strip().upper().replace(",", "")
            
            if "K" in text:
                return int(float(text.replace("K", "")) * 1000)
            elif "M" in text:
                return int(float(text.replace("M", "")) * 1_000_000)
            else:
                return int(text)
        except (ValueError, IndexError):
            return 0
    
    def get_session_stats(self) -> dict:
        """Get statistics for the current session."""
        return self.session_stats.copy()

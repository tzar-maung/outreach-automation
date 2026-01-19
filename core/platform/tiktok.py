"""
TikTok Platform Adapter

Supports view-only actions for TikTok profiles and videos.
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
    browse_naturally,
)
from outreach_bot.core.element_actions import (
    wait_for_element,
    hover_and_click,
)


class TikTokAdapter(BasePlatformAdapter):
    """
    TikTok-specific adapter.
    
    View-only actions (SAFE):
        - view_profile()
        - view_videos()
        - get_profile_info()
    
    Note: TikTok is aggressive with bot detection.
    Use with extreme caution and realistic delays.
    """
    
    PLATFORM_NAME = "tiktok"
    BASE_URL = "https://www.tiktok.com"
    
    # Selectors (TikTok changes frequently)
    SELECTORS = {
        # Login detection
        "login_button": "[data-e2e='top-login-button']",
        "logged_in_avatar": "[data-e2e='profile-icon']",
        
        # Profile page
        "profile_header": "[data-e2e='user-page']",
        "username": "[data-e2e='user-title']",
        "user_subtitle": "[data-e2e='user-subtitle']",
        "followers_count": "[data-e2e='followers-count']",
        "following_count": "[data-e2e='following-count']",
        "likes_count": "[data-e2e='likes-count']",
        "bio": "[data-e2e='user-bio']",
        
        # Videos
        "video_items": "[data-e2e='user-post-item']",
        "video_link": "[data-e2e='user-post-item'] a",
        
        # Video player
        "video_player": "video",
        "like_button": "[data-e2e='like-icon']",
        "comment_button": "[data-e2e='comment-icon']",
        "share_button": "[data-e2e='share-icon']",
        
        # Follow button
        "follow_button": "[data-e2e='follow-button']",
        
        # Popups
        "captcha_frame": "iframe[src*='captcha']",
        "cookie_banner": "[class*='cookie']",
    }
    
    def __init__(self, driver, logger):
        super().__init__(driver, logger)
        self.session_stats = {
            "profiles_viewed": 0,
            "videos_viewed": 0,
            "follows_sent": 0,
            "likes_sent": 0,
        }
    
    # --------------------------------------------------
    # Core Methods
    # --------------------------------------------------
    
    def open_target(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            self.logger.info(f"Opening: {url}")
            self.driver.get(url)
            human_pause(3.0, 5.0)  # TikTok loads slowly
            self._handle_popups()
            return True
        except Exception as e:
            self.logger.error(f"Failed to open {url}: {e}")
            return False
    
    def perform_actions(self) -> dict:
        """Default action sequence for TikTok profiles."""
        result = {
            "url": self.driver.current_url,
            "platform": self.PLATFORM_NAME,
            "status": "success",
            "actions": [],
            "profile_info": None,
        }
        
        try:
            # 1. Handle any popups
            self._handle_popups()
            
            # 2. Browse naturally
            self.logger.info("Browsing profile naturally...")
            browse_naturally(self.driver, duration_sec=5.0)
            result["actions"].append("browse")
            
            # 3. Extract profile info
            info = self.get_profile_info()
            result["profile_info"] = info
            result["actions"].append("extract_info")
            
            # 4. View some videos
            videos_viewed = self.view_videos(count=2)
            result["actions"].append(f"viewed_{videos_viewed}_videos")
            
            # 5. Cooldown
            cooldown = random.uniform(4.0, 8.0)
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
        """Check if user is logged in to TikTok."""
        try:
            if "tiktok.com" not in self.driver.current_url:
                self.driver.get(self.BASE_URL)
                human_pause(3.0, 4.0)
            
            # Look for profile icon (logged in)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.SELECTORS["logged_in_avatar"])
                    )
                )
                self.logger.info("✓ Logged in to TikTok")
                return True
            except TimeoutException:
                pass
            
            # Look for login button (not logged in)
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["login_button"]
                )
                self.logger.warning("✗ Not logged in to TikTok")
                return False
            except NoSuchElementException:
                return True  # Assume logged in if neither found
                
        except Exception as e:
            self.logger.error(f"Login check failed: {e}")
            return False
    
    # --------------------------------------------------
    # View-Only Actions
    # --------------------------------------------------
    
    def view_profile(self, username: str) -> bool:
        """
        Navigate to and view a user's profile.
        
        Args:
            username: TikTok username (with or without @)
        
        Returns:
            True if profile loaded successfully
        """
        # TikTok usernames use @ in URL
        username = username.lstrip("@").strip()
        profile_url = f"{self.BASE_URL}/@{username}"
        
        if not self.open_target(profile_url):
            return False
        
        try:
            # Wait for profile to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, self.SELECTORS["profile_header"])
                )
            )
            
            browse_naturally(self.driver, duration_sec=4.0)
            
            self.session_stats["profiles_viewed"] += 1
            self.logger.info(f"✓ Viewed profile: @{username}")
            return True
            
        except TimeoutException:
            self.logger.error(f"Profile @{username} did not load")
            return False
    
    def view_videos(self, count: int = 2) -> int:
        """
        View videos on the current profile page.
        
        Args:
            count: Number of videos to view
        
        Returns:
            Number of videos actually viewed
        """
        viewed = 0
        
        try:
            # Scroll to video grid
            human_scroll_pattern(self.driver, rounds=2)
            
            # Find video items
            videos = self.driver.find_elements(
                By.CSS_SELECTOR, self.SELECTORS["video_items"]
            )
            
            if not videos:
                self.logger.info("No videos found on profile")
                return 0
            
            for video in videos[:count]:
                try:
                    # Click video
                    hover_and_click(self.driver, video)
                    
                    # Watch for a bit (simulate viewing)
                    watch_time = random.uniform(5.0, 12.0)
                    self.logger.info(f"Watching video for {watch_time:.1f}s")
                    time.sleep(watch_time)
                    
                    # Go back
                    self.driver.back()
                    human_pause(2.0, 3.0)
                    
                    viewed += 1
                    self.session_stats["videos_viewed"] += 1
                    
                except Exception as e:
                    self.logger.warning(f"Could not view video: {e}")
                    self.driver.back()
                    human_pause(1.0, 2.0)
            
            self.logger.info(f"Viewed {viewed} videos")
            
        except Exception as e:
            self.logger.error(f"Error viewing videos: {e}")
        
        return viewed
    
    def get_profile_info(self) -> dict:
        """Extract profile information from current page."""
        info = {
            "username": None,
            "followers": None,
            "following": None,
            "likes": None,
            "bio": None,
        }
        
        try:
            # Username
            try:
                username_el = self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["username"]
                )
                info["username"] = username_el.text.strip()
            except NoSuchElementException:
                # Get from URL
                url = self.driver.current_url
                if "/@" in url:
                    info["username"] = url.split("/@")[1].split("?")[0].split("/")[0]
            
            # Followers
            try:
                followers_el = self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["followers_count"]
                )
                info["followers"] = self._parse_count(followers_el.text)
            except NoSuchElementException:
                pass
            
            # Following
            try:
                following_el = self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["following_count"]
                )
                info["following"] = self._parse_count(following_el.text)
            except NoSuchElementException:
                pass
            
            # Likes
            try:
                likes_el = self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["likes_count"]
                )
                info["likes"] = self._parse_count(likes_el.text)
            except NoSuchElementException:
                pass
            
            # Bio
            try:
                bio_el = self.driver.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["bio"]
                )
                info["bio"] = bio_el.text.strip()[:200]  # Truncate
            except NoSuchElementException:
                pass
            
            self.logger.info(f"Profile info: {info}")
            
        except Exception as e:
            self.logger.error(f"Failed to extract profile info: {e}")
        
        return info
    
    # --------------------------------------------------
    # Outreach Actions (USE WITH CAUTION)
    # --------------------------------------------------
    
    def follow_user(self) -> bool:
        """Follow the user on the current profile page."""
        try:
            follow_btn = wait_for_element(
                self.driver,
                By.CSS_SELECTOR,
                self.SELECTORS["follow_button"],
                timeout=5
            )
            
            if follow_btn and "Follow" in follow_btn.text:
                hover_and_click(self.driver, follow_btn)
                self.session_stats["follows_sent"] += 1
                self.logger.info("✓ Followed user")
                return True
            else:
                self.logger.info("Follow button not found or already following")
                return False
                
        except Exception as e:
            self.logger.error(f"Follow failed: {e}")
            return False
    
    # --------------------------------------------------
    # Helper Methods
    # --------------------------------------------------
    
    def _handle_popups(self):
        """Handle cookie banners and other popups."""
        try:
            # Cookie banner
            cookie_btn = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), 'Accept')]"
            )
            if cookie_btn:
                cookie_btn[0].click()
                human_pause(0.5, 1.0)
        except Exception:
            pass
        
        # Check for captcha (warn user)
        try:
            captcha = self.driver.find_elements(
                By.CSS_SELECTOR, self.SELECTORS["captcha_frame"]
            )
            if captcha:
                self.logger.warning("⚠️ CAPTCHA detected! Manual intervention needed.")
        except Exception:
            pass
    
    def _parse_count(self, text: str) -> int:
        """Parse counts (handles K, M suffixes)."""
        try:
            text = text.strip().upper().replace(",", "")
            
            if "K" in text:
                return int(float(text.replace("K", "")) * 1000)
            elif "M" in text:
                return int(float(text.replace("M", "")) * 1_000_000)
            elif "B" in text:
                return int(float(text.replace("B", "")) * 1_000_000_000)
            else:
                return int(text)
        except (ValueError, IndexError):
            return 0
    
    def get_session_stats(self) -> dict:
        """Get statistics for the current session."""
        return self.session_stats.copy()

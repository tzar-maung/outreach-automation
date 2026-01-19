"""
CAPTCHA Detection and Handling

Features:
- Detect various CAPTCHA types
- Auto-pause for manual solving
- Optional 2Captcha integration
"""
import time
import os
from typing import Optional, Tuple, Callable
from enum import Enum

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class CaptchaType(Enum):
    NONE = "none"
    RECAPTCHA = "recaptcha"
    HCAPTCHA = "hcaptcha"
    INSTAGRAM_CHALLENGE = "instagram_challenge"
    INSTAGRAM_BLOCKED = "instagram_blocked"
    TIKTOK_CAPTCHA = "tiktok_captcha"


class CaptchaHandler:
    """Detect and handle CAPTCHAs and verification challenges."""
    
    DETECTION_SELECTORS = {
        "recaptcha": "iframe[src*='recaptcha']",
        "hcaptcha": "iframe[src*='hcaptcha']",
        "ig_challenge": "form[action*='challenge']",
        "ig_blocked": "//*[contains(text(), 'Action Blocked')]",
        "ig_try_again": "//*[contains(text(), 'Try Again Later')]",
        "tt_slider": ".secsdk-captcha-drag-icon",
    }
    
    CHALLENGE_PATTERNS = [
        "action blocked", "try again later", "verify it's you",
        "confirm your identity", "suspicious activity", "we limit how often",
    ]
    
    def __init__(self, driver, logger, mode: str = "manual",
                 api_key: str = None, timeout: int = 300):
        self.driver = driver
        self.logger = logger
        self.mode = mode
        self.api_key = api_key or os.environ.get("CAPTCHA_API_KEY")
        self.timeout = timeout
        self.stats = {"detected": 0, "solved": 0, "failed": 0}
    
    def detect_captcha(self) -> Tuple[bool, CaptchaType]:
        """Detect if a CAPTCHA or challenge is present."""
        # reCAPTCHA
        if self._element_exists(self.DETECTION_SELECTORS["recaptcha"]):
            self.stats["detected"] += 1
            return True, CaptchaType.RECAPTCHA
        
        # hCaptcha
        if self._element_exists(self.DETECTION_SELECTORS["hcaptcha"]):
            self.stats["detected"] += 1
            return True, CaptchaType.HCAPTCHA
        
        # Instagram blocked
        if self._element_exists(self.DETECTION_SELECTORS["ig_blocked"]) or \
           self._element_exists(self.DETECTION_SELECTORS["ig_try_again"]):
            self.stats["detected"] += 1
            return True, CaptchaType.INSTAGRAM_BLOCKED
        
        # Instagram challenge
        if self._element_exists(self.DETECTION_SELECTORS["ig_challenge"]):
            self.stats["detected"] += 1
            return True, CaptchaType.INSTAGRAM_CHALLENGE
        
        # TikTok
        if self._element_exists(self.DETECTION_SELECTORS["tt_slider"]):
            self.stats["detected"] += 1
            return True, CaptchaType.TIKTOK_CAPTCHA
        
        # Check page text
        if self._check_page_text():
            self.stats["detected"] += 1
            return True, CaptchaType.INSTAGRAM_BLOCKED
        
        return False, CaptchaType.NONE
    
    def _element_exists(self, selector: str, timeout: float = 2) -> bool:
        try:
            by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return True
        except TimeoutException:
            return False
    
    def _check_page_text(self) -> bool:
        try:
            page_text = self.driver.page_source.lower()
            return any(p in page_text for p in self.CHALLENGE_PATTERNS)
        except Exception:
            return False
    
    def handle_captcha(self, captcha_type: CaptchaType = None) -> bool:
        """Handle a detected CAPTCHA."""
        if captcha_type is None:
            detected, captcha_type = self.detect_captcha()
            if not detected:
                return True
        
        self.logger.warning(f"🔒 Handling {captcha_type.value}...")
        
        if self.mode == "skip":
            self.stats["failed"] += 1
            return False
        
        solved = self._solve_manual(captcha_type)
        
        if solved:
            self.stats["solved"] += 1
        else:
            self.stats["failed"] += 1
        
        return solved
    
    def _solve_manual(self, captcha_type: CaptchaType) -> bool:
        """Wait for user to manually solve."""
        self.logger.info("=" * 50)
        self.logger.info("⚠️  CAPTCHA/CHALLENGE DETECTED")
        self.logger.info("=" * 50)
        self.logger.info(f"Type: {captcha_type.value}")
        self.logger.info(f"URL: {self.driver.current_url}")
        self.logger.info("")
        self.logger.info("Please solve in the browser window.")
        self.logger.info("Press ENTER when done (or 'skip')...")
        self.logger.info("=" * 50)
        
        print("\a")  # Beep
        
        try:
            user_input = input()
            if user_input.lower() == 'skip':
                return False
        except Exception:
            return False
        
        time.sleep(2)
        still_present, _ = self.detect_captcha()
        
        if still_present:
            self.logger.warning("Challenge still present")
            return False
        
        self.logger.info("✅ Challenge cleared!")
        return True
    
    def get_stats(self) -> dict:
        return dict(self.stats)
    
    def print_stats(self):
        """Print CAPTCHA statistics."""
        print(f"\n{'='*40}")
        print("CAPTCHA Statistics")
        print(f"{'='*40}")
        print(f"Detected: {self.stats['detected']}")
        print(f"Solved: {self.stats['solved']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"{'='*40}\n")


def check_and_handle_captcha(driver, logger, mode: str = "manual") -> bool:
    """Quick function to check and handle CAPTCHA."""
    handler = CaptchaHandler(driver, logger, mode=mode)
    detected, captcha_type = handler.detect_captcha()
    if detected:
        return handler.handle_captcha(captcha_type)
    return True

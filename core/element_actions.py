"""
Element interaction helpers with human-like behavior.
"""
import time
import random

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from outreach_bot.core.human_behavior import (
    human_pause,
    human_mouse_move,
    human_scroll_pattern
)


# --------------------------------------------------
# Wait for element
# --------------------------------------------------

def wait_for_element(driver, by, selector, timeout=10):
    """
    Wait for an element to be present on the page.
    
    Args:
        driver: WebDriver instance
        by: Locator type (By.CSS_SELECTOR, By.XPATH, etc.)
        selector: Element selector
        timeout: Max wait time in seconds
    
    Returns:
        Element if found, None otherwise
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
    except TimeoutException:
        return None


# --------------------------------------------------
# Scroll until element is visible
# --------------------------------------------------

def scroll_until_visible(driver, by, selector, max_attempts=6):
    """
    Scroll the page until an element becomes visible.
    
    Args:
        driver: WebDriver instance
        by: Locator type
        selector: Element selector
        max_attempts: Maximum scroll attempts
    
    Returns:
        Element if found and visible, None otherwise
    """
    for _ in range(max_attempts):
        element = wait_for_element(driver, by, selector, timeout=3)

        if element and element.is_displayed():
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                element
            )
            human_pause(0.8, 1.4)
            return element

        human_scroll_pattern(driver, rounds=1)

    return None


# --------------------------------------------------
# Human-like hover + click
# --------------------------------------------------

def hover_and_click(driver, element):
    """
    Move mouse to element and click with human-like behavior.
    
    Args:
        driver: WebDriver instance
        element: Element to click
    
    Returns:
        True if click successful, False otherwise
    """
    if not element:
        return False

    try:
        human_mouse_move(driver, element)
        human_pause(0.4, 0.9)
        element.click()
        human_pause(1.0, 2.0)
        return True

    except Exception:
        return False


# --------------------------------------------------
# Prevent duplicate actions
# --------------------------------------------------

class ActionMemory:
    """Track completed actions to prevent duplicates."""
    
    def __init__(self):
        self._seen = set()

    def already_done(self, key):
        """Check if action was already performed."""
        return key in self._seen

    def mark_done(self, key):
        """Mark action as completed."""
        self._seen.add(key)
    
    def reset(self):
        """Clear all tracked actions."""
        self._seen.clear()

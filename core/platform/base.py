"""
Base platform adapter - abstract class for all platform-specific adapters.
"""
from abc import ABC, abstractmethod


class BasePlatformAdapter(ABC):
    """
    Abstract base class for platform-specific adapters.
    
    All platform adapters (Instagram, TikTok, etc.) should inherit
    from this and implement the abstract methods.
    """
    
    PLATFORM_NAME = "base"
    BASE_URL = ""
    
    def __init__(self, driver, logger):
        """
        Initialize the adapter.
        
        Args:
            driver: Selenium WebDriver instance
            logger: Logger instance
        """
        self.driver = driver
        self.logger = logger

    @abstractmethod
    def open_target(self, url: str):
        """
        Navigate to a target URL.
        
        Args:
            url: URL to navigate to
        
        Returns:
            True if navigation successful
        """
        pass

    @abstractmethod
    def perform_actions(self):
        """
        Perform platform-specific actions on the current page.
        
        Returns:
            Dictionary with action results
        """
        pass
    
    def get_current_url(self) -> str:
        """Get the current page URL."""
        return self.driver.current_url
    
    def take_screenshot(self, filepath: str) -> bool:
        """
        Take a screenshot of the current page.
        
        Args:
            filepath: Path to save screenshot
        
        Returns:
            True if successful
        """
        try:
            self.driver.save_screenshot(filepath)
            return True
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return False

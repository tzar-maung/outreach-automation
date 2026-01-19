"""
Generic web adapter for basic web browsing automation.
"""
import time
from outreach_bot.core.platform.base import BasePlatformAdapter
from outreach_bot.core.human_behavior import human_scroll, browse_naturally


class GenericWebAdapter(BasePlatformAdapter):
    """
    Generic adapter for basic web browsing.
    
    Used for testing and as a fallback for non-specific platforms.
    """
    
    PLATFORM_NAME = "generic_web"
    BASE_URL = ""
    
    def open_target(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            self.logger.info(f"Opening: {url}")
            self.driver.get(url)
            time.sleep(3)
            return True
        except Exception as e:
            self.logger.error(f"Failed to open {url}: {e}")
            return False

    def perform_actions(self) -> dict:
        """Perform generic browsing actions."""
        result = {
            "url": self.driver.current_url,
            "platform": self.PLATFORM_NAME,
            "status": "success",
            "actions": [],
        }
        
        try:
            # Natural browsing
            self.logger.info("Browsing naturally...")
            browse_naturally(self.driver, duration_sec=6.0)
            result["actions"].append("browse")
            
            # Scroll the page
            self.logger.info("Scrolling page...")
            human_scroll(self.driver, scroll_count=3)
            result["actions"].append("scroll")
            
            self.logger.info("Actions completed")
            
        except Exception as e:
            self.logger.error(f"Action error: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    def extract_text(self) -> str:
        """Extract visible text from the current page."""
        try:
            body = self.driver.find_element("tag name", "body")
            return body.text
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            return ""
    
    def get_links(self) -> list:
        """Get all links on the current page."""
        try:
            links = self.driver.find_elements("tag name", "a")
            hrefs = [
                link.get_attribute("href") 
                for link in links 
                if link.get_attribute("href")
            ]
            return hrefs
        except Exception as e:
            self.logger.error(f"Link extraction failed: {e}")
            return []

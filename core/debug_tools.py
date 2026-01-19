"""
Debug Tools - Error Screenshots, Page Saving, and Diagnostics

Production-ready debugging tools:
- Automatic screenshot on error
- Save page source for analysis
- Network request logging
- Console error capture
- Debug report generation

Usage:
    debugger = DebugTools(driver, logger)
    
    try:
        # do something
    except Exception as e:
        debugger.capture_error(e, "action_name")
"""
import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ErrorReport:
    """Structured error report."""
    timestamp: str
    error_type: str
    error_message: str
    action: str
    url: str
    screenshot_path: Optional[str] = None
    page_source_path: Optional[str] = None
    console_logs: List[str] = field(default_factory=list)
    network_errors: List[str] = field(default_factory=list)
    stack_trace: str = ""
    selector_attempted: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


class DebugTools:
    """
    Production debugging tools for browser automation.
    
    Features:
    - Automatic screenshots on error
    - Page source saving
    - Console log capture
    - Network error detection
    - Structured error reports
    """
    
    def __init__(self, driver, logger, output_dir: str = "debug"):
        """
        Initialize debug tools.
        
        Args:
            driver: Selenium WebDriver
            logger: Logger instance
            output_dir: Directory for debug output
        """
        self.driver = driver
        self.logger = logger
        self.output_dir = Path(output_dir)
        
        # Create subdirectories
        self.screenshots_dir = self.output_dir / "screenshots"
        self.pages_dir = self.output_dir / "pages"
        self.reports_dir = self.output_dir / "reports"
        
        for dir_path in [self.screenshots_dir, self.pages_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Error history
        self.error_history: List[ErrorReport] = []
        self.max_history = 100
    
    # --------------------------------------------------
    # Screenshot Capture
    # --------------------------------------------------
    
    def take_screenshot(self, name: str = None) -> Optional[str]:
        """
        Take a screenshot of the current page.
        
        Args:
            name: Optional name for the screenshot
        
        Returns:
            Path to screenshot file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{name}_{timestamp}.png" if name else f"screenshot_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            self.driver.save_screenshot(str(filepath))
            self.logger.info(f"📸 Screenshot saved: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def take_element_screenshot(self, element, name: str = None) -> Optional[str]:
        """Take a screenshot of a specific element."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"element_{name}_{timestamp}.png" if name else f"element_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            element.screenshot(str(filepath))
            self.logger.info(f"📸 Element screenshot saved: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to take element screenshot: {e}")
            return None
    
    # --------------------------------------------------
    # Page Source Saving
    # --------------------------------------------------
    
    def save_page_source(self, name: str = None) -> Optional[str]:
        """
        Save the current page's HTML source.
        
        Args:
            name: Optional name for the file
        
        Returns:
            Path to saved file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{name}_{timestamp}.html" if name else f"page_{timestamp}.html"
            filepath = self.pages_dir / filename
            
            page_source = self.driver.page_source
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(page_source)
            
            self.logger.info(f"📄 Page source saved: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save page source: {e}")
            return None
    
    # --------------------------------------------------
    # Console & Network Logs
    # --------------------------------------------------
    
    def get_console_logs(self) -> List[str]:
        """Get browser console logs."""
        try:
            logs = self.driver.get_log("browser")
            return [
                f"[{log['level']}] {log['message']}" 
                for log in logs
            ]
        except Exception:
            return []
    
    def get_network_errors(self) -> List[str]:
        """Get network errors from performance logs."""
        try:
            logs = self.driver.get_log("performance")
            errors = []
            
            for log in logs:
                try:
                    message = json.loads(log["message"])
                    if "Network.responseReceived" in str(message):
                        response = message.get("message", {}).get("params", {}).get("response", {})
                        status = response.get("status", 200)
                        url = response.get("url", "")
                        
                        if status >= 400:
                            errors.append(f"HTTP {status}: {url[:100]}")
                except Exception:
                    continue
            
            return errors
            
        except Exception:
            return []
    
    # --------------------------------------------------
    # Error Capture
    # --------------------------------------------------
    
    def capture_error(self, error: Exception, action: str,
                      selector: str = None, extra_info: Dict = None) -> ErrorReport:
        """
        Capture comprehensive error information.
        
        Args:
            error: The exception that occurred
            action: What action was being performed
            selector: CSS/XPath selector that failed (if applicable)
            extra_info: Additional context information
        
        Returns:
            ErrorReport with all captured data
        """
        self.logger.error(f"🔴 Capturing error during '{action}': {error}")
        
        # Get current URL safely
        try:
            current_url = self.driver.current_url
        except Exception:
            current_url = "unknown"
        
        # Take screenshot
        screenshot_path = self.take_screenshot(f"error_{action}")
        
        # Save page source
        page_source_path = self.save_page_source(f"error_{action}")
        
        # Get console logs
        console_logs = self.get_console_logs()
        
        # Get network errors
        network_errors = self.get_network_errors()
        
        # Create error report
        report = ErrorReport(
            timestamp=datetime.now().isoformat(),
            error_type=type(error).__name__,
            error_message=str(error),
            action=action,
            url=current_url,
            screenshot_path=screenshot_path,
            page_source_path=page_source_path,
            console_logs=console_logs[-20:],  # Last 20 logs
            network_errors=network_errors[-10:],  # Last 10 errors
            stack_trace=traceback.format_exc(),
            selector_attempted=selector,
            additional_info=extra_info or {},
        )
        
        # Save report
        self._save_report(report, action)
        
        # Add to history
        self.error_history.append(report)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        return report
    
    def _save_report(self, report: ErrorReport, name: str):
        """Save error report as JSON."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"error_report_{name}_{timestamp}.json"
            filepath = self.reports_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2, default=str)
            
            self.logger.info(f"📋 Error report saved: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save error report: {e}")
    
    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """
        Run comprehensive diagnostics on current state.
        
        Returns:
            Dictionary with diagnostic information
        """
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "url": None,
            "title": None,
            "page_loaded": False,
            "cookies_count": 0,
            "local_storage_available": False,
            "viewport_size": None,
            "user_agent": None,
            "console_errors": [],
            "network_errors": [],
        }
        
        try:
            diagnostics["url"] = self.driver.current_url
            diagnostics["title"] = self.driver.title
            diagnostics["page_loaded"] = True
        except Exception:
            pass
        
        try:
            diagnostics["cookies_count"] = len(self.driver.get_cookies())
        except Exception:
            pass
        
        try:
            diagnostics["local_storage_available"] = self.driver.execute_script(
                "return typeof(Storage) !== 'undefined';"
            )
        except Exception:
            pass
        
        try:
            diagnostics["viewport_size"] = {
                "width": self.driver.execute_script("return window.innerWidth;"),
                "height": self.driver.execute_script("return window.innerHeight;"),
            }
        except Exception:
            pass
        
        try:
            diagnostics["user_agent"] = self.driver.execute_script(
                "return navigator.userAgent;"
            )
        except Exception:
            pass
        
        diagnostics["console_errors"] = [
            log for log in self.get_console_logs()
            if "ERROR" in log.upper()
        ]
        
        diagnostics["network_errors"] = self.get_network_errors()
        
        return diagnostics
    
    def print_diagnostics(self):
        """Print formatted diagnostics."""
        diag = self.run_diagnostics()
        
        print(f"\n{'='*60}")
        print("🔍 DIAGNOSTICS")
        print(f"{'='*60}")
        print(f"Time: {diag['timestamp']}")
        print(f"URL: {diag['url']}")
        print(f"Title: {diag['title']}")
        print(f"Page Loaded: {diag['page_loaded']}")
        print(f"Cookies: {diag['cookies_count']}")
        print(f"Viewport: {diag['viewport_size']}")
        
        if diag['console_errors']:
            print(f"\n⚠️ Console Errors ({len(diag['console_errors'])}):")
            for err in diag['console_errors'][:5]:
                print(f"  • {err[:100]}")
        
        if diag['network_errors']:
            print(f"\n⚠️ Network Errors ({len(diag['network_errors'])}):")
            for err in diag['network_errors'][:5]:
                print(f"  • {err}")
        
        print(f"{'='*60}\n")
    
    # --------------------------------------------------
    # Element Debugging
    # --------------------------------------------------
    
    def find_similar_elements(self, partial_text: str = None,
                              tag_name: str = None,
                              class_contains: str = None) -> List[Dict]:
        """
        Find elements that might match what you're looking for.
        Useful when selectors are broken.
        
        Args:
            partial_text: Text contained in element
            tag_name: HTML tag name
            class_contains: Partial class name
        
        Returns:
            List of matching elements with their info
        """
        results = []
        
        try:
            if partial_text:
                elements = self.driver.find_elements(
                    "xpath", 
                    f"//*[contains(text(), '{partial_text}')]"
                )
                for el in elements[:10]:
                    results.append(self._get_element_info(el))
            
            if tag_name:
                elements = self.driver.find_elements("tag name", tag_name)
                for el in elements[:20]:
                    results.append(self._get_element_info(el))
            
            if class_contains:
                elements = self.driver.find_elements(
                    "xpath",
                    f"//*[contains(@class, '{class_contains}')]"
                )
                for el in elements[:10]:
                    results.append(self._get_element_info(el))
                    
        except Exception as e:
            self.logger.error(f"Error finding elements: {e}")
        
        return results
    
    def _get_element_info(self, element) -> Dict:
        """Get detailed info about an element."""
        try:
            return {
                "tag": element.tag_name,
                "text": element.text[:100] if element.text else "",
                "class": element.get_attribute("class"),
                "id": element.get_attribute("id"),
                "href": element.get_attribute("href"),
                "aria_label": element.get_attribute("aria-label"),
                "data_testid": element.get_attribute("data-testid"),
                "is_displayed": element.is_displayed(),
                "location": element.location,
                "size": element.size,
            }
        except Exception:
            return {}
    
    def highlight_element(self, element, color: str = "red", duration: float = 2.0):
        """
        Highlight an element on the page (useful for debugging).
        
        Args:
            element: Element to highlight
            color: Border color
            duration: How long to show highlight
        """
        try:
            original_style = element.get_attribute("style")
            
            self.driver.execute_script(
                f"arguments[0].style.border='3px solid {color}';",
                element
            )
            
            import time
            time.sleep(duration)
            
            self.driver.execute_script(
                f"arguments[0].style.border='{original_style or ''}';",
                element
            )
            
        except Exception as e:
            self.logger.error(f"Could not highlight element: {e}")
    
    # --------------------------------------------------
    # Summary Reports
    # --------------------------------------------------
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors in this session."""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_types = {}
        actions_failed = {}
        
        for report in self.error_history:
            # Count by error type
            error_types[report.error_type] = error_types.get(report.error_type, 0) + 1
            
            # Count by action
            actions_failed[report.action] = actions_failed.get(report.action, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "actions_failed": actions_failed,
            "latest_error": self.error_history[-1].timestamp if self.error_history else None,
            "screenshots": [
                r.screenshot_path for r in self.error_history 
                if r.screenshot_path
            ],
        }
    
    def print_error_summary(self):
        """Print formatted error summary."""
        summary = self.get_error_summary()
        
        print(f"\n{'='*60}")
        print("📊 ERROR SUMMARY")
        print(f"{'='*60}")
        print(f"Total Errors: {summary['total_errors']}")
        
        if summary.get('error_types'):
            print("\nBy Error Type:")
            for error_type, count in summary['error_types'].items():
                print(f"  • {error_type}: {count}")
        
        if summary.get('actions_failed'):
            print("\nBy Action:")
            for action, count in summary['actions_failed'].items():
                print(f"  • {action}: {count}")
        
        print(f"{'='*60}\n")


# --------------------------------------------------
# Decorator for automatic error capture
# --------------------------------------------------

def capture_errors(debug_tools: DebugTools, action_name: str):
    """
    Decorator to automatically capture errors.
    
    Usage:
        @capture_errors(debugger, "click_follow")
        def click_follow_button():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                debug_tools.capture_error(e, action_name)
                raise
        return wrapper
    return decorator

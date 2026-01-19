"""
Debug Utilities - Screenshots, Error Logging, and Debug Mode

Features:
- Automatic screenshots on errors
- Page source capture for debugging
- Detailed error logging with context
- Debug mode for development
- Performance timing
"""
import os
import time
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Callable
from functools import wraps
from contextlib import contextmanager


class DebugHelper:
    """
    Debug utilities for browser automation.
    
    Captures screenshots, page source, and detailed error logs
    to help identify and fix issues quickly.
    """
    
    def __init__(self, driver, logger, 
                 debug_dir: str = "debug",
                 enabled: bool = True):
        self.driver = driver
        self.logger = logger
        self.enabled = enabled
        
        # Setup directories
        self.debug_dir = Path(debug_dir)
        self.screenshots_dir = self.debug_dir / "screenshots"
        self.html_dir = self.debug_dir / "html"
        self.logs_dir = self.debug_dir / "error_logs"
        
        self._ensure_directories()
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.error_count = 0
        self.screenshot_count = 0
        self.timings: Dict[str, float] = {}
    
    def _ensure_directories(self):
        """Create debug directories if they don't exist."""
        for dir_path in [self.screenshots_dir, self.html_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generate a unique filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}_{self.session_id}.{extension}"
    
    def screenshot(self, name: str = "screenshot", 
                   include_html: bool = False) -> Optional[str]:
        """Take a screenshot of current page."""
        if not self.enabled:
            return None
        
        try:
            self.screenshot_count += 1
            filename = self._generate_filename(f"{name}_{self.screenshot_count:03d}", "png")
            filepath = self.screenshots_dir / filename
            
            self.driver.save_screenshot(str(filepath))
            self.logger.debug(f"📸 Screenshot saved: {filepath}")
            
            if include_html:
                self.save_page_source(f"{name}_{self.screenshot_count:03d}")
            
            return str(filepath)
            
        except Exception as e:
            self.logger.warning(f"Failed to take screenshot: {e}")
            return None
    
    def save_page_source(self, name: str = "page") -> Optional[str]:
        """Save current page HTML source."""
        if not self.enabled:
            return None
        
        try:
            filename = self._generate_filename(name, "html")
            filepath = self.html_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            self.logger.debug(f"📄 Page source saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.warning(f"Failed to save page source: {e}")
            return None
    
    def capture_error(self, error: Exception, context: str = "unknown",
                      extra_data: Dict = None) -> Dict:
        """Capture comprehensive error information."""
        self.error_count += 1
        timestamp = datetime.now()
        
        # Capture files
        screenshot_path = self.screenshot(f"error_{context}", include_html=True)
        
        # Build error report
        error_report = {
            "timestamp": timestamp.isoformat(),
            "session_id": self.session_id,
            "error_number": self.error_count,
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "url": self._safe_get_url(),
            "title": self._safe_get_title(),
            "screenshot": screenshot_path,
            "extra_data": extra_data or {},
        }
        
        # Save error report
        report_filename = self._generate_filename(f"error_{context}", "json")
        report_path = self.logs_dir / report_filename
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(error_report, f, indent=2, default=str)
        
        self.logger.error(f"❌ Error captured: {report_path}")
        self.logger.error(f"   Context: {context}")
        self.logger.error(f"   Error: {error}")
        
        return {"report": str(report_path), "screenshot": screenshot_path}
    
    def _safe_get_url(self) -> str:
        try:
            return self.driver.current_url
        except Exception:
            return "unknown"
    
    def _safe_get_title(self) -> str:
        try:
            return self.driver.title
        except Exception:
            return "unknown"
    
    @contextmanager
    def timed_action(self, name: str):
        """Context manager to time an action."""
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            self.timings[name] = elapsed
            self.logger.debug(f"⏱️ {name}: {elapsed:.2f}s")
    
    def capture_on_error(self, context: str = None):
        """Decorator to automatically capture errors."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                action_context = context or func.__name__
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.capture_error(e, action_context)
                    raise
            return wrapper
        return decorator
    
    def get_session_summary(self) -> Dict:
        """Get summary of debug session."""
        return {
            "session_id": self.session_id,
            "screenshots_taken": self.screenshot_count,
            "errors_captured": self.error_count,
            "timings": self.timings,
            "debug_dir": str(self.debug_dir),
        }
    
    def print_session_summary(self):
        """Print formatted session summary."""
        summary = self.get_session_summary()
        
        print(f"\n{'='*50}")
        print("DEBUG SESSION SUMMARY")
        print(f"{'='*50}")
        print(f"Session ID: {summary['session_id']}")
        print(f"Screenshots: {summary['screenshots_taken']}")
        print(f"Errors: {summary['errors_captured']}")
        print(f"Debug Dir: {summary['debug_dir']}")
        
        if summary['timings']:
            print(f"\nTimings:")
            for name, duration in summary['timings'].items():
                print(f"  {name}: {duration:.2f}s")
        
        print(f"{'='*50}\n")

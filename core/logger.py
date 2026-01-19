"""
Logging configuration for the outreach bot.
"""
import logging
import sys
import io
from datetime import datetime
import os


class SafeStreamHandler(logging.StreamHandler):
    """
    A StreamHandler that safely handles Unicode characters on Windows.
    Falls back to ASCII representation if encoding fails.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                # Fallback: replace non-ASCII characters
                safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logger(name="bot"):
    """
    Set up a logger with file and console output.
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger instance
    """
    os.makedirs("logs", exist_ok=True)

    log_filename = datetime.now().strftime("logs/%Y-%m-%d.log")

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Format
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    # File handler (UTF-8 for Thai characters)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (safe for Windows)
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

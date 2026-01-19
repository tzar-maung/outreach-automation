"""
Message sending functionality with mock/real modes.
"""
import time
from outreach_bot.core.typing_simulator import human_type
from outreach_bot.core.human_behavior import human_pause


class Messenger:
    """
    Handle sending messages with mock or real mode.
    
    Use mock mode for testing without actually sending messages.
    """
    
    def __init__(self, mode="mock"):
        """
        Initialize messenger.
        
        Args:
            mode: 'mock' (don't send) or 'real' (actually send)
        """
        self.mode = mode
        self.messages_sent = 0

    def send(self, input_element, message, logger):
        """
        Send a message to an input element.
        
        Args:
            input_element: Text input element
            message: Message to send
            logger: Logger instance
        
        Returns:
            True if successful
        """
        logger.info(f"Prepared message: {message}")

        human_pause(1, 2)

        if self.mode == "mock":
            logger.info("MOCK MODE: message not sent")
            return True

        try:
            human_type(input_element, message)
            human_pause(0.8, 1.5)
            input_element.submit()
            self.messages_sent += 1
            logger.info("Message sent")
            return True
        except Exception as e:
            logger.error(f"Message failed: {e}")
            return False
    
    def get_stats(self):
        """Get messaging statistics."""
        return {
            "mode": self.mode,
            "messages_sent": self.messages_sent,
        }

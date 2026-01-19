"""
Human-like typing simulation.
"""
import time
import random


def human_type(element, text):
    """
    Type text character by character like a human.
    
    Args:
        element: Input element to type into
        text: Text to type
    """
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))
        
        # Occasionally pause longer (thinking)
        if random.random() < 0.05:
            time.sleep(random.uniform(0.3, 0.6))

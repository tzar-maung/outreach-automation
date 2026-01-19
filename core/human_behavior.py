"""
Human-like behavior simulation to avoid bot detection.
All functions used by element_actions.py are defined here.

Enhanced with realistic scrolling, mouse movements, and browsing patterns.
"""
import random
import time
import math

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


# --------------------------------------------------
# Delays and Pauses
# --------------------------------------------------

def human_pause(min_sec=1.0, max_sec=2.0):
    """Random pause to simulate human thinking/reading."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def human_sleep(min_sec=1.0, max_sec=3.0):
    """Alias for human_pause (backward compatibility)."""
    human_pause(min_sec, max_sec)


def reading_pause(text_length: int = 100):
    """Pause based on text length (simulates reading speed)."""
    # Average reading speed: 200-300 words per minute
    # Assume 5 characters per word
    words = text_length / 5
    reading_time = words / 4  # 4 words per second (fast scanner)
    reading_time = min(reading_time, 8)  # Cap at 8 seconds
    reading_time = max(reading_time, 1)  # Minimum 1 second
    
    # Add randomness
    actual_time = reading_time * random.uniform(0.8, 1.3)
    time.sleep(actual_time)


def distraction_pause():
    """Occasional longer pause (checking phone, thinking, etc.)"""
    if random.random() < 0.1:  # 10% chance
        time.sleep(random.uniform(3, 8))


# --------------------------------------------------
# Scrolling
# --------------------------------------------------

def human_scroll(driver, scroll_count=5, pause=1.2):
    """Scroll down the page multiple times with random amounts."""
    for _ in range(scroll_count):
        scroll_by = random.randint(300, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_by});")
        time.sleep(pause + random.uniform(0.2, 0.6))


def smooth_scroll(driver, distance: int, duration: float = 1.0):
    """Smooth scroll animation like a real human."""
    steps = int(duration * 20)  # 20 steps per second
    step_distance = distance / steps
    
    for _ in range(steps):
        # Add slight randomness to each step
        actual_step = step_distance * random.uniform(0.8, 1.2)
        driver.execute_script(f"window.scrollBy(0, {actual_step});")
        time.sleep(duration / steps)


def human_scroll_pattern(driver, rounds=3):
    """
    Scroll with a natural pattern: mostly down, occasionally up.
    Simulates a real user scanning a page.
    """
    for i in range(rounds):
        # Scroll down (80% of the time)
        if random.random() < 0.8:
            scroll_amount = random.randint(200, 500)
        else:
            # Scroll up occasionally (re-reading something)
            scroll_amount = random.randint(-200, -50)
        
        # Use smooth scroll sometimes
        if random.random() < 0.5:
            smooth_scroll(driver, scroll_amount, random.uniform(0.3, 0.8))
        else:
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        human_pause(0.8, 1.5)
        
        # Sometimes pause longer (reading content)
        if random.random() < 0.3:
            human_pause(1.5, 3.0)
        
        # Occasionally have a distraction
        distraction_pause()


def scroll_to_element(driver, element):
    """Scroll element into view with smooth behavior."""
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        element
    )
    human_pause(0.5, 1.0)


def scroll_to_bottom(driver, speed: str = "medium"):
    """Scroll to page bottom like a human scanning content."""
    speeds = {
        "slow": (300, 500, 1.5, 2.5),
        "medium": (400, 700, 0.8, 1.5),
        "fast": (600, 1000, 0.4, 0.8),
    }
    min_scroll, max_scroll, min_pause, max_pause = speeds.get(speed, speeds["medium"])
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # Scroll down
        scroll_amount = random.randint(min_scroll, max_scroll)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        human_pause(min_pause, max_pause)
        
        # Check if reached bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        current_pos = driver.execute_script("return window.pageYOffset + window.innerHeight")
        
        if current_pos >= new_height - 10:
            break
        
        # Occasionally scroll up a bit
        if random.random() < 0.15:
            driver.execute_script(f"window.scrollBy(0, {-random.randint(100, 200)});")
            human_pause(0.5, 1.0)


# --------------------------------------------------
# Mouse Movement
# --------------------------------------------------

def human_mouse_move(driver, element):
    """
    Move mouse to element with human-like motion.
    Includes small random offset to avoid exact center clicks.
    """
    try:
        actions = ActionChains(driver)
        
        # Move to element with small random offset
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        actions.perform()
        
        human_pause(0.2, 0.5)
        
    except Exception:
        # Fallback: just move to element center
        try:
            actions = ActionChains(driver)
            actions.move_to_element(element)
            actions.perform()
        except Exception:
            pass


def bezier_mouse_move(driver, start_x, start_y, end_x, end_y, steps=20):
    """
    Move mouse in a curved path (Bezier curve) like a human.
    Humans don't move mouse in straight lines.
    """
    try:
        # Generate control points for curve
        ctrl_x = (start_x + end_x) / 2 + random.randint(-50, 50)
        ctrl_y = (start_y + end_y) / 2 + random.randint(-50, 50)
        
        actions = ActionChains(driver)
        
        for i in range(steps + 1):
            t = i / steps
            
            # Quadratic Bezier curve
            x = (1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * end_x
            y = (1-t)**2 * start_y + 2*(1-t)*t * ctrl_y + t**2 * end_y
            
            # Move relative from current position
            if i == 0:
                actions.move_by_offset(int(x - start_x), int(y - start_y))
            
        actions.perform()
        
    except Exception:
        pass


def random_mouse_movement(driver):
    """
    Perform random mouse movements to appear more human.
    Call this occasionally during browsing.
    """
    try:
        viewport_width = driver.execute_script("return window.innerWidth;")
        viewport_height = driver.execute_script("return window.innerHeight;")
        
        # Random point within viewport
        x = random.randint(100, max(101, viewport_width - 100))
        y = random.randint(100, max(101, viewport_height - 100))
        
        actions = ActionChains(driver)
        actions.move_by_offset(x, y)
        actions.perform()
        
        human_pause(0.1, 0.3)
        
        # Reset position
        actions = ActionChains(driver)
        actions.move_by_offset(-x, -y)
        actions.perform()
        
    except Exception:
        pass  # Ignore mouse movement errors


def hover_element(driver, element, duration: float = None):
    """Hover over an element for a random duration."""
    try:
        human_mouse_move(driver, element)
        
        if duration is None:
            duration = random.uniform(0.5, 2.0)
        
        time.sleep(duration)
        
    except Exception:
        pass


# --------------------------------------------------
# Typing
# --------------------------------------------------

def human_type(element, text, mistakes: bool = True):
    """
    Type text character by character like a human.
    Optionally makes and corrects typos.
    """
    i = 0
    while i < len(text):
        char = text[i]
        
        # Occasionally make a typo (5% chance)
        if mistakes and random.random() < 0.05 and char.isalpha():
            # Type wrong character
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            element.send_keys(wrong_char)
            time.sleep(random.uniform(0.1, 0.3))
            
            # Realize mistake and delete
            time.sleep(random.uniform(0.2, 0.5))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.2))
        
        # Type correct character
        element.send_keys(char)
        
        # Variable typing speed
        if char == ' ':
            # Pause slightly longer after words
            time.sleep(random.uniform(0.1, 0.25))
        elif char in '.!?':
            # Pause after sentences
            time.sleep(random.uniform(0.3, 0.6))
        else:
            time.sleep(random.uniform(0.05, 0.15))
        
        # Occasionally pause longer (thinking)
        if random.random() < 0.03:
            time.sleep(random.uniform(0.5, 1.0))
        
        i += 1


def clear_and_type(element, text, mistakes: bool = True):
    """Clear input field and type new text."""
    element.clear()
    human_pause(0.2, 0.4)
    human_type(element, text, mistakes)


# --------------------------------------------------
# Natural Browsing
# --------------------------------------------------

def browse_naturally(driver, duration_sec=10.0):
    """
    Simulate natural browsing behavior for a duration.
    Combines scrolling, pausing, and mouse movements.
    """
    start_time = time.time()
    
    while time.time() - start_time < duration_sec:
        action = random.choices(
            ["scroll", "pause", "mouse", "read"],
            weights=[0.4, 0.25, 0.15, 0.2]
        )[0]
        
        if action == "scroll":
            human_scroll_pattern(driver, rounds=1)
        elif action == "pause":
            human_pause(1.0, 3.0)
        elif action == "mouse":
            random_mouse_movement(driver)
        else:  # read
            reading_pause(random.randint(50, 200))
        
        human_pause(0.5, 1.5)


def browse_profile(driver, duration_sec: float = None):
    """
    Simulate naturally browsing an Instagram/TikTok profile.
    """
    if duration_sec is None:
        duration_sec = random.uniform(15, 45)  # 15-45 seconds
    
    start_time = time.time()
    
    # Initial pause (page loading, first impression)
    human_pause(1.5, 3.0)
    
    while time.time() - start_time < duration_sec:
        action = random.choices(
            ["scroll_down", "scroll_up", "pause_read", "mouse_move", "look_at_bio"],
            weights=[0.35, 0.1, 0.3, 0.1, 0.15]
        )[0]
        
        if action == "scroll_down":
            scroll_amount = random.randint(200, 500)
            smooth_scroll(driver, scroll_amount, random.uniform(0.3, 0.7))
            human_pause(0.5, 1.5)
            
        elif action == "scroll_up":
            scroll_amount = random.randint(-150, -50)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            human_pause(0.3, 0.8)
            
        elif action == "pause_read":
            human_pause(2.0, 5.0)
            
        elif action == "mouse_move":
            random_mouse_movement(driver)
            human_pause(0.2, 0.5)
            
        elif action == "look_at_bio":
            # Scroll to top to look at bio
            driver.execute_script("window.scrollTo(0, 0);")
            human_pause(1.5, 3.5)
    
    # Final pause before leaving
    human_pause(1.0, 2.0)


def simulate_reading_bio(driver):
    """Simulate reading a profile bio."""
    # Scroll to top
    driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
    human_pause(0.5, 1.0)
    
    # Read bio (2-5 seconds)
    reading_pause(random.randint(100, 300))
    
    # Maybe scroll down a tiny bit
    if random.random() < 0.5:
        driver.execute_script("window.scrollBy(0, 100);")
        human_pause(0.5, 1.0)


def view_posts_naturally(driver, num_posts: int = 3):
    """Scroll through and 'look at' posts naturally."""
    for i in range(num_posts):
        # Scroll to next post area
        scroll_amount = random.randint(300, 500)
        smooth_scroll(driver, scroll_amount, random.uniform(0.4, 0.8))
        
        # Look at post
        human_pause(1.5, 4.0)
        
        # Sometimes hover (would trigger preview on desktop)
        if random.random() < 0.3:
            random_mouse_movement(driver)
        
        # Distraction chance
        distraction_pause()

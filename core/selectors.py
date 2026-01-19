"""
Robust Selector System with Fallbacks

Updated: January 2026

Features:
- Multiple fallback selectors for each element
- Automatic selector validation
- Easy updates when Instagram changes
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


@dataclass
class Selector:
    """Selector with fallbacks."""
    name: str
    primary: str
    by: str = "css"
    fallbacks: List[str] = field(default_factory=list)
    description: str = ""
    
    def get_by(self) -> By:
        mapping = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
        }
        return mapping.get(self.by, By.CSS_SELECTOR)
    
    def all_selectors(self) -> List[str]:
        return [self.primary] + self.fallbacks


# ==================================================
# INSTAGRAM SELECTORS (Updated January 2026)
# ==================================================

INSTAGRAM = {
    # --------------------------------------------------
    # Login & Authentication (only needed if not logged in)
    # --------------------------------------------------
    "username_input": Selector(
        name="username_input",
        primary="input[name='username']",
        fallbacks=[
            "input[aria-label='Phone number, username, or email']",
            "input[autocomplete='username']",
            "//input[@name='username']",
            "form input[type='text']",
        ],
        description="Username input on login page",
    ),
    
    "password_input": Selector(
        name="password_input",
        primary="input[name='password']",
        fallbacks=[
            "input[type='password']",
            "input[aria-label='Password']",
            "input[autocomplete='current-password']",
            "//input[@type='password']",
        ],
        description="Password input on login page",
    ),
    
    "login_button": Selector(
        name="login_button",
        primary="button[type='submit']",
        fallbacks=[
            "//button[@type='submit']",
            "//button[contains(.,'Log in')]",
            "//div[text()='Log in']/ancestor::button",
            "form button",
        ],
        description="Login submit button",
    ),
    
    # --------------------------------------------------
    # Logged In Indicators
    # --------------------------------------------------
    "home_icon": Selector(
        name="home_icon",
        primary="svg[aria-label='Home']",
        fallbacks=[
            "a[href='/'] svg",
            "//*[@aria-label='Home']",
            "nav a[href='/']",
        ],
        description="Home icon (indicates logged in)",
    ),
    
    "profile_link": Selector(
        name="profile_link",
        primary="a[href*='/'][role='link'] img[alt*='profile']",
        fallbacks=[
            "nav img[alt*='profile']",
            "img[alt*='profile picture']",
            "//nav//img[contains(@alt,'profile')]",
        ],
        description="Profile link/avatar in nav",
    ),
    
    # --------------------------------------------------
    # Profile Page
    # --------------------------------------------------
    "profile_header": Selector(
        name="profile_header",
        primary="header section",
        fallbacks=[
            "main header",
            "header",
            "//header//section",
        ],
        description="Profile header section",
    ),
    
    "profile_username": Selector(
        name="profile_username",
        primary="header h2",
        fallbacks=[
            "header section h2",
            "header h1",
            "//header//h2",
            "section h2",
        ],
        description="Username on profile page",
    ),
    
    "posts_count": Selector(
        name="posts_count",
        primary="header section ul li:first-child span",
        fallbacks=[
            "//header//ul/li[1]//span",
            "header ul li span",
            "//header//li[contains(.,'posts')]//span",
        ],
        description="Number of posts",
    ),
    
    "followers_count": Selector(
        name="followers_count",
        primary="header section ul li:nth-child(2) span span",
        fallbacks=[
            "header section ul li:nth-child(2) span",
            "//header//ul/li[2]//span",
            "a[href*='/followers/'] span",
            "//a[contains(@href,'followers')]//span",
        ],
        description="Followers count",
    ),
    
    "following_count": Selector(
        name="following_count",
        primary="header section ul li:nth-child(3) span span",
        fallbacks=[
            "header section ul li:nth-child(3) span",
            "//header//ul/li[3]//span",
            "a[href*='/following/'] span",
            "//a[contains(@href,'following')]//span",
        ],
        description="Following count",
    ),
    
    "bio_text": Selector(
        name="bio_text",
        primary="header section > div > span",
        fallbacks=[
            "header h1 + div span",
            "//header//section//span[string-length(text()) > 20]",
            "header section span",
        ],
        description="Bio text on profile",
    ),
    
    "private_indicator": Selector(
        name="private_indicator",
        primary="//*[contains(text(),'This account is private')]",
        by="xpath",
        fallbacks=[
            "//*[contains(text(),'Private')]",
            "//*[contains(text(),'private account')]",
        ],
        description="Private account message",
    ),
    
    # --------------------------------------------------
    # Posts Grid
    # --------------------------------------------------
    "posts_grid": Selector(
        name="posts_grid",
        primary="main article a[href*='/p/']",
        fallbacks=[
            "article a[href*='/p/']",
            "//article//a[contains(@href,'/p/')]",
            "a[href*='/p/'] img",
            "div[style*='flex'] a[href*='/p/']",
            "article div a[role='link']",
            "//main//a[contains(@href,'/p/')]",
        ],
        description="Post links in grid",
    ),
    
    "post_image": Selector(
        name="post_image",
        primary="article img[style*='object-fit']",
        fallbacks=[
            "article img",
            "div[role='button'] img",
            "a[href*='/p/'] img",
        ],
        description="Post thumbnail image",
    ),
    
    # --------------------------------------------------
    # Action Buttons (Profile)
    # --------------------------------------------------
    "follow_button": Selector(
        name="follow_button",
        primary="//header//button[.//div[contains(text(),'Follow')]]",
        by="xpath",
        fallbacks=[
            "//button[.//text()='Follow']",
            "//header//button[contains(.,'Follow') and not(contains(.,'Following'))]",
            "header button:not([class*='following'])",
            "//button[text()='Follow']",
        ],
        description="Follow button",
    ),
    
    "following_button": Selector(
        name="following_button",
        primary="//header//button[.//div[contains(text(),'Following')]]",
        by="xpath",
        fallbacks=[
            "//button[contains(.,'Following')]",
            "//button[contains(.,'Requested')]",
            "//header//button[contains(.,'Following')]",
        ],
        description="Following/Requested button (already following)",
    ),
    
    "unfollow_confirm": Selector(
        name="unfollow_confirm",
        primary="//button[text()='Unfollow']",
        by="xpath",
        fallbacks=[
            "//div[text()='Unfollow']",
            "//button[contains(.,'Unfollow')]",
            "[role='dialog'] button:last-child",
            "//div[@role='dialog']//button[contains(.,'Unfollow')]",
        ],
        description="Unfollow confirmation in modal",
    ),
    
    "message_button": Selector(
        name="message_button",
        primary="//header//div[text()='Message']",
        by="xpath",
        fallbacks=[
            "//header//button[.//text()='Message']",
            "a[href*='/direct/']",
            "//header//div[contains(text(),'Message')]/ancestor::button",
            "//button[contains(.,'Message')]",
        ],
        description="Message button on profile",
    ),
    
    # --------------------------------------------------
    # Post Interactions (Inside Post Modal/View)
    # --------------------------------------------------
    "like_button": Selector(
        name="like_button",
        primary="//article//span//button[.//*[name()='svg'][@aria-label='Like']]",
        by="xpath",
        fallbacks=[
            "svg[aria-label='Like']",
            "//*[@aria-label='Like']",
            "//span[@class]//button//*[@aria-label='Like']",
            "section span button svg[aria-label='Like']",
            "//article//button[.//*[@aria-label='Like']]",
            "[aria-label='Like']",
            "//section//button[.//svg[@aria-label='Like']]",
        ],
        description="Like button on post",
    ),
    
    "unlike_button": Selector(
        name="unlike_button",
        primary="//article//span//button[.//*[name()='svg'][@aria-label='Unlike']]",
        by="xpath",
        fallbacks=[
            "svg[aria-label='Unlike']",
            "//*[@aria-label='Unlike']",
            "//button[.//*[@aria-label='Unlike']]",
            "[aria-label='Unlike']",
        ],
        description="Unlike button (already liked)",
    ),
    
    "comment_button": Selector(
        name="comment_button",
        primary="//article//span//button[.//*[name()='svg'][@aria-label='Comment']]",
        by="xpath",
        fallbacks=[
            "svg[aria-label='Comment']",
            "//*[@aria-label='Comment']",
            "//button[.//*[@aria-label='Comment']]",
            "[aria-label='Comment']",
        ],
        description="Comment button",
    ),
    
    "save_button": Selector(
        name="save_button",
        primary="//article//span//button[.//*[name()='svg'][@aria-label='Save']]",
        by="xpath",
        fallbacks=[
            "svg[aria-label='Save']",
            "//*[@aria-label='Save']",
            "//button[.//*[@aria-label='Save']]",
            "[aria-label='Save']",
        ],
        description="Save/bookmark button",
    ),
    
    # --------------------------------------------------
    # Modals & Popups
    # --------------------------------------------------
    "close_modal": Selector(
        name="close_modal",
        primary="//div[@role='dialog']//button[.//*[name()='svg'][@aria-label='Close']]",
        by="xpath",
        fallbacks=[
            "svg[aria-label='Close']",
            "//*[@aria-label='Close']",
            "//button[.//*[@aria-label='Close']]",
            "[role='dialog'] button[type='button']",
            "//div[@role='dialog']//button[1]",
            "button svg[aria-label='Close']",
        ],
        description="Close button on modals",
    ),
    
    "not_now_button": Selector(
        name="not_now_button",
        primary="//button[text()='Not Now']",
        by="xpath",
        fallbacks=[
            "//button[contains(text(),'Not now')]",
            "//button[contains(text(),'Not Now')]",
            "//div[text()='Not Now']",
            "//a[text()='Not Now']",
            "[role='dialog'] button:first-child",
        ],
        description="Not Now button on popups",
    ),
    
    # --------------------------------------------------
    # Direct Messages
    # --------------------------------------------------
    "dm_inbox_icon": Selector(
        name="dm_inbox_icon",
        primary="svg[aria-label='Messenger']",
        fallbacks=[
            "a[href='/direct/inbox/']",
            "//*[@aria-label='Messenger']",
            "//a[contains(@href,'/direct/')]",
            "svg[aria-label='Direct']",
        ],
        description="DM inbox icon in nav",
    ),
    
    "new_message_button": Selector(
        name="new_message_button",
        primary="//div[contains(@class,'direct')]//button[.//*[name()='svg']]",
        by="xpath",
        fallbacks=[
            "svg[aria-label='New message']",
            "//*[@aria-label='New message']",
            "//button[.//*[@aria-label='New message']]",
            "//div[contains(@class,'direct')]//button",
            "[aria-label='New message']",
            "//a[contains(@href,'/direct/new/')]",
        ],
        description="New message button",
    ),
    
    "message_input": Selector(
        name="message_input",
        primary="//div[@role='textbox'][@contenteditable='true']",
        by="xpath",
        fallbacks=[
            "textarea[placeholder*='Message']",
            "//textarea[contains(@placeholder,'Message')]",
            "textarea[aria-label*='Message']",
            "div[role='textbox'][contenteditable='true']",
            "[contenteditable='true']",
        ],
        description="Message text input",
    ),
    
    "send_message_button": Selector(
        name="send_message_button",
        primary="//div[text()='Send']",
        by="xpath",
        fallbacks=[
            "//button[text()='Send']",
            "button[type='submit']",
            "//button[contains(.,'Send')]",
            "form button",
        ],
        description="Send message button",
    ),
    
    "recipient_search": Selector(
        name="recipient_search",
        primary="//div[@role='dialog']//input[@type='text']",
        by="xpath",
        fallbacks=[
            "input[placeholder*='Search']",
            "//input[contains(@placeholder,'Search')]",
            "input[name='queryBox']",
            "[role='dialog'] input[type='text']",
        ],
        description="Search for recipient input",
    ),
}


# ==================================================
# TIKTOK SELECTORS (Updated January 2026)
# ==================================================

TIKTOK = {
    "login_button": Selector(
        name="login_button",
        primary="[data-e2e='top-login-button']",
        fallbacks=[
            "//button[contains(text(),'Log in')]",
            "button:contains('Log in')",
        ],
        description="Login button",
    ),
    
    "profile_icon": Selector(
        name="profile_icon",
        primary="[data-e2e='profile-icon']",
        fallbacks=[
            "a[href*='/profile']",
            "//a[contains(@href,'/@')]",
        ],
        description="Profile icon (logged in indicator)",
    ),
    
    "username": Selector(
        name="username",
        primary="[data-e2e='user-title']",
        fallbacks=[
            "h1[data-e2e='user-title']",
            "h2[class*='title']",
            "//h1[contains(@data-e2e,'user')]",
        ],
        description="Username on profile",
    ),
    
    "followers_count": Selector(
        name="followers_count",
        primary="[data-e2e='followers-count']",
        fallbacks=[
            "strong[title*='Followers']",
            "//strong[contains(@title,'Followers')]",
        ],
        description="Followers count",
    ),
    
    "following_count": Selector(
        name="following_count",
        primary="[data-e2e='following-count']",
        fallbacks=[
            "strong[title*='Following']",
            "//strong[contains(@title,'Following')]",
        ],
        description="Following count",
    ),
    
    "likes_count": Selector(
        name="likes_count",
        primary="[data-e2e='likes-count']",
        fallbacks=[
            "strong[title*='Likes']",
            "//strong[contains(@title,'Likes')]",
        ],
        description="Total likes",
    ),
    
    "follow_button": Selector(
        name="follow_button",
        primary="[data-e2e='follow-button']",
        fallbacks=[
            "//button[contains(text(),'Follow')]",
            "//button[@data-e2e='follow-button']",
        ],
        description="Follow button",
    ),
    
    "video_items": Selector(
        name="video_items",
        primary="[data-e2e='user-post-item']",
        fallbacks=[
            "div[class*='video-feed'] a",
            "//div[contains(@class,'DivItemContainer')]",
        ],
        description="Video items on profile",
    ),
}


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def find_element(driver: WebDriver, selector: Selector,
                 timeout: int = 10, required: bool = False) -> Optional[WebElement]:
    """Find an element using primary selector and fallbacks."""
    all_selectors = selector.all_selectors()
    
    for sel in all_selectors:
        try:
            by = By.XPATH if sel.startswith("//") else selector.get_by()
            
            element = WebDriverWait(driver, timeout // len(all_selectors)).until(
                EC.presence_of_element_located((by, sel))
            )
            
            if element and element.is_displayed():
                return element
                
        except (TimeoutException, NoSuchElementException):
            continue
    
    if required:
        raise NoSuchElementException(
            f"Could not find element: {selector.name}\n"
            f"Tried: {all_selectors}"
        )
    
    return None


def find_elements(driver: WebDriver, selector: Selector,
                  timeout: int = 10) -> List[WebElement]:
    """Find multiple elements using primary selector and fallbacks."""
    all_selectors = selector.all_selectors()
    
    for sel in all_selectors:
        try:
            by = By.XPATH if sel.startswith("//") else selector.get_by()
            elements = driver.find_elements(by, sel)
            
            if elements:
                return [el for el in elements if el.is_displayed()]
                
        except Exception:
            continue
    
    return []


def click_element(driver: WebDriver, selector: Selector,
                  timeout: int = 10) -> bool:
    """Find and click an element."""
    element = find_element(driver, selector, timeout)
    
    if element:
        try:
            element.click()
            return True
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                pass
    
    return False


def test_selector(driver: WebDriver, selector: Selector) -> Dict[str, Any]:
    """Test a selector and return detailed results."""
    result = {
        "name": selector.name,
        "description": selector.description,
        "primary_works": False,
        "working_selector": None,
        "total_found": 0,
        "fallbacks_tested": 0,
        "fallbacks_working": 0,
    }
    
    # Test primary
    try:
        by = selector.get_by()
        if selector.primary.startswith("//"):
            by = By.XPATH
        elements = driver.find_elements(by, selector.primary)
        if elements:
            result["primary_works"] = True
            result["working_selector"] = selector.primary
            result["total_found"] = len(elements)
    except Exception:
        pass
    
    # Test fallbacks if primary failed
    if not result["primary_works"]:
        for fallback in selector.fallbacks:
            result["fallbacks_tested"] += 1
            
            try:
                by = By.XPATH if fallback.startswith("//") else selector.get_by()
                elements = driver.find_elements(by, fallback)
                
                if elements:
                    result["fallbacks_working"] += 1
                    if not result["working_selector"]:
                        result["working_selector"] = fallback
                        result["total_found"] = len(elements)
            except Exception:
                pass
    
    return result


def test_all_selectors(driver: WebDriver, selectors: Dict[str, Selector]) -> Dict[str, Dict]:
    """Test all selectors in a dictionary."""
    results = {}
    for name, selector in selectors.items():
        results[name] = test_selector(driver, selector)
    return results


def print_selector_report(results: Dict[str, Dict]):
    """Print formatted selector test report."""
    print(f"\n{'='*60}")
    print("SELECTOR TEST REPORT")
    print(f"{'='*60}")
    
    working = 0
    broken = 0
    
    for name, result in results.items():
        if result["working_selector"]:
            icon = "[OK]"
            working += 1
        else:
            icon = "[FAIL]"
            broken += 1
        
        print(f"{icon} {name}")
        
        if result["working_selector"]:
            if result["primary_works"]:
                print(f"   Primary works ({result['total_found']} found)")
            else:
                print(f"   Fallback works: {result['working_selector'][:50]}...")
        else:
            print(f"   NO WORKING SELECTOR")
    
    print(f"\n{'-'*60}")
    print(f"Summary: {working} working, {broken} broken")
    
    if broken > 0:
        print("WARNING: Some selectors need updating!")
    else:
        print("All selectors working!")
    
    print(f"{'='*60}\n")

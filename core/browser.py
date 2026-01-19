"""
Browser initialization with anti-detection measures.
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_default_chrome_profile():
    """Get the default Chrome user data directory for the current OS."""
    if os.name == 'nt':  # Windows
        return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
    elif os.name == 'posix':  # macOS/Linux
        home = os.path.expanduser('~')
        if os.path.exists(os.path.join(home, 'Library')):  # macOS
            return os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome')
        else:  # Linux
            return os.path.join(home, '.config', 'google-chrome')
    return None


def start_browser(
    user_data_dir: str = None,
    profile_name: str = "Default",
    headless: bool = False,
    window_width: int = 1280,
    window_height: int = 900,
    use_default_profile: bool = True,
    proxy: str = None,
):
    """
    Start Chrome browser with anti-detection and persistent profile.
    
    Args:
        user_data_dir: Path to Chrome user data directory (optional)
        profile_name: Chrome profile name
        headless: Run browser without GUI
        window_width: Browser window width
        window_height: Browser window height
        use_default_profile: If True, use Chrome's default profile (stays logged in)
        proxy: Proxy server URL (e.g., "http://host:port" or "http://user:pass@host:port")
    
    Returns:
        Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    
    # Use default Chrome profile if requested (keeps login sessions!)
    if use_default_profile:
        default_dir = get_default_chrome_profile()
        if default_dir and os.path.exists(default_dir):
            print(f"Using Chrome profile: {default_dir}")
            chrome_options.add_argument(f"--user-data-dir={default_dir}")
            chrome_options.add_argument(f"--profile-directory={profile_name}")
    elif user_data_dir:
        # Use custom profile directory
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument(f"--profile-directory={profile_name}")
    
    chrome_options.add_argument(f"--window-size={window_width},{window_height}")
    
    # Proxy support
    if proxy:
        print(f"Using proxy: {proxy}")
        chrome_options.add_argument(f"--proxy-server={proxy}")
    
    # Anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Performance and stability
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # User agent
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    if headless:
        chrome_options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    
    # Additional anti-detection via CDP
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        },
    )

    return driver

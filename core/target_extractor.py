"""
Extract potential outreach targets from web pages.
"""
from selenium.webdriver.common.by import By


def extract_targets(driver, limit=5):
    """
    Extract possible outreach targets from the page.
    Currently extracts links (<a>) with href.
    
    Args:
        driver: WebDriver instance
        limit: Maximum number of targets to extract
    
    Returns:
        List of target dictionaries with element, href, and text
    """
    elements = driver.find_elements(By.TAG_NAME, "a")

    targets = []
    for el in elements:
        href = el.get_attribute("href")
        text = el.text.strip()

        if not href:
            continue

        if len(text) < 3:
            continue

        targets.append({
            "element": el,
            "href": href,
            "text": text
        })

        if len(targets) >= limit:
            break

    return targets


def extract_usernames(driver, platform="instagram"):
    """
    Extract usernames from a page based on platform.
    
    Args:
        driver: WebDriver instance
        platform: Platform name (instagram, tiktok)
    
    Returns:
        List of usernames found
    """
    usernames = []
    
    if platform == "instagram":
        # Look for profile links
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='instagram.com/']")
        for link in links:
            href = link.get_attribute("href")
            if href and "/p/" not in href and "/reel/" not in href:
                # Extract username from URL
                parts = href.rstrip("/").split("/")
                if parts:
                    username = parts[-1]
                    if username and username not in usernames:
                        usernames.append(username)
    
    elif platform == "tiktok":
        # Look for profile links
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='tiktok.com/@']")
        for link in links:
            href = link.get_attribute("href")
            if href and "/@" in href:
                # Extract username from URL
                username = href.split("/@")[1].split("?")[0].split("/")[0]
                if username and username not in usernames:
                    usernames.append(username)
    
    return usernames

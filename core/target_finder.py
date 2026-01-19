"""
Target Finder - Auto-discover influencers

Features:
- Search by hashtag
- Filter by follower count
- Save to targets list
- Avoid duplicates

Usage:
    finder = TargetFinder(driver, logger)
    targets = finder.find_by_hashtag("fitness", min_followers=3000)
"""
import time
import random
import csv
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from outreach_bot.core.human_behavior import human_pause, human_scroll_pattern


class TargetFinder:
    """Auto-discover Instagram influencer targets."""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.found_targets = []
        self.visited_profiles = set()
        
        self.stats = {
            "profiles_checked": 0,
            "profiles_matched": 0,
            "profiles_skipped": 0,
        }
    
    def find_by_hashtag(self, hashtag: str, 
                        min_followers: int = 3000,
                        max_followers: int = 100000,
                        max_targets: int = 20,
                        niche: str = None) -> List[Dict]:
        """
        Find influencers by searching a hashtag.
        
        Args:
            hashtag: Hashtag to search (without #)
            min_followers: Minimum follower count
            max_followers: Maximum follower count  
            max_targets: Maximum targets to find
            niche: Niche label for found targets
        """
        hashtag = hashtag.lstrip("#")
        niche = niche or hashtag
        
        self.logger.info(f"Searching hashtag: #{hashtag}")
        self.logger.info(f"Filter: {min_followers:,} - {max_followers:,} followers")
        
        # Navigate to hashtag page
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        self.driver.get(url)
        human_pause(3, 5)
        
        # Check if hashtag exists
        if "Page Not Found" in self.driver.page_source:
            self.logger.error(f"Hashtag #{hashtag} not found")
            return []
        
        targets = []
        scroll_rounds = 0
        max_scroll_rounds = 10
        
        while len(targets) < max_targets and scroll_rounds < max_scroll_rounds:
            scroll_rounds += 1
            
            # Find post links
            posts = self._get_post_links()
            self.logger.info(f"Round {scroll_rounds}: Found {len(posts)} posts")
            
            for post_url in posts:
                if len(targets) >= max_targets:
                    break
                
                # Skip if already checked
                if post_url in self.visited_profiles:
                    continue
                self.visited_profiles.add(post_url)
                
                # Extract profile from post
                profile = self._extract_profile_from_post(
                    post_url, min_followers, max_followers, niche
                )
                
                if profile:
                    targets.append(profile)
                    self.logger.info(
                        f"[{len(targets)}/{max_targets}] @{profile['username']} "
                        f"({profile['followers']:,} followers)"
                    )
                
                human_pause(1, 3)
                
                # Go back to hashtag page
                self.driver.get(url)
                human_pause(2, 4)
            
            # Scroll for more posts
            if len(targets) < max_targets:
                human_scroll_pattern(self.driver, rounds=3)
                human_pause(2, 4)
        
        self.found_targets.extend(targets)
        self.logger.info(f"Found {len(targets)} targets for #{hashtag}")
        
        return targets
    
    def _get_post_links(self) -> List[str]:
        """Get all post links on page."""
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
            links = []
            for p in posts:
                href = p.get_attribute("href")
                if href and href not in self.visited_profiles:
                    links.append(href)
            return links[:30]  # Limit to 30 per batch
        except Exception:
            return []
    
    def _extract_profile_from_post(self, post_url: str,
                                   min_followers: int,
                                   max_followers: int,
                                   niche: str) -> Optional[Dict]:
        """Open a post and check the poster's profile."""
        try:
            # Go to post
            self.driver.get(post_url)
            human_pause(2, 4)
            
            self.stats["profiles_checked"] += 1
            
            # Find username link
            username = None
            selectors = [
                "article header a[href*='/']",
                "header a[role='link']",
            ]
            
            for selector in selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    href = elem.get_attribute("href")
                    if href and "instagram.com/" in href:
                        username = href.rstrip("/").split("/")[-1]
                        if username and username not in ["p", "explore"]:
                            break
                except NoSuchElementException:
                    continue
            
            if not username or username in self.visited_profiles:
                self.stats["profiles_skipped"] += 1
                return None
            
            self.visited_profiles.add(username)
            
            # Visit profile
            self.driver.get(f"https://www.instagram.com/{username}/")
            human_pause(2, 4)
            
            # Check if private
            page_source = self.driver.page_source.lower()
            if "this account is private" in page_source:
                self.logger.debug(f"@{username} is private, skipping")
                self.stats["profiles_skipped"] += 1
                return None
            
            # Get follower count
            followers = self._get_follower_count()
            
            if followers is None:
                self.stats["profiles_skipped"] += 1
                return None
            
            # Check criteria
            if followers < min_followers:
                self.logger.debug(f"@{username}: {followers:,} < {min_followers:,}")
                self.stats["profiles_skipped"] += 1
                return None
            
            if followers > max_followers:
                self.logger.debug(f"@{username}: {followers:,} > {max_followers:,}")
                self.stats["profiles_skipped"] += 1
                return None
            
            self.stats["profiles_matched"] += 1
            
            return {
                "username": username,
                "url": f"https://www.instagram.com/{username}/",
                "followers": followers,
                "niche": niche,
                "platform": "instagram",
                "found_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.warning(f"Error checking post: {e}")
            self.stats["profiles_skipped"] += 1
            return None
    
    def _get_follower_count(self) -> Optional[int]:
        """Extract follower count from current profile."""
        try:
            selectors = [
                "header section ul li:nth-child(2) span span",
                "header section ul li:nth-child(2) span",
                "a[href*='/followers/'] span",
            ]
            
            for selector in selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = elem.get_attribute("title") or elem.text
                    return self._parse_count(text)
                except NoSuchElementException:
                    continue
            
            return None
        except Exception:
            return None
    
    def _parse_count(self, text: str) -> int:
        """Parse counts (handles K, M)."""
        try:
            text = text.split()[0].strip().upper().replace(",", "")
            if "K" in text:
                return int(float(text.replace("K", "")) * 1000)
            elif "M" in text:
                return int(float(text.replace("M", "")) * 1_000_000)
            else:
                return int(text)
        except (ValueError, IndexError):
            return 0
    
    def save_to_csv(self, filepath: str = "data/targets.csv", 
                    append: bool = True) -> int:
        """Save found targets to CSV."""
        if not self.found_targets:
            self.logger.warning("No targets to save")
            return 0
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        file_exists = filepath.exists()
        mode = "a" if append and file_exists else "w"
        
        fieldnames = ["url", "platform", "username", "notes", "niche", "followers"]
        
        with open(filepath, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if mode == "w" or not file_exists:
                writer.writeheader()
            
            for target in self.found_targets:
                writer.writerow({
                    "url": target["url"],
                    "platform": "instagram",
                    "username": target["username"],
                    "notes": f"{target['followers']:,} followers",
                    "niche": target.get("niche", ""),
                    "followers": target["followers"],
                })
        
        self.logger.info(f"Saved {len(self.found_targets)} targets to {filepath}")
        return len(self.found_targets)
    
    def get_targets(self) -> List[Dict]:
        """Get found targets."""
        return self.found_targets.copy()
    
    def clear(self):
        """Clear found targets."""
        self.found_targets = []
    
    def print_stats(self):
        """Print statistics."""
        print(f"\n{'='*40}")
        print("TARGET FINDER STATS")
        print(f"{'='*40}")
        print(f"Profiles Checked: {self.stats['profiles_checked']}")
        print(f"Profiles Matched: {self.stats['profiles_matched']}")
        print(f"Profiles Skipped: {self.stats['profiles_skipped']}")
        print(f"Total Found: {len(self.found_targets)}")
        print(f"{'='*40}\n")
    
    def print_targets(self):
        """Print found targets."""
        if not self.found_targets:
            print("No targets found yet.")
            return
        
        print(f"\n{'='*50}")
        print("FOUND TARGETS")
        print(f"{'='*50}")
        
        for i, t in enumerate(self.found_targets, 1):
            print(f"{i}. @{t['username']} ({t['followers']:,} followers)")
        
        print(f"{'='*50}\n")

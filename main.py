"""
Outreach Bot - Production Ready
================================

A complete, production-ready browser automation system with:
- Error recovery & screenshots
- CAPTCHA detection & handling
- Session checkpoints (crash recovery)
- Robust selectors with fallbacks
- Retry logic with exponential backoff
- Comprehensive logging

Usage:
    python -m outreach_bot.main --help
    python -m outreach_bot.main --test
    python -m outreach_bot.main --test-selectors
    python -m outreach_bot.main --platform instagram
    python -m outreach_bot.main --resume SESSION_ID
"""
import argparse
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# Configuration
from outreach_bot.config import (
    BROWSER,
    SESSION,
    DATABASE_PATH,
    TARGETS_FILE,
    PROXY_FILE,
    PROTECTION,
    RATE_LIMITS,
    enable_aggressive_mode,
    print_current_limits,
)

# Core modules
from outreach_bot.core.browser import start_browser
from outreach_bot.core.task_loader import load_targets
from outreach_bot.core.logger import setup_logger
from outreach_bot.core.database import Database
from outreach_bot.core.rate_limiter import RateLimiter
from outreach_bot.core.proxy_manager import ProxyManager
from outreach_bot.core.account_protector import AccountProtector, RiskLevel

# Production modules
from outreach_bot.core.debug_helper import DebugHelper
from outreach_bot.core.captcha_handler import CaptchaHandler, check_and_handle_captcha
from outreach_bot.core.checkpoint import CheckpointManager, SessionFinder
from outreach_bot.core.retry_logic import RetryManager, retry
from outreach_bot.core.selectors import (
    INSTAGRAM, TIKTOK, 
    find_element, test_all_selectors, print_selector_report
)

# Platform adapters
from outreach_bot.core.platform.generic_web import GenericWebAdapter
from outreach_bot.core.platform.instagram import InstagramAdapter
from outreach_bot.core.platform.tiktok import TikTokAdapter

# Target finder
from outreach_bot.core.target_finder import TargetFinder


ADAPTERS = {
    "instagram": InstagramAdapter,
    "tiktok": TikTokAdapter,
    "generic": GenericWebAdapter,
}


def get_adapter(platform: str, driver, logger):
    """Get the appropriate adapter for the platform."""
    adapter_class = ADAPTERS.get(platform.lower(), GenericWebAdapter)
    return adapter_class(driver, logger)


# --------------------------------------------------
# Main Bot Runner (Production)
# --------------------------------------------------

def run_bot(
    platform: str = "instagram",
    targets_file: Path = None,
    headless: bool = False,
    use_proxy: bool = False,
    aggressive_mode: bool = False,
    session_id: str = None,
    max_targets: int = None,
    send_dm: bool = False,
    send_follow: bool = False,
    message_category: str = "generic",
    niche: str = "content",
):
    """
    Run the outreach bot with full production features.
    
    Args:
        send_dm: If True, send DMs to targets
        send_follow: If True, follow targets before DM
        message_category: Template category (collaboration, brand, casual, generic)
        niche: Content niche for message personalization
    """
    from outreach_bot.core.message_templates import get_message
    
    targets_file = targets_file or TARGETS_FILE
    logger = setup_logger("outreach_bot")
    
    if aggressive_mode:
        enable_aggressive_mode()
    
    # Initialize core components
    db = Database(str(DATABASE_PATH))
    rate_limiter = RateLimiter(db)
    protector = AccountProtector(db, logger, aggressive_mode=aggressive_mode)
    retry_manager = RetryManager(logger=logger)
    
    # Initialize checkpoint for session recovery
    checkpoint = CheckpointManager(
        session_id=session_id,
        platform=platform,
        checkpoint_dir="checkpoints",
    )
    
    # Print startup info
    logger.info("=" * 60)
    logger.info("OUTREACH BOT - PRODUCTION")
    logger.info("=" * 60)
    logger.info(f"Platform: {platform}")
    logger.info(f"Session: {checkpoint.session_id}")
    logger.info(f"Mode: {'AGGRESSIVE' if aggressive_mode else 'SAFE'}")
    if send_follow:
        logger.info("Follow Mode: ENABLED")
    if send_dm:
        logger.info(f"DM Mode: ENABLED (category: {message_category})")
    logger.info("=" * 60)
    
    # Load targets
    if targets_file.exists():
        targets = load_targets(targets_file)
        logger.info(f"Loaded {len(targets)} targets from CSV")
    else:
        targets_data = db.get_pending_targets(platform=platform, limit=100)
        targets = [t["url"] for t in targets_data]
        logger.info(f"Loaded {len(targets)} targets from database")
    
    if not targets:
        logger.warning("No targets to process!")
        return []
    
    # Set targets in checkpoint
    checkpoint.set_targets(targets)
    
    # Get pending (not yet processed) targets
    pending_targets = checkpoint.get_pending()
    logger.info(f"Pending targets: {len(pending_targets)}")
    
    if not pending_targets:
        logger.info("All targets already processed!")
        checkpoint.print_progress()
        return []
    
    # Apply session limit
    max_targets = max_targets or SESSION["max_targets_per_session"]
    if len(pending_targets) > max_targets:
        pending_targets = pending_targets[:max_targets]
        logger.info(f"Limited to {max_targets} targets for this session")
    
    # Initialize proxy manager
    proxy_manager = None
    if use_proxy and PROXY_FILE.exists():
        proxy_manager = ProxyManager()
        loaded = proxy_manager.load_from_file(str(PROXY_FILE))
        logger.info(f"Loaded {loaded} proxies")
    
    # Start browser
    driver = None
    results = []
    errors = 0
    
    try:
        logger.info("Starting browser...")
        driver = start_browser(
            user_data_dir=BROWSER["user_data_dir"],
            profile_name=BROWSER["profile_name"],
            headless=headless,
            window_width=BROWSER["window_width"],
            window_height=BROWSER["window_height"],
        )
        logger.info("[OK] Browser started")
        
        # Initialize debug helper
        debugger = DebugHelper(driver, logger, debug_dir="debug")
        
        # Initialize CAPTCHA handler
        captcha_handler = CaptchaHandler(driver, logger, mode="manual")
        
        # Get platform adapter
        adapter = get_adapter(platform, driver, logger)
        
        # Check login
        if platform in ["instagram", "tiktok"]:
            if hasattr(adapter, "is_logged_in") and not adapter.is_logged_in():
                logger.warning("=" * 50)
                logger.warning(f"⚠️ NOT LOGGED IN TO {platform.upper()}")
                logger.warning("Please log in manually in the browser.")
                logger.warning("=" * 50)
                debugger.screenshot("login_required")
                input("Press ENTER after logging in...")
                
                if not adapter.is_logged_in():
                    logger.error("Still not logged in. Exiting.")
                    return results
                
                debugger.screenshot("logged_in")
        
        # Process each target
        for i, url in enumerate(pending_targets, 1):
            # Check safety
            is_safe, reason = protector.is_safe_to_act(platform, "view")
            if not is_safe:
                logger.warning(f"⏸️ Safety check failed: {reason}")
                break
            
            # Check error threshold
            if errors >= SESSION.get("max_errors_before_stop", 5):
                logger.error(f"Too many errors ({errors}). Stopping.")
                break
            
            # Mark as processing
            checkpoint.mark_processing(url)
            
            logger.info("-" * 50)
            logger.info(f"[{i}/{len(pending_targets)}] {url}")
            checkpoint.print_progress_bar()
            print()  # Newline after progress bar
            
            try:
                # Use retry logic for opening target
                def open_and_process():
                    if not adapter.open_target(url):
                        raise Exception(f"Could not open: {url}")
                    
                    # Check for CAPTCHA
                    captcha_detected, captcha_type = captcha_handler.detect_captcha()
                    if captcha_detected:
                        debugger.screenshot(f"captcha_{i}")
                        solved = captcha_handler.handle_captcha(captcha_type)
                        if not solved:
                            raise Exception("CAPTCHA not solved")
                    
                    # Perform standard actions (view profile)
                    action_result = adapter.perform_actions()
                    
                    # Get profile info for follow/DM
                    profile_info = adapter.get_profile_info() if hasattr(adapter, 'get_profile_info') else {}
                    username = profile_info.get('username') or _extract_username(url, platform)
                    followers = profile_info.get('followers', 0)
                    
                    # Check follower minimum (3000+)
                    if followers and followers >= 3000:
                        
                        # Follow if enabled
                        if send_follow and hasattr(adapter, 'follow_user'):
                            logger.info(f"Following {username}...")
                            followed = adapter.follow_user()
                            if followed:
                                logger.info(f"Followed {username}!")
                                protector.record_action(platform, "follow")
                                action_result["followed"] = True
                                from outreach_bot.core.human_behavior import human_pause
                                human_pause(2, 4)
                            else:
                                action_result["followed"] = False
                        
                        # Send DM if enabled
                        if send_dm and hasattr(adapter, 'send_dm'):
                            # Check DM rate limit
                            if rate_limiter.can_dm(platform):
                                # Generate personalized message
                                message = get_message(
                                    name=username,
                                    niche=niche,
                                    category=message_category
                                )
                                
                                logger.info(f"Sending DM to {username}...")
                                logger.info(f"Message: {message[:50]}...")
                                
                                dm_sent = adapter.send_dm(message)
                                
                                if dm_sent:
                                    logger.info(f"DM sent to {username}!")
                                    protector.record_action(platform, "dm")
                                    rate_limiter.record_action(platform, "dm", username)
                                    action_result["dm_sent"] = True
                                else:
                                    logger.warning(f"Failed to send DM to {username}")
                                    action_result["dm_sent"] = False
                            else:
                                logger.info(f"DM rate limit reached, skipping DM for {username}")
                                action_result["dm_sent"] = "rate_limited"
                    else:
                        logger.info(f"Skipping actions - {username} has {followers} followers (need 3000+)")
                        action_result["dm_sent"] = "insufficient_followers"
                    
                    return action_result
                
                retry_result = retry_manager.execute(
                    open_and_process,
                    operation_name=f"process_{i}",
                )
                
                if retry_result.success:
                    result = retry_result.result or {"status": "success", "url": url}
                    checkpoint.mark_completed(url, result)
                    results.append(result)
                    logger.info(f"Success: {url}")
                    
                    # Record action
                    protector.record_action(platform, "view")
                    rate_limiter.record_action(platform, "view", _extract_username(url, platform))
                    
                else:
                    error_msg = str(retry_result.final_error)
                    checkpoint.mark_failed(url, error_msg)
                    results.append({"status": "failed", "url": url, "error": error_msg})
                    errors += 1
                    logger.error(f"Failed: {error_msg}")
                    debugger.capture_error(retry_result.final_error, f"target_{i}")
                
                # Wait before next target
                action_type = "dm" if send_dm else "view"
                protector.wait_smart_delay(action_type)
                
            except KeyboardInterrupt:
                logger.warning("Interrupted by user")
                checkpoint.mark_skipped(url, "User interrupted")
                break
                
            except Exception as e:
                errors += 1
                logger.error(f"Error: {e}")
                checkpoint.mark_failed(url, str(e))
                results.append({"status": "failed", "url": url, "error": str(e)})
                debugger.capture_error(e, f"target_{i}")
        
        # Session complete
        checkpoint.complete("Session finished")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
        if driver:
            DebugHelper(driver, logger).capture_error(e, "fatal_error")
        
    finally:
        # Print summaries
        logger.info("\n" + "=" * 60)
        logger.info("SESSION SUMMARY")
        logger.info("=" * 60)
        
        checkpoint.print_progress()
        retry_manager.print_stats()
        captcha_handler.print_stats() if 'captcha_handler' in dir() else None
        
        if driver:
            logger.info("Closing browser...")
            driver.quit()
    
    return results


def _extract_username(url: str, platform: str) -> str:
    """Extract username from URL."""
    url = url.rstrip("/")
    if platform == "instagram" and "instagram.com/" in url:
        return url.split("instagram.com/")[1].split("/")[0].split("?")[0]
    elif platform == "tiktok" and "/@" in url:
        return url.split("/@")[1].split("/")[0].split("?")[0]
    return url.split("/")[-1]


# --------------------------------------------------
# Test Selectors
# --------------------------------------------------

def test_selectors(platform: str = "instagram"):
    """Test all selectors for a platform."""
    logger = setup_logger("selector_test")
    
    logger.info("=" * 60)
    logger.info(f"🎯 SELECTOR TEST: {platform.upper()}")
    logger.info("=" * 60)
    
    driver = None
    
    try:
        driver = start_browser(
            user_data_dir=BROWSER["user_data_dir"],
            profile_name=BROWSER["profile_name"],
            headless=False,
        )
        
        # Get selectors for platform
        selectors = INSTAGRAM if platform == "instagram" else TIKTOK
        
        # Navigate to platform
        if platform == "instagram":
            driver.get("https://www.instagram.com/instagram/")
        else:
            driver.get("https://www.tiktok.com/@tiktok")
        
        logger.info("Waiting for page to load...")
        time.sleep(5)
        
        # Test selectors
        logger.info("Testing selectors...")
        results = test_all_selectors(driver, selectors)
        
        # Print report
        print_selector_report(results)
        
        # Save report
        broken = [name for name, r in results.items() if not r["working_selector"]]
        
        if broken:
            logger.warning(f"\n⚠️ BROKEN SELECTORS: {', '.join(broken)}")
            logger.warning("These need to be updated in core/selectors.py")
        else:
            logger.info("\n✅ All selectors working!")
        
        input("\nPress ENTER to close browser...")
        
    finally:
        if driver:
            driver.quit()


# --------------------------------------------------
# Resume Session
# --------------------------------------------------

def resume_session(session_id: str = None, platform: str = None):
    """Resume a previous session."""
    finder = SessionFinder("checkpoints")
    
    if session_id:
        # Resume specific session
        run_bot(
            platform=platform or "instagram",
            session_id=session_id,
        )
    else:
        # Show available sessions
        resumable = finder.find_resumable(platform)
        
        if not resumable:
            print("No resumable sessions found.")
            finder.print_sessions()
            return
        
        print("\n📋 Resumable Sessions:")
        for i, s in enumerate(resumable, 1):
            remaining = s["total"] - s["processed"]
            print(f"  {i}. {s['session_id']} - {s['platform']} "
                  f"({s['processed']}/{s['total']}, {remaining} remaining)")
        
        try:
            choice = input("\nEnter number to resume (or 'q' to quit): ")
            if choice.lower() == 'q':
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(resumable):
                session = resumable[idx]
                run_bot(
                    platform=session["platform"],
                    session_id=session["session_id"],
                )
        except (ValueError, IndexError):
            print("Invalid choice.")


# --------------------------------------------------
# Quick Test
# --------------------------------------------------

def run_test():
    """Run a quick test of all components."""
    logger = setup_logger("test")
    
    logger.info("=" * 60)
    logger.info("🧪 RUNNING PRODUCTION TESTS")
    logger.info("=" * 60)
    
    driver = None
    all_passed = True
    
    tests = [
        ("Database", lambda: Database(str(DATABASE_PATH))),
        ("Rate Limiter", lambda: RateLimiter(Database(str(DATABASE_PATH)))),
        ("Account Protector", lambda: AccountProtector(Database(str(DATABASE_PATH)), logger)),
        ("Checkpoint Manager", lambda: CheckpointManager("test_session", "test")),
        ("Retry Manager", lambda: RetryManager(logger=logger)),
        ("Proxy Manager", lambda: ProxyManager()),
    ]
    
    for name, test_func in tests:
        try:
            test_func()
            logger.info(f"✅ {name}")
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            all_passed = False
    
    # Browser test
    try:
        logger.info("\nStarting browser test...")
        driver = start_browser(
            user_data_dir=BROWSER["user_data_dir"],
            profile_name=BROWSER["profile_name"],
            headless=False,
        )
        logger.info("✅ Browser started")
        
        # Debug helper test
        debugger = DebugHelper(driver, logger, debug_dir="debug")
        
        # Load test page
        driver.get("https://www.example.com")
        time.sleep(2)
        
        screenshot = debugger.screenshot("test_page")
        if screenshot:
            logger.info(f"✅ Screenshot: {screenshot}")
        
        # CAPTCHA handler test
        captcha = CaptchaHandler(driver, logger, mode="skip")
        detected, ctype = captcha.detect_captcha()
        logger.info(f"✅ CAPTCHA detection (found: {detected})")
        
        # Test Instagram if possible
        logger.info("\nTesting Instagram adapter...")
        driver.get("https://www.instagram.com")
        time.sleep(3)
        
        adapter = InstagramAdapter(driver, logger)
        is_logged_in = adapter.is_logged_in()
        logger.info(f"✅ Instagram adapter (logged_in: {is_logged_in})")
        
        debugger.print_session_summary()
        
        input("\nPress ENTER to close browser...")
        
    except Exception as e:
        logger.error(f"❌ Browser test: {e}")
        all_passed = False
    finally:
        if driver:
            driver.quit()
    
    # Summary
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
    else:
        logger.info("❌ SOME TESTS FAILED")
    logger.info("=" * 60)
    
    return all_passed


# --------------------------------------------------
# Google Sheets Mode
# --------------------------------------------------

def run_from_google_sheet(sheet_url: str,
                          send_dm: bool = False,
                          send_follow: bool = False,
                          max_targets: int = 20,
                          message_category: str = "generic",
                          niche: str = "content",
                          daily_dms: int = None,
                          proxy: str = None):
    """
    Run bot using targets from Google Sheet.
    
    Args:
        sheet_url: Public Google Sheet URL
        send_dm: Send DMs to targets
        send_follow: Follow targets
        max_targets: Max targets to process
        message_category: DM template category
        niche: Content niche
        daily_dms: Custom daily DM limit (overrides config)
        proxy: Proxy server URL (e.g., http://host:port)
    """
    from outreach_bot.core.sheets_loader import load_from_public_sheet
    from outreach_bot.core.message_templates import get_message
    from outreach_bot.core.human_behavior import human_pause, browse_profile
    
    logger = setup_logger("sheet_outreach")
    
    # Set custom DM limit if provided
    if daily_dms:
        RATE_LIMITS["instagram"]["daily_dms"] = daily_dms
        SESSION["max_dms_per_session"] = min(daily_dms, max_targets)
        logger.info(f"Custom DM limit set: {daily_dms}/day")
    
    print(f"\n{'='*50}")
    print("GOOGLE SHEET MODE")
    print(f"{'='*50}")
    print(f"Sheet: {sheet_url[:50]}...")
    print(f"Max targets: {max_targets}")
    print(f"Daily DM limit: {RATE_LIMITS['instagram']['daily_dms']}")
    if send_dm:
        print(f"DM Category: {message_category}")
        print(f"Niche: {niche}")
    print(f"{'='*50}\n")
    
    # Load targets from Google Sheet
    logger.info("Loading targets from Google Sheet...")
    targets = load_from_public_sheet(sheet_url)
    
    if not targets:
        logger.error("No targets loaded! Make sure sheet is public.")
        print("\nTo make your sheet public:")
        print("1. Click 'Share' in Google Sheets")
        print("2. Change 'General access' to 'Anyone with the link'")
        print("3. Set to 'Viewer'")
        return
    
    # Limit targets
    targets = targets[:max_targets]
    logger.info(f"Processing {len(targets)} targets")
    
    # Initialize
    db = Database(str(DATABASE_PATH))
    rate_limiter = RateLimiter(db)
    protector = AccountProtector(db, logger)
    
    # Start browser (uses your default Chrome profile to stay logged in)
    logger.info("Starting browser with your Chrome profile...")
    print("\nIMPORTANT: Close all other Chrome windows before continuing!")
    print("(Selenium can't use a profile that's already in use)\n")
    
    if proxy:
        print(f"Using proxy: {proxy}")
    
    driver = start_browser(
        use_default_profile=True,
        profile_name=BROWSER["profile_name"],
        headless=False,
        proxy=proxy,
    )
    
    try:
        # Go to Instagram home first
        logger.info("Checking Instagram login status...")
        driver.get("https://www.instagram.com/")
        time.sleep(5)
        
        # Check if logged in (multiple ways)
        is_logged_in = False
        
        # Method 1: Check URL
        if "login" in driver.current_url.lower() or "accounts/login" in driver.current_url:
            is_logged_in = False
        else:
            # Method 2: Look for logged-in indicators
            try:
                # Look for profile icon, home icon, or search icon (only visible when logged in)
                from selenium.webdriver.common.by import By
                indicators = driver.find_elements(By.XPATH, 
                    "//*[contains(@aria-label,'Home')] | //*[contains(@aria-label,'Search')] | //*[contains(@aria-label,'Profile')]"
                )
                if indicators:
                    is_logged_in = True
            except:
                pass
        
        if not is_logged_in:
            print("\n" + "="*50)
            print("NOT LOGGED IN!")
            print("="*50)
            print("Please log in to Instagram in the browser window.")
            print("After logging in, press ENTER here to continue...")
            print("="*50)
            input("\nPress ENTER after logging in...")
            
            # Wait for login to complete
            time.sleep(3)
            
            # Verify login worked
            driver.get("https://www.instagram.com/")
            time.sleep(3)
        
        logger.info("Login verified. Starting outreach...")
        
        # Create adapter
        adapter = InstagramAdapter(driver, logger)
        
        # Results tracking
        results = {
            "viewed": 0,
            "followed": 0,
            "dms_sent": 0,
            "dms_failed": 0,
            "skipped": 0,
        }
        
        # Process each target
        for i, target in enumerate(targets, 1):
            username = target.get('username', '')
            url = target.get('url', '')
            target_niche = target.get('niche') or niche
            
            if not url:
                url = f"https://www.instagram.com/{username}/"
            
            logger.info(f"\n{'='*40}")
            logger.info(f"[{i}/{len(targets)}] @{username}")
            logger.info(f"{'='*40}")
            
            try:
                # Check DM rate limit
                if send_dm and not rate_limiter.can_dm("instagram"):
                    logger.warning("Daily DM limit reached!")
                    print(f"\nDaily DM limit ({RATE_LIMITS['instagram']['daily_dms']}) reached.")
                    print("Try again tomorrow or increase with --daily-dms")
                    break
                
                # Navigate to profile
                logger.info(f"Going to profile: {url}")
                driver.get(url)
                human_pause(4, 6)
                
                # Verify we're on the profile page
                if "login" in driver.current_url.lower():
                    logger.error("Redirected to login - session may have expired")
                    print("\nSession expired! Please restart the bot.")
                    break
                
                # Check if profile exists
                if "Sorry, this page" in driver.page_source:
                    logger.warning(f"Profile not found: {username}")
                    results["skipped"] += 1
                    continue
                
                # Verify we're on correct profile
                if username.lower() not in driver.current_url.lower():
                    logger.warning(f"Not on correct profile page. Current: {driver.current_url}")
                    # Try navigating again
                    driver.get(url)
                    human_pause(3, 5)
                
                # Browse naturally
                logger.info("Browsing profile...")
                browse_profile(driver, duration_sec=random.uniform(8, 15))
                results["viewed"] += 1
                
                # Follow (if enabled)
                if send_follow:
                    logger.info("Following...")
                    followed = adapter.follow_user()
                    if followed:
                        results["followed"] += 1
                        protector.record_action("instagram", "follow")
                        human_pause(3, 6)
                
                # Send DM (if enabled)
                if send_dm:
                    # Check if we've already DM'd this person
                    if db.has_interacted_with(username, "instagram", "dm"):
                        logger.info(f"Already DM'd @{username} before - skipping")
                        results["skipped"] += 1
                        continue
                    
                    logger.info("Sending DM...")
                    
                    # Generate personalized message
                    message = get_message(
                        name=username,
                        niche=target_niche,
                        category=message_category
                    )
                    
                    logger.info(f"Message preview: {message[:50]}...")
                    
                    dm_sent = adapter.send_dm(message)
                    
                    if dm_sent:
                        results["dms_sent"] += 1
                        protector.record_action("instagram", "dm")
                        rate_limiter.record_action("instagram", "dm", username)
                        logger.info("[OK] DM sent!")
                    else:
                        results["dms_failed"] += 1
                        logger.warning("[X] DM failed")
                
                # Cooldown between targets (longer for DMs)
                if send_dm:
                    cooldown = random.uniform(45, 90)  # 45-90 seconds
                else:
                    cooldown = random.uniform(10, 20)
                
                logger.info(f"Waiting {cooldown:.0f}s before next...")
                time.sleep(cooldown)
                
            except Exception as e:
                logger.error(f"Error with @{username}: {e}")
                results["skipped"] += 1
                human_pause(5, 10)
        
        # Print results
        print(f"\n{'='*50}")
        print("SESSION COMPLETE")
        print(f"{'='*50}")
        print(f"Profiles viewed: {results['viewed']}")
        if send_follow:
            print(f"Follows sent: {results['followed']}")
        if send_dm:
            print(f"DMs sent: {results['dms_sent']}")
            print(f"DMs failed: {results['dms_failed']}")
        print(f"Skipped: {results['skipped']}")
        print(f"{'='*50}")
        
        # Show remaining quota
        remaining = RATE_LIMITS['instagram']['daily_dms'] - results['dms_sent']
        print(f"\nDMs remaining today: {remaining}")
        print(f"{'='*50}\n")
        
    finally:
        driver.quit()


# --------------------------------------------------
# CLI Entry Point
# --------------------------------------------------

def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Outreach Bot - Production Ready",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # View profiles only (safe)
    python -m outreach_bot.main --platform instagram --max-targets 5
    
    # Send DMs from Google Sheet
    python -m outreach_bot.main --sheet "YOUR_SHEET_URL" --dm --max-targets 10
    
    # Send DMs with custom daily limit
    python -m outreach_bot.main --dm --daily-dms 20 --max-targets 20
    
    # Find influencers from hashtag
    python -m outreach_bot.main --find --hashtag fitness --max-targets 20
    
    # FULL AUTO: Find + Follow + DM
    python -m outreach_bot.main --auto --hashtag fitness --max-targets 5
    
    # Resume session
    python -m outreach_bot.main --resume
        """,
    )
    
    # Mode selection
    parser.add_argument("--test", action="store_true", help="Run component tests")
    parser.add_argument("--test-selectors", action="store_true", help="Test CSS selectors")
    parser.add_argument("--resume", nargs="?", const="", help="Resume a session")
    parser.add_argument("--list-sessions", action="store_true", help="List all sessions")
    parser.add_argument("--list-templates", action="store_true", help="Show message templates")
    parser.add_argument("--sheet-help", action="store_true", help="Show Google Sheets setup guide")
    
    # Google Sheets options
    parser.add_argument("--sheet", type=str, 
                        help="Google Sheet URL (must be shared as 'Anyone with link')")
    
    # Auto-discovery options
    parser.add_argument("--find", action="store_true", 
                        help="Find targets from hashtag (saves to CSV)")
    parser.add_argument("--auto", action="store_true", 
                        help="FULL AUTO: Find + Follow + DM (high risk!)")
    parser.add_argument("--hashtag", type=str, 
                        help="Hashtag to search (for --find or --auto)")
    parser.add_argument("--min-followers", type=int, default=3000,
                        help="Minimum followers (default: 3000)")
    parser.add_argument("--max-followers", type=int, default=100000,
                        help="Maximum followers (default: 100000)")
    
    # Platform options
    parser.add_argument("--platform", "-p", default="instagram",
                        choices=["instagram", "tiktok", "generic"])
    parser.add_argument("--targets", "-t", type=str, help="Targets CSV file")
    parser.add_argument("--max-targets", type=int, default=10, 
                        help="Max targets to process (default: 10)")
    
    # DM options
    parser.add_argument("--dm", action="store_true", help="Send DMs to targets")
    parser.add_argument("--follow", action="store_true", help="Follow targets before DM")
    parser.add_argument("--category", type=str, default="generic",
                        choices=["collaboration", "brand", "casual", "generic"],
                        help="Message template category")
    parser.add_argument("--niche", type=str, default="content",
                        help="Content niche (e.g., fitness, fashion, beauty)")
    parser.add_argument("--daily-dms", type=int, 
                        help="Custom daily DM limit (overrides config)")
    
    # Browser options
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--proxy", type=str, 
                        help="Proxy server URL (e.g., http://host:port or socks5://host:port)")
    parser.add_argument("--aggressive", action="store_true", help="Aggressive mode (risky)")
    
    args = parser.parse_args()
    
    # Route to appropriate function
    if args.test:
        run_test()
    
    elif args.test_selectors:
        test_selectors(args.platform)
    
    elif args.list_sessions:
        SessionFinder("checkpoints").print_sessions()
    
    elif args.list_templates:
        from outreach_bot.core.message_templates import print_templates
        print_templates()
    
    elif args.sheet_help:
        from outreach_bot.core.google_sheets import print_sheet_template
        print_sheet_template()
    
    elif args.resume is not None:
        session_id = args.resume if args.resume else None
        resume_session(session_id, args.platform)
    
    elif args.sheet:
        # Google Sheets mode
        run_from_google_sheet(
            sheet_url=args.sheet,
            send_dm=args.dm,
            send_follow=args.follow,
            max_targets=args.max_targets,
            message_category=args.category,
            niche=args.niche,
            daily_dms=args.daily_dms,
            proxy=args.proxy,
        )
    
    elif args.find:
        # Find mode - discover targets and save to CSV
        if not args.hashtag:
            print("ERROR: --find requires --hashtag")
            print("Example: python -m outreach_bot.main --find --hashtag fitness")
            return
        
        run_find_targets(
            hashtag=args.hashtag,
            min_followers=args.min_followers,
            max_followers=args.max_followers,
            max_targets=args.max_targets,
            niche=args.niche,
        )
    
    elif args.auto:
        # Auto mode - find + follow + DM (full pipeline)
        if not args.hashtag:
            print("ERROR: --auto requires --hashtag")
            print("Example: python -m outreach_bot.main --auto --hashtag fitness --max-targets 5")
            return
        
        print("\n" + "="*50)
        print("FULL AUTO MODE")
        print("="*50)
        print(f"Hashtag: #{args.hashtag}")
        print(f"Max targets: {args.max_targets}")
        print(f"Followers: {args.min_followers:,} - {args.max_followers:,}")
        print(f"Message category: {args.category}")
        print(f"Niche: {args.niche}")
        print("="*50)
        print("\nWARNING: This will automatically:")
        print("  1. Find influencers from hashtag")
        print("  2. Follow each profile")
        print("  3. Send a DM to each profile")
        print("\nThis is HIGH RISK for account bans!")
        print("="*50)
        response = input("\nContinue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        
        run_auto_pipeline(
            hashtag=args.hashtag,
            min_followers=args.min_followers,
            max_followers=args.max_followers,
            max_targets=args.max_targets,
            message_category=args.category,
            niche=args.niche,
            do_follow=True,
            do_dm=True,
        )
    
    else:
        # Normal mode - process targets from CSV
        
        # Safety warning for aggressive mode
        if args.aggressive:
            print("\nAGGRESSIVE MODE - Higher ban risk!")
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
        
        # Safety warning for DM mode
        if args.dm:
            print("\n" + "="*50)
            print("DM MODE ENABLED")
            print("="*50)
            print(f"Category: {args.category}")
            print(f"Niche: {args.niche}")
            print("\nWARNING: Sending DMs can get your account banned!")
            print("- Only targets with 3000+ followers will receive DMs")
            print("- Rate limits apply (max 10/day in safe mode)")
            print("="*50)
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
        
        targets_file = Path(args.targets) if args.targets else TARGETS_FILE
        
        run_bot(
            platform=args.platform,
            targets_file=targets_file,
            headless=args.headless,
            use_proxy=args.proxy,
            aggressive_mode=args.aggressive,
            max_targets=args.max_targets,
            send_dm=args.dm,
            send_follow=args.follow,
            message_category=args.category,
            niche=args.niche,
        )


# --------------------------------------------------
# Find Targets Mode
# --------------------------------------------------

def run_find_targets(hashtag: str,
                     min_followers: int = 3000,
                     max_followers: int = 100000,
                     max_targets: int = 20,
                     niche: str = None):
    """
    Find targets from hashtag and save to CSV.
    """
    logger = setup_logger("target_finder")
    
    print(f"\n{'='*50}")
    print("TARGET FINDER")
    print(f"{'='*50}")
    print(f"Hashtag: #{hashtag}")
    print(f"Followers: {min_followers:,} - {max_followers:,}")
    print(f"Max targets: {max_targets}")
    print(f"{'='*50}\n")
    
    # Start browser
    logger.info("Starting browser...")
    driver = start_browser(
        user_data_dir=str(BROWSER["user_data_dir"]),
        profile_name=BROWSER["profile_name"],
        headless=False,
    )
    
    try:
        # Go to Instagram
        driver.get("https://www.instagram.com/")
        time.sleep(5)
        
        # Check if logged in
        if "login" in driver.current_url.lower():
            logger.warning("Not logged in! Please log in manually...")
            input("Press ENTER after logging in...")
        
        # Create finder
        finder = TargetFinder(driver, logger)
        
        # Find targets
        targets = finder.find_by_hashtag(
            hashtag=hashtag,
            min_followers=min_followers,
            max_followers=max_followers,
            max_targets=max_targets,
            niche=niche or hashtag,
        )
        
        if targets:
            # Save to CSV
            finder.save_to_csv("data/targets.csv", append=True)
            
            # Print results
            finder.print_stats()
            finder.print_targets()
            
            print(f"\nTargets saved to data/targets.csv")
            print(f"Run with: python -m outreach_bot.main --dm --max-targets {len(targets)}")
        else:
            print("No matching targets found.")
        
    finally:
        driver.quit()


# --------------------------------------------------
# Auto Pipeline Mode
# --------------------------------------------------

def run_auto_pipeline(hashtag: str,
                      min_followers: int = 3000,
                      max_followers: int = 100000,
                      max_targets: int = 10,
                      message_category: str = "generic",
                      niche: str = None,
                      do_follow: bool = True,
                      do_dm: bool = True):
    """
    Full auto pipeline: Find + Follow + DM.
    
    HIGH RISK - Use with caution!
    """
    from outreach_bot.core.message_templates import get_message
    from outreach_bot.core.human_behavior import human_pause, browse_profile
    
    logger = setup_logger("auto_pipeline")
    niche = niche or hashtag
    
    print(f"\n{'='*50}")
    print("AUTO PIPELINE STARTED")
    print(f"{'='*50}\n")
    
    # Initialize
    db = Database(str(DATABASE_PATH))
    rate_limiter = RateLimiter(db)
    protector = AccountProtector(db, logger)
    
    # Start browser
    logger.info("Starting browser...")
    driver = start_browser(
        user_data_dir=str(BROWSER["user_data_dir"]),
        profile_name=BROWSER["profile_name"],
        headless=False,
    )
    
    try:
        # Go to Instagram
        driver.get("https://www.instagram.com/")
        time.sleep(5)
        
        # Check if logged in
        if "login" in driver.current_url.lower():
            logger.warning("Not logged in! Please log in manually...")
            input("Press ENTER after logging in...")
        
        # Create adapter
        adapter = InstagramAdapter(driver, logger)
        
        # Create finder
        finder = TargetFinder(driver, logger)
        
        # Step 1: Find targets
        logger.info(f"\n{'='*40}")
        logger.info("STEP 1: Finding targets...")
        logger.info(f"{'='*40}")
        
        targets = finder.find_by_hashtag(
            hashtag=hashtag,
            min_followers=min_followers,
            max_followers=max_followers,
            max_targets=max_targets,
            niche=niche,
        )
        
        if not targets:
            logger.error("No targets found!")
            return
        
        logger.info(f"Found {len(targets)} targets")
        
        # Step 2: Process each target
        results = {
            "viewed": 0,
            "followed": 0,
            "dms_sent": 0,
            "errors": 0,
        }
        
        for i, target in enumerate(targets, 1):
            username = target["username"]
            url = target["url"]
            followers = target["followers"]
            
            logger.info(f"\n{'='*40}")
            logger.info(f"[{i}/{len(targets)}] @{username} ({followers:,} followers)")
            logger.info(f"{'='*40}")
            
            try:
                # Check rate limits
                if do_dm and not rate_limiter.can_dm("instagram"):
                    logger.warning("DM rate limit reached for today!")
                    break
                
                # Go to profile
                driver.get(url)
                human_pause(3, 5)
                
                # Browse naturally
                logger.info("Browsing profile...")
                browse_profile(driver, duration_sec=random.uniform(10, 20))
                results["viewed"] += 1
                
                # Follow (if enabled)
                if do_follow:
                    logger.info("Following...")
                    followed = adapter.follow_user()
                    if followed:
                        results["followed"] += 1
                        protector.record_action("instagram", "follow")
                        human_pause(2, 4)
                
                # Send DM (if enabled)
                if do_dm:
                    logger.info("Sending DM...")
                    
                    # Generate personalized message
                    message = get_message(
                        name=username,
                        niche=niche,
                        category=message_category
                    )
                    
                    logger.info(f"Message: {message[:60]}...")
                    
                    dm_sent = adapter.send_dm(message)
                    
                    if dm_sent:
                        results["dms_sent"] += 1
                        protector.record_action("instagram", "dm")
                        rate_limiter.record_action("instagram", "dm", username)
                        logger.info("DM sent successfully!")
                    else:
                        logger.warning("DM failed")
                
                # Cooldown between targets
                cooldown = random.uniform(30, 60)  # 30-60 seconds
                logger.info(f"Cooldown: {cooldown:.0f}s")
                time.sleep(cooldown)
                
            except Exception as e:
                logger.error(f"Error processing @{username}: {e}")
                results["errors"] += 1
                human_pause(5, 10)
        
        # Print results
        print(f"\n{'='*50}")
        print("AUTO PIPELINE COMPLETE")
        print(f"{'='*50}")
        print(f"Profiles viewed: {results['viewed']}")
        print(f"Follows sent: {results['followed']}")
        print(f"DMs sent: {results['dms_sent']}")
        print(f"Errors: {results['errors']}")
        print(f"{'='*50}\n")
        
        # Save targets to CSV
        finder.save_to_csv("data/targets.csv", append=True)
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

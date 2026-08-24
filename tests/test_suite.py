"""
Test Suite - Validate Bot Components

Run all tests:
    python -m pytest tests/ -v
    
Or run specific tests:
    python tests/test_suite.py
"""
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from outreach_bot.config import BROWSER, SESSION, RATE_LIMITS_SAFE
        print("  ✅ config")
    except ImportError as e:
        print(f"  ❌ config: {e}")
        return False
    
    try:
        from outreach_bot.core.database import Database
        print("  ✅ database")
    except ImportError as e:
        print(f"  ❌ database: {e}")
        return False
    
    try:
        from outreach_bot.core.rate_limiter import RateLimiter
        print("  ✅ rate_limiter")
    except ImportError as e:
        print(f"  ❌ rate_limiter: {e}")
        return False
    
    try:
        from outreach_bot.core.account_protector import AccountProtector
        print("  ✅ account_protector")
    except ImportError as e:
        print(f"  ❌ account_protector: {e}")
        return False
    
    try:
        from outreach_bot.core.debug_helper import DebugHelper
        print("  ✅ debug_helper")
    except ImportError as e:
        print(f"  ❌ debug_helper: {e}")
        return False
    
    try:
        from outreach_bot.core.captcha_handler import CaptchaHandler
        print("  ✅ captcha_handler")
    except ImportError as e:
        print(f"  ❌ captcha_handler: {e}")
        return False
    
    try:
        from outreach_bot.core.checkpoint import CheckpointManager
        print("  ✅ checkpoint")
    except ImportError as e:
        print(f"  ❌ checkpoint: {e}")
        return False
    
    try:
        from outreach_bot.core.retry_logic import RetryManager, retry
        print("  ✅ retry_logic")
    except ImportError as e:
        print(f"  ❌ retry_logic: {e}")
        return False
    
    try:
        from outreach_bot.core.selectors import INSTAGRAM, TIKTOK, find_element
        print("  ✅ selectors")
    except ImportError as e:
        print(f"  ❌ selectors: {e}")
        return False
    
    try:
        from outreach_bot.core.proxy_manager import ProxyManager
        print("  ✅ proxy_manager")
    except ImportError as e:
        print(f"  ❌ proxy_manager: {e}")
        return False
    
    try:
        from outreach_bot.core.platform.instagram import InstagramAdapter
        from outreach_bot.core.platform.tiktok import TikTokAdapter
        print("  ✅ platform adapters")
    except ImportError as e:
        print(f"  ❌ platform adapters: {e}")
        return False
    
    return True


def test_database():
    """Test database operations."""
    print("\nTesting database...")
    
    from outreach_bot.core.database import Database
    import tempfile
    import os
    
    # Use temp file
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        db = Database(temp_db)
        print("  ✅ Database created")
        
        # Add target
        target_id = db.add_target("https://test.com/user1", "instagram", "user1")
        assert target_id > 0, "Should return target ID"
        print("  ✅ Add target")
        
        # Get target
        target = db.get_target(target_id)
        assert target is not None, "Should find target"
        assert target["url"] == "https://test.com/user1"
        print("  ✅ Get target")
        
        # Log action
        action_id = db.log_action("user1", "instagram", "view", "success")
        assert action_id > 0
        print("  ✅ Log action")
        
        # Get daily count
        count = db.get_daily_count("instagram", "view")
        assert count == 1
        print("  ✅ Daily count")
        
        # Check interaction
        has_interacted = db.has_interacted_with("user1", "instagram")
        assert has_interacted == True
        print("  ✅ Interaction check")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_rate_limiter():
    """Test rate limiter."""
    print("\nTesting rate limiter...")
    
    from outreach_bot.core.database import Database
    from outreach_bot.core.rate_limiter import RateLimiter
    import tempfile
    import os
    
    temp_db = tempfile.mktemp(suffix=".db")
    
    try:
        db = Database(temp_db)
        limiter = RateLimiter(db)
        print("  ✅ Rate limiter created")
        
        # Check can perform
        can_view = limiter.can_view("instagram")
        assert can_view == True
        print("  ✅ Can view check")
        
        # Record action
        limiter.record_action("instagram", "view", "testuser")
        print("  ✅ Record action")
        
        # Get stats
        stats = limiter.get_daily_stats("instagram")
        assert stats["view"] == 1
        print("  ✅ Daily stats")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Rate limiter test failed: {e}")
        return False
        
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_checkpoint():
    """Test checkpoint system."""
    print("\nTesting checkpoint...")
    
    from outreach_bot.core.checkpoint import CheckpointManager
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    checkpoint = None
    
    try:
        checkpoint = CheckpointManager(
            session_id="test_session",
            platform="instagram",
            checkpoint_dir=temp_dir,
            auto_save_interval=0,  # Disable auto-save for test
        )
        print("  ✅ Checkpoint created")
        
        # Set targets
        targets = ["https://test.com/1", "https://test.com/2", "https://test.com/3"]
        checkpoint.set_targets(targets)
        print("  ✅ Targets set")
        
        # Get pending
        pending = checkpoint.get_pending()
        assert len(pending) == 3
        print("  ✅ Get pending")
        
        # Mark processing
        checkpoint.mark_processing(targets[0])
        print("  ✅ Mark processing")
        
        # Mark completed
        checkpoint.mark_completed(targets[0], {"status": "success"})
        pending = checkpoint.get_pending()
        assert len(pending) == 2
        print("  ✅ Mark completed")
        
        # Progress
        progress = checkpoint.get_progress()
        assert progress["processed"] == 1
        assert progress["successful"] == 1
        print("  ✅ Progress tracking")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Checkpoint test failed: {e}")
        return False
        
    finally:
        if checkpoint is not None:
            checkpoint.close(save=False)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_retry_logic():
    """Test retry logic."""
    print("\nTesting retry logic...")
    
    from outreach_bot.core.retry_logic import RetryManager, retry, RetryConfig
    
    try:
        manager = RetryManager()
        print("  ✅ Retry manager created")
        
        # Test successful operation
        def success_op():
            return "success"
        
        result = manager.execute(success_op)
        assert result.success == True
        assert result.result == "success"
        print("  ✅ Successful operation")
        
        # Test retry on failure
        attempt_count = [0]
        
        def failing_op():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Temporary error")
            return "recovered"
        
        result = manager.execute(failing_op, config=RetryConfig(max_attempts=5))
        assert result.success == True
        assert result.attempts == 3
        print("  ✅ Retry on failure")
        
        # Test decorator
        @retry(max_attempts=2, base_delay=0.1)
        def decorated_func():
            return "decorated"
        
        assert decorated_func() == "decorated"
        print("  ✅ Retry decorator")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Retry logic test failed: {e}")
        return False


def test_proxy_manager():
    """Test proxy manager."""
    print("\nTesting proxy manager...")
    
    from outreach_bot.core.proxy_manager import ProxyManager
    
    try:
        manager = ProxyManager(rotation_mode="round_robin")
        print("  ✅ Proxy manager created")
        
        # Add proxies
        manager.add_proxy("1.2.3.4", 8080)
        manager.add_proxy("5.6.7.8", 3128, "user", "pass")
        assert len(manager) == 2
        print("  ✅ Add proxies")
        
        # Get next proxy
        proxy = manager.get_next_proxy()
        assert proxy is not None
        assert proxy.host == "1.2.3.4"
        print("  ✅ Get proxy")
        
        # Rotation
        proxy2 = manager.get_next_proxy()
        assert proxy2.host == "5.6.7.8"
        print("  ✅ Proxy rotation")
        
        # Parse proxy string
        manager.load_from_list([
            "10.0.0.1:8080",
            "http://user:pass@10.0.0.2:3128",
        ])
        assert len(manager) == 4
        print("  ✅ Parse proxy strings")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Proxy manager test failed: {e}")
        return False


def test_selectors():
    """Test selector system."""
    print("\nTesting selectors...")
    
    from outreach_bot.core.selectors import Selector, INSTAGRAM, TIKTOK
    
    try:
        # Test Selector class
        selector = Selector(
            name="test",
            primary="button.follow",
            fallbacks=["//button[text()='Follow']", ".follow-btn"],
        )
        
        all_sels = selector.all_selectors()
        assert len(all_sels) == 3
        print("  ✅ Selector class")
        
        # Test Instagram selectors exist
        assert "follow_button" in INSTAGRAM
        assert "followers_count" in INSTAGRAM
        assert "message_button" in INSTAGRAM
        print("  ✅ Instagram selectors defined")
        
        # Test TikTok selectors exist
        assert "follow_button" in TIKTOK
        assert "followers_count" in TIKTOK
        print("  ✅ TikTok selectors defined")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Selectors test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("🧪 OUTREACH BOT - TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    results["imports"] = test_imports()
    results["database"] = test_database()
    results["rate_limiter"] = test_rate_limiter()
    results["checkpoint"] = test_checkpoint()
    results["retry_logic"] = test_retry_logic()
    results["proxy_manager"] = test_proxy_manager()
    results["selectors"] = test_selectors()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"  {icon} {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

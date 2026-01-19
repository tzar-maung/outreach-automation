"""
Proxy Manager - IP Rotation for Avoiding Bans

Supports:
- Static proxy list
- Rotating proxies
- Proxy health checking
- Automatic failover

Usage:
    proxy_manager = ProxyManager()
    proxy_manager.load_from_file("proxies.txt")
    proxy = proxy_manager.get_next_proxy()
"""
import random
import time
import requests
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class Proxy:
    """Represents a single proxy configuration."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    
    # Health tracking
    is_healthy: bool = True
    last_used: Optional[datetime] = None
    fail_count: int = 0
    success_count: int = 0
    
    def to_selenium_format(self) -> str:
        """Format for Selenium Chrome options."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict:
        """Format for requests library."""
        proxy_url = self.to_selenium_format()
        return {
            "http": proxy_url,
            "https": proxy_url,
        }
    
    def __str__(self):
        return f"{self.host}:{self.port}"


class ProxyManager:
    """
    Manage a pool of proxies with rotation and health checking.
    
    Features:
    - Round-robin or random rotation
    - Automatic health checking
    - Failed proxy quarantine
    - Usage statistics
    """
    
    def __init__(self, rotation_mode: str = "round_robin"):
        """
        Initialize proxy manager.
        
        Args:
            rotation_mode: 'round_robin' or 'random'
        """
        self.proxies: List[Proxy] = []
        self.rotation_mode = rotation_mode
        self.current_index = 0
        self.quarantine_duration = timedelta(minutes=30)
        self.max_fail_count = 3
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    # --------------------------------------------------
    # Loading Proxies
    # --------------------------------------------------
    
    def add_proxy(self, host: str, port: int, 
                  username: str = None, password: str = None,
                  protocol: str = "http") -> None:
        """Add a single proxy to the pool."""
        proxy = Proxy(
            host=host,
            port=port,
            username=username,
            password=password,
            protocol=protocol,
        )
        self.proxies.append(proxy)
    
    def load_from_file(self, filepath: str) -> int:
        """
        Load proxies from a text file.
        
        Supported formats:
            host:port
            host:port:username:password
            protocol://host:port
            protocol://username:password@host:port
        
        Args:
            filepath: Path to proxies file
        
        Returns:
            Number of proxies loaded
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Proxy file not found: {filepath}")
        
        loaded = 0
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                proxy = self._parse_proxy_string(line)
                if proxy:
                    self.proxies.append(proxy)
                    loaded += 1
        
        return loaded
    
    def load_from_list(self, proxy_strings: List[str]) -> int:
        """Load proxies from a list of strings."""
        loaded = 0
        for proxy_str in proxy_strings:
            proxy = self._parse_proxy_string(proxy_str)
            if proxy:
                self.proxies.append(proxy)
                loaded += 1
        return loaded
    
    def _parse_proxy_string(self, proxy_str: str) -> Optional[Proxy]:
        """Parse a proxy string into a Proxy object."""
        try:
            protocol = "http"
            username = None
            password = None
            
            # Check for protocol prefix
            if "://" in proxy_str:
                protocol, proxy_str = proxy_str.split("://", 1)
            
            # Check for authentication
            if "@" in proxy_str:
                auth, proxy_str = proxy_str.rsplit("@", 1)
                if ":" in auth:
                    username, password = auth.split(":", 1)
            
            # Parse host:port
            parts = proxy_str.split(":")
            if len(parts) >= 2:
                host = parts[0]
                port = int(parts[1])
                
                # Check for username:password after port
                if len(parts) == 4 and not username:
                    username = parts[2]
                    password = parts[3]
                
                return Proxy(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    protocol=protocol,
                )
        except (ValueError, IndexError):
            pass
        
        return None
    
    # --------------------------------------------------
    # Proxy Selection
    # --------------------------------------------------
    
    def get_next_proxy(self) -> Optional[Proxy]:
        """
        Get the next available proxy.
        
        Returns:
            Proxy object or None if no healthy proxies
        """
        healthy_proxies = self._get_healthy_proxies()
        
        if not healthy_proxies:
            # Try to recover quarantined proxies
            self._recover_quarantined_proxies()
            healthy_proxies = self._get_healthy_proxies()
        
        if not healthy_proxies:
            return None
        
        if self.rotation_mode == "random":
            proxy = random.choice(healthy_proxies)
        else:  # round_robin
            self.current_index = self.current_index % len(healthy_proxies)
            proxy = healthy_proxies[self.current_index]
            self.current_index += 1
        
        proxy.last_used = datetime.now()
        return proxy
    
    def get_random_proxy(self) -> Optional[Proxy]:
        """Get a random healthy proxy."""
        healthy_proxies = self._get_healthy_proxies()
        if healthy_proxies:
            return random.choice(healthy_proxies)
        return None
    
    def _get_healthy_proxies(self) -> List[Proxy]:
        """Get list of healthy (non-quarantined) proxies."""
        return [p for p in self.proxies if p.is_healthy]
    
    def _recover_quarantined_proxies(self) -> None:
        """Recover proxies that have been quarantined long enough."""
        now = datetime.now()
        for proxy in self.proxies:
            if not proxy.is_healthy and proxy.last_used:
                if now - proxy.last_used > self.quarantine_duration:
                    proxy.is_healthy = True
                    proxy.fail_count = 0
    
    # --------------------------------------------------
    # Health Tracking
    # --------------------------------------------------
    
    def mark_success(self, proxy: Proxy) -> None:
        """Mark a proxy request as successful."""
        proxy.success_count += 1
        proxy.fail_count = 0  # Reset fail count on success
        self.total_requests += 1
        self.successful_requests += 1
    
    def mark_failure(self, proxy: Proxy) -> None:
        """Mark a proxy request as failed."""
        proxy.fail_count += 1
        self.total_requests += 1
        self.failed_requests += 1
        
        # Quarantine if too many failures
        if proxy.fail_count >= self.max_fail_count:
            proxy.is_healthy = False
            proxy.last_used = datetime.now()
    
    def check_proxy_health(self, proxy: Proxy, timeout: int = 10) -> bool:
        """
        Test if a proxy is working.
        
        Args:
            proxy: Proxy to test
            timeout: Request timeout in seconds
        
        Returns:
            True if proxy is working
        """
        test_url = "https://httpbin.org/ip"
        
        try:
            response = requests.get(
                test_url,
                proxies=proxy.to_dict(),
                timeout=timeout,
            )
            if response.status_code == 200:
                self.mark_success(proxy)
                return True
        except Exception:
            pass
        
        self.mark_failure(proxy)
        return False
    
    def check_all_proxies(self, timeout: int = 10) -> Dict[str, int]:
        """
        Test all proxies and return health statistics.
        
        Returns:
            Dictionary with healthy and unhealthy counts
        """
        healthy = 0
        unhealthy = 0
        
        for proxy in self.proxies:
            if self.check_proxy_health(proxy, timeout):
                healthy += 1
            else:
                unhealthy += 1
        
        return {
            "healthy": healthy,
            "unhealthy": unhealthy,
            "total": len(self.proxies),
        }
    
    # --------------------------------------------------
    # Selenium Integration
    # --------------------------------------------------
    
    def get_chrome_options_args(self, proxy: Proxy = None) -> List[str]:
        """
        Get Chrome arguments for proxy configuration.
        
        Args:
            proxy: Specific proxy or None to use next available
        
        Returns:
            List of Chrome argument strings
        """
        if proxy is None:
            proxy = self.get_next_proxy()
        
        if proxy is None:
            return []
        
        args = [f"--proxy-server={proxy.to_selenium_format()}"]
        
        # Disable proxy bypass for local addresses
        args.append("--proxy-bypass-list=<-loopback>")
        
        return args
    
    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------
    
    def get_statistics(self) -> Dict:
        """Get proxy pool statistics."""
        healthy = len(self._get_healthy_proxies())
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": healthy,
            "quarantined_proxies": len(self.proxies) - healthy,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests * 100
                if self.total_requests > 0 else 0
            ),
        }
    
    def __len__(self):
        return len(self.proxies)
    
    def __bool__(self):
        return len(self.proxies) > 0


# --------------------------------------------------
# Proxy Authentication Extension (for Chrome)
# --------------------------------------------------

def create_proxy_auth_extension(proxy: Proxy, extension_dir: str) -> str:
    """
    Create a Chrome extension for proxy authentication.
    
    This is needed because Chrome doesn't support proxy auth via command line.
    
    Args:
        proxy: Proxy with authentication
        extension_dir: Directory to create extension in
    
    Returns:
        Path to extension directory
    """
    import os
    import json
    
    ext_path = Path(extension_dir) / "proxy_auth_extension"
    ext_path.mkdir(parents=True, exist_ok=True)
    
    # manifest.json
    manifest = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy Auth",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        }
    }
    
    with open(ext_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # background.js
    background_js = f"""
var config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "{proxy.protocol}",
            host: "{proxy.host}",
            port: {proxy.port}
        }},
        bypassList: ["localhost"]
    }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

function callbackFn(details) {{
    return {{
        authCredentials: {{
            username: "{proxy.username or ''}",
            password: "{proxy.password or ''}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ['blocking']
);
"""
    
    with open(ext_path / "background.js", "w") as f:
        f.write(background_js)
    
    return str(ext_path)

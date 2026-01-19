"""
Retry Logic & Error Recovery

Features:
- Automatic retry with exponential backoff
- Different retry strategies per error type
- Circuit breaker pattern
- Error classification

Usage:
    @retry(max_attempts=3, backoff=2.0)
    def risky_operation():
        ...
    
    # Or use RetryManager
    retry_manager = RetryManager()
    result = retry_manager.execute(risky_operation, args)
"""
import time
import random
import functools
from typing import Callable, Any, Optional, List, Type, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    TRANSIENT = "transient"      # Retry immediately
    TEMPORARY = "temporary"      # Retry with backoff
    RATE_LIMIT = "rate_limit"    # Wait longer, then retry
    PERMANENT = "permanent"      # Don't retry
    UNKNOWN = "unknown"          # Use default handling


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.5


# Error classification
ERROR_CLASSIFICATIONS = {
    # Transient - retry immediately
    "StaleElementReferenceException": ErrorSeverity.TRANSIENT,
    "ElementClickInterceptedException": ErrorSeverity.TRANSIENT,
    "ElementNotInteractableException": ErrorSeverity.TRANSIENT,
    
    # Temporary - retry with backoff
    "TimeoutException": ErrorSeverity.TEMPORARY,
    "WebDriverException": ErrorSeverity.TEMPORARY,
    "NoSuchElementException": ErrorSeverity.TEMPORARY,
    "ConnectionError": ErrorSeverity.TEMPORARY,
    "ConnectionResetError": ErrorSeverity.TEMPORARY,
    
    # Rate limit - wait longer
    "RateLimitError": ErrorSeverity.RATE_LIMIT,
    
    # Permanent - don't retry
    "InvalidSelectorException": ErrorSeverity.PERMANENT,
    "NoSuchWindowException": ErrorSeverity.PERMANENT,
    "SessionNotCreatedException": ErrorSeverity.PERMANENT,
}


def classify_error(error: Exception) -> ErrorSeverity:
    """
    Classify an error to determine retry strategy.
    
    Args:
        error: The exception
    
    Returns:
        ErrorSeverity level
    """
    error_name = type(error).__name__
    
    # Check explicit classifications
    if error_name in ERROR_CLASSIFICATIONS:
        return ERROR_CLASSIFICATIONS[error_name]
    
    # Check error message for rate limit indicators
    error_str = str(error).lower()
    rate_limit_indicators = [
        "rate limit",
        "too many requests",
        "action blocked",
        "try again later",
        "temporarily blocked",
    ]
    
    for indicator in rate_limit_indicators:
        if indicator in error_str:
            return ErrorSeverity.RATE_LIMIT
    
    return ErrorSeverity.UNKNOWN


def calculate_delay(attempt: int, config: RetryConfig,
                    severity: ErrorSeverity) -> float:
    """
    Calculate delay before next retry.
    
    Args:
        attempt: Current attempt number (1-based)
        config: Retry configuration
        severity: Error severity
    
    Returns:
        Delay in seconds
    """
    if severity == ErrorSeverity.TRANSIENT:
        # Immediate retry with minimal delay
        base = 0.5
    elif severity == ErrorSeverity.RATE_LIMIT:
        # Much longer delay for rate limits
        base = config.base_delay * 10
    else:
        base = config.base_delay
    
    # Exponential backoff
    delay = base * (config.exponential_base ** (attempt - 1))
    
    # Cap at max delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter = delay * config.jitter_range * random.uniform(-1, 1)
        delay = max(0.1, delay + jitter)
    
    return delay


# --------------------------------------------------
# Retry Decorator
# --------------------------------------------------

def retry(max_attempts: int = 3,
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          exponential_base: float = 2.0,
          exceptions: tuple = (Exception,),
          on_retry: Callable = None,
          on_failure: Callable = None):
    """
    Decorator to add retry logic to a function.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch
        on_retry: Callback called on each retry(attempt, error, delay)
        on_failure: Callback called on final failure (error)
    
    Usage:
        @retry(max_attempts=3, base_delay=2.0)
        def my_function():
            ...
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_error = e
                    severity = classify_error(e)
                    
                    # Don't retry permanent errors
                    if severity == ErrorSeverity.PERMANENT:
                        if on_failure:
                            on_failure(e)
                        raise
                    
                    # Last attempt - don't delay, just raise
                    if attempt == max_attempts:
                        if on_failure:
                            on_failure(e)
                        raise
                    
                    # Calculate delay
                    delay = calculate_delay(attempt, config, severity)
                    
                    # Callback
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    time.sleep(delay)
            
            # Should not reach here, but just in case
            if last_error:
                raise last_error
        
        return wrapper
    return decorator


# --------------------------------------------------
# Retry Manager
# --------------------------------------------------

@dataclass
class RetryResult:
    """Result of a retry operation."""
    success: bool
    result: Any = None
    attempts: int = 0
    total_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    final_error: Optional[Exception] = None


class RetryManager:
    """
    Manages retry operations with detailed tracking.
    
    Features:
    - Execute functions with retry
    - Track success/failure rates
    - Circuit breaker pattern
    - Per-operation configuration
    """
    
    def __init__(self, default_config: RetryConfig = None, logger=None):
        """
        Initialize retry manager.
        
        Args:
            default_config: Default retry configuration
            logger: Logger instance
        """
        self.config = default_config or RetryConfig()
        self.logger = logger
        
        # Statistics
        self.stats = {
            "total_operations": 0,
            "successful": 0,
            "failed": 0,
            "total_retries": 0,
        }
        
        # Circuit breaker state
        self._failures = {}
        self._circuit_open_until = {}
    
    def execute(self, func: Callable, *args,
                config: RetryConfig = None,
                operation_name: str = None,
                **kwargs) -> RetryResult:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to function
            config: Override default config
            operation_name: Name for tracking/logging
            **kwargs: Keyword arguments to pass to function
        
        Returns:
            RetryResult with outcome details
        """
        config = config or self.config
        operation_name = operation_name or func.__name__
        
        # Check circuit breaker
        if self._is_circuit_open(operation_name):
            return RetryResult(
                success=False,
                errors=["Circuit breaker open"],
            )
        
        result = RetryResult(success=False)
        start_time = time.time()
        
        self.stats["total_operations"] += 1
        
        for attempt in range(1, config.max_attempts + 1):
            result.attempts = attempt
            
            try:
                result.result = func(*args, **kwargs)
                result.success = True
                self.stats["successful"] += 1
                
                # Reset circuit breaker on success
                self._reset_circuit(operation_name)
                
                break
                
            except Exception as e:
                error_msg = f"Attempt {attempt}: {type(e).__name__}: {str(e)}"
                result.errors.append(error_msg)
                result.final_error = e
                
                if self.logger:
                    self.logger.warning(f"Retry {operation_name}: {error_msg}")
                
                severity = classify_error(e)
                
                # Don't retry permanent errors
                if severity == ErrorSeverity.PERMANENT:
                    break
                
                # Last attempt
                if attempt == config.max_attempts:
                    self.stats["failed"] += 1
                    self._record_failure(operation_name)
                    break
                
                self.stats["total_retries"] += 1
                
                # Wait before retry
                delay = calculate_delay(attempt, config, severity)
                
                if self.logger:
                    self.logger.info(f"Waiting {delay:.1f}s before retry...")
                
                time.sleep(delay)
        
        result.total_time = time.time() - start_time
        
        return result
    
    # --------------------------------------------------
    # Circuit Breaker
    # --------------------------------------------------
    
    def _is_circuit_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for an operation."""
        if operation in self._circuit_open_until:
            if datetime.now() < self._circuit_open_until[operation]:
                return True
            else:
                # Circuit timeout expired
                del self._circuit_open_until[operation]
                self._failures[operation] = 0
        
        return False
    
    def _record_failure(self, operation: str):
        """Record a failure for circuit breaker."""
        self._failures[operation] = self._failures.get(operation, 0) + 1
        
        # Open circuit after 5 consecutive failures
        if self._failures[operation] >= 5:
            # Open circuit for 5 minutes
            self._circuit_open_until[operation] = datetime.now() + timedelta(minutes=5)
            
            if self.logger:
                self.logger.warning(
                    f"Circuit breaker opened for {operation} - "
                    f"too many failures"
                )
    
    def _reset_circuit(self, operation: str):
        """Reset circuit breaker on success."""
        self._failures[operation] = 0
        if operation in self._circuit_open_until:
            del self._circuit_open_until[operation]
    
    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        total = self.stats["total_operations"]
        
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful"] / total * 100
                if total > 0 else 0
            ),
            "avg_retries_per_operation": (
                self.stats["total_retries"] / total
                if total > 0 else 0
            ),
            "open_circuits": list(self._circuit_open_until.keys()),
        }
    
    def print_stats(self):
        """Print formatted statistics."""
        stats = self.get_stats()
        
        print(f"\n{'='*40}")
        print("🔄 Retry Statistics")
        print(f"{'='*40}")
        print(f"Total Operations: {stats['total_operations']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Total Retries: {stats['total_retries']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        
        if stats['open_circuits']:
            print(f"\n⚠️ Open Circuits: {', '.join(stats['open_circuits'])}")
        
        print(f"{'='*40}\n")


# --------------------------------------------------
# Convenience Functions
# --------------------------------------------------

def retry_on_stale_element(func: Callable, max_attempts: int = 3) -> Callable:
    """
    Decorator specifically for stale element errors.
    
    Very common in dynamic pages like Instagram.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "stale" in str(e).lower():
                    if attempt < max_attempts - 1:
                        time.sleep(0.5)
                        continue
                raise
    return wrapper


def with_timeout(timeout: float):
    """
    Decorator to add a timeout to a function.
    
    Note: This uses threading and may not work perfectly
    with all functions.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import threading
            
            result = [None]
            error = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=target)
            thread.start()
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s")
            
            if error[0]:
                raise error[0]
            
            return result[0]
        
        return wrapper
    return decorator

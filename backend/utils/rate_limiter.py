"""AgriSmart Phase 13: Lightweight, thread-safe rate limiter.

Provides sliding-window rate limiting for sensitive endpoints (auth, OTP, prediction, IoT).
Requires zero external dependencies and supports test resets.
"""

from collections import deque
from functools import wraps
import os
import threading
import time
from flask import jsonify, request


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        self._hits = {}
        self._enabled = True

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def is_enabled(self):
        return self._enabled

    def reset(self):
        """Reset all rate limiter state (useful for test isolation)."""
        with self._lock:
            self._hits.clear()

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int):
        """Check if request under key exceeds max_requests in window_seconds.

        Returns (allowed: bool, retry_after: int).
        """
        if not self._enabled:
            return True, 0

        # Allow disabling via environment variable for specific environments
        if os.getenv("DISABLE_RATE_LIMITER", "").lower() in ("true", "1", "yes"):
            return True, 0

        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            if key not in self._hits:
                self._hits[key] = deque()

            bucket = self._hits[key]

            # Evict timestamps older than the window
            while bucket and bucket[0] < window_start:
                bucket.popleft()

            if len(bucket) >= max_requests:
                earliest = bucket[0]
                retry_after = max(1, int(earliest + window_seconds - now))
                return False, retry_after

            bucket.append(now)
            return True, 0


# Global singleton instance
limiter = InMemoryRateLimiter()


def get_client_ip():
    """Retrieve client IP respecting reverse-proxy headers if present."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the list is the client IP
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def rate_limit(max_requests: int, window_seconds: int, scope: str = None, key_func=None):
    """Decorator to apply rate limiting to a Flask route."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not limiter.is_enabled():
                return fn(*args, **kwargs)

            # Determine rate limit key
            if key_func:
                identifier = key_func()
            else:
                identifier = get_client_ip()

            endpoint_name = scope or request.endpoint or fn.__name__
            rate_key = f"{endpoint_name}:{identifier}"

            allowed, retry_after = limiter.check_rate_limit(
                rate_key, max_requests, window_seconds
            )

            if not allowed:
                response = jsonify({
                    "status": "error",
                    "message": f"Too many requests. Please try again in {retry_after} second(s).",
                    "retry_after": retry_after
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            return fn(*args, **kwargs)
        return wrapper
    return decorator

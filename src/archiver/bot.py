"""PRAW stream listener with conservative read and write guards."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterable
from typing import Any


class RateLimiter:
    """Sliding-window request guard that stays below 10 requests/minute."""

    def __init__(self, requests_per_minute: int = 9) -> None:
        self.requests_per_minute = min(9, max(1, requests_per_minute))
        self.window_seconds = 60.0
        self.timestamps: deque[float] = deque()

    def wait(self) -> None:
        """Block until one additional request is permitted."""
        while True:
            now = time.monotonic()
            while self.timestamps and now - self.timestamps[0] >= self.window_seconds:
                self.timestamps.popleft()
            if len(self.timestamps) < self.requests_per_minute:
                self.timestamps.append(now)
                return
            time.sleep(min(1.0, self.window_seconds - (now - self.timestamps[0])))


class RedditBot:
    """Listen to subreddit streams and gate all writes by policy limits."""

    def __init__(
        self,
        reddit: Any,
        subreddits: Iterable[str],
        dry_run: bool = True,
        requests_per_minute: int = 9,
        write_cooldown_seconds: int = 120,
        max_backoff_seconds: int = 300,
    ) -> None:
        self.reddit = reddit
        self.subreddits = tuple(subreddits)
        self.dry_run = dry_run
        self.limiter = RateLimiter(requests_per_minute)
        self.write_cooldown_seconds = max(120, write_cooldown_seconds)
        self.max_backoff_seconds = max_backoff_seconds
        self._last_write = 0.0
        self._seen_ids: set[str] = set()

    def is_seen(self, item_id: str) -> bool:
        return item_id in self._seen_ids

    def mark_seen(self, item_id: str) -> None:
        self._seen_ids.add(item_id)

    def write_allowed(self) -> bool:
        """Check cooldown and dry-run policy without performing a write."""
        if self.dry_run:
            return False
        elapsed = time.monotonic() - self._last_write
        return elapsed >= self.write_cooldown_seconds

    def can_write(self) -> bool:
        """Compatibility name for write_allowed."""
        return self.write_allowed()

    def submit(self, subreddit: str, title: str, body: str) -> Any:
        """Submit a digest only when live mode and cooldown permit it."""
        if not self.write_allowed():
            return None
        result = self.reddit.subreddit(subreddit).submit(title=title, selftext=body)
        self._last_write = time.monotonic()
        return result

    def reply(self, item: Any, body: str) -> Any:
        """Reply to an item only when live mode and cooldown permit it."""
        if not self.write_allowed():
            return None
        result = item.reply(body)
        self._last_write = time.monotonic()
        return result

    def monitor(self, callback: Any = None) -> None:
        """Stream submissions indefinitely, stopping safely on interruptions."""
        for subreddit_name in self.subreddits:
            subreddit = self.reddit.subreddit(subreddit_name)
            for submission in subreddit.stream.submissions(skip_existing=True):
                self.limiter.wait()
                item_id = str(getattr(submission, "id", ""))
                if not item_id or self.is_seen(item_id):
                    continue
                self.mark_seen(item_id)
                if callback:
                    callback(submission)

    def run_with_backoff(self, operation: Any) -> Any:
        """Retry an operation with exponential backoff for rate-limit errors."""
        backoff = 1
        while True:
            try:
                return operation()
            except Exception as error:
                status = getattr(error, "status_code", None)
                message = str(error).lower()
                if status != 429 and "ratelimit" not in message:
                    raise
                time.sleep(min(backoff, self.max_backoff_seconds))
                backoff = min(backoff * 2, self.max_backoff_seconds)

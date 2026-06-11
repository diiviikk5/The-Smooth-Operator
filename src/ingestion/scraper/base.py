"""Abstract base class for all scrapers in The Smooth Operator.

Provides common scraping infrastructure including rate limiting, retry logic
with exponential backoff, user-agent rotation, and a standardized data model.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ScraperError(Exception):
    """Base exception for scraper-related errors."""


class RateLimitError(ScraperError):
    """Raised when rate limit is exceeded and retries are exhausted."""


class ScrapingTimeoutError(ScraperError):
    """Raised when a scraping request times out after all retries."""


class InvalidURLError(ScraperError):
    """Raised when the supplied URL fails validation."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ScrapedData:
    """Standardised container for data returned by any scraper.

    Attributes:
        url: The canonical URL that was scraped.
        title: Page / profile / document title.
        content: Cleaned plain-text content.
        metadata: Arbitrary key-value metadata extracted during scraping.
        scraped_at: UTC timestamp of when the scrape occurred.
        raw_html: The raw HTML response body (empty for API-based scrapers).
        content_hash: SHA-256 hash of ``content`` for deduplication.
        status_code: HTTP status code of the response.
        source_type: Identifier for the scraper that produced this data.
    """

    url: str
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_html: str = ""
    content_hash: str = ""
    status_code: int = 200
    source_type: str = "web"

    def __post_init__(self) -> None:
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class TokenBucketRateLimiter:
    """Async token-bucket rate limiter.

    Attributes:
        rate: Maximum tokens (requests) per second.
        max_tokens: Burst capacity.
    """

    def __init__(self, rate: float, max_tokens: Optional[float] = None) -> None:
        self.rate = rate
        self.max_tokens = max_tokens or rate
        self._tokens = self.max_tokens
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a token is available."""
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self.rate
                await asyncio.sleep(wait)
                self._refill()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.rate)
        self._last_refill = now


# ---------------------------------------------------------------------------
# User-agent rotation pool
# ---------------------------------------------------------------------------

_DEFAULT_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


# ---------------------------------------------------------------------------
# Abstract base scraper
# ---------------------------------------------------------------------------


class BaseScraper(ABC):
    """Abstract base class that every scraper must implement.

    Provides:
    * Configurable rate limiting via a token-bucket algorithm.
    * Automatic retry with exponential back-off and jitter.
    * User-agent rotation for each request.

    Args:
        requests_per_second: Max sustained request rate.
        max_retries: How many times to retry a failed request.
        base_backoff: Initial back-off delay in seconds (doubles each retry).
        timeout: Per-request timeout in seconds.
        user_agents: Optional list of user-agent strings to rotate through.
        proxy_url: Optional HTTP/SOCKS proxy URL.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        timeout: int = 30,
        user_agents: Optional[List[str]] = None,
        proxy_url: Optional[str] = None,
    ) -> None:
        self.requests_per_second = requests_per_second
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.timeout = timeout
        self.user_agents = user_agents or list(_DEFAULT_USER_AGENTS)
        self.proxy_url = proxy_url

        self._rate_limiter = TokenBucketRateLimiter(rate=requests_per_second)
        self._request_count: int = 0
        self._error_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape(self, url: str) -> ScrapedData:
        """Scrape the given URL with rate limiting and retries.

        Args:
            url: The URL to scrape.

        Returns:
            ScrapedData populated with the extracted information.

        Raises:
            InvalidURLError: If ``validate_url`` rejects the URL.
            ScraperError: If all retry attempts fail.
        """
        if not await self.validate_url(url):
            raise InvalidURLError(f"URL failed validation: {url}")

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                self._request_count += 1
                logger.debug(
                    "Scraping %s (attempt %d/%d)", url, attempt, self.max_retries
                )
                result = await self._do_scrape(url)
                logger.info("Successfully scraped %s", url)
                return result
            except Exception as exc:
                self._error_count += 1
                last_exception = exc
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "Scrape attempt %d/%d for %s failed: %s – retrying in %.1fs",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                    delay,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)

        raise ScraperError(
            f"All {self.max_retries} attempts failed for {url}"
        ) from last_exception

    async def validate_url(self, url: str) -> bool:
        """Check that *url* looks structurally valid.

        Subclasses can override this to enforce domain-specific rules.

        Args:
            url: The URL to validate.

        Returns:
            ``True`` when the URL is acceptable.
        """
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Helpers available to subclasses
    # ------------------------------------------------------------------

    def _get_random_user_agent(self) -> str:
        """Return a randomly selected user-agent string."""
        return random.choice(self.user_agents)

    def _backoff_delay(self, attempt: int) -> float:
        """Compute exponential back-off with jitter.

        Args:
            attempt: Current (1-indexed) attempt number.

        Returns:
            Delay in seconds.
        """
        base = self.base_backoff * (2 ** (attempt - 1))
        jitter = random.uniform(0, base * 0.5)
        return base + jitter

    @property
    def stats(self) -> Dict[str, int]:
        """Return request/error counts for observability."""
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
        }

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def _do_scrape(self, url: str) -> ScrapedData:
        """Perform the actual scraping logic.

        Subclasses implement this — the public ``scrape()`` method handles
        rate limiting and retries around it.

        Args:
            url: Validated, rate-limited URL ready to fetch.

        Returns:
            ScrapedData with extracted content.
        """
        ...

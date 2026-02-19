"""
Base scraper with rate limiting, retries, caching, and job tracking.
All scrapers inherit from this.
"""
import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings


class RateLimiter:
    """
    Per-domain rate limiter.
    Tracks last request time per domain and enforces minimum delay.
    """

    def __init__(self, delay: float | None = None):
        self.delay = delay or settings.SCRAPER_DELAY_SECONDS
        self._last_request: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str) -> None:
        async with self._lock:
            last = self._last_request.get(domain, 0)
            elapsed = time.monotonic() - last
            if elapsed < self.delay:
                # Add small jitter so request cadence is less predictable.
                wait_time = (self.delay - elapsed) + random.uniform(0.1, 0.8)
                logger.debug(f"Rate limit: waiting {wait_time:.1f}s for {domain}")
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()


_rate_limiter = RateLimiter()


class BaseScraper(ABC):
    """
    Base class for all scrapers.

    Features:
    - Automatic rate limiting per domain
    - Retry with exponential backoff on transient errors
    - Rotation of header profiles on 403/429/503 responses
    - Redis caching to avoid redundant requests
    """

    SOURCE_NAME: str = "unknown"
    BASE_URL: str = ""
    DEFAULT_HEADERS: dict = {
        "User-Agent": "FootballDataBot/1.0 (research project; contact@example.com)",
        "Accept": "application/json, text/html;q=0.9",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    }

    HEADER_PROFILES: tuple[dict, ...] = (
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
        },
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
            "Pragma": "no-cache",
        },
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Cache-Control": "no-cache",
        },
    )

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis = redis_client
        self._client: Optional[httpx.AsyncClient] = None
        self._header_profile_idx = random.randint(0, len(self.HEADER_PROFILES) - 1)

    async def __aenter__(self):
        active_headers = dict(self.DEFAULT_HEADERS)
        active_headers.update(self.HEADER_PROFILES[self._header_profile_idx])
        self._client = httpx.AsyncClient(
            headers=active_headers,
            timeout=httpx.Timeout(settings.SCRAPER_TIMEOUT_SECONDS),
            follow_redirects=True,
            http2=True,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    async def _get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        cache_ttl: Optional[int] = None,
    ) -> dict | str:
        """
        GET request with rate limiting, caching, and anti-block retries.
        Returns parsed JSON dict/list or raw text.
        """
        from urllib.parse import urlparse
        import json

        if self._client is None:
            raise RuntimeError("HTTP client not initialized. Use 'async with' for scraper instances.")

        domain = urlparse(url).netloc

        if self.redis and cache_ttl:
            cache_key = f"scrape:{url}:{str(params)}"
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {url}")
                return json.loads(cached)

        await _rate_limiter.wait(domain)

        max_attempts = 4
        resp: Optional[httpx.Response] = None
        for attempt in range(1, max_attempts + 1):
            request_headers = headers
            if request_headers is None and attempt > 1:
                self._rotate_header_profile()
                request_headers = self._client.headers

            logger.debug(f"GET {url} (attempt {attempt}/{max_attempts})")
            resp = await self._client.get(url, params=params, headers=request_headers)

            if resp.status_code in (403, 429, 503) and attempt < max_attempts:
                backoff_s = min(30.0, (2 ** attempt) + random.uniform(0.3, 1.1))
                logger.warning(
                    f"Temporary block {resp.status_code} on {domain}. Retrying in {backoff_s:.1f}s."
                )
                await asyncio.sleep(backoff_s)
                continue
            break

        if resp is None:
            raise RuntimeError(f"Failed to fetch {url}: no response")

        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            data: dict | list | str = resp.json()
        else:
            data = resp.text

        if self.redis and cache_ttl and isinstance(data, (dict, list)):
            cache_key = f"scrape:{url}:{str(params)}"
            await self.redis.setex(cache_key, cache_ttl, json.dumps(data))

        return data

    @abstractmethod
    async def scrape(self, *args, **kwargs) -> Any:
        """Main scraping method to implement in each subclass."""
        raise NotImplementedError

    def log(self, msg: str, level: str = "info") -> None:
        getattr(logger, level)(f"[{self.SOURCE_NAME}] {msg}")

    def _rotate_header_profile(self) -> None:
        if not self._client:
            return
        self._header_profile_idx = (self._header_profile_idx + 1) % len(self.HEADER_PROFILES)
        next_headers = dict(self.DEFAULT_HEADERS)
        next_headers.update(self.HEADER_PROFILES[self._header_profile_idx])
        self._client.headers.clear()
        self._client.headers.update(next_headers)

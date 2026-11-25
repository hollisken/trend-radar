"""Bounded HTTP helpers: TLS verification, per-host politeness, size and time caps."""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

USER_AGENT = "trend-radar/0.1 (metadata-only aggregator; see POLICY.md)"
DEFAULT_TIMEOUT = 15
DEFAULT_MAX_BYTES = 2_000_000

_last_request: dict[str, float] = {}


@dataclass
class FetchResult:
    url: str
    status: int | None
    body: bytes = b""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300 and not self.error


def _throttle(url: str, min_interval: float) -> None:
    host = (urlsplit(url).hostname or "").lower()
    previous = _last_request.get(host)
    if previous is not None:
        wait = min_interval - (time.monotonic() - previous)
        if wait > 0:
            time.sleep(wait)
    _last_request[host] = time.monotonic()


def get(url: str, *, timeout: float = DEFAULT_TIMEOUT, max_bytes: int = DEFAULT_MAX_BYTES,
        min_interval: float = 1.0, accept: str = "*/*") -> FetchResult:
    """GET one URL once. Returns an error field instead of raising."""
    if urlsplit(url).scheme not in ("http", "https"):
        return FetchResult(url=url, status=None, error="bad_scheme")
    _throttle(url, min_interval)
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes)
            return FetchResult(url=url, status=response.status, body=body)
    except urllib.error.HTTPError as exc:
        return FetchResult(url=url, status=exc.code, error=f"http_{exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return FetchResult(url=url, status=None, error=f"transport_{type(exc).__name__}")

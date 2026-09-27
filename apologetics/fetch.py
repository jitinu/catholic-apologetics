import hashlib
import logging
import re
import time
from pathlib import Path

import requests

from .config import CACHE_DIR

LOGGER = logging.getLogger(__name__)
USER_AGENT = "Mozilla/5.0 (apologetics-tool personal use)"
_last_uncached_request = 0.0


def _cache_path(url: str) -> Path:
    return CACHE_DIR / hashlib.sha1(url.encode("utf-8")).hexdigest()


def _declared_encoding(response: requests.Response) -> str | None:
    content_type = response.headers.get("Content-Type", "")
    match = re.search(r"charset\s*=\s*[\"']?([\w.-]+)", content_type, re.IGNORECASE)
    if match:
        return match.group(1)
    head = response.content[:2048].decode("ascii", errors="ignore")
    match = re.search(r"charset\s*=\s*[\"']?([\w.-]+)", head, re.IGNORECASE)
    return match.group(1) if match else None


def fetch(url: str, refresh: bool = False) -> str:
    """Fetch a URL with a small persistent cache and polite retries."""
    global _last_uncached_request
    path = _cache_path(url)
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    wait = 0.5 - (time.monotonic() - _last_uncached_request)
    if wait > 0:
        time.sleep(wait)
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            _last_uncached_request = time.monotonic()
            if 500 <= response.status_code < 600:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            encoding = _declared_encoding(response) or response.apparent_encoding or "utf-8"
            text = response.content.decode(encoding, errors="replace")
            path.write_text(text, encoding="utf-8")
            return text
        except (requests.RequestException, UnicodeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(f"Could not fetch {url}: {last_error}") from last_error

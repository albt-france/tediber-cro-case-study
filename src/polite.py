"""Polite HTTP helper for the public-data collectors.

Rules applied to every request:
- robots.txt is checked before fetching (urllib.robotparser); disallowed paths are never fetched;
- at most one request every 10 seconds to tediber.com (MIN_DELAY_S);
- the first HTTP 429 (rate limit) stops all further requests to that host for the run: no retry,
  no IP change, no User-Agent rotation;
- a neutral User-Agent with no personal contact details.
"""
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = "cro-case-study/1.0"
MIN_DELAY_S = 10.0
_last_call: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}
_blocked: set[str] = set()


def _root(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def allowed(url: str) -> bool:
    root = _root(url)
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        r = requests.get(root + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=20)
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        _robots[root] = rp
        _last_call[root] = time.time()
    return _robots[root].can_fetch(USER_AGENT, url)


def get(url: str, delay: float = MIN_DELAY_S) -> requests.Response | None:
    """GET url if robots.txt allows it and the host has not rate-limited us; None otherwise."""
    root = _root(url)
    if root in _blocked:
        print(f"[stopped] {root} returned 429 earlier: {url} not fetched")
        return None
    if not allowed(url):
        print(f"[robots] disallowed, skipped: {url}")
        return None
    wait = delay - (time.time() - _last_call.get(root, 0))
    if wait > 0:
        time.sleep(wait)
    _last_call[root] = time.time()
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
                         timeout=30)
    except requests.RequestException as e:
        print(f"[error] {url}: {e}")
        return None
    if r.status_code == 429:
        _blocked.add(root)
        print(f"[429] {url}: rate limited, no further requests to {root} in this run")
        return None
    return r

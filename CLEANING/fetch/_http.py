"""Shared, polite HTTP helpers for the fetchers (retries, delay, sitemap, file download)."""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests

log = logging.getLogger("fetch")

USER_AGENT = "SIH26165-research-fetcher/1.0 (+student hackathon project; contact via repo)"
DEFAULT_DELAY = 1.0          # seconds between requests to the same host
TIMEOUT = 60

_session: requests.Session | None = None
_last_hit: dict[str, float] = {}


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
    return _session


def _polite(url: str, delay: float) -> None:
    host = urlparse(url).netloc
    now = time.time()
    wait = _last_hit.get(host, 0) + delay - now
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def get(url: str, *, delay: float = DEFAULT_DELAY, retries: int = 3, **kw) -> requests.Response:
    """GET with delay + retry. Raises on final failure."""
    last: Exception | None = None
    for attempt in range(retries):
        _polite(url, delay)
        try:
            r = session().get(url, timeout=TIMEOUT, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code} for {url}")
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            sleep = 2 ** attempt * delay
            log.warning("retry %d/%d in %.0fs: %s", attempt + 1, retries, sleep, exc)
            time.sleep(sleep)
    raise RuntimeError(f"giving up on {url}: {last}")


def download(url: str, dest: Path, *, delay: float = DEFAULT_DELAY, skip_existing: bool = True) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if skip_existing and dest.exists() and dest.stat().st_size > 0:
        return dest
    r = get(url, delay=delay, stream=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as fh:
        for chunk in r.iter_content(1 << 16):
            fh.write(chunk)
    tmp.replace(dest)
    log.info("saved %s (%.0f KB)", dest.name, dest.stat().st_size / 1024)
    return dest


def sitemap_urls(base: str, *, match: str, delay: float = DEFAULT_DELAY) -> list[str]:
    """Collect URLs from /sitemap.xml (and nested sitemap indexes) whose path matches the regex."""
    seen: set[str] = set()
    out: list[str] = []
    queue = [urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml"), urljoin(base, "/wp-sitemap.xml")]
    rx = re.compile(match)
    while queue:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        try:
            r = get(sm, delay=delay)
        except Exception:  # noqa: BLE001
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
        for loc in locs:
            if loc.endswith(".xml") and loc not in seen:
                queue.append(loc)
            elif rx.search(loc) and loc not in out:
                out.append(loc)
    return out


def soup(html: str):
    from bs4 import BeautifulSoup  # noqa: WPS433

    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # noqa: BLE001 - lxml missing
        return BeautifulSoup(html, "html.parser")


def absolute(base: str, hrefs: Iterable[str]) -> list[str]:
    return [urljoin(base, h) for h in hrefs if h]


def slug_from_url(url: str) -> str:
    s = urlparse(url).path.rstrip("/").split("/")[-1]
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:120] or "item"

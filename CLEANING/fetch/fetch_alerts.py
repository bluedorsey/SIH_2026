"""
Safety-alert fetchers: IADC, IMCA, Step Change in Safety, OISD.

Each writes DATA/RAW/Safety Alerts/<SOURCE>/index.jsonl (one line per alert:
url, title, date, tags, html_text, pdf/zip file name) and downloads the
attachment (PDF / ZIP) next to it.  The parser (CLEANING/clean_alerts.py)
prefers the PDF text when present and falls back to html_text.

    python -m CLEANING.fetch.fetch_alerts --source iadc [--max-pages 2]
    python -m CLEANING.fetch.fetch_alerts --source imca
    python -m CLEANING.fetch.fetch_alerts --source stepchange
    python -m CLEANING.fetch.fetch_alerts --source oisd
    python -m CLEANING.fetch.fetch_alerts               # all four

These are public "shared for information" resources; the fetcher is polite
(1 request/second, identifies itself, never re-downloads).  Re-run any time:
it resumes from index.jsonl.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "CLEANING.fetch"  # noqa: A001

from ..config import RAW_ALERTS_DIR  # noqa: E402
from ._http import absolute, download, get, sitemap_urls, slug_from_url, soup  # noqa: E402

log = logging.getLogger("fetch.alerts")

_ATTACH_RE = re.compile(r"\.(pdf|zip|docx?)(\?.*)?$", re.I)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _usable(row: dict) -> bool:
    return len((row.get("html_text") or "").strip()) > 80 or bool(row.get("attachments"))


def _load_index(path: Path, only_usable: bool = False) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        rows = [json.loads(ln) for ln in fh if ln.strip()]
    if only_usable:                      # empty rows (JS-rendered page, failed parse) are re-fetched on the next run
        rows = [r for r in rows if _usable(r)]
    return {r["url"]: r for r in rows}


def _rewrite_index(path: Path, rows: dict[str, dict]) -> None:
    tmp = path.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for r in rows.values():
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _append_index(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _main_text(page) -> str:
    """Visible text of the article body, with headings kept on their own lines."""
    for t in page(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        t.decompose()
    body = page.find("article") or page.find("main") or page.body or page
    lines: list[str] = []
    for el in body.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li", "td", "th", "div"]):
        if el.find(["p", "li", "h1", "h2", "h3", "h4", "div"]) and el.name == "div":
            continue  # container div - its children are visited separately
        txt = el.get_text(" ", strip=True)
        if not txt:
            continue
        if el.name.startswith("h"):
            lines.append("\n## " + txt)
        else:
            lines.append(txt)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _embedded_text(page) -> str:
    """Fallback for JavaScript-rendered pages (Next.js / Nuxt / JSON-LD): pull long strings out of embedded JSON."""
    chunks: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("articleBody", "description", "body", "content", "summary", "text", "html", "excerpt") and isinstance(v, str):
                    chunks.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and len(o) > 120 and " " in o and not o.startswith(("http", "{", "[")):
            chunks.append(o)

    for sc in page.find_all("script"):
        sid, styp = (sc.get("id") or ""), (sc.get("type") or "")
        if sid in ("__NEXT_DATA__", "__NUXT_DATA__") or "json" in styp:
            try:
                walk(json.loads(sc.string or ""))
            except Exception:  # noqa: BLE001
                continue
    if not chunks:
        for m in page.find_all("meta", attrs={"name": ["description", "twitter:description"]}) + page.find_all("meta", attrs={"property": "og:description"}):
            if m.get("content"):
                chunks.append(m["content"])
    seen, out = set(), []
    for c in chunks:
        c = re.sub(r"<[^>]+>", " ", c)
        c = re.sub(r"\s+", " ", c).strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return "\n".join(out).strip()


def _attachments(page, base: str) -> list[str]:
    hrefs = [a.get("href") for a in page.find_all("a", href=True)]
    return [u for u in absolute(base, hrefs) if _ATTACH_RE.search(u)]


def _meta_date(page) -> str | None:
    for sel in ({"property": "article:published_time"}, {"name": "date"}, {"itemprop": "datePublished"}):
        m = page.find("meta", attrs=sel)
        if m and m.get("content"):
            return m["content"][:10]
    t = page.find("time")
    if t and (t.get("datetime") or t.get_text(strip=True)):
        return (t.get("datetime") or t.get_text(strip=True))[:25]
    m = re.search(r"\b(\d{1,2} \w+ 20\d\d|\w+ \d{1,2}, 20\d\d|20\d\d-\d\d-\d\d)\b", page.get_text(" ")[:3000])
    return m.group(1) if m else None


def _fetch_one(url: str, out_dir: Path, source: str) -> dict:
    r = get(url)
    page = soup(r.text)
    title = (page.find("h1").get_text(" ", strip=True) if page.find("h1") else (page.title.get_text(strip=True) if page.title else url))
    tags = [t.get_text(" ", strip=True) for t in page.select(".tag, .tags a, .category a, .life-saving-rule, .lsr, [class*='tag'] a")]
    embedded = _embedded_text(page)          # must run before _main_text, which strips <script> tags
    text = _main_text(page)
    if len(text) < 80:
        text = embedded or text
    row = {"source": source, "url": url, "title": title, "date": _meta_date(page), "tags": sorted(set(tags))[:20],
           "html_text": text, "attachments": []}
    for i, att in enumerate(_attachments(page, url)[:3]):
        ext = _ATTACH_RE.search(att).group(1).lower()
        name = f"{slug_from_url(url)}{'' if i == 0 else f'_{i}'}.{ext}"
        try:
            download(att, out_dir / "files" / name)
            row["attachments"].append({"url": att, "file": f"files/{name}"})
        except Exception as exc:  # noqa: BLE001
            log.warning("attachment failed %s: %s", att, exc)
    return row


def _crawl(source: str, urls: list[str], out_dir: Path, limit: int | None = None) -> int:
    index = out_dir / "index.jsonl"
    all_rows = _load_index(index)
    have = {u: r for u, r in all_rows.items() if _usable(r)}
    if len(have) != len(all_rows):
        log.info("%s: %d empty rows in the index will be re-fetched", source, len(all_rows) - len(have))
        _rewrite_index(index, have)
    todo = [u for u in urls if u not in have]
    if limit:
        todo = todo[:limit]
    log.info("%s: %d known, %d to fetch", source, len(have), len(todo))
    n = 0
    for u in todo:
        try:
            row = _fetch_one(u, out_dir, source)
            _append_index(index, row)
            n += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("skip %s: %s", u, exc)
    log.info("%s: fetched %d new alerts -> %s", source, n, index)
    return n


# --------------------------------------------------------------------------
# IADC  https://iadc.org/health-safety-environment/safety-alerts/  (26 pages, HTML + PDF)
# --------------------------------------------------------------------------
def iadc(max_pages: int | None = None, limit: int | None = None) -> int:
    base = "https://iadc.org"
    urls = sitemap_urls(base, match=r"iadc\.org/safety-alerts/[^/]+/?$")
    if not urls:
        log.info("no sitemap - paginating listing")
        p = 1
        while True:
            if max_pages and p > max_pages:
                break
            list_url = f"{base}/health-safety-environment/safety-alerts/" + (f"page/{p}/" if p > 1 else "")
            try:
                page = soup(get(list_url).text)
            except Exception:  # noqa: BLE001
                break
            found = [a["href"] for a in page.find_all("a", href=True) if "/safety-alerts/" in a["href"] and "/page/" not in a["href"]]
            found = [u for u in absolute(list_url, found) if re.search(r"iadc\.org/safety-alerts/[^/]+/?$", u)]
            new = [u for u in found if u not in urls]
            if not new:
                break
            urls.extend(new)
            p += 1
    return _crawl("IADC", sorted(set(urls)), RAW_ALERTS_DIR / "IADC", limit)


# --------------------------------------------------------------------------
# IMCA  https://www.imca-int.com/resources/safety/safety-flashes/  (2,395 flashes, HTML, LSR tags)
# --------------------------------------------------------------------------
def imca(max_pages: int | None = None, limit: int | None = None) -> int:
    base = "https://www.imca-int.com"
    urls = sitemap_urls(base, match=r"/resources/safety/safety-flashes/\d+[^/]*/?$")
    if not urls:
        log.info("no sitemap - trying RSS + listing pagination")
        try:
            rss = get(base + "/resources/safety/safety-flashes/rss-feed/").text
            urls += re.findall(r"<link>\s*(https?://[^<\s]+/safety-flashes/\d+[^<\s]*)\s*</link>", rss)
        except Exception:  # noqa: BLE001
            pass
        for p in range(1, (max_pages or 200) + 1):
            for cand in (f"{base}/resources/safety/safety-flashes/page/{p}/", f"{base}/resources/safety/safety-flashes/?page={p}"):
                try:
                    page = soup(get(cand).text)
                except Exception:  # noqa: BLE001
                    continue
                found = [u for u in absolute(cand, [a["href"] for a in page.find_all("a", href=True)])
                         if re.search(r"/safety-flashes/\d+[^/]*/?$", u)]
                new = [u for u in found if u not in urls]
                if new:
                    urls.extend(new)
                    break
            else:
                break
    return _crawl("IMCA", sorted(set(urls)), RAW_ALERTS_DIR / "IMCA", limit)


# --------------------------------------------------------------------------
# Step Change in Safety  https://www.stepchangeinsafety.com/alerts-learnings/  (HTML summary + zip/pdf)
# --------------------------------------------------------------------------
def stepchange(max_pages: int | None = None, limit: int | None = None) -> int:
    base = "https://www.stepchangeinsafety.com"
    urls = sitemap_urls(base, match=r"/alerts-learnings/[^/]+/?$")
    urls = [u for u in urls if "/page/" not in u]
    if not urls:
        for p in range(1, (max_pages or 60) + 1):
            list_url = f"{base}/alerts-learnings/" + (f"page/{p}/" if p > 1 else "")
            try:
                page = soup(get(list_url).text)
            except Exception:  # noqa: BLE001
                break
            found = [u for u in absolute(list_url, [a["href"] for a in page.find_all("a", href=True)])
                     if re.search(r"/alerts-learnings/[^/]+/?$", u) and "/page/" not in u]
            new = [u for u in found if u not in urls]
            if not new:
                break
            urls.extend(new)
    return _crawl("StepChange", sorted(set(urls)), RAW_ALERTS_DIR / "StepChange", limit)


# --------------------------------------------------------------------------
# OISD  https://www.oisd.gov.in/en-in/SafetyAlerts  (table with View/Download PDF links)
# --------------------------------------------------------------------------
def oisd(max_pages: int | None = None, limit: int | None = None) -> int:
    list_url = "https://www.oisd.gov.in/en-in/SafetyAlerts"
    out_dir = RAW_ALERTS_DIR / "OISD"
    index = out_dir / "index.jsonl"
    have = _load_index(index)
    page = soup(get(list_url, verify=True).text)
    rows = page.find_all("tr")
    n = 0
    for tr in rows:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        links = [a["href"] for a in tr.find_all("a", href=True)]
        atts = [u for u in absolute(list_url, links) if _ATTACH_RE.search(u) or "download" in u.lower() or "filemanager" in u.lower()]
        if not atts or len(cells) < 2:
            continue
        att = atts[0]
        if att in have:
            continue
        ref = next((c for c in cells if re.search(r"OISD/|/SA/", c)), cells[0])
        desc = max(cells, key=len)
        name = re.sub(r"[^A-Za-z0-9]+", "_", ref)[:80] or slug_from_url(att)
        ext = (_ATTACH_RE.search(att).group(1).lower() if _ATTACH_RE.search(att) else "pdf")
        try:
            download(att, out_dir / "files" / f"{name}.{ext}")
        except Exception as exc:  # noqa: BLE001
            log.warning("OISD attachment failed %s: %s", att, exc)
            continue
        _append_index(index, {"source": "OISD", "url": att, "title": desc, "reference": ref, "date": next((c for c in cells if re.search(r"\d{2}[-/.]\d{2}[-/.]\d{4}|\d{4}-\d{2}-\d{2}", c)), None),
                              "tags": [ref.split("/")[3] if ref.count("/") >= 3 else ""], "html_text": " | ".join(cells),
                              "attachments": [{"url": att, "file": f"files/{name}.{ext}"}]})
        n += 1
        if limit and n >= limit:
            break
    log.info("OISD: fetched %d new alerts -> %s", n, index)
    if n == 0 and not have:
        log.warning("OISD: no attachment links found - the page may be JavaScript-rendered. Open %s in a browser, "
                    "save each 'View / Download' PDF into %s and re-run the parser.", list_url, out_dir / "files")
    return n


SOURCES = {"iadc": iadc, "imca": imca, "stepchange": stepchange, "oisd": oisd}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=list(SOURCES) + ["all"], default="all")
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None, help="stop after N new alerts (smoke test)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    for name, fn in SOURCES.items():
        if a.source in ("all", name):
            try:
                fn(max_pages=a.max_pages, limit=a.limit)
            except Exception as exc:  # noqa: BLE001
                log.error("%s failed: %s", name, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Optional: Playwright fallback for JS pages
try:
    from playwright.sync_api import sync_playwright
    _HAS_PLAYWRIGHT = True
except Exception:
    _HAS_PLAYWRIGHT = False

USER_AGENT = "Mozilla/5.0 (compatible; MyAgent/1.0; +https://example.org/bot)"


def _fetch_html(url: str, js: bool = False, timeout: int = 15) -> Dict[str, Any]:
    """Return dict with keys: html, final_url, error (optional)."""
    headers = {"User-Agent": USER_AGENT}

    if not js:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return {"html": r.text, "final_url": r.url}
        except Exception as e:
            if _HAS_PLAYWRIGHT:
                js = True
            else:
                return {"error": str(e)}

    if js:
        if not _HAS_PLAYWRIGHT:
            return {"error": "Playwright not installed; cannot render JS."}

        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                html = page.content()
                final_url = page.url
                browser.close()
                return {"html": html, "final_url": final_url}
        except Exception as e:
            return {"error": str(e)}

    return {"error": "Unknown fetch failure"}


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _word_snippet(full_text: str, span: tuple, window_words: int = 20):
    """Return snippet of window_words before and after the match."""
    tokens = re.findall(r"\S+", full_text)

    positions = []
    pos = 0
    for t in tokens:
        start = full_text.find(t, pos)
        positions.append((start, start + len(t)))
        pos = start + len(t)

    start_char, end_char = span
    start_idx = next((i for i, (a, b) in enumerate(positions) if b > start_char), 0)
    end_idx = next((i for i, (a, b) in enumerate(positions) if a >= end_char), len(tokens)-1)

    s = max(0, start_idx - window_words)
    e = min(len(tokens), end_idx + window_words + 1)

    return " ".join(tokens[s:e]), s, e


def _find_nearby_urls(soup: BeautifulSoup, element) -> List[str]:
    urls = set()

    for a in element.select("a[href]"):
        urls.add(a.get("href"))

    parent = element.parent
    if parent:
        for a in parent.select("a[href]"):
            urls.add(a.get("href"))

        prev = element.find_previous_sibling()
        if prev:
            for a in prev.select("a[href]"):
                urls.add(a.get("href"))

        nxt = element.find_next_sibling()
        if nxt:
            for a in nxt.select("a[href]"):
                urls.add(a.get("href"))

    return [u for u in urls if u]




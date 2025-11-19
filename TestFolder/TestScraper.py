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
    
    if element:
        element_text_len = len(element.get_text(" ", strip=True))

    # URLs from element itself
    element_urls = [a.get("href") for a in element.select("a[href]")] if element else []
    for a in element_urls:
        urls.add(a)

    parent = element.parent if element else None
    if parent:
        parent_urls = [a.get("href") for a in parent.select("a[href]")]
        for a in parent_urls:
            urls.add(a)

        prev = element.find_previous_sibling()
        if prev:
            prev_urls = [a.get("href") for a in prev.select("a[href]")]
            for a in prev_urls:
                urls.add(a)

        nxt = element.find_next_sibling()
        if nxt:
            next_urls = [a.get("href") for a in nxt.select("a[href]")]
            for a in next_urls:
                urls.add(a)

    final_urls = [u for u in urls if u]
    return final_urls


def _extract_table_structure(table_element) -> Dict[str, Any]:
    """Extract table structure as rows and columns."""
    rows = []
    headers = []
    
    # Try to find header row (thead or first tr with th)
    thead = table_element.find('thead')
    if thead:
        header_row = thead.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
    
    # If no thead, check first tr for th elements
    if not headers:
        first_row = table_element.find('tr')
        if first_row:
            th_elements = first_row.find_all('th')
            if th_elements:
                headers = [th.get_text(strip=True) for th in th_elements]
    
    # Extract all data rows
    tbody = table_element.find('tbody') or table_element
    for tr in tbody.find_all('tr'):
        # Skip header row if it was already processed
        if tr.find('th') and headers:
            continue
            
        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if not cells:
            continue
            
        # If we have headers, create dict; otherwise use list
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
        else:
            rows.append(cells)
    
    return {
        "headers": headers if headers else None,
        "rows": rows,
        "row_count": len(rows)
    }


def scrape_data(url: str,
                selector: Optional[str] = None,
                keyword: Optional[str] = None,
                js: bool = False,
                max_snippets: int = 5,
                window_words: int = 20) -> Dict[str, Any]:
    """
    Scrape a webpage and extract content based on different modes.
    
    This tool can operate in three modes:
    1. Initial exploration: Returns page headings and available selectors (when both selector and keyword are None)
    2. Keyword search: Finds text snippets containing the keyword with context (when keyword is provided)
    3. CSS selector extraction: Extracts content matching a CSS selector (when selector is provided)
    
    Args:
        url (str): The URL of the webpage to scrape.
        selector (Optional[str]): CSS selector to extract specific elements (e.g., "article", "table", ".class-name").
                                  If None and keyword is also None, returns page structure info.
        keyword (Optional[str]): Search for a specific keyword in the page text. Returns snippets with context.
        js (bool): Whether to render JavaScript (requires Playwright). Default is False.
        max_snippets (int): Maximum number of snippets to return. Default is 5.
        window_words (int): Number of words before and after keyword match to include in snippet. Default is 20.
    
    Returns:
        Dict[str, Any]: A dictionary with the following structure:
            - status: "ok", "error", "not_found"
            - snippets: List of keyword-based text snippets with nearby URLs (if keyword search)
            - selector_results: List of extracted content from CSS selectors (if selector used)
            - headings: List of page headings h1, h2, h3 (if initial exploration)
            - selectors_hint: List of available selectors found on page (if initial exploration)
            - meta: Dictionary with fetched_url and final_url
            - error/note: Error message or note if something went wrong
    
    Usage Notes (for the agent):
        - First call with only url to explore page structure (get headings and selector hints)
        - Use keyword parameter to search for specific text content
        - Use selector parameter to extract structured content (tables, articles, lists, etc.)
        - Set js=True if the page requires JavaScript rendering
        - Combine with web_search() to find relevant URLs first, then scrape them
    """

    fetched = _fetch_html(url, js=js)
    if "error" in fetched:
        return {"status": "error", "error": fetched["error"], "meta": {"fetched_url": url}}

    html = fetched["html"]
    final_url = fetched.get("final_url", url)
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    page_text = _clean_text(soup.get_text(" ", strip=True))

    result = {
        "status": "ok",
        "snippets": [],
        "selector_results": [],
        "headings": [],
        "meta": {"fetched_url": url, "final_url": final_url}
    }

    # CASE 1 ------------------ Initial call (no keyword + no selector)
    if not selector and not keyword:
        headings = [h.get_text(" ", strip=True) for h in soup.select("h1, h2, h3")][:40]
        selectors_found = []

        for sel in ["table", "article", "main", "ul", "ol"]:
            if soup.select_one(sel):
                selectors_found.append(sel)

        result["headings"] = headings
        result["selectors_hint"] = selectors_found
        return result

    # CASE 2 ------------------ Keyword search
    if keyword:
        low = page_text.lower()
        kw = keyword.lower()

        matches = []
        start = 0
        while len(matches) < max_snippets:
            idx = low.find(kw, start)
            if idx == -1:
                break
            matches.append((idx, idx + len(kw)))
            start = idx + len(kw)


        if matches:
            for i, span in enumerate(matches):
               
                snippet, _, _ = _word_snippet(page_text, span, window_words=window_words)
          

                # Find the most specific (smallest) element containing the keyword
                element = None
                elements_checked = 0
                candidate_elements = []
                
                # Skip these large container elements
                skip_tags = {'html', 'body', 'main', 'div', 'section', 'article'}
                
                for el in soup.find_all():
                    elements_checked += 1
                    try:
                        el_text = el.get_text(" ", strip=True).lower()
                        if kw in el_text:
                            # Skip very large elements (likely page containers)
                            if len(el_text) > 500:
                                continue
                            # Prefer smaller, more specific elements
                            candidate_elements.append((el, len(el_text)))
                    except:
                        continue
                
                if candidate_elements:
                    # Sort by text length (smallest first) and take the most specific
                    candidate_elements.sort(key=lambda x: x[1])
                    element = candidate_elements[-1][0]
                   

                urls = _find_nearby_urls(soup, element) if element else []
                
                # Calculate size of this snippet entry
                snippet_entry = {
                    "text": snippet,
                    "urls": urls
                }
                entry_size = len(json.dumps(snippet_entry))

                result["snippets"].append(snippet_entry)

            # Calculate final result size
            final_size = len(json.dumps(result))
            return result

        else:
            if not selector:
                return {
                    "status": "not_found",
                    "note": f"Keyword '{keyword}' not found on page.",
                    "meta": result["meta"]
                }

    # CASE 3 ------------------ CSS Selector extraction
    if selector:
        elems = soup.select(selector)
        if not elems:
            return {
                "status": "not_found",
                "note": f"Selector '{selector}' not found on page.",
                "meta": result["meta"]
            }

        for el in elems[:max_snippets]:
            # Check if this is a table element
            if el.name == 'table':
                # Extract table structure
                table_data = _extract_table_structure(el)
                print(table_data)
                urls = [a.get("href") for a in el.select("a[href]")]
                result["selector_results"].append({
                    "selector": selector,
                    "type": "table",
                    "table_data": table_data,
                    "text": _clean_text(el.get_text(" ", strip=True)),  # Keep plain text as fallback
                    "urls": urls
                })
            else:
                # For non-table elements, use existing text extraction
                text = _clean_text(el.get_text(" ", strip=True))
                urls = [a.get("href") for a in el.select("a[href]")]
                result["selector_results"].append({
                    "selector": selector,
                    "type": "text",
                    "text": text,
                    "urls": urls
                })

        return result

    return {"status": "not_found", "note": "No matches found", "meta": result["meta"]}

#data = scrape_data(selector = 'table', url ='https://en.wikipedia.org/wiki/Mercedes_Sosa')

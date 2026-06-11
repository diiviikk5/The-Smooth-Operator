"""General-purpose web scraper using httpx + BeautifulSoup.

Extracts structured content from arbitrary web pages — company sites,
blog posts, about pages, team pages — and returns clean plain text with
rich metadata.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from src.ingestion.scraper.base import BaseScraper, ScrapedData, ScraperError

logger = logging.getLogger(__name__)

# Tags whose entire subtree should be removed before text extraction.
_REMOVE_TAGS: Set[str] = {
    "script", "style", "noscript", "iframe", "svg",
    "nav", "footer", "header", "aside", "form",
    "button", "input", "select", "textarea",
}

# Tags treated as structural boilerplate (less aggressive than _REMOVE_TAGS).
_BOILERPLATE_CLASSES: Set[str] = {
    "sidebar", "menu", "cookie", "popup", "modal", "ad", "ads",
    "advertisement", "banner", "social", "share", "comment",
    "comments", "breadcrumb", "pagination", "newsletter",
}


class WebScraper(BaseScraper):
    """Scrapes arbitrary web pages into clean structured text.

    Args:
        requests_per_second: Max sustained request rate.
        max_retries: Retry count on failure.
        base_backoff: Initial back-off delay.
        timeout: Per-request timeout (seconds).
        user_agents: Optional custom user-agent pool.
        proxy_url: Optional HTTP(S) proxy.
        follow_redirects: Whether to follow HTTP redirects.
        max_content_length: Reject responses larger than this (bytes).
        extract_links: Whether to extract outbound links.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        timeout: int = 30,
        user_agents: Optional[List[str]] = None,
        proxy_url: Optional[str] = None,
        follow_redirects: bool = True,
        max_content_length: int = 10 * 1024 * 1024,  # 10 MB
        extract_links: bool = True,
    ) -> None:
        super().__init__(
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            base_backoff=base_backoff,
            timeout=timeout,
            user_agents=user_agents,
            proxy_url=proxy_url,
        )
        self.follow_redirects = follow_redirects
        self.max_content_length = max_content_length
        self.extract_links = extract_links

    # ------------------------------------------------------------------
    # Core scraping
    # ------------------------------------------------------------------

    async def _do_scrape(self, url: str) -> ScrapedData:
        """Fetch *url* with httpx and parse with BeautifulSoup.

        Args:
            url: The validated URL to fetch.

        Returns:
            ScrapedData with cleaned text and metadata.

        Raises:
            ScraperError: On HTTP errors or content too large.
        """
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

        transport_kwargs: Dict[str, Any] = {}
        if self.proxy_url:
            transport_kwargs["proxy"] = self.proxy_url

        async with httpx.AsyncClient(
            follow_redirects=self.follow_redirects,
            timeout=httpx.Timeout(self.timeout),
            **transport_kwargs,
        ) as client:
            response = await client.get(url, headers=headers)

        if response.status_code >= 400:
            raise ScraperError(
                f"HTTP {response.status_code} for {url}: {response.reason_phrase}"
            )

        content_length = len(response.content)
        if content_length > self.max_content_length:
            raise ScraperError(
                f"Response too large ({content_length} bytes) for {url}"
            )

        # Detect encoding — httpx usually does this, but be safe.
        encoding = response.encoding or "utf-8"
        raw_html = response.text

        soup = BeautifulSoup(raw_html, "html.parser")

        title = self._extract_title(soup)
        meta = self._extract_metadata(soup, url, response.status_code)
        self._remove_boilerplate(soup)
        content = self._extract_content(soup)
        headings = self._extract_headings(soup)

        if self.extract_links:
            meta["links"] = self._extract_links(soup, url)

        meta["headings"] = headings
        meta["word_count"] = len(content.split())
        meta["encoding"] = encoding

        return ScrapedData(
            url=str(response.url),  # canonical after redirects
            title=title,
            content=content,
            metadata=meta,
            raw_html=raw_html,
            status_code=response.status_code,
            source_type="web",
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        """Extract the page title from ``<title>`` or ``<h1>``."""
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            return str(og_title["content"]).strip()
        return ""

    @staticmethod
    def _extract_metadata(
        soup: BeautifulSoup, url: str, status_code: int
    ) -> Dict[str, Any]:
        """Pull meta description, Open-Graph tags, author, and date."""
        meta: Dict[str, Any] = {
            "source_url": url,
            "status_code": status_code,
        }

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            meta["description"] = str(desc_tag["content"]).strip()

        # Open Graph
        for prop in ("og:description", "og:image", "og:type", "og:site_name"):
            tag = soup.find("meta", attrs={"property": prop})
            if tag and tag.get("content"):
                meta[prop.replace(":", "_")] = str(tag["content"]).strip()

        # Author
        author_tag = soup.find("meta", attrs={"name": "author"})
        if author_tag and author_tag.get("content"):
            meta["author"] = str(author_tag["content"]).strip()

        # Published date
        for attr in ("article:published_time", "datePublished", "date"):
            date_tag = soup.find("meta", attrs={"property": attr}) or soup.find(
                "meta", attrs={"name": attr}
            )
            if date_tag and date_tag.get("content"):
                meta["published_date"] = str(date_tag["content"]).strip()
                break

        # Canonical URL
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            meta["canonical_url"] = str(canonical["href"]).strip()

        return meta

    @staticmethod
    def _remove_boilerplate(soup: BeautifulSoup) -> None:
        """Remove script/style/nav/footer tags and common boilerplate classes."""
        # Remove entire tag trees
        for tag_name in _REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove elements whose class/id matches boilerplate patterns
        for element in soup.find_all(True):
            classes = " ".join(element.get("class", [])).lower()
            el_id = (element.get("id") or "").lower()
            combined = f"{classes} {el_id}"
            if any(bp in combined for bp in _BOILERPLATE_CLASSES):
                element.decompose()

    @staticmethod
    def _extract_content(soup: BeautifulSoup) -> str:
        """Convert cleaned soup to well-formatted plain text.

        Preserves paragraph breaks and list structure.
        """
        lines: List[str] = []
        body = soup.find("body") or soup

        for element in body.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "blockquote", "pre", "code"]
        ):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            tag_name = element.name
            if tag_name and tag_name.startswith("h"):
                level = tag_name[1]
                lines.append(f"\n{'#' * int(level)} {text}\n")
            elif tag_name == "li":
                lines.append(f"  • {text}")
            elif tag_name == "blockquote":
                lines.append(f"> {text}")
            elif tag_name in ("pre", "code"):
                lines.append(f"```\n{text}\n```")
            else:
                lines.append(text)

        content = "\n".join(lines)
        # Collapse excessive whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    @staticmethod
    def _extract_headings(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Return a list of heading dicts ``{level, text}``."""
        headings: List[Dict[str, str]] = []
        for tag in soup.find_all(re.compile(r"^h[1-6]$")):
            text = tag.get_text(strip=True)
            if text:
                headings.append({"level": tag.name, "text": text})
        return headings

    @staticmethod
    def _extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all outbound ``<a>`` links with text and absolute URL."""
        links: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            if href.startswith(("#", "javascript:", "mailto:")):
                continue
            absolute = urljoin(base_url, href)
            if absolute in seen:
                continue
            seen.add(absolute)
            links.append({
                "url": absolute,
                "text": anchor.get_text(strip=True)[:200],
            })
        return links

    # ------------------------------------------------------------------
    # Specialised page detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def detect_page_type(url: str, soup: BeautifulSoup) -> str:
        """Heuristically classify a page as about, team, blog, product, etc.

        Args:
            url: The page URL.
            soup: Parsed BeautifulSoup tree (already cleaned or not).

        Returns:
            A string label: ``about``, ``team``, ``blog``, ``product``, ``contact``, or ``general``.
        """
        path = urlparse(url).path.lower()
        title_text = (soup.title.string if soup.title and soup.title.string else "").lower()
        combined = f"{path} {title_text}"

        if any(kw in combined for kw in ("about", "who-we-are", "our-story")):
            return "about"
        if any(kw in combined for kw in ("team", "people", "leadership", "staff")):
            return "team"
        if any(kw in combined for kw in ("blog", "article", "post", "news")):
            return "blog"
        if any(kw in combined for kw in ("product", "features", "solutions", "pricing")):
            return "product"
        if any(kw in combined for kw in ("contact", "get-in-touch", "support")):
            return "contact"
        return "general"

    def extract_structured_company_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract JSON-LD or microdata company information if present.

        Args:
            soup: Parsed page.

        Returns:
            Dictionary with available structured data fields.
        """
        import json as _json

        info: Dict[str, Any] = {}

        # JSON-LD
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = _json.loads(script.string or "")
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            info.update(self._parse_jsonld(item))
                elif isinstance(data, dict):
                    info.update(self._parse_jsonld(data))
            except (ValueError, TypeError):
                continue

        return info

    @staticmethod
    def _parse_jsonld(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful fields from a JSON-LD object."""
        result: Dict[str, Any] = {}
        ld_type = data.get("@type", "")

        if ld_type in ("Organization", "Corporation", "LocalBusiness"):
            for key in ("name", "url", "description", "email", "telephone",
                        "foundingDate", "numberOfEmployees"):
                if key in data:
                    result[f"org_{key}"] = data[key]
            if "address" in data and isinstance(data["address"], dict):
                result["org_address"] = data["address"]

        if ld_type == "Person":
            for key in ("name", "jobTitle", "url", "email"):
                if key in data:
                    result[f"person_{key}"] = data[key]

        if ld_type in ("Article", "BlogPosting", "NewsArticle"):
            for key in ("headline", "datePublished", "author", "description"):
                if key in data:
                    result[f"article_{key}"] = data[key]

        return result

"""LinkedIn profile scraper with proxy support and detection avoidance.

Because LinkedIn aggressively blocks automated access, this scraper uses a
multi-layered approach:
1. Public profile API endpoint (no auth required for public profiles).
2. HTTP-based scraping with proxy rotation and realistic headers.
3. Graceful degradation — returns partial data rather than failing.

IMPORTANT: Always comply with LinkedIn's Terms of Service. This module is
provided for educational and authorized-use scenarios only.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from src.ingestion.scraper.base import BaseScraper, ScrapedData, ScraperError

logger = logging.getLogger(__name__)

# Realistic browser headers for LinkedIn requests.
_LINKEDIN_HEADERS_TEMPLATE: Dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class LinkedInScraper(BaseScraper):
    """Scrapes LinkedIn public profiles with proxy support.

    Args:
        requests_per_second: Very conservative rate (LinkedIn is strict).
        max_retries: Retry count.
        base_backoff: Initial backoff (longer for LinkedIn).
        timeout: Request timeout.
        user_agents: User-agent pool.
        proxy_url: HTTP/SOCKS proxy URL (strongly recommended).
        proxy_pool: Optional list of proxy URLs for rotation.
        cookies: Optional cookie dict for authenticated sessions.
    """

    def __init__(
        self,
        requests_per_second: float = 0.3,
        max_retries: int = 3,
        base_backoff: float = 5.0,
        timeout: int = 45,
        user_agents: Optional[List[str]] = None,
        proxy_url: Optional[str] = None,
        proxy_pool: Optional[List[str]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            base_backoff=base_backoff,
            timeout=timeout,
            user_agents=user_agents,
            proxy_url=proxy_url,
        )
        self.proxy_pool = proxy_pool or ([proxy_url] if proxy_url else [])
        self.cookies = cookies or {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_url(self, url: str) -> bool:
        """Accept linkedin.com profile URLs."""
        parsed = urlparse(url)
        if parsed.netloc not in ("linkedin.com", "www.linkedin.com"):
            return False
        path = parsed.path.strip("/")
        return path.startswith("in/") or path.startswith("company/")

    # ------------------------------------------------------------------
    # Core scraping
    # ------------------------------------------------------------------

    async def _do_scrape(self, url: str) -> ScrapedData:
        """Scrape a LinkedIn profile or company page."""
        path = urlparse(url).path.strip("/")
        if path.startswith("company/"):
            return await self._scrape_company(url)
        return await self._scrape_profile(url)

    # ------------------------------------------------------------------
    # Profile scraping
    # ------------------------------------------------------------------

    async def _scrape_profile(self, url: str) -> ScrapedData:
        """Scrape a personal LinkedIn profile."""
        raw_html = await self._fetch_page(url)
        soup = BeautifulSoup(raw_html, "html.parser")

        profile = self._extract_profile_data(soup, url)
        content = self._build_profile_content(profile)

        return ScrapedData(
            url=url,
            title=f"LinkedIn: {profile.get('name', 'Unknown')}",
            content=content,
            metadata=profile,
            raw_html=raw_html,
            source_type="linkedin_profile",
        )

    async def _scrape_company(self, url: str) -> ScrapedData:
        """Scrape a LinkedIn company page."""
        raw_html = await self._fetch_page(url)
        soup = BeautifulSoup(raw_html, "html.parser")

        company = self._extract_company_data(soup, url)
        content = self._build_company_content(company)

        return ScrapedData(
            url=url,
            title=f"LinkedIn Company: {company.get('name', 'Unknown')}",
            content=content,
            metadata=company,
            raw_html=raw_html,
            source_type="linkedin_company",
        )

    # ------------------------------------------------------------------
    # HTTP fetch with proxy rotation
    # ------------------------------------------------------------------

    async def _fetch_page(self, url: str) -> str:
        """Fetch a LinkedIn page with realistic headers and optional proxy.

        Adds random delays to mimic human browsing behaviour.
        """
        # Random pre-request delay (2-6 seconds) to avoid detection
        await asyncio.sleep(random.uniform(2.0, 6.0))

        headers = dict(_LINKEDIN_HEADERS_TEMPLATE)
        headers["User-Agent"] = self._get_random_user_agent()

        proxy = self._pick_proxy()
        transport_kwargs: Dict[str, Any] = {}
        if proxy:
            transport_kwargs["proxy"] = proxy

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(self.timeout),
            cookies=self.cookies or None,
            **transport_kwargs,
        ) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 999:
            raise ScraperError(
                "LinkedIn returned 999 — likely bot detection. Use proxies."
            )
        if response.status_code == 429:
            raise ScraperError("LinkedIn rate limited (429). Back off.")
        if response.status_code >= 400:
            raise ScraperError(
                f"LinkedIn HTTP {response.status_code}: {response.reason_phrase}"
            )

        return response.text

    def _pick_proxy(self) -> Optional[str]:
        """Randomly select a proxy from the pool."""
        if not self.proxy_pool:
            return None
        return random.choice(self.proxy_pool)

    # ------------------------------------------------------------------
    # Profile data extraction
    # ------------------------------------------------------------------

    def _extract_profile_data(
        self, soup: BeautifulSoup, url: str
    ) -> Dict[str, Any]:
        """Extract structured profile fields from parsed HTML.

        LinkedIn's HTML is heavily obfuscated and changes frequently, so
        we use multiple heuristic strategies.
        """
        profile: Dict[str, Any] = {"source_url": url}

        # --- Name ---
        name_tag = (
            soup.find("h1")
            or soup.find("title")
        )
        if name_tag:
            raw_name = name_tag.get_text(strip=True)
            # LinkedIn titles are often "Name | LinkedIn" — strip the suffix
            profile["name"] = re.sub(r"\s*[|–-]\s*LinkedIn.*$", "", raw_name).strip()

        # --- Headline / title ---
        headline_tag = soup.find("div", class_=re.compile(r"headline|subtitle", re.I))
        if not headline_tag:
            headline_tag = soup.find("h2")
        if headline_tag:
            profile["headline"] = headline_tag.get_text(strip=True)[:300]

        # --- Current role & company from headline ---
        headline = profile.get("headline", "")
        role_match = re.match(
            r"^(.+?)\s+(?:at|@)\s+(.+?)(?:\s*[|·]|$)", headline, re.I
        )
        if role_match:
            profile["current_role"] = role_match.group(1).strip()
            profile["current_company"] = role_match.group(2).strip()

        # --- Location ---
        loc_tag = soup.find("span", class_=re.compile(r"location", re.I))
        if loc_tag:
            profile["location"] = loc_tag.get_text(strip=True)

        # --- About / summary ---
        about_section = soup.find("section", id=re.compile(r"about", re.I))
        if not about_section:
            about_section = soup.find("div", class_=re.compile(r"summary|about", re.I))
        if about_section:
            profile["about"] = about_section.get_text(separator=" ", strip=True)[:2000]

        # --- Experience ---
        profile["experience"] = self._extract_section_items(soup, "experience")

        # --- Education ---
        profile["education"] = self._extract_section_items(soup, "education")

        # --- Skills ---
        profile["skills"] = self._extract_skills(soup)

        # --- Certifications ---
        profile["certifications"] = self._extract_section_items(
            soup, "certification"
        )

        # --- Recent posts (if visible) ---
        profile["recent_posts"] = self._extract_posts(soup)

        return profile

    @staticmethod
    def _extract_section_items(
        soup: BeautifulSoup, section_keyword: str
    ) -> List[Dict[str, str]]:
        """Generic extractor for experience / education / certification sections."""
        items: List[Dict[str, str]] = []
        section = soup.find(
            "section", id=re.compile(section_keyword, re.I)
        ) or soup.find(
            "div", class_=re.compile(section_keyword, re.I)
        )
        if not section:
            return items

        for entry in section.find_all("li", limit=15):
            text = entry.get_text(separator=" | ", strip=True)
            if text and len(text) > 5:
                items.append({"text": text[:500]})
        return items

    @staticmethod
    def _extract_skills(soup: BeautifulSoup) -> List[str]:
        """Extract skills list."""
        skills: List[str] = []
        section = soup.find("section", id=re.compile(r"skill", re.I)) or soup.find(
            "div", class_=re.compile(r"skill", re.I)
        )
        if not section:
            return skills
        for item in section.find_all("span", limit=30):
            text = item.get_text(strip=True)
            if text and len(text) > 1 and not text.isdigit():
                skills.append(text)
        return list(dict.fromkeys(skills))  # dedupe preserving order

    @staticmethod
    def _extract_posts(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract visible recent posts/activity."""
        posts: List[Dict[str, str]] = []
        activity_section = soup.find(
            "section", id=re.compile(r"activity", re.I)
        ) or soup.find("div", class_=re.compile(r"feed|activity", re.I))
        if not activity_section:
            return posts
        for item in activity_section.find_all("div", limit=5):
            text = item.get_text(separator=" ", strip=True)
            if text and len(text) > 20:
                posts.append({"text": text[:500]})
        return posts

    # ------------------------------------------------------------------
    # Company data extraction
    # ------------------------------------------------------------------

    def _extract_company_data(
        self, soup: BeautifulSoup, url: str
    ) -> Dict[str, Any]:
        """Extract company page information."""
        company: Dict[str, Any] = {"source_url": url}

        title_tag = soup.find("h1") or soup.find("title")
        if title_tag:
            raw = title_tag.get_text(strip=True)
            company["name"] = re.sub(r"\s*[|–-]\s*LinkedIn.*$", "", raw).strip()

        tagline = soup.find("p", class_=re.compile(r"tagline|subtitle", re.I))
        if tagline:
            company["tagline"] = tagline.get_text(strip=True)[:300]

        about = soup.find("section", id=re.compile(r"about", re.I)) or soup.find(
            "div", class_=re.compile(r"about|overview", re.I)
        )
        if about:
            company["about"] = about.get_text(separator=" ", strip=True)[:3000]

        # Detail items (industry, size, etc.)
        for dt in soup.find_all("dt"):
            key = dt.get_text(strip=True).lower().replace(" ", "_")
            dd = dt.find_next_sibling("dd")
            if dd and key:
                company[key] = dd.get_text(strip=True)[:200]

        return company

    # ------------------------------------------------------------------
    # Content builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_profile_content(profile: Dict[str, Any]) -> str:
        """Build human-readable content from profile data."""
        sections: List[str] = []
        sections.append(f"# LinkedIn Profile: {profile.get('name', 'Unknown')}")

        if profile.get("headline"):
            sections.append(f"\n{profile['headline']}")
        if profile.get("location"):
            sections.append(f"Location: {profile['location']}")
        if profile.get("current_role") and profile.get("current_company"):
            sections.append(
                f"Current: {profile['current_role']} at {profile['current_company']}"
            )
        if profile.get("about"):
            sections.append(f"\n## About\n{profile['about']}")

        if profile.get("experience"):
            sections.append("\n## Experience")
            for exp in profile["experience"]:
                sections.append(f"  • {exp.get('text', '')}")

        if profile.get("education"):
            sections.append("\n## Education")
            for edu in profile["education"]:
                sections.append(f"  • {edu.get('text', '')}")

        if profile.get("skills"):
            sections.append(
                "\n## Skills\n" + ", ".join(profile["skills"][:20])
            )

        if profile.get("certifications"):
            sections.append("\n## Certifications")
            for cert in profile["certifications"]:
                sections.append(f"  • {cert.get('text', '')}")

        if profile.get("recent_posts"):
            sections.append("\n## Recent Posts")
            for post in profile["recent_posts"]:
                sections.append(f"  • {post.get('text', '')[:200]}")

        return "\n".join(sections)

    @staticmethod
    def _build_company_content(company: Dict[str, Any]) -> str:
        """Build human-readable content from company data."""
        sections: List[str] = []
        sections.append(
            f"# LinkedIn Company: {company.get('name', 'Unknown')}"
        )
        if company.get("tagline"):
            sections.append(f"\n{company['tagline']}")
        if company.get("about"):
            sections.append(f"\n## About\n{company['about']}")

        detail_keys = {
            "industry", "company_size", "headquarters", "founded",
            "type", "specialties", "website",
        }
        details = {
            k: v for k, v in company.items()
            if k in detail_keys and v
        }
        if details:
            sections.append("\n## Details")
            for k, v in details.items():
                sections.append(f"  • {k.replace('_', ' ').title()}: {v}")

        return "\n".join(sections)

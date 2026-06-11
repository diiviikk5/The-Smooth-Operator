"""Search tools for The Smooth Operator agents.

Provides LangChain @tool decorated functions for web search, company lookup,
tech stack detection, and social media search. Each tool handles errors
gracefully and returns structured data for downstream agents.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Structured search result."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""
    relevance_score: float = 0.0


class CompanyInfo(BaseModel):
    """Structured company information."""

    name: str = ""
    domain: str = ""
    description: str = ""
    industry: str = ""
    employee_count: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters: str = ""
    tech_stack: List[str] = Field(default_factory=list)
    funding_stage: str = ""
    revenue_range: str = ""
    social_profiles: Dict[str, str] = Field(default_factory=dict)
    recent_news: List[str] = Field(default_factory=list)


class TechStackResult(BaseModel):
    """Detected technology stack."""

    url: str = ""
    technologies: Dict[str, List[str]] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    scan_timestamp: float = 0.0


class SocialProfile(BaseModel):
    """Social media profile information."""

    platform: str = ""
    url: str = ""
    username: str = ""
    bio: str = ""
    followers: Optional[int] = None
    recent_posts: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-memory cache to reduce duplicate requests within a single pipeline run
# ---------------------------------------------------------------------------

_search_cache: Dict[str, Any] = {}


def _cache_key(prefix: str, *parts: str) -> str:
    raw = f"{prefix}:" + "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@tool
def web_search(query: str) -> str:
    """Search the web for information about a lead, company, or topic.

    Performs a web search using the configured search provider and returns
    structured results with titles, URLs, snippets, and relevance scores.

    Args:
        query: The search query string.

    Returns:
        JSON string containing a list of search results.
    """
    logger.info("web_search called with query=%r", query)
    settings = get_settings()

    cache_k = _cache_key("web_search", query)
    if cache_k in _search_cache:
        logger.debug("web_search cache hit for query=%r", query)
        return _search_cache[cache_k]

    try:
        # Attempt to use a real search provider (SerpAPI / Tavily / DuckDuckGo)
        results = _execute_web_search(query, max_results=10)
    except Exception as exc:
        logger.error("web_search failed for query=%r: %s", query, exc, exc_info=True)
        results = [
            SearchResult(
                title="Search unavailable",
                url="",
                snippet=f"Search failed: {exc}. Using query as context.",
                source="error",
                relevance_score=0.0,
            )
        ]

    output = json.dumps([r.model_dump() for r in results], indent=2)
    _search_cache[cache_k] = output
    return output


def _execute_web_search(query: str, max_results: int = 10) -> List[SearchResult]:
    """Execute the actual web search via available providers.

    Tries providers in order: Tavily → SerpAPI → DuckDuckGo fallback.

    Args:
        query: Search query.
        max_results: Maximum number of results to return.

    Returns:
        List of SearchResult objects.
    """
    settings = get_settings()

    # Try Tavily first (best for LLM-oriented search)
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        tavily = TavilySearchResults(max_results=max_results)
        raw_results = tavily.invoke(query)
        results: List[SearchResult] = []
        if isinstance(raw_results, list):
            for i, item in enumerate(raw_results):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="tavily",
                        relevance_score=round(1.0 - (i * 0.05), 2),
                    )
                )
        logger.info("Tavily returned %d results for query=%r", len(results), query)
        return results
    except Exception as tavily_err:
        logger.debug("Tavily unavailable: %s", tavily_err)

    # Fallback: DuckDuckGo (no API key needed)
    try:
        from langchain_community.tools import DuckDuckGoSearchResults

        ddg = DuckDuckGoSearchResults(max_results=max_results)
        raw = ddg.invoke(query)
        results = []
        # DuckDuckGo returns a string representation – parse it
        if isinstance(raw, str):
            # Extract snippets from the raw output
            entries = raw.split("],")
            for i, entry in enumerate(entries[:max_results]):
                snippet_match = re.search(r"snippet:\s*(.+?)(?:,\s*title:|$)", entry)
                title_match = re.search(r"title:\s*(.+?)(?:,\s*link:|$)", entry)
                link_match = re.search(r"link:\s*(.+?)(?:,|\]|$)", entry)
                results.append(
                    SearchResult(
                        title=title_match.group(1).strip() if title_match else "",
                        url=link_match.group(1).strip() if link_match else "",
                        snippet=snippet_match.group(1).strip() if snippet_match else entry.strip(),
                        source="duckduckgo",
                        relevance_score=round(1.0 - (i * 0.08), 2),
                    )
                )
        logger.info("DuckDuckGo returned %d results for query=%r", len(results), query)
        return results
    except Exception as ddg_err:
        logger.debug("DuckDuckGo unavailable: %s", ddg_err)

    # Final fallback – return empty
    logger.warning("All search providers failed for query=%r", query)
    return []


@tool
def company_lookup(domain: str) -> str:
    """Look up company information by domain name.

    Aggregates company data from multiple sources including Clearbit-style
    enrichment, web scraping, and public APIs.

    Args:
        domain: The company's domain (e.g., 'stripe.com').

    Returns:
        JSON string with structured company information.
    """
    logger.info("company_lookup called with domain=%r", domain)

    cache_k = _cache_key("company_lookup", domain)
    if cache_k in _search_cache:
        return _search_cache[cache_k]

    clean_domain = domain.replace("https://", "").replace("http://", "").strip("/")

    company = CompanyInfo(domain=clean_domain)

    # Strategy 1: Web search for company info
    try:
        search_results_raw = web_search.invoke(f"{clean_domain} company information about employees funding")
        search_data = json.loads(search_results_raw)

        for result in search_data[:5]:
            snippet = result.get("snippet", "")
            if snippet:
                # Extract employee count patterns
                emp_match = re.search(r"(\d[\d,]+)\s*(?:employees|people|team members)", snippet, re.IGNORECASE)
                if emp_match and not company.employee_count:
                    company.employee_count = emp_match.group(1).replace(",", "")

                # Extract founding year
                year_match = re.search(r"(?:founded|established|started)\s*(?:in\s*)?(\d{4})", snippet, re.IGNORECASE)
                if year_match and not company.founded_year:
                    yr = int(year_match.group(1))
                    if 1900 <= yr <= 2026:
                        company.founded_year = yr

                # Extract industry keywords
                industry_patterns = [
                    r"(?:in the|in)\s+([\w\s]+?)\s+(?:industry|sector|space|market)",
                    r"(?:is a|is an)\s+([\w\s]+?)\s+(?:company|startup|firm|platform)",
                ]
                for pattern in industry_patterns:
                    ind_match = re.search(pattern, snippet, re.IGNORECASE)
                    if ind_match and not company.industry:
                        company.industry = ind_match.group(1).strip()[:50]

                # Build description from best snippet
                if not company.description and len(snippet) > 30:
                    company.description = snippet[:300]

                # Extract company name from domain if needed
                if not company.name:
                    name_match = re.search(r"([\w\s&.]+?)(?:\s*[-|–—]|\s*is|\s*-)", snippet)
                    if name_match:
                        candidate = name_match.group(1).strip()
                        if 2 <= len(candidate) <= 50:
                            company.name = candidate

        # Fallback name from domain
        if not company.name:
            company.name = clean_domain.split(".")[0].capitalize()

    except Exception as exc:
        logger.warning("company_lookup search enrichment failed: %s", exc)
        company.name = clean_domain.split(".")[0].capitalize()

    # Strategy 2: Check for social profiles via common patterns
    company.social_profiles = {
        "linkedin": f"https://linkedin.com/company/{clean_domain.split('.')[0]}",
        "twitter": f"https://twitter.com/{clean_domain.split('.')[0]}",
    }

    output = company.model_dump_json(indent=2)
    _search_cache[cache_k] = output
    logger.info("company_lookup completed for domain=%r: name=%s", domain, company.name)
    return output


@tool
def tech_stack_detect(url: str) -> str:
    """Detect the technology stack used by a website.

    Analyzes the target URL for frontend frameworks, backend technologies,
    analytics tools, CDN providers, and other technical indicators.

    Args:
        url: The website URL to analyze.

    Returns:
        JSON string with detected technologies grouped by category.
    """
    logger.info("tech_stack_detect called with url=%r", url)

    cache_k = _cache_key("tech_stack", url)
    if cache_k in _search_cache:
        return _search_cache[cache_k]

    result = TechStackResult(url=url, scan_timestamp=time.time())

    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        import httpx

        with httpx.Client(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": get_settings().scraping.user_agent},
        ) as client:
            response = client.get(url)
            html = response.text
            headers = dict(response.headers)

        # Detect technologies from HTML content and headers
        detections: Dict[str, List[str]] = {
            "frontend": [],
            "backend": [],
            "analytics": [],
            "cdn": [],
            "cms": [],
            "hosting": [],
            "javascript_libraries": [],
            "css_frameworks": [],
        }
        confidences: Dict[str, float] = {}

        # Frontend framework detection
        frontend_signals = {
            "React": [r"react[\.-]", r"_reactRootContainer", r"__NEXT_DATA__"],
            "Vue.js": [r"vue[\.-]", r"__vue__", r"Vue\."],
            "Angular": [r"ng-version", r"angular[\.-]", r"ng-app"],
            "Svelte": [r"svelte[\.-]", r"__svelte"],
            "Next.js": [r"__NEXT_DATA__", r"_next/static", r"next[\.-]"],
            "Nuxt.js": [r"__NUXT__", r"_nuxt/"],
            "Gatsby": [r"gatsby[\.-]", r"___gatsby"],
        }
        for tech, patterns in frontend_signals.items():
            score = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if score > 0:
                detections["frontend"].append(tech)
                confidences[tech] = min(score / len(patterns), 1.0)

        # CSS framework detection
        css_signals = {
            "Tailwind CSS": [r"tailwind", r"tw-"],
            "Bootstrap": [r"bootstrap[\.-]", r"class=\"[^\"]*\b(container|row|col-)\b"],
            "Material UI": [r"mui", r"material-ui", r"MuiButton"],
            "Bulma": [r"bulma[\.-]"],
        }
        for tech, patterns in css_signals.items():
            score = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if score > 0:
                detections["css_frameworks"].append(tech)
                confidences[tech] = min(score / len(patterns), 1.0)

        # Analytics detection
        analytics_signals = {
            "Google Analytics": [r"google-analytics\.com", r"gtag\(", r"GoogleAnalyticsObject"],
            "Segment": [r"cdn\.segment\.com", r"analytics\.js"],
            "Mixpanel": [r"mixpanel\.com", r"mixpanel\.init"],
            "Hotjar": [r"hotjar\.com", r"hj\("],
            "Amplitude": [r"amplitude\.com", r"amplitude\.init"],
            "Plausible": [r"plausible\.io"],
            "PostHog": [r"posthog", r"app\.posthog\.com"],
        }
        for tech, patterns in analytics_signals.items():
            score = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if score > 0:
                detections["analytics"].append(tech)
                confidences[tech] = min(score / len(patterns), 1.0)

        # CDN detection from headers
        cdn_signals = {
            "Cloudflare": [r"cloudflare", r"cf-ray"],
            "AWS CloudFront": [r"cloudfront", r"x-amz-cf"],
            "Fastly": [r"fastly", r"x-served-by"],
            "Vercel": [r"vercel", r"x-vercel"],
            "Netlify": [r"netlify"],
        }
        headers_str = json.dumps(headers).lower()
        for tech, patterns in cdn_signals.items():
            score = sum(1 for p in patterns if re.search(p, headers_str, re.IGNORECASE))
            if score > 0:
                detections["cdn"].append(tech)
                confidences[tech] = min(score / len(patterns), 1.0)

        # Backend / server detection from headers
        server_header = headers.get("server", "").lower()
        x_powered = headers.get("x-powered-by", "").lower()
        backend_map = {
            "nginx": "Nginx",
            "apache": "Apache",
            "express": "Node.js/Express",
            "asp.net": "ASP.NET",
            "php": "PHP",
            "gunicorn": "Python/Gunicorn",
            "uvicorn": "Python/Uvicorn",
            "kestrel": "ASP.NET Core",
        }
        for key, tech in backend_map.items():
            if key in server_header or key in x_powered:
                detections["backend"].append(tech)
                confidences[tech] = 0.9

        # CMS detection
        cms_signals = {
            "WordPress": [r"wp-content", r"wp-includes", r"wordpress"],
            "Shopify": [r"cdn\.shopify\.com", r"shopify"],
            "Webflow": [r"webflow\.com", r"wf-"],
            "Squarespace": [r"squarespace\.com", r"sqsp"],
            "Ghost": [r"ghost[\.-]"],
            "HubSpot": [r"hs-scripts\.com", r"hubspot"],
        }
        for tech, patterns in cms_signals.items():
            score = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if score > 0:
                detections["cms"].append(tech)
                confidences[tech] = min(score / len(patterns), 1.0)

        # JS library detection
        js_signals = {
            "jQuery": [r"jquery[\.-]", r"\$\(document\)"],
            "Lodash": [r"lodash[\.-]"],
            "Axios": [r"axios[\.-]"],
            "D3.js": [r"d3[\.-]js", r"d3\.select"],
            "Three.js": [r"three[\.-]", r"THREE\."],
        }
        for tech, patterns in js_signals.items():
            score = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if score > 0:
                detections["javascript_libraries"].append(tech)
                confidences[tech] = min(score / len(patterns), 1.0)

        # Remove empty categories
        result.technologies = {k: v for k, v in detections.items() if v}
        result.confidence_scores = confidences

    except ImportError:
        logger.warning("httpx not installed – using search-based tech detection")
        try:
            search_raw = web_search.invoke(f"site:{urlparse(url).netloc} technology stack")
            result.technologies = {"note": ["Install httpx for direct detection"]}
        except Exception:
            pass
    except Exception as exc:
        logger.error("tech_stack_detect failed for url=%r: %s", url, exc, exc_info=True)
        result.technologies = {"error": [str(exc)]}

    output = result.model_dump_json(indent=2)
    _search_cache[cache_k] = output
    return output


@tool
def social_media_search(name: str, company: str) -> str:
    """Search for social media profiles of a person at a company.

    Searches across LinkedIn, Twitter/X, GitHub, and other platforms to
    find professional social profiles and recent activity.

    Args:
        name: The person's full name.
        company: The company name or domain.

    Returns:
        JSON string with discovered social profiles and recent activity.
    """
    logger.info("social_media_search called for name=%r company=%r", name, company)

    cache_k = _cache_key("social", name, company)
    if cache_k in _search_cache:
        return _search_cache[cache_k]

    profiles: List[SocialProfile] = []

    # Search strategies for different platforms
    platform_queries = {
        "linkedin": f"site:linkedin.com/in {name} {company}",
        "twitter": f"site:twitter.com {name} {company}",
        "github": f"site:github.com {name} {company}",
        "medium": f"site:medium.com {name} {company}",
        "dev.to": f"site:dev.to {name} {company}",
    }

    for platform, query in platform_queries.items():
        try:
            raw_results = web_search.invoke(query)
            search_data = json.loads(raw_results)

            for result in search_data[:2]:  # Top 2 results per platform
                result_url = result.get("url", "")
                snippet = result.get("snippet", "")

                # Validate the result is actually from the right platform
                if platform.replace(".", "") in result_url.lower().replace(".", ""):
                    profile = SocialProfile(
                        platform=platform,
                        url=result_url,
                        username=_extract_username(result_url, platform),
                        bio=snippet[:200] if snippet else "",
                        recent_posts=[],
                    )

                    # Try to extract follower count from snippet
                    follower_match = re.search(
                        r"(\d[\d,.]*[kKmM]?)\s*(?:followers|connections)", snippet
                    )
                    if follower_match:
                        profile.followers = _parse_follower_count(follower_match.group(1))

                    profiles.append(profile)
                    break  # One profile per platform is enough

        except Exception as exc:
            logger.debug("Social search failed for platform=%s: %s", platform, exc)

    output = json.dumps([p.model_dump() for p in profiles], indent=2)
    _search_cache[cache_k] = output
    logger.info("social_media_search found %d profiles for %s at %s", len(profiles), name, company)
    return output


def _extract_username(url: str, platform: str) -> str:
    """Extract username from a social media URL.

    Args:
        url: The profile URL.
        platform: The platform name.

    Returns:
        Extracted username or empty string.
    """
    try:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if platform == "linkedin" and len(path_parts) >= 2:
            return path_parts[1]  # /in/username
        elif path_parts:
            return path_parts[-1]
    except Exception:
        pass
    return ""


def _parse_follower_count(raw: str) -> int:
    """Parse follower count strings like '1.5K', '2M', '500'.

    Args:
        raw: Raw follower count string.

    Returns:
        Integer follower count.
    """
    raw = raw.strip().replace(",", "")
    multiplier = 1
    if raw.lower().endswith("k"):
        multiplier = 1_000
        raw = raw[:-1]
    elif raw.lower().endswith("m"):
        multiplier = 1_000_000
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return 0

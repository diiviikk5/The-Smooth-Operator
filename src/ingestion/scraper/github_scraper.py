"""GitHub profile and repository scraper using the GitHub REST API.

Extracts user profiles, repository metadata, README content, tech-stack
detection, and recent activity — all via the public (or authenticated)
GitHub API with proper rate-limit handling.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from src.ingestion.scraper.base import BaseScraper, ScrapedData, ScraperError

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"

# Common framework / tool markers found in repos
_TECH_INDICATORS: Dict[str, List[str]] = {
    "React": ["react", "jsx", "tsx", "next.js", "nextjs"],
    "Vue": ["vue", "nuxt"],
    "Angular": ["angular"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Express": ["express"],
    "Rails": ["rails", "ruby on rails"],
    "Spring": ["spring", "spring-boot"],
    "Docker": ["docker", "dockerfile", "docker-compose"],
    "Kubernetes": ["kubernetes", "k8s", "helm"],
    "Terraform": ["terraform", ".tf"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "keras"],
    "LangChain": ["langchain"],
    "AWS": ["aws", "amazon web services", "s3", "lambda", "ec2"],
    "GCP": ["gcp", "google cloud", "bigquery"],
    "Azure": ["azure"],
}


class GitHubScraper(BaseScraper):
    """Scrapes GitHub user profiles and repositories via the REST API.

    Args:
        api_token: Optional GitHub personal-access token for higher rate limits.
        requests_per_second: Sustained request rate (GitHub allows 5k/hr authed).
        max_retries: Retry count.
        base_backoff: Initial backoff.
        timeout: Per-request timeout.
        max_repos: Maximum number of repos to fetch for a user.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        requests_per_second: float = 1.0,
        max_retries: int = 3,
        base_backoff: float = 2.0,
        timeout: int = 30,
        max_repos: int = 30,
    ) -> None:
        super().__init__(
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            base_backoff=base_backoff,
            timeout=timeout,
        )
        self.api_token = api_token
        self.max_repos = max_repos

    # ------------------------------------------------------------------
    # URL validation
    # ------------------------------------------------------------------

    async def validate_url(self, url: str) -> bool:
        """Accept github.com user or repo URLs."""
        parsed = urlparse(url)
        if parsed.netloc not in ("github.com", "www.github.com"):
            return False
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        return 1 <= len(parts) <= 2

    # ------------------------------------------------------------------
    # Core scraping
    # ------------------------------------------------------------------

    async def _do_scrape(self, url: str) -> ScrapedData:
        """Route to user or repo scraping based on URL structure."""
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        if len(parts) == 1:
            return await self._scrape_user(parts[0], url)
        return await self._scrape_repo(parts[0], parts[1], url)

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self._get_random_user_agent(),
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _api_get(self, path: str) -> Any:
        """Perform an authenticated GET against the GitHub API.

        Handles 403/429 rate-limit responses by inspecting the
        ``X-RateLimit-Remaining`` header and waiting if needed.
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            resp = await client.get(
                f"{_GITHUB_API}{path}", headers=self._headers()
            )

        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) < 5:
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0"))
            wait = max(0, reset_ts - int(datetime.now(timezone.utc).timestamp())) + 1
            logger.warning("GitHub rate limit nearly exhausted – sleeping %ds", wait)
            import asyncio
            await asyncio.sleep(min(wait, 60))

        if resp.status_code in (403, 429):
            raise ScraperError(
                f"GitHub rate limit hit ({resp.status_code}): {resp.text[:200]}"
            )
        if resp.status_code == 404:
            raise ScraperError(f"GitHub resource not found: {path}")
        if resp.status_code >= 400:
            raise ScraperError(f"GitHub API error {resp.status_code}: {resp.text[:300]}")

        return resp.json()

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    async def _scrape_user(self, username: str, original_url: str) -> ScrapedData:
        """Scrape a GitHub user profile."""
        user = await self._api_get(f"/users/{username}")
        repos = await self._fetch_repos(username)
        events = await self._fetch_events(username)

        languages = self._aggregate_languages(repos)
        tech_stack = self._detect_tech_stack(repos)

        # Build human-readable content
        sections: List[str] = []
        sections.append(f"# GitHub Profile: {user.get('name') or username}")
        if user.get("bio"):
            sections.append(f"\n{user['bio']}")
        if user.get("company"):
            sections.append(f"Company: {user['company']}")
        if user.get("location"):
            sections.append(f"Location: {user['location']}")
        if user.get("blog"):
            sections.append(f"Website: {user['blog']}")

        sections.append(
            f"\nPublic repos: {user.get('public_repos', 0)} | "
            f"Followers: {user.get('followers', 0)} | "
            f"Following: {user.get('following', 0)}"
        )

        if languages:
            sections.append(
                "\n## Top Languages\n"
                + ", ".join(f"{lang} ({pct:.0f}%)" for lang, pct in languages[:10])
            )

        if tech_stack:
            sections.append("\n## Detected Tech Stack\n" + ", ".join(sorted(tech_stack)))

        if repos:
            sections.append("\n## Notable Repositories")
            for repo in sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:10]:
                stars = repo.get("stargazers_count", 0)
                desc = repo.get("description") or "No description"
                sections.append(f"  • {repo['name']} ★{stars} — {desc}")

        if events:
            sections.append("\n## Recent Activity")
            for ev in events[:10]:
                sections.append(f"  • [{ev['type']}] {ev.get('repo', {}).get('name', '')} — {ev.get('created_at', '')[:10]}")

        content = "\n".join(sections)

        metadata: Dict[str, Any] = {
            "github_username": username,
            "name": user.get("name"),
            "bio": user.get("bio"),
            "company": user.get("company"),
            "location": user.get("location"),
            "blog": user.get("blog"),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "created_at": user.get("created_at"),
            "top_languages": languages[:10],
            "tech_stack": sorted(tech_stack) if tech_stack else [],
            "avatar_url": user.get("avatar_url"),
            "hireable": user.get("hireable"),
        }

        return ScrapedData(
            url=original_url,
            title=f"GitHub: {user.get('name') or username}",
            content=content,
            metadata=metadata,
            source_type="github_user",
        )

    # ------------------------------------------------------------------
    # Repository
    # ------------------------------------------------------------------

    async def _scrape_repo(self, owner: str, repo: str, original_url: str) -> ScrapedData:
        """Scrape a GitHub repository."""
        repo_data = await self._api_get(f"/repos/{owner}/{repo}")
        readme_text = await self._fetch_readme(owner, repo)
        languages_raw = await self._api_get(f"/repos/{owner}/{repo}/languages")

        total_bytes = sum(languages_raw.values()) if languages_raw else 1
        languages = [
            (lang, (count / total_bytes) * 100)
            for lang, count in sorted(languages_raw.items(), key=lambda x: x[1], reverse=True)
        ]

        tech_stack = self._detect_tech_from_text(
            f"{repo_data.get('description', '')} {readme_text}"
        )

        sections: List[str] = []
        sections.append(f"# {repo_data['full_name']}")
        if repo_data.get("description"):
            sections.append(f"\n{repo_data['description']}")
        sections.append(
            f"\n★ {repo_data.get('stargazers_count', 0)} stars | "
            f"🍴 {repo_data.get('forks_count', 0)} forks | "
            f"👁 {repo_data.get('watchers_count', 0)} watchers"
        )

        if languages:
            sections.append(
                "\n## Languages\n"
                + ", ".join(f"{lang} ({pct:.1f}%)" for lang, pct in languages)
            )

        if repo_data.get("topics"):
            sections.append("\n## Topics\n" + ", ".join(repo_data["topics"]))

        if tech_stack:
            sections.append("\n## Detected Tech Stack\n" + ", ".join(sorted(tech_stack)))

        if readme_text:
            sections.append(f"\n## README\n\n{readme_text[:5000]}")

        content = "\n".join(sections)

        metadata: Dict[str, Any] = {
            "owner": owner,
            "repo_name": repo,
            "full_name": repo_data["full_name"],
            "description": repo_data.get("description"),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language"),
            "languages": languages,
            "topics": repo_data.get("topics", []),
            "license": (repo_data.get("license") or {}).get("spdx_id"),
            "created_at": repo_data.get("created_at"),
            "updated_at": repo_data.get("updated_at"),
            "default_branch": repo_data.get("default_branch"),
            "is_fork": repo_data.get("fork", False),
            "tech_stack": sorted(tech_stack) if tech_stack else [],
            "homepage": repo_data.get("homepage"),
        }

        return ScrapedData(
            url=original_url,
            title=f"GitHub Repo: {repo_data['full_name']}",
            content=content,
            metadata=metadata,
            source_type="github_repo",
        )

    # ------------------------------------------------------------------
    # Data-fetching helpers
    # ------------------------------------------------------------------

    async def _fetch_repos(self, username: str) -> List[Dict[str, Any]]:
        """Fetch public repos (up to ``max_repos``)."""
        try:
            per_page = min(self.max_repos, 100)
            repos: List[Dict[str, Any]] = await self._api_get(
                f"/users/{username}/repos?per_page={per_page}&sort=pushed&type=owner"
            )
            return repos[: self.max_repos]
        except ScraperError:
            logger.warning("Failed to fetch repos for %s", username)
            return []

    async def _fetch_events(self, username: str) -> List[Dict[str, Any]]:
        """Fetch recent public events."""
        try:
            events: List[Dict[str, Any]] = await self._api_get(
                f"/users/{username}/events/public?per_page=30"
            )
            return events
        except ScraperError:
            logger.warning("Failed to fetch events for %s", username)
            return []

    async def _fetch_readme(self, owner: str, repo: str) -> str:
        """Fetch decoded README content."""
        try:
            import base64
            data = await self._api_get(f"/repos/{owner}/{repo}/readme")
            encoded = data.get("content", "")
            return base64.b64decode(encoded).decode("utf-8", errors="replace")
        except ScraperError:
            logger.debug("No README found for %s/%s", owner, repo)
            return ""

    # ------------------------------------------------------------------
    # Tech-stack analysis
    # ------------------------------------------------------------------

    def _aggregate_languages(
        self, repos: List[Dict[str, Any]]
    ) -> List[tuple[str, float]]:
        """Aggregate language usage across repos.

        Returns:
            Sorted list of ``(language, percentage)`` tuples.
        """
        counts: Counter[str] = Counter()
        for repo in repos:
            lang = repo.get("language")
            if lang:
                counts[lang] += 1
        total = sum(counts.values()) or 1
        return [
            (lang, (count / total) * 100)
            for lang, count in counts.most_common()
        ]

    def _detect_tech_stack(self, repos: List[Dict[str, Any]]) -> set[str]:
        """Heuristically detect technologies from repo descriptions and topics."""
        combined_text = " ".join(
            f"{r.get('description', '')} {' '.join(r.get('topics', []))}"
            for r in repos
        ).lower()
        return self._detect_tech_from_text(combined_text)

    @staticmethod
    def _detect_tech_from_text(text: str) -> set[str]:
        """Match technology indicators against freeform text."""
        text_lower = text.lower()
        detected: set[str] = set()
        for tech, keywords in _TECH_INDICATORS.items():
            if any(kw in text_lower for kw in keywords):
                detected.add(tech)
        return detected

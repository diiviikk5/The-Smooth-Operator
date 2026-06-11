import logging
from typing import Dict, Any
from src.ingestion.scraper.web_scraper import WebScraper
from src.ingestion.scraper.github_scraper import GitHubScraper
from src.ingestion.scraper.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)

class ScraperAgent:
    \"\"\"Agent responsible for scraping raw lead information from multiple sources.\"\"\"

    def __init__(self):
        self.web_scraper = WebScraper()
        self.github_scraper = GitHubScraper()
        self.linkedin_scraper = LinkedInScraper()

    async def run(self, url: str) -> Dict[str, Any]:
        logger.info(f"Running ScraperAgent on URL: {url}")
        
        # Simple routing based on URL domain
        if "github.com" in url:
            data = await self.github_scraper.scrape(url)
        elif "linkedin.com" in url:
            data = await self.linkedin_scraper.scrape(url)
        else:
            data = await self.web_scraper.scrape(url)
            
        return {
            "url": url,
            "title": data.title,
            "content": data.content,
            "metadata": data.metadata,
            "raw_html": data.raw_html,
        }

"""Scraper sub-package for The Smooth Operator ingestion pipeline."""

from src.ingestion.scraper.base import BaseScraper, ScrapedData
from src.ingestion.scraper.github_scraper import GitHubScraper
from src.ingestion.scraper.linkedin_scraper import LinkedInScraper
from src.ingestion.scraper.web_scraper import WebScraper

__all__ = [
    "BaseScraper",
    "ScrapedData",
    "WebScraper",
    "GitHubScraper",
    "LinkedInScraper",
]

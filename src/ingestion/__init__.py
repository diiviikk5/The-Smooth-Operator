"""Ingestion pipeline for The Smooth Operator.

Provides web scraping, document parsing, and text chunking capabilities
for building the knowledge base used by the RAG system.

Modules:
    scraper: Web scrapers for different data sources (web, GitHub, LinkedIn).
    parsers: Document parsers for HTML, PDF, and Markdown formats.
    chunking: Text chunking strategies and embedding generation.
"""

from src.ingestion.chunking.embeddings import EmbeddingGenerator
from src.ingestion.chunking.strategies import (
    BaseChunker,
    Chunk,
    FixedSizeChunker,
    RecursiveChunker,
    SemanticChunker,
    SlidingWindowChunker,
)
from src.ingestion.parsers.html_parser import HTMLParser
from src.ingestion.parsers.markdown_parser import MarkdownParser
from src.ingestion.parsers.pdf_parser import PDFParser
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
    "HTMLParser",
    "PDFParser",
    "MarkdownParser",
    "BaseChunker",
    "Chunk",
    "FixedSizeChunker",
    "RecursiveChunker",
    "SemanticChunker",
    "SlidingWindowChunker",
    "EmbeddingGenerator",
]

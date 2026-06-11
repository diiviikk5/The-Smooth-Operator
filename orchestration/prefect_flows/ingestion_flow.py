import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Basic mock representation of Prefect flow decorators
def task(name=None):
    def decorator(func):
        return func
    return decorator

def flow(name=None):
    def decorator(func):
        return func
    return decorator

@task(name="fetch_lead_urls")
def fetch_lead_urls() -> List[str]:
    logger.info("Fetching lead URLs from datasource")
    return ["https://github.com/john-doe", "https://example.com/company-about"]

@task(name="scrape_and_parse")
def scrape_and_parse(urls: List[str]) -> List[Dict[str, Any]]:
    logger.info(f"Scraping and parsing {len(urls)} URLs")
    return [{"url": u, "content": f"Scraped text from {u}", "metadata": {}} for u in urls]

@task(name="chunk_and_embed")
def chunk_and_embed(parsed_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info(f"Chunking and embedding {len(parsed_docs)} documents")
    return [{"content": doc["content"], "embedding": [0.1] * 384, "metadata": doc["metadata"]} for doc in parsed_docs]

@task(name="upsert_to_db")
def upsert_to_db(embedded_chunks: List[Dict[str, Any]]):
    logger.info(f"Upserting {len(embedded_chunks)} chunks to ChromaDB")

@flow(name="daily-ingestion")
def ingestion_flow():
    urls = fetch_lead_urls()
    docs = scrape_and_parse(urls)
    chunks = chunk_and_embed(docs)
    upsert_to_db(chunks)

if __name__ == "__main__":
    ingestion_flow()

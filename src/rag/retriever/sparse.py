from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SparseRetriever:
    \"\"\"Retrieves documents using sparse term frequency retrieval (BM25).\"\"\"

    def __init__(self):
        self.corpus = []
        self.bm25 = None
        
        try:
            from rank_bm25 import BM25Okapi
            self.BM25Okapi = BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed. SparseRetriever will run in mock mode.")
            self.BM25Okapi = None

    def index(self, documents: List[Dict[str, Any]]):
        self.corpus = documents
        if self.BM25Okapi:
            # Tokenize corpus for BM25
            tokenized_corpus = [doc["content"].lower().split() for doc in documents]
            self.bm25 = self.BM25Okapi(tokenized_corpus)
            logger.info(f"Indexed {len(documents)} documents for BM25")
        else:
            logger.info("Indexed mock corpus for BM25")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.corpus:
            return []

        if self.bm25:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            # Rank documents
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            results = []
            for idx in ranked_indices:
                if scores[idx] > 0:
                    results.append({
                        "id": self.corpus[idx].get("id", ""),
                        "content": self.corpus[idx]["content"],
                        "metadata": self.corpus[idx].get("metadata", {}),
                        "score": float(scores[idx])
                    })
            return results
        else:
            # Mock BM25 retrieval (just return first N matching queries containing words)
            results = []
            words = query.lower().split()
            for doc in self.corpus:
                match_count = sum(1 for w in words if w in doc["content"].lower())
                if match_count > 0:
                    results.append({
                        "id": doc.get("id", ""),
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {}),
                        "score": float(match_count)
                    })
            # Sort by match count
            results = sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
            return results

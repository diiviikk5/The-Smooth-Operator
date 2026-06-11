import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    \"\"\"Reranks retrieved documents using a Cross-Encoder model (e.g. MS-MARCO).\"\"\"

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None

        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            logger.info(f"Loaded CrossEncoder model: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Reranker will run in mock/no-op mode.")

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        if not documents:
            return []

        if self.model:
            # Prepare pairs for scoring
            pairs = [[query, doc["content"]] for doc in documents]
            scores = self.model.predict(pairs)
            
            # Update scores
            for idx, score in enumerate(scores):
                documents[idx]["score"] = float(score)
            
            # Sort by score desc
            reranked = sorted(documents, key=lambda x: x["score"], reverse=True)[:top_k]
            return reranked
        else:
            # Fallback mock reranking (just return documents sorted by their original score)
            logger.debug("Mock reranking executed (no-op)")
            return sorted(documents, key=lambda x: x.get("score", 0.0), reverse=True)[:top_k]

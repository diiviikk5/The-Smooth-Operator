from typing import List, Dict, Any, Optional
from src.rag.retriever.dense import DenseRetriever
from src.rag.retriever.sparse import SparseRetriever

class HybridRetriever:
    \"\"\"Combines Dense (vector) and Sparse (BM25) retrieval using Reciprocal Rank Fusion (RRF).\"\"\"

    def __init__(self, collection_name: str = "leads"):
        self.dense_retriever = DenseRetriever(collection_name)
        self.sparse_retriever = SparseRetriever()
        
    def index_sparse(self, corpus: List[Dict[str, Any]]):
        self.sparse_retriever.index(corpus)

    def retrieve(self, query: str, top_k: int = 5, dense_weight: float = 0.5, rrf_k: int = 60) -> List[Dict[str, Any]]:
        dense_results = self.dense_retriever.retrieve(query, top_k=top_k * 2)
        sparse_results = self.sparse_retriever.retrieve(query, top_k=top_k * 2)

        # Reciprocal Rank Fusion
        rrf_scores = {}
        doc_map = {}

        # Process dense results
        for rank, doc in enumerate(dense_results):
            doc_id = doc["id"] or doc["content"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (dense_weight / (rrf_k + rank + 1))

        # Process sparse results
        for rank, doc in enumerate(sparse_results):
            doc_id = doc["id"] or doc["content"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + ((1 - dense_weight) / (rrf_k + rank + 1))

        # Sort by RRF score
        sorted_docs = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]
        
        fused_results = []
        for doc_id in sorted_docs:
            doc = doc_map[doc_id]
            doc["score"] = rrf_scores[doc_id]
            fused_results.append(doc)

        return fused_results

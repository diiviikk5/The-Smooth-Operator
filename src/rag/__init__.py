"""RAG (Retrieval-Augmented Generation) system for The Smooth Operator.

Provides advanced retrieval capabilities including dense/sparse/hybrid retrieval,
cross-encoder reranking, knowledge graph integration, and a full RAG pipeline.

Modules:
    retriever: Dense, sparse, and hybrid retrieval with reranking.
    knowledge_graph: NetworkX-based knowledge graph for entity relationships.
    vectorstore: ChromaDB vector store integration.
    pipeline: Full RAG pipeline orchestration.
"""

from src.rag.knowledge_graph.graph import KnowledgeGraph
from src.rag.pipeline import RAGPipeline
from src.rag.retriever.dense import DenseRetriever
from src.rag.retriever.hybrid import HybridRetriever
from src.rag.retriever.reranker import CrossEncoderReranker
from src.rag.retriever.sparse import SparseRetriever
from src.rag.vectorstore.chroma_store import ChromaVectorStore

__all__ = [
    "DenseRetriever",
    "SparseRetriever",
    "HybridRetriever",
    "CrossEncoderReranker",
    "KnowledgeGraph",
    "ChromaVectorStore",
    "RAGPipeline",
]

import pytest
from src.rag.retriever.dense import DenseRetriever
from src.rag.retriever.sparse import SparseRetriever
from src.rag.retriever.hybrid import HybridRetriever

def test_dense_retriever_init():
    retriever = DenseRetriever()
    assert retriever.vector_store is not None

def test_sparse_retriever_index():
    retriever = SparseRetriever()
    corpus = [{"id": "1", "content": "RAG systems are great"}]
    retriever.index(corpus)
    assert len(retriever.corpus) == 1

def test_sparse_retriever_query():
    retriever = SparseRetriever()
    corpus = [{"id": "1", "content": "React and Node.js developer"}]
    retriever.index(corpus)
    results = retriever.retrieve("React", top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "1"

def test_hybrid_retriever_rrf():
    retriever = HybridRetriever()
    corpus = [{"id": "1", "content": "React and Node.js developer"}]
    retriever.index_sparse(corpus)
    results = retriever.retrieve("React", top_k=1)
    assert len(results) <= 1

def test_sparse_retriever_empty():
    retriever = SparseRetriever()
    results = retriever.retrieve("Python", top_k=5)
    assert len(results) == 0

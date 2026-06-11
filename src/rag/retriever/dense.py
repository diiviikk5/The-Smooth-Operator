from typing import List, Dict, Any, Optional
from src.rag.vectorstore.chroma_store import ChromaVectorStore
from src.ingestion.chunking.embeddings import EmbeddingGenerator

class DenseRetriever:
    \"\"\"Retrieves documents using dense vector representations (ChromaDB similarity search).\"\"\"

    def __init__(self, collection_name: str = "leads"):
        self.vector_store = ChromaVectorStore(collection_name)
        self.embedding_generator = EmbeddingGenerator()

    def retrieve(self, query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # Generate embedding for the query
        query_embeddings = self.embedding_generator.generate([query])
        
        # Query ChromaDB
        return self.vector_store.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
            where=where
        )

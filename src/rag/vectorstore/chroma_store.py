import logging
from typing import Dict, Any, List, Optional
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    \"\"\"Wrapper around ChromaDB client for vector search operations.\"\"\"

    def __init__(self, collection_name: str = "leads"):
        self.settings = get_settings()
        self.collection_name = collection_name
        self.client = None
        self.collection = None

        try:
            import chromadb
            # Try to connect to Chroma server, fallback to ephemeral/local
            self.client = chromadb.PersistentClient(path="./data/chroma")
            self.collection = self.client.get_or_create_collection(name=collection_name)
            logger.info(f"Initialized ChromaDB with collection: {collection_name}")
        except ImportError:
            logger.warning("chromadb not installed. ChromaVectorStore running in mock mode.")
            # Use basic mock lists
            self.mock_db = []

    def add_documents(self, ids: List[str], documents: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if self.collection:
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
        else:
            logger.debug(f"Mock add {len(ids)} documents")
            for idx, doc_id in enumerate(ids):
                self.mock_db.append({
                    "id": doc_id,
                    "document": documents[idx],
                    "embedding": embeddings[idx],
                    "metadata": metadatas[idx]
                })

    def query(self, query_embeddings: List[List[float]], n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if self.collection:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
            # Normalize structure
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            
            formatted = []
            for i in range(len(ids)):
                formatted.append({
                    "id": ids[i],
                    "content": documents[i],
                    "metadata": metadatas[i],
                    "score": 1.0 - distances[i] # Cosine similarity
                })
            return formatted
        else:
            # Simple mock similarity (just return the first N mock_db entries)
            logger.debug("Mock vector query executed")
            formatted = []
            for item in self.mock_db[:n_results]:
                formatted.append({
                    "id": item["id"],
                    "content": item["document"],
                    "metadata": item["metadata"],
                    "score": 0.85
                })
            return formatted

    def delete(self, ids: List[str]):
        if self.collection:
            self.collection.delete(ids=ids)
        else:
            self.mock_db = [item for item in self.mock_db if item["id"] not in ids]
            
    def count(self) -> int:
        if self.collection:
            return self.collection.count()
        return len(self.mock_db)

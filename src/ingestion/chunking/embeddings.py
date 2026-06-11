import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    \"\"\"Generates vector embeddings for chunks of text.\"\"\"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self.model = None
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded SentenceTransformer model: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Using mock/random embeddings.")

    def generate(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self.model:
            # Generate real embeddings
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Fallback mock embeddings
            logger.debug(f"Generating mock embeddings of dimension {self.dimension} for {len(texts)} texts")
            np.random.seed(42)
            mock_embeddings = np.random.randn(len(texts), self.dimension)
            # L2 normalize
            norms = np.linalg.norm(mock_embeddings, axis=1, keepdims=True)
            normalized = mock_embeddings / norms
            return normalized.tolist()

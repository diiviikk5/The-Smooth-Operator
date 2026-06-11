from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Chunk:
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int = 0

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        pass

class FixedSizeChunker(BaseChunker):
    \"\"\"Splits text into fixed-size chunks with overlapping boundaries.\"\"\"

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        chunks = []
        if not text:
            return chunks

        start = 0
        chunk_idx = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            content = text[start:end]
            
            chunks.append(Chunk(
                content=content,
                metadata=metadata.copy(),
                chunk_index=chunk_idx,
                start_char=start,
                end_char=end,
                token_count=len(content.split()) # Simple word count estimation
            ))
            
            chunk_idx += 1
            if end == text_len:
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks

class RecursiveChunker(BaseChunker):
    \"\"\"Recursively splits text on natural delimiters like paragraphs, sentences, words.\"\"\"

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\\n\\n", "\\n", " ", ""]

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        # Simple implementation of recursive splits
        chunks = []
        raw_splits = text.split("\\n\\n")
        
        current_chunk = []
        current_len = 0
        chunk_idx = 0
        start_char = 0

        for split in raw_splits:
            split_len = len(split)
            if current_len + split_len > self.chunk_size and current_chunk:
                content = "\\n\\n".join(current_chunk)
                chunks.append(Chunk(
                    content=content,
                    metadata=metadata.copy(),
                    chunk_index=chunk_idx,
                    start_char=start_char,
                    end_char=start_char + len(content),
                    token_count=len(content.split())
                ))
                chunk_idx += 1
                start_char += len(content) + 2 # Add paragraph break length
                # Basic overlap strategy
                current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                current_len = sum(len(c) for c in current_chunk)
            
            current_chunk.append(split)
            current_len += split_len

        if current_chunk:
            content = "\\n\\n".join(current_chunk)
            chunks.append(Chunk(
                content=content,
                metadata=metadata.copy(),
                chunk_index=chunk_idx,
                start_char=start_char,
                end_char=start_char + len(content),
                token_count=len(content.split())
            ))

        return chunks

class SlidingWindowChunker(BaseChunker):
    def __init__(self, window_size: int = 3, step_size: int = 1):
        self.window_size = window_size
        self.step_size = step_size

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        sentences = re.split(r'(?<=[.!?])\\s+', text)
        chunks = []
        chunk_idx = 0
        
        for i in range(0, len(sentences), self.step_size):
            window = sentences[i:i + self.window_size]
            if not window:
                break
            content = " ".join(window)
            chunks.append(Chunk(
                content=content,
                metadata=metadata.copy(),
                chunk_index=chunk_idx,
                start_char=0, # Simplified
                end_char=len(content),
                token_count=len(content.split())
            ))
            chunk_idx += 1
            if i + self.window_size >= len(sentences):
                break
                
        return chunks

import re

import pytest
from src.ingestion.chunking.strategies import FixedSizeChunker, RecursiveChunker

def test_fixed_size_chunker_basic():
    chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=10)
    text = "This is a long sentence used to test the fixed size chunking strategy parameters."
    chunks = chunker.chunk(text, {"source": "test"})
    assert len(chunks) > 0
    assert chunks[0].content == text[:100]

def test_fixed_size_chunker_empty():
    chunker = FixedSizeChunker()
    chunks = chunker.chunk("", {})
    assert len(chunks) == 0

def test_fixed_size_chunker_overlap():
    chunker = FixedSizeChunker(chunk_size=20, chunk_overlap=5)
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunker.chunk(text, {})
    assert len(chunks) == 2
    assert chunks[1].start_char == 15

def test_recursive_chunker_paragraphs():
    chunker = RecursiveChunker(chunk_size=50, chunk_overlap=5)
    text = "Paragraph one is short.\\n\\nParagraph two is also short."
    chunks = chunker.chunk(text, {})
    assert len(chunks) == 2
    assert "Paragraph one" in chunks[0].content

def test_recursive_chunker_single():
    chunker = RecursiveChunker(chunk_size=200)
    text = "Hello world"
    chunks = chunker.chunk(text, {})
    assert len(chunks) == 1
    assert chunks[0].content == "Hello world"

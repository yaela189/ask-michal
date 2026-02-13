# -*- coding: utf-8 -*-
import os
import tempfile
import pytest

from server.config import Settings


class TestChunking:
    """Test the text chunking logic without needing ML models."""

    def test_chunk_splits_text(self):
        from server.rag.ingest import PDFIngestor

        # Create a minimal mock to test chunking only
        class MockIngestor:
            def __init__(self):
                self.settings = Settings()
                self.settings.chunk_size = 10
                self.settings.chunk_overlap = 2

            chunk_text = PDFIngestor.chunk_text

        ingestor = MockIngestor()
        text = " ".join(f"word{i}" for i in range(25))
        chunks = ingestor.chunk_text(text)

        assert len(chunks) >= 3
        # First chunk should have 10 words
        assert len(chunks[0].split()) == 10
        # Chunks should overlap
        first_chunk_words = chunks[0].split()
        second_chunk_words = chunks[1].split()
        # Last 2 words of chunk 0 should be first 2 words of chunk 1
        assert first_chunk_words[-2:] == second_chunk_words[:2]

    def test_empty_text_returns_no_chunks(self):
        from server.rag.ingest import PDFIngestor

        class MockIngestor:
            def __init__(self):
                self.settings = Settings()

            chunk_text = PDFIngestor.chunk_text

        ingestor = MockIngestor()
        chunks = ingestor.chunk_text("")
        assert chunks == []

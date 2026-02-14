# -*- coding: utf-8 -*-
import json
import os

import faiss
import numpy as np
from fastembed import TextEmbedding

from server.config import Settings


class KnowledgeRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedding_model = TextEmbedding(settings.embedding_model)
        self._load_index()

    def _load_index(self):
        index_path = self.settings.faiss_index_path
        faiss_file = f"{index_path}.faiss"
        meta_file = f"{index_path}.meta.json"

        if os.path.exists(faiss_file) and os.path.exists(meta_file):
            self.index = faiss.read_index(faiss_file)
            with open(meta_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.index = None
            self.metadata = {"chunks": []}

    def is_ready(self) -> bool:
        return self.index is not None and len(self.metadata["chunks"]) > 0

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """Retrieve the most relevant chunks for a query."""
        if not self.is_ready():
            return []

        k = min(top_k or self.settings.retrieval_top_k, self.index.ntotal)
        if k == 0:
            return []

        query_embedding = list(self.embedding_model.embed([query]))[0]
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        query_embedding = np.array([query_embedding], dtype=np.float32)

        distances, indices = self.index.search(query_embedding, k)

        results = []
        for i in range(len(indices[0])):
            idx = int(indices[0][i])
            if idx < 0 or idx >= len(self.metadata["chunks"]):
                continue
            chunk = self.metadata["chunks"][idx]
            results.append(
                {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "score": float(distances[0][i]),
                }
            )

        return results

    def format_context(self, results: list[dict]) -> str:
        """Format retrieved chunks for injection into Claude's context."""
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(f"[קטע {i}]\n{r['text']}")
        return "\n\n---\n\n".join(parts)

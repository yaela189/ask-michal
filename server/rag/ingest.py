# -*- coding: utf-8 -*-
import hashlib
import json
import os
import re

import faiss
import fitz  # PyMuPDF
import numpy as np
from fastembed import TextEmbedding

from server.config import Settings


class PDFIngestor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedding_model = TextEmbedding(settings.embedding_model)
        # Get dimension from a test embedding
        test = list(self.embedding_model.embed(["test"]))[0]
        self.dimension = len(test)
        self._load_or_create_index()

    def _load_or_create_index(self):
        index_path = self.settings.faiss_index_path
        faiss_file = f"{index_path}.faiss"
        meta_file = f"{index_path}.meta.json"

        if os.path.exists(faiss_file) and os.path.exists(meta_file):
            self.index = faiss.read_index(faiss_file)
            with open(meta_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine with normalized vectors)
            self.metadata = {"chunks": [], "id_map": {}}

    def _save_index(self):
        index_path = self.settings.faiss_index_path
        os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
        faiss.write_index(self.index, f"{index_path}.faiss")
        with open(f"{index_path}.meta.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _strip_headers(text: str) -> str:
        """Remove repeating PDF headers/footers that pollute embeddings."""
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # Skip common IDF document header patterns
            if re.match(r"^הוראת קבע אכ\"?א", stripped):
                continue
            if re.match(r"^-?\s*\d+\s*-?\s*$", stripped):
                continue
            if re.match(r"^מטכ\"?ל אכ\"?א", stripped):
                continue
            if stripped in ("", "-בלמ\"ס-"):
                continue
            # Skip lines that are just unit/branch headers repeated on every page
            if re.match(r"^חט' תכנון", stripped):
                continue
            if re.match(r"^תכנון כ\"א", stripped):
                continue
            if re.match(r"^ענף ושמ\"פ", stripped):
                continue
            if re.match(r"^מדור תע\"ם", stripped):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    def extract_text_from_pdf(self, pdf_path: str) -> list[dict]:
        """Extract text from PDF with page metadata."""
        doc = fitz.open(pdf_path)
        pages = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = self._strip_headers(text)
            if text:
                pages.append(
                    {
                        "text": text,
                        "page": page_num,
                        "source": os.path.basename(pdf_path),
                    }
                )
        doc.close()
        return pages

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks by word count."""
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + self.settings.chunk_size
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            start = end - self.settings.chunk_overlap
        return chunks

    def ingest_pdf(self, pdf_path: str) -> int:
        """Process a single PDF: extract, chunk, embed, store in FAISS."""
        pages = self.extract_text_from_pdf(pdf_path)
        total_chunks = 0

        for page_data in pages:
            chunks = self.chunk_text(page_data["text"])

            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.sha256(
                    f"{page_data['source']}:{page_data['page']}:{i}".encode()
                ).hexdigest()

                # Skip if already indexed
                if chunk_id in self.metadata["id_map"]:
                    continue

                embedding = list(self.embedding_model.embed([chunk]))[0]
                embedding = embedding / np.linalg.norm(embedding)  # normalize for cosine sim
                embedding = np.array([embedding], dtype=np.float32)

                idx = self.index.ntotal
                self.index.add(embedding)

                self.metadata["id_map"][chunk_id] = idx
                self.metadata["chunks"].append(
                    {
                        "id": chunk_id,
                        "text": chunk,
                        "source": page_data["source"],
                        "page": page_data["page"],
                        "chunk_index": i,
                    }
                )
                total_chunks += 1

        self._save_index()
        return total_chunks

    def ingest_directory(self, directory: str) -> dict[str, int]:
        """Process all PDFs in a directory."""
        results = {}
        for filename in sorted(os.listdir(directory)):
            if filename.lower().endswith(".pdf"):
                path = os.path.join(directory, filename)
                count = self.ingest_pdf(path)
                results[filename] = count
        return results

    def clear(self):
        """Clear the entire index."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = {"chunks": [], "id_map": {}}
        self._save_index()

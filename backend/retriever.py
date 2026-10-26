import logging
import os
import numpy as np


class VectorStore:
    """Semantic search. Uses sentence-transformers (local); falls back to TF-IDF if unavailable."""

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.kind = "tfidf"
        if os.getenv("PDFSAGE_EMBEDDER", "auto") != "tfidf":
            try:
                from sentence_transformers import SentenceTransformer
                self._st = SentenceTransformer("all-MiniLM-L6-v2")
                self.kind = "sentence-transformers"
            except Exception as e:
                logging.getLogger(__name__).info("Embedding model unavailable, using TF-IDF: %s", e)
        if self.kind == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._tf = TfidfVectorizer(stop_words="english", sublinear_tf=True, max_features=4000).fit(chunks)
        self.emb = self._enc(chunks)

    def _enc(self, texts):
        if self.kind == "tfidf":
            return self._tf.transform(texts).toarray()
        return self._st.encode(texts, normalize_embeddings=True)

    def search(self, query: str, k: int = 4) -> list[str]:
        scores = self.emb @ self._enc([query])[0]
        return [self.chunks[i] for i in np.argsort(-scores)[:k]]

    def representative(self, n: int = 6) -> list[str]:
        """Chunks closest to the document centroid, kept in document order."""
        scores = self.emb @ self.emb.mean(axis=0)
        return [self.chunks[i] for i in sorted(np.argsort(-scores)[:n])]

    def spread(self, n: int = 6) -> list[str]:
        idx = np.linspace(0, len(self.chunks) - 1, min(n, len(self.chunks))).astype(int)
        return [self.chunks[i] for i in sorted(set(idx))]

"""

EMBEDDING_PROVIDER=fastembed, using BAAI/bge-small-en-v1.5 via
FastEmbed.

"""
import os
import pickle
import numpy as np
from typing import List
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


class LocalTfidfEmbeddings(Embeddings):

    def __init__(self, n_components: int = 128, model_path: str = None):
        self.n_components = n_components
        self.model_path = model_path
        self.vectorizer: TfidfVectorizer = None
        self.svd: TruncatedSVD = None

    def fit(self, texts: List[str]):
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        n_comp = min(self.n_components, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
        n_comp = max(n_comp, 2)
        self.svd = TruncatedSVD(n_components=n_comp, random_state=42)
        self.svd.fit(tfidf_matrix)
        return self

    def _transform(self, texts: List[str]) -> np.ndarray:
        if self.vectorizer is None or self.svd is None:
            raise RuntimeError("Embeddings not fitted/loaded. Run ingest.py first.")
        tfidf_matrix = self.vectorizer.transform(texts)
        vecs = self.svd.transform(tfidf_matrix)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return vecs / norms

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._transform(texts).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._transform([text])[0].tolist()

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "svd": self.svd,
                         "n_components": self.n_components}, f)

    @classmethod
    def load(cls, path: str) -> "LocalTfidfEmbeddings":
        with open(path, "rb") as f:
            state = pickle.load(f)
        obj = cls(n_components=state["n_components"])
        obj.vectorizer = state["vectorizer"]
        obj.svd = state["svd"]
        return obj


def get_embeddings(mode: str = None):
    provider = (mode or os.environ.get("EMBEDDING_PROVIDER", "fastembed")).lower()

    if provider == "local":
        vectorstore_dir = os.environ.get("VECTORSTORE_DIR", "vectorstore")
        embed_path = os.path.join(vectorstore_dir, "tfidf_embeddings.pkl")
        if os.path.exists(embed_path):
            return LocalTfidfEmbeddings.load(embed_path)
        return LocalTfidfEmbeddings()

    elif provider == "fastembed":
        from langchain_community.embeddings import FastEmbedEmbeddings
        model_name = os.environ.get("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
        return FastEmbedEmbeddings(model_name=model_name)

    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")

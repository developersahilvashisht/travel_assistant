"""
Embeddings factory — provider-agnostic on purpose.

Why: the assignment asks for "an appropriate embedding model," but doesn't require
a specific one, and the user doesn't yet have an API key. Rather than blocking the
whole RAG pipeline on that, this module defaults to a small LOCAL embedding backend
(TF-IDF + SVD, via scikit-learn, already a dependency) that needs zero API key and
zero large downloads. It is swappable via one environment variable.

To upgrade later (recommended once you have API access / more disk space):
    EMBEDDING_PROVIDER=huggingface   -> sentence-transformers (local, high quality)
    EMBEDDING_PROVIDER=openai        -> OpenAI text-embedding-3-small (needs OPENAI_API_KEY)
    EMBEDDING_PROVIDER=local (default) -> TF-IDF+SVD, no key needed, weaker semantics

The rest of the app (ingest.py, rag.py) only ever imports `get_embeddings()` from
here, so swapping providers never requires touching retrieval code.
"""
import os
import pickle
import numpy as np
from typing import List
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


class LocalTfidfEmbeddings(Embeddings):
    """A zero-API-key, zero-heavy-download embedding backend.

    Fits a TF-IDF vectorizer + SVD (a form of latent semantic analysis) over the
    knowledge base corpus at index-build time, then projects new text into that
    same space at query time. This is meaningfully weaker than a transformer
    embedding model (it captures word overlap / co-occurrence, not deep semantics),
    but it requires no API key, no GPU, and no multi-hundred-MB model download —
    appropriate for a course assignment demo environment with limited resources.
    Swap to HuggingFaceEmbeddings or OpenAIEmbeddings for production quality.
    """

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
        # normalize so cosine similarity behaves well for FAISS
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
    """Factory: returns a LangChain-compatible Embeddings object based on
    EMBEDDING_PROVIDER env var (or the `mode` argument, which takes priority).
    """
    provider = (mode or os.environ.get("EMBEDDING_PROVIDER", "local")).lower()

    if provider == "local":
        vectorstore_dir = os.environ.get("VECTORSTORE_DIR", "vectorstore")
        embed_path = os.path.join(vectorstore_dir, "tfidf_embeddings.pkl")
        if os.path.exists(embed_path):
            return LocalTfidfEmbeddings.load(embed_path)
        return LocalTfidfEmbeddings()  # unfitted; ingest.py will fit + save it

    elif provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        model_name = os.environ.get("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(model_name=model_name)

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        model_name = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddings(model=model_name)

    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")

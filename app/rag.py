"""
RAG Retrieval
1. Retrieve relevant chunks for each user question
2. Generate answers in the retrieved content
3. Display the source title / source link used for the answer
"""
import os
import re
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.tools import tool


def _bm25_preprocess(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()

from app.embeddings import get_embeddings
from app.ingest import load_documents, chunk_documents

VECTORSTORE_DIR = os.environ.get("VECTORSTORE_DIR", "vectorstore")

_retriever = None


class HybridRetriever:

    def __init__(self, bm25_retriever, vector_retriever, k: int = 4, rrf_k: int = 60):
        self.bm25_retriever = bm25_retriever
        self.vector_retriever = vector_retriever
        self.k = k
        self.rrf_k = rrf_k

    def invoke(self, query: str) -> list[Document]:
        bm25_docs = self.bm25_retriever.invoke(query)
        vector_docs = self.vector_retriever.invoke(query)

        scores = {}
        doc_map = {}
        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content
            scores[key] = scores.get(key, 0) + 1.0 / (self.rrf_k + rank + 1)
            doc_map[key] = doc
        for rank, doc in enumerate(vector_docs):
            key = doc.page_content
            scores[key] = scores.get(key, 0) + 1.0 / (self.rrf_k + rank + 1)
            doc_map[key] = doc

        ranked_keys = sorted(scores, key=scores.get, reverse=True)
        return [doc_map[k] for k in ranked_keys[: self.k]]


def get_retriever(k: int = 5):
    global _retriever
    if _retriever is not None:
        return _retriever

    if not os.path.exists(os.path.join(VECTORSTORE_DIR, "index.faiss")):
        raise RuntimeError(
            f"No vector store found at '{VECTORSTORE_DIR}/'. Run: python3 -m app.ingest"
        )

    embeddings = get_embeddings()
    vs = FAISS.load_local(VECTORSTORE_DIR, embeddings, allow_dangerous_deserialization=True)
    vector_retriever = vs.as_retriever(search_kwargs={"k": k})

    docs = load_documents()
    chunks = chunk_documents(docs)
    bm25_retriever = BM25Retriever.from_documents(chunks, preprocess_func=_bm25_preprocess)
    bm25_retriever.k = k

    _retriever = HybridRetriever(bm25_retriever, vector_retriever, k=k)
    return _retriever


def format_sources(docs: list[Document]) -> str:
    seen = set()
    lines = []
    for d in docs:
        title = d.metadata.get("source_title", d.metadata.get("title", "Unknown source"))
        url = d.metadata.get("source_url", "")
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {title} ({url})" if url else f"- {title}")
    return "\n".join(lines)


@tool
def search_travel_knowledge_base(query: str) -> str:
    """Search the Singapore travel knowledge base for destination facts:
    attractions, neighbourhoods, transportation, culture, food, sample
    itineraries, and indoor/outdoor activity classifications. Use this tool
    for ANY question about Singapore destination knowledge. Do NOT use this
    tool for current/live information like today's weather or currency rates —
    use the weather or currency MCP tools for those instead.
    """
    retriever = get_retriever()
    docs = retriever.invoke(query)

    if not docs:
        return "NO_RESULTS: The knowledge base has no relevant content for this query."

    context_blocks = []
    for i, d in enumerate(docs, 1):
        title = d.metadata.get("title", "Untitled")
        context_blocks.append(f"[Chunk {i} — {title}]\n{d.page_content}")

    context = "\n\n".join(context_blocks)
    sources = format_sources(docs)

    return f"RETRIEVED_CONTEXT:\n{context}\n\nSOURCES:\n{sources}"

"""
RAG Retrieval — implements assignment requirements 5-7:
5. Retrieve relevant chunks for each user question
6. Generate answers grounded in the retrieved content (done by the agent, see agent.py)
7. Display the source title / source link used for the answer

We use a HYBRID retriever: BM25 (keyword/lexical match) + FAISS (vector/semantic
match), combined via LangChain's EnsembleRetriever. This is a standard production
RAG pattern — vector search alone can miss exact-term matches (e.g. a query
containing the literal word "indoor" should reliably surface chunks explicitly
about indoor activities), while BM25 alone misses paraphrases and synonyms.
Combining both gives more robust retrieval than either alone, which matters
especially with our lightweight local embedding backend (see embeddings.py).
"""
import os
import re
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.tools import tool


def _bm25_preprocess(text: str) -> list[str]:
    """Lowercase + strip punctuation before tokenizing.

    NOTE: langchain_community's default BM25 preprocessing is a bare
    `text.split()` — no lowercasing, no punctuation stripping. That silently
    breaks matching (e.g. query "indoor" never matches document token
    "Indoor," or "(Indoor)"). This custom function fixes that.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()

from app.embeddings import get_embeddings
from app.ingest import load_documents, chunk_documents

VECTORSTORE_DIR = os.environ.get("VECTORSTORE_DIR", "vectorstore")

_retriever = None  # module-level cache


class HybridRetriever:
    """Combines BM25 (keyword) and FAISS (vector) retrieval via Reciprocal Rank
    Fusion (RRF) — a simple, well-known way to merge two ranked lists without
    needing comparable similarity scores between the two methods. Each
    document's fused score is the sum of 1/(60 + rank) across the lists it
    appears in; documents found by both methods naturally rank higher.

    Implemented directly (rather than relying on a specific LangChain version's
    EnsembleRetriever, which moved/changed across recent releases) to keep this
    resilient to the LangChain API churn currently underway.
    """

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
    """Builds (once) and returns the hybrid BM25 + FAISS retriever."""
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

    # BM25 needs the raw chunk documents (not just the FAISS index) to build its
    # keyword index, so we re-derive the same chunks used at ingest time.
    docs = load_documents()
    chunks = chunk_documents(docs)
    bm25_retriever = BM25Retriever.from_documents(chunks, preprocess_func=_bm25_preprocess)
    bm25_retriever.k = k

    _retriever = HybridRetriever(bm25_retriever, vector_retriever, k=k)
    return _retriever


def format_sources(docs: list[Document]) -> str:
    """Dedupe and format a human-readable source list for citation."""
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

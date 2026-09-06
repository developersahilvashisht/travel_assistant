"""
RAG Ingestion Pipeline
=======================
Loads travel knowledge-base documents, splits them into chunks, generates
embeddings, and stores them in a FAISS vector store for semantic retrieval.

Run:
    python3 -m app.ingest

Implements RAG requirements 1-4 from the assignment brief:
1. Load travel content from documents        -> load_documents()
2. Divide content into meaningful chunks     -> RecursiveCharacterTextSplitter
3. Generate embeddings for the chunks        -> get_embeddings()
4. Store embeddings in a vector store        -> FAISS
"""
import os
import glob
import frontmatter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app.embeddings import get_embeddings, LocalTfidfEmbeddings

KB_DIR = os.environ.get("KB_DIR", "data/knowledge_base")
VECTORSTORE_DIR = os.environ.get("VECTORSTORE_DIR", "vectorstore")


def load_documents(kb_dir: str = KB_DIR) -> list[Document]:
    """Load every markdown file in the knowledge base, keeping YAML front-matter
    (title, source_title, source_url, category) as metadata for later citation.
    """
    docs = []
    for path in sorted(glob.glob(os.path.join(kb_dir, "*.md"))):
        post = frontmatter.load(path)
        metadata = dict(post.metadata)
        metadata["file"] = os.path.basename(path)
        docs.append(Document(page_content=post.content, metadata=metadata))
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split documents into overlapping chunks along markdown structure where
    possible (headings), falling back to plain recursive character splitting.
    Chunk size is kept moderate so each chunk is a coherent, citeable unit
    (e.g. one neighbourhood's description) rather than a random slice of text.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    return chunks


def build_vectorstore(chunks: list[Document], vectorstore_dir: str = VECTORSTORE_DIR):
    os.makedirs(vectorstore_dir, exist_ok=True)
    texts = [c.page_content for c in chunks]

    embeddings = get_embeddings()
    if isinstance(embeddings, LocalTfidfEmbeddings):
        # local backend must be *fit* on the corpus before it can embed anything
        embeddings.fit(texts)
        embeddings.save(os.path.join(vectorstore_dir, "tfidf_embeddings.pkl"))

    vs = FAISS.from_documents(chunks, embeddings)
    vs.save_local(vectorstore_dir)
    return vs


def main():
    print("Loading knowledge base documents...")
    docs = load_documents()
    print(f"  Loaded {len(docs)} source documents:")
    for d in docs:
        print(f"    - {d.metadata.get('title')} ({d.metadata.get('file')})")

    print("\nChunking documents...")
    chunks = chunk_documents(docs)
    print(f"  Produced {len(chunks)} chunks.")

    print("\nGenerating embeddings and building FAISS vector store...")
    build_vectorstore(chunks)
    print(f"  Vector store saved to '{VECTORSTORE_DIR}/'.")
    print("\nDone. Run the CLI with: python3 -m app.cli")


if __name__ == "__main__":
    main()

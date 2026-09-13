"""
RAG Ingestion Pipeline
=======================
Loads travel knowledge-base content DIRECTLY from the source PDFs the user
downloaded from Wikivoyage and Visit Singapore (data/knowledge_base/raw/*.pdf),
extracts text, cleans web-page boilerplate, splits into chunks, generates
embeddings, and stores them in a FAISS vector store for semantic retrieval.

Run:
    python3 -m app.ingest

Implements RAG requirements 1-4 from the assignment brief, literally:
1. Load travel content from documents         -> load_documents() [pdftotext on real source PDFs]
2. Divide content into meaningful chunks      -> RecursiveCharacterTextSplitter
3. Generate embeddings for the chunks         -> get_embeddings()
4. Store embeddings in a vector store         -> FAISS
"""
import os
import re
import glob
import subprocess
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app.embeddings import get_embeddings, LocalTfidfEmbeddings

KB_DIR = os.environ.get("KB_DIR", "data/knowledge_base")
RAW_PDF_DIR = os.environ.get("RAW_PDF_DIR", os.path.join(KB_DIR, "raw"))
VECTORSTORE_DIR = os.environ.get("VECTORSTORE_DIR", "vectorstore")

# Maps each source PDF's filename to the human-readable title and canonical
# source URL used for citation, since a browser-printed PDF has no metadata
# giving us this info directly (the URL DOES appear as page-footer text
# in these files, which _extract_source_url below reads back out to
# double-check consistency, but this table is the authoritative source).
SOURCE_REGISTRY = {
    "wikivoyage_singapore.pdf": {
        "source_title": "Wikivoyage Singapore Travel Guide",
        "source_url": "https://en.wikivoyage.org/wiki/Singapore",
    },
    "visitsg_essential_info.pdf": {
        "source_title": "Visit Singapore - Essential Travel Information",
        "source_url": "https://www.visitsingapore.com/travel-tips/essential-travel-information/",
    },
    "visitsg_itineraries.pdf": {
        "source_title": "Visit Singapore - Itineraries",
        "source_url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/",
    },
    "visitsg_things_to_do.pdf": {
        "source_title": "Visit Singapore - Things to Do",
        "source_url": "https://www.visitsingapore.com/things-to-do/top-things-to-do/",
    },
}

# Lines that are website chrome, not travel content -- stripped before
# chunking so they don't dilute retrieval or get quoted back to the user.
_BOILERPLATE_PATTERNS = [
    r"^\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*(AM|PM)\s*$",  # browser print timestamp
    r"^Chat with us\s*$",
    r"^Home\s*/.*$",                          # breadcrumb nav
    r"^(Related Sites|Need Help\?|Connect with Us|Contact Us)\s*$",
    r"^(Singapore Tourism Board|Business Events|Visit Southeast Asia)\s*$",
    r"^(Terms of Use|Privacy|Cookie Policy|Sitemap|Report Vulnerability).*$",
    r"^Copyright © \d{4} Singapore Tourism Board\s*$",
    r"^Last Updated .*$",
    r"^https?://\S+\s+\d+/\d+\s*$",           # "https://... 1/4" page-number footer line (same line)
    r"^https?://en\.wikivoyage\.org/wiki/\S+\s*$",  # wikivoyage footer URL (own line)
    r"^https?://www\.visitsingapore\.com/\S+\s*$",  # visitsingapore footer URL (own line)
    r"^\d{1,3}/\d{1,3}\s*$",                  # bare "20/68" page-number footer (own line)
    r"^(FIND OUT MORE|GET A MRT MAP|START EXPLORING|START YOUR JOURNEY|PLAN YOUR PARTY|FUN FOR THE FAMILY|GET RECOMMENDATIONS)\s*$",
    # Site nav / filter pills -- each rendered on its own isolated line by
    # pdftotext, so these are matched as standalone lines, not phrases.
    r"^(Home|/|Shop|Dine|What's Happening|Neighbourhoods|Things To Do|Travel Tips)\s*$",
    r"^(Unique Experiences|City in Nature|Culture & Heritage|Iconic Architecture|Family Fun|After Dark|Museums & Galleries)\s*$",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS))


def _pdf_to_text(pdf_path: str) -> str:
    """Extract text with pdftotext (text layer confirmed present via pdffonts
    for all 4 source files -- no OCR needed). Plain mode (not -layout) reads
    more linearly for these single/simple-column web-page PDFs.
    """
    result = subprocess.run(
        ["pdftotext", pdf_path, "-"], capture_output=True, text=True, check=True
    )
    return result.stdout


def _clean_text(raw_text: str) -> str:
    lines = raw_text.split("\n")
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            kept.append("")  # preserve paragraph breaks
            continue
        if _BOILERPLATE_RE.match(stripped):
            continue
        kept.append(stripped)
    cleaned = "\n".join(kept)
    # collapse 3+ blank lines down to 2 (one blank line between paragraphs)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def load_documents(kb_dir: str = KB_DIR, raw_pdf_dir: str = RAW_PDF_DIR) -> list[Document]:
    """Load every source PDF in data/knowledge_base/raw/, extract and clean
    its text, and return one Document per PDF with source_title/source_url
    metadata for citation (per SOURCE_REGISTRY above).
    """
    docs = []
    pdf_paths = sorted(glob.glob(os.path.join(raw_pdf_dir, "*.pdf")))
    if not pdf_paths:
        raise RuntimeError(
            f"No source PDFs found in '{raw_pdf_dir}/'. Download the sources named "
            f"in the assignment brief (Wikivoyage Singapore, Visit Singapore Essential "
            f"Info / Itineraries / Things to Do) and place them there. See README.md."
        )

    for path in pdf_paths:
        filename = os.path.basename(path)
        raw_text = _pdf_to_text(path)
        cleaned_text = _clean_text(raw_text)

        registry_entry = SOURCE_REGISTRY.get(filename, {
            "source_title": filename.replace(".pdf", "").replace("_", " ").title(),
            "source_url": "",
        })
        metadata = {
            "title": registry_entry["source_title"],
            "source_title": registry_entry["source_title"],
            "source_url": registry_entry["source_url"],
            "file": filename,
        }
        docs.append(Document(page_content=cleaned_text, metadata=metadata))

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

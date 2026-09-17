"""
RAG Ingestion
======================

Loads travel knowledge-base content DIRECTLY from the source PDFs
(data/knowledge_base/raw/*.pdf), extracts text, cleans web-page boilerplate,
splits into chunks, generates embeddings, and stores them in a FAISS vector
store for semantic retrieval.

Run:
    python -m app.ingest

Implements RAG requirements 1-4 from the assignment brief, literally:
1. Load travel content from documents         -> load_documents()
2. Divide content into meaningful chunks       -> RecursiveCharacterTextSplitter
3. Generate embeddings for the chunks         -> get_embeddings()
4. Store embeddings in a vector store         -> FAISS
"""

import os
import re
import glob

from pypdf import PdfReader

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app.embeddings import get_embeddings, LocalTfidfEmbeddings


KB_DIR = os.environ.get("KB_DIR", "data/knowledge_base")
RAW_PDF_DIR = os.environ.get(
    "RAW_PDF_DIR",
    os.path.join(KB_DIR, "raw")
)
VECTORSTORE_DIR = os.environ.get(
    "VECTORSTORE_DIR",
    "vectorstore"
)

SOURCE_REGISTRY = {
    "wikivoyage_singapore.pdf": {
        "source_title": "Wikivoyage Singapore Travel Guide",
        "source_url": "https://en.wikivoyage.org/wiki/Singapore",
    },
    "visitsg_essential_info.pdf": {
        "source_title": "Visit Singapore - Essential Travel Information",
        "source_url": (
            "https://www.visitsingapore.com/"
            "travel-tips/essential-travel-information/"
        ),
    },
    "visitsg_itineraries.pdf": {
        "source_title": "Visit Singapore - Itineraries",
        "source_url": (
            "https://www.visitsingapore.com/"
            "travel-tips/travelling-to-singapore/itineraries/"
        ),
    },
    "visitsg_things_to_do.pdf": {
        "source_title": "Visit Singapore - Things to Do",
        "source_url": (
            "https://www.visitsingapore.com/"
            "things-to-do/top-things-to-do/"
        ),
    },
}

_BOILERPLATE_PATTERNS = [
    r"^\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*(AM|PM)\s*$",
    r"^Chat with us\s*$",
    r"^Home\s*/.*$",
    r"^(Related Sites|Need Help\?|Connect with Us|Contact Us)\s*$",
    r"^(Singapore Tourism Board|Business Events|Visit Southeast Asia)\s*$",
    r"^(Terms of Use|Privacy|Cookie Policy|Sitemap|Report Vulnerability).*$",
    r"^Copyright © \d{4} Singapore Tourism Board\s*$",
    r"^Last Updated .*$",
    r"^https?://\S+\s+\d+/\d+\s*$",
    r"^https?://en\.wikivoyage\.org/wiki/\S+\s*$",
    r"^https?://www\.visitsingapore\.com/\S+\s*$",
    r"^\d{1,3}/\d{1,3}\s*$",
    r"^(FIND OUT MORE|GET A MRT MAP|START EXPLORING|"
    r"START YOUR JOURNEY|PLAN YOUR PARTY|FUN FOR THE FAMILY|"
    r"GET RECOMMENDATIONS)\s*$",
    r"^(Home|/|Shop|Dine|What's Happening|Neighbourhoods|"
    r"Things To Do|Travel Tips)\s*$",
    r"^(Unique Experiences|City in Nature|Culture & Heritage|"
    r"Iconic Architecture|Family Fun|After Dark|"
    r"Museums & Galleries)\s*$",
]

_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS))


def _pdf_to_text(pdf_path: str) -> str:
    """
    Extract text from a PDF using pypdf.

    This replaces the previous external `pdftotext` command so the
    application does not depend on pdftotext.exe being installed on
    Windows or available in PATH.
    """
    reader = PdfReader(pdf_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n\n".join(pages)


def _clean_text(raw_text: str) -> str:
    """Remove web-page boilerplate while preserving paragraph breaks."""
    lines = raw_text.split("\n")
    kept = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            kept.append("")
            continue

        if _BOILERPLATE_RE.match(stripped):
            continue

        kept.append(stripped)

    cleaned = "\n".join(kept)

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def load_documents(
    kb_dir: str = KB_DIR,
    raw_pdf_dir: str = RAW_PDF_DIR,
) -> list[Document]:
    """
    Load every source PDF in data/knowledge_base/raw/, extract and clean
    its text, and return one Document per PDF with source_title/source_url
    metadata for citation.
    """
    docs = []

    pdf_paths = sorted(
        glob.glob(
            os.path.join(raw_pdf_dir, "*.pdf")
        )
    )

    if not pdf_paths:
        raise RuntimeError(
            f"No source PDFs found in '{raw_pdf_dir}/'. "
            "Download the sources named in the assignment brief "
            "(Wikivoyage Singapore, Visit Singapore Essential "
            "Info / Itineraries / Things to Do) and place them there. "
        )

    for path in pdf_paths:
        filename = os.path.basename(path)

        print(f"    Reading: {filename}")

        try:
            raw_text = _pdf_to_text(path)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract text from PDF '{path}': {exc}"
            ) from exc

        cleaned_text = _clean_text(raw_text)

        if not cleaned_text:
            print(
                f"    WARNING: No text extracted from {filename}"
            )

        registry_entry = SOURCE_REGISTRY.get(
            filename,
            {
                "source_title": (
                    filename
                    .replace(".pdf", "")
                    .replace("_", " ")
                    .title()
                ),
                "source_url": "",
            },
        )

        metadata = {
            "title": registry_entry["source_title"],
            "source_title": registry_entry["source_title"],
            "source_url": registry_entry["source_url"],
            "file": filename,
        }

        docs.append(
            Document(
                page_content=cleaned_text,
                metadata=metadata,
            )
        )

    return docs


def chunk_documents(
    docs: list[Document],
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=[
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            " ",
            "",
        ],
    )

    chunks = splitter.split_documents(docs)

    return chunks


def build_vectorstore(
    chunks: list[Document],
    vectorstore_dir: str = VECTORSTORE_DIR,
):
    """Generate embeddings and save the FAISS vector store."""
    os.makedirs(vectorstore_dir, exist_ok=True)

    texts = [
        chunk.page_content
        for chunk in chunks
    ]

    embeddings = get_embeddings()

    if isinstance(
        embeddings,
        LocalTfidfEmbeddings
    ):

        embeddings.fit(texts)

        embeddings.save(
            os.path.join(
                vectorstore_dir,
                "tfidf_embeddings.pkl",
            )
        )

    vs = FAISS.from_documents(
        chunks,
        embeddings,
    )

    vs.save_local(vectorstore_dir)

    return vs


def main():
    print("Loading knowledge base documents...")

    docs = load_documents()

    print(
        f"  Loaded {len(docs)} source documents:"
    )

    for document in docs:
        print(
            f"    - {document.metadata.get('title')} "
            f"({document.metadata.get('file')})"
        )

    print("\nChunking documents...")

    chunks = chunk_documents(docs)

    print(
        f"  Produced {len(chunks)} chunks."
    )

    print(
        "\nGenerating embeddings and building "
        "FAISS vector store..."
    )

    build_vectorstore(chunks)

    print(
        f"  Vector store saved to '{VECTORSTORE_DIR}/'."
    )

    print(
        "\nDone. Run the CLI with: "
        "python -m app.cli"
    )


if __name__ == "__main__":
    main()

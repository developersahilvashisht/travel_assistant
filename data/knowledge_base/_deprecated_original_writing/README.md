# Deprecated — Not Used by the Application

These 5 markdown files were the project's **first-draft knowledge base**:
original writing, researched from public Singapore travel sources but
written in my own words rather than extracted directly from source pages.

They have been **superseded** by direct PDF ingestion (see `../raw/*.pdf`
and `app/ingest.py`), which loads and parses the actual downloaded source
pages — the more literal reading of the assignment's "load travel content
from public documents... for ingestion" requirement.

`app/ingest.py::load_documents()` no longer reads this folder. These files
are kept only for historical reference / comparison, not as part of the
active pipeline.

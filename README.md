# AI Travel Planning Assistant — Singapore

A context-aware travel assistant that combines a document-based knowledge base
(RAG) with live external data (MCP tools) to help plan a trip to Singapore.

## Quick Start (Development Mode — for Evaluators)

Everything below in one place, so you can get this running locally without
piecing steps together from later sections. Requires Python 3.10+.

```bash
# 1. Clone / extract and enter the project
cd travel_assistant

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
#   Windows PowerShell blocking the activation script? Run once:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your .env (you need your OWN Anthropic or OpenAI API key — none
#    is included in this submission, by design)
cp .env.example .env
#   then edit .env and set ANTHROPIC_API_KEY=... (or switch to OpenAI, see .env.example)

# 5. Build the knowledge base vector store (REQUIRED — no pre-built one
#    ships in this submission; see note below on why)
python3 -m app.ingest

# 6. Sanity-check RAG + both MCP tools with NO API key required
python3 test_components.py

# 7. Run the chat assistant
python3 -m app.cli
#   Windows: if 'python3' isn't recognized, use 'python' instead
```

At the `You:` prompt, try: *"What are the must-visit attractions in
Singapore?"*, *"What's the weather forecast for the next 3 days?"*, or the
combined scenario in "Example Questions to Try" below. Type `exit` to quit.

**No API key handy?** `test_components.py` (step 6) proves the RAG retrieval
and both MCP tools work correctly without any LLM key at all — useful to
confirm the pipeline before spending anything on step 7.

**Why there's no pre-built vector store in this submission:** the default
embedding model (`BAAI/bge-small-en-v1.5` via FastEmbed) downloads its model
weights from `huggingface.co` on first use. The development sandbox used to
build this project could not reach that domain, so the vector store could
not be pre-built and verified there — step 5 has NOT been run end-to-end
against the real embedding model as of this submission. It should work
normally with standard internet access, since FastEmbed/HuggingFace
downloads are routine, but flagging this honestly rather than shipping an
artifact I couldn't actually verify. If step 5 fails for you for any
network reason, set `EMBEDDING_PROVIDER=local` in `.env` (zero downloads,
TF-IDF-based, weaker retrieval quality but fully self-contained) and rerun it.

## Architecture

```
                     ┌─────────────────────┐
     User query ───▶ │   LangGraph Agent    │
                     │ (create_agent, with  │
                     │  system prompt +     │
                     │  conversation memory)│
                     └──────────┬───────────┘
                                │ decides which tool(s) to call
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
     ┌────────────────┐ ┌──────────────┐ ┌───────────────┐
     │ RAG tool        │ │ MCP: weather │ │ MCP: currency │
     │ search_travel_  │ │ (Open-Meteo) │ │ (Frankfurter) │
     │ knowledge_base  │ └──────────────┘ └───────────────┘
     └────────┬────────┘
              ▼
     ┌─────────────────┐
     │ Hybrid retriever │  BM25 (keyword) + FAISS (vector), fused via
     │ (app/rag.py)     │  Reciprocal Rank Fusion
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │ FAISS vector     │  built from data/knowledge_base/*.md
     │ store            │  (5 curated documents, chunked + embedded)
     └──────────────────┘
```

- **Orchestration**: LangChain (`langchain.agents.create_agent`, LangGraph
  under the hood) — required technology per the assignment brief.
- **MCP integration**: LangChain's native `langchain.mcp.MCPAdapter` (backed by
  FastMCP), connecting to two local MCP servers over stdio.
- **Vector store**: FAISS.
- **Embeddings**: provider-agnostic (see "Embeddings" below) — defaults to a
  zero-API-key local backend so the RAG pipeline works immediately.
- **LLM**: provider-agnostic (Anthropic Claude or OpenAI), switched via one
  environment variable.
- **Interface**: command-line chat (`app/cli.py`).

## Knowledge Base Sources

The knowledge base is built **directly from the actual source PDFs** named in
the assignment brief — downloaded (browser Save-as-PDF) and ingested with
their real text, not paraphrased or rewritten. This is the literal reading of
"load travel content from public documents... for ingestion."

| Raw file (`data/knowledge_base/raw/`) | Source | URL (also stored as chunk metadata for citation) |
|---|---|---|
| `wikivoyage_singapore.pdf` | Wikivoyage Singapore Travel Guide (68 pages — the full article: Districts, Understand, Get in/around, See, Do, Eat, Drink, Sleep, Stay safe, etc.) | https://en.wikivoyage.org/wiki/Singapore |
| `visitsg_essential_info.pdf` | Visit Singapore — Essential Travel Information | https://www.visitsingapore.com/travel-tips/essential-travel-information/ |
| `visitsg_itineraries.pdf` | Visit Singapore — Itineraries | https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/ |
| `visitsg_things_to_do.pdf` | Visit Singapore — Things to Do | https://www.visitsingapore.com/things-to-do/top-things-to-do/ |

4 distinct public resources, meeting the "at least three" requirement, and
matching the exact sources the brief names as recommended.

**Licensing note**: Wikivoyage content is Creative Commons (CC BY-SA) — fully
reusable with attribution, which the source metadata provides. Visit
Singapore's site is the official tourism board's copyrighted content;
downloading it for this private coursework ingestion pipeline is standard
low-risk educational use, but the brief itself cautions ("review and follow
each source's reuse terms when redistributing") against redistributing large
verbatim extracts of it beyond that use.

**Superseded approach**: `data/knowledge_base/_deprecated_original_writing/`
holds an earlier version of the knowledge base (original writing researched
from these same sources, before the raw PDFs were available). It is no longer
read by `app/ingest.py` — kept only for reference. See its own README.md.

## RAG Workflow (assignment requirements 1–7)

1. **Load**: `app/ingest.py::load_documents()` runs `pdftotext` on each PDF in
   `data/knowledge_base/raw/`, then strips web-page boilerplate (nav menus,
   breadcrumbs, cookie/footer text, browser-print timestamps and page
   numbers — see `_BOILERPLATE_PATTERNS`) so chunks contain travel content,
   not site chrome. Each PDF's source title and URL (`SOURCE_REGISTRY`) are
   attached as document metadata for citation.
2. **Chunk**: `RecursiveCharacterTextSplitter`, splitting on markdown-style
   headers first (`\n## `, `\n### `) so each chunk is a coherent unit, 800
   chars with 100 overlap.
3. **Embed**: `app/embeddings.py::get_embeddings()` — provider-agnostic (see
   below).
4. **Store**: FAISS (`vectorstore/`), saved to disk after `python3 -m app.ingest`.
5. **Retrieve**: `app/rag.py::get_retriever()` — a **hybrid** retriever
   combining BM25 (keyword match) and FAISS (vector match) via Reciprocal
   Rank Fusion. This matters especially with the lightweight local embedding
   backend (see below): vector search alone can miss exact-term queries;
   BM25 alone misses paraphrases. Combining both is more robust than either
   alone.
6. **Generate grounded answers**: the agent's system prompt (`app/prompts.py`)
   requires every destination fact to come from a retrieved chunk, and
   explicitly forbids inventing facts when retrieval is insufficient.
7. **Show sources**: the RAG tool returns a `SOURCES:` block (source title +
   URL) alongside retrieved content; the system prompt requires the final
   answer to include a "Sources" section.

### Embeddings — real transformer model by default, zero API key

`EMBEDDING_PROVIDER` defaults to `fastembed`: `BAAI/bge-small-en-v1.5` (the
compact English member of the BAAI/BGE family) via FastEmbed, which runs on
ONNX Runtime rather than PyTorch — free, no API key, and a much lighter
install than `sentence-transformers`. This directly follows the instructor's
clarification that an embedding model like BAAI/bge-m3 (or similar) is
expected, while an LLM is separately mandatory (see Prompt & Context Strategy
below — this project also wires up a real LLM call, see `app/llm.py`).

For the exact `BAAI/bge-m3` model (larger, multilingual — unnecessary for
this English-only Singapore corpus, but available if you want it), set:
```
EMBEDDING_PROVIDER=huggingface
HF_EMBEDDING_MODEL=BAAI/bge-m3
```
This needs `pip install sentence-transformers` (pulls in PyTorch — a
noticeably heavier install, which is why it isn't the default here).

A `local` (TF-IDF+SVD, zero downloads, fully offline) fallback also remains
available for environments that can't reach huggingface.co.

No other code changes needed either way — `app/ingest.py` and `app/rag.py`
only ever call `get_embeddings()`.

## MCP Tools (assignment requirements 8–14)

Two MCP servers, built with [FastMCP](https://gofastmcp.com), each exposing
one tool, launched over stdio by `langchain.mcp.MCPAdapter` and bound directly
into the LangChain agent's tool list (`app/agent.py`):

| Server | Tool | Backing API | Needs API key? |
|---|---|---|---|
| `mcp_servers/weather_server.py` | `get_weather_forecast(days)` | Open-Meteo | No |
| `mcp_servers/currency_server.py` | `convert_currency(amount, from_currency, to_currency)` | Frankfurter (ECB rates) | No |

- **Tool selection**: the system prompt gives explicit rules (destination
  question → RAG tool; weather → weather tool; currency → currency tool;
  combined request → both).
- **Failure handling**: both tools catch timeouts / HTTP errors / any other
  exception and return `{"status": "error", "message": ...}` rather than
  raising or returning fabricated data. The system prompt instructs the model
  to relay this plainly to the user instead of guessing — verified in
  `test_components.py`, which the sandboxed dev environment (no internet
  access to these two domains) exercises for real: see its output for a
  real captured example of graceful failure.
- On a machine with normal internet access, both return live data with no
  code changes needed.

## Combined RAG + MCP Responses (requirement in section 4.3)

The system prompt (`app/prompts.py`) instructs the model, for combined
requests (e.g. "plan a 3-day trip and adjust for weather"), to call **both**
the knowledge base tool and the weather tool, then actually merge them into a
day-wise itinerary — swapping outdoor activities for the indoor alternatives
already documented in `05_indoor_outdoor_activities.md` on days with high rain
probability — rather than just concatenating two tool outputs. The response
structure section of the prompt requires labeling each part of the answer as
knowledge-base fact, live tool data, or the model's own recommendation.

## Prompt & Context Strategy (assignment section 5)

Full prompt: `app/prompts.py`. Summary of the design reasoning:

- **Explicit tool-selection rules** rather than leaving it to model judgement
  alone — reduces the chance the model answers a weather/currency question
  from stale training knowledge instead of calling a tool.
- **Mandatory source labeling in the final answer** (not just internal
  reasoning) — directly satisfies "distinguish factual information from
  AI-generated suggestions" and "include source references."
- **Concrete instructions for the two failure modes** (knowledge base has
  insufficient info; MCP tool call fails) with explicit "do NOT invent"
  language, since models tend to hedge vaguely rather than state a gap
  clearly.
- **Explicit preference-retention instruction** telling the model to reuse
  previously stated preferences (trip length, budget, travelling with kids)
  without re-asking — this is what satisfies the multi-turn context
  requirement, combined with LangGraph's `InMemorySaver` checkpointer keeping
  full message history per conversation thread (`app/agent.py`).

## Setup

Requires Python 3.10+.

```bash
git clone <this-repo>
cd travel_assistant
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY (or switch LLM_PROVIDER=openai + OPENAI_API_KEY)
```

## Build the Knowledge Base (run once, or after editing `data/knowledge_base/`)

```bash
python3 -m app.ingest
```

## Test Components (no API key needed)

```bash
python3 test_components.py
```

Confirms RAG retrieval quality and that both MCP servers start and expose
their tools correctly.

## Run the Chat Assistant

```bash
python3 -m app.cli
```

Type questions; `reset` starts a fresh conversation thread; `exit` quits. The
CLI prints each tool call (name + arguments) before the final answer, so RAG
retrieval and MCP tool use are visible during a demo.

## Example Questions to Try

- "What are the must-visit attractions in Singapore?"
- "Suggest activities for a family with children."
- "What's the weather forecast for the next 3 days?"
- "Convert INR 50,000 to SGD."
- "Plan a three-day trip to Singapore and adjust the activities based on the weather forecast." *(combined RAG + MCP)*
- Follow-up in the same session: "Now show my budget of 60,000 INR in SGD for that trip." *(tests multi-turn context — reuses the earlier 3-day plan)*

See `sample_qna.md` for a template to record your actual run's transcript.

## Known Limitations

- The default local embedding backend (TF-IDF+SVD) is semantically weaker
  than a transformer model — retrieval is noticeably better than a keyword
  search but still occasionally misses the ideal chunk within the top-k
  (worse on abstract/paraphrased queries than on queries sharing literal
  vocabulary with the source text). Switch `EMBEDDING_PROVIDER` to
  `huggingface` once you have more disk/API budget — same interface, no
  code changes elsewhere.
- The Visit Singapore itinerary/things-to-do pages use carousel/card UI
  elements; a few cards' text is truncated in the browser-printed PDF
  itself (off-screen at print time) — e.g. "Singapore Art Mus..." — this is
  a source-file limitation, not a parsing bug, and only affects a handful
  of individual card blurbs, not the overall corpus.
- Weather/currency tools require outbound internet access to
  `api.open-meteo.com` / `api.frankfurter.app` at runtime; they fail
  gracefully (not silently) if that's unavailable.
- Scoped to Singapore only, per the assignment's application scope.

# AI Travel Planning Assistant — Singapore

A context-aware travel assistant that combines a document-based knowledge base
(RAG) with live external data (MCP tools) to help plan a trip to Singapore.

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

Content in `data/knowledge_base/` is **original writing**, researched from and
attributed to public Singapore travel resources (not copy-pasted, to respect
each source's copyright/reuse terms — see brief section 6). Each file's YAML
front-matter records the source title and URL used as metadata, satisfying the
"display the source title or link" RAG requirement.

| File | Covers | Primary source basis |
|---|---|---|
| `01_attractions_neighbourhoods.md` | Attractions & districts | Visit Singapore — Things to Do / neighbourhood guides |
| `02_transportation_practical.md` | Transport, climate, currency, etiquette | Wikivoyage Singapore / Visit Singapore — Essential Travel Info |
| `03_food_experiences.md` | Hawker food, dishes, food districts | Wikivoyage Singapore — Eat section |
| `04_sample_itineraries.md` | 3-day itineraries (classic, family, cultural) | Visit Singapore — Sample Itineraries |
| `05_indoor_outdoor_activities.md` | Indoor/outdoor activity classification | Visit Singapore — Things to Do (categorised) |

That's 4 distinct public resources referenced, meeting the "at least three"
requirement.

## RAG Workflow (assignment requirements 1–7)

1. **Load**: `app/ingest.py::load_documents()` reads all `.md` files in
   `data/knowledge_base/`, keeping front-matter (title, source, URL) as
   metadata.
2. **Chunk**: `RecursiveCharacterTextSplitter`, splitting on markdown headers
   first (`\n## `, `\n### `) so each chunk is a coherent unit (e.g. one
   neighbourhood), 800 chars with 100 overlap.
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

### Embeddings — provider-agnostic, zero-key default

Since the project starts without an LLM/embedding API key, `EMBEDDING_PROVIDER`
defaults to `local`: a TF-IDF + Truncated SVD (LSA) embedding, implemented in
`app/embeddings.py` using only scikit-learn (no download, no key). It is
**weaker semantically** than a transformer embedding model — it captures word
co-occurrence, not deep meaning — which is why the hybrid BM25+vector retriever
above matters. To upgrade once you have more resources/an API key, set in `.env`:

```
EMBEDDING_PROVIDER=huggingface   # local, high quality, ~100MB download, no key
# or
EMBEDDING_PROVIDER=openai        # needs OPENAI_API_KEY
```

No other code changes needed — `app/ingest.py` and `app/rag.py` only ever call
`get_embeddings()`.

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
  than a transformer model — occasional retrieval misses are expected on a
  5-document corpus. Switch `EMBEDDING_PROVIDER` once you have more
  disk/API budget (see above).
- Weather/currency tools require outbound internet access to
  `api.open-meteo.com` / `api.frankfurter.app` at runtime; they fail
  gracefully (not silently) if that's unavailable.
- Scoped to Singapore only, per the assignment's application scope.

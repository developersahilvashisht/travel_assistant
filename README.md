# AI Travel Planning Assistant — Singapore

A context-aware travel assistant that combines a document-based knowledge base
(RAG) with live external data (MCP tools) to help plan a trip to Singapore.

Github repo : https://github.com/developersahilvashisht/travel_assistant

Demo Video : https://nagarro-my.sharepoint.com/:v:/p/sahil01/IQDdVVX_KyYUSr9hwMrrtrrgAeOkLKvYkcIpQvTN7oTXAmE?e=5muEbs

```bash

cd travel_assistant

python3 -m venv venv

pip install -r requirements.txt

python3 -m app.ingest

python3 test_components.py

python3 -m app.cli
```

At the `You:` prompt, try: *"What are the must-visit attractions in
Singapore?"*, *"What's the weather forecast for the next 3 days?"*, or the
combined scenario in "Example Questions to Try" below. Type `exit` to quit.


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
     │ Hybrid retriever │ 
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │ FAISS vector     │  built from data/knowledge_base/*.md
     │ store            │  (5 documents, chunked + embedded)
     └──────────────────┘
```

- **Orchestration**: LangChain (`langchain.agents.create_agent`
- **MCP integration**: LangChain's native `langchain.mcp.MCPAdapter` (backed by
  FastMCP), connecting to two local MCP servers.
- **Vector store**: FAISS.
- **Embeddings**: `BAAI/bge-small-en-v1.5` via FastEmbed
- **LLM**:Gemini-> Gemini 3.6 Flash(`app/llm.py`).
- **Interface**: command-line chat (`app/cli.py`).

## Knowledge Base Sources

The knowledge base is built **directly from the source PDFs** — downloaded (browser Save-as-PDF) and ingested with
their real text. This is the literal reading of
"load travel content from public documents... for ingestion."

| Raw file (`data/knowledge_base/raw/`) | Source | URL (also stored as chunk metadata for citation) |
|---|---|---|
| `wikivoyage_singapore.pdf` | Wikivoyage Singapore Travel Guide (68 pages — the full article: Districts, Understand, Get in/around, See, Do, Eat, Drink, Sleep, Stay safe, etc.) | https://en.wikivoyage.org/wiki/Singapore |
| `visitsg_essential_info.pdf` | Visit Singapore — Essential Travel Information | https://www.visitsingapore.com/travel-tips/essential-travel-information/ |
| `visitsg_itineraries.pdf` | Visit Singapore — Itineraries | https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/ |
| `visitsg_things_to_do.pdf` | Visit Singapore — Things to Do | https://www.visitsingapore.com/things-to-do/top-things-to-do/ |


## RAG Workflow

1. **Load**: `app/ingest.py::load_documents()` runs `pdftotext` on each PDF in
   `data/knowledge_base/raw/`, then strips web-page so chunks contain travel content.
    Each PDF's source title and URL (`SOURCE_REGISTRY`) are
   attached as document metadata for citation.
2. **Embed**: `app/embeddings.py::get_embeddings()` 
3. **Store**: FAISS (`vectorstore/`), saved to disk after `python -m app.ingest`.
5. **Retrieve**: `app/rag.py::get_retriever()` — a **hybrid** retriever
   combining BM25 (keyword match) and FAISS (vector match).
6. **Generate answers**: the agent's system prompt (`app/prompts.py`)
   requires every destination fact to come from a retrieved chunk.
7. **Show sources**: the RAG tool returns a `SOURCES:` block (source title +
   URL) alongside retrieved content.

### Embeddings

`EMBEDDING_PROVIDER` defaults to `fastembed`: `BAAI/bge-small-en-v1.5` via FastEmbed, which runs on
ONNX Runtime.


## MCP Tools

Two MCP servers, built with [FastMCP] and bound directly
into the LangChain agent's tool list (`app/agent.py`):

| Server | Tool | Backing API |
|---|---|---|---|
| `mcp_servers/weather_server.py` | `get_weather_forecast(days)` | Open-Meteo |
| `mcp_servers/currency_server.py` | `convert_currency(amount, from_currency, to_currency)` | Frankfurter (ECB rates) |


## Setup

Requires Python 3.10+.

```bash
git clone repo
cd travel_assistant
python3 -m venv venv
pip install -r requirements.txt
```

## Build the Knowledge Base

```bash
python3 -m app.ingest
```

## Run the Chat Assistant

```bash
python3 -m app.cli
```

Type questions; `reset` starts a fresh conversation thread; `exit` quits. The
CLI prints each tool call (name + arguments) before the final answer.

## Example Questions to Try

- "What are the must-visit attractions in Singapore?"
- "Suggest activities for a family with children."
- "What's the weather forecast for the next 3 days?"
- "Convert INR 50,000 to SGD."
- "Plan a three-day trip to Singapore and adjust the activities based on the weather forecast." *(combined RAG + MCP)*
- Follow-up in the same session: "Now show my budget of 60,000 INR in SGD for that trip."

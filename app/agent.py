"""
Agent Orchestration
=====================
Wires together:
- The RAG tool (search_travel_knowledge_base) from app/rag.py
- Two MCP tools (weather, currency) served by mcp_servers/*.py, connected via
  LangChain's native MCP adapter (langchain.mcp.MCPAdapter, backed by FastMCP)
- The system prompt from app/prompts.py
- An LLM from app/llm.py (provider-agnostic)
- A LangGraph in-memory checkpointer, giving the agent multi-turn conversation
  memory keyed by a thread_id — this satisfies the "multi-turn conversation
  with retained context" acceptance criterion.

This module exposes an async context manager, `travel_agent()`, so the MCP
subprocess connections are properly opened/closed around a chat session.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from langgraph.checkpoint.memory import InMemorySaver

from app.llm import get_llm
from app.prompts import SYSTEM_PROMPT
from app.rag import search_travel_knowledge_base

MCP_SERVERS_DIR = Path(__file__).resolve().parent.parent / "mcp_servers"


@asynccontextmanager
async def travel_agent():
    """Async context manager yielding a ready-to-use LangGraph agent.

    Usage:
        async with travel_agent() as (agent, config):
            result = await agent.ainvoke({"messages": [...]}, config=config)
    """
    weather_path = MCP_SERVERS_DIR / "weather_server.py"
    currency_path = MCP_SERVERS_DIR / "currency_server.py"

    async with MCPAdapter(weather_path) as weather_adapter, \
               MCPAdapter(currency_path) as currency_adapter:

        mcp_tools = await weather_adapter.list_tools() + await currency_adapter.list_tools()
        all_tools = [search_travel_knowledge_base] + mcp_tools

        llm = get_llm()
        checkpointer = InMemorySaver()

        agent = create_agent(
            model=llm,
            tools=all_tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

        yield agent


def new_thread_config(thread_id: str = "default-session"):
    """LangGraph config dict that ties a conversation to a persistent thread_id,
    so the checkpointer retains message history across turns for that thread."""
    return {"configurable": {"thread_id": thread_id}}

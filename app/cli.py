"""
Command-Line Chat Interface
==============================
Run:
    python3 -m app.cli

Type your travel questions; type 'exit' or 'quit' to stop, 'reset' to start
a fresh conversation thread (clears memory).

This CLI prints which tools the agent calls (and with what arguments) before
showing the final answer, so RAG retrieval and MCP tool use are visible and
demonstrable — useful both for your own debugging and for the assignment's
"demonstration showing RAG, MCP, a combined response, and conversational
context" deliverable.
"""
import asyncio
import sys
import uuid

from dotenv import load_dotenv
load_dotenv()

from app.agent import travel_agent, new_thread_config

BANNER = """
==========================================================
  Singapore AI Travel Planning Assistant  (CLI)
==========================================================
Ask about attractions, neighbourhoods, food, transport,
itineraries, weather, or currency conversion for Singapore.

Example questions:
  - What are the must-visit attractions in Singapore?
  - What's the weather forecast for the next 3 days?
  - Convert INR 50000 to SGD
  - Plan a 3-day trip and adjust it based on the weather

Commands: 'reset' (new conversation), 'exit' / 'quit'
==========================================================
"""


def print_tool_call(name: str, args: dict):
    print(f"\n  [tool call] {name}({args})")


async def run_turn(agent, config, user_input: str):
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
    )
    messages = result["messages"]

    # Surface any tool calls that happened during this turn, for transparency
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                print_tool_call(tc["name"], tc.get("args", {}))

    final_message = messages[-1]
    return final_message.content


async def main():
    print(BANNER)
    thread_id = str(uuid.uuid4())
    config = new_thread_config(thread_id)

    async with travel_agent() as agent:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            if user_input.lower() == "reset":
                thread_id = str(uuid.uuid4())
                config = new_thread_config(thread_id)
                print("(Conversation reset — starting a new thread.)")
                continue

            try:
                answer = await run_turn(agent, config, user_input)
                print(f"\nAssistant: {answer}")
            except Exception as e:
                print(f"\n[Error] {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio


def test_rag():
    print("=" * 60)
    print("TESTING RAG RETRIEVAL")
    print("=" * 60)
    from app.rag import search_travel_knowledge_base

    questions = [
        "What are the must-visit attractions in Singapore?",
        "How can a tourist travel around Singapore?",
        "Suggest activities for a family with children",
        "Create a three-day sightseeing itinerary",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        result = search_travel_knowledge_base.invoke({"query": q})
        print(result[:400], "...\n" if len(result) > 400 else "")


async def test_mcp_servers():
    print("=" * 60)
    print("TESTING MCP SERVERS")
    print("=" * 60)
    from fastmcp import Client
    from mcp_servers.weather_server import mcp as weather_mcp
    from mcp_servers.currency_server import mcp as currency_mcp

    async with Client(weather_mcp) as client:
        tools = await client.list_tools()
        print(f"\nWeather server exposes: {[t.name for t in tools]}")
        result = await client.call_tool("get_weather_forecast", {"days": 3})
        data = result.data if hasattr(result, "data") else result
        print("Weather tool result:", data)
        if isinstance(data, dict) and data.get("status") == "error":
            print("  (This is EXPECTED in a sandboxed/offline environment without "
                  "internet access to api.open-meteo.com. On your machine with "
                  "normal internet, this will return a real forecast.)")

    async with Client(currency_mcp) as client:
        tools = await client.list_tools()
        print(f"\nCurrency server exposes: {[t.name for t in tools]}")
        result = await client.call_tool(
            "convert_currency", {"amount": 50000, "from_currency": "INR", "to_currency": "SGD"}
        )
        data = result.data if hasattr(result, "data") else result
        print("Currency tool result:", data)
        if isinstance(data, dict) and data.get("status") == "error":
            print("  (This is EXPECTED without internet access to "
                  "api.frankfurter.app. On your machine it will return a real rate.)")


def main():
    test_rag()
    asyncio.run(test_mcp_servers())
    print("\n" + "=" * 60)
    print("Component tests complete. If RAG results look relevant and both MCP "
          "tools were discovered (regardless of whether the live API calls "
          "succeeded), the pipeline is wired correctly.")
    print("=" * 60)


if __name__ == "__main__":
    main()

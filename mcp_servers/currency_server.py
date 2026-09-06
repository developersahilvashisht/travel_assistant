"""
MCP Currency Server
=====================
Exposes a single MCP tool, `convert_currency`, backed by the free Frankfurter
API (European Central Bank reference rates, no API key required). Runs as a
standalone MCP server over stdio, launched by the agent process.

Run standalone for testing:
    python3 mcp_servers/currency_server.py
"""
import httpx
from fastmcp import FastMCP

mcp = FastMCP("currency-converter")


@mcp.tool()
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount from one currency to another using current exchange rates.

    Args:
        amount: The amount to convert (e.g. 50000).
        from_currency: 3-letter ISO currency code to convert from (e.g. "INR", "USD").
        to_currency: 3-letter ISO currency code to convert to (e.g. "SGD").

    Returns:
        A dict with 'status' ('ok' or 'error'), and on success 'amount',
        'from_currency', 'to_currency', 'converted_amount', 'rate', 'date',
        and 'source'. On failure, returns {'status': 'error', 'message': ...} —
        callers must NOT fabricate an exchange rate when this happens.
    """
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    url = "https://api.frankfurter.app/latest"
    params = {"amount": amount, "from": from_currency, "to": to_currency}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if to_currency not in data.get("rates", {}):
            return {
                "status": "error",
                "message": f"Currency code '{to_currency}' not recognized or not supported by the rate provider.",
            }

        converted = data["rates"][to_currency]
        rate = converted / amount if amount else None

        return {
            "status": "ok",
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "converted_amount": round(converted, 2),
            "rate": round(rate, 4) if rate else None,
            "date": data.get("date"),
            "source": "Frankfurter API (ECB reference rates, api.frankfurter.app)",
        }

    except httpx.TimeoutException:
        return {"status": "error", "message": "Currency service timed out. Do not guess the exchange rate."}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"Currency service returned an error ({e.response.status_code}) — check the currency codes. Do not guess the exchange rate."}
    except Exception as e:
        return {"status": "error", "message": f"Currency service unavailable: {str(e)}. Do not guess the exchange rate."}


if __name__ == "__main__":
    mcp.run()

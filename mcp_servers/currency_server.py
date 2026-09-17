"""
MCP Currency Server
=====================
Exposes a single MCP tool, `convert_currency`, backed by the free Frankfurter
API
"""
import httpx
from fastmcp import FastMCP

mcp = FastMCP("currency-converter")


@mcp.tool()
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount from one currency to another using current exchange rates.
    """
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    url = "https://api.frankfurter.app/latest"
    params = {"amount": amount, "from": from_currency, "to": to_currency}

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
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

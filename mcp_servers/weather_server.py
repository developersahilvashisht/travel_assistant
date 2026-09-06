"""
MCP Weather Server
====================
Exposes a single MCP tool, `get_weather_forecast`, backed by the free
Open-Meteo API (no API key required). Runs as a standalone MCP server over
stdio, launched by the agent process (see app/agent.py).

Run standalone for testing:
    python3 mcp_servers/weather_server.py
"""
import httpx
from fastmcp import FastMCP

mcp = FastMCP("singapore-weather")

# Singapore's coordinates — this assignment scopes the app to one destination,
# so we hardcode them rather than adding a geocoding step.
SINGAPORE_LAT = 1.3521
SINGAPORE_LON = 103.8198

# WMO weather interpretation codes (standard, used by Open-Meteo) -> plain English
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


@mcp.tool()
async def get_weather_forecast(days: int = 3) -> dict:
    """Get the current weather and a multi-day forecast for Singapore.

    Args:
        days: Number of forecast days to return (1-7). Default 3.

    Returns:
        A dict with 'status' ('ok' or 'error'), and on success a 'forecast'
        list of {date, min_temp_c, max_temp_c, rain_probability_pct, condition},
        plus 'source' identifying the data provider.
        On failure, returns {'status': 'error', 'message': ...} — callers must
        NOT fabricate weather data when this happens.
    """
    days = max(1, min(days, 7))
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": SINGAPORE_LAT,
        "longitude": SINGAPORE_LON,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "timezone": "Asia/Singapore",
        "forecast_days": days,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data["daily"]
        forecast = []
        for i, date in enumerate(daily["time"]):
            code = daily["weathercode"][i]
            forecast.append({
                "date": date,
                "min_temp_c": daily["temperature_2m_min"][i],
                "max_temp_c": daily["temperature_2m_max"][i],
                "rain_probability_pct": daily["precipitation_probability_max"][i],
                "condition": WEATHER_CODES.get(code, f"weather code {code}"),
            })

        return {
            "status": "ok",
            "location": "Singapore",
            "forecast": forecast,
            "source": "Open-Meteo (api.open-meteo.com)",
        }

    except httpx.TimeoutException:
        return {"status": "error", "message": "Weather service timed out. Do not guess the forecast."}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"Weather service returned an error ({e.response.status_code}). Do not guess the forecast."}
    except Exception as e:
        return {"status": "error", "message": f"Weather service unavailable: {str(e)}. Do not guess the forecast."}


if __name__ == "__main__":
    mcp.run()

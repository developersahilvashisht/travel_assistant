"""
MCP Weather Server
====================
Exposes a single MCP tool, `get_weather_forecast`, backed by the free
Open-Meteo API.

"""
import httpx
from fastmcp import FastMCP

mcp = FastMCP("singapore-weather")

SINGAPORE_LAT = 1.3521
SINGAPORE_LON = 103.8198

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
    """
    Get the current weather and a multi-day forecast for Singapore.
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
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
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

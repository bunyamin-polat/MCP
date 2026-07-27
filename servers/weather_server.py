# weather_server.py
import logging

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("weather_server")

mcp = FastMCP("Weather", host="0.0.0.0")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> human-readable description
# https://open-meteo.com/en/docs
WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


@mcp.tool()
async def get_weather(location: str) -> str:
    """Get the current weather for a given city name, using the free Open-Meteo API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            geo_response = await client.get(
                GEOCODING_URL, params={"name": location, "count": 1}
            )
            geo_response.raise_for_status()
            geo_results = geo_response.json().get("results")

            if not geo_results:
                logger.warning("No geocoding results for location=%r", location)
                return f"Could not find a location named '{location}'."

            place = geo_results[0]
            latitude, longitude = place["latitude"], place["longitude"]

            forecast_response = await client.get(
                FORECAST_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current_weather": "true",
                },
            )
            forecast_response.raise_for_status()
            current = forecast_response.json().get("current_weather")

            if not current:
                logger.error(
                    "No current_weather field in forecast response for %r", location
                )
                return f"Weather data is currently unavailable for '{location}'."

            description = WEATHER_CODES.get(
                current["weathercode"], "unknown conditions"
            )
            resolved_name = f"{place['name']}, {place.get('country', '')}".strip(", ")
            return (
                f"Current weather in {resolved_name}: {current['temperature']}°C, "
                f"{description}, wind {current['windspeed']} km/h."
            )
    except httpx.TimeoutException:
        logger.error("Timed out fetching weather for location=%r", location)
        return f"Timed out while fetching weather for '{location}'. Please try again."
    except httpx.HTTPError as exc:
        logger.error("HTTP error fetching weather for location=%r: %s", location, exc)
        return f"Failed to fetch weather for '{location}' due to a network error."


if __name__ == "__main__":
    logger.info(
        "Starting weather MCP server on streamable-http transport (port %d)",
        mcp.settings.port,
    )
    mcp.run(transport="streamable-http")

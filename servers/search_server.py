# search_server.py
import logging
import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("search_server")

mcp = FastMCP("Search", host="0.0.0.0", port=8001)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


@mcp.tool()
async def web_search(query: str) -> str:
    """Search the web for up-to-date information using Tavily and return a short summary with sources."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY is not set")
        return "Web search is unavailable: TAVILY_API_KEY is not configured."

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": 5,
                    "include_answer": True,
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        logger.error("Timed out searching for query=%r", query)
        return f"Timed out while searching for '{query}'. Please try again."
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Tavily returned HTTP %s for query=%r", exc.response.status_code, query
        )
        return f"Web search failed for '{query}' (HTTP {exc.response.status_code})."
    except httpx.HTTPError as exc:
        logger.error("HTTP error searching for query=%r: %s", query, exc)
        return f"Web search failed for '{query}' due to a network error."

    answer = data.get("answer")
    results = data.get("results", [])

    if not answer and not results:
        return f"No web search results found for '{query}'."

    lines = []
    if answer:
        lines.append(f"Answer: {answer}")
    if results:
        lines.append("Sources:")
        for result in results:
            lines.append(f"- {result.get('title')}: {result.get('url')}")
    return "\n".join(lines)


if __name__ == "__main__":
    logger.info(
        "Starting search MCP server on streamable-http transport (port %d)",
        mcp.settings.port,
    )
    mcp.run(transport="streamable-http")

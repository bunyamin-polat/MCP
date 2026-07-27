import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv()

MATH_SERVER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "servers", "math_server.py"
)

# Defaults target localhost for local runs; docker-compose overrides these to service names (e.g. http://weather:8000/mcp).
WEATHER_SERVER_URL = os.environ.get("WEATHER_SERVER_URL", "http://localhost:8000/mcp")
SEARCH_SERVER_URL = os.environ.get("SEARCH_SERVER_URL", "http://localhost:8001/mcp")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            "args": [MATH_SERVER_PATH],
            "transport": "stdio",
        },
        "weather": {
            # Start this server first: uv run python servers/weather_server.py
            "url": WEATHER_SERVER_URL,
            "transport": "streamable_http",
        },
        "search": {
            # Start this server first: uv run python servers/search_server.py
            "url": SEARCH_SERVER_URL,
            "transport": "streamable_http",
        },
    }
)


async def main():
    tools = await client.get_tools()
    agent = create_agent(llm, tools)

    math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
    print(math_response["messages"][-1].content)

    weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
    print(weather_response["messages"][-1].content)

    search_response = await agent.ainvoke(
        {"messages": "search the web for the latest LangChain release"}
    )
    print(search_response["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())

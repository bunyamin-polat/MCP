import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("cli")

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
            # Start first: uv run python servers/weather_server.py
            "url": WEATHER_SERVER_URL,
            "transport": "streamable_http",
        },
        "search": {
            # Start first: uv run python servers/search_server.py
            "url": SEARCH_SERVER_URL,
            "transport": "streamable_http",
        },
    }
)


async def main():
    try:
        tools = await client.get_tools()
    except Exception:
        logger.exception(
            "Could not fetch tools from one or more MCP servers. "
            "Make sure servers/weather_server.py and servers/search_server.py are running."
        )
        return

    logger.info("Loaded %d tools: %s", len(tools), [tool.name for tool in tools])

    agent = create_agent(llm, tools, checkpointer=InMemorySaver())
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("MCP chat agent ready. Type 'exit' or 'quit' to stop, Ctrl+C also works.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Bye!")
            break

        try:
            result = await agent.ainvoke({"messages": user_input}, config=config)
            print(f"Agent: {result['messages'][-1].content}")
        except Exception:
            logger.exception("Agent failed to handle the request")
            print("Agent: Sorry, something went wrong handling that request.")


if __name__ == "__main__":
    asyncio.run(main())

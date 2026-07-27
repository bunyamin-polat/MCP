import os

import pytest
from langchain_mcp_adapters.client import MultiServerMCPClient

MATH_SERVER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "servers",
    "math_server.py",
)


@pytest.fixture
def math_client():
    return MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                "args": [MATH_SERVER_PATH],
                "transport": "stdio",
            }
        }
    )


async def test_math_server_tools_discovered_over_stdio(math_client):
    tools = await math_client.get_tools()
    tool_names = {tool.name for tool in tools}

    assert tool_names == {"add", "multiply"}


async def test_math_server_add_tool_call_over_stdio(math_client):
    tools = await math_client.get_tools()
    add_tool = next(tool for tool in tools if tool.name == "add")

    result = await add_tool.ainvoke({"a": 3, "b": 5})

    assert result[0]["text"] == "8"

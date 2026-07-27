from dotenv import load_dotenv
import asyncio
load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent


llm = ChatOpenAI()

stdio_server_params = StdioServerParameters(
    command="python",
    args=["/Users/bunyamin/Desktop/AI_Course/MCP/servers/math_server.py"]
)

async def main():
    print("Hello from MCP!")


if __name__ == "__main__":
    main()

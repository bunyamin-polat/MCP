# MCP + LangChain Example

A hands-on learning project that shows how to build tool servers with the **Model Context Protocol (MCP)** and use them from a **LangChain/LangGraph** agent. If you've never touched MCP before, read the "What is MCP?" section first — everything else in this README builds on it.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open, model-agnostic standard for connecting AI applications to external tools and data. Instead of every AI framework inventing its own way to expose "tools" (functions an LLM can call), MCP defines one protocol that any client and any server can speak.

Two roles:

- **MCP server** — a small program that exposes one or more *tools* (plain functions with a name, description, and typed arguments). In this repo, `servers/math_server.py`, `servers/weather_server.py`, and `servers/search_server.py` are MCP servers.
- **MCP client** — the part that connects to one or more servers, discovers their tools, and calls them. Here, `langchain-mcp-adapters` acts as the client and turns each MCP tool into a LangChain `Tool` object, so a LangChain agent can use it like any other tool.

**Transports** (how client and server talk to each other):

- `stdio` — the client starts the server as a subprocess and talks to it over stdin/stdout. No network involved; simplest option for local tools. Used by `math_server.py`.
- `streamable-http` — the server runs as its own long-lived HTTP process (e.g. `uvicorn` on a port), and the client connects over HTTP. Needed when the tool server should run independently of the client (a separate machine, a container, shared by multiple clients). Used by `weather_server.py` and `search_server.py`.
- `sse` — an older HTTP-based transport, now superseded by `streamable-http`. Not used in this repo.

Why bother with MCP instead of just writing local Python functions and passing them to LangChain directly? Because MCP servers are **decoupled and reusable** — the same `weather_server.py` process could be used by a completely different client (Claude Desktop, a different agent framework, another team's app) without any code changes, since they all speak the same protocol.

## What This Project Demonstrates

| File | What it shows |
|---|---|
| [main.py](main.py) | The lowest-level way to talk to one MCP server: manually opening a `stdio_client`, an MCP `ClientSession`, and loading tools with `load_mcp_tools`. Good for understanding what `langchain-mcp-adapters` does under the hood. |
| [multi_server_client.py](multi_server_client.py) | The higher-level, recommended way: `MultiServerMCPClient` connects to **several** servers at once (stdio *and* streamable-http) and hands all their tools to one agent. Runs a few one-off questions and exits. |
| [cli.py](cli.py) | A real interactive chat loop, built on the same idea as `multi_server_client.py`, with **multi-turn memory** (the agent remembers earlier turns in the same session) via a LangGraph checkpointer. |
| [servers/math_server.py](servers/math_server.py) | Simplest possible MCP server: `add` and `multiply` tools, stdio transport. |
| [servers/weather_server.py](servers/weather_server.py) | MCP server calling the real, free [Open-Meteo](https://open-meteo.com/) API (no key required) for current weather, streamable-http transport. |
| [servers/search_server.py](servers/search_server.py) | MCP server calling the [Tavily](https://tavily.com/) web search API (requires `TAVILY_API_KEY`), streamable-http transport. |
| [tests/](tests/) | `pytest` tests: pure unit tests for the math tools, mocked-HTTP tests for the weather/search tools, and a real end-to-end test that spins up `math_server.py` over stdio via `MultiServerMCPClient`. |
| [Dockerfile](Dockerfile) / [docker-compose.yml](docker-compose.yml) | Containerizes the servers and the CLI app so the whole stack can be started with one command. |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | GitHub Actions workflow that lints with `ruff` and runs the test suite on every push/PR to `main`. |

## Project Structure

```text
MCP/
├── main.py                       # Low-level single-server (math) example
├── multi_server_client.py        # MultiServerMCPClient with math + weather + search, one-shot
├── cli.py                        # Interactive chat REPL with multi-turn memory
├── servers/
│   ├── math_server.py            # add/multiply tools, stdio transport
│   ├── weather_server.py         # Real weather via Open-Meteo, streamable-http
│   └── search_server.py          # Web search via Tavily, streamable-http
├── tests/
│   ├── test_math_server.py
│   ├── test_weather_server.py
│   ├── test_search_server.py
│   └── test_mcp_integration.py
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml
├── pyproject.toml                # Dependencies, managed with uv
├── .env                          # Your local secrets (gitignored, not committed)
└── uv.lock
```

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- An OpenAI API key (for the agent's LLM)
- Optionally, a [Tavily](https://tavily.com/) API key (only needed for the web search tool)

## Setup

```bash
uv sync
```

Create a `.env` file in the project root with your own keys:

```bash
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
LANGSMITH_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=MCP
```

| Variable | Required? | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Needed to run the `ChatOpenAI` model |
| `TAVILY_API_KEY` | Only for `search_server.py` | Powers the `web_search` tool; without it, that tool returns a clear error message instead of crashing |
| `LANGSMITH_API_KEY` | No | Only if you want tracing via LangSmith |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | No | LangSmith project name traces will appear under |

`.env` is listed in `.gitignore`, so it is never committed — your keys stay local.

## Running

### 1) Single-server example (`main.py`)

Starts and connects to `math_server.py` over stdio, demonstrating the MCP SDK's low-level `ClientSession` API. No other servers need to be running.

```bash
uv run python main.py
```

### 2) Multi-server, one-shot example (`multi_server_client.py`)

Uses `MultiServerMCPClient` to talk to `math` (stdio), `weather` (streamable-http), and `search` (streamable-http) at once, then asks a few questions and exits. Start the HTTP servers first, each in their own terminal:

```bash
# Terminal 1
uv run python servers/weather_server.py

# Terminal 2
uv run python servers/search_server.py

# Terminal 3
uv run python multi_server_client.py
```

### 3) Interactive chat with memory (`cli.py`)

Same servers as above, but instead of a couple of hardcoded questions you get a REPL, and the agent remembers previous turns in the conversation (try telling it something, then asking it to recall it later):

```bash
# Terminal 1
uv run python servers/weather_server.py

# Terminal 2
uv run python servers/search_server.py

# Terminal 3
uv run python cli.py
```

Type `exit` or `quit` (or Ctrl+C) to stop.

### 4) Everything at once with Docker Compose

No need to juggle multiple terminals — this builds one image and runs the weather server, search server, and the interactive CLI together, wired to talk to each other over the Docker network:

```bash
docker compose up -d weather search   # start the two HTTP tool servers in the background
docker compose run --rm app           # attach an interactive session for the CLI
```

The `weather` and `search` services bind to `0.0.0.0` inside their containers (instead of the local-only default) so the `app` container can reach them at `http://weather:8000/mcp` and `http://search:8001/mcp` over the Docker network; `cli.py`/`multi_server_client.py` pick these up via the `WEATHER_SERVER_URL`/`SEARCH_SERVER_URL` environment variables set in `docker-compose.yml`.

## How It Works

1. Each server in `servers/` uses `FastMCP` to expose its tools (`add`, `multiply`, `get_weather`, `web_search`) over the MCP protocol — one over stdio, two over streamable-http.
2. On the client side, `langchain_mcp_adapters` converts these MCP tools into LangChain `Tool` objects (`load_mcp_tools` for a single session, or `MultiServerMCPClient.get_tools()` for several servers at once).
3. `langchain.agents.create_agent` combines those tools with an OpenAI model (`gpt-4o-mini`) to build a LangGraph-based agent (a small state graph that loops between "call the model" and "run any tools it asked for" until it has a final answer).
4. In `cli.py`, the agent is also given a LangGraph `InMemorySaver` checkpointer and a fixed `thread_id`, so each new `ainvoke` call in the same process appends to the same conversation history instead of starting fresh.
5. The agent takes the user's message, decides whether it needs a tool, calls it via the MCP client if so, and returns the result in natural language.

## Testing

```bash
uv run pytest -v
```

The suite covers:

- **Unit tests** for `add`/`multiply` (pure functions, no mocking needed).
- **Mocked-HTTP tests** for `get_weather` and `web_search`, so they run offline and don't depend on Open-Meteo/Tavily being reachable or an API key being set.
- **A real integration test** that starts `math_server.py` as an actual subprocess over stdio via `MultiServerMCPClient`, discovers its tools, and calls `add` end-to-end through the MCP protocol.

None of the tests call OpenAI, so they run without an `OPENAI_API_KEY`.

## Linting

```bash
uv run ruff check .
```

## CI

`.github/workflows/ci.yml` runs `ruff check` and `pytest` on every push and pull request to `main`. No secrets are required since the tests don't hit OpenAI/Tavily/Open-Meteo directly.

## Troubleshooting

- **`uv add` fails with a dependency resolution error mentioning your own project name** — this happens if your `pyproject.toml` project is named the same as one of its dependencies (e.g. naming your project `mcp`, which collides with the real `mcp` package `langchain-mcp-adapters` depends on). Rename your project in `pyproject.toml`.
- **weather/search tool calls fail even though the server "looks" running** — check `lsof -i :8000` / `lsof -i :8001` for a *stale* process left over from an earlier run still holding the port. Kill it (`pkill -f servers/weather_server.py`) and restart cleanly; a leftover process serving old code is a common source of confusing failures.
- **`await` SyntaxError / "await allowed only within async function"** — all `await` calls must live inside an `async def` function, which must itself be started with `asyncio.run(...)`, not called at module top-level.
- **`httpx.HTTPStatusError: 421 Misdirected Request` when a client connects to a streamable-http MCP server under a different hostname than `localhost`/`127.0.0.1`** — the MCP SDK auto-enables DNS-rebinding protection (which only allows `Host` headers of `localhost`/`127.0.0.1`) whenever `FastMCP(...)` is constructed with the default host. Since Docker containers reach each other by service name (e.g. `weather`, not `localhost`), that protection must be turned off by explicitly passing `host="0.0.0.0"` to the `FastMCP(...)` constructor itself — setting `mcp.settings.host` afterwards is too late, since the decision is made at construction time. See `servers/weather_server.py` and `servers/search_server.py`.

## Ideas for Further Improvement

Logging/error handling, a real weather API, a web search tool, conversation memory, an interactive CLI, tests, Docker, and CI have all been implemented already. Remaining ideas if you want to keep extending this project:

- **More MCP servers**: filesystem access, database querying, or code execution tools.
- **A real UI**: a Streamlit or FastAPI + web frontend instead of a terminal REPL.
- **Persistent memory**: swap `InMemorySaver` for a database-backed LangGraph checkpointer (e.g. Postgres) so conversations survive a restart.
- **Streaming responses**: use `agent.astream(...)` instead of `ainvoke` to show tokens/tool calls as they happen.
- **Auth/rate limiting**: if the streamable-http servers were ever exposed beyond localhost/Docker, they'd need authentication and rate limiting.
- **Structured tool output**: return typed/structured data from tools instead of formatted strings, so the agent (and any UI) can work with it more reliably.


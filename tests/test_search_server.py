import httpx

from servers import search_server


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class FakeAsyncClient:
    def __init__(self, response, **kwargs):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, json=None):
        return self._response


async def test_web_search_missing_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    result = await search_server.web_search("test query")

    assert "TAVILY_API_KEY" in result


async def test_web_search_success(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "fake-key")
    response = FakeResponse(
        {
            "answer": "It's sunny.",
            "results": [{"title": "Weather Site", "url": "https://example.com"}],
        }
    )
    monkeypatch.setattr(
        search_server.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(response, **kwargs),
    )

    result = await search_server.web_search("weather today")

    assert "It's sunny." in result
    assert "https://example.com" in result


async def test_web_search_no_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "fake-key")
    response = FakeResponse({"answer": None, "results": []})
    monkeypatch.setattr(
        search_server.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(response, **kwargs),
    )

    result = await search_server.web_search("something obscure")

    assert "No web search results" in result

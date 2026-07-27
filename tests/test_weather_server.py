import httpx
import pytest

from servers import weather_server


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
    """Stands in for httpx.AsyncClient, returning canned responses per URL."""

    def __init__(self, responses, **kwargs):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, params=None):
        return self._responses[url]


@pytest.fixture
def patch_client(monkeypatch):
    def _patch(responses):
        monkeypatch.setattr(
            weather_server.httpx,
            "AsyncClient",
            lambda **kwargs: FakeAsyncClient(responses, **kwargs),
        )

    return _patch


async def test_get_weather_success(patch_client):
    patch_client(
        {
            weather_server.GEOCODING_URL: FakeResponse(
                {
                    "results": [
                        {
                            "latitude": 41.0,
                            "longitude": 29.0,
                            "name": "Istanbul",
                            "country": "Turkiye",
                        }
                    ]
                }
            ),
            weather_server.FORECAST_URL: FakeResponse(
                {
                    "current_weather": {
                        "temperature": 20.0,
                        "windspeed": 5.0,
                        "weathercode": 1,
                    }
                }
            ),
        }
    )

    result = await weather_server.get_weather("Istanbul")

    assert "Istanbul" in result
    assert "20.0" in result
    assert "mainly clear" in result


async def test_get_weather_unknown_location(patch_client):
    patch_client({weather_server.GEOCODING_URL: FakeResponse({"results": []})})

    result = await weather_server.get_weather("Nowhereville")

    assert "Could not find a location" in result

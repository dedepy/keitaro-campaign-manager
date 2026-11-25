
import asyncio

import httpx
import pytest

from app.integrations.keitaro import KeitaroClient, KeitaroError


API_URL = "https://example.com/admin_api/v1"


def test_get_campaigns_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/admin_api/v1/campaigns"
        assert request.headers["Api-Key"] == "test-key"

        return httpx.Response(
            200,
            json=[
                {"id": 1, "name": "test_campaign"},
            ],
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            campaigns = await client.get_campaigns()

        assert len(campaigns) == 1
        assert campaigns[0]["name"] == "test_campaign"

    asyncio.run(run())


def test_get_campaigns_unauthorized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized"})

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(KeitaroError) as exc_info:
                await client.get_campaigns()

            assert exc_info.value.status_code == 401

    asyncio.run(run())


def test_get_campaigns_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="Not a JSON response",
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(
                KeitaroError,
                match="invalid JSON",
            ):
                await client.get_campaigns()

    asyncio.run(run())


def test_get_campaigns_invalid_structure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"campaigns": []},
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(
                KeitaroError,
                match="Unexpected campaigns",
            ):
                await client.get_campaigns()

    asyncio.run(run())

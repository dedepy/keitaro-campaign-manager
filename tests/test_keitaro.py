
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

@pytest.mark.parametrize(
    ("endpoint", "method_name"),
    [
        ("domains", "get_domains"),
        ("offers", "get_offers"),
        ("traffic_sources", "get_traffic_sources"),
    ],
)
def test_get_resources(
    endpoint: str,
    method_name: str,
) -> None:

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == (
            f"/admin_api/v1/{endpoint}"
        )

        return httpx.Response(
            200,
            json=[{"id": 1, "name": "Test resource"}],
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            method = getattr(client, method_name)
            result = await method()

        assert result == [
            {"id": 1, "name": "Test resource"}
        ]

    asyncio.run(run())


def test_create_campaign() -> None:
    payload = {
        "name": "test_medvedev_campaign1",
        "alias": "test_medvedev_campaign1",
        "type": "position",
        "state": "disabled",
        "group_id": "10332",
        "traffic_source_id": 836,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/admin_api/v1/campaigns"

        import json
        body = json.loads(request.content)

        assert body == payload
        assert request.headers["Api-Key"] == "test-key"

        return httpx.Response(
            200,
            json={"id": 12345, **payload},
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            campaign = await client.create_campaign(payload)

        assert campaign["id"] == 12345
        assert campaign["state"] == "disabled"

    asyncio.run(run())


def test_get_campaign_streams() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == (
            "/admin_api/v1/campaigns/269/streams"
        )

        return httpx.Response(
            200,
            json=[
                {
                    "id": 501,
                    "campaign_id": 269,
                    "name": "Google GEO",
                    "type": "regular",
                    "schema": "redirect",
                }
            ],
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            streams = await client.get_campaign_streams(269)

        assert len(streams) == 1
        assert streams[0]["campaign_id"] == 269
        assert streams[0]["type"] == "regular"

    asyncio.run(run())


def test_create_stream() -> None:
    payload = {
        "campaign_id": 269,
        "name": "test_medvedev_google_DE",
        "type": "regular",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://www.google.com/",
        "filters": [
            {
                "name": "country",
                "mode": "accept",
                "payload": ["DE"],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        assert request.method == "POST"
        assert request.url.path == "/admin_api/v1/streams"
        assert request.headers["Api-Key"] == "test-key"

        body = json.loads(request.content)

        assert body == payload
        assert body["campaign_id"] == 269
        assert body["filters"][0]["payload"] == ["DE"]

        return httpx.Response(
            200,
            json={"id": 501, **payload},
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            stream = await client.create_stream(payload)

        assert stream["id"] == 501
        assert stream["type"] == "regular"

    asyncio.run(run())

def test_create_default_offer_stream() -> None:
    import json

    from scripts.preview_streams import build_offer_stream

    payload = build_offer_stream()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/admin_api/v1/streams"

        body = json.loads(request.content)

        assert body["campaign_id"] == 269
        assert body["type"] == "default"
        assert body["schema"] == "landings"

        assert body["offers"] == [
            {
                "offer_id": 18004,
                "share": 100,
                "state": "active",
            }
        ]

        return httpx.Response(
            200,
            json={"id": 532, **body},
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            stream = await client.create_stream(payload)

        assert stream["id"] == 532
        assert stream["type"] == "default"
        assert stream["offers"][0]["share"] == 100

    asyncio.run(run())

def test_update_stream_offers() -> None:
    import json

    offers = [
        {
            "offer_id": 18004,
            "share": 50,
            "state": "active",
        },
        {
            "offer_id": 18005,
            "share": 50,
            "state": "active",
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/admin_api/v1/streams/535"
        assert json.loads(request.content) == {
            "offers": offers
        }

        return httpx.Response(
            200,
            json={"id": 535, "offers": offers},
        )

    async def run() -> None:
        async with KeitaroClient(
            API_URL,
            "test-key",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client.update_stream_offers(
                535,
                offers,
            )

        assert result["id"] == 535
        assert len(result["offers"]) == 2

    asyncio.run(run())

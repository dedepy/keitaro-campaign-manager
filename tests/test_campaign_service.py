
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.keitaro import KeitaroError
from app.schemas.campaign import CampaignCreateRequest
from app.services.campaigns import (
    CampaignService,
    CampaignSetupError,
)


def make_request() -> CampaignCreateRequest:
    return CampaignCreateRequest(
        name="test_medvedev_campaign2",
        geo="DE",
        domain_id=1813,
        group_id=10332,
        traffic_source_id=836,
        offer_id=18004,
    )


def make_client() -> SimpleNamespace:
    client = SimpleNamespace()

    client.get_domains = AsyncMock(
        return_value=[{"id": 1813, "name": "kt-emulator.test"}]
    )
    client.get_campaign_groups = AsyncMock(
        return_value=[{"id": 10332, "name": "FORTESTS"}]
    )
    client.get_traffic_sources = AsyncMock(
        return_value=[{"id": 836, "name": "FORTESTS"}]
    )
    client.get_offers = AsyncMock(
        return_value=[{"id": 18004, "name": "Test offer"}]
    )
    client.get_campaigns = AsyncMock(return_value=[])

    client.create_campaign = AsyncMock(
        return_value={"id": 300}
    )
    client.create_stream = AsyncMock(
        side_effect=[{"id": 601}, {"id": 602}]
    )

    client.get_campaign_streams = AsyncMock(
        return_value=[
            {
                "id": 601,
                "type": "regular",
                "schema": "redirect",
                "state": "active",
                "position": 1,
                "action_type": "http",
                "action_payload": "https://www.google.com/",
                "filters": [
                    {
                        "name": "country",
                        "mode": "accept",
                        "payload": ["DE"],
                    }
                ],
            },
            {
                "id": 602,
                "type": "default",
                "schema": "landings",
                "state": "active",
                "position": 2,
                "offers": [
                    {
                        "offer_id": 18004,
                        "share": 100,
                        "state": "active",
                    }
                ],
            },
        ]
    )

    return client


def test_create_campaign_success() -> None:
    client = make_client()
    service = CampaignService(client)

    result = asyncio.run(service.create(make_request()))

    assert result["campaign_id"] == 300
    assert result["google_stream_id"] == 601
    assert result["offer_stream_id"] == 602
    assert result["state"] == "disabled"

    client.create_campaign.assert_awaited_once()
    assert client.create_stream.await_count == 2

    first_payload = client.create_stream.await_args_list[0].args[0]
    second_payload = client.create_stream.await_args_list[1].args[0]

    assert first_payload["campaign_id"] == 300
    assert first_payload["filters"][0]["payload"] == ["DE"]
    assert second_payload["offers"][0]["offer_id"] == 18004


def test_reject_unknown_offer() -> None:
    client = make_client()
    client.get_offers.return_value = []

    service = CampaignService(client)

    with pytest.raises(ValueError, match="Offer"):
        asyncio.run(service.create(make_request()))

    client.create_campaign.assert_not_awaited()


def test_partial_creation_failure() -> None:
    client = make_client()

    client.create_stream.side_effect = [
        {"id": 601},
        KeitaroError("Keitaro returned HTTP 500", 500),
    ]

    service = CampaignService(client)

    with pytest.raises(CampaignSetupError) as exc_info:
        asyncio.run(service.create(make_request()))

    assert exc_info.value.campaign_id == 300
    assert client.create_stream.await_count == 2

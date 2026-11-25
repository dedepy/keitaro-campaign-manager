
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.offer_editor import OfferEditorService


def make_stream(offers: list[dict]) -> dict:
    return {
        "id": 535,
        "campaign_id": 278,
        "name": "Default Offer",
        "type": "default",
        "schema": "landings",
        "state": "active",
        "position": 2,
        "action_type": "http",
        "action_payload": None,
        "filters": [],
        "offers": offers,
    }


def make_offer(offer_id: int, share: int) -> dict:
    return {
        "offer_id": offer_id,
        "share": share,
        "state": "active",
    }


def make_client(before: dict, after: dict | None = None):
    client = SimpleNamespace()

    responses = [[before]]
    if after is not None:
        responses.append([after])

    client.get_campaign_streams = AsyncMock(
        side_effect=responses
    )
    client.get_offers = AsyncMock(
        return_value=[
            {"id": 18004},
            {"id": 18005},
        ]
    )
    client.update_stream_offers = AsyncMock(
        return_value={"id": 535}
    )

    return client


def test_add_offer() -> None:
    before = make_stream([make_offer(18005, 100)])
    after = make_stream([
        make_offer(18005, 50),
        make_offer(18004, 50),
    ])

    client = make_client(before, after)
    service = OfferEditorService(client)

    result = asyncio.run(
        service.add_offer(278, 535, 18004)
    )

    assert result["changed"] is True
    assert sum(o["share"] for o in result["offers"]) == 100

    client.update_stream_offers.assert_awaited_once_with(
        535,
        [
            make_offer(18005, 50),
            make_offer(18004, 50),
        ],
    )


def test_remove_offer() -> None:
    before = make_stream([
        make_offer(18004, 50),
        make_offer(18005, 50),
    ])
    after = make_stream([make_offer(18005, 100)])

    client = make_client(before, after)
    service = OfferEditorService(client)

    result = asyncio.run(
        service.remove_offer(278, 535, 18004)
    )

    assert result["changed"] is True
    assert result["offers"] == [make_offer(18005, 100)]


def test_remove_missing_offer_is_noop() -> None:
    current = make_stream([make_offer(18005, 100)])

    client = make_client(current)
    service = OfferEditorService(client)

    result = asyncio.run(
        service.remove_offer(278, 535, 18004)
    )

    assert result["changed"] is False
    client.update_stream_offers.assert_not_awaited()


def test_add_existing_offer_is_noop() -> None:
    current = make_stream([make_offer(18005, 100)])

    client = make_client(current)
    service = OfferEditorService(client)

    result = asyncio.run(
        service.add_offer(278, 535, 18005)
    )

    assert result["changed"] is False
    client.update_stream_offers.assert_not_awaited()


def test_cannot_remove_last_offer() -> None:
    current = make_stream([make_offer(18005, 100)])

    client = make_client(current)
    service = OfferEditorService(client)

    with pytest.raises(ValueError, match="last offer"):
        asyncio.run(
            service.remove_offer(278, 535, 18005)
        )

    client.update_stream_offers.assert_not_awaited()


def test_detects_incorrect_saved_shares() -> None:
    before = make_stream([make_offer(18005, 100)])
    incorrect = make_stream([
        make_offer(18005, 70),
        make_offer(18004, 30),
    ])

    client = make_client(before, incorrect)
    service = OfferEditorService(client)

    with pytest.raises(
        ValueError,
        match="Post-update verification failed",
    ):
        asyncio.run(
            service.add_offer(278, 535, 18004)
        )

from app.integrations.keitaro import KeitaroClient
from typing import Any


class StreamNotFoundError(ValueError):
    """Requested stream does not exist."""


class OfferNotFoundError(ValueError):
    """Requested offer does not exist."""


class OfferUpdateVerificationError(ValueError):
    """Saved stream state differs from expected."""

def distribute_offer_shares(
    offer_ids: list[int],
) -> list[dict[str, Any]]:
    if not offer_ids:
        raise ValueError(
            "At least one offer is required"
        )

    if len(offer_ids) > 100:
        raise ValueError(
            "Cannot assign at least 1% to more than 100 offers"
        )

    if any(
        type(offer_id) is not int or offer_id <= 0
        for offer_id in offer_ids
    ):
        raise ValueError(
            "Offer IDs must be positive integers"
        )

    if len(set(offer_ids)) != len(offer_ids):
        raise ValueError(
            "Duplicate offer IDs are not allowed"
        )

    base_share, remainder = divmod(
        100,
        len(offer_ids),
    )

    return [
        {
            "offer_id": offer_id,
            "share": base_share + (index < remainder),
            "state": "active",
        }
        for index, offer_id in enumerate(offer_ids)
    ]

def remove_offer_from_distribution(
    current_offers: list[dict[str, Any]],
    offer_id: int,
) -> list[dict[str, Any]]:
    if not current_offers:
        raise ValueError("Stream has no offers")

    if any(
        offer.get("state") != "active"
        for offer in current_offers
    ):
        raise ValueError(
            "Cannot redistribute inactive offers"
        )

    current_ids = [
        offer["offer_id"]
        for offer in current_offers
    ]

    if len(set(current_ids)) != len(current_ids):
        raise ValueError("Duplicate offers in stream")

    if offer_id not in current_ids:
        raise ValueError("Offer is not attached to stream")

    remaining_ids = [
        current_id
        for current_id in current_ids
        if current_id != offer_id
    ]

    if not remaining_ids:
        raise ValueError(
            "Cannot remove the last offer"
        )

    return distribute_offer_shares(remaining_ids)

class OfferEditorService:
    PROTECTED_FIELDS = (
        "campaign_id",
        "name",
        "type",
        "schema",
        "state",
        "position",
        "action_type",
        "action_payload",
        "filters",
    )

    def __init__(self, client: KeitaroClient) -> None:
        self.client = client

    async def _load_stream(
        self,
        campaign_id: int,
        stream_id: int,
    ) -> tuple[dict[str, Any], list[int]]:
        if campaign_id <= 0 or stream_id <= 0:
            raise ValueError("IDs must be positive")

        streams = await self.client.get_campaign_streams(
            campaign_id
        )

        stream = next(
            (s for s in streams if s.get("id") == stream_id),
            None,
        )

        if stream is None:
            raise ValueError("Stream not found")

        if (
            stream.get("campaign_id") != campaign_id
            or stream.get("type") != "default"
            or stream.get("schema") != "landings"
            or stream.get("state") != "active"
        ):
            raise ValueError("Stream cannot be edited")

        offers = stream.get("offers")

        if not isinstance(offers, list) or not offers:
            raise ValueError("Stream has no offers")

        if any(
            offer.get("state") != "active"
            for offer in offers
        ):
            raise ValueError("Inactive offers are not supported")

        ids = [offer.get("offer_id") for offer in offers]

        # Validate IDs and reject duplicates.
        distribute_offer_shares(ids)

        if any(
            type(offer.get("share")) is not int
            or offer["share"] <= 0
            for offer in offers
        ):
            raise ValueError("Invalid offer shares")

        if sum(offer["share"] for offer in offers) != 100:
            raise ValueError("Offer shares must total 100")

        return stream, ids

    @staticmethod
    def _result(
        stream: dict[str, Any],
        changed: bool,
    ) -> dict[str, Any]:
        return {
            "campaign_id": stream["campaign_id"],
            "stream_id": stream["id"],
            "changed": changed,
            "offers": [
                {
                    "offer_id": offer["offer_id"],
                    "share": offer["share"],
                    "state": offer["state"],
                }
                for offer in stream["offers"]
            ],
        }

    async def _save(
        self,
        campaign_id: int,
        stream_id: int,
        original: dict[str, Any],
        new_offers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        await self.client.update_stream_offers(
            stream_id,
            new_offers,
        )

        streams = await self.client.get_campaign_streams(
            campaign_id
        )

        updated = next(
            (s for s in streams if s.get("id") == stream_id),
            None,
        )

        if updated is None:
            raise ValueError(
                "Stream missing after update; inspect Keitaro"
            )

        for field in self.PROTECTED_FIELDS:
            if original.get(field) != updated.get(field):
                raise ValueError(
                    f"Unexpected change in {field}"
                )

        actual = updated.get("offers", [])

        expected_values = sorted(
            (
                o["offer_id"],
                o["share"],
                o["state"],
            )
            for o in new_offers
        )

        try:
            actual_values = sorted(
                (
                    o["offer_id"],
                    o["share"],
                    o["state"],
                )
                for o in actual
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "Invalid saved offers; inspect Keitaro"
            ) from exc

        if actual_values != expected_values:
            raise ValueError(
                "Post-update verification failed; "
                "inspect Keitaro before retrying"
            )

        return self._result(updated, changed=True)

    async def add_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
    ) -> dict[str, Any]:
        if type(offer_id) is not int or offer_id <= 0:
            raise ValueError("Invalid offer ID")

        stream, current_ids = await self._load_stream(
            campaign_id,
            stream_id,
        )

        if offer_id in current_ids:
            return self._result(stream, changed=False)

        available = await self.client.get_offers()

        if not any(
            offer.get("id") == offer_id
            for offer in available
        ):
            raise ValueError("Offer does not exist")

        new_offers = distribute_offer_shares(
            current_ids + [offer_id]
        )

        return await self._save(
            campaign_id,
            stream_id,
            stream,
            new_offers,
        )

    async def remove_offer(
        self,
        campaign_id: int,
        stream_id: int,
        offer_id: int,
    ) -> dict[str, Any]:
        if type(offer_id) is not int or offer_id <= 0:
            raise ValueError("Invalid offer ID")

        stream, current_ids = await self._load_stream(
            campaign_id,
            stream_id,
        )

        if offer_id not in current_ids:
            return self._result(stream, changed=False)

        new_offers = remove_offer_from_distribution(
            stream["offers"],
            offer_id,
        )

        return await self._save(
            campaign_id,
            stream_id,
            stream,
            new_offers,
        )

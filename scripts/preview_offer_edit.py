
import asyncio
import json

from app.core.config import settings
from app.integrations.keitaro import KeitaroClient
from app.services.offer_editor import (
    distribute_offer_shares,
)


CAMPAIGN_ID = 278
STREAM_ID = 535
NEW_OFFER_ID = 18005


async def main() -> None:
    async with KeitaroClient(
        api_url=settings.keitaro_api_url,
        api_key=settings.keitaro_api_key.get_secret_value(),
    ) as client:
        streams = await client.get_campaign_streams(
            CAMPAIGN_ID
        )

        stream = next(
            (
                item for item in streams
                if item.get("id") == STREAM_ID
            ),
            None,
        )

        if stream is None:
            raise ValueError("Stream not found")

        if (
            stream.get("type") != "default"
            or stream.get("schema") != "landings"
        ):
            raise ValueError(
                "Only default offer streams can be edited"
            )

        current_offers = stream.get("offers", [])

        if any(
            item.get("state") != "active"
            for item in current_offers
        ):
            raise ValueError(
                "Disabled offers require separate handling"
            )

        current_ids = [
            item["offer_id"] for item in current_offers
        ]

        available_offers = await client.get_offers()

        if not any(
            offer.get("id") == NEW_OFFER_ID
            for offer in available_offers
        ):
            raise ValueError("New offer not found")

        if NEW_OFFER_ID in current_ids:
            raise ValueError("Offer is already attached")

        updated_ids = current_ids + [NEW_OFFER_ID]

        new_offers = distribute_offer_shares(
            updated_ids
        )

        print("Current offer IDs:", current_ids)
        print("\nProposed PUT payload:")
        print(json.dumps(
            {"offers": new_offers},
            indent=2,
        ))

        print("\nDRY RUN: no changes made.")


if __name__ == "__main__":
    asyncio.run(main())

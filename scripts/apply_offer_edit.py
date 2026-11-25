
import argparse
import asyncio
import json
from typing import Any

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)
from app.services.offer_editor import distribute_offer_shares


CAMPAIGN_ID = 278
STREAM_ID = 535
GOOGLE_STREAM_ID = 534
NEW_OFFER_ID = 18005

PROTECTED_FIELDS = (
    "id",
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


def find_stream(
    streams: list[dict[str, Any]],
    stream_id: int,
) -> dict[str, Any]:
    stream = next(
        (item for item in streams if item.get("id") == stream_id),
        None,
    )

    if stream is None:
        raise ValueError(f"Stream {stream_id} not found")

    return stream


def protected_settings(
    stream: dict[str, Any],
) -> dict[str, Any]:
    return {
        field: stream.get(field)
        for field in PROTECTED_FIELDS
    }


async def main(apply: bool) -> None:
    async with KeitaroClient(
        api_url=settings.keitaro_api_url,
        api_key=settings.keitaro_api_key.get_secret_value(),
    ) as client:

        streams_before = await client.get_campaign_streams(
            CAMPAIGN_ID
        )

        target = find_stream(streams_before, STREAM_ID)
        google = find_stream(
            streams_before, GOOGLE_STREAM_ID
        )

        if (
            target.get("campaign_id") != CAMPAIGN_ID
            or target.get("type") != "default"
            or target.get("schema") != "landings"
        ):
            raise ValueError("Unexpected target stream configuration")

        if target.get("state") != "active":
            raise ValueError("Target stream is not active")

        current_offers = target.get("offers", [])

        if not current_offers or any(
            offer.get("state") != "active"
            for offer in current_offers
        ):
            raise ValueError("Unexpected existing offer states")

        current_ids = [
            offer["offer_id"] for offer in current_offers
        ]

        available_offers = await client.get_offers()

        if not any(
            offer.get("id") == NEW_OFFER_ID
            for offer in available_offers
        ):
            raise ValueError("New offer does not exist")

        if NEW_OFFER_ID in current_ids:
            raise ValueError(
                "Offer already attached. Check its shares manually."
            )

        updated_offers = distribute_offer_shares(
            current_ids + [NEW_OFFER_ID]
        )

        print("Current offers:")
        print(json.dumps(current_offers, indent=2))

        print("\nProposed offers:")
        print(json.dumps(updated_offers, indent=2))

        if not apply:
            print("\nDRY RUN: no changes made.")
            return

        # Save the new offer distribution.
        await client.update_stream_offers(
            STREAM_ID,
            updated_offers,
        )

        # Read actual data from Keitaro again.
        streams_after = await client.get_campaign_streams(
            CAMPAIGN_ID
        )

        updated_target = find_stream(
            streams_after, STREAM_ID
        )
        updated_google = find_stream(
            streams_after, GOOGLE_STREAM_ID
        )

        actual = {
            item["offer_id"]: (
                item["share"],
                item["state"],
            )
            for item in updated_target.get("offers", [])
        }

        expected = {
            item["offer_id"]: (
                item["share"],
                item["state"],
            )
            for item in updated_offers
        }

        if actual != expected:
            raise ValueError(
                "Saved offer distribution does not match"
            )

        if protected_settings(target) != protected_settings(
            updated_target
        ):
            raise ValueError(
                "Target stream settings changed unexpectedly"
            )

        if google != updated_google:
            raise ValueError(
                "Google stream changed unexpectedly"
            )

        print("\nSUCCESS: offer distribution updated!")
        print(json.dumps(
            updated_target["offers"],
            indent=2,
            ensure_ascii=False,
        ))
        print("\nGoogle stream unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to Keitaro",
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(args.apply))
    except (KeitaroError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1) from exc

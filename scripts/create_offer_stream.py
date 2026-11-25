
import argparse
import asyncio
import json
from typing import Any

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)
from scripts.preview_streams import (
    CAMPAIGN_ID,
    build_offer_stream,
)


def validate_stream(
    stream: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Verify that Keitaro saved the expected configuration."""

    fields = (
        "campaign_id",
        "name",
        "type",
        "schema",
        "state",
        "position",
    )

    for field in fields:
        if stream.get(field) != expected.get(field):
            raise ValueError(
                f"Mismatch in {field}: "
                f"expected {expected.get(field)!r}, "
                f"got {stream.get(field)!r}"
            )

    offers = stream.get("offers")

    if not isinstance(offers, list) or len(offers) != 1:
        raise ValueError("Expected exactly one offer")

    offer = offers[0]
    expected_offer = expected["offers"][0]

    for field in ("offer_id", "share", "state"):
        if offer.get(field) != expected_offer[field]:
            raise ValueError(
                f"Unexpected offer {field}: {offer.get(field)!r}"
            )


async def main(apply: bool) -> None:
    payload = build_offer_stream()

    try:
        async with KeitaroClient(
            api_url=settings.keitaro_api_url,
            api_key=settings.keitaro_api_key.get_secret_value(),
        ) as client:

            # Check that the selected offer exists.
            offers = await client.get_offers()

            selected_offer = next(
                (
                    offer for offer in offers
                    if offer.get("id") == payload["offers"][0]["offer_id"]
                ),
                None,
            )

            if selected_offer is None:
                raise ValueError("Selected offer does not exist")

            print(f"Selected offer: {selected_offer['name']}")

            # Check existing streams to avoid duplicates.
            streams = await client.get_campaign_streams(
                CAMPAIGN_ID
            )

            existing = next(
                (
                    stream for stream in streams
                    if stream.get("name") == payload["name"]
                ),
                None,
            )

            if existing is not None:
                print(f"Stream already exists: {existing['id']}")
                validate_stream(existing, payload)
                print("Existing configuration is correct.")
                return

            print("\nPrepared payload:")
            print(json.dumps(payload, indent=2))

            if not apply:
                print("\nDRY RUN: no changes made.")
                return

            # Create the stream.
            created = await client.create_stream(payload)
            stream_id = created["id"]

            print(f"\nStream created! ID: {stream_id}")

            # Read the saved configuration back.
            updated = await client.get_campaign_streams(
                CAMPAIGN_ID
            )

            saved = next(
                (
                    stream for stream in updated
                    if stream.get("id") == stream_id
                ),
                None,
            )

            if saved is None:
                raise ValueError(
                    "Created stream was not found in Keitaro"
                )

            validate_stream(saved, payload)

            print("Stream configuration verified!")
            print(f"Type: {saved['type']}")
            print(f"Schema: {saved['schema']}")
            print(f"Offers: {saved['offers']}")

    except (KeitaroError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the offer stream in Keitaro",
    )

    args = parser.parse_args()
    asyncio.run(main(args.apply))

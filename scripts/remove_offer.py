
import argparse
import asyncio
import json

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)
from app.services.offer_editor import (
    remove_offer_from_distribution,
)

from scripts.apply_offer_edit import (
    CAMPAIGN_ID,
    STREAM_ID,
    GOOGLE_STREAM_ID,
    find_stream,
    protected_settings,
)


REMOVE_OFFER_ID = 18004


async def main(apply: bool) -> None:
    async with KeitaroClient(
        api_url=settings.keitaro_api_url,
        api_key=settings.keitaro_api_key.get_secret_value(),
    ) as client:

        streams_before = await client.get_campaign_streams(
            CAMPAIGN_ID
        )

        target = find_stream(
            streams_before, STREAM_ID
        )

        google = find_stream(
            streams_before, GOOGLE_STREAM_ID
        )

        if (
            target.get("campaign_id") != CAMPAIGN_ID
            or target.get("type") != "default"
            or target.get("schema") != "landings"
        ):
            raise ValueError("Unexpected stream configuration")

        current_offers = target.get("offers", [])

        updated_offers = remove_offer_from_distribution(
            current_offers,
            REMOVE_OFFER_ID,
        )

        print("Current offers:")
        print(json.dumps(current_offers, indent=2))

        print("\nProposed offers:")
        print(json.dumps(updated_offers, indent=2))

        if not apply:
            print("\nDRY RUN: no changes made.")
            return

        await client.update_stream_offers(
            STREAM_ID,
            updated_offers,
        )

        streams_after = await client.get_campaign_streams(
            CAMPAIGN_ID
        )

        updated_target = find_stream(
            streams_after, STREAM_ID
        )

        updated_google = find_stream(
            streams_after, GOOGLE_STREAM_ID
        )

        def normalized(offers: list[dict]) -> set[tuple]:
            return {
                (
                    item["offer_id"],
                    item["share"],
                    item["state"],
                )
                for item in offers
            }

        if normalized(
            updated_target.get("offers", [])
        ) != normalized(updated_offers):
            raise ValueError(
                "Saved offers do not match expected distribution"
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

        print("\nSUCCESS: offer removed from stream!")
        print(json.dumps(
            updated_target["offers"],
            indent=2,
        ))
        print("\nGoogle stream unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply removal in Keitaro",
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(args.apply))
    except (KeitaroError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1) from exc

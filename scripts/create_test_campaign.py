
import argparse
import asyncio

from app.core.config import settings
from app.integrations.keitaro import KeitaroClient, KeitaroError


CAMPAIGN_NAME = "test_medvedev_campaign1"

PAYLOAD = {
    "name": CAMPAIGN_NAME,
    "alias": CAMPAIGN_NAME,
    "type": "position",
    "state": "disabled",
    "group_id": "10332",
    "traffic_source_id": 836,
}


async def main(apply: bool) -> None:
    try:
        async with KeitaroClient(
            api_url=settings.keitaro_api_url,
            api_key=settings.keitaro_api_key.get_secret_value(),
        ) as client:
            campaigns = await client.get_campaigns()

            existing = next(
                (
                    item for item in campaigns
                    if item.get("name") == CAMPAIGN_NAME
                    or item.get("alias") == CAMPAIGN_NAME
                ),
                None,
            )

            if existing:
                print("Campaign already exists.")
                print(f"ID: {existing.get('id')}")
                return

            if not apply:
                print("DRY RUN: no changes will be made.")
                print("Prepared payload:")
                print(PAYLOAD)
                return

            campaign = await client.create_campaign(PAYLOAD)

            print("Campaign created!")
            print(f"ID: {campaign['id']}")
            print(f"Name: {campaign.get('name')}")
            print(f"State: {campaign.get('state')}")

            verified = await client.get_campaigns()
            found = any(
                item.get("id") == campaign["id"]
                for item in verified
            )

            print(f"Verified in campaign list: {found}")

    except KeitaroError as exc:
        print(f"Keitaro error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the campaign in Keitaro",
    )

    args = parser.parse_args()
    asyncio.run(main(args.apply))

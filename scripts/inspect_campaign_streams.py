
import asyncio

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)


CAMPAIGN_ID = 278


async def main() -> None:
    try:
        async with KeitaroClient(
            api_url=settings.keitaro_api_url,
            api_key=settings.keitaro_api_key.get_secret_value(),
        ) as client:
            streams = await client.get_campaign_streams(
                CAMPAIGN_ID
            )

        print(f"Campaign ID: {CAMPAIGN_ID}")
        print(f"Streams found: {len(streams)}")


        for stream in streams:
            print("-" * 50)

            fields = (
                "id",
                "name",
                "campaign_id",
                "type",
                "schema",
                "state",
                "position",
                "action_type",
                "action_payload",
                "filters",
                "offers",
            )

            for field in fields:
                print(f"{field}: {stream.get(field)}")

    except KeitaroError as exc:
        print(f"Keitaro error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())

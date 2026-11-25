
import asyncio
from typing import Any

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)


def show_items(
    title: str,
    items: list[dict[str, Any]],
    limit: int = 15,
) -> None:
    print(f"\n{title}: {len(items)}")

    for item in items[:limit]:
        identifier = item.get("id", item.get("key", item.get("value")))
        name = item.get("name", item.get("value", ""))

        print(f"  {identifier} | {name}")


async def main() -> None:
    async with KeitaroClient(
        api_url=settings.keitaro_api_url,
        api_key=settings.keitaro_api_key.get_secret_value(),
    ) as client:

        resources = [
            ("Campaign groups", client.get_campaign_groups),
            ("Stream schemas", client.get_stream_schemas),
            ("Stream types", client.get_stream_types),
            ("Stream filters", client.get_stream_filters),
        ]

        for title, getter in resources:
            try:
                items = await getter()

                show_items(title, items)

                if title == "Stream filters":
                    country_filters = [
                        item for item in items
                        if "country" in str(item).lower()
                        or "geo" in str(item).lower()
                    ]

                    print("\nCountry-related filters:")
                    for item in country_filters:
                        print(
                            f"  {item.get('value')} | "
                            f"Modes: {item.get('modes')}"
                        )

            except KeitaroError as exc:
                print(f"\n{title}: ERROR - {exc}")


if __name__ == "__main__":
    asyncio.run(main())

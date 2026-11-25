
import asyncio
from typing import Any

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)


def print_resources(
    title: str,
    items: list[dict[str, Any]],
) -> None:
    print(f"\n{title}: {len(items)}")

    for item in items[:5]:
        print(
            f"  ID: {item.get('id')} | "
            f"Name: {item.get('name')}"
        )


async def main() -> None:
    async with KeitaroClient(
        api_url=settings.keitaro_api_url,
        api_key=settings.keitaro_api_key.get_secret_value(),
    ) as client:

        resources = [
            ("Campaigns", client.get_campaigns),
            ("Domains", client.get_domains),
            ("Offers", client.get_offers),
            ("Traffic sources", client.get_traffic_sources),
        ]

        for title, getter in resources:
            try:
                items = await getter()
                print_resources(title, items)

            except KeitaroError as exc:
                print(f"\n{title}: ERROR - {exc}")


if __name__ == "__main__":
    asyncio.run(main())

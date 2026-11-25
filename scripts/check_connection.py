
import asyncio

from app.core.config import settings
from app.integrations.keitaro import KeitaroClient, KeitaroError


async def main() -> None:
    try:
        async with KeitaroClient(
            api_url=settings.keitaro_api_url,
            api_key=settings.keitaro_api_key.get_secret_value(),
        ) as client:
            campaigns = await client.get_campaigns()

        print("Connection successful!")
        print(f"Campaigns found: {len(campaigns)}")

    except KeitaroError as exc:
        print(f"Keitaro error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())


import argparse
import asyncio
import json

from app.core.config import settings
from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)
from scripts.preview_streams import (
    CAMPAIGN_ID,
    build_google_stream,
)


async def main(apply: bool) -> None:
    payload = build_google_stream()

    try:
        async with KeitaroClient(
            api_url=settings.keitaro_api_url,
            api_key=settings.keitaro_api_key.get_secret_value(),
        ) as client:

            # 1. Check existing streams
            streams = await client.get_campaign_streams(
                CAMPAIGN_ID
            )

            existing = next(
                (
                    stream
                    for stream in streams
                    if stream.get("name") == payload["name"]
                ),
                None,
            )

            if existing is not None:
                print("Stream already exists.")
                print(f"Stream ID: {existing.get('id')}")
                return

            # 2. Preview request body
            print("Prepared stream:")
            print(json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ))

            if not apply:
                print("\nDRY RUN: no changes made.")
                return

            # 3. Create stream
            created = await client.create_stream(payload)
            stream_id = created["id"]

            print("\nStream created!")
            print(f"Stream ID: {stream_id}")

            # 4. Read back from Keitaro
            updated_streams = await client.get_campaign_streams(
                CAMPAIGN_ID
            )

            saved = next(
                (
                    stream
                    for stream in updated_streams
                    if stream.get("id") == stream_id
                ),
                None,
            )

            if saved is None:
                print("ERROR: stream was not found after creation.")
                raise SystemExit(1)

            print("\nVerified stream:")
            for field in (
                "id",
                "name",
                "type",
                "schema",
                "state",
                "action_type",
                "action_payload",
                "filters",
            ):
                print(f"{field}: {saved.get(field)}")

    except KeitaroError as exc:
        print(f"\nKeitaro API error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the stream in Keitaro",
    )

    args = parser.parse_args()
    asyncio.run(main(args.apply))

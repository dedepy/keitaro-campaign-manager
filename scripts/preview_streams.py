
import json

CAMPAIGN_ID = 269
COUNTRY = "DE"
OFFER_ID = 18004


def build_google_stream() -> dict:
    return {
        "campaign_id": CAMPAIGN_ID,
        "name": "test_medvedev_google_DE",
        "type": "regular",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://www.google.com/",
        "position": 1,
        "state": "active",
        "filters": [
            {
                "name": "country",
                "mode": "accept",
                "payload": [COUNTRY],
            }
        ],
    }


def build_offer_stream() -> dict:
    return {
        "campaign_id": CAMPAIGN_ID,
        "name": "test_medvedev_default_offer",
        "type": "default",
        "schema": "landings",
        "action_type": "http",
        "position": 2,
        "state": "active",
        "offers": [
            {
                "offer_id": OFFER_ID,
                "share": 100,
                "state": "active",
            }
        ],
    }


if __name__ == "__main__":
    streams = [
        build_google_stream(),
        build_offer_stream(),
    ]

    print("DRY RUN: streams will NOT be created.")

    for index, stream in enumerate(streams, start=1):
        print(f"\nStream {index}:")
        print(json.dumps(
            stream,
            indent=2,
            ensure_ascii=False,
        ))

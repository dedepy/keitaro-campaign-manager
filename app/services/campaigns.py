
from typing import Any

from app.integrations.keitaro import (
    KeitaroClient,
    KeitaroError,
)
from app.schemas.campaign import CampaignCreateRequest


class CampaignAlreadyExistsError(ValueError):
    """Campaign name or alias is already in use."""

class CampaignSetupError(Exception):
    def __init__(self, campaign_id: int) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            f"Campaign {campaign_id} was created, "
            "but setup failed. Check its streams."
        )


def build_google_stream(
    campaign_id: int,
    geo: str,
) -> dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "name": f"Google GEO {geo}",
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
                "payload": [geo],
            }
        ],
    }


def build_offer_stream(
    campaign_id: int,
    offer_id: int,
) -> dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "name": "Default Offer",
        "type": "default",
        "schema": "landings",
        "action_type": "http",
        "position": 2,
        "state": "active",
        "offers": [
            {
                "offer_id": offer_id,
                "share": 100,
                "state": "active",
            }
        ],
    }


def resource_exists(
    items: list[dict[str, Any]],
    resource_id: int,
) -> bool:
    return any(
        str(item.get("id")) == str(resource_id)
        for item in items
    )


class CampaignService:
    def __init__(self, client: KeitaroClient) -> None:
        self.client = client

    async def create(
        self,
        data: CampaignCreateRequest,
    ) -> dict[str, Any]:

        # Step 1: Validate referenced resources.
        domains = await self.client.get_domains()
        groups = await self.client.get_campaign_groups()
        sources = await self.client.get_traffic_sources()
        offers = await self.client.get_offers()

        resources = (
            ("Domain", domains, data.domain_id),
            ("Group", groups, data.group_id),
            ("Traffic source", sources, data.traffic_source_id),
            ("Offer", offers, data.offer_id),
        )

        for name, items, resource_id in resources:
            if not resource_exists(items, resource_id):
                raise ValueError(
                    f"{name} with ID {resource_id} not found"
                )

        # Step 2: Prevent ordinary duplicate creation.
        campaigns = await self.client.get_campaigns()

        if any(
            item.get("name") == data.name
            or item.get("alias") == data.name
            for item in campaigns
        ):
            raise CampaignAlreadyExistsError("Campaign already exists")

        # Step 3: Create a disabled campaign.
        campaign_payload = {
            "name": data.name,
            "alias": data.name,
            "type": "position",
            "state": "disabled",
            "group_id": str(data.group_id),
            "traffic_source_id": data.traffic_source_id,
        }

        campaign = await self.client.create_campaign(
            campaign_payload
        )
        campaign_id = campaign["id"]

        # Step 4: Create and verify both streams.
        try:
            google = await self.client.create_stream(
                build_google_stream(campaign_id, data.geo)
            )

            fallback = await self.client.create_stream(
                build_offer_stream(campaign_id, data.offer_id)
            )

            streams = await self.client.get_campaign_streams(
                campaign_id
            )

            self._verify_streams(
                streams,
                google["id"],
                fallback["id"],
                data.geo,
                data.offer_id,
            )

        except (KeitaroError, ValueError) as exc:
            raise CampaignSetupError(campaign_id) from exc

        return {
            "campaign_id": campaign_id,
            "google_stream_id": google["id"],
            "offer_stream_id": fallback["id"],
            "domain_id": data.domain_id,
            "state": "disabled",
        }

    @staticmethod
    def _verify_streams(
        streams: list[dict[str, Any]],
        google_id: int,
        fallback_id: int,
        geo: str,
        offer_id: int,
    ) -> None:
        google = next(
            (s for s in streams if s.get("id") == google_id),
            None,
        )
        fallback = next(
            (s for s in streams if s.get("id") == fallback_id),
            None,
        )

        if google is None or fallback is None:
            raise ValueError("Created streams were not found")

        valid_google = (
            google.get("type") == "regular"
            and google.get("schema") == "redirect"
            and google.get("state") == "active"
            and google.get("position") == 1
            and google.get("action_type") == "http"
            and google.get("action_payload")
            == "https://www.google.com/"
            and any(
                f.get("name") == "country"
                and f.get("mode") == "accept"
                and f.get("payload") == [geo]
                for f in google.get("filters", [])
            )
        )

        valid_fallback = (
            fallback.get("type") == "default"
            and fallback.get("schema") == "landings"
            and fallback.get("state") == "active"
            and fallback.get("position") == 2
            and any(
                o.get("offer_id") == offer_id
                and o.get("share") == 100
                and o.get("state") == "active"
                for o in fallback.get("offers", [])
            )
        )

        if not valid_google or not valid_fallback:
            raise ValueError("Stream settings do not match")

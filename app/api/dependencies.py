from app.services.offer_editor import OfferEditorService
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.integrations.keitaro import KeitaroClient
from app.services.campaigns import CampaignService


async def get_keitaro_client() -> AsyncIterator[KeitaroClient]:
    # Load configuration only when this dependency is used.
    from app.core.config import settings

    async with KeitaroClient(
        api_url=settings.keitaro_api_url,
        api_key=settings.keitaro_api_key.get_secret_value(),
    ) as client:
        yield client


def get_campaign_service(
    client: Annotated[
        KeitaroClient,
        Depends(get_keitaro_client),
    ],
) -> CampaignService:
    return CampaignService(client)

def get_offer_editor_service(
    client: Annotated[
        KeitaroClient,
        Depends(get_keitaro_client),
    ],
) -> OfferEditorService:
    return OfferEditorService(client)


from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_campaign_service
from app.integrations.keitaro import KeitaroError
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignCreateResponse,
)
from app.services.campaigns import (
    CampaignAlreadyExistsError,
    CampaignService,
    CampaignSetupError,
)


router = APIRouter(tags=["Campaigns"])


@router.post(
    "/campaigns",
    response_model=CampaignCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    payload: CampaignCreateRequest,
    service: Annotated[
        CampaignService,
        Depends(get_campaign_service),
    ],
) -> CampaignCreateResponse:
    try:
        result = await service.create(payload)

    except CampaignAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except CampaignSetupError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Campaign was created, but stream "
                    "setup was not completed"
                ),
                "campaign_id": exc.campaign_id,
            },
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except KeitaroError as exc:
        raise HTTPException(
            status_code=502,
            detail="Keitaro API request failed",
        ) from exc

    return CampaignCreateResponse.model_validate(result)

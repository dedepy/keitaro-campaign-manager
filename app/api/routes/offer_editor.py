
from collections.abc import Awaitable
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
)

from app.api.dependencies import (
    get_keitaro_client,
    get_offer_editor_service,
)
from app.integrations.keitaro import KeitaroClient, KeitaroError
from app.schemas.offer import (
    OfferAddRequest,
    OfferEditResponse,
)
from app.services.offer_editor import (
    OfferEditorService,
    OfferNotFoundError,
    OfferUpdateVerificationError,
    StreamNotFoundError,
)


router = APIRouter(tags=["Offer Editor"])


async def execute_edit(
    operation: Awaitable[dict[str, Any]],
) -> OfferEditResponse:
    try:
        result = await operation

    except (StreamNotFoundError, OfferNotFoundError) as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except OfferUpdateVerificationError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Update verification failed. "
                "The change may already be saved in Keitaro. "
                "Inspect the stream before retrying."
            ),
        ) from exc

    except KeitaroError as exc:
        raise HTTPException(
            status_code=502,
            detail="Keitaro API request failed",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return OfferEditResponse.model_validate(result)


@router.get("/campaigns/{campaign_id}/streams")
async def get_campaign_streams(
    campaign_id: Annotated[int, Path(gt=0)],
    client: Annotated[
        KeitaroClient,
        Depends(get_keitaro_client),
    ],
) -> list[dict[str, Any]]:
    try:
        return await client.get_campaign_streams(
            campaign_id
        )

    except KeitaroError as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to load Keitaro streams",
        ) from exc


@router.post(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers",
    response_model=OfferEditResponse,
)
async def add_offer(
    campaign_id: Annotated[int, Path(gt=0)],
    stream_id: Annotated[int, Path(gt=0)],
    payload: OfferAddRequest,
    service: Annotated[
        OfferEditorService,
        Depends(get_offer_editor_service),
    ],
) -> OfferEditResponse:
    return await execute_edit(
        service.add_offer(
            campaign_id,
            stream_id,
            payload.offer_id,
        )
    )


@router.delete(
    "/campaigns/{campaign_id}/streams/{stream_id}/offers/{offer_id}",
    response_model=OfferEditResponse,
)
async def remove_offer(
    campaign_id: Annotated[int, Path(gt=0)],
    stream_id: Annotated[int, Path(gt=0)],
    offer_id: Annotated[int, Path(gt=0)],
    service: Annotated[
        OfferEditorService,
        Depends(get_offer_editor_service),
    ],
) -> OfferEditResponse:
    return await execute_edit(
        service.remove_offer(
            campaign_id,
            stream_id,
            offer_id,
        )
    )


from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
)


class OfferAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_id: PositiveInt


class OfferShareResponse(BaseModel):
    offer_id: PositiveInt
    share: int = Field(ge=1, le=100)
    state: Literal["active"]


class OfferEditResponse(BaseModel):
    campaign_id: PositiveInt
    stream_id: PositiveInt
    changed: bool
    offers: list[OfferShareResponse]

from typing import Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
)


class CampaignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=15,
        max_length=80,
        pattern=r"^test_medvedev_[a-z0-9_-]+$",
    )

    geo: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )

    domain_id: PositiveInt
    group_id: PositiveInt
    traffic_source_id: PositiveInt
    offer_id: PositiveInt

    @field_validator("geo", mode="before")
    @classmethod
    def normalize_geo(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()

        return value

class CampaignCreateResponse(BaseModel):
    campaign_id: PositiveInt
    google_stream_id: PositiveInt
    offer_stream_id: PositiveInt
    domain_id: PositiveInt
    state: Literal["disabled"]

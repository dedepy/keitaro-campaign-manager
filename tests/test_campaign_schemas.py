
import pytest
from pydantic import ValidationError

from app.schemas.campaign import CampaignCreateRequest


VALID_DATA = {
    "name": "test_medvedev_campaign2",
    "geo": "DE",
    "domain_id": 1813,
    "group_id": 10332,
    "traffic_source_id": 836,
    "offer_id": 18004,
}


def test_valid_campaign_request() -> None:
    data = VALID_DATA.copy()
    data["geo"] = "de"

    campaign = CampaignCreateRequest(**data)

    assert campaign.geo == "DE"
    assert campaign.offer_id == 18004
    assert campaign.group_id == 10332


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"geo": "GER"},
        {"offer_id": -1},
        {"name": "campaign_without_prefix"},
    ],
)
def test_invalid_campaign_request(
    invalid_data: dict,
) -> None:
    data = {**VALID_DATA, **invalid_data}

    with pytest.raises(ValidationError):
        CampaignCreateRequest(**data)

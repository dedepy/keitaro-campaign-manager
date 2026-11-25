
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_campaign_service
from app.main import app
from app.services.campaigns import (
    CampaignAlreadyExistsError,
    CampaignSetupError,
)


VALID_BODY = {
    "name": "test_medvedev_campaign2",
    "geo": "DE",
    "domain_id": 1813,
    "group_id": 10332,
    "traffic_source_id": 836,
    "offer_id": 18004,
}


def post_with_mock(
    service: SimpleNamespace,
    body: dict,
):
    app.dependency_overrides[get_campaign_service] = (
        lambda: service
    )

    try:
        with TestClient(app) as client:
            return client.post(
                "/api/campaigns",
                json=body,
            )
    finally:
        app.dependency_overrides.pop(
            get_campaign_service,
            None,
        )


def test_create_campaign_api_success() -> None:
    service = SimpleNamespace(
        create=AsyncMock(
            return_value={
                "campaign_id": 300,
                "google_stream_id": 601,
                "offer_stream_id": 602,
                "domain_id": 1813,
                "state": "disabled",
            }
        )
    )

    response = post_with_mock(service, VALID_BODY)

    assert response.status_code == 201
    assert response.json()["campaign_id"] == 300
    assert response.json()["state"] == "disabled"

    service.create.assert_awaited_once()


def test_create_campaign_api_invalid_geo() -> None:
    service = SimpleNamespace(create=AsyncMock())

    body = {**VALID_BODY, "geo": "GER"}

    response = post_with_mock(service, body)

    assert response.status_code == 422
    service.create.assert_not_awaited()


def test_create_campaign_api_duplicate() -> None:
    service = SimpleNamespace(
        create=AsyncMock(
            side_effect=CampaignAlreadyExistsError(
                "Campaign already exists"
            )
        )
    )

    response = post_with_mock(service, VALID_BODY)

    assert response.status_code == 409


def test_create_campaign_api_partial_failure() -> None:
    service = SimpleNamespace(
        create=AsyncMock(
            side_effect=CampaignSetupError(300)
        )
    )

    response = post_with_mock(service, VALID_BODY)

    assert response.status_code == 502
    assert response.json()["detail"]["campaign_id"] == 300


from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_keitaro_client,
    get_offer_editor_service,
)
from app.integrations.keitaro import KeitaroError
from app.main import app
from app.services.offer_editor import (
    OfferUpdateVerificationError,
    StreamNotFoundError,
)


BASE_URL = "/api/campaigns/278/streams/535"

RESULT = {
    "campaign_id": 278,
    "stream_id": 535,
    "changed": True,
    "offers": [
        {
            "offer_id": 18005,
            "share": 100,
            "state": "active",
        }
    ],
}


def make_request(
    method: str,
    url: str,
    service=None,
    keitaro=None,
    body=None,
):
    if service is not None:
        app.dependency_overrides[
            get_offer_editor_service
        ] = lambda: service

    if keitaro is not None:
        app.dependency_overrides[
            get_keitaro_client
        ] = lambda: keitaro

    try:
        with TestClient(app) as client:
            return client.request(
                method,
                url,
                json=body,
            )
    finally:
        app.dependency_overrides.pop(
            get_offer_editor_service,
            None,
        )
        app.dependency_overrides.pop(
            get_keitaro_client,
            None,
        )


def test_get_streams_api() -> None:
    keitaro = SimpleNamespace(
        get_campaign_streams=AsyncMock(
            return_value=[{"id": 535}]
        )
    )

    response = make_request(
        "GET",
        "/api/campaigns/278/streams",
        keitaro=keitaro,
    )

    assert response.status_code == 200
    assert response.json() == [{"id": 535}]
    keitaro.get_campaign_streams.assert_awaited_once_with(278)


def test_add_offer_api() -> None:
    service = SimpleNamespace(
        add_offer=AsyncMock(return_value=RESULT)
    )

    response = make_request(
        "POST",
        BASE_URL + "/offers",
        service=service,
        body={"offer_id": 18005},
    )

    assert response.status_code == 200
    assert response.json()["changed"] is True

    service.add_offer.assert_awaited_once_with(
        278, 535, 18005
    )


def test_remove_offer_api() -> None:
    service = SimpleNamespace(
        remove_offer=AsyncMock(return_value=RESULT)
    )

    response = make_request(
        "DELETE",
        BASE_URL + "/offers/18004",
        service=service,
    )

    assert response.status_code == 200
    service.remove_offer.assert_awaited_once_with(
        278, 535, 18004
    )


def test_invalid_offer_id_api() -> None:
    service = SimpleNamespace(add_offer=AsyncMock())

    response = make_request(
        "POST",
        BASE_URL + "/offers",
        service=service,
        body={"offer_id": -1},
    )

    assert response.status_code == 422
    service.add_offer.assert_not_awaited()


def test_missing_stream_api() -> None:
    service = SimpleNamespace(
        remove_offer=AsyncMock(
            side_effect=StreamNotFoundError(
                "Stream not found"
            )
        )
    )

    response = make_request(
        "DELETE",
        BASE_URL + "/offers/18004",
        service=service,
    )

    assert response.status_code == 404


def test_keitaro_error_api() -> None:
    service = SimpleNamespace(
        add_offer=AsyncMock(
            side_effect=KeitaroError(
                "Keitaro returned HTTP 500",
                500,
            )
        )
    )

    response = make_request(
        "POST",
        BASE_URL + "/offers",
        service=service,
        body={"offer_id": 18005},
    )

    assert response.status_code == 502


def test_verification_failure_api() -> None:
    service = SimpleNamespace(
        remove_offer=AsyncMock(
            side_effect=OfferUpdateVerificationError(
                "Saved state does not match"
            )
        )
    )

    response = make_request(
        "DELETE",
        BASE_URL + "/offers/18004",
        service=service,
    )

    assert response.status_code == 502
    assert "may already be saved" in (
        response.json()["detail"]
    )


def test_noop_api() -> None:
    no_change = {**RESULT, "changed": False}
    service = SimpleNamespace(
        remove_offer=AsyncMock(return_value=no_change)
    )

    response = make_request(
        "DELETE",
        BASE_URL + "/offers/18004",
        service=service,
    )

    assert response.status_code == 200
    assert response.json()["changed"] is False

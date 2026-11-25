
from typing import Any, Self

import httpx


class KeitaroError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class KeitaroClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=api_url.rstrip("/") + "/",
            headers={
                "Api-Key": api_key,
                "Accept": "application/json",
            },
            timeout=15.0,
            follow_redirects=False,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        await self._client.aclose()

    async def request(
            self,
            method: str,
            endpoint: str,
            payload: dict[str, Any] | None = None,
            params: dict[str, str] | None = None,
    ) -> Any:
        try:
            response = await self._client.request(
                method=method,
                url=endpoint.lstrip("/"),
                json=payload,
                params=params,
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise KeitaroError(
                f"Keitaro returned HTTP {status}",
                status_code=status,
            ) from exc

        except httpx.RequestError as exc:
            raise KeitaroError(
                "Failed to communicate with Keitaro"
            ) from exc

        try:
            return response.json()

        except ValueError as exc:
            raise KeitaroError(
                "Keitaro returned invalid JSON"
            ) from exc


    async def create_campaign(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = await self.request(
            method="POST",
            endpoint="campaigns",
            payload=payload,
        )

        if not isinstance(data, dict):
            raise KeitaroError(
                "Unexpected campaign creation response"
            )

        if not isinstance(data.get("id"), int):
            raise KeitaroError(
                "Created campaign has no valid ID"
            )

        return data

    async def _get_collection(
        self,
        endpoint: str,
        resource_name: str,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        data = await self.request(
            "GET",
            endpoint,
            params=params,
        )

        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise KeitaroError(
                f"Unexpected {resource_name} response format"
            )

        return data

    async def get_campaigns(self) -> list[dict[str, Any]]:
        return await self._get_collection(
            "campaigns", "campaigns"
        )

    async def get_domains(self) -> list[dict[str, Any]]:
        return await self._get_collection(
            "domains", "domains"
        )

    async def get_offers(self) -> list[dict[str, Any]]:
        return await self._get_collection(
            "offers", "offers"
        )

    async def get_traffic_sources(self) -> list[dict[str, Any]]:
        return await self._get_collection(
            "traffic_sources", "traffic sources"
        )

    async def get_campaign_groups(
        self,
    ) -> list[dict[str, Any]]:
        return await self._get_collection(
            "groups",
            "campaign groups",
            params={"type": "campaigns"},
        )

    async def get_stream_schemas(
        self,
    ) -> list[dict[str, Any]]:
        return await self._get_collection(
            "stream_schemas",
            "stream schemas",
        )

    async def get_stream_filters(
        self,
    ) -> list[dict[str, Any]]:
        return await self._get_collection(
            "stream_filters",
            "stream filters",
        )

    async def get_stream_types(
        self,
    ) -> list[dict[str, Any]]:
        return await self._get_collection(
            "stream_types",
            "stream types",
        )

    async def get_campaign_streams(
        self,
        campaign_id: int,
    ) -> list[dict[str, Any]]:
        if campaign_id <= 0:
            raise ValueError("Campaign ID must be positive")

        return await self._get_collection(
            endpoint=f"campaigns/{campaign_id}/streams",
            resource_name="campaign streams",
        )

    async def create_stream(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = await self.request(
            method="POST",
            endpoint="streams",
            payload=payload,
        )

        if not isinstance(data, dict):
            raise KeitaroError(
                "Unexpected stream creation response"
            )

        stream_id = data.get("id")

        if not isinstance(stream_id, int) or isinstance(
            stream_id, bool
        ) or stream_id <= 0:
            raise KeitaroError(
                "Created stream has no valid ID"
            )

        return data


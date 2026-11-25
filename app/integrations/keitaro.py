
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
    ) -> Any:
        try:
            response = await self._client.request(
                method=method,
                url=endpoint.lstrip("/"),
                json=payload,
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

    async def get_campaigns(self) -> list[dict[str, Any]]:
        data = await self.request("GET", "campaigns")

        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise KeitaroError(
                "Unexpected campaigns response format"
            )

        return data

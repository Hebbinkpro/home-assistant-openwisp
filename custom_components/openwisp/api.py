"""Sample API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp
import async_timeout


class OpenWispApiClientError(Exception):
    """Exception to indicate a general API error."""


class OpenWispApiClientCommunicationError(
    OpenWispApiClientError,
):
    """Exception to indicate a communication error."""


class OpenWispApiClientAuthenticationError(
    OpenWispApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise OpenWispApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()




class OpenWispApiClient:
    """Sample API Client."""

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        *,
        verify_ssl: bool = True,
    ) -> None:
        """Sample API Client."""
        self._url = url.strip(" \t/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._session = session
        self._token: str|None = None

    async def async_authenticate(self) -> None:
        """Retrieve an access token from the API."""
        res = await self._api_wrapper(
            method="post",
            path="/api/v1/users/token/",
            data={
                "username": self._username,
                "password": self._password,
            },
        )

        if "token" not in res:
            raise OpenWispApiClientAuthenticationError
        self._token = res["token"]

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="get",
            path="/posts/1",
        )

    async def async_set_title(self, value: str) -> Any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="patch",
            path="/posts/1",
            data={"title": value},
        )

    async def async_get_devices(self) -> list[Device]:
        """Get all device information from the API."""
        res = await self._api_wrapper(
            method="get",
            path="/api/v1/monitoring/device/"
        )

        return [Device.from_dict(device) for device in res["results"]]

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        headers = headers or {}
        if data is not None:
            headers["Content-type"] = "application/json; charset=UTF-8"
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=f"{self._url}{path}",
                    headers=headers,
                    json=data,
                    ssl=self._verify_ssl,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise OpenWispApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise OpenWispApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise OpenWispApiClientError(
                msg,
            ) from exception

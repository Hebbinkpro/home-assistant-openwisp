"""Sample API Client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import ipaddress
import socket
from dataclasses import dataclass
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

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


@dataclass(slots=True)
class DeviceConfigStatus:
    """Configuration information of an OpenWISP device."""

    status: str
    error_reason: str
    backend: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceConfigStatus:
        """Create DeviceConfig from a dict."""
        return cls(**data)


@dataclass(slots=True)
class DeviceMonitoringStatus:
    """Monitoring information of an OpenWISP device."""

    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceMonitoringStatus:
        """Create DeviceMonitoring from a dict."""
        return cls(**data)


@dataclass(slots=True)
class OpenWispDevice:
    """OpenWISP device."""

    id: UUID
    name: str
    organization: UUID
    group: UUID
    mac_address: str
    key: str
    last_ip: IPv4Address | IPv6Address
    management_ip: IPv4Address | IPv6Address
    model: str
    os: str
    system: str
    notes: str
    config: DeviceConfigStatus
    monitoring: DeviceMonitoringStatus
    created: datetime
    modified: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenWispDevice:
        """Create a Device from a dict."""
        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            organization=UUID(data["organization"]),
            group=UUID(data["group"]),
            mac_address=data["mac_address"].upper(),
            key=data["key"],
            last_ip=ipaddress.ip_address(data["last_ip"]),
            management_ip=ipaddress.ip_address(data["management_ip"]),
            model=data["model"],
            os=data["os"],
            system=data["system"],
            notes=data["notes"],
            config=DeviceConfigStatus.from_dict(data["config"]),
            monitoring=DeviceMonitoringStatus.from_dict(data["monitoring"]),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]),
        )


@dataclass(slots=True)
class OpenWispOrganization:
    """OpenWISP organization."""

    id: UUID
    name: str
    is_active: bool
    slug: str
    description: str
    url: str
    created: datetime
    modified: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenWispOrganization:
        """Create an Organization from a dict."""
        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            is_active=data["is_active"],
            slug=data["slug"],
            description=data["description"],
            url=data["url"],
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]),
        )


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
        self._token: str | None = None

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

    async def get_organizations(self) -> list[OpenWispOrganization]:
        """Get all organizations from the API."""
        res = await self._api_wrapper(
            method="get",
            path="/api/v1/users/organization/",
        )
        return [OpenWispOrganization.from_dict(org) for org in res["results"]]

    async def async_get_devices(self) -> list[OpenWispDevice]:
        """Get all device information from the API."""
        res = await self._api_wrapper(method="get", path="/api/v1/monitoring/device/")

        return [OpenWispDevice.from_dict(device) for device in res["results"]]

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

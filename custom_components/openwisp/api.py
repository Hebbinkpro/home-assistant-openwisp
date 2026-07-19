"""Sample API Client."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any
from urllib.parse import urlparse
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


@dataclass(slots=True)
class DeviceListConfig:
    """Configuration information of an OpenWISP device."""

    status: str
    error_reason: str
    backend: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceListConfig:
        """Create DeviceConfig from a dict."""
        return cls(**data)


@dataclass(slots=True)
class BaseDeviceMonitoring:
    """Monitoring information of an OpenWISP device."""

    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseDeviceMonitoring:
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
    config: DeviceListConfig
    monitoring: BaseDeviceMonitoring
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
            config=DeviceListConfig.from_dict(data["config"]),
            monitoring=BaseDeviceMonitoring.from_dict(data["monitoring"]),
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
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._host = host
        self._username = username
        self._password = password
        self._session = session

        self._token: str | None = None
        self._auth_lock = asyncio.Lock()

    @property
    def hostname(self) -> str:
        """Return the hostname of the API."""
        return urlparse(self._host).hostname or ""

    @property
    def is_authenticated(self) -> bool:
        """Return True if the API is authenticated."""
        return self._token is not None

    async def async_get_organizations(self) -> list[OpenWispOrganization]:
        """Get all organizations from the API."""
        res = await self._api_wrapper(
            method="get",
            path="/api/v1/users/organization/",
        )
        return [OpenWispOrganization.from_dict(org) for org in res["results"]]

    async def async_get_devices(
        self, organization: UUID | None = None
    ) -> dict[UUID, OpenWispDevice]:
        """Get all device information from the API."""
        if organization is None:
            res = await self._api_wrapper(
                method="get", path="/api/v1/monitoring/device/"
            )
        else:
            res = await self._api_wrapper(
                method="get",
                path=f"/api/v1/monitoring/device/?organization={organization}",
            )

        return {
            UUID(device["id"]): OpenWispDevice.from_dict(device)
            for device in res["results"]
        }

    async def async_authenticate(self) -> None:
        """Authenticate and store a new token."""
        res = await self._request(
            method="post",
            path="/api/v1/users/token/",
            data={
                "username": self._username,
                "password": self._password,
            },
            auth=False,
        )

        self._token = res["token"]

    async def _ensure_authenticated(self) -> None:
        """Ensure a valid token exists."""
        if self._token is not None:
            return

        async with self._auth_lock:
            if self._token is None:
                await self.async_authenticate()

    async def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
        *,
        auth: bool = True,
    ) -> Any:
        """Perform a single HTTP request."""
        headers = dict(headers or {})

        if data is not None:
            headers["Content-Type"] = "application/json"

        if auth and self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        async with async_timeout.timeout(10):
            response = await self._session.request(
                method=method,
                url=f"{self._host}{path}",
                json=data,
                headers=headers,
            )

        if response.status in (401, 403):
            raise OpenWispApiClientAuthenticationError

        response.raise_for_status()
        return await response.json()

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
        *,
        auth: bool = True,
    ) -> Any:
        """Perform an authenticated API request with automatic reauthentication."""
        try:
            if auth:
                await self._ensure_authenticated()

            return await self._request(
                method=method,
                path=path,
                data=data,
                headers=headers,
                auth=auth,
            )

        except OpenWispApiClientAuthenticationError:
            if not auth:
                raise

            # Token expired -> clear and reauthenticate
            self._token = None

            async with self._auth_lock:
                if self._token is None:
                    await self.async_authenticate()

            # Retry once
            return await self._request(
                method=method,
                path=path,
                data=data,
                headers=headers,
                auth=True,
            )

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise OpenWispApiClientCommunicationError(msg) from exception

        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise OpenWispApiClientCommunicationError(msg) from exception

        except Exception as exception:
            msg = f"Unknown error fetching information - {exception}"
            raise OpenWispApiClientError(msg) from exception

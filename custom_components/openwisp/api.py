"""Sample API Client."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import aiohttp
import async_timeout
from slugify import slugify

from custom_components.openwisp.const import LOGGER

_SEMAPHORE = asyncio.Semaphore(10)


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


@dataclass
class DeviceListConfig:
    """Configuration information of an OpenWISP device."""

    status: str
    error_reason: str
    backend: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceListConfig:
        """Create DeviceConfig from a dict."""
        return cls(**data)


@dataclass
class BaseDeviceMonitoring:
    """Monitoring information of an OpenWISP device."""

    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseDeviceMonitoring:
        """Create DeviceMonitoring from a dict."""
        return cls(
            status=data["status"],
        )


@dataclass
class DeviceStatusMemoryResources:
    """Device status memory resources of an OpenWISP device."""

    total: int
    shared: int
    free: int
    cached: int
    available: int
    buffered: int


@dataclass
class DeviceStatusDiskResources:
    """Device status disk resources of an OpenWISP device."""

    filesystem: str
    available_bytes: int
    mount_point: str
    used_percent: int
    size_bytes: int
    used_bytes: int


@dataclass
class DeviceStatusSwapResources:
    """Device status swap resources of an OpenWISP device."""

    free: int
    total: int


@dataclass
class DeviceStatusResources:
    """Device status resources of an OpenWISP device."""

    memory: DeviceStatusMemoryResources
    cpus: int
    disks: dict[str, DeviceStatusDiskResources]
    load: tuple[float, float, float]
    swap: DeviceStatusSwapResources

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusResources:
        """Create DeviceStatusResources from a dict."""
        return cls(
            memory=DeviceStatusMemoryResources(**data["memory"]),
            cpus=data["cpus"],
            disks={
                slugify(disk["filesystem"]): DeviceStatusDiskResources(**disk)
                for disk in data["disk"]
            },
            load=(data["load"][0], data["load"][1], data["load"][2]),
            swap=DeviceStatusSwapResources(**data["swap"]),
        )


@dataclass
class DeviceWirelessClient:
    """Client associated with a wireless interface."""

    mac_address: str
    signal: int | None


@dataclass
class DeviceWirelessInterface:
    """Wireless interface of an OpenWISP device."""

    name: str
    ssid: str | None
    mode: str | None
    channel: int | None
    frequency: int | None
    tx_power: int | None
    noise: int | None
    clients: list[DeviceWirelessClient]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceWirelessInterface:
        """Create DeviceWirelessInterface from an interface dict."""
        wireless = data["wireless"]
        return cls(
            name=data["name"],
            ssid=wireless.get("ssid"),
            mode=wireless.get("mode"),
            channel=wireless.get("channel"),
            frequency=wireless.get("frequency"),
            tx_power=wireless.get("tx_power"),
            noise=wireless.get("noise"),
            clients=[
                DeviceWirelessClient(
                    mac_address=client["mac"].upper(),
                    signal=client.get("signal"),
                )
                for client in wireless.get("clients") or []
            ],
        )


@dataclass
class DeviceStatusInformation:
    """Device status information of an OpenWISP device."""

    type: str
    local_time: datetime
    uptime: timedelta
    hostname: str
    resources: DeviceStatusResources
    wireless: dict[str, DeviceWirelessInterface]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusInformation:
        """Create DeviceStatusInformation from a dict."""
        if data["type"] != "DeviceMonitoring":
            msg = f"Invalid device status information type: {data['type']}"
            raise ValueError(msg)

        return cls(
            type=data["type"],
            local_time=datetime.fromtimestamp(
                data["general"]["local_time"],
                tz=UTC,
            ),
            uptime=timedelta(seconds=data["general"]["uptime"]),
            hostname=data["general"]["hostname"],
            resources=DeviceStatusResources.from_dict(data["resources"]),
            wireless={
                interface["name"]: DeviceWirelessInterface.from_dict(interface)
                for interface in data.get("interfaces") or []
                if interface.get("wireless")
            },
        )


@dataclass
class DeviceWifiSessions:
    """Device Wi-Fi session information of an OpenWISP device."""

    active_sessions: int


@dataclass
class WifiSession:
    """Open Wi-Fi session of a client on an OpenWISP device."""

    device: str
    ssid: str
    interface_name: str
    mac_address: str
    vendor: str | None
    start_time: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WifiSession:
        """Create a WifiSession from a dict."""
        return cls(
            device=data["device"],
            ssid=data["ssid"],
            interface_name=data["interface_name"],
            mac_address=data["client"]["mac_address"].upper(),
            vendor=data["client"].get("vendor") or None,
            start_time=datetime.fromisoformat(data["start_time"]),
        )


@dataclass(slots=True)
class OpenWispDevice:
    """OpenWISP device."""

    id: UUID
    name: str
    organization: UUID
    group: UUID | None
    mac_address: str
    last_ip: IPv4Address | IPv6Address
    management_ip: IPv4Address | IPv6Address | None
    model: str
    os: str
    system: str
    notes: str
    config: DeviceListConfig
    monitoring: BaseDeviceMonitoring
    created: datetime
    modified: datetime
    data: DeviceStatusInformation | None
    wifi_sessions: DeviceWifiSessions | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenWispDevice:
        """Create a Device from a dict."""
        status_information = None
        if data.get("data") is not None:
            status_information = DeviceStatusInformation.from_dict(data["data"])

        # the management IP is apparently nullable
        management_ip = None
        if data["management_ip"] is not None:
            management_ip = ipaddress.ip_address(data["management_ip"])

        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            organization=UUID(data["organization"]),
            group=UUID(data["group"]) if data.get("group") else None,
            mac_address=data["mac_address"].upper(),
            last_ip=ipaddress.ip_address(data["last_ip"]),
            management_ip=management_ip,
            model=data["model"],
            os=data["os"],
            system=data["system"],
            notes=data["notes"],
            config=DeviceListConfig.from_dict(data["config"]),
            monitoring=BaseDeviceMonitoring.from_dict(data["monitoring"]),
            created=datetime.fromisoformat(data["created"]),
            modified=datetime.fromisoformat(data["modified"]),
            data=status_information,
            wifi_sessions=None,
        )


@dataclass
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


@dataclass(slots=True)
class ApiRequest:
    """API request parameters."""

    method: str
    path: str
    query: dict[str, str] | None = None
    data: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    auth: bool = True


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
            ApiRequest(
                method="get",
                path="/api/v1/users/organization/",
            )
        )
        return [OpenWispOrganization.from_dict(org) for org in res["results"]]

    async def async_get_devices(
        self, organization: UUID | None = None
    ) -> dict[UUID, OpenWispDevice]:
        """Get all device information from the API."""
        if organization is None:
            res = await self._api_wrapper(
                ApiRequest(
                    method="get",
                    path="/api/v1/monitoring/device/",
                )
            )
        else:
            res = await self._api_wrapper(
                ApiRequest(
                    method="get",
                    path="/api/v1/monitoring/device/",
                    query={"organization": str(organization)},
                )
            )

        devices = {
            UUID(device["id"]): OpenWispDevice.from_dict(device)
            for device in res["results"]
        }

        await asyncio.gather(
            *(self._populate_device_data(device) for device in devices.values())
        )

        return devices

    async def async_get_device_wifi_sessions(
        self, devices: dict[UUID, OpenWispDevice], organization: UUID | None = None
    ) -> list[WifiSession]:
        """Get the open Wi-Fi sessions and count them per device."""
        sessions = await self.async_get_open_wifi_sessions(organization)
        for device in devices.values():
            device.wifi_sessions = DeviceWifiSessions(
                sum(1 for session in sessions if session.device == device.name)
            )
        return sessions

    async def _populate_device_data(self, device: OpenWispDevice) -> OpenWispDevice:
        """Populate the device data with status data."""
        async with _SEMAPHORE:
            detailed = await self.async_get_device(device.id, status=True)
            device.data = detailed.data
            return device

    async def async_get_device(
        self, device_id: UUID, *, status: bool
    ) -> OpenWispDevice:
        """Get device information from the API."""
        query = {}
        if status:
            # Note: no matter the value of status, the API provides the status data.
            query["status"] = "true"

        res = await self._api_wrapper(
            ApiRequest(
                method="get",
                path=f"/api/v1/monitoring/device/{device_id}/",
                query=query,
            )
        )
        return OpenWispDevice.from_dict(res)

    async def _async_authenticate(self) -> None:
        """Authenticate and store a new token."""
        res = await self._request(
            ApiRequest(
                method="post",
                path="/api/v1/users/token/",
                data={
                    "username": self._username,
                    "password": self._password,
                },
                auth=False,
            )
        )

        self._token = res["token"]

    async def async_get_open_wifi_sessions(
        self, organization: UUID | None = None
    ) -> list[WifiSession]:
        """Get all open Wi-Fi sessions, following the pagination."""
        query = {"stop_time__isnull": "true", "page_size": "100"}
        if organization is not None:
            query["device__organization"] = str(organization)

        sessions: list[WifiSession] = []
        page = 1
        while True:
            res = await self._api_wrapper(
                ApiRequest(
                    method="get",
                    path="/api/v1/monitoring/wifi-session/",
                    query={**query, "page": str(page)},
                )
            )
            sessions.extend(WifiSession.from_dict(item) for item in res["results"])
            if not res.get("next"):
                return sessions
            page += 1

    async def ensure_authenticated(self) -> None:
        """Ensure a valid token exists."""
        if self._token is not None:
            return

        async with self._auth_lock:
            if self._token is None:
                await self._async_authenticate()

    async def _request(
        self,
        request: ApiRequest,
    ) -> Any:
        """Perform a single HTTP request."""
        headers = {}
        if request.headers is not None:
            headers.update(request.headers)

        if request.data is not None:
            headers["Content-Type"] = "application/json"

        if request.auth and self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        url = f"{self._host}{request.path}"
        if request.query:
            url += "?" + "&".join(f"{k}={v}" for k, v in request.query.items())

        req_id = uuid4()
        LOGGER.debug(f"[{req_id}] Requesting: {url}")

        async with async_timeout.timeout(10):
            response = await self._session.request(
                method=request.method,
                url=url,
                json=request.data,
                headers=headers,
            )

        LOGGER.debug(f"[{req_id}] Response status: {response.status}")
        if response.status in (401, 403):
            raise OpenWispApiClientAuthenticationError

        response.raise_for_status()
        return await response.json()

    async def _api_wrapper(
        self,
        request: ApiRequest,
    ) -> Any:
        """Perform an authenticated API request with automatic reauthentication."""
        if not request.auth:
            return await self._request(request)

        try:
            await self.ensure_authenticated()
            return await self._request(request)

        except OpenWispApiClientAuthenticationError:
            if not request.auth:
                raise

            # Token expired -> clear and reauthenticate
            self._token = None

            await self.ensure_authenticated()

            # Retry once
            return await self._request(request)

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise OpenWispApiClientCommunicationError(msg) from exception

        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise OpenWispApiClientCommunicationError(msg) from exception

        except Exception as exception:
            msg = f"Unknown error fetching information - {exception}"
            raise OpenWispApiClientError(msg) from exception

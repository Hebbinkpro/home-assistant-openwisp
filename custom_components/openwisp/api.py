"""Sample API Client."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID, uuid4

import aiohttp
import async_timeout
from slugify import slugify

from .const import LOGGER, API_RESULTS_PAGE_SIZE
from .utils import get_and_apply, parse_bool

if TYPE_CHECKING:
    from ipaddress import IPv4Address, IPv6Address
    from typing import Any

_SEMAPHORE = asyncio.Semaphore(10)


class OpenWispApiError(Exception):
    """Exception to indicate a general API error."""


class OpenWispApiClientError(OpenWispApiError):
    """Exception to indicate a general API error caused by the API client."""


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
        return cls(
            status=data.get("status", ""),
            error_reason=data.get("error_reason", ""),
            backend=data.get("backend", ""),
        )


@dataclass
class BaseDeviceMonitoring:
    """Monitoring information of an OpenWISP device."""

    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseDeviceMonitoring:
        """Create DeviceMonitoring from a dict."""
        return cls(
            status=data.get("status", ""),
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusMemoryResources:
        """Create DeviceStatusMemoryResources from a dict."""
        return cls(
            total=data.get("total", 0),
            shared=data.get("shared", 0),
            free=data.get("free", 0),
            cached=data.get("cached", 0),
            available=data.get("available", 0),
            buffered=data.get("buffered", 0),
        )


@dataclass
class DeviceStatusDiskResources:
    """Device status disk resources of an OpenWISP device."""

    filesystem: str
    available_bytes: int
    mount_point: str
    used_percent: int
    size_bytes: int
    used_bytes: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusDiskResources:
        """Create DeviceStatusDiskResources from a dict."""
        return cls(
            filesystem=data.get("filesystem", ""),
            available_bytes=data.get("available_bytes", 0),
            mount_point=data.get("mount_point", ""),
            used_percent=data.get("used_percent", 0),
            size_bytes=data.get("size_bytes", 0),
            used_bytes=data.get("used_bytes", 0),
        )


@dataclass
class DeviceStatusSwapResources:
    """Device status swap resources of an OpenWISP device."""

    free: int
    total: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusSwapResources:
        """Create DeviceStatusSwapResources from a dict."""
        return cls(
            free=data.get("free", 0),
            total=data.get("total", 0),
        )


@dataclass
class DeviceStatusResources:
    """Device status resources of an OpenWISP device."""

    memory: DeviceStatusMemoryResources | None
    cpus: int
    disks: dict[str, DeviceStatusDiskResources]
    load: tuple[float, float, float]
    swap: DeviceStatusSwapResources | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusResources:
        """Create DeviceStatusResources from a dict."""
        disks: dict[str, DeviceStatusDiskResources] = {}

        for disk_data in data.get("disk", []):
            disk_resources = DeviceStatusDiskResources.from_dict(disk_data)
            disks[slugify(disk_resources.filesystem)] = disk_resources

        load = data.get("load", (0, 0, 0))

        return cls(
            memory=get_and_apply(data, "memory", DeviceStatusMemoryResources.from_dict),
            cpus=data.get("cpus", 0),
            disks=disks,
            load=(load[0], load[1], load[2]),
            swap=get_and_apply(data, "swap", DeviceStatusSwapResources.from_dict),
        )


@dataclass
class GeneralDeviceStatusInformation:
    """General device status information of an OpenWISP device."""

    local_time: datetime | None
    uptime: timedelta | None
    hostname: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneralDeviceStatusInformation:
        """Create GeneralDeviceStatusInformation from a dict."""
        return cls(
            local_time=get_and_apply(data, "local_time", datetime.fromtimestamp),
            uptime=get_and_apply(data, "uptime", lambda x: timedelta(seconds=x)),
            hostname=data.get("hostname", ""),
        )


@dataclass
class DeviceWirelessClient:
    """Client associated with a wireless interface."""

    mac_address: str
    signal: int | None
    noise: int | None
    throughput: int | None
    vendor: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceWirelessClient:
        if data.get("mac") is None:
            msg = "Wireless client does not have a MAC-address"
            raise OpenWispApiError(msg)

        return cls(
            mac_address=data["mac"].upper(),
            signal=data.get("signal"),
            noise=data.get("noise"),
            throughput=data.get("throughput"),
            vendor=data.get("vendor"),
        )

@dataclass
class DeviceWirelessInterface:
    ssid: str
    noise: int | None
    country: str  | None
    clients: dict[str, DeviceWirelessClient]
    signal: int | None
    bitrate: float| None
    quality_max: int | None
    quality: int | None
    channel: int | None
    tx_power: int | None
    mode: str | None
    htmode: str | None
    frequency: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceWirelessInterface:

        if data.get("ssid") is None:
            msg = "Wireless interface does not have a SSID"
            raise OpenWispApiError(msg)

        clients = {}
        for client_data in data.get("clients", []):
            client = DeviceWirelessClient.from_dict(client_data)
            clients[client.mac_address] = client

        return cls(
            ssid=data["ssid"],
            noise=data.get("noise"),
            country=data.get("country"),
            clients=clients,
            signal=data.get("signal"),
            bitrate=data.get("bitrate"),
            quality_max=data.get("quality_max"),
            quality=data.get("quality"),
            channel=data.get("channel"),
            tx_power=data.get("tx_power"),
            mode=data.get("mode"),
            htmode=data.get("htmode"),
            frequency=data.get("frequency"),
        )

@dataclass
class DeviceInterface:
    """Wireless interface of an OpenWISP device."""

    name: str
    mac: str | None
    type: str
    mtu: int
    txqueuelen: int
    wireless: DeviceWirelessInterface | None
    multicast: bool
    up: bool


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceInterface:
        """Create DeviceWirelessInterface from an interface dict."""

        if data.get("name") is None:
            msg = f"Device interface does not have a name."
            raise OpenWispApiError(msg)

        return cls(
            name=data["name"],
            mac=get_and_apply(data, "mac", str.upper),
            type=data.get("type", ""),
            mtu=data.get("mtu", 0),
            txqueuelen=data.get("txqueuelen", 0),
            wireless=get_and_apply(data, "wireless", DeviceWirelessInterface.from_dict),
            multicast=data.get("multicast", False),
            up=data.get("up", False),
        )


@dataclass
class DeviceStatusInformation:
    """Device status information of an OpenWISP device."""

    type: str
    general: GeneralDeviceStatusInformation | None
    resources: DeviceStatusResources | None
    interfaces: dict[str, DeviceInterface]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceStatusInformation:
        """Create DeviceStatusInformation from a dict."""
        information_type = data.get("type", "")
        if information_type != "DeviceMonitoring":
            msg = f"Invalid device status information type: {data['type']}"
            raise OpenWispApiError(msg)

        interfaces = {}
        for interface_data in data.get("interfaces", []):
            interface = DeviceInterface.from_dict(interface_data)
            interfaces[interface.name] = interface

        return cls(
            type=information_type,
            general=get_and_apply(
                data, "general", GeneralDeviceStatusInformation.from_dict
            ),
            resources=get_and_apply(data, "resources", DeviceStatusResources.from_dict),
            interfaces=interfaces,
        )

@dataclass
class WifiSessionClient:
    """Client associated with a wifi session."""
    mac_address: str | None
    vendor: str
    wifi6: bool | None
    wifi5: bool | None
    wifi4: bool | None
    wmm: bool | None
    wds: bool | None
    wps: bool | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WifiSessionClient:
        return cls(
            mac_address=get_and_apply(data, "mac_address", str.upper),
            vendor=data.get("vendor", ""),
            # Note: The API is capable of returning null, "True", "False", true, and false...
            wifi6=parse_bool(data.get("wifi6")),
            wifi5=parse_bool(data.get("wifi5")),
            wifi4=parse_bool(data.get("wifi4")),
            wmm=parse_bool(data.get("wmm")),
            wds=parse_bool(data.get("wds")),
            wps=parse_bool(data.get("wps")),
        )


@dataclass
class WifiSession:
    """Open Wi-Fi session of a client on an OpenWISP device."""

    id: UUID
    organization: str | None
    device: str | None
    ssid: str
    interface_name: str
    client: WifiSessionClient | None
    start_time: datetime | None
    stop_time: datetime | None
    modified: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WifiSession:
        """Create a WifiSession from a dict."""
        if data.get("id") is None:
            msg = "Missing device ID while parsing OpenWispDevice"
            raise OpenWispApiError(msg)

        return cls(
            id=UUID(data["id"]),
            organization=data.get("organization"),
            device=data.get("device"),
            ssid=data.get("ssid", ""),
            interface_name=data.get("interface_name", ""),
            client=get_and_apply(data, "client", WifiSessionClient.from_dict),
            start_time=get_and_apply(data, "start_time", datetime.fromisoformat),
            stop_time=get_and_apply(data, "stop_time", datetime.fromisoformat),
            modified=get_and_apply(data, "modified", datetime.fromisoformat),
        )

@dataclass
class DeviceWifiSessions:
    """Device Wi-Fi session information of an OpenWISP device."""

    active_sessions: dict[UUID, WifiSession]


@dataclass(slots=True)
class OpenWispDevice:
    """OpenWISP device."""

    id: UUID
    name: str
    organization: UUID | None
    group: UUID | None
    mac_address: str
    last_ip: IPv4Address | IPv6Address | None
    management_ip: IPv4Address | IPv6Address | None
    model: str
    os: str
    system: str
    notes: str
    config: DeviceListConfig | None
    monitoring: BaseDeviceMonitoring | None
    created: datetime | None
    modified: datetime | None
    data: DeviceStatusInformation | None
    wifi_sessions: DeviceWifiSessions | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenWispDevice:
        """Create a Device from a dict."""
        if data.get("id") is None:
            msg = "Missing device ID while parsing OpenWispDevice"
            raise OpenWispApiError(msg)

        return cls(
            id=UUID(data["id"]),
            name=data.get("name", ""),
            organization=get_and_apply(data, "organization", UUID),
            group=get_and_apply(data, "group", UUID),
            mac_address=data.get("mac_address", "").upper(),
            last_ip=get_and_apply(data, "last_ip", ipaddress.ip_address),
            management_ip=get_and_apply(data, "management_ip", ipaddress.ip_address),
            model=data.get("model", ""),
            os=data.get("os", ""),
            system=data.get("system", ""),
            notes=data.get("notes", ""),
            config=get_and_apply(data, "config", DeviceListConfig.from_dict),
            monitoring=get_and_apply(
                data, "monitoring", BaseDeviceMonitoring.from_dict
            ),
            created=get_and_apply(data, "created", datetime.fromisoformat),
            modified=get_and_apply(data, "modified", datetime.fromisoformat),
            data=get_and_apply(data, "data", DeviceStatusInformation.from_dict),
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
    created: datetime | None
    modified: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenWispOrganization:
        """Create an Organization from a dict."""
        if data.get("id") is None:
            msg = "Missing organization ID while parsing OpenWispOrganization"
            raise OpenWispApiError(msg)

        return cls(
            id=UUID(data["id"]),
            name=data.get("name", ""),
            is_active=data.get("is_active", False),
            slug=data.get("slug", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            created=get_and_apply(data, "created", datetime.fromisoformat),
            modified=get_and_apply(data, "modified", datetime.fromisoformat),
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

        organizations: list[OpenWispOrganization] = []

        for org in res.get("results", []):
            try:
                organizations.append(OpenWispOrganization.from_dict(org))
            except OpenWispApiError as e:
                LOGGER.error(f"Error creating OpenWisp organization: {e}")

        return organizations

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

        devices: dict[UUID, OpenWispDevice] = {}

        for device_data in res.get("results", []):
            # attempt to create OpenWispDevice from device data, but log any errors
            try:
                device = OpenWispDevice.from_dict(device_data)
                devices[device.id] = device
            except OpenWispApiError as e:
                LOGGER.error("Error creating OpenWispDevice from data: %s", e)
                continue

        await asyncio.gather(
            *(self._populate_device_data(device) for device in devices.values())
        )

        return devices

    async def async_populate_device_wifi_sessions(
        self, devices: dict[UUID, OpenWispDevice]
    ) -> list[WifiSession]:
        """Get the open Wi-Fi sessions and count them per device."""
        sessions = []
        for device in devices.values():
            device_sessions = await self._async_get_device_wifi_sessions(device)
            device.wifi_sessions = DeviceWifiSessions(device_sessions)
            sessions.extend(device_sessions.values())

        return sessions


    async def _populate_device_data(self, device: OpenWispDevice) -> OpenWispDevice:
        """Populate the device data with status data."""
        async with _SEMAPHORE:
            # attempt to populate device data, but log any errors
            try:
                detailed = await self.async_get_device(device.id, status=True)
                if detailed is None:
                    return device

                device.data = detailed.data
            except OpenWispApiError as e:
                LOGGER.error(
                    f"Error populating data of device with UUID {device.id}: %s", e
                )

            return device

    async def async_get_device(
        self, device_id: UUID, *, status: bool
    ) -> OpenWispDevice | None:
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

        try:
            return OpenWispDevice.from_dict(res)
        except OpenWispApiError as e:
            LOGGER.error(f"Error creating OpenWisp device: {e}")
            return None

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

    async def _async_get_device_wifi_sessions(
        self, device: OpenWispDevice
    ) -> dict[UUID, WifiSession]:
        """Get all open Wi-Fi sessions from a given device, following the pagination."""
        query = {
            "device": str(device.id),
            "stop_time__isnull": "true",
            "page_size": str(API_RESULTS_PAGE_SIZE)
        }

        sessions: dict[UUID, WifiSession] = {}
        page = 1
        next_page = True
        while next_page:
            res = await self._api_wrapper(
                ApiRequest(
                    method="get",
                    path="/api/v1/monitoring/wifi-session/",
                    query={**query, "page": str(page)},
                )
            )

            for item in res.get("results", []):
                try:
                    session = WifiSession.from_dict(item)
                    sessions[session.id] = session
                except OpenWispApiError as e:
                    LOGGER.warning("Ignoring malformed Wi-Fi session %s: %s", item, e)

            next_page = res.get("next") is not None
            page += 1

        return sessions

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

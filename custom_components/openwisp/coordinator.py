"""DataUpdateCoordinator for openwisp."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OpenWispApiClient,
    OpenWispApiClientAuthenticationError,
    OpenWispApiClientCommunicationError,
    OpenWispDevice,
    WifiSession,
)
from .const import CONSIDER_HOME, DOMAIN, LOGGER, UPDATE_INTERVAL

if TYPE_CHECKING:
    from uuid import UUID

    from homeassistant.core import HomeAssistant


@dataclass
class WifiClient:
    """Wi-Fi client seen in the open sessions of the organization."""

    mac_address: str
    last_seen: datetime
    session: WifiSession | None
    signal: int | None = None
    connected: bool = field(default=True)


class OpenWispDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for OpenWISP."""

    client: OpenWispApiClient
    organization: UUID | None
    wifi_clients: dict[str, WifiClient]

    def __init__(
        self,
        hass: HomeAssistant,
        client: OpenWispApiClient,
        organization: UUID | None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

        self.client = client
        self.organization = organization
        self.wifi_clients: dict[str, WifiClient] = {}

    async def _async_update_data(self) -> dict[UUID, OpenWispDevice]:
        """Fetch data from OpenWISP."""
        try:
            devices = await self.client.async_get_devices(self.organization)
            await self.client.async_populate_device_wifi_sessions(devices)
        except OpenWispApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed from exception
        except OpenWispApiClientCommunicationError as exception:
            raise UpdateFailed(str(exception)) from exception
        else:
            self._update_wifi_clients(devices)
            return devices

    def _update_wifi_clients(
        self, devices: dict[UUID, OpenWispDevice]
    ) -> None:
        """
        Track the Wi-Fi clients of the open sessions.

        A client that roams closes its session on one device and opens one on
        the next, possibly one report apart, so a client only counts as gone
        once it has been missing for CONSIDER_HOME.
        """
        now = datetime.now(UTC)

        currently_connected = set()
        for device in devices.values():
            if device.data is None:
                continue

            for interface in device.data.interfaces.values():
                if interface.wireless is None:
                    continue

                for mac,client in interface.wireless.clients.items():
                    self.wifi_clients[mac] = WifiClient(
                        mac_address=mac,
                        last_seen=now,
                        session=client.session,
                        signal=client.signal
                    )
                    currently_connected.add(mac)

        not_connected = set(self.wifi_clients.keys()) - currently_connected
        for mac in not_connected:
            client = self.wifi_clients[mac]
            client.connected = now - client.last_seen < CONSIDER_HOME


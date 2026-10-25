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
    session: WifiSession
    signal: int | None = None
    connected: bool = field(default=True)


class OpenWispDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for OpenWISP."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OpenWispApiClient,
        organization: UUID,
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

    async def _async_update_data(self) -> dict[UUID, object]:
        """Fetch data from OpenWISP."""
        try:
            devices = await self.client.async_get_devices(self.organization)
            sessions = await self.client.async_get_device_wifi_sessions(
                devices, self.organization
            )
        except OpenWispApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed from exception
        except OpenWispApiClientCommunicationError as exception:
            raise UpdateFailed(str(exception)) from exception
        else:
            self._update_wifi_clients(devices, sessions)
            return devices

    def _update_wifi_clients(
        self, devices: dict[UUID, OpenWispDevice], sessions: list[WifiSession]
    ) -> None:
        """
        Track the Wi-Fi clients of the open sessions.

        A client that roams closes its session on one device and opens one on
        the next, possibly one report apart, so a client only counts as gone
        once it has been missing for CONSIDER_HOME.
        """
        now = datetime.now(UTC)
        signals = {
            client.mac_address: client.signal
            for device in devices.values()
            if device.data is not None
            for interface in device.data.wireless.values()
            for client in interface.clients
        }
        # the latest session wins when a roam left two open
        for session in sorted(sessions, key=lambda s: s.start_time):
            self.wifi_clients[session.mac_address] = WifiClient(
                mac_address=session.mac_address,
                last_seen=now,
                session=session,
                signal=signals.get(session.mac_address),
            )
        for client in self.wifi_clients.values():
            client.connected = now - client.last_seen < CONSIDER_HOME

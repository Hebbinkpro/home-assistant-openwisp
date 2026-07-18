"""DataUpdateCoordinator for openwisp."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OpenWispApiClient,
    OpenWispApiClientAuthenticationError,
    OpenWispApiClientCommunicationError,
)
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from uuid import UUID

    from homeassistant.core import HomeAssistant


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
            update_interval=timedelta(minutes=5),
        )

        self.client = client
        self.organization = organization

    async def _async_update_data(self) -> dict[UUID, object]:
        """Fetch data from OpenWISP."""
        try:
            devices = await self.client.async_get_devices(self.organization)
        except OpenWispApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed from exception
        except OpenWispApiClientCommunicationError as exception:
            raise UpdateFailed(str(exception)) from exception
        else:
            return devices

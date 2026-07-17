"""DataUpdateCoordinator for openwisp."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OpenWispApiClientAuthenticationError,
    OpenWispApiClientError, Device,
)

if TYPE_CHECKING:
    from .data import OpenWispConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class OpenWispDataUpdateCoordinator(DataUpdateCoordinator[list[Device]]):
    """Class to manage fetching data from the API."""

    config_entry: OpenWispConfigEntry

    async def _async_setup(self) -> None:
        """Set up the OpenWisp integration."""
        await self.config_entry.runtime_data.client.async_authenticate()

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            return await self.config_entry.runtime_data.client.async_get_devices()
        except OpenWispApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OpenWispApiClientError as exception:
            raise UpdateFailed(exception) from exception

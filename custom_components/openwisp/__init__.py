"""
Custom integration to integrate openwisp with Home Assistant.

For more details about this integration, please refer to
https://github.com/hebbinkpro/home-assistant-openwisp
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenWispApiClient
from .const import DOMAIN, LOGGER
from .coordinator import OpenWispDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import OpenWispConfigEntry

PLATFORMS: list[Platform] = [
    # Platform.SENSOR,
    # Platform.BINARY_SENSOR,
    # Platform.SWITCH,
]


async def create_openwisp_client(
    hass: HomeAssistant, data: dict[str, Any]
) -> OpenWispApiClient:
    """Create an OpenWISP API client for the given config entry."""
    host: str = data[CONF_HOST]
    verify_ssl = bool(data[CONF_VERIFY_SSL])
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    return OpenWispApiClient(
        host=host,
        username=username,
        password=password,
        session=session,
    )


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenWispConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = OpenWispDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(hours=1),
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: OpenWispConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: OpenWispConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

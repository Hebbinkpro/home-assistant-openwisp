"""OpenWISP device tracker platform: Wi-Fi clients of the open sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity import OpenWispEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OpenWispDataUpdateCoordinator, WifiClient
    from .data import OpenWispConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenWispConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a tracker for every Wi-Fi client, now and as new ones appear."""
    coordinator = entry.runtime_data.coordinator
    tracked: set[str] = set()

    # clients tracked before keep their entity while they are away
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain == "device_tracker" and entity.unique_id.startswith(
            f"{DOMAIN}_wifi_"
        ):
            tracked.add(entity.unique_id.removeprefix(f"{DOMAIN}_wifi_"))

    @callback
    def add_new_clients() -> None:
        new = [mac for mac in coordinator.wifi_clients if mac not in tracked]
        tracked.update(new)
        async_add_entities(OpenWispWifiClientTracker(coordinator, mac) for mac in new)

    async_add_entities(
        OpenWispWifiClientTracker(coordinator, mac)
        for mac in tracked
        if mac not in coordinator.wifi_clients
    )
    add_new_clients()
    entry.async_on_unload(coordinator.async_add_listener(add_new_clients))


class OpenWispWifiClientTracker(OpenWispEntity, ScannerEntity):
    """Wi-Fi client connected to any device of the organization."""

    def __init__(self, coordinator: OpenWispDataUpdateCoordinator, mac: str) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{DOMAIN}_wifi_{mac}"
        self._attr_name = f"Wi-Fi {mac}"

    @property
    def _client(self) -> WifiClient | None:
        return self.coordinator.wifi_clients.get(self._mac)

    @property
    def mac_address(self) -> str:
        """Return the MAC address of the client."""
        return self._mac

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the tracker."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return whether the client is connected."""
        return self._client is not None and self._client.connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return where the client was last seen."""
        if self._client is None:
            return {}
        session = self._client.session
        return {
            "device": session.device,
            "ssid": session.ssid,
            "interface": session.interface_name,
            "signal": self._client.signal,
            "vendor": session.vendor,
            "connected_since": session.start_time.isoformat(),
            "last_seen": self._client.last_seen.isoformat(),
        }

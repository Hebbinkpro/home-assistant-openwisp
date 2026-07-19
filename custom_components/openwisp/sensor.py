"""OpenWISP sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity import OpenWispDeviceEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import OpenWispDevice
    from .data import OpenWispConfigEntry, OpenWispDataUpdateCoordinator


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: OpenWispConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform entities."""
    coordinator = entry.runtime_data.coordinator

    entities = []

    for device in coordinator.data.values():
        entities.extend(
            [
                OpenWispDeviceConfigStatusSensor(
                    coordinator,
                    device,
                ),
                OpenWispDeviceMonitoringStatusSensor(
                    coordinator,
                    device,
                ),
            ]
        )

    async_add_entities(entities)


class OpenWispDeviceConfigStatusSensor(OpenWispDeviceEntity, SensorEntity):
    """Configuration status."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator, device)

        self._attr_unique_id = f"{DOMAIN}_{device.id}_configuration_status"
        self._attr_name = "Configuration status"

    @property
    def native_value(self) -> str:
        """Get the device configuration status."""
        return self.device.config.status
    
    @property
    def options(self) -> list[str]:
        """Get the config value options."""
        return [
            "modified",
            "applied",
            "error",
            "deactivating",
            "deactivated",
        ]


class OpenWispDeviceMonitoringStatusSensor(OpenWispDeviceEntity, SensorEntity):
    """Monitoring status."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator, device)

        self._attr_unique_id = f"{DOMAIN}_{device.id}_monitoring_status"
        self._attr_name = "Monitoring status"

    @property
    def native_value(self) -> str:
        """Get the device monitoring status."""
        return self.device.monitoring.status

    @property
    def options(self) -> list[str]:
        """Get the monitoring value options."""
        return [
            "unknown",
            "ok",
            "problem",
            "critical",
            "deactivated",
        ]
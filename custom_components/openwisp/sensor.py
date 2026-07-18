"""OpenWISP sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .entity import OpenWispDeviceEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import OpenWispConfigEntry


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

    _attr_name = "Configuration status"

    @property
    def native_value(self) -> str:
        """Get the device configuration status."""
        return self.device.config.status


class OpenWispDeviceMonitoringStatusSensor(OpenWispDeviceEntity, SensorEntity):
    """Monitoring status."""

    _attr_name = "Monitoring status"

    @property
    def native_value(self) -> str:
        """Get the device monitoring status."""
        return self.device.monitoring.status

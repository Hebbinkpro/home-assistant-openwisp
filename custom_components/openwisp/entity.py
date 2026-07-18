"""OpenWispEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenWispDataUpdateCoordinator

if TYPE_CHECKING:
    from .api import OpenWispDevice


class OpenWispEntity(CoordinatorEntity[OpenWispDataUpdateCoordinator]):
    """OpenWispEntity class."""

    def __init__(self, coordinator: OpenWispDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)


class OpenWispDeviceEntity(
    OpenWispEntity,
):
    """Base OpenWISP device entity."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator)

        self._device_id = device.id

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device.id))},
            connections={
                (
                    CONNECTION_NETWORK_MAC,
                    device.mac_address,
                )
            },
            name=device.name,
            manufacturer="OpenWISP",
            model=device.model,
            sw_version=device.os,
            hw_version=device.system,
        )

    @property
    def device(self) -> OpenWispDevice:
        """Return the device."""
        return self.coordinator.data[self._device_id]

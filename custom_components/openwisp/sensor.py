"""OpenWISP sensor platform."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from datetime import datetime, UTC
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfInformation,
    UnitOfRatio,
)
from slugify import slugify

from .entity import OpenWispDeviceEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import DeviceStatusDiskResources, OpenWispDevice
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
                OpenWispDeviceConfigStatusSensor(coordinator, device),
                OpenWispDeviceMonitoringStatusSensor(coordinator, device),
            ]
        )

        if device.data is not None:
            entities.extend(
                [
                    OpenWispDeviceStatusUptimeSensor(coordinator, device, enabled=True),
                    OpenWispDeviceStatusLocalTimeSensor(coordinator, device),
                    OpenWispDeviceStatusHostnameSensor(
                        coordinator, device, enabled=True
                    ),
                    OpenWispDeviceStatusCpuCountSensor(coordinator, device),
                    OpenWispDeviceStatusLoad1Sensor(coordinator, device, enabled=True),
                    OpenWispDeviceStatusLoad5Sensor(coordinator, device),
                    OpenWispDeviceStatusLoad15Sensor(coordinator, device),
                    OpenWispDeviceStatusMemoryAvailableSensor(
                        coordinator, device, enabled=True
                    ),
                    OpenWispDeviceStatusMemoryTotalSensor(
                        coordinator, device, enabled=True
                    ),
                    OpenWispDeviceStatusMemoryFreeSensor(coordinator, device),
                    OpenWispDeviceStatusMemoryBufferedSensor(coordinator, device),
                    OpenWispDeviceStatusMemorySharedSensor(coordinator, device),
                    OpenWispDeviceStatusSwapFreeSensor(
                        coordinator, device, enabled=True
                    ),
                    OpenWispDeviceStatusSwapTotalSensor(
                        coordinator, device, enabled=True
                    ),
                ]
            )

            for disk in device.data.resources.disks.values():
                entities.extend(
                    [
                        OpenWispDeviceStatusDiskAvailableBytesSensor(
                            coordinator, device, disk
                        ),
                        OpenWispDeviceStatusDiskMountPointSensor(
                            coordinator, device, disk
                        ),
                        OpenWispDeviceStatusDiskUsedPercentSensor(
                            coordinator, device, disk, enabled=True
                        ),
                        OpenWispDeviceStatusDiskSizeBytesSensor(
                            coordinator, device, disk
                        ),
                        OpenWispDeviceStatusDiskUsedBytesSensor(
                            coordinator, device, disk
                        ),
                    ]
                )

        if device.wifi_sessions is not None:
            entities.extend(
                [
                    OpenWispDeviceActiveWifiSessionsSensor(coordinator, device),
                ]
            )

    async_add_entities(entities)


class OpenWispDeviceConfigStatusSensor(OpenWispDeviceEntity, SensorEntity):
    """Configuration status."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator, device)

        self._attr_unique_id = f"{self._base_unique_id}_configuration_status"
        self._attr_name = "Configuration status"

    @property
    def native_value(self) -> str | None:
        """Get the device configuration status."""
        if self.device.config is None:
            return None

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

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator, device)

        self._attr_unique_id = f"{self._base_unique_id}_monitoring_status"
        self._attr_name = "Monitoring status"

    @property
    def native_value(self) -> str | None:
        """Get the device monitoring status."""
        if self.device.monitoring is None:
            return None

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


class OpenWispDeviceActiveWifiSessionsSensor(OpenWispDeviceEntity, SensorEntity):
    """WiFi clients."""

    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
    ) -> None:
        """Initialize the device entity."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._base_unique_id}_active_wifi_sessions"
        self._attr_name = "Active WiFi sessions"

    @property
    def available(self) -> bool:
        """Only available when Wi-Fi sessions have been fetched."""
        return super().available and self.device.wifi_sessions is not None

    @property
    def native_value(self) -> int | None:
        """Get the number of active Wi-Fi sessions."""
        if self.device.wifi_sessions is None:
            return None

        return self.device.wifi_sessions.active_sessions


class OpenWispDeviceStatusInformationSensor(OpenWispDeviceEntity, SensorEntity):
    """Base class for device status information sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_entity_registry_enabled_default = enabled

    @property
    def available(self) -> bool:
        """Only available when detailed status data has been fetched."""
        return super().available and self.device.data is not None


class OpenWispDeviceStatusUptimeSensor(OpenWispDeviceStatusInformationSensor):
    """Device uptime."""

    _attr_device_class = SensorDeviceClass.UPTIME

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_uptime"
        self._attr_name = "Uptime"

    @property
    def native_value(self) -> datetime | None:
        """Return the device uptime."""
        if self.device.data is None:
            return None
        if self.device.data.general is None:
            return None

        return datetime.now(UTC) - self.device.data.general.uptime


class OpenWispDeviceStatusLocalTimeSensor(OpenWispDeviceStatusInformationSensor):
    """Device local time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_local_time"
        self._attr_name = "Local time"

    @property
    def native_value(self) -> datetime | None:
        """Return the device local time."""
        if self.device.data is None:
            return None
        if self.device.data.general is None:
            return None

        # ensure that the timezone is set
        tz = self.coordinator.hass.config.time_zone
        local_time = self.device.data.general.local_time
        local_time = local_time.astimezone(ZoneInfo(tz))

        return local_time


class OpenWispDeviceStatusHostnameSensor(OpenWispDeviceStatusInformationSensor):
    """Device hostname."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_hostname"
        self._attr_name = "Hostname"

    @property
    def native_value(self) -> str | None:
        """Return the device hostname."""
        if self.device.data is None:
            return None
        if self.device.data.general is None:
            return None

        return self.device.data.general.hostname


class OpenWispDeviceStatusCpuCountSensor(OpenWispDeviceStatusInformationSensor):
    """Device CPU count."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_cpus"
        self._attr_name = "CPU count"

    @property
    def native_value(self) -> int | None:
        """Return the number of CPUs."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.cpus


class OpenWispDeviceStatusLoad1Sensor(OpenWispDeviceStatusInformationSensor):
    """Device 1 minute load average."""

    _attr_suggested_display_precision = 2
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_load_1"
        self._attr_name = "Load (1 min)"

    @property
    def native_value(self) -> float | None:
        """Return the 1 minute load average."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.load[0]


class OpenWispDeviceStatusLoad5Sensor(OpenWispDeviceStatusInformationSensor):
    """Device 5 minute load average."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_load_5"
        self._attr_name = "Load (5 min)"

    @property
    def native_value(self) -> float | None:
        """Return the 5 minute load average."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.load[1]


class OpenWispDeviceStatusLoad15Sensor(OpenWispDeviceStatusInformationSensor):
    """Device 15 minute load average."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_load_15"
        self._attr_name = "Load (15 min)"

    @property
    def native_value(self) -> float | None:
        """Return the 15 minute load average."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.load[2]


class OpenWispDeviceStatusMemoryAvailableSensor(OpenWispDeviceStatusInformationSensor):
    """Available memory."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_memory_available"
        self._attr_name = "Memory available"

    @property
    def native_value(self) -> int | None:
        """Return available memory."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.memory is None:
            return None

        return self.device.data.resources.memory.available


class OpenWispDeviceStatusMemoryTotalSensor(OpenWispDeviceStatusInformationSensor):
    """Total memory."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_memory_total"
        self._attr_name = "Memory total"

    @property
    def native_value(self) -> int | None:
        """Return total memory."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.memory is None:
            return None

        return self.device.data.resources.memory.total


class OpenWispDeviceStatusMemoryFreeSensor(OpenWispDeviceStatusInformationSensor):
    """Free memory."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_memory_free"
        self._attr_name = "Memory free"

    @property
    def native_value(self) -> int | None:
        """Return free memory."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.memory is None:
            return None

        return self.device.data.resources.memory.free


class OpenWispDeviceStatusMemoryBufferedSensor(OpenWispDeviceStatusInformationSensor):
    """Buffered memory."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_memory_buffered"
        self._attr_name = "Memory buffered"

    @property
    def native_value(self) -> int | None:
        """Return buffered memory."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.memory is None:
            return None

        return self.device.data.resources.memory.buffered


class OpenWispDeviceStatusMemorySharedSensor(OpenWispDeviceStatusInformationSensor):
    """Shared memory."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_memory_shared"
        self._attr_name = "Memory shared"

    @property
    def native_value(self) -> int | None:
        """Return shared memory."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.memory is None:
            return None

        return self.device.data.resources.memory.shared


class OpenWispDeviceStatusSwapFreeSensor(OpenWispDeviceStatusInformationSensor):
    """Free swap."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_swap_free"
        self._attr_name = "Swap free"

    @property
    def native_value(self) -> int | None:
        """Return free swap."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.swap is None:
            return None

        return self.device.data.resources.swap.free


class OpenWispDeviceStatusSwapTotalSensor(OpenWispDeviceStatusInformationSensor):
    """Total swap."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_swap_total"
        self._attr_name = "Swap total"

    @property
    def native_value(self) -> int | None:
        """Return total swap."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None
        if self.device.data.resources.swap is None:
            return None

        return self.device.data.resources.swap.total


class OpenWispDeviceStatusDiskSensor(OpenWispDeviceStatusInformationSensor):
    """Base disk sensor."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        disk: DeviceStatusDiskResources,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, enabled=enabled)
        self._disk_id = slugify(disk.filesystem)
        self._base_unique_id = f"{self._base_unique_id}_{self._disk_id}"


class OpenWispDeviceStatusDiskAvailableBytesSensor(OpenWispDeviceStatusDiskSensor):
    """Disk available bytes sensor."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        disk: DeviceStatusDiskResources,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, disk, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_available_bytes"
        self._attr_name = f"{disk.filesystem}: Available bytes"

    @property
    def native_value(self) -> int | None:
        """Return available bytes."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.disks[self._disk_id].available_bytes


class OpenWispDeviceStatusDiskMountPointSensor(OpenWispDeviceStatusDiskSensor):
    """Disk mount point sensor."""

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        disk: DeviceStatusDiskResources,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, disk, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_mount_point"
        self._attr_name = f"{disk.filesystem}: Mount point"

    @property
    def native_value(self) -> str | None:
        """Return mount point."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.disks[self._disk_id].mount_point


class OpenWispDeviceStatusDiskUsedPercentSensor(OpenWispDeviceStatusDiskSensor):
    """Disk used percent sensor."""

    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        disk: DeviceStatusDiskResources,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, disk, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_used_percent"
        self._attr_name = f"{disk.filesystem}: Used percent"

    @property
    def native_value(self) -> int | None:
        """Return used percent."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.disks[self._disk_id].used_percent


class OpenWispDeviceStatusDiskSizeBytesSensor(OpenWispDeviceStatusDiskSensor):
    """Disk size bytes sensor."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        disk: DeviceStatusDiskResources,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, disk, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_size_bytes"
        self._attr_name = f"{disk.filesystem}: Size bytes"

    @property
    def native_value(self) -> int | None:
        """Return size bytes."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.disks[self._disk_id].size_bytes


class OpenWispDeviceStatusDiskUsedBytesSensor(OpenWispDeviceStatusDiskSensor):
    """Disk used bytes sensor."""

    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
    _attr_suggested_display_precision = 2
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: OpenWispDataUpdateCoordinator,
        device: OpenWispDevice,
        disk: DeviceStatusDiskResources,
        *,
        enabled: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device, disk, enabled=enabled)
        self._attr_unique_id = f"{self._base_unique_id}_used_bytes"
        self._attr_name = f"{disk.filesystem}: Used bytes"

    @property
    def native_value(self) -> int | None:
        """Return used bytes."""
        if self.device.data is None:
            return None
        if self.device.data.resources is None:
            return None

        return self.device.data.resources.disks[self._disk_id].used_bytes

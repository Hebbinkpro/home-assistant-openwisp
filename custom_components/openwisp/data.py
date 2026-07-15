"""Custom types for openwisp."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import OpenWispApiClient
    from .coordinator import OpenWispDataUpdateCoordinator


type OpenWispConfigEntry = ConfigEntry[OpenWispData]


@dataclass
class OpenWispData:
    """Data for the OpenWisp integration."""

    client: OpenWispApiClient
    coordinator: OpenWispDataUpdateCoordinator
    integration: Integration

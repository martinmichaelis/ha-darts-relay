"""Darts Relay: Spielstand, Checkout-Wege und Ereignisse aus dem Darts-Relais in Home Assistant."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import DartsRelayCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]

type DartsRelayConfigEntry = ConfigEntry[DartsRelayCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry) -> bool:
    coordinator = DartsRelayCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(hass, coordinator.async_listen(), "darts_relay_listen")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

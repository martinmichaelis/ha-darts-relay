"""Binaersensoren: laeuft ein Spiel, sind die Geraete erreichbar."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DartsRelayConfigEntry
from .entity import DartsRelayEntity

DEVICES = ("hub", "board_manager", "board", "pixelit", "wled")


async def async_setup_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([PlayingSensor(coordinator, "playing"), *(DeviceSensor(coordinator, key) for key in DEVICES)])


class PlayingSensor(DartsRelayEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("playing"))


class DeviceSensor(DartsRelayEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("devices", {}).get(self._key))

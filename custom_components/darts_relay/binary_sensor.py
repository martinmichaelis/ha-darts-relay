"""Binaersensoren: laeuft ein Spiel, sind die Geraete erreichbar."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DartsRelayConfigEntry
from .entity import DartsRelayEntity

DEVICES = ("hub", "board_manager", "board", "pixelit", "wled")


async def async_setup_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([PlayingSensor(coordinator, "playing"), RelayOnlineSensor(coordinator, "relay_online"),
                        *(DeviceSensor(coordinator, key) for key in DEVICES)])


class PlayingSensor(DartsRelayEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("playing"))


class RelayOnlineSensor(DartsRelayEntity, BinarySensorEntity):
    """Laeuft das Relais (Darts-PC an)? Ist es aus, zeigen die anderen Werte den letzten Stand (Attribut "stand")."""
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        return self.coordinator.online

    @property
    def extra_state_attributes(self) -> dict:
        t = self.coordinator.saved_at
        return {"stand": dt_util.utc_from_timestamp(t).isoformat() if t else None}


class DeviceSensor(DartsRelayEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("devices", {}).get(self._key))

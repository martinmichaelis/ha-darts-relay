"""Ereignis-Entitaet: 180, Bust, Leg gewonnen und so weiter, direkt nutzbar als Automations-Ausloeser."""
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DartsRelayConfigEntry
from .const import EVENT_TYPES, SIGNAL_EVENT
from .entity import DartsRelayEntity


async def async_setup_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([DartsEvent(entry.runtime_data, "game_event")])


class DartsEvent(DartsRelayEntity, EventEntity):
    _attr_event_types = EVENT_TYPES

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_EVENT.format(self.coordinator.config_entry.entry_id), self._handle_event))

    @callback
    def _handle_event(self, event: dict[str, Any]) -> None:
        if event["type"] in self.event_types:
            self._trigger_event(event["type"], {k: v for k, v in event.items() if k not in ("type", "seq")})
            self.async_write_ha_state()

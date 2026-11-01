"""Sensoren: Spiel, Checkout-Weg, Statistik, Spielzeit."""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DartsRelayConfigEntry
from .entity import DartsRelayEntity


def _checkout(key: str) -> Callable[[dict], Any]:
    return lambda d: (d.get("checkout") or {}).get(key)


def _stat(key: str) -> Callable[[dict], Any]:
    return lambda d: d["stats"].get(key)


@dataclass(frozen=True, kw_only=True)
class DartsSensorDescription(SensorEntityDescription):
    value: Callable[[dict], Any]
    attributes: Callable[[dict], dict[str, Any]] | None = None


SENSORS = (
    DartsSensorDescription(key="active_player", value=lambda d: d.get("active_player"), attributes=lambda d: {"players": d.get("players")}),
    DartsSensorDescription(key="mode", value=lambda d: d.get("mode")),
    DartsSensorDescription(key="variant", value=lambda d: d.get("variant")),
    DartsSensorDescription(key="checkout_route", value=_checkout("route"), attributes=lambda d: dict(d.get("checkout") or {})),
    DartsSensorDescription(key="checkout_kind", value=_checkout("kind")),
    DartsSensorDescription(key="checkout_rest", value=_checkout("rest"), state_class=SensorStateClass.MEASUREMENT),
    DartsSensorDescription(key="darts_left", value=_checkout("darts_left")),
    DartsSensorDescription(key="average", value=_stat("average"), state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="checkout_percent", value=_stat("checkout_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT),
    DartsSensorDescription(key="win_percent", value=_stat("win_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT),
    DartsSensorDescription(key="best_leg_darts", value=_stat("best_leg_darts")),
    DartsSensorDescription(key="best_checkout", value=_stat("best_checkout")),
    DartsSensorDescription(key="playtime_today", value=lambda d: d["playtime"]["today_min"], device_class=SensorDeviceClass.DURATION,
                           native_unit_of_measurement=UnitOfTime.MINUTES, state_class=SensorStateClass.MEASUREMENT),
    DartsSensorDescription(key="playtime_week", value=lambda d: d["playtime"]["week_min"], device_class=SensorDeviceClass.DURATION,
                           native_unit_of_measurement=UnitOfTime.MINUTES, state_class=SensorStateClass.MEASUREMENT),
    DartsSensorDescription(key="board_memory", value=lambda d: d.get("board_memory"), entity_category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(DartsSensor(entry.runtime_data, description) for description in SENSORS)


class DartsSensor(DartsRelayEntity, SensorEntity):
    entity_description: DartsSensorDescription

    def __init__(self, coordinator, description: DartsSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attributes = self.entity_description.attributes
        return attributes(self.coordinator.data) if attributes else None

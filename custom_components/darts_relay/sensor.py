"""Sensoren: Spiel, Checkout-Weg, Statistik, Spielzeit."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
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


def _ana(part: str, key: str) -> Callable[[dict], Any]:
    """Wurfanalyse aus den Autodarts-Koordinaten (ab Relais 13.11.2026)."""
    return lambda d: ((d.get("analysis") or {}).get(part) or {}).get(key)


MM = "mm"


def _last_180(d: dict) -> date | None:
    """Tag der letzten 180 laut Autodarts-Statistik (ab Relais 23.11.2026)."""
    try:
        return date.fromisoformat((d.get("t180") or {}).get("last") or "")
    except ValueError:
        return None


def _tr(game: str, key: str) -> Callable[[dict], Any]:
    """Trainingsspiele des Relais (170 Checkout, JDC Challenge; ab Relais 24.11.2026)."""
    return lambda d: ((d.get("training") or {}).get(game) or {}).get(key)


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
    # Streuung und Tendenz auf der T20 (Darts beim Punkten, Rest ueber 170)
    DartsSensorDescription(key="t20_hit_percent", value=_ana("t20", "hit_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="t20_in_20_percent", value=_ana("t20", "in_20_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="t20_spread", value=_ana("t20", "spread_mm"), native_unit_of_measurement=MM,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="t20_bias_x", value=_ana("t20", "bias_x_mm"), native_unit_of_measurement=MM,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="t20_bias_y", value=_ana("t20", "bias_y_mm"), native_unit_of_measurement=MM,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="t20_tendency", value=_ana("t20", "tendency"),
                           attributes=lambda d: dict((d.get("analysis") or {}).get("t20") or {})),
    # Doppel-Analyse (Rest gerade und hoechstens 40, bzw. 50 aufs Bull)
    DartsSensorDescription(key="double_hit_percent", value=_ana("double", "hit_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="double_miss_inside", value=_ana("double", "miss_inside_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="double_miss_outside", value=_ana("double", "miss_outside_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="double_miss_side", value=_ana("double", "miss_side_percent"), native_unit_of_measurement=PERCENTAGE,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="double_bias_radial", value=_ana("double", "bias_radial_mm"), native_unit_of_measurement=MM,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="double_bias_side", value=_ana("double", "bias_side_mm"), native_unit_of_measurement=MM,
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1),
    DartsSensorDescription(key="double_tendency", value=_ana("double", "tendency"),
                           attributes=lambda d: dict((d.get("analysis") or {}).get("double") or {})),
    # Letztes Leg; der Verlauf (fuer Zeitstrahlen) steht als Attribut history = [[Zeit, Average, Darts, gewonnen], ...]
    DartsSensorDescription(key="last_leg_average", value=lambda d: ((d.get("legs") or {}).get("last") or {}).get("average"),
                           state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
                           attributes=lambda d: dict(((d.get("legs") or {}).get("last") or {}), history=(d.get("legs") or {}).get("history") or [])),
    DartsSensorDescription(key="last_leg_darts", value=lambda d: ((d.get("legs") or {}).get("last") or {}).get("darts"),
                           state_class=SensorStateClass.MEASUREMENT,
                           attributes=lambda d: {"won": ((d.get("legs") or {}).get("last") or {}).get("won")}),
    # 180er laut Autodarts (Profil und Tagesgrafik, alle 30 Minuten aktualisiert); days = [["2026-11-23", 1], ...]
    DartsSensorDescription(key="total_180s", value=lambda d: (d.get("t180") or {}).get("total"),
                           state_class=SensorStateClass.TOTAL_INCREASING,
                           attributes=lambda d: {"days": (d.get("t180") or {}).get("days") or [],
                                                 "since": (d.get("t180") or {}).get("since")}),
    DartsSensorDescription(key="last_180", value=_last_180, device_class=SensorDeviceClass.DATE),
    # Eigene Trainingsspiele des Relais (ab 0.4.2): letztes Ergebnis mit Verlauf als Attribut history, Bestwert
    DartsSensorDescription(key="training_170_last", value=_tr("c170", "last"), native_unit_of_measurement="Checkouts",
                           state_class=SensorStateClass.MEASUREMENT,
                           attributes=lambda d: {"rounds": _tr("c170", "last_rounds")(d), "darts_per_round": _tr("c170", "last_darts")(d),
                                                 "avg_darts": _tr("c170", "last_avg_darts")(d), "time": _tr("c170", "last_time")(d),
                                                 "count": _tr("c170", "count")(d), "history": _tr("c170", "history")(d) or []}),
    DartsSensorDescription(key="training_170_best", value=_tr("c170", "best"), native_unit_of_measurement="Checkouts"),
    DartsSensorDescription(key="training_jdc_last", value=_tr("jdc", "last"), native_unit_of_measurement="Punkte",
                           state_class=SensorStateClass.MEASUREMENT,
                           attributes=lambda d: {"parts": _tr("jdc", "last_parts")(d), "time": _tr("jdc", "last_time")(d),
                                                 "average10": _tr("jdc", "average10")(d), "count": _tr("jdc", "count")(d),
                                                 "history": _tr("jdc", "history")(d) or []}),
    DartsSensorDescription(key="training_jdc_best", value=_tr("jdc", "best"), native_unit_of_measurement="Punkte"),
    DartsSensorDescription(key="analysis_darts", value=lambda d: (d.get("analysis") or {}).get("darts_total"),
                           state_class=SensorStateClass.TOTAL, entity_category=EntityCategory.DIAGNOSTIC),
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

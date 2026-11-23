"""Verbindung zum Darts-Relais: wartende Abfrage von /ha, jede Aenderung kommt sofort an.

Ab 0.4.0 merkt sich die Integration den letzten Stand in Home Assistant (.storage). Ist der Darts-PC aus, bleiben Statistik,
Wurfanalyse und Leg-Verlauf mit dem letzten Wert stehen (auch nach einem Neustart von Home Assistant); nur was es ohne
laufendes Spiel nicht gibt (Spiel laeuft, aktiver Spieler, Checkout-Weg, Geraete) wird zurueckgesetzt.
"""
import asyncio
import logging
import time
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import BUS_EVENT, DOMAIN, POLL_TIMEOUT, POLL_WAIT, RETRY_AFTER, SAVE_DELAY, SIGNAL_EVENT, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


async def async_fetch(session: aiohttp.ClientSession, host: str, port: int, after: int | None = None, wait: int = 0) -> dict[str, Any]:
    """Zustand und neue Ereignisse vom Relais holen."""
    params = {"wait": wait}
    if after is not None:
        params["after"] = after
    timeout = aiohttp.ClientTimeout(total=POLL_TIMEOUT)
    async with session.get(f"http://{host}:{port}/ha", params=params, timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.json()


def offline_state(state: dict[str, Any]) -> dict[str, Any]:
    """Letzter Stand ohne die Teile, die es nur bei laufendem Relais gibt."""
    data = dict(state)
    data.update(playing=False, mode=None, variant=None, players=[], active_player=None, checkout=None,
                devices={k: False for k in (state.get("devices") or {})}, board_memory=None)
    return data


class DartsRelayCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Haelt den Zustand des Relais; update_interval bleibt leer, die Daten kommen ueber async_listen."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.session = async_get_clientsession(hass)
        self._seq: int | None = None
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.online = False
        self.saved_at: float | None = None   # Zeit des gespeicherten Stands (fuer "Stand vom ...")
        self._saved_state: dict[str, Any] | None = None
        self._last_write = 0.0

    async def async_start(self) -> None:
        """Erster Stand: vom Relais, sonst der gespeicherte. Ohne beides (erste Einrichtung, PC aus): spaeter erneut versuchen."""
        stored = await self._store.async_load()
        try:
            payload = await async_fetch(self.session, self.host, self.port)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            if not stored or not isinstance(stored.get("state"), dict):
                raise ConfigEntryNotReady(f"Relais nicht erreichbar: {err}") from err
            _LOGGER.info("Relais nicht erreichbar, nehme den gespeicherten Stand vom %s",
                         time.strftime("%d.%m. %H:%M", time.localtime(stored.get("saved") or 0)))
            self.saved_at = stored.get("saved")
            self.async_set_updated_data(offline_state(stored["state"]))
            return
        self._seq = payload["seq"]
        self._accept(payload["state"])

    def _accept(self, state: dict[str, Any]) -> None:
        self.online = True
        self.saved_at = time.time()
        self.async_set_updated_data(state)
        if state == self._saved_state:
            return
        # Speichern: hoechstens einmal je SAVE_DELAY sofort, sonst den letzten Stand verzoegert nachziehen
        # (async_delay_save allein wuerde bei Aenderungen alle paar Sekunden immer wieder verschoben)
        self._saved_state = state
        data = {"saved": self.saved_at, "state": state}
        if self.saved_at - self._last_write >= SAVE_DELAY:
            self._last_write = self.saved_at
            self.hass.async_create_task(self._store.async_save(data))
        else:
            self._store.async_delay_save(lambda: data, SAVE_DELAY)

    async def _async_update_data(self) -> dict[str, Any]:
        """Wird nicht gebraucht (keine regelmaessige Abfrage); liefert den aktuellen Stand."""
        return self.data or {}

    async def async_listen(self) -> None:
        """Laeuft, solange die Integration geladen ist."""
        while True:
            try:
                payload = await async_fetch(self.session, self.host, self.port, self._seq, POLL_WAIT)
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                if self.online:
                    _LOGGER.info("Relais nicht erreichbar (%s), Werte bleiben auf dem letzten Stand", err)
                    self.online = False
                    self._seq = None
                    self.async_set_updated_data(offline_state(self.data or {}))
                await asyncio.sleep(RETRY_AFTER)
                continue
            self._seq = payload["seq"]
            for event in payload["events"]:
                self.hass.bus.async_fire(BUS_EVENT, event)
                async_dispatcher_send(self.hass, SIGNAL_EVENT.format(self.config_entry.entry_id), event)
            self._accept(payload["state"])

    async def async_save_now(self) -> None:
        """Beim Entladen den letzten Stand sofort sichern."""
        if self.online and self.data:
            await self._store.async_save({"saved": self.saved_at, "state": self.data})

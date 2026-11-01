"""Verbindung zum Darts-Relais: wartende Abfrage von /ha, jede Aenderung kommt sofort an."""
import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BUS_EVENT, DOMAIN, POLL_TIMEOUT, POLL_WAIT, RETRY_AFTER, SIGNAL_EVENT

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


class DartsRelayCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Haelt den Zustand des Relais; update_interval bleibt leer, die Daten kommen ueber async_listen."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry)
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._session = async_get_clientsession(hass)
        self._seq: int | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            payload = await async_fetch(self._session, self._host, self._port)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Relais nicht erreichbar: {err}") from err
        self._seq = payload["seq"]
        return payload["state"]

    async def async_listen(self) -> None:
        """Laeuft, solange die Integration geladen ist."""
        while True:
            try:
                payload = await async_fetch(self._session, self._host, self._port, self._seq, POLL_WAIT)
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                self.async_set_update_error(UpdateFailed(f"Relais nicht erreichbar: {err}"))
                await asyncio.sleep(RETRY_AFTER)
                continue
            self._seq = payload["seq"]
            for event in payload["events"]:
                self.hass.bus.async_fire(BUS_EVENT, event)
                async_dispatcher_send(self.hass, SIGNAL_EVENT.format(self.config_entry.entry_id), event)
            self.async_set_updated_data(payload["state"])

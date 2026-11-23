"""Trefferbild der Wurfanalyse als Bild-Entitaet (ab 0.4.0).

Das Bild kommt vom Relais (/api/wurfbild.png), sobald sich die Wurfanalyse aendert, und wird unter
/config/darts_relay/ gespeichert. So bleibt es auch sichtbar, wenn der Darts-PC aus ist oder Home Assistant neu startet.
"""
import logging
import os
from typing import Any

import aiohttp
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import DartsRelayConfigEntry
from .const import DOMAIN
from .coordinator import DartsRelayCoordinator
from .entity import DartsRelayEntity

_LOGGER = logging.getLogger(__name__)
PNG = b"\x89PNG\r\n\x1a\n"


async def async_setup_entry(hass: HomeAssistant, entry: DartsRelayConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([HitMapImage(hass, entry.runtime_data)])


def _read(path: str) -> tuple[bytes | None, float | None]:
    try:
        with open(path, "rb") as f:
            return f.read(), os.path.getmtime(path)
    except OSError:
        return None, None


def _write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


class HitMapImage(DartsRelayEntity, ImageEntity):
    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, coordinator: DartsRelayCoordinator) -> None:
        DartsRelayEntity.__init__(self, coordinator, "hit_map")
        ImageEntity.__init__(self, hass)
        self._path = hass.config.path(DOMAIN, f"{coordinator.config_entry.entry_id}_trefferbild.png")
        self._image: bytes | None = None
        self._key: Any = None
        self._busy = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data, mtime = await self.hass.async_add_executor_job(_read, self._path)
        if data:
            self._image = data
            self._attr_image_last_updated = dt_util.utc_from_timestamp(mtime)
            self.async_write_ha_state()
        self._maybe_fetch()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._maybe_fetch()
        super()._handle_coordinator_update()

    def _analysis_key(self) -> Any:
        a = (self.coordinator.data or {}).get("analysis") or {}
        return (a.get("darts_total"), (a.get("t20") or {}).get("darts"), (a.get("double") or {}).get("darts"))

    @callback
    def _maybe_fetch(self) -> None:
        """Neues Bild holen, wenn das Relais laeuft und sich die Auswertung geaendert hat (oder noch keins da ist)."""
        if not self.coordinator.online or self._busy:
            return
        key = self._analysis_key()
        if self._image is not None and key == self._key:
            return
        self._busy = True
        self.hass.async_create_task(self._fetch(key))

    async def _fetch(self, key: Any) -> None:
        url = f"http://{self.coordinator.host}:{self.coordinator.port}/api/wurfbild.png"
        try:
            async with self.coordinator.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Trefferbild nicht geholt: %s", err)
            return
        finally:
            self._busy = False
        if not data.startswith(PNG):
            _LOGGER.debug("Trefferbild: Relais lieferte kein PNG")
            return
        self._key = key
        if data == self._image:
            return
        self._image = data
        self._attr_image_last_updated = dt_util.utcnow()
        try:
            await self.hass.async_add_executor_job(_write, self._path, data)
        except OSError as err:
            _LOGGER.warning("Trefferbild nicht gespeichert: %s", err)
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self._image

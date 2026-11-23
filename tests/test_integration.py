"""Prueft Einrichtung, Sensoren, Ereignisse und den Ausfall des Relais in einem echten Home Assistant."""
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.darts_relay.const import BUS_EVENT, DOMAIN

pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])


async def setup_entry(hass: HomeAssistant, relay) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "127.0.0.1", CONF_PORT: relay.server.port}, title="Darts Relay")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def settle(hass: HomeAssistant, check) -> None:
    import asyncio
    for _ in range(100):
        await hass.async_block_till_done()
        if check():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Zustand nicht erreicht")


async def test_config_flow(hass: HomeAssistant, relay) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "127.0.0.1", CONF_PORT: relay.server.port})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(result["result"].entry_id)


async def test_config_flow_cannot_connect(hass: HomeAssistant, relay) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "127.0.0.1", CONF_PORT: 1})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_entities(hass: HomeAssistant, relay) -> None:
    entry = await setup_entry(hass, relay)
    assert hass.states.get("sensor.darts_checkout_route").state == "T20 T20 BULL"
    assert hass.states.get("sensor.darts_active_player").attributes["players"][0]["rest"] == 170
    assert hass.states.get("sensor.darts_my_remaining_score").state == "170"
    assert hass.states.get("binary_sensor.darts_game_running").state == "on"
    assert hass.states.get("binary_sensor.darts_8x32_display").state == "off"
    assert hass.states.get("sensor.darts_play_time_today").state == "41"
    assert hass.states.get("sensor.darts_t20_hit_rate").state == "12.4"
    assert hass.states.get("sensor.darts_t20_tendency").state == "mittig"
    assert hass.states.get("sensor.darts_double_misses_outside").state == "57.7"
    assert hass.states.get("sensor.darts_double_tendency").attributes["per_double"]["D16"]["hits"] == 2
    assert hass.states.get("sensor.darts_last_leg_average").state == "56.4"
    assert hass.states.get("sensor.darts_last_leg_average").attributes["history"][1][2] == 24
    assert hass.states.get("sensor.darts_last_leg_darts").state == "24"
    assert hass.states.get("sensor.darts_total_180s").state == "18"
    assert hass.states.get("sensor.darts_total_180s").attributes["days"][1] == ["2026-11-23", 1]
    assert hass.states.get("sensor.darts_last_180").state == "2026-11-23"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_event_arrives_at_once(hass: HomeAssistant, relay) -> None:
    entry = await setup_entry(hass, relay)
    bus = async_capture_events(hass, BUS_EVENT)
    relay.push({"type": "180", "player": "mamic", "score": "60", "visit": "180", "dart": "3", "mode": "X01", "variant": "501"},
               checkout=None, playing=True)
    await settle(hass, lambda: bool(bus))
    assert bus[0].data["type"] == "180"
    state = hass.states.get("event.darts_game_event")
    assert state.attributes["event_type"] == "180"
    assert state.attributes["player"] == "mamic"
    assert hass.states.get("sensor.darts_checkout_route").state == "unknown"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_relay_goes_away(hass: HomeAssistant, relay) -> None:
    """Ab 0.4.0: Statistik bleibt auf dem letzten Stand, nur Live-Werte werden leer, "Relais erreichbar" geht aus."""
    entry = await setup_entry(hass, relay)
    assert hass.states.get("binary_sensor.darts_relay_reachable").state == "on"
    await relay.server.close()
    relay.push()
    await settle(hass, lambda: hass.states.get("binary_sensor.darts_relay_reachable").state == "off")
    assert hass.states.get("sensor.darts_checkout_route").state == "unknown"
    assert hass.states.get("binary_sensor.darts_game_running").state == "off"
    assert hass.states.get("sensor.darts_average").state == "45.6"
    assert hass.states.get("sensor.darts_t20_hit_rate").state == "12.4"
    assert hass.states.get("sensor.darts_last_leg_average").attributes["history"][1][2] == 24
    await hass.config_entries.async_unload(entry.entry_id)


async def test_start_without_relay_uses_saved_state(hass: HomeAssistant, relay, hass_storage) -> None:
    """Home Assistant startet, waehrend der Darts-PC aus ist: gespeicherter Stand statt "nicht verfuegbar"."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "127.0.0.1", CONF_PORT: 1}, title="Darts Relay")
    entry.add_to_hass(hass)
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {"version": 1, "key": f"{DOMAIN}.{entry.entry_id}",
                                                  "data": {"saved": 1794522900, "state": dict(relay.state)}}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.darts_average").state == "45.6"
    assert hass.states.get("sensor.darts_last_leg_average").attributes["history"][0][1] == 48.1
    assert hass.states.get("binary_sensor.darts_relay_reachable").state == "off"
    assert hass.states.get("binary_sensor.darts_game_running").state == "off"
    assert hass.states.get("sensor.darts_checkout_route").state == "unknown"
    await hass.config_entries.async_unload(entry.entry_id)


async def test_start_without_relay_and_nothing_saved(hass: HomeAssistant, socket_enabled) -> None:
    """Erste Einrichtung bei ausgeschaltetem PC: wie bisher spaeter erneut versuchen."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "127.0.0.1", CONF_PORT: 1}, title="Darts Relay")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.SETUP_RETRY


async def test_state_is_saved(hass: HomeAssistant, relay, hass_storage) -> None:
    entry = await setup_entry(hass, relay)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    saved = hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]
    assert saved["state"]["stats"]["average"] == 45.6


async def test_hit_map_image(hass: HomeAssistant, relay, hass_client) -> None:
    """Trefferbild wird vom Relais geholt und erst bei geaenderter Auswertung neu geladen."""
    entry = await setup_entry(hass, relay)
    await settle(hass, lambda: hass.states.get("image.darts_hit_map").state not in ("unknown", "unavailable"))
    client = await hass_client()
    resp = await client.get(hass.states.get("image.darts_hit_map").attributes["entity_picture"])
    assert resp.status == 200
    assert (await resp.read()).endswith(b"bild1")
    calls = relay.image_calls
    relay.push(playing=True)   # Auswertung unveraendert: kein neues Bild
    await settle(hass, lambda: True)
    assert relay.image_calls == calls
    relay.png = b"\x89PNG\r\n\x1a\n" + b"bild2"
    relay.push(analysis=dict(relay.state["analysis"], darts_total=339))
    await settle(hass, lambda: relay.image_calls == calls + 1)
    await hass.config_entries.async_unload(entry.entry_id)

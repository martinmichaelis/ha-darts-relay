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
    entry = await setup_entry(hass, relay)
    await relay.server.close()
    relay.push()
    await settle(hass, lambda: hass.states.get("sensor.darts_checkout_route").state == STATE_UNAVAILABLE)
    await hass.config_entries.async_unload(entry.entry_id)

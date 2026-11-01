"""Testumgebung: ein kleines Ersatz-Relais im Testprozess."""
import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


STATE = {"playing": True, "mode": "X01", "variant": "501", "active_player": "mamic",
         "players": [{"name": "mamic", "rest": 170, "darts": 3, "average": 60.0, "leg_average": 60.0}],
         "checkout": {"route": "T20 T20 BULL", "kind": "finish", "darts": ["T20", "T20", "BULL"], "leave": 0, "player": "mamic",
                      "rest": 170, "darts_left": 3, "waiting": False},
         "stats": {"average": 45.6, "checkout_percent": 22.0, "win_percent": 65.0, "best_leg_darts": 15, "best_checkout": 126},
         "playtime": {"today_min": 41, "week_min": 192},
         "devices": {"hub": True, "board_manager": True, "board": True, "pixelit": False, "wled": True},
         "board_memory": "12.4 KB (20:00)"}


class FakeRelay:
    def __init__(self):
        self.seq = 1
        self.state = dict(STATE)
        self.events = []
        self.changed = asyncio.Event()
        self.server = TestServer(web.Application())
        self.server.app.router.add_get("/ha", self.handle)

    async def handle(self, request):
        after = request.query.get("after")
        wait = int(request.query.get("wait", 0))
        if wait and after is not None and int(after) == self.seq:
            try:
                await asyncio.wait_for(self.changed.wait(), wait)
            except TimeoutError:
                pass
        self.changed.clear()
        events, self.events = self.events, []
        return web.json_response({"seq": self.seq, "events": events, "state": self.state})

    def push(self, event=None, **changes):
        self.seq += 1
        self.state.update(changes)
        if event:
            self.events.append(dict(event, seq=self.seq))
        self.changed.set()


@pytest.fixture
async def relay(socket_enabled):
    fake = FakeRelay()
    await fake.server.start_server()
    yield fake
    await fake.server.close()

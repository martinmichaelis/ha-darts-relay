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
         "board_memory": "12.4 KB (20:00)",
         "analysis": {"darts_total": 338,
                      "t20": {"darts": 218, "hit_percent": 12.4, "in_20_percent": 68.8, "bias_x_mm": 3.1, "bias_y_mm": -2.6,
                              "spread_mm": 21.8, "distance_mm": 22.1, "tendency": "mittig"},
                      "double": {"darts": 33, "hit_percent": 21.2, "miss_inside_percent": 38.5, "miss_outside_percent": 57.7,
                                 "miss_side_percent": 0.0, "bias_radial_mm": -0.4, "bias_side_mm": -18.4,
                                 "tendency": "Hoehe passt, eher gegen den Uhrzeigersinn",
                                 "per_double": {"D16": {"darts": 7, "hits": 2, "hit_percent": 28.6}}}},
         "legs": {"last": {"average": 56.4, "darts": 24, "won": True, "opponent": "bot", "time": 1794522900},
                  "history": [[1794522000, 48.1, 30, 0], [1794522900, 56.4, 24, 1]]},
         "t180": {"total": 18, "days": [["2026-11-18", 1], ["2026-11-23", 1]], "last": "2026-11-23", "since": "2026-07-30"},
         "training": {"c170": {"count": 2, "best": 4, "last": 3, "last_rounds": 10, "last_darts": 9, "last_avg_darts": 6.3,
                               "last_time": "2026-11-24T13:40:00",
                               "history": [["2026-11-24T12:00:00", 4, 10, 9, 5.5], ["2026-11-24T13:40:00", 3, 10, 9, 6.3]]},
                      "jdc": {"count": 1, "best": 812, "last": 812, "last_parts": [301, 250, 261], "last_time": "2026-11-24T14:00:00",
                              "average10": 812, "history": [["2026-11-24T14:00:00", 812, 301, 250, 261]]}}}


class FakeRelay:
    def __init__(self):
        self.seq = 1
        self.state = dict(STATE)
        self.events = []
        self.changed = asyncio.Event()
        self.server = TestServer(web.Application())
        self.server.app.router.add_get("/ha", self.handle)
        self.server.app.router.add_get("/api/wurfbild.png", self.image)
        self.png = b"\x89PNG\r\n\x1a\n" + b"bild1"
        self.image_calls = 0

    async def image(self, request):
        self.image_calls += 1
        return web.Response(body=self.png, content_type="image/png")

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

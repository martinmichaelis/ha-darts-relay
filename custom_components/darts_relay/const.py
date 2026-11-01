"""Konstanten der Integration Darts Relay."""
DOMAIN = "darts_relay"
DEFAULT_PORT = 8080
BUS_EVENT = "darts_relay_event"
SIGNAL_EVENT = "darts_relay_event_{}"

POLL_WAIT = 25    # Sekunden, die das Relais auf ein Ereignis wartet
POLL_TIMEOUT = 40
RETRY_AFTER = 10

EVENT_TYPES = ["180", "bust", "high_finish", "leg_started", "game_started", "match_started", "leg_won", "game_won",
               "match_won", "bull_off", "player_changed", "throw"]

# Darts Relay für Home Assistant

Bringt Spielstand, Checkout-Wege, Ereignisse und Statistik aus dem Darts-Relais nach Home Assistant. Die Daten kommen über das lokale Netz, Ereignisse wie 180, Bust oder Leg gewonnen kommen ohne Abfrage-Pause an. Die Integration liest nur, sie steuert nichts.

Voraussetzung ist ein laufendes Darts-Relais (`dartsrelay.py`) ab November 2026 mit der Schnittstelle `/ha`.

## Installation

Über HACS: Benutzerdefinierte Repositories, dieses Repository als Typ „Integration“ eintragen, Darts Relay installieren, Home Assistant neu starten.

Von Hand: den Ordner `custom_components/darts_relay` nach `/config/custom_components/` kopieren und Home Assistant neu starten.

Danach: Einstellungen, Geräte & Dienste, Integration hinzufügen, Darts Relay. Als Adresse die IP des Darts-PCs eintragen, Port 8080.

## Was du bekommst

- Sensoren: aktiver Spieler, Spielmodus, Checkout-Weg, Rest, Darts der Aufnahme, Average, Quoten, Spielzeit
- Binärsensoren: Spiel läuft, Darts-Hub, Board Manager, großes Display, 8x32-Display, WLED
- Ereignis-Entität und Bus-Ereignis `darts_relay_event` mit `type`: `180`, `bust`, `high_finish`, `leg_started`, `game_started`, `match_started`, `leg_won`, `game_won`, `match_won`, `bull_off`, `player_changed`, `throw`

Beispiele für Licht-Automationen stehen in `examples/licht_automationen.yaml`.

## Tests

```bash
pip install pytest-homeassistant-custom-component
pytest tests
```

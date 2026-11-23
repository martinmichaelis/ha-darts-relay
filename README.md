# Darts Relay für Home Assistant

Bringt Spielstand, Checkout-Wege, Ereignisse und Statistik aus dem Darts-Relais nach Home Assistant. Die Daten kommen über das lokale Netz, Ereignisse wie 180, Bust oder Leg gewonnen kommen ohne Abfrage-Pause an. Die Integration liest nur, sie steuert nichts.

Voraussetzung ist ein laufendes Darts-Relais (`dartsrelay.py`) ab November 2026 mit der Schnittstelle `/ha`.

## Installation

Über HACS: Benutzerdefinierte Repositories, dieses Repository als Typ „Integration“ eintragen, Darts Relay installieren, Home Assistant neu starten.

Von Hand: den Ordner `custom_components/darts_relay` nach `/config/custom_components/` kopieren und Home Assistant neu starten.

Danach: Einstellungen, Geräte & Dienste, Integration hinzufügen, Darts Relay. Als Adresse die IP des Darts-PCs eintragen, Port 8080.

## Was du bekommst

- Sensoren: aktiver Spieler, Spielmodus, Checkout-Weg, Rest, Darts der Aufnahme, Average, Quoten, Spielzeit
- Wurfanalyse aus den Autodarts-Koordinaten: Trefferquote, Streuung und Tendenz auf der T20 (mm, rechts/links, hoch/tief), Doppel-Trefferquote, Fehlwürfe innen/außen/seitlich, Abweichung am Doppel und Quote je Doppel (Attribut `per_double`). Braucht ein Relais ab 13.11.2026 (`/api/wurfanalyse`).
- Letztes Leg: Average und Darts als Sensoren, dazu der Verlauf der letzten 300 Legs als Attribut `history` (`[Zeit, Average, Darts, gewonnen]`), z. B. für Zeitstrahlen mit der ApexCharts-Karte.
- Binärsensoren: Spiel läuft, Relais erreichbar, Darts-Hub, Board Manager, großes Display, 8x32-Display, WLED
- 180er laut Autodarts-Statistik (ab 0.4.1): Gesamtzahl mit Attribut `days` (`[["2026-11-23", 1], ...]`) und Tag der letzten 180
- Trefferbild der Wurfanalyse als Bild-Entität (ab 0.4.0), gespeichert unter `/config/darts_relay/`
- Ab 0.4.0 bleibt der letzte Stand erhalten, wenn der Darts-PC aus ist (auch nach einem Neustart von Home Assistant): Statistik, Wurfanalyse, Leg-Verlauf und Trefferbild zeigen den letzten Wert, nur die Live-Werte (Spiel läuft, aktiver Spieler, Checkout-Weg, Geräte) werden leer. Das Attribut `stand` von „Relais erreichbar“ sagt, von wann die Werte sind.
- Ereignis-Entität und Bus-Ereignis `darts_relay_event` mit `type`: `180`, `bust`, `high_finish`, `leg_started`, `game_started`, `match_started`, `leg_won`, `game_won`, `match_won`, `bull_off`, `player_changed`, `throw`

Beispiele für Licht-Automationen stehen in `examples/licht_automationen.yaml`, dazu je eine fertige Automation zum Einfügen: `licht_ergebnis.yaml` (Leg-/Match-Ergebnis), `licht_spielstimmung.yaml` (Spiellicht während des Matches), `licht_wer_wirft.yaml` (Farbe je Spieler) und `licht_highlights.yaml` (100+, 180, Bust, High Finish).

## Tests

```bash
pip install pytest-homeassistant-custom-component
pytest tests
```

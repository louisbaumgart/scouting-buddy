"""Alle Stellschrauben des Projekts an einem Ort."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PLAYERS_PARQUET = DATA_DIR / "players.parquet"

# Understat ist die Hauptquelle, weil es als einzige frei zugängliche Quelle
# noch xG-Daten liefert. Abgedeckt sind damit die fünf großen Ligen.
UNDERSTAT_LEAGUES = [
    "GER-Bundesliga",
    "ENG-Premier League",
    "ESP-La Liga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]

# fbref liefert seit dem Opta-Aus im Januar 2026 nur noch Basiswerte. Für
# zusätzliche Ligen reicht das trotzdem, wenn man auf xG verzichten kann.
# "Big 5 European Leagues Combined" ist ein einzelner Liga-Key und spart
# gegenüber fünf Einzelabfragen viel Ladezeit.
FBREF_LEAGUES = [
    "Big 5 European Leagues Combined",
    # "NED-Eredivisie",
    # "POR-Primeira Liga",
    # "ENG-Championship",
]
USE_FBREF_EXTRA = False

# SoFIFA liefert Attributwerte wie Zweikampf oder Kopfball. Das sind
# Einschätzungen aus dem Spiel, keine gemessenen Ereignisse. Der Scraper braucht
# einen Browser und ist entsprechend langsam, deshalb standardmäßig aus.
USE_SOFIFA = False

SEASONS = ["2425", "2526"]
MIN_MINUTES = 270  # unter drei Spielen Einsatzzeit sind per-90-Werte reines Rauschen

MODEL_NAME = "gpt-4o"
TEMPERATURE = 0  # bei Datenabfragen wollen wir reproduzierbare Antworten

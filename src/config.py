"""Zentrale Konfiguration für Scouting Buddy."""
from pathlib import Path

# Pfade
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PLAYERS_PARQUET = DATA_DIR / "players.parquet"

# --- Datengrundlage ---------------------------------------------------------
# Primärquelle: Understat (liefert xG, xA, npxG, Key Passes)
# Hinweis: fbref hat im Januar 2026 seine Advanced Stats (Opta) verloren –
# dort gibt es nur noch Basisdaten. Understat deckt Big 5 + RUS ab.
UNDERSTAT_LEAGUES = [
    "GER-Bundesliga",
    "ENG-Premier League",
    "ESP-La Liga",
    "ITA-Serie A",
    "FRA-Ligue 1",
]

# Optionale Zusatzquelle: fbref-Basisdaten (Tore/Assists/Minuten, KEIN xG)
# für weitere Ligen. "Big 5 European Leagues Combined" ist ein einzelner
# League-Key in soccerdata und effizienter als 5 Einzelabfragen.
FBREF_LEAGUES = [
    "Big 5 European Leagues Combined",
    # weitere Ligen ergänzbar, z. B.:
    # "NED-Eredivisie", "POR-Primeira Liga", "ENG-Championship",
]
USE_FBREF_EXTRA = False  # auf True setzen, um zusätzliche Ligen (nur Basisdaten) zu mergen

SEASONS = ["2425", "2526"]  # bei Bedarf anpassen
MIN_MINUTES = 270

# LLM
MODEL_NAME = "gpt-4o"
TEMPERATURE = 0

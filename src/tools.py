"""Die Werkzeuge, die das Sprachmodell aufrufen darf.

Bewusst keine frei generierten Pandas-Ausdrücke: Das Modell wählt eine Funktion
und füllt getypte Parameter. Das ist nicht nur sicherer, sondern liefert auch
verlässlichere Ergebnisse, weil ungültige Eingaben sofort auffallen.
"""
from datetime import date
from functools import lru_cache
from typing import Optional

import pandas as pd
from langchain_core.tools import tool

from src.config import PLAYERS_PARQUET


@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    """Lädt den Datensatz einmal pro Prozess und hält ihn im Speicher.

    Das Alter berechnen wir hier statt es abzuspeichern, sonst wäre der
    Datensatz nach einem Jahreswechsel stillschweigend veraltet.
    """
    df = pd.read_parquet(PLAYERS_PARQUET)
    if "birth_year" in df.columns:
        df["age"] = (date.today().year - df["birth_year"]).astype("Int64")
    return df


@tool
def query_players(
    position: Optional[str] = None,
    league: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[str] = None,
    min_minutes: Optional[float] = None,
    max_age: Optional[int] = None,
    min_age: Optional[int] = None,
    sort_by: str = "xg_per90",
    ascending: bool = False,
    limit: int = 10,
) -> str:
    """Sucht Spieler nach Filterkriterien und gibt eine sortierte Liste zurück.

    position: 'Abwehr', 'Mittelfeld' oder 'Sturm'
    league: zum Beispiel 'GER-Bundesliga'
    season: zum Beispiel '2526' für die Saison 2025/26
    max_age, min_age: Altersgrenzen, etwa max_age=23 für U23
    sort_by: eine Zahlenspalte, etwa 'xa_per90' oder 'xg_buildup_per90'
    """
    df = load_players()

    if position:
        df = df[df["position"] == position]
    if league:
        df = df[df["league"] == league]
    if team:
        # Teilstring, damit auch "Freiburg" statt "SC Freiburg" funktioniert
        df = df[df["team"].str.contains(team, case=False, na=False)]
    if season:
        df = df[df["season"].astype(str) == str(season)]
    if min_minutes is not None:
        df = df[df["minutes"] >= min_minutes]

    # Spieler ohne Geburtsjahr fliegen bei Altersfiltern raus. Sie stillschweigend
    # drinzulassen wäre schlimmer, weil sie das Ergebnis verfälschen würden.
    if max_age is not None:
        df = df[df["age"].notna() & (df["age"] <= max_age)]
    if min_age is not None:
        df = df[df["age"].notna() & (df["age"] >= min_age)]

    if sort_by not in df.columns:
        return f"Die Spalte '{sort_by}' gibt es nicht. Vorhanden sind: {list(df.columns)}"

    df = df.dropna(subset=[sort_by])
    if df.empty:
        return "Dazu passt kein Spieler. Vielleicht sind die Filter zu eng gesetzt."

    spalten = ["name", "team", "league", "season", "position", "age", "minutes", sort_by]
    treffer = df.sort_values(sort_by, ascending=ascending).head(limit)
    return treffer[[s for s in spalten if s in treffer.columns]].to_markdown(index=False)


@tool
def player_profile(name: str) -> str:
    """Gibt alle Werte zu einem Spieler aus, eine Zeile je Saison.

    Die Suche geht über Namensteile, "Grifo" genügt also.
    """
    df = load_players()
    treffer = df[df["name"].str.contains(name, case=False, na=False)]
    if treffer.empty:
        return f"Zu '{name}' ist niemand im Datensatz."
    return treffer.to_markdown(index=False)


@tool
def list_metrics() -> str:
    """Zeigt, welche Statistiken der Datensatz überhaupt kennt.

    Gedacht für Fragen nach Werten, die es womöglich nicht gibt, etwa
    Zweikämpfe oder Tacklings.
    """
    df = load_players()
    zahlenspalten = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    attribute = [c for c in zahlenspalten if c.startswith("rating_")]
    gemessen = [c for c in zahlenspalten if not c.startswith("rating_")]

    text = ["**Gemessene Werte:** " + ", ".join(gemessen)]
    if attribute:
        text.append("**Attributwerte aus SoFIFA, also Einschätzungen statt "
                    "gemessener Ereignisse:** " + ", ".join(attribute))
    text.append("**Nicht vorhanden:** Zweikämpfe, Luftzweikämpfe, Tacklings, "
                "Interceptions und Passstatistiken. Diese Opta-Daten sind seit "
                "Januar 2026 nicht mehr frei verfügbar.")
    return "\n\n".join(text)


ALL_TOOLS = [query_players, player_profile, list_metrics]

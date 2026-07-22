"""Strukturierte Tools, die der Agent per Function Calling aufruft.

Designentscheidung: Das LLM schreibt keinen freien Code, sondern ruft
Tools mit validierten Parametern auf (robuster & sicherer).
"""
from functools import lru_cache
from typing import Optional

import pandas as pd
from langchain_core.tools import tool

from src.config import PLAYERS_PARQUET


@lru_cache(maxsize=1)
def _load() -> pd.DataFrame:
    return pd.read_parquet(PLAYERS_PARQUET)


@tool
def query_players(
    position: Optional[str] = None,
    league: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[str] = None,
    min_minutes: Optional[float] = None,
    sort_by: str = "xg_per90",
    ascending: bool = False,
    limit: int = 10,
) -> str:
    """Filtert und sortiert Spieler nach Kriterien und gibt eine Top-Liste zurück.

    position: 'Abwehr', 'Mittelfeld' oder 'Sturm'.
    league: z. B. 'GER-Bundesliga'. season: z. B. '2526'.
    sort_by: numerische Spalte, z. B. 'xa_per90', 'key_passes_per90', 'goals'.
    """
    df = _load()
    if position:
        df = df[df["position"] == position]
    if league:
        df = df[df["league"] == league]
    if team:
        df = df[df["team"].str.contains(team, case=False, na=False)]
    if season:
        df = df[df["season"].astype(str) == str(season)]
    if min_minutes is not None:
        df = df[df["minutes"] >= min_minutes]

    if sort_by not in df.columns:
        return f"Unbekannte Spalte '{sort_by}'. Verfügbar: {list(df.columns)}"
    df = df.dropna(subset=[sort_by])
    if df.empty:
        return "Keine Spieler gefunden – Filter ggf. lockern."

    cols = ["name", "team", "league", "season", "position", "minutes", sort_by]
    out = df.sort_values(sort_by, ascending=ascending).head(limit)
    return out[cols].to_markdown(index=False)


@tool
def player_profile(name: str) -> str:
    """Gibt alle verfügbaren Statistiken zu einem Spieler zurück (Teilstring-Suche im Namen)."""
    df = _load()
    hit = df[df["name"].str.contains(name, case=False, na=False)]
    if hit.empty:
        return f"Kein Spieler gefunden für '{name}'."
    return hit.to_markdown(index=False)


ALL_TOOLS = [query_players, player_profile]

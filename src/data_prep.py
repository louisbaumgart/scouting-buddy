"""Einmalige Datenaufbereitung für Scouting Buddy.

Primärquelle: Understat (xG, xA, npxG, Key Passes; Big 5-Ligen).
Optional: fbref-Basisdaten für weitere Ligen (seit Jan. 2026 ohne Advanced Stats).

Ausführen mit:  python -m src.data_prep
"""
import pandas as pd
import soccerdata as sd

from src.config import (
    UNDERSTAT_LEAGUES, FBREF_LEAGUES, USE_FBREF_EXTRA,
    SEASONS, MIN_MINUTES, PLAYERS_PARQUET, DATA_DIR,
)


def _per90(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[f"{c}_per90"] = (df[c] / df["minutes"] * 90).round(2)
    return df


def load_understat() -> pd.DataFrame:
    us = sd.Understat(leagues=UNDERSTAT_LEAGUES, seasons=SEASONS)
    df = us.read_player_season_stats().reset_index()

    # Spalten vereinheitlichen – Namen ggf. an tatsächliche Ausgabe anpassen
    rename_map = {
        "player": "name",
        "position": "position_raw",
        "matches": "matches",
        "minutes": "minutes",
        "goals": "goals",
        "assists": "assists",
        "xg": "xg",
        "np_xg": "npxg",
        "xa": "xa",
        "shots": "shots",
        "key_passes": "key_passes",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Torhüter raus, grobe Positionsgruppe
    df = df[~df["position_raw"].astype(str).str.contains("GK", na=False)]

    def pos_group(p: str) -> str:
        p = str(p)
        if p.startswith("D"):
            return "Abwehr"
        if p.startswith("M"):
            return "Mittelfeld"
        return "Sturm"

    df["position"] = df["position_raw"].map(pos_group)

    num_cols = ["minutes", "goals", "assists", "xg", "npxg", "xa", "shots", "key_passes"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["minutes"] >= MIN_MINUTES]
    df = _per90(df, ["goals", "assists", "xg", "npxg", "xa", "shots", "key_passes"])
    df["source"] = "understat"
    return df


def load_fbref_extra() -> pd.DataFrame:
    """Basisdaten (kein xG!) für zusätzliche Ligen über fbref."""
    fbref = sd.FBref(leagues=FBREF_LEAGUES, seasons=SEASONS)
    df = fbref.read_player_season_stats(stat_type="standard").reset_index()
    df.columns = [
        "_".join(str(p) for p in col if p and "Unnamed" not in str(p)).strip("_")
        if isinstance(col, tuple) else str(col)
        for col in df.columns
    ]
    rename_map = {
        "player": "name",
        "pos": "position_raw",
        "Playing Time_Min": "minutes",
        "Performance_Gls": "goals",
        "Performance_Ast": "assists",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df = df[~df["position_raw"].astype(str).str.contains("GK", na=False)]
    df["position"] = df["position_raw"].map(
        lambda p: "Abwehr" if "DF" in str(p) else ("Mittelfeld" if "MF" in str(p) else "Sturm")
    )
    for c in ["minutes", "goals", "assists"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["minutes"] >= MIN_MINUTES]
    df = _per90(df, ["goals", "assists"])
    df["source"] = "fbref_basic"
    return df


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    frames = [load_understat()]
    if USE_FBREF_EXTRA:
        frames.append(load_fbref_extra())
    df = pd.concat(frames, ignore_index=True)

    keep = ["name", "team", "league", "season", "position", "minutes", "source",
            "goals", "assists", "xg", "npxg", "xa", "shots", "key_passes"] + \
           [c for c in df.columns if c.endswith("_per90")]
    df = df[[c for c in keep if c in df.columns]].reset_index(drop=True)

    df.to_parquet(PLAYERS_PARQUET, index=False)
    print(f"{len(df)} Spielersaisons gespeichert unter {PLAYERS_PARQUET}")
    print(df.head())


if __name__ == "__main__":
    main()

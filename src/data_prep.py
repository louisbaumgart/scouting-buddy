"""Baut den Datensatz, auf dem Scouting Buddy arbeitet.

Einmal ausführen, danach liest die App nur noch das fertige Parquet:

    python -m src.data_prep

Zusammengetragen wird aus drei Quellen:
  Understat  Torgefahr, Kreativität, Angriffsbeteiligung (inklusive xG)
  fbref      Geburtsjahr, damit Altersfilter wie U23 funktionieren
  SoFIFA     Attributwerte für ein Defensivprofil, optional

Was fehlt und auch nicht zu beschaffen ist: Zweikämpfe, Luftzweikämpfe,
Tacklings, Interceptions. Diese Werte kamen von Opta über fbref und wurden
im Januar 2026 abgeschaltet.
"""
import unicodedata

import pandas as pd
import soccerdata as sd

from src.config import (
    UNDERSTAT_LEAGUES, FBREF_LEAGUES, USE_FBREF_EXTRA, USE_SOFIFA,
    SEASONS, MIN_MINUTES, PLAYERS_PARQUET, DATA_DIR,
)


def normalize_name(name: str) -> str:
    """Vereinheitlicht Spielernamen für den Abgleich zwischen den Quellen.

    Understat schreibt "Vincenzo Grifo", fbref manchmal mit Akzenten oder
    Bindestrichen. Ohne diese Normalisierung findet der Merge die Hälfte nicht.
    """
    ohne_akzente = unicodedata.normalize("NFKD", str(name))
    ohne_akzente = "".join(c for c in ohne_akzente if not unicodedata.combining(c))
    return "".join(c for c in ohne_akzente.lower() if c.isalpha() or c == " ").strip()


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """fbref liefert verschachtelte Spaltenköpfe, die machen wir hier flach."""
    df = df.copy()
    df.columns = [
        "_".join(str(teil) for teil in spalte if teil and "Unnamed" not in str(teil)).strip("_")
        if isinstance(spalte, tuple) else str(spalte)
        for spalte in df.columns
    ]
    return df


def rename_first_match(df: pd.DataFrame, ziel: str, kandidaten: list[str]) -> pd.DataFrame:
    """Benennt die erste passende Spalte um.

    Die Quellen ändern ihre Spaltennamen gelegentlich (mal "xg_chain", mal
    "xgchain"). Statt bei jeder Umbenennung das Skript zu reparieren, probieren
    wir mehrere Schreibweisen durch.
    """
    vorhanden = {c.lower().replace(" ", "_"): c for c in df.columns}
    for kandidat in kandidaten:
        if kandidat in vorhanden:
            return df.rename(columns={vorhanden[kandidat]: ziel})
    return df


def add_per90(df: pd.DataFrame, spalten: list[str]) -> pd.DataFrame:
    """Rechnet Saisonsummen auf 90 Minuten um, damit Ersatzspieler vergleichbar werden."""
    for spalte in spalten:
        if spalte in df.columns:
            df[f"{spalte}_per90"] = (df[spalte] / df["minutes"] * 90).round(2)
    return df


# Links das gewünschte Ziel, rechts die Schreibweisen, unter denen Understat
# den Wert schon ausgeliefert hat.
UNDERSTAT_FELDER = {
    "name":         ["player", "player_name", "name"],
    "position_raw": ["position"],
    "matches":      ["matches", "games", "apps"],
    "minutes":      ["minutes", "time"],
    "goals":        ["goals"],
    "npg":          ["npg", "np_goals", "non_penalty_goals"],
    "assists":      ["assists"],
    "xg":           ["xg"],
    "npxg":         ["npxg", "np_xg"],
    "xa":           ["xa", "xag"],
    "xg_chain":     ["xg_chain", "xgchain"],
    "xg_buildup":   ["xg_buildup", "xgbuildup"],
    "shots":        ["shots"],
    "key_passes":   ["key_passes", "keypasses"],
    "yellow_cards": ["yellow_cards", "yellow"],
    "red_cards":    ["red_cards", "red"],
}

ZAHLENSPALTEN = [
    "matches", "minutes", "goals", "npg", "assists", "xg", "npxg", "xa",
    "xg_chain", "xg_buildup", "shots", "key_passes", "yellow_cards", "red_cards",
]

# Karten pro 90 wären Unsinn, deshalb hier bewusst eine kürzere Liste.
PER90_SPALTEN = [
    "goals", "npg", "assists", "xg", "npxg", "xa",
    "xg_chain", "xg_buildup", "shots", "key_passes",
]


def gruppiere_position(position: str) -> str:
    """Understat kennt Feinpositionen wie "DMC". Für Filter reichen drei Gruppen."""
    position = str(position)
    if position.startswith("D"):
        return "Abwehr"
    if position.startswith("M"):
        return "Mittelfeld"
    return "Sturm"


def load_understat() -> pd.DataFrame:
    """Holt die Saisonwerte aller Feldspieler aus den konfigurierten Ligen."""
    understat = sd.Understat(leagues=UNDERSTAT_LEAGUES, seasons=SEASONS)
    df = understat.read_player_season_stats().reset_index()

    for ziel, kandidaten in UNDERSTAT_FELDER.items():
        df = rename_first_match(df, ziel, kandidaten)

    fehlend = [feld for feld in UNDERSTAT_FELDER if feld not in df.columns]
    if fehlend:
        print(f"Diese Understat-Spalten kamen nicht an: {fehlend}")

    # Torhüter haben ein völlig anderes Statistikprofil und würden jede
    # Sortierung nach xG oder Key Passes nur verwässern.
    df = df[~df["position_raw"].astype(str).str.contains("GK", na=False)]
    df["position"] = df["position_raw"].map(gruppiere_position)

    for spalte in ZAHLENSPALTEN:
        if spalte in df.columns:
            df[spalte] = pd.to_numeric(df[spalte], errors="coerce")

    df = df[df["minutes"] >= MIN_MINUTES]
    df = add_per90(df, PER90_SPALTEN)
    df["source"] = "understat"
    return df


def load_birth_years() -> pd.DataFrame:
    """Zieht das Geburtsjahr je Spieler aus den fbref-Basisdaten.

    Ein exaktes Geburtsdatum gibt fbref hier nicht her, nur das Jahr. Für einen
    U23-Filter reicht das, die Altersangabe ist dadurch aber ein Jahr unscharf.
    """
    fbref = sd.FBref(leagues=["Big 5 European Leagues Combined"], seasons=SEASONS)
    df = flatten_columns(fbref.read_player_season_stats(stat_type="standard").reset_index())

    namensspalte = "player" if "player" in df.columns else "name"
    jahresspalte = next((c for c in df.columns if c.lower().endswith("born")), None)
    if jahresspalte is None:
        print("Keine Spalte mit Geburtsjahr gefunden, Altersfilter bleiben leer.")
        return pd.DataFrame(columns=["name_norm", "birth_year"])

    df["birth_year"] = pd.to_numeric(df[jahresspalte], errors="coerce")
    df["name_norm"] = df[namensspalte].map(normalize_name)
    df = df.dropna(subset=["birth_year"])

    # Ein Spieler taucht über mehrere Saisons und Vereine auf. Der häufigste
    # Wert fängt einzelne Tippfehler in der Quelle ab.
    return (
        df.groupby("name_norm")["birth_year"]
        .agg(lambda werte: werte.mode().iat[0])
        .reset_index()
    )


# SoFIFA benennt seine Spalten je Spielversion um, deshalb suchen wir per
# Teilstring statt nach exakten Namen.
SOFIFA_ATTRIBUTE = {
    "rating_defending":    ["defending", "defence", "defense"],
    "rating_physical":     ["physic", "physical"],
    "rating_pace":         ["pace", "speed"],
    "rating_tackle":       ["standing_tackle", "tackling", "tackle"],
    "rating_heading":      ["heading", "header"],
    "rating_strength":     ["strength"],
    "rating_aggression":   ["aggression"],
    "rating_interception": ["interception"],
    "rating_overall":      ["overall"],
}


def load_sofifa_ratings() -> pd.DataFrame:
    """Holt Attributwerte als Ersatz für die fehlenden Defensivstatistiken.

    Scheitert der Scraper, läuft der Rest der Aufbereitung trotzdem durch. Die
    Quelle ist ein Bonus, kein Fundament.
    """
    try:
        sofifa = sd.SoFIFA(leagues=UNDERSTAT_LEAGUES, versions="latest")
        df = flatten_columns(sofifa.read_player_ratings().reset_index())
    except Exception as fehler:  # noqa: BLE001
        print(f"SoFIFA nicht erreichbar ({fehler}), Attribute werden übersprungen.")
        return pd.DataFrame(columns=["name_norm"])

    namensspalte = next((c for c in df.columns if c.lower() in ("player", "name")), None)
    if namensspalte is None:
        print("SoFIFA lieferte keine erkennbare Spielerspalte.")
        return pd.DataFrame(columns=["name_norm"])

    ergebnis = pd.DataFrame({"name_norm": df[namensspalte].map(normalize_name)})
    spalten_klein = {c.lower(): c for c in df.columns}
    for ziel, suchbegriffe in SOFIFA_ATTRIBUTE.items():
        treffer = next(
            (original for klein, original in spalten_klein.items()
             if any(begriff in klein for begriff in suchbegriffe)),
            None,
        )
        if treffer is not None:
            ergebnis[ziel] = pd.to_numeric(df[treffer], errors="coerce")

    gefunden = [c for c in ergebnis.columns if c != "name_norm"]
    print(f"SoFIFA-Attribute übernommen: {gefunden or 'keine'}")

    # Ein Spieler kann mehrfach gelistet sein, wir behalten den besten Wert.
    return ergebnis.groupby("name_norm", as_index=False).max()


def load_fbref_extra() -> pd.DataFrame:
    """Basiswerte für Ligen außerhalb der Big 5. Ohne xG, das gibt fbref nicht mehr her."""
    fbref = sd.FBref(leagues=FBREF_LEAGUES, seasons=SEASONS)
    df = flatten_columns(fbref.read_player_season_stats(stat_type="standard").reset_index())

    umbenennung = {
        "player": "name",
        "pos": "position_raw",
        "Playing Time_Min": "minutes",
        "Performance_Gls": "goals",
        "Performance_Ast": "assists",
    }
    df = df.rename(columns={alt: neu for alt, neu in umbenennung.items() if alt in df.columns})
    df = df[~df["position_raw"].astype(str).str.contains("GK", na=False)]
    df["position"] = df["position_raw"].map(
        lambda p: "Abwehr" if "DF" in str(p) else ("Mittelfeld" if "MF" in str(p) else "Sturm")
    )

    for spalte in ["minutes", "goals", "assists"]:
        df[spalte] = pd.to_numeric(df[spalte], errors="coerce")

    df = df[df["minutes"] >= MIN_MINUTES]
    df = add_per90(df, ["goals", "assists"])
    df["source"] = "fbref_basic"
    return df


def spaltenreihenfolge(df: pd.DataFrame) -> list[str]:
    """Sortiert die Spalten so, dass Stammdaten vorne stehen."""
    wunsch = (
        ["name", "team", "league", "season", "position", "source", "birth_year",
         "matches", "minutes"]
        + ZAHLENSPALTEN[2:]
        + [c for c in df.columns if c.endswith("_per90")]
        + [c for c in df.columns if c.startswith("rating_")]
    )
    gesehen, ergebnis = set(), []
    for spalte in wunsch:
        if spalte in df.columns and spalte not in gesehen:
            gesehen.add(spalte)
            ergebnis.append(spalte)
    return ergebnis


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    teile = [load_understat()]
    if USE_FBREF_EXTRA:
        teile.append(load_fbref_extra())
    df = pd.concat(teile, ignore_index=True)
    df["name_norm"] = df["name"].map(normalize_name)

    df = df.merge(load_birth_years(), on="name_norm", how="left")
    if "birth_year" in df.columns:
        quote = df["birth_year"].notna().mean()
        print(f"Geburtsjahr zugeordnet für {quote:.0%} der Spielersaisons")

    if USE_SOFIFA:
        attribute = load_sofifa_ratings()
        if len(attribute.columns) > 1:
            df = df.merge(attribute, on="name_norm", how="left")
            beispiel = [c for c in df.columns if c.startswith("rating_")][0]
            print(f"SoFIFA zugeordnet für {df[beispiel].notna().mean():.0%} der Spielersaisons")

    df = df.drop(columns=["name_norm"])
    df = df[spaltenreihenfolge(df)].reset_index(drop=True)
    df.to_parquet(PLAYERS_PARQUET, index=False)

    print(f"\n{len(df)} Spielersaisons mit {len(df.columns)} Spalten in {PLAYERS_PARQUET}")
    print("Spalten:", list(df.columns))


if __name__ == "__main__":
    main()

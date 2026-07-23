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

# Die Werte, über die Ähnlichkeit berechnet wird. Alles per 90, damit
# Stammspieler und Ergänzungsspieler vergleichbar sind.
KEY_METRICS = [
    "goals_per90", "npg_per90", "assists_per90", "xg_per90", "npxg_per90",
    "xa_per90", "shots_per90", "key_passes_per90",
    "xg_chain_per90", "xg_buildup_per90",
]

# Kurze Achsenbeschriftungen für das Spinnendiagramm in der Oberfläche
METRIC_LABELS = {
    "goals_per90": "Tore",
    "npg_per90": "Tore o. Elfer",
    "assists_per90": "Assists",
    "xg_per90": "xG",
    "npxg_per90": "npxG",
    "xa_per90": "xA",
    "shots_per90": "Schüsse",
    "key_passes_per90": "Key Passes",
    "xg_chain_per90": "Angriffsbet.",
    "xg_buildup_per90": "Aufbau",
}

# Für Diagrammachsen auch die Saisonsummen benennen
CHART_LABELS = {
    **{k: v + " / 90" for k, v in METRIC_LABELS.items()},
    "goals": "Tore",
    "npg": "Tore ohne Elfmeter",
    "assists": "Assists",
    "xg": "xG",
    "npxg": "npxG",
    "xa": "xA",
    "shots": "Schüsse",
    "key_passes": "Key Passes",
    "xg_chain": "xG Chain",
    "xg_buildup": "xG Buildup",
    "minutes": "Minuten",
    "matches": "Spiele",
}

# Übergabepunkte an die Oberfläche: Die Werkzeuge legen hier Daten für
# Diagramme ab, die App liest sie nach der Antwort aus. Ein Rückgabewert
# reicht nicht, weil zwischen Werkzeug und Oberfläche das Sprachmodell sitzt
# und nur Text weitergibt.
LAST_RADAR: dict = {}
LAST_CHART: dict = {}


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
    LAST_CHART.clear()
    LAST_RADAR.clear()
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

    # Ranglisten lassen sich als Balken schneller erfassen als als Tabelle,
    # deshalb bekommt die Oberfläche die Daten fürs Diagramm mit.
    LAST_CHART.update({
        "metrik": CHART_LABELS.get(sort_by, sort_by),
        "spalte": sort_by,
        "eintraege": [
            {"name": zeile["name"], "wert": float(zeile[sort_by])}
            for _, zeile in treffer.iterrows()
        ],
    })

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


@tool
def similar_players(name: str, limit: int = 5) -> str:
    """Findet Spieler, die einem Referenzspieler statistisch ähneln.

    Verglichen werden alle Leistungswerte pro 90 Minuten, nicht nur einer.
    Kandidaten sind Feldspieler derselben Positionsgruppe und Saison mit
    genug Einsatzzeit. Der Score reicht von 100 (nahezu identisches Profil)
    bis 0.

    name: Namensteil des Referenzspielers, etwa 'Grifo'
    limit: Anzahl der ähnlichsten Spieler in der Antwort
    """
    LAST_RADAR.clear()
    LAST_CHART.clear()
    df = load_players()

    treffer = df[df["name"].str.contains(name, case=False, na=False)]
    if treffer.empty:
        return f"Zu '{name}' ist niemand im Datensatz."

    # Bei mehreren Saisons zählt die aktuellste, bei mehreren Spielern der
    # mit den meisten Minuten. Wen wir gewählt haben, steht in der Antwort.
    treffer = treffer.sort_values(["season", "minutes"], ascending=False)
    referenz = treffer.iloc[0]

    metriken = [m for m in KEY_METRICS if m in df.columns]
    pool = df[
        (df["position"] == referenz["position"])
        & (df["season"] == referenz["season"])
        & (df["minutes"] >= 450)
    ].dropna(subset=metriken).copy()

    if referenz["name"] not in pool["name"].values:
        pool = pd.concat([pool, referenz.to_frame().T], ignore_index=True)

    if len(pool) < 3:
        return "Der Vergleichspool ist zu klein für eine sinnvolle Ähnlichkeitssuche."

    # Erst standardisieren, dann Abstände messen. Ohne diesen Schritt würden
    # Werte mit großer Spannweite wie Schüsse alles andere übertönen.
    z = (pool[metriken] - pool[metriken].mean()) / pool[metriken].std().replace(0, 1)
    z_referenz = z[pool["name"] == referenz["name"]].iloc[0]

    # Mittlere absolute Abweichung in Standardabweichungen, linear auf einen
    # Score abgebildet: 0 Abweichung ergibt 100, ab 3 Standardabweichungen 0.
    # Bewusst so schlicht, damit sich der Score im Gespräch erklären lässt.
    abweichung = (z - z_referenz).abs().mean(axis=1)
    pool["score"] = ((1 - abweichung / 3).clip(lower=0) * 100).round(1)

    aehnliche = (
        pool[pool["name"] != referenz["name"]]
        .sort_values("score", ascending=False)
        .head(limit)
    )

    # Für das Diagramm eignen sich Perzentile besser als Rohwerte, weil alle
    # Achsen dieselbe Skala von 0 bis 100 bekommen.
    perzentile = pool[metriken].rank(pct=True) * 100
    def profil(zeile_index) -> dict:
        return {METRIC_LABELS.get(m, m): round(float(perzentile.loc[zeile_index, m]), 1)
                for m in metriken}

    referenz_index = pool[pool["name"] == referenz["name"]].index[0]
    LAST_RADAR.update({
        "referenz": {"name": referenz["name"], "werte": profil(referenz_index)},
        "spieler": [
            {"name": zeile["name"], "werte": profil(index)}
            for index, zeile in aehnliche.head(3).iterrows()
        ],
    })

    kopf = (
        f"Referenz: {referenz['name']} ({referenz['team']}, {referenz['season']}, "
        f"Position {referenz['position']}"
        + (f", {int(referenz['age'])} Jahre" if pd.notna(referenz.get("age")) else "")
        + f"). Vergleichspool: {len(pool)} Spieler derselben Position und Saison "
        f"mit mindestens 450 Minuten.\n\n"
    )

    # Das Profil der Referenz gehört mit in die Antwort: die Werte selbst und
    # ihre Einordnung als Perzentil im Pool. Erst dadurch versteht man, worauf
    # sich die Ähnlichkeit der anderen überhaupt bezieht.
    profilzeilen = ["Kennwerte von " + referenz["name"] + " (je 90 Minuten, in Klammern das Perzentil im Pool):"]
    for m in metriken:
        wert = referenz[m]
        perzentil = perzentile.loc[referenz_index, m]
        profilzeilen.append(
            f"- {METRIC_LABELS.get(m, m)}: {wert:.2f} (Top {100 - perzentil:.0f}%)"
            if perzentil >= 50 else
            f"- {METRIC_LABELS.get(m, m)}: {wert:.2f} ({perzentil:.0f}. Perzentil)"
        )
    profil_text = "\n".join(profilzeilen) + "\n\n"

    spalten = ["name", "team", "league", "age", "minutes", "score"]
    tabelle = aehnliche[[s for s in spalten if s in aehnliche.columns]].to_markdown(index=False)
    return kopf + profil_text + "Die ähnlichsten Spieler:\n\n" + tabelle


ALL_TOOLS = [query_players, player_profile, list_metrics, similar_players]

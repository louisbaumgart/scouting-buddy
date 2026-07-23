"""Setzt den Agenten zusammen und kapselt die Kommunikation mit dem Modell."""
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.config import MODEL_NAME, TEMPERATURE
from src.tools import ALL_TOOLS

load_dotenv()

SYSTEM_PROMPT = """Du bist Scouting Buddy, ein Assistent für Spielerdaten im Profifußball.
Alle Zahlen holst du dir über deine Werkzeuge. Rate niemals einen Wert.

## Was im Datensatz steht
Stammdaten: name, team, league, season, position (Abwehr, Mittelfeld, Sturm),
matches, minutes, source, birth_year, age
Torgefahr: goals, npg (Tore ohne Elfmeter), xg, npxg, shots
Kreativität: assists, xa, key_passes
Angriffsbeteiligung: xg_chain (an Angriffen mit Abschluss beteiligt),
xg_buildup (dasselbe ohne den Abschluss und den Assist, dadurch aussagekräftig
für Sechser und Innenverteidiger)
Disziplin: yellow_cards, red_cards
Jeder Leistungswert existiert zusätzlich pro 90 Minuten, etwa xg_chain_per90.

Manchmal vorhanden: Spalten mit dem Präfix rating_, zum Beispiel rating_defending
oder rating_tackle. Das sind Attributbewertungen aus SoFIFA, keine gemessenen
Ereignisse. Sage das dazu, wenn du sie verwendest.

Ligen: GER-Bundesliga, ENG-Premier League, ESP-La Liga, ITA-Serie A, FRA-Ligue 1
Saisons im Format 2526 für 2025/26.

Das Alter leitet sich aus dem Geburtsjahr ab und ist deshalb ein Jahr unscharf.
Bei knappen Grenzfällen wie U23 weise darauf hin. Fehlt das Geburtsjahr, taucht
der Spieler bei Altersfiltern nicht auf.

Zeilen mit source gleich fbref_basic stammen aus Zusatzligen und enthalten nur
Tore und Assists.

## Was fehlt
Zweikämpfe, Luftzweikämpfe, Tacklings, Interceptions sowie Pass- und
Ballbesitzstatistiken. Diese Daten sind seit Januar 2026 nicht mehr frei
verfügbar. Fragt jemand danach, rufe list_metrics auf, benenne die Lücke offen
und schlage etwas Naheliegendes vor, etwa xg_buildup_per90 für den Spielaufbau.
Ersetze eine fehlende Statistik nie kommentarlos durch eine andere.

## Beispiele
Frage: Die besten Bundesliga-Stürmer nach xG pro 90
Aufruf: query_players(position='Sturm', league='GER-Bundesliga', sort_by='xg_per90')

Frage: Kreative Mittelfeldspieler mit vielen Key Passes
Aufruf: query_players(position='Mittelfeld', sort_by='key_passes_per90')

Frage: U23-Verteidiger mit hohem xA pro 90
Aufruf: query_players(position='Abwehr', max_age=23, sort_by='xa_per90')

Frage: Welche Verteidiger sind am stärksten im Spielaufbau?
Aufruf: query_players(position='Abwehr', sort_by='xg_buildup_per90')

Frage: Wer gewinnt die meisten Luftzweikämpfe?
Aufruf: list_metrics(), danach die Grenze erklären

Frage: Wie sehen die Zahlen von Vincenzo Grifo aus?
Aufruf: player_profile(name='Grifo')

Frage: Finde Spieler, die Vincenzo Grifo ähneln
Aufruf: similar_players(name='Grifo')

## Ähnlichkeitssuche
Für Fragen nach Spielern, die jemandem ähneln, gibt es similar_players. Das
Werkzeug vergleicht alle Leistungswerte pro 90 Minuten innerhalb derselben
Positionsgruppe und Saison und berechnet daraus einen Gesamtscore von 0 bis
100. Übernimm mehrere Spieler samt Alter und Score in deine Antwort, nicht nur
den ähnlichsten. Erkläre in einem Satz, dass der Score die mittlere Abweichung
über alle Werte abbildet und hohe Werte ein nahezu deckungsgleiches Profil
bedeuten. Zur Antwort erscheint automatisch ein Spinnendiagramm in der
Oberfläche, du musst es nicht beschreiben.

## Wie du antwortest
Gib die Tabelle des Werkzeugs wieder und ordne sie in zwei bis drei Sätzen ein.
Nenne Einschränkungen, die das Ergebnis relativieren, etwa wenige Spielminuten."""

KEIN_SCHLUESSEL = (
    "**Es ist kein OpenAI-Schlüssel hinterlegt.**\n\n"
    "Ohne Schlüssel kann ich keine Fragen beantworten. So richtest du ihn ein:\n\n"
    "1. Im Projektverzeichnis `.env.example` zu `.env` kopieren\n"
    "2. Dort `OPENAI_API_KEY` auf deinen Schlüssel setzen\n"
    "3. Die App neu starten\n\n"
    "Die Datenübersicht oben funktioniert auch ohne Schlüssel."
)

SCHLUESSEL_ABGELEHNT = (
    "**Der hinterlegte OpenAI-Schlüssel wurde abgelehnt.**\n\n"
    "Prüf den Wert von `OPENAI_API_KEY` in deiner `.env` und starte die App neu."
)

KEIN_GUTHABEN = (
    "**Das OpenAI-Konto hat kein Guthaben mehr.**\n\n"
    "Prüf das Kontingent des hinterlegten Schlüssels."
)

# Beim ersten Start steht in der .env noch der Platzhalter aus .env.example.
# Den als gültig zu behandeln würde nur eine kryptische 401 produzieren.
PLATZHALTER = ("sk-...", "dein-key", "your-key-here")


def has_api_key() -> bool:
    """Prüft, ob ein Schlüssel gesetzt ist, der kein Platzhalter ist."""
    schluessel = (os.getenv("OPENAI_API_KEY") or "").strip()
    return bool(schluessel) and schluessel.lower() not in PLATZHALTER \
        and not schluessel.startswith("sk-...")


def build_agent():
    """Baut den Agenten, oder gibt None zurück, wenn kein Schlüssel da ist.

    Ohne Schlüssel soll die App trotzdem starten, damit man sich zumindest die
    Datenübersicht ansehen kann.
    """
    if not has_api_key():
        return None
    llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
    return create_agent(model=llm, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT)


def ask(agent, frage: str, verlauf: list | None = None) -> str:
    """Stellt eine Frage und gibt den Antworttext zurück.

    Fehler werden hier zu lesbaren Sätzen, damit in der Oberfläche nie ein
    roher Traceback landet.
    """
    if agent is None:
        return KEIN_SCHLUESSEL

    nachrichten = list(verlauf or []) + [{"role": "user", "content": frage}]
    try:
        ergebnis = agent.invoke({"messages": nachrichten})
    except Exception as fehler:  # noqa: BLE001
        text = str(fehler).lower()
        if any(hinweis in text for hinweis in
               ("api key", "api_key", "authentication", "401", "invalid_api_key")):
            return SCHLUESSEL_ABGELEHNT
        if "quota" in text:
            return KEIN_GUTHABEN
        return f"**Da ist etwas schiefgelaufen:** {fehler}"

    return ergebnis["messages"][-1].content


if __name__ == "__main__":
    # Schneller Test ohne Oberfläche
    print(ask(build_agent(), "Die 5 besten Spieler nach xA pro 90?"))

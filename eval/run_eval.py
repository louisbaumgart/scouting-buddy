"""Automatisierter Evaluationslauf für Scouting Buddy.

Aufruf aus dem Projektverzeichnis:

    python -m eval.run_eval              alle Fälle
    python -m eval.run_eval 1 5 9        nur einzelne Fälle

Bewertet wird die Werkzeugwahl, nicht der Antworttext. Welches Werkzeug mit
welchen Parametern aufgerufen wurde, steht eindeutig fest und lässt sich
vergleichen. Ob eine Formulierung gelungen ist, lässt sich das nicht.

Jeder Fall kostet einen Modellaufruf. Ein voller Lauf sind also so viele
Anfragen, wie es Fälle gibt.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.cases import FAELLE, Testfall
from src.agent import build_agent, has_api_key
from src.config import PLAYERS_PARQUET

REPORT = Path(__file__).resolve().parent / "report.md"

OK = "ok"
TEILWEISE = "teilweise"
FEHLERHAFT = "fehlerhaft"
MANUELL = "manuell prüfen"


def sammle_werkzeugaufrufe(nachrichten: list) -> list[dict]:
    """Zieht alle Werkzeugaufrufe aus dem Nachrichtenverlauf.

    Das Modell kann mehrfach zugreifen, etwa erst list_metrics und dann
    query_players. Deshalb sammeln wir alle Aufrufe statt nur den ersten.
    """
    aufrufe = []
    for nachricht in nachrichten:
        for aufruf in getattr(nachricht, "tool_calls", None) or []:
            aufrufe.append({"name": aufruf["name"], "args": aufruf.get("args", {})})
    return aufrufe


def werte_gleich(sollwert, istwert) -> bool:
    """Vergleicht zwei Parameterwerte großzügig.

    Das Modell liefert Zahlen mal als 900 und mal als 900.0, Text mal groß und
    mal klein geschrieben. Beides soll nicht als Fehler zählen.
    """
    try:
        return float(sollwert) == float(istwert)
    except (TypeError, ValueError):
        return str(sollwert).strip().lower() == str(istwert).strip().lower()


def parameter_stimmen(erwartet: dict, tatsaechlich: dict) -> tuple[bool, list[str]]:
    """Prüft, ob alle erwarteten Parameter gesetzt sind.

    Zusätzliche Parameter sind erlaubt. Wer bei der Frage nach Bundesliga-
    Stürmern noch ein Limit setzt, hat nichts falsch gemacht.
    """
    abweichungen = []
    for schluessel, sollwert in erwartet.items():
        istwert = tatsaechlich.get(schluessel)
        if istwert is None:
            abweichungen.append(f"{schluessel} fehlt")
        elif not werte_gleich(sollwert, istwert):
            abweichungen.append(f"{schluessel}={istwert} statt {sollwert}")
    return not abweichungen, abweichungen


def bewerte(fall: Testfall, aufrufe: list[dict]) -> tuple[str, str]:
    """Vergibt eine Note und begründet sie in einem Satz."""
    namen = [aufruf["name"] for aufruf in aufrufe]

    # Fälle ohne erwartetes Werkzeug: Das Modell soll nachfragen oder ablehnen.
    if not fall.erwartete_werkzeuge:
        if namen:
            return FEHLERHAFT, f"kein Werkzeug erwartet, aufgerufen wurde {', '.join(namen)}"
        return MANUELL, "kein Werkzeug aufgerufen, Antwort inhaltlich prüfen"

    passende = [a for a in aufrufe if a["name"] in fall.erwartete_werkzeuge]
    if not passende:
        erwartet = " oder ".join(fall.erwartete_werkzeuge)
        return FEHLERHAFT, f"{erwartet} erwartet, aufgerufen wurde {', '.join(namen) or 'nichts'}"

    if not fall.erwartete_parameter:
        return (MANUELL if fall.manuell else OK), "Werkzeug korrekt gewählt"

    # Bei mehreren Treffern zählt der beste, sonst bestrafen wir zusätzliche
    # Nachfassaufrufe des Modells.
    bestes_ergebnis = (False, ["kein Aufruf ausgewertet"])
    for aufruf in passende:
        stimmt, abweichungen = parameter_stimmen(fall.erwartete_parameter, aufruf["args"])
        if stimmt:
            bestes_ergebnis = (True, [])
            break
        if len(abweichungen) < len(bestes_ergebnis[1]):
            bestes_ergebnis = (False, abweichungen)

    if bestes_ergebnis[0]:
        return (MANUELL if fall.manuell else OK), "Werkzeug und Parameter korrekt"
    return TEILWEISE, "Werkzeug korrekt, aber " + "; ".join(bestes_ergebnis[1])


def fuehre_fall_aus(agent, fall: Testfall) -> dict:
    """Stellt eine Frage ohne Gesprächsverlauf, damit die Fälle unabhängig bleiben."""
    try:
        ergebnis = agent.invoke({"messages": [{"role": "user", "content": fall.frage}]})
    except Exception as fehler:  # noqa: BLE001
        return {
            "fall": fall,
            "note": FEHLERHAFT,
            "begruendung": f"Aufruf fehlgeschlagen: {fehler}",
            "aufrufe": [],
            "antwort": "",
        }

    aufrufe = sammle_werkzeugaufrufe(ergebnis["messages"])
    note, begruendung = bewerte(fall, aufrufe)
    return {
        "fall": fall,
        "note": note,
        "begruendung": begruendung,
        "aufrufe": aufrufe,
        "antwort": ergebnis["messages"][-1].content,
    }


def formatiere_aufrufe(aufrufe: list[dict]) -> str:
    if not aufrufe:
        return "keine"
    return "; ".join(
        f"{a['name']}({', '.join(f'{k}={v}' for k, v in a['args'].items())})"
        for a in aufrufe
    )


def schreibe_report(ergebnisse: list[dict]) -> None:
    """Legt den Lauf als Markdown ab, damit er in die Ausarbeitung wandern kann."""
    automatisch = [e for e in ergebnisse if e["note"] in (OK, TEILWEISE, FEHLERHAFT)]
    bestanden = [e for e in automatisch if e["note"] == OK]
    quote = len(bestanden) / len(automatisch) if automatisch else 0

    zeilen = [
        "# Evaluationslauf",
        "",
        f"Durchgeführt am {datetime.now():%d.%m.%Y um %H:%M} Uhr.",
        "",
        f"Automatisch bewertet: {len(bestanden)} von {len(automatisch)} Fällen "
        f"korrekt ({quote:.0%}). Zusätzlich "
        f"{len(ergebnisse) - len(automatisch)} Fälle zur manuellen Prüfung.",
        "",
        "| # | Frage | Note | Werkzeugaufruf | Anmerkung |",
        "|---|-------|------|----------------|-----------|",
    ]

    for e in ergebnisse:
        fall = e["fall"]
        zeilen.append(
            f"| {fall.nummer} | {fall.frage} | {e['note']} | "
            f"`{formatiere_aufrufe(e['aufrufe'])}` | {e['begruendung']} |"
        )

    # Ohne den Antworttext laesst sich ein Fehlschlag nicht diagnostizieren.
    # Deshalb landen fehlerhafte Faelle hier genauso im Bericht wie die
    # manuell zu bewertenden.
    auffaellig = [e for e in ergebnisse if e["note"] != OK]
    if auffaellig:
        zeilen += ["", "## Antworten im Wortlaut", ""]
        for e in auffaellig:
            fall = e["fall"]
            zeilen += [f"### {fall.nummer}. {fall.frage}", ""]
            if e["note"] == MANUELL:
                zeilen += [
                    f"Worauf achten: {fall.worauf_achten or 'inhaltliche Angemessenheit'}",
                    "",
                ]
            else:
                zeilen += [f"Bewertet als {e['note']}: {e['begruendung']}", ""]
            zeilen += [
                "Antwort des Assistenten:",
                "",
                "> " + (e["antwort"] or "keine Antwort").replace("\n", "\n> "),
                "",
            ]

    REPORT.write_text("\n".join(zeilen), encoding="utf-8")


def main() -> int:
    if not PLAYERS_PARQUET.exists():
        print("Es liegen keine Daten vor. Führ zuerst 'python -m src.data_prep' aus.")
        return 1

    if not has_api_key():
        print(
            "Es ist kein OpenAI-Schlüssel hinterlegt, der Lauf braucht aber einen.\n"
            "Kopier '.env.example' zu '.env' und trag OPENAI_API_KEY dort ein."
        )
        return 1

    agent = build_agent()

    # Optional lassen sich einzelne Fälle über ihre Nummer auswählen.
    gewuenscht = {int(a) for a in sys.argv[1:] if a.isdigit()}
    faelle = [f for f in FAELLE if not gewuenscht or f.nummer in gewuenscht]

    print(f"Starte {len(faelle)} Testfälle\n")
    ergebnisse = []
    for fall in faelle:
        ergebnis = fuehre_fall_aus(agent, fall)
        ergebnisse.append(ergebnis)
        print(f"{fall.nummer:>2}. {ergebnis['note']:<14} {fall.frage}")
        if ergebnis["note"] in (TEILWEISE, FEHLERHAFT):
            print(f"    {ergebnis['begruendung']}")

    schreibe_report(ergebnisse)

    automatisch = [e for e in ergebnisse if e["note"] != MANUELL]
    bestanden = [e for e in automatisch if e["note"] == OK]
    print(f"\n{len(bestanden)} von {len(automatisch)} automatisch bewerteten Fällen korrekt")
    print(f"Bericht geschrieben nach {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

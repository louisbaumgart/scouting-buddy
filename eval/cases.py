"""Die Testfälle des Evaluationslaufs.

Ein Fall besteht aus der Frage, dem erwarteten Werkzeug und den Parametern,
die dabei mindestens gesetzt sein müssen. Geprüft wird also nicht der
Antworttext, sondern die Entscheidung des Modells. Das ist der Teil, der sich
überhaupt maschinell bewerten lässt.

Fälle mit manuell=True kann kein Skript bewerten. Dort geht es darum, ob eine
Rückfrage kommt oder eine Grenze erklärt wird. Der Lauf sammelt die Antwort
ein, die Note vergibst du selbst.
"""
from dataclasses import dataclass, field


@dataclass
class Testfall:
    nummer: int
    frage: str
    erwartete_werkzeuge: list[str]
    erwartete_parameter: dict = field(default_factory=dict)
    manuell: bool = False
    worauf_achten: str = ""


FAELLE = [
    # Eindeutige Zuordnung. Scheitert hier etwas, liegt es am Systemprompt.
    Testfall(
        1, "Beste Bundesliga-Stürmer nach xG pro 90",
        ["query_players"],
        {"position": "Sturm", "league": "GER-Bundesliga", "sort_by": "xg_per90"},
    ),
    Testfall(
        2, "Kreative Mittelfeldspieler mit vielen Key Passes",
        ["query_players"],
        {"position": "Mittelfeld", "sort_by": "key_passes_per90"},
    ),
    Testfall(
        3, "Zeig mir die Zahlen von Vincenzo Grifo",
        ["player_profile"],
        {"name": "Grifo"},
    ),
    Testfall(
        4, "Top-5-Vorlagengeber der Premier League",
        ["query_players"],
        {"league": "ENG-Premier League", "limit": 5},
    ),
    Testfall(
        5, "Verteidiger mit hohem xA pro 90, mindestens 900 Minuten",
        ["query_players"],
        {"position": "Abwehr", "sort_by": "xa_per90", "min_minutes": 900},
    ),

    # Altersfilter, seit das Geburtsjahr aus fbref dazukommt.
    Testfall(
        6, "U23-Mittelfeldspieler mit den meisten Key Passes",
        ["query_players"],
        {"position": "Mittelfeld", "max_age": 23, "sort_by": "key_passes_per90"},
        worauf_achten="Wird die Unschärfe von einem Jahr erwähnt?",
    ),
    Testfall(
        7, "Welche Stürmer über 30 treffen noch am besten?",
        ["query_players"],
        {"position": "Sturm", "min_age": 30},
    ),
    Testfall(
        8, "Die größten Talente der Bundesliga",
        ["query_players"],
        {"league": "GER-Bundesliga"},
        manuell=True,
        worauf_achten="Wird eine Altersgrenze gesetzt und begründet?",
    ),

    # Hält das Modell xGChain und xGBuildup auseinander?
    Testfall(
        9, "Welche Verteidiger sind am stärksten im Spielaufbau?",
        ["query_players"],
        {"position": "Abwehr", "sort_by": "xg_buildup_per90"},
    ),
    Testfall(
        10, "Wer ist an den meisten Angriffen beteiligt?",
        ["query_players"],
        {"sort_by": "xg_chain_per90"},
    ),

    # Der wichtigste Block: Fragen, die der Datensatz nicht beantworten kann.
    Testfall(
        11, "Wer gewinnt die meisten Luftzweikämpfe?",
        ["list_metrics"],
        manuell=True,
        worauf_achten="Wird die Lücke benannt statt eine andere Statistik untergeschoben?",
    ),
    Testfall(
        12, "Welche Spieler haben die beste Zweikampfquote?",
        ["list_metrics"],
        manuell=True,
        worauf_achten="Wird der Grund genannt, warum es die Daten nicht gibt?",
    ),
    Testfall(
        13, "Welche Statistiken kannst du auswerten?",
        ["list_metrics"],
    ),
    Testfall(
        14, "Zeig mir die besten Torhüter",
        ["query_players", "list_metrics"],
        manuell=True,
        worauf_achten="Torhüter sind bewusst ausgeschlossen, steht aber nicht im Prompt.",
    ),
    Testfall(
        15, "Wer sind aktuell die besten Spieler?",
        [],
        manuell=True,
        worauf_achten="Kommt eine Rückfrage nach dem Kriterium?",
    ),
    Testfall(
        16, "Wie viele Tore schießt Musiala nächste Saison?",
        [],
        manuell=True,
        worauf_achten="Wird die Prognose abgelehnt, statt Zahlen zu erfinden?",
    ),
]

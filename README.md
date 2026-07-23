# ⚽ Scouting Buddy

Ein digitaler Scouting-Assistent, der natürlichsprachliche Fragen
zu Spielerstatistiken per **Tool-Use / Function Calling** in strukturierte
Datenabfragen übersetzt. Umgesetzt mit **LangChain, OpenAI API und Streamlit**.

## Was der Assistent kann

| Frage (Beispiel) | Werkzeug | Antwort |
|---|---|---|
| "Beste Bundesliga-Stürmer nach xG pro 90" | `query_players` | Tabelle + Balkendiagramm |
| "U23-Mittelfeldspieler mit den meisten Key Passes" | `query_players` | Tabelle + Balkendiagramm |
| "Wie sehen die Zahlen von Vincenzo Grifo aus?" | `player_profile` | alle Saisonwerte des Spielers |
| "Finde Spieler, die Vincenzo Grifo ähneln" | `similar_players` | Kennwerte, Score-Rangliste + Spinnendiagramm |
| "Welche Statistiken kannst du auswerten?" | `list_metrics` | Übersicht inkl. der Lücken |
| "Wer gewinnt die meisten Luftzweikämpfe?" | `list_metrics` | benennt die fehlenden Daten, statt zu raten |

Filtern lässt sich nach Positionsgruppe, Liga, Verein, Saison, Einsatzminuten
und Alter (etwa U23), sortieren nach jeder Kennzahl im Datensatz.

**Diagramme:** Ranglisten erscheinen zusätzlich als horizontales Balkendiagramm
in den Farben der Oberfläche. Die Ähnlichkeitssuche zeigt ein Spinnendiagramm,
in dem der Referenzspieler und die drei ähnlichsten Profile als Perzentile
übereinanderliegen.

### Ähnlichkeitssuche

`similar_players` vergleicht einen Referenzspieler über alle zehn
Leistungswerte pro 90 Minuten mit Feldspielern derselben Positionsgruppe und
Saison (mindestens 450 Minuten). Die Werte werden standardisiert, aus der
mittleren Abweichung entsteht ein Gesamtscore von 0 bis 100. Die Antwort nennt
zuerst die Kennwerte des angefragten Spielers samt Einordnung im Pool, dann
die ähnlichsten Spieler mit Alter und Score.

## Architektur

```
Nutzer → Streamlit-Chat → LangChain Agent (create_agent, GPT-4o)
           → Tools: query_players / player_profile / list_metrics / similar_players
                    (Pandas auf Parquet)
           → Antwort: Tabelle + Einordnung, dazu Balken- oder Spinnendiagramm
```

Techniken: Tool-Use, Few-shot Prompting (im System-Prompt), Evaluation über
ein Testset (`eval/`).

Das Modell schreibt bewusst keinen freien Code, sondern wählt eine Funktion und
füllt getypte Parameter. Das ist sicherer und liefert verlässlichere Ergebnisse,
weil ungültige Eingaben sofort auffallen. Die Diagramme entstehen nicht im
Sprachmodell: Die Werkzeuge legen die Daten in einem Übergabepunkt ab, die
Oberfläche liest ihn nach der Antwort aus und rendert mit Plotly.

## Datengrundlage

- **Understat** (Primärquelle, via `soccerdata`): xG, npxG, xA, xGChain,
  xGBuildup, Shots, Key Passes, Karten für die Big-5-Ligen. Alle Leistungswerte
  zusätzlich als per-90.
- **fbref**: liefert das Geburtsjahr, aus dem zur Laufzeit das Alter berechnet
  wird. Damit funktionieren Filter wie U23. Da nur das Jahr vorliegt, ist die
  Altersangabe ein Jahr unscharf.
- **fbref, optional** (`USE_FBREF_EXTRA=True` in `src/config.py`): Basisdaten
  (Tore/Assists/Minuten) für weitere Ligen, z. B. Eredivisie oder Championship.
- **SoFIFA, optional** (`USE_SOFIFA=True`): Attributwerte wie Zweikampf,
  Kopfball oder Stärke. Das sind Einschätzungen, keine gemessenen Ereignisse,
  und im Datensatz am Präfix `rating_` erkennbar.

**Kontext:** fbref hat im Januar 2026 seine Advanced Stats verloren (Opta hat
den Vertrag gekündigt). Frei verfügbare xG-Daten gibt es daher nur noch für
wenige Ligen (Understat: Big 5 + RUS). Gemessene Defensivwerte wie Zweikämpfe,
Luftzweikämpfe, Tacklings und Interceptions sind gar nicht mehr frei zu
bekommen. Das Werkzeug `list_metrics` macht diese Lücke im Dialog sichtbar,
statt sie durch eine andere Statistik zu ersetzen. Eine bewusst reflektierte
Limitation der Datengrundlage.

## Setup

```bash
# 1. Virtuelle Umgebung
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. API-Key hinterlegen
cp .env.example .env             # dann OPENAI_API_KEY eintragen

# 3. Daten einmalig laden
python -m src.data_prep

# 4. App starten
python -m streamlit run src/app.py

# 5. App beenden
control + c
```

Schneller Test ohne UI: `python -m src.agent`

Ohne hinterlegten Schlüssel startet die App trotzdem. Die Datenübersicht bleibt
nutzbar, auf Fragen antwortet der Assistent mit einem Hinweis auf die `.env`.
Auch ein abgelehnter Schlüssel oder fehlendes Guthaben führen zu einer
erklärenden Antwort im Chat statt zu einem Traceback.

> Hinweis: Das Projekt nutzt die **LangChain-1.x-API** (`create_agent`).
> Die ältere Kombination `AgentExecutor` + `create_tool_calling_agent` liegt seit
> LangChain 1.0 im Paket `langchain-classic` und wird hier bewusst nicht verwendet.

## Evaluation

Der Lauf stellt dem Assistenten eine feste Liste von Fragen und prüft, welches
Werkzeug er mit welchen Parametern aufruft. Bewertet wird also die Entscheidung
des Modells, nicht die Formulierung der Antwort. Zusätzliche Parameter sind
erlaubt, Zahlen werden numerisch verglichen.

```bash
python -m eval.run_eval          # alle Fälle
python -m eval.run_eval 1 5 9    # nur einzelne Fälle
```

Das Ergebnis landet in `eval/report.md`: Trefferquote, eine Tabelle mit allen
Werkzeugaufrufen und die Volltexte der Antworten, die von Hand zu beurteilen
sind. Fälle, bei denen es auf eine Rückfrage oder eine erklärte Grenze ankommt,
sind in `eval/cases.py` als `manuell` markiert. Das Skript sammelt dort die
Antwort ein, die Bewertung nimmst du selbst vor. Auch fehlerhafte Fälle stehen
mit ihrem Antworttext im Bericht, damit sich die Ursache nachvollziehen lässt.

Jeder Fall kostet einen Modellaufruf. `eval/test_questions.md` enthält
dieselben Fälle in einer Fassung zum Abhaken von Hand.

## Projektstruktur

```
├── .streamlit/
│   └── config.toml        # Farbschema der Oberfläche
├── src/
│   ├── config.py          # Ligen, Saisons, Modell, Datenquellen-Schalter
│   ├── data_prep.py       # Understat + fbref + SoFIFA → bereinigtes Parquet
│   ├── tools.py           # strukturierte Tools inkl. Ähnlichkeitssuche
│   ├── agent.py           # Agent, System-Prompt, Fehlerbehandlung
│   └── app.py             # Streamlit-Chat mit Balken- und Spinnendiagramm
├── eval/
│   ├── cases.py           # Testfälle als Datenobjekte
│   ├── run_eval.py        # automatisierter Lauf, schreibt report.md
│   └── test_questions.md  # dieselben Fälle zum manuellen Abhaken
├── data/                  # players.parquet, nicht im Repo
├── requirements.txt
├── .env.example
└── .gitignore
```

## Mögliche Erweiterungen

- RAG über Scouting-Berichte als zweite Technik
- Exaktes Geburtsdatum über Transfermarkt, um die Unschärfe beim Alter zu beheben
- Mehrere Evaluationsläufe vergleichen, um die Stabilität der Werkzeugwahl zu messen
- Ähnlichkeitssuche über Saisons hinweg, etwa um den Nachfolger eines Abgangs zu finden
- Gewichtung der Kennzahlen in der Ähnlichkeitssuche, z. B. Kreativität stärker als Torgefahr

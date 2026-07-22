# ⚽ Scouting Buddy

Ein digitaler Scouting-Assistent, der natürlichsprachliche Fragen
zu Spielerstatistiken per **Tool-Use / Function Calling** in strukturierte
Datenabfragen übersetzt. Umgesetzt mit **LangChain, OpenAI API und Streamlit**.

## Architektur

```
Nutzer → Streamlit-Chat → LangChain Agent (create_agent, GPT-4o)
           → Tools: query_players / player_profile (Pandas auf Parquet)
           → Antwort: Tabelle + Einordnung
```

Techniken: Tool-Use, Few-shot Prompting (im System-Prompt), Evaluation über Testset (`eval/`).

## Datengrundlage

- **Understat** (Primärquelle, via `soccerdata`): xG, npxG, xA, Shots, Key Passes
  für die Big-5-Ligen. Alle Werte zusätzlich als per-90.
- **fbref** (optional, `USE_FBREF_EXTRA=True` in `src/config.py`): Basisdaten
  (Tore/Assists/Minuten) für weitere Ligen, z. B. Eredivisie oder Championship.
- **Kontext:** fbref hat im Januar 2026 seine Advanced Stats
  verloren (Opta hat den Vertrag gekündigt). Frei verfügbare xG-Daten gibt es
  daher nur noch für wenige Ligen (Understat: Big 5 + RUS) – eine bewusst
  reflektierte Limitation der Datengrundlage.

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

#5. App beenden
control + c
```

Schneller Test ohne UI: `python -m src.agent`

> Hinweis: Das Projekt nutzt die **LangChain-1.x-API** (`create_agent`).
> Die ältere Kombination `AgentExecutor` + `create_tool_calling_agent` liegt seit
> LangChain 1.0 im Paket `langchain-classic` und wird hier bewusst nicht verwendet.

## GitHub-Setup

```bash
git init
git add .
git commit -m "Initial commit: Scouting Buddy Grundgerüst"

# Repo auf github.com anlegen (ohne README), dann:
git remote add origin https://github.com/<DEIN-USER>/scouting-buddy.git
git branch -M main
git push -u origin main
```

**Wichtig:** `.env` (API-Key) und `data/*.parquet` sind über `.gitignore`
ausgeschlossen – der Key darf nie ins Repo.

## Projektstruktur

```
├── src/
│   ├── config.py      # Ligen, Saisons, Modell, Datenquellen-Schalter
│   ├── data_prep.py   # Understat (+ optional fbref) → bereinigtes Parquet
│   ├── tools.py       # strukturierte Tools (Function Calling)
│   ├── agent.py       # Agent + System-Prompt (Data Dictionary, Few-shots)
│   └── app.py         # Streamlit-Chat
├── eval/test_questions.md
├── requirements.txt
└── .env.example
```

## Mögliche Erweiterungen

- Spieler-Alter aus fbref-Basisdaten oder Transfermarkt anreichern (für U23-Filter)
- Plot-Tool (Scatter xG vs. Tore) als drittes Tool
- RAG über Scouting-Berichte als zweite Technik

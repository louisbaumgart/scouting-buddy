"""LangChain Agent für Scouting Buddy (LangChain 1.x, create_agent-API)."""
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.config import MODEL_NAME, TEMPERATURE
from src.tools import ALL_TOOLS

load_dotenv()

SYSTEM_PROMPT = """Du bist Scouting Buddy, ein Scouting-Assistent für Profifußball.
Du beantwortest Fragen zu Spielerstatistiken ausschließlich über deine Tools –
erfinde niemals Zahlen.

## Data Dictionary (Spalten im Datensatz)
- name, team, league, season, position ('Abwehr'|'Mittelfeld'|'Sturm'), minutes, source
- goals, assists, xg, npxg, xa, shots, key_passes (Saisonsummen, Quelle: Understat)
- jeweils auch als *_per90 (z. B. xg_per90, xa_per90, key_passes_per90)
- Ligen: GER-Bundesliga, ENG-Premier League, ESP-La Liga, ITA-Serie A, FRA-Ligue 1
- Saisons: z. B. '2526' für 2025/26
- Achtung: Zeilen mit source='fbref_basic' (Zusatzligen) haben KEINE xG-Werte,
  nur goals/assists. Ein Alter der Spieler ist nicht im Datensatz enthalten.

## Few-shot-Beispiele (Frage → korrekter Tool-Aufruf)
Frage: "Die besten Bundesliga-Stürmer nach xG pro 90"
→ query_players(position='Sturm', league='GER-Bundesliga', sort_by='xg_per90')

Frage: "Kreative Mittelfeldspieler mit vielen Key Passes"
→ query_players(position='Mittelfeld', sort_by='key_passes_per90')

Frage: "Wie sehen die Zahlen von Vincenzo Grifo aus?"
→ player_profile(name='Grifo')

## Antwortstil
Gib die Tabelle aus dem Tool wieder und ergänze 2–3 Sätze Einordnung.
Weise auf Einschränkungen hin (z. B. geringe Spielminuten, fehlende Metriken).
Wird nach Alter gefragt, erkläre transparent, dass diese Info nicht vorliegt."""


def build_agent():
    """Erzeugt den Tool-Calling-Agent (LangGraph-basiert)."""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
    return create_agent(model=llm, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT)


def ask(agent, question: str, history: list | None = None) -> str:
    """Stellt eine Frage und gibt den Antworttext zurück.

    history: Liste von LangChain-Messages aus vorherigen Turns.
    """
    messages = list(history or []) + [{"role": "user", "content": question}]
    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content


if __name__ == "__main__":
    agent = build_agent()
    print(ask(agent, "Die 5 besten Spieler nach xA pro 90?"))

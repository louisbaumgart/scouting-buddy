"""Die Streamlit-Oberfläche von Scouting Buddy.

Start aus dem Projektverzeichnis:

    python -m streamlit run src/app.py
"""
import sys
from pathlib import Path

# Streamlit legt nur den Ordner des Skripts auf den Suchpfad. Ohne diese Zeile
# findet der Import von src.agent das Paket nicht.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from src.agent import build_agent, ask
from src.config import PLAYERS_PARQUET

EMERALD = "#064e3b"
EMERALD_TIEF = "#04382b"
EMERALD_HELL = "#0b6b4f"
CHAMPAGNE = "#f8e7c9"

BEISPIELFRAGEN = [
    "Beste Bundesliga-Stürmer nach xG pro 90",
    "U23-Mittelfeldspieler mit den meisten Key Passes",
    "Welche Verteidiger sind am stärksten im Spielaufbau?",
    "Welche Statistiken kannst du auswerten?",
]

# Spielfeld als Inline-SVG statt als Bilddatei, damit das Projekt ohne
# zusätzliche Assets auskommt. Das Doppelkreuz der Farbe muss als %23
# geschrieben werden, sonst bricht die Data-URL ab.
SPIELFELD = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 380'>"
    "<g fill='none' stroke='%23f8e7c9' stroke-width='2.5'>"
    "<rect x='20' y='20' width='560' height='340' rx='2'/>"
    "<line x1='300' y1='20' x2='300' y2='360'/>"
    "<circle cx='300' cy='190' r='52'/>"
    "<rect x='20' y='95' width='90' height='190'/>"
    "<rect x='490' y='95' width='90' height='190'/>"
    "<rect x='20' y='145' width='34' height='90'/>"
    "<rect x='546' y='145' width='34' height='90'/>"
    "<path d='M110,150 A50,50 0 0 1 110,230'/>"
    "<path d='M490,150 A50,50 0 0 0 490,230'/>"
    "<path d='M20,32 A12,12 0 0 0 32,20'/>"
    "<path d='M568,20 A12,12 0 0 0 580,32'/>"
    "<path d='M32,360 A12,12 0 0 0 20,348'/>"
    "<path d='M580,348 A12,12 0 0 0 568,360'/>"
    "</g>"
    "<g fill='%23f8e7c9'>"
    "<circle cx='300' cy='190' r='4'/>"
    "<circle cx='80' cy='190' r='4'/>"
    "<circle cx='520' cy='190' r='4'/>"
    "</g>"
    "</svg>"
)

st.set_page_config(page_title="Scouting Buddy", page_icon="⚽", layout="centered")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;800&display=swap');

    .stApp {{
        background:
            radial-gradient(ellipse at 20% -10%, {EMERALD_HELL}55 0%, transparent 55%),
            linear-gradient(165deg, {EMERALD} 0%, {EMERALD_TIEF} 100%);
    }}

    /* Spielfeld liegt hinter allem und fängt keine Klicks ab */
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background: url("{SPIELFELD}") no-repeat center 58% / min(150vh, 115vw) auto;
        opacity: 0.08;
        pointer-events: none;
        z-index: 0;
    }}

    h1, h2, h3 {{
        font-family: 'Archivo', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: 0.02em;
        color: {CHAMPAGNE} !important;
    }}

    .untertitel {{
        color: {CHAMPAGNE}99;
        font-size: 0.95rem;
        margin-top: -0.6rem;
        margin-bottom: 1.2rem;
    }}

    /* Nachrichten sollen nur so breit sein wie nötig, nicht über die ganze Spalte */
    [data-testid="stChatMessage"] {{
        background: {CHAMPAGNE}0d;
        border: 1px solid {CHAMPAGNE}26;
        border-radius: 14px;
        width: fit-content;
        max-width: 85%;
    }}

    /* Eigene Fragen rechts, Avatar wandert mit */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
        margin-left: auto;
        margin-right: 0;
        flex-direction: row-reverse;
        max-width: 75%;
        background: {CHAMPAGNE}1a;
    }}

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
        margin-right: auto;
        margin-left: 0;
    }}

    [data-testid="stExpander"] {{
        background: {CHAMPAGNE}08;
        border: 1px solid {CHAMPAGNE}26;
        border-radius: 14px;
    }}

    .stButton > button {{
        background: transparent;
        border: 1px solid {CHAMPAGNE}59;
        color: {CHAMPAGNE};
        border-radius: 999px;
        font-size: 0.85rem;
    }}
    .stButton > button:hover {{
        border-color: {CHAMPAGNE};
        background: {CHAMPAGNE}14;
        color: {CHAMPAGNE};
    }}

    [data-testid="stMetricValue"] {{ color: {CHAMPAGNE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Scouting Buddy")
st.markdown(
    "<div class='untertitel'>Dein Assistent für Spielerdaten der europäischen "
    "Topligen. Stell deine Frage in normaler Sprache.</div>",
    unsafe_allow_html=True,
)


def zeige_datenuebersicht() -> None:
    """Macht sichtbar, worauf die Antworten beruhen und wo die Grenzen liegen."""
    if not PLAYERS_PARQUET.exists():
        st.info(
            "Noch keine Daten vorhanden. Führ einmal `python -m src.data_prep` "
            "im Projektverzeichnis aus."
        )
        return

    df = pd.read_parquet(PLAYERS_PARQUET)

    links, mitte, rechts = st.columns(3)
    links.metric("Spielersaisons", f"{len(df):,}".replace(",", "."))
    mitte.metric("Ligen", df["league"].nunique())
    rechts.metric("Saisons", df["season"].nunique())

    hat_attribute = any(c.startswith("rating_") for c in df.columns)
    st.markdown(
        "**Torgefahr:** Tore, Tore ohne Elfmeter, xG, npxG, Schüsse  \n"
        "**Kreativität:** Assists, xA, Key Passes  \n"
        "**Angriffsbeteiligung:** xGChain, xGBuildup  \n"
        "**Weiteres:** Einsatzminuten, Spiele, Karten, Position, Alter "
        "(aus dem Geburtsjahr, ein Jahr unscharf)  \n"
        "Alle Leistungswerte gibt es zusätzlich pro 90 Minuten."
        + ("  \n**Attributwerte aus SoFIFA:** Zweikampf, Kopfball, Stärke, "
           "Tempo. Das sind Bewertungen, keine gemessenen Ereignisse."
           if hat_attribute else "")
    )
    st.markdown(
        "**Quellen:** Understat für die Spielwerte, fbref für das Geburtsjahr. "
        "Es wird nichts live abgerufen, der Stand entspricht der letzten Aufbereitung."
    )
    st.caption(
        "Nicht enthalten: Zweikämpfe, Luftzweikämpfe, Tacklings und Interceptions. "
        "Diese Opta-Daten sind seit Januar 2026 nicht mehr frei verfügbar."
    )

    if "xg_per90" in df.columns:
        aktuelle_saison = df["season"].astype(str).max()
        top = (
            df[(df["season"].astype(str) == aktuelle_saison) & (df["minutes"] >= 900)]
            .nlargest(5, "xg_per90")
            .set_index("name")["xg_per90"]
            .sort_values()
        )
        if not top.empty:
            st.caption(f"Top 5 xG pro 90, Saison {aktuelle_saison}, ab 900 Minuten")
            st.bar_chart(top, horizontal=True, color=CHAMPAGNE, height=220)


with st.expander("Welche Daten stecken drin?"):
    zeige_datenuebersicht()

if "verlauf" not in st.session_state:
    st.session_state.verlauf = []
if "agent" not in st.session_state:
    # Ist None, solange kein Schlüssel hinterlegt ist
    st.session_state.agent = build_agent()

# Die Buttons bleiben dauerhaft stehen. Wichtig ist nur, dass sie in jedem
# Durchlauf erzeugt werden, sonst geht ein Klick verloren.
st.caption("Probier zum Beispiel:")
angeklickt = None
for start in range(0, len(BEISPIELFRAGEN), 2):
    zeile = BEISPIELFRAGEN[start:start + 2]
    spalten = st.columns(len(zeile))
    for spalte, beispiel in zip(spalten, zeile):
        if spalte.button(beispiel, use_container_width=True, key=f"beispiel_{beispiel}"):
            angeklickt = beispiel

getippt = st.chat_input("z. B. 'U23-Verteidiger mit hohem xA pro 90'")
frage = getippt or angeklickt

for nachricht in st.session_state.verlauf:
    with st.chat_message(nachricht["role"]):
        st.markdown(nachricht["content"])

if frage:
    with st.chat_message("user"):
        st.markdown(frage)

    with st.chat_message("assistant"):
        with st.spinner("Einen Moment"):
            antwort = ask(st.session_state.agent, frage, st.session_state.verlauf)
        st.markdown(antwort)

    st.session_state.verlauf += [
        {"role": "user", "content": frage},
        {"role": "assistant", "content": antwort},
    ]

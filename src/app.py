"""Streamlit-Chat-UI für Scouting Buddy.

Start (im Projekt-Root):  python -m streamlit run src/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.agent import build_agent, ask

st.set_page_config(page_title="Scouting Buddy", page_icon="⚽")
st.title("⚽ Scouting Buddy")
st.caption("Frag mich nach Spielerstatistiken der europäischen Topligen.")

if "history" not in st.session_state:
    st.session_state.history = []   # Liste von {"role": ..., "content": ...}
if "agent" not in st.session_state:
    st.session_state.agent = build_agent()

# Verlauf anzeigen
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("z. B. 'Beste Bundesliga-Stürmer nach xG pro 90'"):
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Denke nach …"):
            answer = ask(st.session_state.agent, question, st.session_state.history)
        st.markdown(answer)

    st.session_state.history += [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]

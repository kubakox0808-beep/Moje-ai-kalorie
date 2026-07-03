import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

st.set_page_config(page_title="Yazio", layout="centered")

# --- CSS BEZ DŁUGICH LINII ---
css = "<style>"
css += ".main { background-color: #09090B; color: #FAFAFA; }"
css += ".stButton>button { background: #00E676; color: white; "
css += "width: 100%; border-radius: 12px; }"
css += "</style>"
st.markdown(css, unsafe_allow_html=True)

# --- BAZA ---
if "db" not in st.session_state:
    if os.path.exists("db.json"):
        with open("db.json", "r") as f:
            st.session_state.db = json.load(f)
    else:
        st.session_state.db = {}

def zapisz():
    with open("db.json", "w") as f:
        json.dump(st.session_state.db, f)

if "dzien" not in st.session_state:
    st.session_state.dzien = datetime.now().strftime("%Y-%m-%d")

# --- NAWIGACJA ---
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("◀"):
        d = datetime.strptime(st.session_state.dzien, "%Y-%m-%d")
        st.session_state.dzien = (d - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with c2:
    st.write(st.session_state.dzien)
with c3:
    if st.button("▶"):
        d = datetime.strptime(st.session_state.dzien, "%Y-%m-%d")
        st.session_state.dzien = (d + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

# --- ANALIZA AI ---
if st.button("🚀 Analizuj dzień"):
    api = st.session_state.get("api_key")
    if api:
        genai.configure(api_key=api)
        model = genai.GenerativeModel('gemini-1.5-flash')
        dane = str(st.session_state.db.get(st.session_state.dzien, {}))
        try:
            res = model.generate_content("Ocen jadlospis: " + dane)
            st.info(res.text)
        except:
            st.error("Błąd AI")
    else:
        st.warning("Ustaw klucz w profilu")

# --- DODAWANIE ---
with st.expander("➕ Dodaj posiłek"):
    nazwa = st.text_input("Nazwa produktu")
    kcal = st.number_input("Kalorie", value=0)
    if st.button("Zapisz posiłek"):
        d = st.session_state.dzien
        if d not in st.session_state.db:
            st.session_state.db[d] = {"posilki": []}
        st.session_state.db[d]["posilki"].append({"n": nazwa, "k": kcal})
        zapisz()
        st.rerun()

# --- WIDOK ---
dane = st.session_state.db.get(st.session_state.dzien, {})
for p in dane.get("posilki", []):
    st.write(f"- {p['n']}: {p['k']} kcal")

# --- PROFIL ---
with st.expander("⚙️ Profil"):
    st.session_state.api_key = st.text_input("Klucz Gemini", type="password")

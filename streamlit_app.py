import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime

# Konfiguracja
st.set_page_config(page_title="Yazio", layout="centered")

# Baza danych
if "db" not in st.session_state:
    if os.path.exists("db.json"):
        with open("db.json", "r") as f:
            st.session_state.db = json.load(f)
    else:
        st.session_state.db = {}

def zapisz():
    with open("db.json", "w") as f:
        json.dump(st.session_state.db, f)

# Stan
if "dzien" not in st.session_state:
    st.session_state.dzien = datetime.now().strftime("%Y-%m-%d")

# Nawigacja
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("◀"):
        st.rerun()
with c2:
    st.write(st.session_state.dzien)
with c3:
    if st.button("▶"):
        st.rerun()

# Analiza AI
if st.button("🚀 Analizuj dzień"):
    api = st.session_state.get("api_key")
    if api:
        genai.configure(api_key=api)
        model = genai.GenerativeModel('gemini-1.5-flash')
        d = st.session_state.db.get(st.session_state.dzien, {})
        try:
            res = model.generate_content("Oceń dietę: " + str(d))
            st.info(res.text)
        except:
            st.error("Błąd AI")
    else:
        st.warning("Ustaw klucz w profilu")

# Dodawanie
with st.expander("➕ Dodaj posiłek"):
    nazwa = st.text_input("Nazwa")
    kcal = st.number_input("Kcal", value=0)
    if st.button("Zapisz"):
        d = st.session_state.dzien
        if d not in st.session_state.db:
            st.session_state.db[d] = {"posilki": []}
        item = {"n": nazwa, "k": kcal}
        st.session_state.db[d]["posilki"].append(item)
        zapisz()
        st.rerun()

# Lista
d = st.session_state.db.get(st.session_state.dzien, {})
for p in d.get("posilki", []):
    st.write(f"- {p['n']}: {p['k']} kcal")

# Profil
with st.expander("⚙️ Profil"):
    st.session_state.api_key = st.text_input("Klucz API", type="password")

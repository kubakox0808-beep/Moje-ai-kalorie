import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

# Konfiguracja strony
st.set_page_config(page_title="Yazio", layout="centered")

# Funkcje bazy danych
def wczytaj_baze():
    if not os.path.exists("db.json"):
        return {}
    with open("db.json", "r", encoding="utf-8") as f:
        return json.load(f)

def zapisz_baze(dane):
    with open("db.json", "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False)

if "db" not in st.session_state:
    st.session_state.db = wczytaj_baze()
if "dzien" not in st.session_state:
    st.session_state.dzien = datetime.now().strftime("%Y-%m-%d")

# Funkcja AI
def analiza_ai():
    api = st.session_state.get("api_key")
    if not api:
        return "Brak klucza API"
    genai.configure(api_key=api)
    model = genai.GenerativeModel('gemini-1.5-flash')
    dane = str(st.session_state.db.get(st.session_state.dzien, {}))
    try:
        resp = model.generate_content(f"Ocen jadlospis: {dane}")
        return resp.text
    except:
        return "Blad AI"

# UI - Naglowek
st.title("🍏 Moja Dieta")

# Nawigacja
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Poprzedni"):
        d = datetime.strptime(st.session_state.dzien, "%Y-%m-%d")
        st.session_state.dzien = (d - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with col2:
    st.write(st.session_state.dzien)
with col3:
    if st.button("Nastepny"):
        d = datetime.strptime(st.session_state.dzien, "%Y-%m-%d")
        st.session_state.dzien = (d + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

# Analiza AI - przycisk
if st.button("🚀 Analizuj dzien"):
    with st.spinner("Analizowanie..."):
        st.info(analiza_ai())

# Dodawanie posilku
with st.expander("➕ Dodaj posilek"):
    nazwa = st.text_input("Nazwa")
    kcal = st.number_input("Kcal", value=0)
    if st.button("Zapisz"):
        if st.session_state.dzien not in st.session_state.db:
            st.session_state.db[st.session_state.dzien] = {"posilki": []}
        
        nowy = {"nazwa": nazwa, "kcal": kcal}
        st.session_state.db[st.session_state.dzien]["posilki"].append(nowy)
        zapisz_baze(st.session_state.db)
        st.rerun()

# Wyswietlanie
dzien_dane = st.session_state.db.get(st.session_state.dzien, {})
posilki = dzien_dane.get("posilki", [])
for p in posilki:
    st.write(f"- {p['nazwa']}: {p['kcal']} kcal")

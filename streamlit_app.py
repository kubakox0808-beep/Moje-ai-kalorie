import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

# --- KONFIGURACJA ---
st.set_page_config(page_title="Yazio", page_icon="🍏", layout="centered")

# --- CSS (TWOJE) ---
css = "<style>"
css += ".block-container { padding: 0.5rem 0.5rem; }"
css += ".main { background-color: #09090B; color: #FAFAFA; }"
css += ".stButton>button { background: linear-gradient(135deg, "
css += "#00E676 0%, #00C853 100%); color: white; width: 100%; "
css += "border-radius: 12px; height: 45px; font-weight: 700; }"
css += "div[data-testid='stMetricValue'] { font-size: 16px !important; "
css += "color: #00E676; }"
css += ".section-card { background: #18181B; padding: 10px; "
css += "border-radius: 12px; margin-top: 8px; border: 1px solid #27272A; }"
css += ".meal-title { font-size: 14px; font-weight: 700; color: #FFFFFF; "
css += "display: flex; justify-content: space-between; }"
css += ".meal-kcal { background: rgba(0, 230, 118, 0.15); color: #00E676; "
css += "padding: 1px 6px; border-radius: 8px; font-size: 11px; }"
css += ".product-row { background: #121214; padding: 8px; border-radius: 10px; "
css += "margin-top: 4px; border-left: 3px solid #00E676; }"
css += "</style>"
st.markdown(css, unsafe_allow_html=True)

# --- BAZA ---
def wczytaj_baze():
    if not os.path.exists("db.json"): return {}
    with open("db.json", "r", encoding="utf-8") as f: return json.load(f)

if "db" not in st.session_state: st.session_state.db = wczytaj_baze()
if "dzien" not in st.session_state: 
    st.session_state.dzien = datetime.now().strftime("%Y-%m-%d")

# --- FUNKCJA AI ---
def analiza():
    api = st.session_state.get("api_key", "")
    if not api: return "⚠️ Wpisz klucz API w profilu!"
    genai.configure(api_key=api)
    model = genai.GenerativeModel('gemini-1.5-flash')
    dane = str(st.session_state.db.get(st.session_state.dzien, {}))
    try:
        res = model.generate_content("Ocen dietę: " + dane)
        return res.text
    except: return "Błąd połączenia"

# --- INTERFEJS ---
st.title("🍏 Yazio")

# Przycisk analizy umieszczony wysoko
if st.button("🚀 Analizuj dzień (AI)"):
    with st.spinner("Analiza w toku..."):
        st.info(analiza())

# Tu wklej resztę swojej logiki dodawania posiłków
# Dbaj o to, aby każda linia była krótka!

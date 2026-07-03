import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

st.set_page_config(
    page_title="Yazio",
    page_icon="🍏",
    layout="centered"
)

# --- FUNKCJA ANALIZY AI (DODANA) ---
def przeprowadz_analize():
    api = st.session_state.get("api_key")
    if not api:
        return "⚠️ Brak klucza API w ustawieniach!"
    
    genai.configure(api_key=api)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dane = st.session_state.db.get(st.session_state.current_date, {})
    posilki = dane.get("posilki", [])
    
    if not posilki:
        return "Brak danych do analizy."
    
    prompt = f"Oceń jadłospis: {posilki}. Czy jest zdrowy? Podaj 3 zwięzłe rady."
    try:
        res = model.generate_content(prompt)
        return res.text
    except:
        return "Błąd połączenia z AI."

# --- STYL CSS ---
css = """
<style>
.block-container { padding: 0.5rem 0.5rem; }
.main { background-color: #09090B; color: #FAFAFA; }
.stButton>button { 
    background: linear-gradient(135deg, #00E676 0%, #00C853 100%); 
    color: white; width: 100%; border-radius: 12px; 
    height: 45px; font-weight: 700; border: none; }
div[data-testid='stMetricValue'] { font-size: 16px !important; color: #00E676; }
.section-card { background: #18181B; padding: 10px; border-radius: 12px; margin-top: 8px; border: 1px solid #27272A; }
.meal-title { font-size: 14px; font-weight: 700; color: #FFFFFF; display: flex; justify-content: space-between; }
.meal-kcal { background: rgba(0, 230, 118, 0.15); color: #00E676; padding: 1px 6px; border-radius: 8px; font-size: 11px; }
.product-row { background: #121214; padding: 8px; border-radius: 10px; margin-top: 4px; border-left: 3px solid #00E676; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- BAZA DANYCH ---
DB_FILE = "db.json"

def wczytaj_baze():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def zapisz_baze(dane):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=4)

if "db" not in st.session_state: st.session_state.db = wczytaj_baze()
if "current_date" not in st.session_state: st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
if "profil" not in st.session_state:
    st.session_state.profil = {"waga": 80.0, "wzrost": 180, "wiek": 25, "plec": "Mężczyzna", "aktywnosc": "Niska", "cel": "Utrzymanie wagi"}

# --- FUNKCJE API (SKRÓCONE DLA CZYTELNOŚCI) ---
def akcja_szukaj(txt):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    prm = {"search_terms": txt, "json": 1, "page_size": 3}
    try:
        res = requests.get(url, params=prm, timeout=5).json()
        out = []
        for p in res.get('products', []):
            n = p.get('nutriments', {})
            if 'energy-kcal_100g' in n:
                out.append({"nazwa": p.get('product_name', "Produkt"), "kcal_100g": int(n.get('energy-kcal_100g', 0)), "b_100g": float(n.get('proteins_100g', 0)), "w_100g": float(n.get('carbohydrates_100g', 0)), "t_100g": float(n.get('fat_100g', 0))})
        return out
    except: return []

def akcja_gemini(user_input, is_image=False):
    genai.configure(api_key=st.session_state.get("api_key", ""))
    model = genai.GenerativeModel('gemini-1.5-flash')
    prmt = "Zwroc JSON: {\"nazwa\": \"X\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
    try:
        img = PIL.Image.open(user_input) if is_image else user_input
        raw = model.generate_content([prmt, img]).text
        return json.loads(raw.replace("```json", "").replace("```", "").strip())
    except: return None

# --- UI GŁÓWNE ---
c_prev, c_date, c_next = st.columns([1, 3, 1])
with c_prev:
    if st.button("◀"):
        st.session_state.current_date = (datetime.strptime(st.session_state.current_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with c_date:
    st.markdown(f"<h4 style='text-align:center;'>{st.session_state.current_date}</h4>", unsafe_allow_html=True)
with c_next:
    if st.button("▶"):
        st.session_state.current_date = (datetime.strptime(st.session_state.current_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

# Analiza AI (przycisk)
if st.button("🚀 ANALIZUJ DZIEŃ (AI)"):
    with st.spinner("Analizuję..."):
        st.info(przeprowadz_analize())

# --- RESZTA KODU POZOSTAJE BEZ ZMIAN ---
# [Tutaj wklej resztę Twojego kodu: sekcje DODAWANIA, DZIENNIK i PROFIL]

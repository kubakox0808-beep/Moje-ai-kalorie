import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

# --- INTERFEJS PREMIUM (A LA YAZIO / DIETY) ---
st.set_page_config(page_title="Yazio AI Clone", page_icon="🍏", layout="centered")

# Zaawansowane stylowanie CSS dla nowoczesnego wyglądu mobilnego
st.markdown("""
    <style>
    /* Globalne tło i czcionki */
    .block-container { padding-top: 1rem; padding-bottom: 2rem; padding-left: 0.75rem; padding-right: 0.75rem; }
    .main { background-color: #09090B; color: #FAFAFA; }
    
    /* Główny przycisk akcji (Zielony Yazio) */
    .stButton>button { 
        background: linear-gradient(135deg, #00E676 0%, #00C853 100%); 
        color: white; width: 100%; border-radius: 16px; 
        height: 52px; font-size: 16px; font-weight: 700; border: none;
        box-shadow: 0 4px 12px rgba(0, 200, 83, 0.2);
        transition: all 0.2s ease;
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(0, 200, 83, 0.3); }
    .stButton>button:active { transform: translateY(1px); }
    
    /* Mniejsze przyciski pomocnicze */
    .sub-btn div button { 
        height: 40px !important; background-color: #1F1F23 !important; 
        border-radius: 12px !important; font-size: 14px !important; 
        color: #E4E4E7 !important; border: 1px solid #27272A !important;
    }
    
    /* Stylizacja kafelków z makroskładnikami */
    div[data-testid="stMetricValue"] { font-size: 22px !important; color: #00E676; font-weight: 800; letter-spacing: -0.5px; }
    div[data-testid="stMetricLabel"] { font-size: 12px !important; color: #A1A1AA; font-weight: 500; text-transform: uppercase; }
    div[data-testid="stMetric"] { background-color: #18181B; padding: 12px; border-radius: 14px; border: 1px solid #27272A; text-align: center; }
    
    /* Piękne karty posiłków */
    .section-card { 
        background: linear-gradient(145deg, #18181B, #121214); 
        padding: 16px; border-radius: 18px; margin-top: 14px; margin-bottom: 4px;
        border: 1px solid #27272A; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .meal-title { font-size: 17px; font-weight: 700; color: #FFFFFF; display: flex; justify-content: space-between; align-items: center; }
    .meal-kcal { background-color: rgba(0, 230, 118, 0.15); color: #00E676; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 700; }
    
    /* Pojedyncze produkty w posiłku */
    .product-row {
        background-color: #121214; padding: 12px; border-radius: 12px; margin-top: 8px;
        border-left: 3px solid #00E676; display: flex; justify-content: space-between; align-items: center;
    }
    .product-info { font-size: 14px; color: #E4E4E7; }
    .product-macro { font-size: 12px; color: #71717A; margin-top: 2px; }
    
    /* Customowy pasek postępu */
    .stProgress > div > div > div > div { background-color: #00E676; }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
DB_FILE = "db.json"

def wczytaj_baze():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except: return {}

def zapisz_baze(dane):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=4)

if "db" not in st.session_state: st.session_state.db = wczytaj_baze()
if "current_date" not in st.session_state: st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
if "profil" not in st.session_state:
    st.session_state.profil = {"waga": 80.0, "wzrost": 180, "wiek": 25, "plec": "Mężczyzna", "aktywnosc": "Niska (praca siedząca)", "cel": "Utrzymanie wagi"}

# --- FUNKCJE POMOCNICZE (BEZPIECZNE DLA EDYTOPA) ---
def akcja_szukaj(txt):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={txt}&search_simple=1&action=process&json=1&page_size=5"
    try:
        res = requests.get(url, headers={'User-Agent': 'Yazio - 1.0'}, timeout=5).json()
        out = []
        for p in res.get('products', []):
            n = p.get('nutriments', {})
            if 'energy-kcal_100g' in n:
                out.append({
                    "nazwa": p.get('product_name_pl') or p.get('product_name') or "Produkt",
                    "kcal_100g": int(n.get('energy-kcal_100g', 0)),
                    "b_100g": float(n.get('proteins_100g', 0)),
                    "w_100g": float(n.get('carbohydrates_100g', 0)),
                    "t_100g": float(n.get('fat_100g', 0))
                })
        return out
    except: return []

def akcja_gemini(user_input, is_image=False):
    if not st.session_state.get("api_key"):
        st.warning("Wklej klucz API w zakładce Profil!")
        return None
    genai.configure(api_key=st.session_state.api_key)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prmt = "Podaj kalorie i makro jako czysty JSON: {\"nazwa\": \"nazwa\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
        if is_image:
            img = PIL.Image.open(user_input)
            response = model.generate_content([prmt, img])
        else:
            response = model.generate_content([prmt, user_input])
        t = response.text.strip().replace("```json", "").replace("

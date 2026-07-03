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

# --- CSS W ULTRA KRÓTKICH LINIACH ---
st.markdown("""
<style>
.block-container {
    padding: 1rem 0.75rem;
}
.main {
    background-color: #09090B;
    color: #FAFAFA;
}
.stButton>button {
    background: linear-gradient(
        135deg, 
        #00E676 0%, 
        #00C853 100%
    );
    color: white;
    width: 100%;
    border-radius: 16px;
    height: 50px;
    font-size: 16px;
    font-weight: 700;
    border: none;
}
div[data-testid="stMetricValue"] {
    font-size: 22px !important;
    color: #00E676;
    font-weight: 800;
}
div[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    color: #A1A1AA;
}
div[data-testid="stMetric"] {
    background-color: #18181B;
    padding: 12px;
    border-radius: 14px;
    border: 1px solid #27272A;
    text-align: center;
}
.section-card {
    background: #18181B;
    padding: 14px;
    border-radius: 16px;
    margin-top: 12px;
    border: 1px solid #27272A;
}
.meal-title {
    font-size: 16px;
    font-weight: 700;
    color: #FFFFFF;
    display: flex;
    justify-content: space-between;
}
.meal-kcal {
    background: rgba(0, 230, 118, 0.15);
    color: #00E676;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
}
.product-row {
    background: #121214;
    padding: 10px;
    border-radius: 12px;
    margin-top: 6px;
    border-left: 3px solid #00E676;
}
</style>
""", unsafe_allow_html=True)

DB_FILE = "db.json"

def wczytaj_baze():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def zapisz_baze(dane):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=4)

if "db" not in st.session_state:
    st.session_state.db = wczytaj_baze()
if "current_date" not in st.session_state:
    st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
if "profil" not in st.session_state:
    st.session_state.profil = {
        "waga": 80.0,
        "wzrost": 180,
        "wiek": 25,
        "plec": "Mężczyzna",
        "aktywnosc": "Niska",
        "cel": "Utrzymanie wagi"
    }

def akcja_szukaj(txt):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    prm = {
        "search_terms": txt,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5
    }
    try:
        hd = {'User-Agent': 'Yazio'}
        res = requests.get(url, params=prm, headers=hd, timeout=5).json()
        out = []
        for p in res.get('products', []):
            n = p.get('nutriments', {})
            if 'energy-kcal_100g' in n:
                nazwa_p = p.get('product_name_pl') or p.get('product_name') or "Produkt"
                out.append({
                    "nazwa": nazwa_p,
                    "kcal_100g": int(n.get('energy-kcal_100g', 0)),
                    "b_100g": float(n.get('proteins_100g', 0)),
                    "w_100g": float(n.get('carbohydrates_100g', 0)),
                    "t_100g": float(n.get('fat_100g', 0))
                })
        return out
    except:
        return []

def akcja_gemini(user_input, is_image=False):
    if not st.session_state.get("api_key"):
        st.warning("Brak klucza API!")
        return None
    genai.configure(api_key=st.session_state.api_key)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prmt = "Zwroc JSON: {\"nazwa\": \"X\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
        if is_image:
            img = PIL.Image.open(user_input)
            raw = model.generate_content([prmt, img]).text
        else:
            raw = model.generate_content([prmt, user_input]).text
        
        czysty = raw.strip()
        if czysty.startswith("```"):
            lines = czysty.splitlines()
            czysty = "\n".join(lines[1:-1])
        return json.loads(czysty.strip())
    except:
        st.error("Blad AI")
        return None

# --- LIMIT DIETY ---
p = st.session_state.profil
bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"])
if p["plec"] == "Mężczyzna":
    bmr += 5
else:
    bmr -= 161

pal = 1.2
if p["aktywnosc"] == "Średnia":
    pal = 1.4
elif p["aktywnosc"] == "Wysoka":
    pal = 1.6

cpm = bmr * pal
limit_kcal = cpm
if p["cel"] == "Redukcja":
    limit_kcal -= 400
elif p["cel"] == "Masa":
    limit_kcal += 300

limit_kcal = int(limit_kcal)
limit_b = int(p["waga"] * 2.0)
limit_w = int((limit_kcal * 0.45) / 4)
limit_t = int((limit_kcal * 0.25) / 9)

curr_dt = datetime.strptime(st.session_state.current_date, "%Y-%m-%d")
if st.session_state.current_date not in st.session_state.db:
    st.session_state.db[st.session_state.current_date] = {
        "posilki": [],
        "woda": 0
    }
dzisiejsze_dane = st.session_state.db[st.session_state.current_date]

# --- NAWIGACJA DNI ---
c_prev, c_date, c_next = st.columns([1, 4, 1])
with c_prev:
    if st.button("◀", key="p_day"):
        prev_str = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        st.session_state.current_date = prev_str
        st.rerun()
with c_date:
    st.markdown(
        f"<h3 style='text-align:center;margin:0;font-size:18px;'>"
        f"🍏 {st.session_state.current_date}</h3>",
        unsafe_allow_html=True
    )
with c_next:
    if st.button("▶", key="n_day"):
        next_str = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        st.session_state.current_date = next_str
        st.rerun()

# --- PODSUMOWANIE METRYK ---
tkcal, tb, tw, tt = 0, 0, 0, 0
lista_posilkow = dzisiejsze_dane.get("posilki", [])
for i in lista_posilkow:
    tkcal += i.get("kcal", 0)
    tb += i.get("b", 0)
    tw += i.get("w", 0)
    tt += i.get("t", 0)

st.write("")
progres_val = 0.0
if limit_kcal > 0:
    progres_val = min(tkcal / limit_kcal, 1.0)
st.progress(progres_val)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{tkcal}/{limit_kcal}")
col2.metric("Białko", f"{tb}g/{limit_b}g")
col3.metric("Węgle", f"{tw}g/{limit_w}g")
col4.metric("Tłuszcz", f"{tt}g/{limit_t}g")

st.write("")
t_dziennik, t_dodaj, t_profil = st.tabs([
    "📅 Dziennik", 
    "➕ Dodaj", 
    "⚙️ Profil"
])

# --- DZIENNIK ---
with t_dziennik:
    woda_ile = dzisiejsze_dane.get('woda', 0)
    st.markdown(f"💧 Woda: {woda_ile} / 2500 ml")
    if st.button("➕ Wypij szklankę (250ml)", key="woda_b"):
        st.session_state.db[st.session_state.current_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()
    
    kat_list = ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]
    for kat in kat_list:
        w_kat = []
        for i in dzisiejsze_dane.get("posilki", []):
            if i.get("typ") == kat:
                w_kat.append(i)
        
        skcal = 0
        for i in w_kat:
            skcal += i.get("kcal", 0)
        
        st.markdown(
            f"<div class='section-card'><div class='meal-title'>"
            f"<span>{kat}</span>"
            f"<span class='meal-kcal'>{skcal} kcal</span>"

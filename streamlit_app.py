import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

# --- STYLIZACJA PREMIUM ---
st.set_page_config(page_title="Yazio", page_icon="🍏", layout="centered")

st.markdown("""
    <style>
    .block-container { padding: 1rem 0.75rem; }
    .main { background-color: #09090B; color: #FAFAFA; }
    
    .stButton>button { 
        background: linear-gradient(135deg, #00E676 0%, #00C853 100%); 
        color: white; width: 100%; border-radius: 16px; 
        height: 50px; font-size: 16px; font-weight: 700; border: none;
    }
    
    div[data-testid="stMetricValue"] { font-size: 22px !important; color: #00E676; font-weight: 800; }
    div[data-testid="stMetricLabel"] { font-size: 12px !important; color: #A1A1AA; }
    div[data-testid="stMetric"] { background-color: #18181B; padding: 12px; border-radius: 14px; border: 1px solid #27272A; text-align: center; }
    
    .section-card { 
        background: #18181B; padding: 14px; border-radius: 16px; margin-top: 12px;
        border: 1px solid #27272A;
    }
    .meal-title { font-size: 16px; font-weight: 700; color: #FFFFFF; display: flex; justify-content: space-between; }
    .meal-kcal { background: rgba(0, 230, 118, 0.15); color: #00E676; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    
    .product-row { background: #121214; padding: 10px; border-radius: 12px; margin-top: 6px; border-left: 3px solid #00E676; }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
DB_FILE = "db.json"

def wczytaj_baze():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def zapisz_baze(dane):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=4)

if "db" not in st.session_state: st.session_state.db = wczytaj_baze()
if "current_date" not in st.session_state: st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
if "profil" not in st.session_state:
    st.session_state.profil = {"waga": 80.0, "wzrost": 180, "wiek": 25, "plec": "Mężczyzna", "aktywnosc": "Niska", "cel": "Utrzymanie wagi"}

# --- FUNKCJE ---
def akcja_szukaj(txt):
    url = f"[https://world.openfoodfacts.org/cgi/search.pl?search_terms=](https://world.openfoodfacts.org/cgi/search.pl?search_terms=){txt}&search_simple=1&action=process&json=1&page_size=5"
    try:
        res = requests.get(url, headers={'User-Agent': 'Yazio'}, timeout=5).json()
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
        st.warning("Brak klucza API!")
        return None
    genai.configure(api_key=st.session_state.api_key)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prmt = "Zwroc tylko JSON: {\"nazwa\": \"X\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
        if is_image:
            img = PIL.Image.open(user_input)
            raw = model.generate_content([prmt, img]).text
        else:
            raw = model.generate_content([prmt, user_input]).text
        
        # Bezpieczne czyszczenie kodu przed JSON
        czysty = raw.strip()
        if czysty.startswith("```"):
            czysty = czysty.splitlines()[1:]
            czysty = "\n".join(czysty).replace("```", "")
        return json.loads(czysty.strip())
    except:
        st.error("Blad AI")
        return None

# --- KALKULATOR ---
p = st.session_state.profil
bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) + (5 if p["plec"] == "Mężczyzna" else -161)
pal = {"Niska": 1.2, "Średnia": 1.4, "Wysoka": 1.6}.get(p["aktywnosc"], 1.2)
cpm = bmr * pal
if p["cel"] == "Redukcja": limit_kcal = cpm - 400
elif p["cel"] == "Masa": limit_kcal = cpm + 300
else: limit_kcal = cpm

limit_kcal = int(limit_kcal)
limit_b = int(p["waga"] * 2.0)
limit_w = int((limit_kcal * 0.45) / 4)
limit_t = int((limit_kcal * 0.25) / 9)

# --- DNIE ---
curr_dt = datetime.strptime(st.session_state.current_date, "%Y-%m-%d")
if st.session_state.current_date not in st.session_state.db:
    st.session_state.db[st.session_state.current_date] = {"posilki": [], "woda": 0}
dzisiejsze_dane = st.session_state.db[st.session_state.current_date]

# --- NAWIGACJA ---
c_prev, c_date, c_next = st.columns([1, 4, 1])
with c_prev:
    if st.button("◀", key="p_day"):
        st.session_state.current_date = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with c_date:
    st.markdown(f"<h3 style='text-align:center;margin:0;font-size:18px;'>🍏 {st.session_state.current_date}</h3>", unsafe_allow_html=True)
with c_next:
    if st.button("▶", key="n_day"):
        st.session_state.current_date = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

# --- LICZNIKI ---
tkcal, tb, tw, tt = 0, 0, 0, 0
for i in dzisiejsze_dane.get("posilki", []):
    tkcal += i.get("kcal", 0)
    tb += i.get("b", 0)
    tw += i.get("w", 0)
    tt += i.get("t", 0)

st.write("")
st.progress(min(tkcal / limit_kcal, 1.0) if limit_kcal > 0 else 0.0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{tkcal}/{limit_kcal}")
col2.metric("Białko", f"{tb}g/{limit_b}g")
col3.metric("Węgle", f"{tw}g/{limit_w}g")
col4.metric("Tłuszcz", f"{tt}g/{limit_t}g")

st.write("")
t_dziennik, t_dodaj, t_profil = st.tabs(["📅 Dziennik", "➕ Dodaj", "⚙️ Profil"])

# --- WIDOK: DZIENNIK ---
with t_dziennik:
    st.markdown(f"💧 Woda: {dzisiejsze_dane.get('woda', 0)} / 2500 ml")
    if st.button("➕ Wypij szklankę (250ml)", key="woda_b"):
        st.session_state.db[st.session_state.current_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()
    
    for kat in ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]:
        w_kat = [i for i in dzisiejsze_dane.get("posilki", []) if i.get("typ") == kat]
        skcal = sum(i.get("kcal", 0) for i in w_kat)
        
        st.markdown(f"<div class='section-card'><div class='meal-title'><span>{kat}</span><span class='meal-kcal'>{skcal} kcal</span></div></div>", unsafe_allow_html=True)
        
        for item in w_kat:
            cl, cp = st.columns([5, 1])
            with cl:
                st.markdown(f"""
                <div class='product-row'>
                    <b>{item.get('nazwa')}</b><br>
                    <span style='color:#71717A;font-size:12px;'>🔥 {item.get('kcal')} kcal | B:{item.get('b')}g W:{item.get('w')}g T:{item.get('t')}g</span>
                </div>
                """, unsafe_allow_html=True)
            with cp:
                st.write("")
                if st.button("❌", key=f"d_{item.get('id')}"):
                    st.session_state.db[st.session_state.current_date]["posilki"] = [i for i in dzisiejsze_dane["posilki"] if i.get("id") != item.get("id")]
                    zapisz_baze(st.session_state.db)
                    st.rerun()

# --- WIDOK: DODAJ ---
with t_dodaj:
    kat_wyb = st.selectbox("Kategoria:", ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"])
    metoda = st.radio("Metoda:", ["Baza", "Foto", "Tekst", "Recznie"], horizontal=True)
    res_posilek = None

    if metoda == "Baza":
        stxt = st.text_input("Szukaj:")
        if stxt:
            w = akcja_szukaj(stxt)
            if w:
                wyb = st.selectbox("Wynik:", w, format_func=lambda x: f"{x['nazwa']} ({x['kcal_100g']} kcal)")
                g = st.number_input("Gramy:", min_value=1, value=100)
                if st.button("Dodaj produkt"):
                    m = g / 100.0
                    res_posilek = {"nazwa": f"{wyb['nazwa']} ({g}

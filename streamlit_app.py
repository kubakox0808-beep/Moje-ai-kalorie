import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

# --- INTERFEJS MOBILNY ---
st.set_page_config(page_title="Yazio AI Clone", page_icon="🍏", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem; padding-bottom: 2rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    .main { background-color: #0B0B0C; color: #F4F4F5; }
    .stButton>button { 
        background-color: #00C853; color: white; width: 100%; border-radius: 14px; 
        height: 50px; font-size: 15px; font-weight: bold; border: none; margin-top: 5px;
    }
    .sub-btn>div>button { height: 38px !important; background-color: #1F1F22 !important; border-radius: 10px !important; font-size: 13px !important; }
    div[data-testid="stMetricValue"] { font-size: 20px !important; color: #00C853; font-weight: bold; }
    div[data-testid="stMetricLabel"] { font-size: 11px !important; color: #A1A1AA; }
    .section-card { background-color: #18181B; padding: 12px; border-radius: 14px; margin-bottom: 10px; border: 1px solid #27272A; }
    .meal-title { font-size: 15px; font-weight: bold; color: #FFFFFF; display: flex; justify-content: space-between; }
    .meal-item { font-size: 13px; color: #D4D4D8; padding: 6px 0; border-bottom: 1px solid #27272A; }
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

# --- WYDZIELONE FUNKCJE (UNIKANIE WCIĘĆ) ---
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
        st.warning("Brak klucza API!")
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
        t = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(t.strip())
    except:
        st.error("Blad AI")
        return None

# --- OBLICZENIA DIETY ---
p = st.session_state.profil
bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) + (5 if p["plec"] == "Mężczyzna" else -161)
pal = {"Niska (praca siedząca)": 1.2, "Średnia (1-3 treningi/tydz)": 1.4, "Wysoka (codzienne treningi)": 1.6}.get(p["aktywnosc"], 1.2)
cpm = bmr * pal
if p["cel"] == "Redukcja tkanki tłuszczowej": limit_kcal = cpm - 400
elif p["cel"] == "Budowanie masy mięśniowej": limit_kcal = cpm + 300
else: limit_kcal = cpm
limit_kcal = int(limit_kcal)
limit_b = int(p["waga"] * 2.0)
limit_w = int((limit_kcal * 0.45) / 4)
limit_t = int((limit_kcal * 0.25) / 9)

# --- INICJALIZACJA DNIA ---
curr_dt = datetime.strptime(st.session_state.current_date, "%Y-%m-%d")
if st.session_state.current_date not in st.session_state.db:
    st.session_state.db[st.session_state.current_date] = {"posilki": [], "woda": 0}
dzisiejsze_dane = st.session_state.db[st.session_state.current_date]

# --- NAWIGACJA ---
c_prev, c_date, c_next = st.columns([1, 3, 1])
with c_prev:
    if st.button("◀", key="prev_day"):
        st.session_state.current_date = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with c_date:
    st.markdown(f"<h3 style='text-align: center; margin: 0; font-size: 18px;'>📆 {st.session_state.current_date}</h3>", unsafe_allow_html=True)
with c_next:
    if st.button("▶", key="next_day"):
        st.session_state.current_date = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

# --- SUMY ---
total_kcal = 0
total_b = 0
total_w = 0
total_t = 0
for i in dzisiejsze_dane.get("posilki", []):
    total_kcal += i.get("kcal", 0)
    total_b += i.get("b", 0)
    total_w += i.get("w", 0)
    total_t += i.get("t", 0)

st.progress(min(total_kcal / limit_kcal, 1.0) if limit_kcal > 0 else 0.0)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{total_kcal}/{limit_kcal}")
col2.metric("Białko", f"{total_b}/{limit_b}g")
col3.metric("Węgle", f"{total_w}/{limit_w}g")
col4.metric("Tłuszcz", f"{total_t}/{limit_t}g")

tab_dziennik, tab_dodaj, tab_profil = st.tabs(["📅 Dziennik", "➕ Dodaj", "⚙️ Profil"])

# --- WIDOK: DZIENNIK ---
with tab_dziennik:
    st.markdown(f"💧 Woda: {dzisiejsze_dane.get('woda', 0)} / 2500 ml")
    if st.button("➕ Szklanka (250ml)", key="add_w"):
        st.session_state.db[st.session_state.current_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()
    
    for kat in ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]:
        w_kat = [i for i in dzisiejsze_dane.get("posilki", []) if i.get("typ") == kat]
        skcal = sum(i.get("kcal", 0) for i in w_kat)
        st.markdown(f"<div class='section-card'><div class='meal-title'><span>{kat}</span><span>{skcal} kcal</span></div></div>", unsafe_allow_html=True)
        for item in w_kat:
            cx, cd = st.columns([6, 1])
            cx.markdown(f"**{item.get('nazwa')}**<br>{item.get('kcal')} kcal | B:{item.get('b')}g", unsafe_allow_html=True)
            if cd.button("❌", key=f"del_{item.get('id')}"):
                st.session_state.db[st.session_state.current_date]["posilki"] = [i for i in dzisiejsze_dane["posilki"] if i.get("id") != item.get("id")]
                zapisz_baze(st.session_state.db)
                st.rerun()

# --- WIDOK: DODAJ ---
with tab_dodaj:
    kat_wyb = st.selectbox("Kategoria:", ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"])
    metoda = st.radio("Metoda:", ["Baza", "Foto", "Tekst", "Recznie"], horizontal=True)
    res_posilek = None

    if metoda == "Baza":
        stxt = st.text_input("Nazwa produktu:")
        if stxt:
            w = akcja_szukaj(stxt)
            if w:
                wyb = st.selectbox("Wyniki:", w, format_func=lambda x: f"{x['nazwa']} ({x['kcal_100g']} kcal)")
                g = st.number_input("Gramy:", min_value=1, value=100)
                if st.button("Zapisz produkt"):
                    m = g / 100.0
                    res_posilek = {"nazwa": f"{wyb['nazwa']} ({g}g)", "kcal": int(wyb['kcal_100g'] * m), "b": int(wyb['b_100g'] * m), "w": int(wyb['w_100g'] * m), "t": int(wyb['t_100g'] * m)}

    if metoda == "Foto":
        f = st.camera_input("Zdjecie:")
        if f and st.button("Skanuj AI"):
            res_posilek = akcja_gemini(f, is_image=True)

    if metoda == "Tekst":
        t = st.text_input("Co zjadles?:")
        if t and st.button("Licz AI"):
            res_posilek = akcja_gemini(t, is_image=False)

    if metoda == "Recznie":
        with st.form("f_man"):
            rn = st.text_input("Nazwa:", "Wpis")
            rk = st.number_input("Kcal:", value=100)
            rb = st.number_input("Białko:", value=0)
            rw = st.number_input("Węgle:", value=0)
            rt = st.number_input("Tłuszcz:", value=0)
            if st.form_submit_button("Dodaj recznie"):
                res_posilek = {"nazwa": rn, "kcal": int(rk), "b": int(rb), "w": int(rw), "t": int(rt)}

    if res_posilek:
        res_posilek["typ"] = kat_wyb
        res_posilek["id"] = datetime.now().timestamp()
        st.session_state.db[st.session_state.current_date]["posilki"].append(res_posilek)
        zapisz_baze(st.session_state.db)
        st.success("Dodano!")
        st.rerun()

# --- WIDOK: PROFIL ---
with tab_profil:
    st.session_state.api_key = st.text_input("Gemini API Key:", value=st.session_state.get("api_key", ""), type="password")
    st.session_state.profil["plec"] = st.radio("Płeć:", ["Mężczyzna", "Kobieta"], horizontal=True)
    st.session_state.profil["waga"] = st.number_input("Waga (kg):", value=st.session_state.profil["waga"])
    st.session_state.profil["wzrost"] = st.number_input("Wzrost (cm):", value=st.session_state.profil["wzrost"])
    st.session_state.profil["wiek"] = st.number_input("Wiek:", value=st.session_state.profil["wiek"])
    st.session_state.profil["aktywnosc"] = st.selectbox("Aktywność:", ["Niska (praca siedząca)", "Średnia (1-3 treningi/tydz)", "Wysoka (codzienne treningi)"])
    st.session_state.profil["cel"] = st.selectbox("Cel:", ["Redukcja tkanki tłuszczowej", "Utrzymanie wagi", "Budowanie masy mięśniowej"])
    if st.button("Zapisz profil"): st.rerun()

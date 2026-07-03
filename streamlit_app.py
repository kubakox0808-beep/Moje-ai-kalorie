import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

# --- INTERFEJS PREMIUM MOBILNY ---
st.set_page_config(page_title="Yazio AI Clone", page_icon="🍏", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem; padding-bottom: 2rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    .main { background-color: #0B0B0C; color: #F4F4F5; }
    
    .stButton>button { 
        background-color: #00C853; color: white; width: 100%; border-radius: 14px; 
        height: 50px; font-size: 15px; font-weight: bold; border: none; margin-top: 5px;
    }
    .stButton>button:active { background-color: #009624; }
    
    .sub-btn>div>button { height: 38px !important; background-color: #1F1F22 !important; border-radius: 10px !important; font-size: 13px !important; }
    
    div[data-testid="stMetricValue"] { font-size: 20px !important; color: #00C853; font-weight: bold; }
    div[data-testid="stMetricLabel"] { font-size: 11px !important; color: #A1A1AA; }
    
    .section-card { background-color: #18181B; padding: 12px; border-radius: 14px; margin-bottom: 10px; border: 1px solid #27272A; }
    .meal-title { font-size: 15px; font-weight: bold; color: #FFFFFF; display: flex; justify-content: space-between; }
    .meal-item { font-size: 13px; color: #D4D4D8; padding: 6px 0; border-bottom: 1px solid #27272A; }
    .meal-item:last-child { border-bottom: none; }
    </style>
    """, unsafe_allow_html=True)

# --- TRWAŁA BAZA DANYCH (JSON) ---
DB_FILE = "db.json"

def wczytaj_baze():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                dane = json.load(f)
                if isinstance(dane, dict): return dane
                return {}
        except: return {}
    return {}

def zapisz_baze(dane):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=4)

if "db" not in st.session_state: st.session_state.db = wczytaj_baze()
if "current_date" not in st.session_state: st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")
if "profil" not in st.session_state:
    st.session_state.profil = {"waga": 80.0, "wzrost": 180, "wiek": 25, "plec": "Mężczyzna", "aktywnosc": "Niska (praca siedząca)", "cel": "Utrzymanie wagi"}

# --- FUNKCJA WYSZUKIWANIA W OPEN FOOD FACTS (1:1) ---
def szukaj_w_bazie_off(zapytanie):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={zapytanie}&search_simple=1&action=process&json=1&page_size=5"
    headers = {'User-Agent': 'YazioAiClone - Web - 1.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        produkty = []
        for p in res.get('products', []):
            n = p.get('nutriments', {})
            if 'energy-kcal_100g' in n:
                produkty.append({
                    "nazwa": p.get('product_name_pl') or p.get('product_name') or "Nieznany produkt",
                    "kcal_100g": int(n.get('energy-kcal_100g', 0)),
                    "b_100g": float(n.get('proteins_100g', 0)),
                    "w_100g": float(n.get('carbohydrates_100g', 0)),
                    "t_100g": float(n.get('fat_100g', 0))
                })
        return produkty
    except:
        return []

# --- KALKULATOR DIETY ---
def przelicz_zapotrzebowanie():
    p = st.session_state.profil
    bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) + (5 if p["plec"] == "Mężczyzna" else -161)
    pal = {"Niska (praca siedząca)": 1.2, "Średnia (1-3 treningi/tydz)": 1.4, "Wysoka (codzienne treningi)": 1.6}.get(p["aktywnosc"], 1.2)
    cpm = bmr * pal
    if p["cel"] == "Redukcja tkanki tłuszczowej": kcal = cpm - 400
    elif p["cel"] == "Budowanie masy mięśniowej": kcal = cpm + 300
    else: kcal = cpm
    kcal = int(kcal)
    return kcal, int(p["waga"] * 2.0), int((kcal * 0.45) / 4), int((kcal * 0.25) / 9)

limit_kcal, limit_b, limit_w, limit_t = przelicz_zapotrzebowanie()

# --- NAWIGACJA DATĄ ---
curr_dt = datetime.strptime(st.session_state.current_date, "%Y-%m-%d")
c_prev, c_date, c_next = st.columns([1, 3, 1])
with c_prev:
    if st.button("◀", key="prev_day"):
        st.session_state.current_date = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with c_date:
    wyswietl_date = "Dzisiaj" if st.session_state.current_date == datetime.now().strftime("%Y-%m-%d") else st.session_state.current_date
    st.markdown(f"<h3 style='text-align: center; margin: 0; font-size: 18px;'>📆 {wyswietl_date}</h3>", unsafe_allow_html=True)
with c_next:
    if st.button("▶", key="next_day"):
        st.session_state.current_date = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

if st.session_state.current_date not in st.session_state.db or not isinstance(st.session_state.db[st.session_state.current_date], dict):
    st.session_state.db[st.session_state.current_date] = {"posilki": [], "woda": 0}
    zapisz_baze(st.session_state.db)

dzisiejsze_dane = st.session_state.db[st.session_state.current_date]
if "posilki" not in dzisiejsze_dane: dzisiejsze_dane["posilki"] = []
if "woda" not in dzisiejsze_dane: dzisiejsze_dane["woda"] = 0

# --- PODSUMOWANIE DNIA ---
total_kcal = 0
total_b = 0
total_w = 0
total_t = 0

for i in dzisiejsze_dane["posilki"]:
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

st.write("")
tab_dziennik, tab_dodaj, tab_profil = st.tabs(["📅 Dziennik", "➕ Dodaj posiłek", "⚙️ Profil i Cele"])

# ==================== KATEGORIA: DZIENNIK ====================
with tab_dziennik:
    st.markdown(f"💧 **Woda:** {dzisiejsze_dane.get('woda', 0)} / 2500 ml")
    st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
    if st.button("➕ Wypij szklankę (250ml)", key="add_water"):
        st.session_state.db[st.session_state.current_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    kategorie = ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]
    wczoraj_str = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")

    for kat in kategorie:
        w_kat = []
        for i in dzisiejsze_dane.get("posilki", []):
            if i.get("typ") == kat:
                w_kat.append(i)
                
        kat_kcal = sum(i.get("kcal", 0) for i in w_kat)
        st.markdown(f"<div class='section-card'><div class='meal-title'><span>{kat}</span><span style='color: #00C853;'>{kat_kcal} kcal</span></div></div>", unsafe_allow_html=True)
        
        if not w_kat:
            wczorajsze_dane = st.session_state.db.get(wczoraj_str, {})
            wczorajsze_w_kat = []
            if isinstance(wczorajsze_dane, dict):
                for i in wczorajsze_dane.get("posilki", []):
                    if i.get("typ") == kat:
                        wczorajsze_w_kat.append(i)
                        
            if wczorajsze_w_kat:
                st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
                if st.button(f"📋 Skopiuj wczorajsze {kat.lower()}", key=f"copy_{kat}"):
                    for item in wczorajsze_w_kat:
                        skopiowany = item.copy()
                        skopiowany["id"] = datetime.now().timestamp() + item.get("id", 0)
                        st.session_state.db[st.session_state.current_date]["posilki"].append(skopiowany)
                    zapisz_baze(st.session_state.db)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #52525B; font-size: 12px; margin-left: 10px; margin-top: -5px;'>Brak posiłków</p>", unsafe_allow_html=True)
        else:
            for item in w_kat:
                col_txt, col_del = st.columns([6, 1])
                with col_txt:
                    st.markdown(f"<div class='meal-item'><b>{item.get('nazwa', 'Wpis')}</b><br><span style='color: #A1A1AA;'>🔥 {item.get('kcal', 0)} kcal | B: {item.get('b', 0)}g | W: {item.get('w', 0)}g | T: {item.get('t', 0)}g</span></div>", unsafe_allow_html=True)
                with col_del:
                    if st.button("❌", key=f"del_{item.get('id', 0)}"):
                        nowa_lista = []
                        for i in dzisiejsze_dane["posilki"]:
                            if i.get("id") != item.get("id"):
                                nowa_lista.append(i)
                        st.session_state.db[st.session_state.current_date]["posilki"] = nowa_lista
                        zapisz_baze(st.session_state.db)
                        st.rerun()

# ==================== KATEGORIA: DODAJ POSIŁEK ====================
with tab_dodaj:
    st.subheader("📝 Nowy wpis")
    rodzaj_posilku = st.selectbox("Wybierz kategorię posiłku:", ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"])
    
    # Bezpieczne opcje bez emoji, aby edytor nie urywał tekstu
    metoda = st.radio("Metoda:", ["Baza produktów", "Zdjecie posilku AI", "Opis tekstowy AI", "Recznie"], horizontal=True)
    
    nowy_posilek = None
    if "api_key" in st.session_state and st.session_state.api_key: genai.configure(api_key=st.session_state.api_key)
    
    if metoda == "Baza produktów":
        szukany_tekst = st.text_input("Wpisz nazwę produktu (np. Skyr Piątnica, Ketchup Włocławek):")
        if szukany_tekst:
            wyniki = szukaj_w_bazie_off(szukany_tekst)
            if wyniki:
                wybrany = st.selectbox("Znalezione produkty:", wyniki, format_func=lambda x: f"{x['nazwa']} ({x['kcal_100g']} kcal/100g)")
                waga_g = st.number_input("Ile gramów zjadłeś? (g):", min_value=1, value=100, step=10)
                if st.button("💾 Dodaj produkt"):
                    mnoznik = waga_g / 100.0
                    nowy_posilek = {
                        "nazwa": f"{wybrany['nazwa']} ({waga_g}g)",
                        "kcal": int(wybrany['kcal_100g'] * mnoznik),
                        "b": int(wybrany['b_100g'] * mnoznik),
                        "w": int(wybrany['w_100g'] * mnoznik),
                        "t": int(wybrany['t_100g'] * mnoznik)
                    }
            else:
                st.info("Brak produktów w bazie. Użyj opcji Opis tekstowy AI.")

    elif metoda == "Zdjecie posilku AI":
        if not st.session_state.get("api_key"): st.warning("⚠️ Wklej klucz API w zakładce Profil i Cele!")
        else:
            foto = st.camera_input("Zrób zdjęcie", label_visibility="collapsed")
            if foto and st.button("Skanuj danie"):
                with st.spinner("Skanowanie..."):
                    try:
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        instr = "Podaj kalorie i makro posiłku jako czysty JSON: {\"nazwa\": \"nazwa\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
                        response = model.generate_content([instr, PIL.Image.open(foto)])
                        czysty_tekst = response.text.strip()
                        czysty_tekst = czysty_tekst.replace("```json", "").replace("```", "")
                        nowy_posilek = json.loads(czysty_tekst.strip())
                    except: st.error("Nie udało się przeanalizować zdjęcia.")

    elif metoda ==

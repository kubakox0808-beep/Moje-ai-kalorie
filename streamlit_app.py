import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime, timedelta
import PIL.Image

# --- INTERFEJS PREMIUM MOBILNY (YAZIO AI) ---
st.set_page_config(page_title="Yazio AI Clone", page_icon="🍏", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem; padding-bottom: 2rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    .main { background-color: #0B0B0C; color: #F4F4F5; }
    
    /* Przyciski główne i akcji */
    .stButton>button { 
        background-color: #00C853; color: white; width: 100%; border-radius: 14px; 
        height: 50px; font-size: 15px; font-weight: bold; border: none; margin-top: 5px;
    }
    .stButton>button:active { background-color: #009624; }
    
    /* Małe przyciski (woda, quick add) */
    .sub-btn>div>button { height: 38px !important; background-color: #1F1F22 !important; border-radius: 10px !important; font-size: 13px !important; }
    
    /* Liczniki i estetyka kart */
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
                return json.load(f)
        except:
            return {}
    return {}

def zapisz_baze(dane):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=4)

# Inicjalizacja danych w aplikacji
if "db" not in st.session_state:
    st.session_state.db = wczytaj_baze()
if "current_date" not in st.session_state:
    st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")

if "profil" not in st.session_state:
    st.session_state.profil = {
        "waga": 80.0, "wzrost": 180, "wiek": 25, "plec": "Mężczyzna",
        "aktywnosc": "Niska (praca siedząca)", "cel": "Utrzymanie wagi"
    }

# --- KALKULATOR DIETY ---
def przelicz_zapotrzebowanie():
    p = st.session_state.profil
    if p["plec"] == "Mężczyzna":
        bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) + 5
    else:
        bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) - 161
    
    pal_map = {"Niska (praca siedząca)": 1.2, "Średnia (1-3 treningi/tydz)": 1.4, "Wysoka (codzienne treningi)": 1.6}
    cpm = bmr * pal_map.get(p["aktywnosc"], 1.2)
    
    if p["cel"] == "Redukcja tkanki tłuszczowej": kcal = cpm - 400
    elif p["cel"] == "Budowanie masy mięśniowej": kcal = cpm + 300
    else: kcal = cpm
        
    kcal = int(kcal)
    b = int(p["waga"] * 2.0)
    t = int((kcal * 0.25) / 9)
    w = int((kcal - (b * 4) - (t * 9)) / 4)
    return kcal, b, w, t

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

# Przygotuj strukturę na wybrany dzień
if st.session_state.current_date not in st.session_state.db:
    st.session_state.db[st.session_state.current_date] = {"posilki": [], "woda": 0}
    zapisz_baze(st.session_state.db)

dzisiejsze_dane = st.session_state.db[st.session_state.current_date]

# --- PODSUMOWANIE DNIA ---
total_kcal = sum(i["kcal"] for i in dzisiejsze_dane.get("posilki", []))
total_b = sum(i["b"] for i in dzisiejsze_dane.get("posilki", []))
total_w = sum(i["w"] for i in dzisiejsze_dane.get("posilki", []))
total_t = sum(i["t"] for i in dzisiejsze_dane.get("posilki", []))

st.progress(min(total_kcal / limit_kcal, 1.0) if limit_kcal > 0 else 0.0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{total_kcal}/{limit_kcal}")
col2.metric("Białko", f"{total_b}/{limit_b}g")
col3.metric("Węgle", f"{total_w}/{limit_w}g")
col4.metric("Tłuszcz", f"{total_t}/{limit_t}g")

# --- LICZNIK WODY I QUICK ADD ---
st.write("")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("<p style='font-size:13px; margin-bottom:2px; color:#A1A1AA;'>💧 Licznik Wody</p>", unsafe_allow_html=True)
    st.markdown(f"**Wypite:** {dzisiejsze_dane.get('woda', 0)} ml / 2500 ml")
    st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
    if st.button("➕ Szklanka (250ml)", key="add_water"):
        st.session_state.db[st.session_state.current_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown("<p style='font-size:13px; margin-bottom:2px; color:#A1A1AA;'>⚡ Szybkie dodawanie (Kcal)</p>", unsafe_allow_html=True)
    st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
    c_q1, c_q2 = st.columns(2)
    with c_q1:
        if st.button("+100 kcal", key="q_100"):
            st.session_state.db[st.session_state.current_date]["posilki"].append({"nazwa": "Szybki wpis", "kcal": 100, "b": 0, "w": 0, "t": 0, "typ": "Przekąski", "id": datetime.now().timestamp()})
            zapisz_baze(st.session_state.db)
            st.rerun()
        if st.button("+10g Białka", key="q_b10"):
            st.session_state.db[st.session_state.current_date]["posilki"].append({"nazwa": "Szybkie białko", "kcal": 40, "b": 10, "w": 0, "t": 0, "typ": "Przekąski", "id": datetime.now().timestamp()})
            zapisz_baze(st.session_state.db)
            st.rerun()
    with c_q2:
        if st.button("+300 kcal", key="q_300"):
            st.session_state.db[st.session_state.current_date]["posilki"].append({"nazwa": "Szybki wpis", "kcal": 300, "b": 0, "w": 0, "t": 0, "typ": "Przekąski", "id": datetime.now().timestamp()})
            zapisz_baze(st.session_state.db)
            st.rerun()
        if st.button("+500 kcal", key="q_500"):
            st.session_state.db[st.session_state.current_date]["posilki"].append({"nazwa": "Szybki wpis", "kcal": 500, "b": 0, "w": 0, "t": 0, "typ": "Przekąski", "id": datetime.now().timestamp()})
            zapisz_baze(st.session_state.db)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- DODAWANIE POSIŁKU (FOTO AI / TEKST / RĘCZNIE) ---
st.write("")
with st.expander("➕ DODAJ POSIŁEK / SKANUJ"):
    rodzaj_posilku = st.selectbox("Gdzie dodać?", ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"])
    metoda = st.radio("Metoda wprowadzenia:", ["📸 Skanuj foto przez AI", "✍️ Napisz tekstowo (AI)", "✏️ Wpisz ręcznie (Znam makro)"], horizontal=False)
    
    nowy_posilek = None
    if "api_key" in st.session_state and st.session_state.api_key:
        genai.configure(api_key=st.session_state.api_key)
    
    if "AI" in metoda and (not st.session_state.get("api_key")):
        st.warning("⚠️ Wklej klucz API w ustawieniach na dole!")
        
    elif metoda == "📸 Skanuj foto przez AI":
        foto = st.camera_input("Zrób zdjęcie", label_visibility="collapsed")
        if foto and st.button("🔍 Analizuj obraz"):
            with st.spinner("AI analizuje..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    instr = "Podaj kalorie i makro posiłku jako czysty JSON: {\"nazwa\": \"nazwa\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
                    response = model.generate_content([instr, PIL.Image.open(foto)])
                    nowy_posilek = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                except: st.error("Błąd skanowania.")

    elif metoda == "✍️ Napisz tekstowo (AI)":
        tekst = st.text_input("Co zjadłeś?", placeholder="np. owsianka z bananem")
        if tekst and st.button("🔍 Oblicz przez AI"):
            with st.spinner("AI liczy makro..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    instr = "Podaj kalorie i makro posiłku jako czysty JSON: {\"nazwa\": \"nazwa\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
                    response = model.generate_content([instr, tekst])
                    nowy_posilek = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                except: st.error("Błąd AI.")

    elif metoda == "✏️ Wpisz ręcznie (Znam makro)":
        with st.form("manual_form"):
            r_nazwa = st.text_input("Nazwa produktu/posiłku:", "Wpis własny")
            r_kcal = st.number_input("Kalorie (kcal):", min_value=0, value=100)
            rc_b = st.number_input("Białko (g):", min_value=0, value=0)
            rc_w = st.number_input("Węglowodany (g):", min_value=0, value=0)
            rc_t = st.number_input("Tłuszcz (g):", min_value=0, value=0)
            if st.form_submit_button("💾 Dodaj do dziennika"):
                nowy_posilek = {"nazwa": r_nazwa, "kcal": int(r_kcal), "b": int(rc_b), "w": int(rc_w), "t": int(rc_t)}

    if nowy_posilek:
        nowy_posilek["typ"] = rodzaj_posilku
        nowy_posilek["id"] = datetime.now().timestamp()
        st.session_state.db[st.session_state.current_date]["posilki"].append(nowy_posilek)
        zapisz_baze(st.session_state.db)
        st.success(f"Dodano do: {rodzaj_posilku}!")
        st.rerun()

# --- DZIENNIK POTRAW ---
st.write("")
kategorie = ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]
wczoraj_str = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")

for kat in kategorie:
    w_kat = [i for i in dzisiejsze_dane.get("posilki", []) if i["typ"] == kat]
    kat_kcal = sum(i["kcal"] for i in w_kat)
    
    st.markdown(f"<div class='section-card'><div class='meal-title'><span>{kat}</span><span style='color: #00C853;'>{kat_kcal} kcal</span></div></div>", unsafe_allow_html=True)
    
    if not w_kat:
        wczorajsze_w_kat = st.session_state.db.get(wczoraj_str, {}).get("posilki", [])
        wczorajsze_w_kat = [i for i in wczorajsze_w_kat if i["typ"] == kat]
        
        if wczorajsze_w_kat:
            st.markdown("<div class='sub-btn'>", unsafe_allow_html=True)
            if st.button(f"📋 Skopiuj wczorajsze {kat.lower()}", key=f"copy_{kat}"):
                for item in wczorajsze_w_kat:
                    skopiowany = item.copy()
                    skopiowany["id"] = datetime.now().timestamp() + item["id"]
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
                st.markdown(f"<div class='meal-item'><b>{item['nazwa']}</b><br><span style='color: #A1A1AA;'>🔥 {item['kcal']} kcal | B: {item['b']}g | W: {item['w']}g | T: {item['t']}g</span></div>", unsafe_allow_html=True)
            with col_del:
                if st.button("❌", key=f"del_{item['id']}"):
                    st.session_state.db[st.session_state.current_date]["posilki"] = [i for i in dzisiejsze_dane["posilki"] if i["id"] != item["id"]]
                    zapisz_baze(st.session_state.db)
                    st.rerun()

# --- PANEL CONFIGU ---
st.write("---")
with st.expander("⚙️ Twój Profil i Ustawienia"):
    st.session_state.api_key = st.text_input("Klucz Gemini API:", value=st.session_state.get("api_key", ""), type="password")
    st.subheader("📊 Twoje dane biologiczne")
    st.session_state.profil["plec"] = st.radio("Płeć:", ["Mężczyzna", "Kobieta"], horizontal=True, index=0 if st.session_state.profil["plec"] == "Mężczyzna" else 1)
    st.session_state.profil["waga"] = st.number_input("Waga (kg):", value=st.session_state.profil["waga"], step=0.1)
    st.session_state.profil["wzrost"] = st.number_input("Wzrost (cm):", value=st.session_state.profil["wzrost"], step=1)
    st.session_state.profil["wiek"] = st.number_input("Wiek (lata):", value=st.session_state.profil["wiek"], step=1)
    st.session_state.profil["aktywnosc"] = st.selectbox("Poziom aktywności:", ["Niska (praca siedząca)", "Średnia (1-3 treningi/tydz)", "Wysoka (codzienne treningi)"])
    st.session_state.profil["cel"] = st.selectbox("Twój cel sylwetkowy:", ["Redukcja tkanki tłuszczowej", "Utrzymanie wagi", "Budowanie masy mięśniowej"])
    if st.button("🔄 Zapisz profil i przelicz diete"):
        st.rerun()

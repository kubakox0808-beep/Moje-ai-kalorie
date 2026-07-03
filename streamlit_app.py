import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime, timedelta
import PIL.Image

# --- INTERFEJS PREMIUM MOBILNY (YAZIO CORE) ---
st.set_page_config(page_title="Yazio AI Clone", page_icon="🍏", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem; padding-bottom: 2rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    .main { background-color: #0B0B0C; color: #F4F4F5; }
    
    /* Przyciski główne i akcji */
    .stButton>button { 
        background-color: #00C853; color: white; width: 100%; border-radius: 14px; 
        height: 52px; font-size: 15px; font-weight: bold; border: none; margin-top: 5px;
    }
    .stButton>button:active { background-color: #009624; }
    
    /* Przyciski nawigacji datą */
    div[data-testid="column"] .stButton>button { height: 40px; background-color: #1F1F22; border-radius: 10px; }
    
    /* Liczniki i estetyka kart */
    div[data-testid="stMetricValue"] { font-size: 20px !important; color: #00C853; font-weight: bold; }
    div[data-testid="stMetricLabel"] { font-size: 11px !important; color: #A1A1AA; }
    
    .section-card { background-color: #18181B; padding: 12px; border-radius: 14px; margin-bottom: 10px; border: 1px solid #27272A; }
    .meal-title { font-size: 15px; font-weight: bold; color: #FFFFFF; display: flex; justify-content: space-between; }
    .meal-item { font-size: 13px; color: #D4D4D8; padding: 6px 0; border-bottom: 1px solid #27272A; }
    .meal-item:last-child { border-bottom: none; }
    </style>
    """, unsafe_allow_html=True)

# --- INICJALIZACJA BAZY DANYCH W PAMIĘCI ---
if "db" not in st.session_state:
    st.session_state.db = {}  # Format: {"YYYY-MM-DD": [lista_posilkow]}
if "current_date" not in st.session_state:
    st.session_state.current_date = datetime.now().strftime("%Y-%m-%d")

# Domyślne wartości profilu
if "profil" not in st.session_state:
    st.session_state.profil = {
        "waga": 80.0, "wzrost": 180, "wiek": 25, "plec": "Mężczyzna",
        "aktywnosc": "Niska (praca siedząca)", "cel": "Utrzymanie wagi"
    }

# --- KALKULATOR DIETY (MIFflin-ST JEOR) ---
def przelicz_zapotrzebowanie():
    p = st.session_state.profil
    # BMR
    if p["plec"] == "Mężczyzna":
        bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) + 5
    else:
        bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"]) - 161
    
    # Współczynnik aktywności (PAL)
    pal_map = {
        "Niska (praca siedząca)": 1.2,
        "Średnia (1-3 treningi/tydz)": 1.4,
        "Wysoka (codzienne treningi)": 1.6
    }
    cpm = bmr * pal_map.get(p["aktywnosc"], 1.2)
    
    # Cel
    if p["cel"] == "Redukcja tkanki tłuszczowej":
        kcal = cpm - 400
    elif p["cel"] == "Budowanie masy mięśniowej":
        kcal = cpm + 300
    else:
        kcal = cpm
        
    kcal = int(kcal)
    # Rozkład makro (Białko 2g/kg, Tłuszcz 25% energii, reszta Węgle)
    b = int(p["waga"] * 2.0)
    t = int((kcal * 0.25) / 9)
    w = int((kcal - (b * 4) - (t * 9)) / 4)
    return kcal, b, w, t

limit_kcal, limit_b, limit_w, limit_t = przelicz_zapotrzebowanie()

# --- NAWIGACJA DATĄ (GÓRNY PANEL) ---
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

# Pobierz dane dla wybranego dnia
if st.session_state.current_date not in st.session_state.db:
    st.session_state.db[st.session_state.current_date] = []
dzisiejsze_wpisy = st.session_state.db[st.session_state.current_date]

# --- PODSUMOWANIE DNIA (DASHBOARD) ---
total_kcal = sum(i["kcal"] for i in dzisiejsze_wpisy)
total_b = sum(i["b"] for i in dzisiejsze_wpisy)
total_w = sum(i["w"] for i in dzisiejsze_wpisy)
total_t = sum(i["t"] for i in dzisiejsze_wpisy)

st.progress(min(total_kcal / limit_kcal, 1.0) if limit_kcal > 0 else 0.0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{total_kcal}/{limit_kcal}")
col2.metric("Białko", f"{total_b}/{limit_b}g")
col3.metric("Węgle", f"{total_w}/{limit_w}g")
col4.metric("Tłuszcz", f"{total_t}/{limit_t}g")

# --- DODAWANIE NOWEGO POSIŁKU ---
st.write("")
with st.expander("➕ DODAJ POSIŁEK / SKANUJ"):
    rodzaj_posilku = st.selectbox("Gdzie dodać?", ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"])
    metoda = st.radio("Metoda wprowadzenia:", ["📸 Skanuj foto przez AI", "✍️ Napisz tekstowo (AI)", "✏️ Wpisz ręcznie (Znam makro)"], horizontal=False)
    
    nowy_posilek = None
    
    if "api_key" in st.session_state and st.session_state.api_key:
        genai.configure(api_key=st.session_state.api_key)
    
    if "AI" in metoda and (not st.session_state.get("api_key")):
        st.warning("⚠️ Wklej najpierw swój darmowy klucz API w ustawieniach na dole!")
        
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
        tekst = st.text_input("Co zjadłeś?", placeholder="np. owsianka z bananem i masłem orzechowym")
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
        st.session_state.db[st.session_state.current_date].append(nowy_posilek)
        st.success(f"Dodano do: {rodzaj_posilku}!")
        st.rerun()

# --- DZIENNIK POTRAW (STRUKTURA YAZIO) ---
st.write("")
kategorie = ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]

for kat in kategorie:
    w_kat = [i for i in dzisiejsze_wpisy if i["typ"] == kat]
    kat_kcal = sum(i["kcal"] for i in w_kat)
    
    st.markdown(f"""
    <div class='section-card'>
        <div class='meal-title'>
            <span>{kat}</span>
            <span style='color: #00C853;'>{kat_kcal} kcal</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not w_kat:
        st.markdown("<p style='color: #52525B; font-size: 12px; margin-left: 10px; margin-top: -5px;'>Brak posiłków</p>", unsafe_allow_html=True)
    else:
        for item in w_kat:
            col_txt, col_del = st.columns([6, 1])
            with col_txt:
                st.markdown(f"<div class='meal-item'><b>{item['nazwa']}</b><br><span style='color: #A1A1AA;'>🔥 {item['kcal']} kcal | B: {item['b']}g | W: {item['w']}g | T: {item['t']}g</span></div>", unsafe_allow_html=True)
            with col_del:
                if st.button("❌", key=f"del_{item['id']}"):
                    st.session_state.db[st.session_state.current_date] = [i for i in dzisiejsze_wpisy if i["id"] != item["id"]]
                    st.rerun()

# --- PANEL PROFILU I CONFIGU (NA SAMYM DOLE) ---
st.write("---")
with st.expander("⚙️ Twój Profil i Ustawienia (Waga, Wzrost, Wiek)"):
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

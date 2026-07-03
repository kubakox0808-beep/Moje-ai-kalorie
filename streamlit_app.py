import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime
import PIL.Image

# --- INTERFEJS SKROJONY POD IPHONE (MOBILE-FIRST) ---
st.set_page_config(page_title="Fitatu AI", page_icon="🍏", layout="centered")

# Agresywny CSS pod ekrany smartfonów
st.markdown("""
    <style>
    /* Usunięcie marginesów dla lepszego widoku na telefonie */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    .main { background-color: #0F0F10; color: #E4E4E7; }
    
    /* Stylizacja wielkich przycisków mobilnych */
    .stButton>button { 
        background-color: #22C55E; color: white; width: 100%; border-radius: 12px; 
        height: 55px; font-size: 16px; font-weight: bold; border: none; margin-bottom: 10px;
    }
    .stButton>button:active { background-color: #16A34A; }
    
    /* Wygląd wskaźników makro */
    div[data-testid="stMetricValue"] { font-size: 22px !important; color: #22C55E; font-weight: bold; }
    div[data-testid="stMetricLabel"] { font-size: 12px !important; }
    
    /* Dziennik posiłków na telefonie */
    .meal-row { background-color: #18181B; padding: 10px; border-radius: 10px; margin-bottom: 8px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# Pamięć podręczna aplikacji
if "history" not in st.session_state:
    st.session_state.history = []
if "limit_kcal" not in st.session_state:
    st.session_state.limit_kcal = 2000

# --- NAGŁÓWEK ---
st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>🍏 Moje Fitatu AI</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A1A1AA; font-size: 14px;'>Aparat lub tekst – szybko i bez klikania</p>", unsafe_allow_html=True)

# --- PANEL PODSUMOWANIA ---
total_kcal = sum(item["kcal"] for item in st.session_state.history)
total_b = sum(item["bialko"] for item in st.session_state.history)
total_w = sum(item["wegle"] for item in st.session_state.history)
total_t = sum(item["tluszcz"] for item in st.session_state.history)

pozostalo_kcal = st.session_state.limit_kcal - total_kcal
progress = min(total_kcal / st.session_state.limit_kcal, 1.0) if st.session_state.limit_kcal > 0 else 0.0

# Główny pasek postępu
st.progress(progress)

# Siatka makroskładników dostosowana do szerokości iPhone'a
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{total_kcal}/{st.session_state.limit_kcal}")
col2.metric("Białko", f"{total_b}g")
col3.metric("Węgle", f"{total_w}g")
col4.metric("Tłuszcz", f"{total_t}g")

if pozostalo_kcal >= 0:
    st.markdown(f"<div style='background-color: #14532D; padding: 8px; border-radius: 8px; text-align: center; font-size: 13px;'>Zostało: <b>{pozostalo_kcal} kcal</b></div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div style='background-color: #7F1D1D; padding: 8px; border-radius: 8px; text-align: center; font-size: 13px;'>Przekroczono o: <b>{abs(pozostalo_kcal)} kcal</b></div>", unsafe_allow_html=True)

# --- DODAWANIE POSIŁKÓW ---
st.write("")
tab1, tab2 = st.tabs(["📸 Zrób zdjęcie", "✍️ Wpisz / Podyktuj"])
result = None

with tab1:
    img_file = st.camera_input("Zrób zdjęcie", label_visibility="collapsed")
    if img_file:
        if st.button("🔍 Skanuj talerz przez AI", key="btn_foto"):
            with st.spinner("AI patrzy na talerz..."):
                if "api_key" in st.session_state and st.session_state.api_key:
                    genai.configure(api_key=st.session_state.api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    system_instruction = "Jesteś licznikiem kalorii. Przeanalizuj foto i zwróć wyłącznie JSON: {\"nazwa\": \"nazwa posiłku po polsku\", \"kcal\": 0, \"bialko\": 0, \"wegle\": 0, \"tluszcz\": 0}"
                    try:
                        img = PIL.Image.open(img_file)
                        response = model.generate_content([system_instruction, img])
                        raw_text = response.text.replace("```json", "").replace("```", "").strip()
                        result = json.loads(raw_text)
                    except Exception as e:
                        st.error("Błąd klucza API lub przetwarzania zdjęcia.")
                else:
                    st.warning("Wklej klucz API na dole ekranu!")

with tab2:
    text_input = st.text_input("Co zjadłeś? (Użyj mikrofonu)", placeholder="np. Kebab w cienkim, cola zero")
    if text_input and st.button("🔍 Podlicz tekst", key="btn_text"):
        with st.spinner("AI liczy..."):
            if "api_key" in st.session_state and st.session_state.api_key:
                genai.configure(api_key=st.session_state.api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                system_instruction = "Jesteś licznikiem kalorii. Przeanalizuj tekst i zwróć wyłącznie JSON: {\"nazwa\": \"nazwa posiłku po polsku\", \"kcal\": 0, \"bialko\": 0, \"wegle\": 0, \"tluszcz\": 0}"
                try:
                    response = model.generate_content([system_instruction, text_input])
                    raw_text = response.text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(raw_text)
                except Exception as e:
                    st.error("Błąd AI.")
            else:
                st.warning("Wklej klucz API na dole ekranu!")

# Zapisywanie posiłku
if result:
    st.session_state.history.append({
        "czas": datetime.now().strftime("%H:%M"),
        "nazwa": result["nazwa"],
        "kcal": int(result["kcal"]),
        "bialko": int(result["bialko"]),
        "wegle": int(result["wegle"]),
        "tluszcz": int(result["tluszcz"])
    })
    st.rerun()

# --- HISTORIA DNIA ---
st.markdown("<h4 style='margin-top: 15px; margin-bottom: 5px;'>📝 Dzisiejszy dziennik:</h4>", unsafe_allow_html=True)
if not st.session_state.history:
    st.markdown("<p style='color: #71717A; font-size: 13px;'>Brak wpisów. Zjedz coś!</p>", unsafe_allow_html=True)
else:
    for idx, item in enumerate(reversed(st.session_state.history)):
        real_idx = len(st.session_state.history) - 1 - idx
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"<div class='meal-row'>⏱️ <b>{item['czas']}</b> - {item['nazwa']}<br>🔥 {item['kcal']} kcal | B: {item['bialko']}g | W: {item['wegle']}g | T: {item['tluszcz']}g</div>", unsafe_allow_html=True)
        if c2.button("❌", key=f"del_{real_idx}"):
            st.session_state.history.pop(real_idx)
            st.rerun()

# --- USTAWIENIA NA SAMYM DOLE ---
st.write("---")
with st.expander("⚙️ Konfiguracja i profil"):
    st.session_state.api_key = st.text_input("Twój klucz Gemini API:", value=st.session_state.get("api_key", ""), type="password")
    st.session_state.limit_kcal = st.number_input("Twój dzienny cel kcal:", value=st.session_state.limit_kcal)
    if st.button("🗑️ Resetuj cały dzień", key="reset_all"):
        st.session_state.history = []
        st.rerun()

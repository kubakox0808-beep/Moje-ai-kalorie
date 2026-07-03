import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime
import PIL.Image

# --- KONFIGURACJA STRONY (STYL FITATU/YAZIO DARK) ---
st.set_page_config(page_title="Moje Fitatu AI", page_icon="🍏", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    .stButton>button { background-color: #4CAF50; color: white; width: 100%; border-radius: 10px; height: 50px; font-size: 18px;}
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

st.title("🍏 Moje Prywatne Fitatu AI")
st.subheader("Zrób zdjęcie lub wpisz posiłek – AI zajmie się resztą.")

# --- DZIENNIK POSIŁKÓW W PAMIĘCI ---
if "history" not in st.session_state:
    st.session_state.history = []
if "limit_kcal" not in st.session_state:
    st.session_state.limit_kcal = 2000  # Twój domyślny limit, możesz zmienić

# --- LEWY PANEL - USTAWIENIA ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    api_key = st.text_input("Wklej swój klucz Gemini API:", type="password")
    st.session_state.limit_kcal = st.number_input("Twój dzienny limit kcal:", value=st.session_state.limit_kcal)
    
    if st.button("🗑️ Wyczyść cały dzień"):
        st.session_state.history = []
        st.rerun()

# --- SPRAWDZENIE KLUCZA API ---
if not api_key:
    st.warning("👈 Aby zacząć, wklej swój darmowy klucz API w lewym panelu!")
    st.stop()

genai.configure(api_key=api_key)

# --- FUNKCJA ANALIZY AI ---
def analyze_meal(image=None, text_prompt=None):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    system_instruction = """
    Jesteś precyzyjnym licznikiem kalorii dostosowanym do polskich realiów kulinarnych. 
    Przeanalizuj przesłane zdjęcie lub tekst posiłku. Oszacuj wagę i podaj kalorie oraz makroskładniki.
    Zwróć wynik TYLKO I WYŁĄCZNIE jako czysty format JSON (bez żadnego dodatkowego tekstu, bez markdown, bez ```json):
    {
        "nazwa": "Nazwa dania po polsku",
        "kcal": 0,
        "bialko": 0,
        "wegle": 0,
        "tluszcz": 0
    }
    Jeśli na zdjęciu jest kilka rzeczy, zsumuj je w jeden posiłek. Bądź realistyczny w kwestii gramatury.
    """
    
    try:
        if image:
            img = PIL.Image.open(image)
            response = model.generate_content([system_instruction, img, "Oceń ten posiłek."])
        else:
            response = model.generate_content([system_instruction, text_prompt])
            
        # Oczyszczanie tekstu z ewentualnych znaczników markdown
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        st.error(f"Błąd AI: {e}")
        return None

# --- DODAWANIE POSIŁKU ---
st.write("---")
tab1, tab2 = st.tabs(["📸 Zrób zdjęcie / Wgraj foto", "✍️ Wpisz tekst / Podyktuj"])

result = None

with tab1:
    source = st.radio("Źródło obrazu:", ["Aparat (Telefon)", "Galeria zdjęć"], horizontal=True)
    if source == "Aparat (Telefon)":
        img_file = st.camera_input("Zrób zdjęcie posiłku")
    else:
        img_file = st.file_uploader("Wybierz zdjęcie z galerii", type=["jpg", "jpeg", "png"])
        
    if img_file and st.button("🔍 Analizuj zdjęcie przez AI"):
        with st.spinner("Sztuczna inteligencja analizuje Twój talerz..."):
            result = analyze_meal(image=img_file)

with tab2:
    text_input = st.text_area("Wpisz na luzie co zjadłeś (np. 'Zapiekanka z Żabki i puszka coli zero' albo '3 jajka sadzone na maśle')", "")
    if text_input and st.button("🔍 Dodaj tekstowo przez AI"):
        with st.spinner("AI podlicza posiłek..."):
            result = analyze_meal(text_prompt=text_input)

# Jeśli AI zwróciło wynik, dodaj do historii
if result:
    st.session_state.history.append({
        "czas": datetime.now().strftime("%H:%M"),
        "nazwa": result["nazwa"],
        "kcal": int(result["kcal"]),
        "bialko": int(result["bialko"]),
        "wegle": int(result["wegle"]),
        "tluszcz": int(result["tluszcz"])
    })
    st.success(f"Dodano: {result['nazwa']} (+{result['kcal']} kcal)")
    st.rerun()

# --- PODSUMOWANIE DNIA (W STYLU YAZIO) ---
st.write("---")
st.header("📊 Podsumowanie dzisiejszego dnia")

total_kcal = sum(item["kcal"] for item in st.session_state.history)
total_b = sum(item["bialko"] for item in st.session_state.history)
total_w = sum(item["wegle"] for item in st.session_state.history)
total_t = sum(item["tluszcz"] for item in st.session_state.history)

# Pasek postępu kalorii
pozostalo_kcal = st.session_state.limit_kcal - total_kcal
progress = min(total_kcal / st.session_state.limit_kcal, 1.0) if st.session_state.limit_kcal > 0 else 0.0
st.progress(progress)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Zjedzone Kcal", f"{total_kcal} / {st.session_state.limit_kcal}")
col2.metric("Białko (B)", f"{total_b}g")
col3.metric("Węgle (W)", f"{total_w}g")
col4.metric("Tłuszcz (T)", f"{total_t}g")

if pozostalo_kcal >= 0:
    st.info(f"💡 Możesz jeszcze dzisiaj zjeść: **{pozostalo_kcal} kcal**")
else:
    st.error(f"⚠️ Przekroczyłeś limit o: **{abs(pozostalo_kcal)} kcal**")

# --- LISTA POSIŁKÓW (HISTORIA) ---
st.write("---")
st.header("📝 Dzisiejszy dziennik")

if not st.session_state.history:
    st.info("Twój dziennik jest pusty. Dodaj pierwszy posiłek powyżej!")
else:
    for idx, item in enumerate(reversed(st.session_state.history)):
        real_idx = len(st.session_state.history) - 1 - idx
        
        with st.container():
            c1, c2, c3 = st.columns([1, 4, 1])
            c1.write(f"⏱️ {item['czas']}")
            c2.write(f"**{item['nazwa']}** — 🔥 {item['kcal']} kcal | B: {item['bialko']}g | W: {item['wegle']}g | T: {item['tluszcz']}g")
            if c3.button("❌", key=f"del_{real_idx}"):
                st.session_state.history.pop(real_idx)
                st.rerun()

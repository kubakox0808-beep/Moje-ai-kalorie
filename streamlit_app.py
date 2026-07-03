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

# --- ULTRA-MOBILNY STYL CSS ---
css = ""
css += "<style>"
css += ".block-container { padding: 0.5rem 0.5rem; }"
css += ".main { background-color: #09090B; color: #FAFAFA; }"
# Przyciski dostosowane do kciuka
css += ".stButton>button { "
css += "background: linear-gradient(135deg, #00E676 0%, #00C853 100%); "
css += "color: white; width: 100%; border-radius: 12px; "
css += "height: 45px; font-size: 14px; font-weight: 700; border: none; }"
# Kompaktowe metryki obok siebie
css += "div[data-testid='stMetricValue'] { "
css += "font-size: 16px !important; color: #00E676; font-weight: 800; }"
css += "div[data-testid='stMetricLabel'] { "
css += "font-size: 11px !important; color: #A1A1AA; }"
css += "div[data-testid='stMetric'] { "
css += "background-color: #18181B; padding: 6px; border-radius: 10px; "
css += "border: 1px solid #27272A; text-align: center; }"
# Karty posiłków na całą szerokość ekranu telefonu
css += ".section-card { "
css += "background: #18181B; padding: 10px; border-radius: 12px; "
css += "margin-top: 8px; border: 1px solid #27272A; }"
css += ".meal-title { "
css += "font-size: 14px; font-weight: 700; color: #FFFFFF; "
css += "display: flex; justify-content: space-between; }"
css += ".meal-kcal { "
css += "background: rgba(0, 230, 118, 0.15); color: #00E676; "
css += "padding: 1px 6px; border-radius: 8px; font-size: 11px; }"
css += ".product-row { "
css += "background: #121214; padding: 8px; border-radius: 10px; "
css += "margin-top: 4px; border-left: 3px solid #00E676; }"
css += "</style>"

st.markdown(css, unsafe_allow_html=True)

# --- BAZA DANYCH ---
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

# --- FUNKCJE API ---
def akcja_szukaj(txt):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    prm = {"search_terms": txt, "search_simple": 1, "action": "process", "json": 1, "page_size": 5}
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
        prmt = "Zwroc tylko JSON: {\"nazwa\": \"X\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
        if is_image:
            img = PIL.Image.open(user_input)
            raw = model.generate_content([prmt, img]).text
        else:
            raw = model.generate_content([prmt, user_input]).text
        
        czysty = raw.strip()
        if "```" in czysty:
            czysty = czysty.replace("```json", "").replace("```", "")
        return json.loads(czysty.strip())
    except:
        st.error("Blad AI")
        return None

# --- KALKULATOR DIETY ---
p = st.session_state.profil
bmr = (10 * p["waga"]) + (6.25 * p["wzrost"]) - (5 * p["wiek"])
bmr += 5 if p["plec"] == "Mężczyzna" else -161
pal = 1.2 if p["aktywnosc"] == "Niska" else (1.4 if p["aktywnosc"] == "Średnia" else 1.6)
limit_kcal = bmr * pal
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
    st.session_state.db[st.session_state.current_date] = {"posilki": [], "woda": 0}
dzisiejsze_dane = st.session_state.db[st.session_state.current_date]

# --- TOP BAR: NAWIGACJA (MIEŚCI SIĘ W JEDNEJ LINII NA TELEFONIE) ---
c_prev, c_date, c_next = st.columns([1, 3, 1])
with c_prev:
    if st.button("◀", key="p_day"):
        st.session_state.current_date = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()
with c_date:
    st.markdown(f"<h4 style='text-align:center;margin-top:8px;font-size:16px;'>🍏 {st.session_state.current_date}</h4>", unsafe_allow_html=True)
with c_next:
    if st.button("▶", key="n_day"):
        st.session_state.current_date = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        st.rerun()

# --- WYLICZENIA MAKRO ---
tkcal, tb, tw, tt = 0, 0, 0, 0
for i in dzisiejsze_dane.get("posilki", []):
    tkcal += i.get("kcal", 0)
    tb += i.get("b", 0)
    tw += i.get("w", 0)
    tt += i.get("t", 0)

# Pasek progresu i kafelki 2x2 idealne na ekran smartfona
st.progress(min(tkcal / max(limit_kcal, 1), 1.0))
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{tkcal}\n/ {limit_kcal}")
col2.metric("Białko", f"{tb}g\n/ {limit_b}g")
col3.metric("Węgle", f"{tw}g\n/ {limit_w}g")
col4.metric("Tłuszcz", f"{tt}g\n/ {limit_t}g")

st.write("")

# --- NOWY MOBILNY PANEL DODAWANIA (ZAMIAST TABSÓW) ---
with st.expander("➕ DODAJ POSIŁEK / SKANUJ AI", expanded=False):
    kat_wyb = st.selectbox("Wybierz kategorię:", ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"])
    
    # Ikony zamiast długich napisów – mieści się idealnie w poziomie na telefonie
    m_wyb = st.radio("Metoda:", ["🔍 Baza", "📸 Foto", "✍️ Tekst", "⚙️ Ręcznie"], horizontal=True)
    res_posilek = None

    if "Baza" in m_wyb:
        stxt = st.text_input("Nazwa produktu:", placeholder="np. Banan")
        if stxt:
            w = akcja_szukaj(stxt)
            if w:
                wyb = st.selectbox("Wyniki wyszukiwania:", w, format_func=lambda x: f"{x['nazwa']} ({x['kcal_100g']} kcal)")
                g = st.number_input("Waga w gramach:", min_value=1, value=100)
                if st.button("Dodaj do dziennika"):
                    m = g / 100.0
                    res_posilek = {
                        "nazwa": f"{wyb['nazwa']} ({g}g)",
                        "kcal": int(wyb['kcal_100g'] * m),
                        "b": int(wyb['b_100g'] * m),
                        "w": int(wyb['w_100g'] * m),
                        "t": int(wyb['t_100g'] * m)
                    }

    elif "Foto" in m_wyb:
        f = st.camera_input("Zrób zdjęcie posiłku:")
        if f and st.button("Skanuj talerz przez AI"):
            res_posilek = akcja_gemini(f, is_image=True)

    elif "Tekst" in m_wyb:
        t = st.text_input("Co zjadłeś?", placeholder="np. 3 jajka sadzone i kromka chleba")
        if t and st.button("Przelicz przez AI"):
            res_posilek = akcja_gemini(t, is_image=False)

    elif "Ręcznie" in m_wyb:
        with st.form("f_m"):
            rn = st.text_input("Nazwa:", "Wpis własny")
            rk = st.number_input("Kcal:", value=0)
            rb = st.number_input("Białko (g):", value=0)
            rw = st.number_input("Węgle (g):", value=0)
            rt = st.number_input("Tłuszcz (g):", value=0)
            if st.form_submit_button("Zapisz kalorie"):
                res_posilek = {"nazwa": rn, "kcal": int(rk), "b": int(rb), "w": int(rw), "t": int(rt)}

    if res_posilek:
        res_posilek["typ"] = kat_wyb
        res_posilek["id"] = datetime.now().timestamp()
        st.session_state.db[st.session_state.current_date]["posilki"].append(res_posilek)
        zapisz_baze(st.session_state.db)
        st.success("Dodano!")
        st.rerun()

# --- DZIENNIK GŁÓWNY (ZGRABNY I PRZEJRZYSTY) ---
st.write("")
woda_ile = dzisiejsze_dane.get('woda', 0)
cw1, cw2 = st.columns([2, 1])
with cw1:
    st.markdown(f"💧 **Woda:** {woda_ile} / 2500 ml")
with cw2:
    if st.button("🥤 +250ml", key="woda_b"):
        st.session_state.db[st.session_state.current_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()

kat_list = ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]
for kat in kat_list:
    w_kat = [i for i in dzisiejsze_dane.get("posilki", []) if i.get("typ") == kat]
    skcal = sum(i.get("kcal", 0) for i in w_kat)
    
    card = f"<div class='section-card'><div class='meal-title'><span>{kat}</span><span class='meal-kcal'>{skcal} kcal</span></div></div>"
    st.markdown(card, unsafe_allow_html=True)
    
    for item in w_kat:
        cl, cp = st.columns([5, 1])
        with cl:
            row = f"<div class='product-row'><b>{item.get('nazwa')}</b><br><span style='color:#71717A;font-size:11px;'>🔥 {item.get('kcal')} kcal | B:{item.get('b')}g W:{item.get('w')}g T:{item.get('t')}g</span></div>"
            st.markdown(row, unsafe_allow_html=True)
        with cp:
            st.write("")
            if st.button("❌", key=f"d_{item.get('id')}"):
                nowa_l = [i for i in dzisiejsze_dane["posilki"] if i.get("id") != item.get("id")]
                st.session_state.db[st.session_state.current_date]["posilki"] = nowa_l
                zapisz_baze(st.session_state.db)
                st.rerun()

# --- USTAWIENIA PROFILU NA SAMYM DOLE W EXPANDERZE ---
st.write("")
with st.expander("⚙️ USTAWIENIA PROFILU & API"):
    st.session_state.api_key = st.text_input("Klucz Gemini:", value=st.session_state.get("api_key", ""), type="password")
    st.session_state.profil["plec"] = st.radio("Płeć:", ["Mężczyzna", "Kobieta"], horizontal=True)
    st.session_state.profil["waga"] = st.number_input("Waga (kg):", value=st.session_state.profil["waga"])
    st.session_state.profil["wzrost"] = st.number_input("Wzrost (cm):", value=st.session_state.profil["wzrost"])
    st.session_state.profil["wiek"] = st.number_input("Wiek:", value=st.session_state.profil["wiek"])
    st.session_state.profil["aktywnosc"] = st.selectbox("Aktywność:", ["Niska", "Średnia", "Wysoka"])
    st.session_state.profil["cel"] = st.selectbox("Cel:", ["Redukcja", "Utrzymanie wagi", "Masa"])
    if st.button("Zapisz ustawienia"):
        st.rerun()

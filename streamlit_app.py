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

# --- BEZPIECZNY, ROZBITY STYL CSS ---
css = ""
css += "<style>"
css += ".block-container { padding: 1rem 0.75rem; }"
css += ".main { background-color: #09090B; color: #FAFAFA; }"
css += ".stButton>button { "
css += "background: linear-gradient(135deg, #00E676 0%, #00C853 100%); "
css += "color: white; width: 100%; border-radius: 16px; "
css += "height: 50px; font-size: 16px; font-weight: 700; border: none; }"
css += "div[data-testid='stMetricValue'] { "
css += "font-size: 22px !important; color: #00E676; font-weight: 800; }"
css += "div[data-testid='stMetricLabel'] { "
css += "font-size: 12px !important; color: #A1A1AA; }"
css += "div[data-testid='stMetric'] { "
css += "background-color: #18181B; padding: 12px; border-radius: 14px; "
css += "border: 1px solid #27272A; text-align: center; }"
css += ".section-card { "
css += "background: #18181B; padding: 14px; border-radius: 16px; "
css += "margin-top: 12px; border: 1px solid #27272A; }"
css += ".meal-title { "
css += "font-size: 16px; font-weight: 700; color: #FFFFFF; "
css += "display: flex; justify-content: space-between; }"
css += ".meal-kcal { "
css += "background: rgba(0, 230, 118, 0.15); color: #00E676; "
css += "padding: 2px 8px; border-radius: 12px; font-size: 12px; }"
css += ".product-row { "
css += "background: #121214; padding: 10px; border-radius: 12px; "
css += "margin-top: 6px; border-left: 3px solid #00E676; }"
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

# --- FUNKCJE ---
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
        prmt = "Zwroc tylko JSON: {\"nazwa\": \"X\", \"kcal\": 0, \"b\": 0, \"w\": 0, \"t\": 0}"
        if is_image:
            img = PIL.Image.open(user_input)
            raw = model.generate_content([prmt, img]).text
        else:
            raw = model.generate_content([prmt, user_input]).text
        
        czysty = raw.strip()
        if "```" in czysty:
            czysty = czysty.replace("```json", "")
            czysty = czysty.replace("```", "")
        return json.loads(czysty.strip())
    except:
        st.error("Blad AI")
        return None

# --- OBLICZENIA KALORII ---
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

# --- LICZNIKI ---
tkcal, tb, tw, tt = 0, 0, 0, 0
for i in dzisiejsze_dane.get("posilki", []):
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

# --- ZAKŁADKA: DZIENNIK ---
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
        
        skcal = sum(i.get("kcal", 0) for i in w_kat)
        
        card = ""
        card += "<div class='section-card'><div class='meal-title'>"
        card += f"<span>{kat}</span>"
        card += f"<span class='meal-kcal'>{skcal} kcal</span>"
        card += "</div></div>"
        st.markdown(card, unsafe_allow_html=True)
        
        for item in w_kat:
            cl, cp = st.columns([5, 1])
            with cl:
                row = ""
                row += "<div class='product-row'>"
                row += f"<b>{item.get('nazwa')}</b><br>"
                row += "<span style='color:#71717A;font-size:12px;'>"
                row += f"🔥 {item.get('kcal')} kcal | "
                row += f"B:{item.get('b')}g W:{item.get('w')}g T:{item.get('t')}g"
                row += "</span></div>"
                st.markdown(row, unsafe_allow_html=True)
            with cp:
                st.write("")
                if st.button("❌", key=f"d_{item.get('id')}"):
                    nowa_l = [i for i in dzisiejsze_dane["posilki"] if i.get("id") != item.get("id")]
                    st.session_state.db[st.session_state.current_date]["posilki"] = nowa_l
                    zapisz_baze(st.session_state.db)
                    st.rerun()

# --- ZAKŁADKA: DODAJ ---
with t_dodaj:
    kat_wyb = st.selectbox("Kategoria:", [
        "Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"
    ])
    metoda = st.radio("Metoda:", ["Baza", "Foto", "Tekst", "Recznie"], horizontal=True)
    res_posilek = None

    if metoda == "Baza":
        stxt = st.text_input("Szukaj:")
        if stxt:
            w = akcja_szukaj(stxt)
            if w:
                wyb = st.selectbox(
                    "Wynik:", 
                    w, 
                    format_func=lambda x: f"{x['nazwa']} ({x['kcal_100g']} kcal)"
                )
                g = st.number_input("Gramy:", min_value=1, value=100)
                if st.button("Dodaj produkt"):
                    m = g / 100.0
                    res_posilek = {}
                    res_posilek["nazwa"] = wyb['nazwa'] + " (" + str(g) + "g)"
                    res_posilek["kcal"] = int(wyb['kcal_100g'] * m)
                    res_posilek["b"] = int(wyb['b_100g'] * m)
                    res_posilek["w"] = int(wyb['w_100g'] * m)
                    res_posilek["t"] = int(wyb['t_100g'] * m)

    if metoda == "Foto":
        f = st.camera_input("Foto:")
        if f and st.button("Skanuj AI"):
            res_posilek = akcja_gemini(f, is_image=True)

    if metoda == "Tekst":
        t = st.text_input("Napisz co zjadłeś:")
        if t and st.button("Licz AI"):
            res_posilek = akcja_gemini(t, is_image=False)

    if metoda == "Recznie":
        with st.form("f_m"):
            rn = st.text_input("Nazwa:", "Wpis")
            rk = st.number_input("Kcal:", value=100)
            rb = st.number_input("Białko:", value=0)
            rw = st.number_input("Węgle:", value=0)
            rt = st.number_input("Tłuszcz:", value=0)
            if st.form_submit_button("Zapisz"):
                res_posilek = {
                    "nazwa": rn, 
                    "kcal": int(rk), 
                    "b": int(rb), 
                    "w": int(rw), 
                    "t": int(rt)
                }

    if res_posilek:
        res_posilek["typ"] = kat_wyb
        res_posilek["id"] = datetime.now().timestamp()
        st.session_state.db[st.session_state.current_date]["posilki"].append(res_posilek)
        zapisz_baze(st.session_state.db)
        st.success("Dodano!")
        st.rerun()

# --- ZAKŁADKA: PROFIL ---
with t_profil:
    st.session_state.api_key = st.text_input(
        "Klucz Gemini:", 
        value=st.session_state.get("api_key", ""), 
        type="password"
    )
    st.session_state.profil["plec"] = st.radio(
        "Płeć:", 
        ["Mężczyzna", "Kobieta"], 
        horizontal=True
    )
    st.session_state.profil["waga"] = st.number_input(
        "Waga (kg):", 
        value=st.session_state.profil["waga"]
    )
    st.session_state.profil["wzrost"] = st.number_input(
        "Wzrost (cm):", 
        value=st.session_state.profil["wzrost"]
    )
    st.session_state.profil["wiek"] = st.number_input(
        "Wiek:", 
        value=st.session_state.profil["wiek"]
    )
    st.session_state.profil["aktywnosc"] = st.selectbox(
        "Aktywność:", 
        ["Niska", "Średnia", "Wysoka"]
    )
    st.session_state.profil["cel"] = st.selectbox(
        "Cel:", 
        ["Redukcja", "Utrzymanie wagi", "Masa"]
    )
    if st.button("Zapisz profil"):
        st.rerun()

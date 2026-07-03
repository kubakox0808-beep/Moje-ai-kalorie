import streamlit as st
import google.generativeai as genai
import json
import os
import requests
from datetime import datetime, timedelta
import PIL.Image

st.set_page_config(
    page_title="Yazio Clone",
    page_icon="🍏",
    layout="centered"
)

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
        prmt = "Zwroc tylko JSON bez markdown: "
        prmt += '{"nazwa": "X", "kcal": 0, "b": 0, "w": 0, "t": 0}'
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

# --- ZAPOTRZEBOWANIE ---
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

# --- NAWIGACJA ---
st.title("🍏 Aplikacja Kcal")
c_prev, c_date, c_next = st.columns([1, 4, 1])
with c_prev:
    if st.button("◀", key="p_day"):
        prev_str = (curr_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        st.session_state.current_date = prev_str
        st.rerun()
with c_date:
    st.subheader(st.session_state.current_date)
with c_next:
    if st.button("▶", key="n_day"):
        next_str = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        st.session_state.current_date = next_str
        st.rerun()

# --- WYLICZENIA ---
tkcal, tb, tw, tt = 0, 0, 0, 0
for i in dzisiejsze_dane.get("posilki", []):
    tkcal += i.get("kcal", 0)
    tb += i.get("b", 0)
    tw += i.get("w", 0)
    tt += i.get("t", 0)

progres_val = 0.0
if limit_kcal > 0:
    progres_val = min(tkcal / limit_kcal, 1.0)
st.progress(progres_val)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{tkcal}/{limit_kcal}")
col2.metric("Białko", f"{tb}g/{limit_b}g")
col3.metric("Węgle", f"{tw}g/{limit_w}g")
col4.metric("Tłuszcz", f"{tt}g/{limit_t}g")

t_dziennik, t_dodaj, t_profil = st.tabs([
    "📅 Dziennik", 
    "➕ Dodaj", 
    "⚙️ Profil"
])

# --- DZIENNIK ---
with t_dziennik:
    woda_ile = dzisiejsze_dane.get('woda', 0)
    st.subheader(f"💧 Woda: {woda_ile} / 2500 ml")
    if st.button("➕ Wypij 250ml", key="woda_b"):
        st.session_state.db[st.session_date]["woda"] += 250
        zapisz_baze(st.session_state.db)
        st.rerun()
    
    kat_list = ["Śniadanie", "Drugie śniadanie", "Obiad", "Kolacja", "Przekąski"]
    for kat in kat_list:
        st.write(f"### {kat}")
        w_kat = []
        for i in dzisiejsze_dane.get("posilki", []):
            if i.get("typ") == kat:
                w_kat.append(i)
        
        if not w_kat:
            st.text("Brak posiłków")
        
        for item in w_kat:
            cl, cp = st.columns([5, 1])
            with cl:
                txt_p = f"**{item.get('nazwa')}** - {item.get('kcal')} kcal "
                txt_p += f"(B:{item.get('b')}g W:{item.get('w')}g T:{item.get('t')}g)"
                st.write(txt_p)
            with cp:
                if st.button("❌", key=f"d_{item.get('id')}"):
                    nowa_lista = []
                    for i in dzisiejsze_dane["posilki"]:
                        if i.get("id") != item.get("id"):
                            nowa_lista.append(i)
                    st.session_state.db[st.session_state.current_date]["posilki"] = nowa_lista
                    zapisz_baze(st.session_state.db)
                    st.rerun()

# --- DODAWANIE ---
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

# --- PROFIL ---
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

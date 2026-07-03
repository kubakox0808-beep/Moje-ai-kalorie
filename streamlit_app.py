# --- DODAJ TO W SEKCJI "DZIENNIK" LUB POD NIM ---

def przeprowadz_analize_ai():
    if not st.session_state.get("api_key"):
        return "Brak klucza API."
    
    # Przygotowanie danych dla AI
    dzien = st.session_state.db.get(st.session_state.current_date, {})
    posilki = dzien.get("posilki", [])
    if not posilki:
        return "Brak posiłków do analizy."
    
    genai.configure(api_key=st.session_state.api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"Oto mój dzienny jadłospis: {posilki}. "
    prompt += "Oceń krótko: czy jest zdrowo? Czego brakuje (Białko/Węgle/Tłuszcze)? "
    prompt += "Daj 3 krótkie porady. Bądź surowy, pisz po polsku."
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Błąd połączenia z AI."

# --- UMIEŚĆ TEN PRZYCISK W GŁÓWNEJ CZĘŚCI (NP. POD METRYKAMI) ---
if st.button("🚀 ANALIZUJ DZIEŃ (AI)"):
    with st.spinner("AI analizuje Twój talerz..."):
        wynik = przeprowadz_analize_ai()
        st.info(wynik)

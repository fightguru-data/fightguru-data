import streamlit as st
import pandas as pd
import os
import threading
import telebot
from PIL import Image

# --- ПАРАМЕТРЫ ТЕЛЕГРАМ-БОТА ---
BOT_TOKEN = '8677319918:AAHqlbO9FnZ1lcLkM1WLWfZ2vC9q_8gyc6c'

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
try:
    logo_img = Image.open("logo.png")
except:
    logo_img = "🥋"

st.set_page_config(page_title="FIGHTGURU DATA CENTER", page_icon=logo_img, layout="wide")

# --- СТИЛИЗАЦИЯ (MOBILE OPTIMIZED CSS) ---
st.markdown("""
<style>
    .main .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 2rem; }
    .match-card {
        background: #111111;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 8px solid #444;
    }
    .win-card { border-left-color: #28a745 !important; }
    .loss-card { border-left-color: #e63946 !important; }
    .match-header {
        font-size: 11px;
        color: #777;
        text-transform: uppercase;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        font-weight: 700;
    }
    .match-round {
        background: #222;
        color: #eee;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
    }
    .match-tournament { font-weight: 800; color: #ffffff; font-size: 13px; margin-bottom: 8px; line-height: 1.2; }
    .match-main { display: flex; justify-content: space-between; align-items: center; }
    .opponent-name { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 2px; }
    .opponent-country { font-size: 12px; color: #999; text-transform: uppercase; }
    .match-score { font-size: 24px; font-weight: 900; color: #e63946; text-align: right; min-width: 70px; }
    .match-cat { font-size: 11px; color: #e63946; font-weight: 700; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# --- СПРАВОЧНИКИ ---
ROUND_NAMES = {
    "FNL": "ФИНАЛ", "FIN": "ФИНАЛ", "SFL": "1/2 ФИНАЛА", "QFL": "1/4 ФИНАЛА",
    "R16": "1/8 ФИНАЛА", "R32": "1/16 ФИНАЛА", "R64": "1/32 ФИНАЛА", 
    "R128": "1/64 ФИНАЛА", "REP": "УТЕШИТЕЛЬНЫЙ БОЙ", "PRL": "ПРЕДВАРИТЕЛЬНЫЙ"
}

FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", 
    "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯", "TKM": "🇹🇲", "AIN": "🏳️", "FRA": "🇫🇷", "SRB": "🇷🇸", 
    "USA": "🇺🇸", "UKR": "🇺🇦", "BUL": "🇧🇬", "CRO": "🇭🇷", "MKD": "🇲🇰", "ROU": "🇷🇴", "ISR": "🇮🇱", 
    "ITA": "🇮🇹", "ESP": "🇪🇸", "GER": "🇩🇪", "LAT": "🇱🇻", "LTU": "🇱🇹", "EST": "🇪🇪", "GRE": "🇬🇷", 
    "HUN": "🇭🇺", "NED": "🇳🇱", "MAR": "🇲🇦", "CMR": "🇨🇲", "KOR": "🇰🇷", "JPN": "🇯🇵", "MDA": "🇲🇩"
}

COUNTRY_NAMES_RU = {
    "RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН", 
    "MGL": "МОНГОЛИЯ", "GEO": "ГРУЗИЯ", "ARM": "АРМЕНИЯ", "AZE": "АЗЕРБАЙДЖАН", "TJK": "ТАДЖИКИСТАН", 
    "TKM": "ТУРКМЕНИСТАН", "AIN": "НЕЙТР. АТЛЕТ", "UKR": "УКРАИНА", "BUL": "БОЛГАРИЯ", "CRO": "ХОРВАТИЯ", 
    "MKD": "МАКЕДОНИЯ", "ROU": "РУМЫНИЯ", "ISR": "ИЗРАИЛЬ", "ITA": "ИТАЛИЯ", "ESP": "ИСПАНИЯ", 
    "FRA": "ФРАНЦИЯ", "GER": "ГЕРМАНИЯ", "MDA": "МОЛДОВА", "SRB": "СЕРБИЯ", "USA": "США"
}

TOURNAMENT_GROUPS = {
    "Чемпионат Мира": ["World Sambo Championships", "World SAMBO Championships"],
    "Кубок Мира": ["Cup", "President"],
    "Чемпионат Европы": ["European Sambo Championships", "European Championships"],
    "ЧМ Азии и Океании": ["Asia and Oceania Sambo Championships"]
}
DIVISIONS = {"Спортивное Самбо (М)": "samm", "Спортивное Самбо (Ж)": "samw", "Боевое Самбо (М)": "csmm", "Боевое Самбо (Ж)": "csmw"}

# --- ФУНКЦИИ ---
def get_flag(c): return FLAG_EMOJIS.get(str(c).upper().strip(), "🌍")
def get_full_country(c): return COUNTRY_NAMES_RU.get(str(c).upper().strip(), str(c))
def get_round_name(c): return ROUND_NAMES.get(str(c).upper().strip(), str(c))

def get_readable_cat(code):
    c = str(code).upper().strip()
    p = ""
    if "SAMM" in c: p = "Спорт М"
    elif "SAMW" in c: p = "Спорт Ж"
    elif "CSMM" in c: p = "Боевое М"
    elif "CSMW" in c: p = "Боевое Ж"
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts) > 1:
            raw = parts[1]
            w = (raw[:-1] + "+") if raw.endswith('O') else raw
    return (p + " " + w + "кг").strip() if p else c

@st.cache_data(ttl=3600)
def load_data_v55():
    if not os.path.exists("AllTournament.csv"): return None
    try:
        df = pd.read_csv("AllTournament.csv", low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]
        for col in ['winner_athlete_id', 'red_id', 'blue_id']:
            df[col] = df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None)
        df['red_full_name'] = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
        df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
        df['date_start'] = pd.to_datetime(df['date_start'], errors='coerce')
        df['Human_Category'] = df['category_code'].apply(get_readable_cat)
        
        dob_cols = [c for c in df.columns if any(x in c for x in ['birth', 'birthday', 'рождения'])]
        df['athlete_dob'] = df[dob_cols[0]].fillna('Н/Д') if dob_cols else 'Н/Д'

        df['red_score'] = pd.to_numeric(df['red_score'], errors='coerce').fillna(0).astype(int)
        df['blue_score'] = pd.to_numeric(df['blue_score'], errors='coerce').fillna(0).astype(int)
        return df
    except: return None

df = load_data_v55()

# --- ТЕЛЕГРАМ БОТ ---
def start_bot():
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    @bot.message_handler(commands=['start'])
    def welcome(m): bot.reply_to(m, "FIGHTGURU: Фамилия (лат)?")
    @bot.message_handler(func=lambda m: True)
    def search_tg(m):
        q = m.text.strip().lower()
        if len(q) < 3: return
        try:
            data = pd.read_csv("AllTournament.csv", low_memory=False)
            data.columns = [c.strip().lower() for c in data.columns]
            res = data[(data['red_last_name'].str.lower().str.contains(q, na=False)) | 
                       (data['blue_last_name'].str.lower().str.contains(q, na=False))].copy()
            if res.empty: return
            res['date_start'] = pd.to_datetime(res['date_start'], errors='coerce')
            res = res.sort_values('date_start', ascending=False).head(10)
            msg = "👤 " + q.upper() + "\n" + "="*15 + "\n"
            for _, r in res.iterrows():
                win = "✅" if str(r['winner_athlete_id']) == (str(r['red_id']) if q in str(r['red_last_name']).lower() else str(r['blue_id'])) else "❌"
                msg += win + " " + str(r['date_start'].year) + " | " + str(int(r['red_score'])) + ":" + str(int(r['blue_score'])) + "\n"
            bot.send_message(m.chat.id, msg)
        except: pass
    bot.infinity_polling(timeout=20)

if "bot_active" not in st.session_state:
    threading.Thread(target=start_bot, daemon=True).start()
    st.session_state.bot_active = True

# --- ИНТЕРФЕЙС ---
if df is not None:
    nav = st.sidebar.radio("Меню", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        st.subheader("👤 Досье Спортсмена")
        search = st.text_input("Фамилия (Osipenko, Mikhailin...):").lower().strip()
        
        if search:
            m = df[(df['red_last_name'].str.lower().str.contains(search, na=False)) | 
                   (df['blue_last_name'].str.lower().str.contains(search, na=False))].copy()
            
            if not m.empty:
                m = m.sort_values('date_start', ascending=False)
                sample = m.iloc[0]
                name = sample['red_full_name'] if search in sample['red_last_name'].lower() else sample['blue_full_name']
                
                st.markdown(f"### {name.upper()}")
                st.markdown(f"**Д.Р.:** {sample['athlete_dob']}")
                st.divider()

                for _, r in m.iterrows():
                    is_red = search in str(r['red_last_name']).lower()
                    win_id = str(r['winner_athlete_id'])
                    is_win = (is_red and win_id == str(r['red_id'])) or (not is_red and win_id == str(r['blue_id']))
                    
                    opp_name = r['blue_full_name'] if is_red else r['red_full_name']
                    opp_nat = r['blue_nationality_code'] if is_red else r['red_nationality_code']
                    
                    c_class = "match-card win-card" if is_win else "match-card loss-card"
                    s_icon = "✅ ПОБЕДА" if is_win else "❌ ПОРАЖЕНИЕ"
                    round_txt = get_round_name(r['round_code'])
                    
                    st.markdown(f"""
                    <div class="{c_class}">
                        <div class="match-header">
                            <span>{r['date_start'].strftime('%d.%m.%Y') if pd.notna(r['date_start']) else '????'}</span>
                            <span class="match-round">{round_txt}</span>
                            <span>{s_icon}</span>
                        </div>
                        <div class="match-tournament">{str(r['tournament_name']).upper()}</div>
                        <div class="match-main">
                            <div>
                                <div class="opponent-name">{opp_name}</div>
                                <div class="opponent-country">{get_flag(opp_nat)} {get_full_country(opp_nat)}</div>
                                <div class="match-cat">{r['Human_Category']}</div>
                            </div>
                            <div class="match-score">{int(r['red_score'])}:{int(r['blue_score'])}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Атлет не найден.")

    elif nav == "🏛️ Пантеон":
        st.subheader("🏛️ Исторический Пантеон")
        t_sel = st.selectbox("Турнир", list(TOURNAMENT_GROUPS.keys()))
        d_sel = st.selectbox("Дивизион", list(DIVISIONS.keys()))
        pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
        f_data = df[df['tournament_name'].str.contains(pattern, case=False, na=False)]
        f_data = f_data[f_data['category_code'].str.contains(DIVISIONS[d_sel], case=False, na=False)]
        fin = f_data[f_data['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
        if not fin.empty:
            def get_w(r):
                if str(r['winner_athlete_id']) == str(r['red_id']):
                    return r['red_full_name'], str(r['red_nationality_code']).upper()
                return r['blue_full_name'], str(r['blue_nationality_code']).upper()
            fin[['w_name', 'w_country']] = fin.apply(lambda r: pd.Series(get_w(r)), axis=1)
            st.dataframe(fin.groupby('w_country').size().reset_index(name='Gold').sort_values('Gold', ascending=False), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

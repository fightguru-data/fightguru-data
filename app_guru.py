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

# --- СТИЛИЗАЦИЯ (ADVANCED MOBILE UI) ---
st.markdown("""
<style>
    .main .block-container { padding-left: 0.7rem; padding-right: 0.7rem; padding-top: 1rem; }
    
    /* Стили для кастомных кнопок-ссылок */
    div.stButton > button:first-child {
        background-color: transparent;
        color: #ffffff;
        border: 1px solid #444;
        font-weight: 700;
        font-size: 16px;
        text-align: left;
        padding: 5px 10px;
        width: 100%;
        border-radius: 8px;
    }
    div.stButton > button:hover { border-color: #e63946; color: #e63946; }

    .match-card {
        background: #111111;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        border-left: 10px solid #444;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    .win-card { border-left-color: #28a745 !important; }
    .loss-card { border-left-color: #e63946 !important; }
    
    .match-header {
        font-size: 12px;
        color: #999;
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-weight: 600;
    }
    .match-tournament { font-weight: 900; color: #fff; font-size: 14px; line-height: 1.3; margin-bottom: 12px; text-transform: uppercase; }
    
    .round-badge {
        background: #e63946;
        color: #fff;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 900;
    }

    .match-score { 
        font-size: 34px; 
        font-weight: 900; 
        color: #ffffff; 
        text-align: right; 
        line-height: 1;
        letter-spacing: -1px;
    }
    
    .match-footer { 
        font-size: 13px; 
        color: #ffffff; 
        margin-top: 12px; 
        display: flex; 
        justify-content: space-between; 
        border-top: 1px solid #333; 
        padding-top: 10px;
        font-weight: 500;
    }
    .time-label { color: #00ff00; font-weight: 800; }
    .match-cat { font-size: 12px; color: #e63946; margin-top: 5px; font-weight: 800; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
DATABASE_FILE = "AllTournament.csv"
ROUND_MAP = {
    'FIN': (7, 'ФИНАЛ'), 'FNL': (7, 'ФИНАЛ'), 'SFL': (6, '1/2 ФИНАЛА'), 
    'QFL': (5, '1/4 ФИНАЛА'), 'R16': (4, '1/8 ФИНАЛА'), 'R32': (3, '1/16 ФИНАЛА'),
    'R64': (2, '1/32 ФИНАЛА'), 'R128': (1, '1/64 ФИНАЛА')
}
FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", 
    "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯", "TKM": "🇹🇲", "AIN": "🏳️", "FRA": "🇫🇷", "SRB": "🇷🇸", 
    "USA": "🇺🇸", "UKR": "🇺🇦", "BUL": "🇧🇬", "CRO": "🇭🇷", "MKD": "🇲🇰", "ROU": "🇷🇴", "ITA": "🇮🇹",
    "ESP": "🇪🇸", "GER": "🇩🇪", "ISR": "🇮🇱", "GRE": "🇬🇷", "NED": "🇳🇱", "MAR": "🇲🇦", "CMR": "🇨🇲",
    "LAT": "🇱🇻", "LTU": "🇱🇹", "EST": "🇪🇪", "LVA": "🇱🇻", "TUR": "🇹🇷"
}
COUNTRY_NAMES_RU = {
    "RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН", 
    "MGL": "МОНГОЛИЯ", "GEO": "ГРУЗИЯ", "ARM": "АРМЕНИЯ", "AZE": "АЗЕРБАЙДЖАН", "TJK": "ТАДЖИКИСТАН", 
    "TKM": "ТУРКМЕНИСТАН", "AIN": "НЕЙТР. АТЛЕТ", "UKR": "УКРАИНА", "BUL": "БОЛГАРИЯ"
}

# --- УТИЛИТЫ ---
def format_time(val):
    try:
        s = str(val).strip()
        if ':' in s: return s
        ms = int(float(s))
        if ms == 0: return "0:00"
        ts = ms // 1000
        return f"{ts // 60}:{ts % 60:02d}"
    except: return str(val)

def get_flag(c): return FLAG_EMOJIS.get(str(c).upper().strip(), "🌍")
def get_full_country(c): return COUNTRY_NAMES_RU.get(str(c).upper().strip(), str(c))

def get_readable_cat(code):
    c = str(code).upper().strip()
    p = "Спорт" if "SAM" in c else "Боевое" if "CSM" in c else ""
    g = "М" if "SAMM" in c or "CSMM" in c else "Ж" if "SAMW" in c or "CSMW" in c else ""
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts) > 1:
            raw = parts[1]
            w = (raw[:-1] + "+") if raw.endswith('O') else raw
    return f"{p} {g} {w}кг".strip()

@st.cache_data(ttl=300)
def load_data_v57():
    if not os.path.exists(DATABASE_FILE): return None
    try:
        df = pd.read_csv(DATABASE_FILE, low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]
        for col in ['winner_athlete_id', 'red_id', 'blue_id']:
            df[col] = df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None)
        df['red_full_name'] = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
        df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
        df['date_start'] = pd.to_datetime(df['date_start'], errors='coerce')
        df['round_rank'] = df['round_code'].apply(lambda x: ROUND_MAP.get(str(x).upper(), (0, str(x)))[0])
        return df
    except: return None

df = load_data_v57()

# --- ТЕЛЕГРАМ БОТ ---
if "bot_active" not in st.session_state:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    def run_bot():
        @bot.message_handler(func=lambda m: True)
        def h(m): bot.send_message(m.chat.id, "Используйте сайт FIGHTGURU.")
        bot.infinity_polling(timeout=20)
    threading.Thread(target=run_bot, daemon=True).start()
    st.session_state.bot_active = True

# --- ИНИЦИАЛИЗАЦИЯ ПОИСКА ---
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# --- ИНТЕРФЕЙС ---
st.title("FIGHTGURU DATA CENTER")

if df is not None:
    nav = st.sidebar.radio("Меню", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        # Поле ввода, связанное с session_state
        search_input = st.text_input("Фамилия (Osipenko, Arzikulov...):", value=st.session_state.search_query)
        
        if search_input:
            search_low = search_input.lower().strip()
            matches = df[(df['red_last_name'].str.lower().str.contains(search_low, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search_low, na=False))].copy()
            
            if not matches.empty:
                matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])
                
                # ЛОГИКА ОПРЕДЕЛЕНИЯ ДАТЫ РОЖДЕНИЯ (ПОИСК ПО ВСЕМ КАРТОЧКАМ АТЛЕТА)
                athlete_dob = "Н/Д"
                athlete_real_name = ""
                for _, r in matches.iterrows():
                    if search_low in str(r['red_last_name']).lower():
                        athlete_dob = r['red_birth_date']
                        athlete_real_name = r['red_full_name']
                        if pd.notna(athlete_dob): break
                    elif search_low in str(r['blue_last_name']).lower():
                        athlete_dob = r['blue_birth_date']
                        athlete_real_name = r['blue_full_name']
                        if pd.notna(athlete_dob): break
                
                st.header(athlete_real_name.upper())
                st.caption(f"📅 Дата рождения: {athlete_dob if pd.notna(athlete_dob) else 'Н/Д'}")
                st.divider()

                for _, row in matches.iterrows():
                    is_red = search_low in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    # Данные оппонента
                    opp_last_name = str(row['blue_last_name']) if is_red else str(row['red_last_name'])
                    opp_full_name = str(row['blue_full_name']) if is_red else str(row['red_full_name'])
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    round_label = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                    card_style = "win-card" if is_win else "loss-card"
                    res_tag = "ПОБЕДА" if is_win else "ПОРАЖЕНИЕ"
                    match_t = format_time(row['fight_time'])

                    # Контейнер карточки
                    st.markdown(f"""
                    <div class="match-card {card_style}">
                        <div class="match-header">
                            <span>{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '????'}</span>
                            <span class="round-badge">{round_label}</span>
                        </div>
                        <div class="match-tournament">{str(row['tournament_name']).upper()}</div>
                        <div class="match-cat">{get_readable_cat(row['category_code'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Кнопка оппонента и счет (в колонках для интерактивности)
                    col_info, col_score = st.columns([3, 1])
                    with col_info:
                        st.write(f"{get_flag(opp_country)} {get_full_country(opp_country)}")
                        # Кнопка переключения на оппонента
                        if st.button(f"👤 {opp_full_name.upper()}", key=f"btn_{row.name}"):
                            st.session_state.search_query = opp_last_name
                            st.rerun()
                            
                    with col_score:
                        st.markdown(f'<div class="match-score">{int(row["red_score"])}:{int(row["blue_score"])}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                        <div class="match-footer">
                            <span>⏱ ВРЕМЯ: <span class="time-label">{match_t}</span></span>
                            <span style="color: {'#28a745' if is_win else '#e63946'}; font-weight: 900;">{res_tag}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.write("") # Отступ
            else:
                st.info("Атлет не найден.")

    elif nav == "🏛️ Пантеон":
        st.subheader("🏛️ Исторический Пантеон")
        t_sel = st.selectbox("Турнир", list(TOURNAMENT_GROUPS.keys()))
        pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
        fin = df[(df['tournament_name'].str.contains(pattern, case=False, na=False)) & (df['round_code'].str.contains('FNL|FIN', case=False, na=False))].copy()
        if not fin.empty:
            def get_w(r): return r['red_nationality_code'] if str(r['winner_athlete_id']) == str(r['red_id']) else r['blue_nationality_code']
            fin['w_country'] = fin.apply(get_w, axis=1)
            stats = fin.groupby('w_country').size().sort_values(ascending=False).reset_index(name='Gold')
            stats['Страна'] = stats['w_country'].apply(lambda x: get_flag(x) + " " + get_full_country(x))
            st.table(stats[['Страна', 'Gold']])

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

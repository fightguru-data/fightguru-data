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

# --- СТИЛИЗАЦИЯ (ELITE SPORTS UI) ---
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    .main .block-container { padding: 1rem 0.5rem; }

    /* Кнопка оппонента - Компактный стиль */
    div.stButton > button:first-child {
        background-color: #1a1a1a;
        color: #ffffff !important;
        border: 1px solid #333;
        font-weight: 700;
        font-size: 14px;
        text-align: left;
        padding: 8px 12px;
        border-radius: 6px;
        width: 100%;
        margin-top: -5px;
    }
    div.stButton > button:hover { border-color: #e63946; background-color: #e63946; }

    /* Карточка поединка - Оптимизированная плотность */
    .match-card {
        background: #111111;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 6px solid #444;
        position: relative;
    }
    .win-card { border-left-color: #28a745 !important; }
    .loss-card { border-left-color: #e63946 !important; }
    
    .match-date { font-size: 11px; color: #666; font-weight: 700; margin-bottom: 4px; }
    .match-tournament { font-weight: 800; color: #ffffff; font-size: 13px; margin-bottom: 4px; line-height: 1.2; padding-right: 70px; }
    .match-cat { font-size: 11px; color: #e63946; font-weight: 800; text-transform: uppercase; margin-bottom: 12px; }
    
    .round-badge {
        position: absolute;
        top: 16px;
        right: 16px;
        background: #e63946;
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 900;
        text-transform: uppercase;
    }

    /* Блок счета */
    .score-container {
        background: #1a1a1a;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        min-width: 80px;
    }
    .score-val { font-size: 28px; font-weight: 900; color: #ffffff; line-height: 1; }
    .score-label { font-size: 9px; color: #555; text-transform: uppercase; margin-top: 4px; }

    .match-footer { 
        margin-top: 12px; 
        display: flex; 
        justify-content: space-between; 
        border-top: 1px solid #222; 
        padding-top: 8px;
        align-items: center;
    }
    .time-val { color: #00ff41; font-weight: 800; font-size: 12px; }
    .status-val { font-weight: 900; font-size: 11px; text-transform: uppercase; }

    /* Шапка досье */
    .athlete-header {
        background: #111111;
        padding: 20px;
        border-radius: 12px;
        border-bottom: 4px solid #e63946;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
DATABASE_FILE = "AllTournament.csv"
ROUND_MAP = {
    'FIN': (7, 'ФИНАЛ'), 'FNL': (7, 'ФИНАЛ'), 'SFL': (6, '1/2'), 
    'QFL': (5, '1/4'), 'R16': (4, '1/8'), 'R32': (3, '1/16')
}
FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", 
    "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯", "TKM": "🇹🇲", "AIN": "🏳️", "FRA": "🇫🇷", "SRB": "🇷🇸", 
    "USA": "🇺🇸", "UKR": "🇺🇦", "BUL": "🇧🇬", "CRO": "🇭🇷", "MKD": "🇲🇰", "ROU": "🇷🇴", "ITA": "🇮🇹",
    "LAT": "🇱🇻", "LTU": "🇱🇹", "EST": "🇪🇪", "TUR": "🇹🇷"
}
COUNTRY_NAMES_RU = {"RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН", "AIN": "НЕЙТР. АТЛЕТ"}

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

@st.cache_data(ttl=300)
def load_data_v59():
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

df = load_data_v59()

# --- БОТ ---
if "bot_active" not in st.session_state:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20), daemon=True).start()
    st.session_state.bot_active = True

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# --- ИНТЕРФЕЙС ---
if df is not None:
    # Сайдбар
    nav = st.sidebar.radio("Навигация", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        search_input = st.text_input("Поиск атлета (Osipenko, Zinnatov...):", value=st.session_state.search_query)
        
        if search_input:
            search_low = search_input.lower().strip()
            matches = df[(df['red_last_name'].str.lower().str.contains(search_low, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search_low, na=False))].copy()
            
            if not matches.empty:
                matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])
                
                # Поиск Д.Р. и имени
                dob_list = []
                final_name = ""
                for _, r in matches.iterrows():
                    if search_low in str(r['red_last_name']).lower():
                        final_name = r['red_full_name']
                        if pd.notna(r['red_birth_date']): dob_list.append(str(r['red_birth_date']).strip())
                    elif search_low in str(r['blue_last_name']).lower():
                        final_name = r['blue_full_name']
                        if pd.notna(r['blue_birth_date']): dob_list.append(str(r['blue_birth_date']).strip())
                athlete_dob = max(set(dob_list), key=dob_list.count) if dob_list else "Н/Д"
                
                # ШАПКА
                st.markdown(f"""
                <div class="athlete-header">
                    <h2 style="margin:0; color:#e63946; font-size: 22px;">{final_name.upper()}</h2>
                    <p style="margin:5px 0 0 0; color:#888; font-size: 12px;">📅 ДАТА РОЖДЕНИЯ: <span style="color:#fff; font-weight:800;">{athlete_dob}</span></p>
                </div>
                """, unsafe_allow_html=True)

                # КАРТОЧКИ
                for _, row in matches.iterrows():
                    is_red = search_low in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    opp_last = str(row['blue_last_name']) if is_red else str(row['red_last_name'])
                    opp_full = str(row['blue_full_name']) if is_red else str(row['red_full_name'])
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    round_label = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                    card_style = "win-card" if is_win else "loss-card"
                    status_txt = "ПОБЕДА" if is_win else "ПОРАЖЕНИЕ"
                    status_clr = "#28a745" if is_win else "#e63946"

                    # Рендерим HTML структуру карточки
                    st.markdown(f"""
                    <div class="match-card {card_style}">
                        <div class="match-date">{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '????'}</div>
                        <div class="round-badge">{round_label}</div>
                        <div class="match-tournament">{str(row['tournament_name']).upper()}</div>
                        <div class="match-cat">{row['category_code'].upper()}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Интерактивный блок: Оппонент + Счет
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"<div style='font-size:11px; color:#555; margin-bottom:2px;'>ПРОТИВНИК:</div>", unsafe_allow_html=True)
                        st.write(f"{get_flag(opp_country)} {get_full_country(opp_country)}")
                        if st.button(f"{opp_full.upper()}", key=f"btn_{row.name}"):
                            st.session_state.search_query = opp_last
                            st.rerun()
                    with c2:
                        st.markdown(f"""
                        <div class="score-container">
                            <div class="score-val">{int(row['red_score'])}:{int(row['blue_score'])}</div>
                            <div class="score-label">СЧЕТ</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Футер карточки
                    st.markdown(f"""
                    <div class="match-footer">
                        <span>⏱ <span class="time-val">{format_time(row['fight_time'])}</span></span>
                        <span class="status-val" style="color:{status_clr};">{status_txt}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("") 
            else:
                st.info("Атлет не найден.")

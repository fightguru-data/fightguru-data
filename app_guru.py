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

# --- СТИЛИЗАЦИЯ (PREMIUM GREY UI) ---
st.markdown("""
<style>
    /* Глобальный фон - Премиальный серый */
    .stApp { background-color: #1e1f22; color: #eeeeee; }
    .main .block-container { padding: 1rem 0.5rem; }

    /* Контейнер карточки (Монолит) */
    .match-box {
        background-color: #2b2d31;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #3f4147;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    
    .win-border { border-left: 6px solid #28a745; }
    .loss-border { border-left: 6px solid #e63946; }

    /* Заголовок карточки */
    .match-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
        border-bottom: 1px solid #3f4147;
        padding-bottom: 8px;
    }
    .date-txt { font-size: 11px; color: #888; font-weight: 600; }
    .round-label {
        background: #e63946;
        color: #fff;
        padding: 1px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 900;
        text-transform: uppercase;
    }

    /* Название турнира */
    .tourney-txt { font-size: 12px; font-weight: 800; color: #fff; text-transform: uppercase; line-height: 1.2; margin-bottom: 12px; }

    /* Счёт и предупреждения */
    .score-container { text-align: right; line-height: 1; }
    .score-txt { font-size: 38px; font-weight: 900; color: #fff; letter-spacing: -1px; }
    .warn-txt { font-size: 10px; color: #e63946; font-weight: 800; margin-top: -5px; }

    /* Оппонент (Кнопка Streamlit будет вставлена между блоками) */
    .opp-flag-box { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
    .flag-txt { font-size: 18px; }
    .country-code { font-size: 11px; font-weight: 800; color: #888; }

    /* Футер карточки */
    .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid #3f4147;
    }
    .cat-txt { font-size: 10px; color: #e63946; font-weight: 800; text-transform: uppercase; }
    .time-txt { font-size: 11px; color: #00ff41; font-weight: 800; }
    .res-txt { font-size: 11px; font-weight: 900; text-transform: uppercase; }

    /* Кнопки оппонентов */
    div.stButton > button:first-child {
        background-color: #1e1f22;
        color: #ffffff !important;
        border: 1px solid #4f5157;
        font-weight: 700;
        font-size: 14px;
        width: 100%;
        text-align: left;
        border-radius: 6px;
        padding: 5px 10px;
    }
    div.stButton > button:hover { border-color: #e63946; color: #e63946 !important; }

    /* Шапка досье */
    .athlete-profile {
        background: #2b2d31;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid #3f4147;
        margin-bottom: 20px;
    }
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

# --- ФУНКЦИИ ---
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

def get_readable_cat(code):
    c = str(code).upper().strip()
    p = "СПОРТ" if "SAM" in c else "БОЕВОЕ" if "CSM" in c else ""
    g = "М" if "SAMM" in c or "CSMM" in c else "Ж" if "SAMW" in c or "CSMW" in c else ""
    w = ""
    if "ADT" in c:
        parts = c.split("ADT"); w = (parts[1][:-1] + "+") if (len(parts)>1 and parts[1].endswith('O')) else parts[1] if len(parts)>1 else ""
    return f"{p} {g} {w}КГ"

@st.cache_data(ttl=300)
def load_data_v60():
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

df = load_data_v60()

# --- БОТ ---
if "bot_active" not in st.session_state:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20), daemon=True).start()
    st.session_state.bot_active = True

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# --- ИНТЕРФЕЙС ---
if df is not None:
    st.sidebar.title("FIGHTGURU")
    nav = st.sidebar.radio("Навигация", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        search_input = st.text_input("ПОИСК АТЛЕТА (Osipenko, Zinnatov...):", value=st.session_state.search_query)
        
        if search_input:
            search_low = search_input.lower().strip()
            matches = df[(df['red_last_name'].str.lower().str.contains(search_low, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search_low, na=False))].copy()
            
            if not matches.empty:
                matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])
                
                # Поиск Д.Р.
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
                
                # ШАПКА ПРОФИЛЯ
                st.markdown(f"""
                <div class="athlete-profile">
                    <h2 style="margin:0; color:#e63946; font-size:24px;">{final_name.upper()}</h2>
                    <p style="margin:8px 0 0 0; color:#aaa; font-size:13px; font-weight:700;">
                        📅 ДАТА РОЖДЕНИЯ: <span style="color:#fff;">{athlete_dob}</span>
                    </p>
                </div>
                """, unsafe_allow_html=True)

                for _, row in matches.iterrows():
                    is_red = search_low in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    # Данные оппонента
                    opp_last = str(row['blue_last_name']) if is_red else str(row['red_last_name'])
                    opp_full = str(row['blue_full_name']) if is_red else str(row['red_full_name'])
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    # Предупреждения (Warnings)
                    my_warn = row['red_warnings'] if is_red else row['blue_warnings']
                    opp_warn = row['blue_warnings'] if is_red else row['red_warnings']
                    
                    round_label = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                    card_cls = "win-border" if is_win else "loss-border"
                    res_tag = "WIN" if is_win else "LOSS"
                    match_t = format_time(row['fight_time'])

                    # Начало блока
                    st.markdown(f"""
                    <div class="match-box {card_cls}">
                        <div class="match-header">
                            <span class="date-txt">{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??.??.????'}</span>
                            <span class="round-label">{round_label}</span>
                        </div>
                        <div class="tourney-txt">{str(row['tournament_name'])}</div>
                    """, unsafe_allow_html=True)

                    # Контент (Оппонент и Счет)
                    c1, c2 = st.columns([2.5, 1])
                    with c1:
                        st.markdown(f"""
                        <div class="opp-flag-box">
                            <span class="flag-txt">{get_flag(opp_country)}</span>
                            <span class="country-code">{opp_country}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"{opp_full.upper()}", key=f"btn_{row.name}"):
                            st.session_state.search_query = opp_last
                            st.rerun()
                    with c2:
                        st.markdown(f"""
                        <div class="score-container">
                            <div class="score-txt">{int(row['red_score'])}:{int(row['blue_score'])}</div>
                            <div class="warn-txt">W: {int(my_warn or 0)} vs {int(opp_warn or 0)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Футер блока
                    st.markdown(f"""
                        <div class="card-footer">
                            <div class="cat-txt">{get_readable_cat(row['category_code'])}</div>
                            <div>
                                <span class="time-txt">⏱ {match_t}</span>
                                <span class="res-txt" style="color: {'#28a745' if is_win else '#e63946'}; margin-left:12px;">{res_tag}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Атлет не найден.")

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

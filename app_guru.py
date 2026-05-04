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

# --- СТИЛИЗАЦИЯ (PRO DESIGN UI) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main .block-container { padding: 1rem 0.5rem; }
    
    /* Стилизация кнопок оппонентов (Компактный вид) */
    div.stButton > button:first-child {
        background-color: #1c1f26;
        color: #ffffff !important;
        border: 1px solid #3d4450;
        font-weight: 700;
        font-size: 14px;
        text-align: left;
        width: auto;
        border-radius: 6px;
        padding: 4px 10px;
        margin-top: -5px;
    }
    div.stButton > button:hover { border-color: #e63946; color: #e63946 !important; }

    /* Карточка поединка */
    .match-card {
        background: #000000;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 8px solid #444;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .win-card { border-left-color: #28a745 !important; }
    .loss-card { border-left-color: #e63946 !important; }
    
    /* Верхняя строка: Дата и Раунд */
    .card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .date-label { font-size: 11px; color: #555; font-weight: 700; }
    .round-badge {
        background: #e63946;
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 900;
        text-transform: uppercase;
    }

    /* Турнир */
    .t-name { font-weight: 800; color: #bbb; font-size: 12px; margin-bottom: 10px; text-transform: uppercase; line-height: 1.2; }

    /* Центральный блок: Флаг + Имя + Счет */
    .main-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .opp-box { display: flex; align-items: center; gap: 8px; flex: 1; }
    .flag-icon { font-size: 20px; }
    .score-val { 
        font-size: 36px; 
        font-weight: 900; 
        color: #ffffff; 
        line-height: 1;
        margin-left: 10px;
    }

    /* Футер карточки */
    .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-top: 1px solid #1a1a1a;
        padding-top: 8px;
        margin-top: 5px;
    }
    .cat-tag { font-size: 11px; color: #e63946; font-weight: 800; text-transform: uppercase; }
    .time-val { color: #00ff41; font-weight: 800; font-size: 12px; }
    .res-tag { font-weight: 900; font-size: 12px; }

    /* Шапка досье */
    .athlete-header {
        background: linear-gradient(135deg, #1c1f26 0%, #000000 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 1px solid #222;
        text-align: center;
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
COUNTRY_NAMES_RU = {"RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН"}

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
def get_full_country(c): return COUNTRY_NAMES_RU.get(str(c).upper().strip(), str(c))

def get_readable_cat(code):
    c = str(code).upper().strip()
    p = "СПОРТ" if "SAM" in c else "БОЕВОЕ" if "CSM" in c else ""
    g = "М" if "SAMM" in c or "CSMM" in c else "Ж" if "SAMW" in c or "CSMW" in c else ""
    w = ""
    if "ADT" in c:
        parts = c.split("ADT"); w = (parts[1][:-1] + "+") if (len(parts)>1 and parts[1].endswith('O')) else parts[1] if len(parts)>1 else ""
    return f"{p} {g} {w}КГ"

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
    # Sidebar
    st.sidebar.title("FIGHTGURU")
    nav = st.sidebar.radio("Меню", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        search_input = st.text_input("ПОИСК АТЛЕТА:", value=st.session_state.search_query, placeholder="Введите фамилию...")
        
        if search_input:
            search_low = search_input.lower().strip()
            matches = df[(df['red_last_name'].str.lower().str.contains(search_low, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search_low, na=False))].copy()
            
            if not matches.empty:
                matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])
                
                # Поиск даты рождения и ФИО
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
                    <h2 style="margin:0; color:#e63946; font-size:26px;">{final_name.upper()}</h2>
                    <p style="margin:5px 0 0 0; color:#888; font-size:14px;">📅 ДАТА РОЖДЕНИЯ: <span style="color:#fff; font-weight:800;">{athlete_dob}</span></p>
                </div>
                """, unsafe_allow_html=True)

                for _, row in matches.iterrows():
                    is_red = search_low in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    opp_last = str(row['blue_last_name']) if is_red else str(row['red_last_name'])
                    opp_full = str(row['blue_full_name']) if is_red else str(row['red_full_name'])
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    round_label = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                    card_style = "win-card" if is_win else "loss-card"
                    res_tag = "WIN" if is_win else "LOSS"
                    match_t = format_time(row['fight_time'])

                    # Начало карточки
                    st.markdown(f"""
                    <div class="match-card {card_style}">
                        <div class="card-top">
                            <span class="date-label">{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??.??.????'}</span>
                            <span class="round-badge">{round_label}</span>
                        </div>
                        <div class="t-name">{str(row['tournament_name'])}</div>
                    """, unsafe_allow_html=True)
                    
                    # Центральный ряд (Оппонент + Счет)
                    m_col1, m_col2 = st.columns([3, 1])
                    with m_col1:
                        st.markdown(f"""
                        <div class="opp-box">
                            <span class="flag-icon">{get_flag(opp_country)}</span>
                            <span style="font-size:12px; color:#666; font-weight:800;">{opp_country}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"{opp_full.upper()}", key=f"btn_{row.name}"):
                            st.session_state.search_query = opp_last
                            st.rerun()
                    with m_col2:
                        st.markdown(f'<div class="score-val">{int(row["red_score"])}:{int(row["blue_score"])}</div>', unsafe_allow_html=True)
                    
                    # Футер карточки
                    st.markdown(f"""
                        <div class="card-footer">
                            <div class="cat-tag">{get_readable_cat(row['category_code'])}</div>
                            <div>
                                <span class="time-val">⏱ {match_t}</span>
                                <span class="res-tag" style="color: {'#28a745' if is_win else '#e63946'}; margin-left:10px;">{res_tag}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.write("") 
            else:
                st.info("Атлет не найден.")

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

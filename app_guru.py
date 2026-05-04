import streamlit as st
import pandas as pd
import os
import threading
import telebot
from PIL import Image

# --- ПАРАМЕТРЫ ТЕЛЕГРАМ-БОТА ---
BOT_TOKEN = '8677319918:AAHqlbO9FnZ1lcLkM1WLWfZ2vC9q_8gyc6c'

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="FIGHTGURU DATA CENTER", page_icon="🥋", layout="wide")

# --- СТИЛИЗАЦИЯ (PREMIUM DESIGN UI) ---
st.markdown("""
<style>
    .stApp { background-color: #1e1f22; color: #eeeeee; }
    .main .block-container { padding: 1rem 0.5rem; }

    /* Контейнер карточки через Streamlit border */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #36393f !important;
        border-radius: 12px !important;
        border: 1px solid #4f5157 !important;
        margin-bottom: 15px !important;
    }

    /* Специфические стили для элементов внутри */
    .m-header { display: flex; justify-content: space-between; font-size: 11px; color: #aaa; margin-bottom: 5px; }
    .m-round { background: #e63946; color: white; padding: 2px 8px; border-radius: 4px; font-weight: 900; font-size: 10px; }
    .m-tourney { font-size: 13px; font-weight: 800; color: #fff; text-transform: uppercase; line-height: 1.2; }
    .m-cat { font-size: 11px; color: #e63946; font-weight: 800; margin-top: 4px; }
    
    .m-info-line { 
        display: flex; 
        justify-content: space-between; 
        background: rgba(0,0,0,0.2); 
        padding: 5px 10px; 
        border-radius: 6px; 
        margin: 10px 0;
        font-size: 12px;
    }
    .m-time { color: #00ff41; font-weight: 800; }
    .m-warn { color: #ffcc00; font-weight: 700; }
    .m-status { font-weight: 900; }

    .m-score { font-size: 48px; font-weight: 900; color: #fff; line-height: 1; text-align: right; }
    .m-opp-label { font-size: 10px; color: #888; margin-bottom: 2px; }
    
    /* Кнопка оппонента */
    div.stButton > button:first-child {
        background-color: #2b2d31;
        color: #ffffff !important;
        border: 1px solid #4f5157;
        font-weight: 700;
        font-size: 16px;
        width: 100%;
        text-align: left;
        border-radius: 8px;
        padding: 10px;
    }
    div.stButton > button:hover { border-color: #e63946; background-color: #1e1f22; }

    /* Сайдбар */
    [data-testid="stSidebar"] { background-color: #1e1f22; border-right: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ И СПРАВОЧНИКИ ---
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
    "TKM": "ТУРКМЕНИСТАН", "AIN": "НЕЙТР. АТЛЕТ", "UKR": "УКРАИНА", "BUL": "БОЛГАРИЯ", "FRA": "ФРАНЦИЯ",
    "ITA": "ИТАЛИЯ", "SRB": "СЕРБИЯ", "ROU": "РУМЫНИЯ", "USA": "США", "MAR": "МАРОККО"
}
TOURNAMENT_GROUPS = {
    "Чемпионат Мира": ["World Sambo Championships", "World SAMBO Championships"],
    "Кубок Мира": ["Cup", "President"],
    "Чемпионат Европы": ["European Sambo Championships", "European Championships"],
    "ЧМ Азии и Океании": ["Asia and Oceania Sambo Championships"]
}
DIVISIONS = {"Спортивное Самбо (М)": "samm", "Спортивное Самбо (Ж)": "samw", "Боевое Самбо (М)": "csmm", "Боевое Самбо (Ж)": "csmw"}

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
def load_data_v63():
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

df = load_data_v63()

# --- ЛОГИКА ТЕЛЕГРАМ-БОТА ---
if "bot_active" not in st.session_state:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
        def run_bot():
            @bot.message_handler(commands=['start'])
            def s(m): bot.reply_to(m, "FIGHTGURU DATA CENTER: Пришлите фамилию атлета.")
            bot.infinity_polling(timeout=20)
        threading.Thread(target=run_bot, daemon=True).start()
        st.session_state.bot_active = True
    except: pass

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# --- ИНТЕРФЕЙС ---
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

st.sidebar.title("FIGHTGURU DATA")
nav = st.sidebar.radio("Навигация", ["👤 Досье", "🏛️ Пантеон"])

if df is not None:
    if nav == "👤 Досье":
        search_input = st.text_input("ПОИСК АТЛЕТА (Osipenko, Zinnatov...):", value=st.session_state.search_query)
        
        if search_input:
            search_low = search_input.lower().strip()
            matches = df[(df['red_last_name'].str.lower().str.contains(search_low, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search_low, na=False))].copy()
            
            if not matches.empty:
                matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])
                
                # Поиск ФИО и ДР
                dob_list, final_name = [], ""
                for _, r in matches.iterrows():
                    if search_low in str(r['red_last_name']).lower():
                        final_name = r['red_full_name']
                        if pd.notna(r['red_birth_date']): dob_list.append(str(r['red_birth_date']).strip())
                    elif search_low in str(r['blue_last_name']).lower():
                        final_name = r['blue_full_name']
                        if pd.notna(r['blue_birth_date']): dob_list.append(str(r['blue_birth_date']).strip())
                athlete_dob = max(set(dob_list), key=dob_list.count) if dob_list else "Н/Д"
                
                # Профиль
                st.markdown(f"""
                <div style="background:#2b2d31; padding:20px; border-radius:12px; text-align:center; border:1px solid #4f5157; margin-bottom:20px;">
                    <h2 style="margin:0; color:#e63946; font-size:26px;">{final_name.upper()}</h2>
                    <p style="margin:5px 0 0 0; color:#888; font-size:14px; font-weight:700;">📅 ДР: <span style="color:#fff;">{athlete_dob}</span></p>
                </div>
                """, unsafe_allow_html=True)

                for _, row in matches.iterrows():
                    # Логика сторон
                    is_red = search_low in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    # Оппонент
                    opp_last = str(row['blue_last_name']) if is_red else str(row['red_last_name'])
                    opp_full = str(row['blue_full_name']) if is_red else str(row['red_full_name'])
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    # Предупреждения (Гибкий поиск колонок)
                    w_c_my = [c for c in row.index if 'warn' in c and ('red' if is_red else 'blue') in c]
                    w_c_op = [c for c in row.index if 'warn' in c and ('blue' if is_red else 'red') in c]
                    warn_my = int(row[w_c_my[0]]) if w_c_my and pd.notna(row[w_c_my[0]]) else 0
                    warn_op = int(row[w_c_op[0]]) if w_c_op and pd.notna(row[w_c_op[0]]) else 0
                    
                    round_label = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                    res_tag = "WIN" if is_win else "LOSS"
                    res_col = "#28a745" if is_win else "#e63946"

                    # Единый контейнер встречи
                    with st.container(border=True):
                        # 1. Шапка
                        st.markdown(f"""
                        <div class="m-header">
                            <span>{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??.??.????'}</span>
                            <span class="m-round">{round_label}</span>
                        </div>
                        <div class="m-tourney">{row['tournament_name']}</div>
                        <div class="m-cat">{get_readable_cat(row['category_code'])}</div>
                        """, unsafe_allow_html=True)
                        
                        # 2. Инфо-линия (Время, Предупреждения, Статус)
                        st.markdown(f"""
                        <div class="m-info-line">
                            <span class="m-time">⏱ {format_time(row['fight_time'])}</span>
                            <span class="m-warn">⚠️ ПРЕД: {warn_my} / {warn_op}</span>
                            <span class="m-status" style="color:{res_col}">{res_tag}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 3. Соперник и Счет
                        c_opp, c_score = st.columns([2.5, 1])
                        with c_opp:
                            st.markdown(f"""
                            <div class="m-opp-label">СОПЕРНИК:</div>
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px;">
                                <span style="font-size:20px;">{get_flag(opp_country)}</span>
                                <span style="font-size:12px; font-weight:800; color:#aaa;">{get_full_country(opp_country)}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"{opp_full.upper()}", key=f"b_{row.name}"):
                                st.session_state.search_query = opp_last
                                st.rerun()
                        with c_score:
                            st.markdown(f"""
                            <div class="m-opp-label" style="text-align:right;">СЧЕТ:</div>
                            <div class="m-score">{int(row.get('red_score', 0))}:{int(row.get('blue_score', 0))}</div>
                            """, unsafe_allow_html=True)
            else:
                st.info("Атлет не найден.")

    elif nav == "🏛️ Пантеон":
        st.header("🏛️ Исторический Пантеон")
        t_sel = st.selectbox("Выберите турнир:", list(TOURNAMENT_GROUPS.keys()))
        d_sel = st.selectbox("Дивизион:", list(DIVISIONS.keys()))
        
        pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
        f_data = df[(df['tournament_name'].str.contains(pattern, case=False, na=False)) & 
                    (df['category_code'].str.contains(DIVISIONS[d_sel], case=False, na=False))]
        
        finals = f_data[f_data['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
        
        if not finals.empty:
            def get_w(r):
                if str(r['winner_athlete_id']) == str(r['red_id']):
                    return r['red_full_name'], r['red_nationality_code']
                return r['blue_full_name'], r['blue_nationality_code']
            
            finals[['w_name', 'w_country']] = finals.apply(lambda r: pd.Series(get_w(r)), axis=1)
            
            st.subheader("📊 Зачет стран (Золото)")
            stats = finals.groupby('w_country').size().sort_values(ascending=False).reset_index(name='Gold')
            stats['Страна'] = stats['w_country'].apply(lambda x: f"{get_flag(x)} {get_full_country(x)}")
            st.table(stats[['Страна', 'Gold']])
            
            st.subheader("🏆 Победители по весам")
            for cat in sorted(finals['Human_Category'].unique()):
                with st.expander(f"Вес: {}"):
                    c_df = finals[finals['Human_Category'] == cat].sort_values('date_start', ascending=False)
                    st.dataframe(c_df[['date_start', 'w_name', 'w_country']], use_container_width=True, hide_index=True)
        else:
            st.warning("Финалы не найдены.")

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

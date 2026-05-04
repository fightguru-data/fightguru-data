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

# --- СТИЛИЗАЦИЯ (MOBILE OPTIMIZED) ---
st.markdown("""
<style>
    .main .block-container { padding-left: 0.5rem; padding-right: 0.5rem; padding-top: 1rem; }
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
        color: #888;
        display: flex;
        justify-content: space-between;
        margin-bottom: 5px;
    }
    .match-tournament { font-weight: 800; color: #fff; font-size: 13px; line-height: 1.2; margin-bottom: 8px; }
    .round-badge {
        background: #333;
        color: #e63946;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
    }
    .match-main { display: flex; justify-content: space-between; align-items: center; }
    .opponent-name { font-size: 16px; font-weight: 700; color: #fff; line-height: 1.1; }
    .opponent-country { font-size: 12px; color: #aaa; margin-top: 2px; }
    .match-score { font-size: 22px; font-weight: 900; color: #fff; text-align: right; min-width: 60px; }
    .match-time { font-size: 11px; color: #555; margin-top: 5px; font-weight: 600; }
    .match-cat { font-size: 11px; color: #e63946; margin-top: 3px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
DATABASE_FILE = "AllTournament.csv"

# Словарь стадий (для сортировки и отображения)
ROUND_MAP = {
    'FIN': (7, 'ФИНАЛ'), 'FNL': (7, 'ФИНАЛ'),
    'SFL': (6, '1/2 ФИНАЛА'), 'QFL': (5, '1/4 ФИНАЛА'),
    'R16': (4, '1/8 ФИНАЛА'), 'R32': (3, '1/16 ФИНАЛА'),
    'R64': (2, '1/32 ФИНАЛА'), 'R128': (1, '1/64 ФИНАЛА')
}

# Расширенный словарь флагов
FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", 
    "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯", "TKM": "🇹🇲", "AIN": "🏳️", "FRA": "🇫🇷", "SRB": "🇷🇸", 
    "USA": "🇺🇸", "UKR": "🇺🇦", "BUL": "🇧🇬", "CRO": "🇭🇷", "MKD": "🇲🇰", "ROU": "🇷🇴", "ITA": "🇮🇹",
    "ESP": "🇪🇸", "GER": "🇩🇪", "ISR": "🇮🇱", "GRE": "🇬🇷", "NED": "🇳🇱", "MAR": "🇲🇦", "CMR": "🇨🇲"
}

COUNTRY_NAMES_RU = {
    "RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН", 
    "MGL": "МОНГОЛИЯ", "GEO": "ГРУЗИЯ", "ARM": "АРМЕНИЯ", "AZE": "АЗЕРБАЙДЖАН", "TJK": "ТАДЖИКИСТАН", 
    "TKM": "ТУРКМЕНИСТАН", "AIN": "НЕЙТР. АТЛЕТ", "UKR": "УКРАИНА", "BUL": "БОЛГАРИЯ"
}

DIVISIONS = {"Спортивное Самбо (М)": "samm", "Спортивное Самбо (Ж)": "samw", "Боевое Самбо (М)": "csmm", "Боевое Самбо (Ж)": "csmw"}

# --- ФУНКЦИИ ---
def get_flag(c): return FLAG_EMOJIS.get(str(c).upper().strip(), "🌍")
def get_full_country(c): return COUNTRY_NAMES_RU.get(str(c).upper().strip(), str(c))

def get_readable_cat(code):
    c = str(code).upper().strip()
    p = "Спорт" if "SAM" in c else "Боевое" if "CSM" in c else ""
    gender = "М" if "SAMM" in c or "CSMM" in c else "Ж" if "SAMW" in c or "CSMW" in c else ""
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts) > 1:
            raw = parts[1]
            w = (raw[:-1] + "+") if raw.endswith('O') else raw
    return f"{p} {gender} {w}кг".strip()

@st.cache_data(ttl=3600)
def load_data_v55():
    if not os.path.exists(DATABASE_FILE): return None
    try:
        df = pd.read_csv(DATABASE_FILE, low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]
        for col in ['winner_athlete_id', 'red_id', 'blue_id']:
            df[col] = df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None)
        df['red_full_name'] = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
        df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
        df['date_start'] = pd.to_datetime(df['date_start'], errors='coerce')
        df['Human_Category'] = df['category_code'].apply(get_readable_cat)
        # Обработка времени
        df['fight_time_clean'] = df['fight_time'].fillna('0:00')
        # Вес стадии для сортировки
        df['round_rank'] = df['round_code'].apply(lambda x: ROUND_MAP.get(str(x).upper(), (0, str(x)))[0])
        return df
    except:
        return None

df = load_data_v55()

# --- ТЕЛЕГРАМ БОТ (Упрощенный для стабильности) ---
def start_bot():
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    @bot.message_handler(func=lambda m: True)
    def handle(m):
        q = m.text.strip().lower()
        if len(q) < 3: return
        data = pd.read_csv(DATABASE_FILE, low_memory=False)
        data.columns = [c.strip().lower() for c in data.columns]
        res = data[(data['red_last_name'].str.lower().str.contains(q, na=False)) | (data['blue_last_name'].str.lower().str.contains(q, na=False))].head(5)
        if res.empty: return
        bot.send_message(m.chat.id, f"Найдено совпадений: {len(res)}. Проверьте досье на сайте.")
    bot.infinity_polling(timeout=20)

if "bot_active" not in st.session_state:
    threading.Thread(target=start_bot, daemon=True).start()
    st.session_state.bot_active = True

# --- ИНТЕРФЕЙС ---
st.title("FIGHTGURU DATA CENTER")

if df is not None:
    nav = st.sidebar.radio("Меню", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        search = st.text_input("Поиск (Osipenko, Mikhailin...):").lower().strip()
        if search:
            matches = df[(df['red_last_name'].str.lower().str.contains(search, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search, na=False))].copy()
            
            if not matches.empty:
                # Сортировка: Сначала свежие турниры, внутри турнира - от Финала к началу
                matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])
                
                # Извлекаем данные атлета (Д.Р. из нужной колонки)
                first = matches.iloc[0]
                is_red_first = search in str(first['red_last_name']).lower()
                real_name = first['red_full_name'] if is_red_first else first['blue_full_name']
                # Новые колонки дат рождения
                birth_val = first['red_birth_date'] if is_red_first else first['blue_birth_date']
                
                st.header(real_name.upper())
                st.caption(f"📅 Дата рождения: {birth_val}")
                st.divider()

                for _, row in matches.iterrows():
                    is_red = search in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    opp_name = row['blue_full_name'] if is_red else row['red_full_name']
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    # Стадия
                    round_info = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                    
                    card_style = "win-card" if is_win else "loss-card"
                    status_txt = "ПОБЕДА" if is_win else "ПОРАЖЕНИЕ"

                    st.markdown(f"""
                    <div class="match-card {card_style}">
                        <div class="match-header">
                            <span>{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '????'}</span>
                            <span class="round-badge">{round_info}</span>
                        </div>
                        <div class="match-tournament">{str(row['tournament_name']).upper()}</div>
                        <div class="match-main">
                            <div class="opponent-info">
                                <div class="opponent-name">{opp_name}</div>
                                <div class="opponent-country">{get_flag(opp_country)} {get_full_country(opp_country)}</div>
                                <div class="match-cat">{row['Human_Category']}</div>
                            </div>
                            <div class="match-score">{int(row['red_score'])}:{int(row['blue_score'])}</div>
                        </div>
                        <div class="match-time">⏱ ВРЕМЯ БОЯ: {row['fight_time_clean']} | {status_txt}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Атлет не найден.")

    elif nav == "🏛️ Пантеон":
        # (Остается без изменений для статистики)
        st.subheader("🏛️ Исторический Пантеон")
        t_sel = st.selectbox("Турнир", list(TOURNAMENT_GROUPS.keys()))
        d_sel = st.selectbox("Дивизион", list(DIVISIONS.keys()))
        pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
        f_data = df[(df['tournament_name'].str.contains(pattern, case=False, na=False)) & (df['category_code'].str.contains(DIVISIONS[d_sel], case=False, na=False))]
        fin = f_data[f_data['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
        if not fin.empty:
            def get_w(r): return (r['red_full_name'], r['red_nationality_code']) if str(r['winner_athlete_id']) == str(r['red_id']) else (r['blue_full_name'], r['blue_nationality_code'])
            fin[['w_name', 'w_country']] = fin.apply(lambda r: pd.Series(get_w(r)), axis=1)
            st.dataframe(fin.groupby('w_country').size().sort_values(ascending=False), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

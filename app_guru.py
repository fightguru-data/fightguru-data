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
        margin-bottom: 15px;
        border-left: 8px solid #444;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .win-card { border-left-color: #28a745 !important; }
    .loss-card { border-left-color: #e63946 !important; }
    .match-header {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        font-weight: 700;
    }
    .match-tournament { font-weight: 800; color: #fff; font-size: 13px; margin-bottom: 10px; line-height: 1.2; }
    .match-main { display: flex; justify-content: space-between; align-items: center; }
    .opponent-info { flex: 1; }
    .opponent-name { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 2px; }
    .opponent-country { font-size: 13px; color: #aaa; font-weight: 500; }
    .match-score {
        font-size: 24px;
        font-weight: 900;
        color: #e63946;
        padding-left: 15px;
        min-width: 65px;
        text-align: right;
    }
    .match-stage {
        display: inline-block;
        background: #222;
        color: #e63946;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 800;
        margin-top: 8px;
        text-transform: uppercase;
    }
    .dob-label { background: #e63946; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
DATABASE_FILE = "AllTournament.csv"

FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", 
    "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯", "TKM": "🇹🇲", "AIN": "🏳️", "FRA": "🇫🇷", "SRB": "🇷🇸", 
    "USA": "🇺🇸", "UKR": "🇺🇦", "MKD": "🇲🇰", "CRO": "🇭🇷", "BUL": "🇧🇬", "ROU": "🇷🇴", "GRE": "🇬🇷",
    "ITA": "🇮🇹", "ESP": "🇪🇸", "GER": "🇩🇪", "ISR": "🇮🇱", "MAR": "🇲🇦", "CMR": "🇨🇲", "NED": "🇳🇱"
}

ROUND_NAMES = {
    "FIN": "ФИНАЛ", "FNL": "ФИНАЛ",
    "SFL": "1/2 ФИНАЛА", "SF": "1/2 ФИНАЛА",
    "QFL": "1/4 ФИНАЛА", "QF": "1/4 ФИНАЛА",
    "R16": "1/8 ФИНАЛА", "R32": "1/16 ФИНАЛА",
    "R64": "1/32 ФИНАЛА", "R128": "1/64 ФИНАЛА",
    "REP": "УТЕШИТЕЛЬНЫЙ", "BRZ": "ЗА 3 МЕСТО"
}

ROUND_PRIORITY = {
    "FIN": 1, "FNL": 1, "SFL": 2, "SF": 2, "QFL": 3, "QF": 3,
    "R16": 4, "R32": 5, "R64": 6, "R128": 7, "REP": 8, "BRZ": 1.5
}

# --- ФУНКЦИИ ---
def get_flag(c): return FLAG_EMOJIS.get(str(c).upper().strip(), "🌍")

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
        
        # Точный поиск Даты Рождения (приоритет колонкам с 'birth' или 'dob')
        dob_col = next((c for c in df.columns if 'birth' in c or 'dob' in c), None)
        if dob_col:
            df['athlete_dob'] = df[dob_col].fillna('Н/Д')
        else:
            df['athlete_dob'] = 'Н/Д'

        df['red_score'] = pd.to_numeric(df['red_score'], errors='coerce').fillna(0).astype(int)
        df['blue_score'] = pd.to_numeric(df['blue_score'], errors='coerce').fillna(0).astype(int)
        
        # Приоритет раундов для сортировки
        df['round_rank'] = df['round_code'].apply(lambda x: ROUND_PRIORITY.get(str(x).upper(), 99))
        return df
    except:
        return None

df = load_data_v55()

# --- ТЕЛЕГРАМ БОТ ---
def start_bot():
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    @bot.message_handler(func=lambda m: True)
    def search_tg(m):
        q = m.text.strip().lower()
        if len(q) < 3: return
        try:
            data = pd.read_csv(DATABASE_FILE, low_memory=False)
            data.columns = [c.strip().lower() for c in data.columns]
            res = data[(data['red_last_name'].str.lower().str.contains(q, na=False)) | 
                       (data['blue_last_name'].str.lower().str.contains(q, na=False))].copy()
            if res.empty: return
            res['date_start'] = pd.to_datetime(res['date_start'], errors='coerce')
            res = res.sort_values(['date_start', 'round_code'], ascending=[False, True]).head(10)
            msg = "👤 " + q.upper() + "\n" + "="*15 + "\n"
            for _, r in res.iterrows():
                is_win = "✅" if str(r['winner_athlete_id']) == (str(r['red_id']) if q in str(r['red_last_name']).lower() else str(r['blue_id'])) else "❌"
                msg += is_win + " " + str(r['date_start'].year) + " | " + str(int(r['red_score'])) + ":" + str(int(r['blue_score'])) + "\n"
            bot.send_message(m.chat.id, msg)
        except: pass
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

if "bot_active" not in st.session_state:
    threading.Thread(target=start_bot, daemon=True).start()
    st.session_state.bot_active = True

# --- ИНТЕРФЕЙС ---
st.title("FIGHTGURU DATA")

if df is not None:
    nav = st.sidebar.radio("Меню", ["👤 Досье", "🏛️ Пантеон"])

    if nav == "👤 Досье":
        search = st.text_input("Фамилия (Osipenko, Mikhailin...):").lower().strip()
        if search:
            matches = df[(df['red_last_name'].str.lower().str.contains(search, na=False)) | 
                         (df['blue_last_name'].str.lower().str.contains(search, na=False))].copy()
            
            if not matches.empty:
                # Сортировка: Сначала по дате (свежие вверху), затем по значимости раунда (Финал первый)
                matches = matches.sort_values(by=['date_start', 'round_rank'], ascending=[False, True])
                
                sample = matches.iloc[0]
                is_red_sample = search in sample['red_last_name'].lower()
                name_display = sample['red_full_name'] if is_red_sample else sample['blue_full_name']
                
                st.subheader(name_display.upper())
                st.markdown(f"<span class='dob-label'>Д.Р. {sample['athlete_dob']}</span>", unsafe_allow_html=True)
                st.divider()

                for _, row in matches.iterrows():
                    is_red = search in str(row['red_last_name']).lower()
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    opp_name = row['blue_full_name'] if is_red else row['red_full_name']
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    stage = ROUND_NAMES.get(str(row['round_code']).upper(), row['round_code'])
                    
                    card_style = "win-card" if is_win else "loss-card"
                    status_text = "ПОБЕДА" if is_win else "ПОРАЖЕНИЕ"

                    st.markdown(f"""
                    <div class="match-card {card_style}">
                        <div class="match-header">
                            <span>{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '????'}</span>
                            <span>{status_text}</span>
                        </div>
                        <div class="match-tournament">{str(row['tournament_name']).upper()}</div>
                        <div class="match-main">
                            <div class="opponent-info">
                                <div class="opponent-name">{opp_name}</div>
                                <div class="opponent-country">{get_flag(opp_country)} {opp_country}</div>
                                <div class="match-stage">{stage} | {row['Human_Category']}</div>
                            </div>
                            <div class="match-score">{int(row['red_score'])}:{int(row['blue_score'])}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Атлет не найден.")
    
    elif nav == "🏛️ Пантеон":
        st.info("Раздел Пантеон активен. Используйте боковую панель для выбора дивизиона.")

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

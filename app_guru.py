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

# --- СТИЛИЗАЦИЯ (CSS) ---
st.markdown("""
<style>
    .stDownloadButton button { background-color: #e63946 !important; color: white !important; font-weight: bold !important; width: 100%; border-radius: 8px !important; }
    .stDataFrame { background: #111; border-radius: 10px; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7bcf,#2e7bcf); color: white; }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
DATABASE_FILE = "AllTournament.csv"
FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", 
    "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯", "TKM": "🇹🇲", "AIN": "🏳️", "FRA": "🇫🇷", "SRB": "🇷🇸", "USA": "🇺🇸"
}
COUNTRY_NAMES_RU = {
    "RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН", 
    "MGL": "МОНГОЛИЯ", "GEO": "ГРУЗИЯ", "ARM": "АРМЕНИЯ", "AZE": "АЗЕРБАЙДЖАН", "TJK": "ТАДЖИКИСТАН", 
    "TKM": "ТУРКМЕНИСТАН", "AIN": "НЕЙТР. АТЛЕТ"
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
def load_data_v51():
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
        return df
    except:
        return None

df = load_data_v51()

# --- ЛОГИКА ТЕЛЕГРАМ-БОТА ---
def start_bot():
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

    @bot.message_handler(commands=['start'])
    def send_welcome(m):
        bot.reply_to(m, "FIGHTGURU DATA CENTER\nВведите фамилию атлета латиницей (например: Osipenko):")

    @bot.message_handler(func=lambda m: True)
    def search_athlete(m):
        name_query = m.text.strip().lower()
        if len(name_query) < 3:
            bot.send_message(m.chat.id, "Ошибка: введите минимум 3 буквы.")
            return

        try:
            # Прямое чтение файла
            data = pd.read_csv(DATABASE_FILE, low_memory=False)
            data.columns = [c.strip().lower() for c in data.columns]
            
            # Поиск
            results = data[(data['red_last_name'].str.lower().str.contains(name_query, na=False)) | 
                           (data['blue_last_name'].str.lower().str.contains(name_query, na=False))].copy()
            
            if results.empty:
                bot.send_message(m.chat.id, "Атлет '" + name_query + "' не найден.")
                return

            results['date_start'] = pd.to_datetime(results['date_start'], errors='coerce')
            results = results.sort_values('date_start', ascending=False).head(10)
            
            msg = "👤 ДОСЬЕ: " + name_query.upper() + "\n" + "="*20 + "\n"
            for _, r in results.iterrows():
                date_str = str(r['date_start'].year) if pd.notna(r['date_start']) else "????"
                category = get_readable_cat(r['category_code'])
                
                win_id = str(r['winner_athlete_id']).split('.')[0] if pd.notna(r['winner_athlete_id']) else ""
                red_id = str(r['red_id']).split('.')[0]
                
                is_red = name_query in str(r['red_last_name']).lower()
                won = (win_id == red_id and is_red) or (win_id != red_id and not is_red)
                res_icon = "✅ WIN" if won else "❌ LOSS"
                
                red_side = get_flag(r['red_nationality_code']) + " " + str(r['red_last_name'])
                blue_side = str(r['blue_last_name']) + " " + get_flag(r['blue_nationality_code'])
                
                msg += res_icon + " | " + date_str + " | " + category + "\n"
                msg += red_side + " vs " + blue_side + "\n"
                msg += "Счет: " + str(int(r['red_score'])) + ":" + str(int(r['blue_score'])) + "\n"
                msg += "-"*15 + "\n"
            
            bot.send_message(m.chat.id, msg)
        except Exception as e:
            bot.send_message(m.chat.id, "Проблема с базой данных.")

    bot.infinity_polling(timeout=20, long_polling_timeout=10)

# Запуск бота один раз при старте сессии
if "bot_thread_active" not in st.session_state:
    try:
        t = threading.Thread(target=start_bot, daemon=True)
        t.start()
        st.session_state.bot_thread_active = True
    except:
        pass

# --- ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ---
st.title("FIGHTGURU DATA CENTER v51.0")

if df is not None:
    nav_mode = st.sidebar.radio("Навигация", ["🏛️ Пантеон", "👤 Досье"])

    if nav_mode == "🏛️ Пантеон":
        t_sel = st.sidebar.selectbox("Выберите турнир", list(TOURNAMENT_GROUPS.keys()))
        d_sel = st.sidebar.selectbox("Выберите дивизион", list(DIVISIONS.keys()))
        
        t_pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
        f_data = df[df['tournament_name'].str.contains(t_pattern, case=False, na=False)]
        f_data = f_data[f_data['category_code'].str.contains(DIVISIONS[d_sel], case=False, na=False)]
        
        fin_matches = f_data[f_data['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
        
        if fin_matches.empty:
            st.warning("В базе нет данных по финалам для этого турнира.")
        else:
            def get_winner_info(row):
                if str(row['winner_athlete_id']) == str(row['red_id']):
                    return row['red_full_name'], str(row['red_nationality_code']).upper()
                return row['blue_full_name'], str(row['blue_nationality_code']).upper()
            
            fin_matches[['w_name', 'w_country']] = fin_matches.apply(lambda r: pd.Series(get_winner_info(r)), axis=1)
            
            st.subheader("📊 ИСТОРИЧЕСКИЙ ЗАЧЕТ СТРАН")
            country_stats = fin_matches.groupby('w_country').size().reset_index(name='Gold').sort_values('Gold', ascending=False)
            country_stats['Страна'] = country_stats['w_country'].apply(lambda x: get_flag(x) + " " + get_full_country(x))
            st.dataframe(country_stats[['Страна', 'Gold']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🏆 ПОКАТЕГОРИЙНЫЙ РЕЙТИНГ")
            for cat_name in sorted(fin_matches['Human_Category'].unique()):
                with st.expander("Весовая категория: " + str(cat_name)):
                    sub_df = fin_matches[fin_matches['Human_Category'] == cat_name].sort_values('date_start', ascending=False)
                    st.table(sub_df[['date_start', 'w_name', 'w_country']])

    elif nav_mode == "👤 Досье":
        search_f = st.text_input("Введите фамилию атлета (лат):").lower().strip()
        if search_f:
            res_df = df[(df['red_full_name'].str.lower().str.contains(search_f)) | 
                        (df['blue_full_name'].str.lower().str.contains(search_f))]
            if not res_df.empty:
                st.dataframe(res_df[['date_start', 'tournament_name', 'Human_Category', 'red_full_name', 'blue_full_name', 'score_total']].sort_values('date_start', ascending=False), use_container_width=True)
            else:
                st.info("Атлет не найден в базе данных.")

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

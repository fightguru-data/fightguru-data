import streamlit as st
import pandas as pd
import os
import io
import threading
import telebot
import time
from PIL import Image, ImageDraw, ImageFont

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
    .poster-card { background: #000; border-left: 10px solid #e63946; padding: 30px; color: white; font-family: sans-serif; margin-bottom: 20px; }
    .p-title { font-size: 24px; font-weight: 900; text-transform: uppercase; }
    .p-weight { font-size: 18px; color: #e63946; font-weight: 700; margin-bottom: 15px; }
    .p-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #222; font-size: 14px; }
    .stDataFrame { background: #111; border-radius: 10px; }
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
    return f"{p} {w}кг" if p else c

@st.cache_data(ttl=3600)
def load_data_v50():
    if not os.path.exists(DATABASE_FILE): return None
    df = pd.read_csv(DATABASE_FILE, low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ['winner_athlete_id', 'red_id', 'blue_id']:
        df[col] = df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None)
    df['red_full_name'] = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
    df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
    df['date_start'] = pd.to_datetime(df['date_start'], errors='coerce')
    df['Human_Category'] = df['category_code'].apply(get_readable_cat)
    return df

df = load_data_v50()

# --- ЛОГИКА ТЕЛЕГРАМ-БОТА (ЗАПУСК В ПОТОКЕ) ---
# Эта часть кода оживляет бота @BotFather
if "bot_active" not in st.session_state:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
        
        @bot.message_handler(commands=['start'])
        def welcome(m):
            bot.reply_to(m, "FIGHTGURU DATA CENTER\nВведите фамилию атлета латиницей (например: Osipenko):")

        @bot.message_handler(func=lambda m: True)
        def search_tg(m):
            query = m.text.strip().lower()
            if len(query) < 3:
                bot.send_message(m.chat.id, "Ошибка: введите минимум 3 буквы.")
                return
            
            # Прямое чтение файла для бота
            data = pd.read_csv(DATABASE_FILE, low_memory=False)
            data.columns = [c.strip().lower() for c in data.columns]
            res = data[(data['red_last_name'].str.lower().str.contains(query, na=False)) | 
                       (data['blue_last_name'].str.lower().str.contains(query, na=False))].copy()
            
            if res.empty:
                bot.send_message(m.chat.id, f"Атлет '{}' не найден.")
                return

            res['date_start'] = pd.to_datetime(res['date_start'], errors='coerce')
            res = res.sort_values('date_start', ascending=False).head(10)
            
            out = f"👤 ДОСЬЕ: {query.upper()}\n" + "="*20 + "\n"
            for _, r in res.iterrows():
                date = r['date_start'].year if pd.notna(r['date_start']) else "????"
                cat = get_readable_cat(r['category_code'])
                win_id = str(r['winner_athlete_id']).split('.')[0] if pd.notna(r['winner_athlete_id']) else ""
                red_id = str(r['red_id']).split('.')[0]
                
                # Проверка победителя
                is_red = query in str(r['red_last_name']).lower()
                won = (win_id == red_id and is_red) or (win_id != red_id and not is_red)
                status = "✅ WIN" if won else "❌ LOSS"
                
                red_txt = f"{get_flag(r['red_nationality_code'])} {r['red_last_name']}"
                blue_txt = f"{r['blue_last_name']} {get_flag(r['blue_nationality_code'])}"
                
                out += f"{status} | {} | {}\n{red_txt} vs {blue_txt}\nСчет: {int(r['red_score'])}:{int(r['blue_score'])}\n" + "-"*15 + "\n"
            
            bot.send_message(m.chat.id, out)

        def start_polling():
            bot.infinity_polling(timeout=20, long_polling_timeout=10)

        bot_thread = threading.Thread(target=start_polling, daemon=True)
        bot_thread.start()
        st.session_state.bot_active = True
    except Exception as e:
        pass

# --- ГРАФИЧЕСКИЙ ИНТЕРФЕЙС (STREAMLIT) ---
st.title("FIGHTGURU DATA CENTER v50.0")

if df is not None:
    menu = st.sidebar.radio("Навигация", ["🏛️ Пантеон", "👤 Досье"])

    if menu == "🏛️ Пантеон":
        t_group = st.sidebar.selectbox("Выберите турнир", list(TOURNAMENT_GROUPS.keys()))
        div_name = st.sidebar.selectbox("Выберите дивизион", list(DIVISIONS.keys()))
        
        pattern = '|'.join(TOURNAMENT_GROUPS[t_group])
        filt = df[df['tournament_name'].str.contains(pattern, case=False, na=False)]
        filt = filt[filt['category_code'].str.contains(DIVISIONS[div_name], case=False, na=False)]
        
        finals = filt[filt['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
        
        if finals.empty:
            st.warning("В базе пока нет данных по финалам для этого выбора.")
        else:
            def identify_winner(r):
                if str(r['winner_athlete_id']) == str(r['red_id']):
                    return r['red_full_name'], str(r['red_nationality_code']).upper()
                return r['blue_full_name'], str(r['blue_nationality_code']).upper()
            
            finals[['w_name', 'w_country']] = finals.apply(lambda r: pd.Series(identify_winner(r)), axis=1)
            
            st.subheader("📊 ИСТОРИЧЕСКИЙ ЗАЧЕТ (ВСЕ ГОДА)")
            stats = finals.groupby('w_country').size().reset_index(name='Gold').sort_values('Gold', ascending=False)
            stats['Страна'] = stats['w_country'].apply(lambda x: f"{get_flag(x)} {get_full_country(x)}")
            st.dataframe(stats[['Страна', 'Gold']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🏆 ПОКАТЕГОРИЙНЫЙ РЕЙТИНГ")
            for cat in sorted(finals['Human_Category'].unique()):
                with st.expander(f"Категория: {}"):
                    cat_df = finals[finals['Human_Category'] == cat].sort_values('date_start', ascending=False)
                    st.table(cat_df[['date_start', 'w_name', 'w_country']])

    elif menu == "👤 Досье":
        s_name = st.text_input("Введите фамилию (лат):").lower().strip()
        if s_name:
            res = df[(df['red_full_name'].str.lower().str.contains(s_name)) | 
                     (df['blue_full_name'].str.lower().str.contains(s_name))]
            if not res.empty:
                st.dataframe(res[['date_start', 'tournament_name', 'Human_Category', 'red_full_name', 'blue_full_name', 'score_total']].sort_values('date_start', ascending=False), use_container_width=True)
            else:
                st.info("Атлет не найден в базе.")

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

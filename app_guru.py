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
    /* Отключаем горизонтальный скролл на мобильных */
    .main .block-container { padding-left: 1rem; padding-right: 1rem; }
    
    /* Карточка схватки */
    .match-card {
        background: #111111;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 8px solid #444;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .win-card { border-left-color: #28a745 !important; } /* Зеленый для побед */
    .loss-card { border-left-color: #e63946 !important; } /* Красный для поражений */
    
    .match-header {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
    }
    .match-tournament { font-weight: 800; color: #fff; font-size: 14px; margin-bottom: 10px; }
    .match-main {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .opponent-info { flex: 1; }
    .opponent-name { font-size: 16px; font-weight: 700; color: #fff; }
    .opponent-country { font-size: 13px; color: #aaa; }
    .match-score {
        font-size: 24px;
        font-weight: 900;
        color: #e63946;
        padding-left: 15px;
        min-width: 60px;
        text-align: right;
    }
    .match-cat { font-size: 12px; color: #e63946; font-weight: 600; margin-top: 5px; }
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
def load_data_v54():
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
        
        dob_cols = [c for c in df.columns if any(x in c for x in ['birth', 'birthday', 'рождения'])]
        df['athlete_dob'] = df[dob_cols[0]].fillna('Н/Д') if dob_cols else 'Н/Д'

        df['red_score'] = pd.to_numeric(df['red_score'], errors='coerce').fillna(0).astype(int)
        df['blue_score'] = pd.to_numeric(df['blue_score'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return None

df = load_data_v54()

# --- ТЕЛЕГРАМ БОТ ---
def start_bot():
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    @bot.message_handler(commands=['start'])
    def welcome(m): bot.reply_to(m, "FIGHTGURU: Введите фамилию латиницей")
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
            res = res.sort_values('date_start', ascending=False).head(10)
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
st.title("FIGHTGURU DATA CENTER")

if df is not None:
    nav_mode = st.sidebar.radio("Навигация", ["👤 Досье", "🏛️ Пантеон"])

    if nav_mode == "👤 Досье":
        search_f = st.text_input("Поиск (фамилия латиницей):", placeholder="Osipenko...").lower().strip()
        
        if search_f:
            # Находим все схватки атлета
            athlete_matches = df[(df['red_last_name'].str.lower().str.contains(search_f, na=False)) | 
                                 (df['blue_last_name'].str.lower().str.contains(search_f, na=False))].copy()
            
            if not athlete_matches.empty:
                athlete_matches = athlete_matches.sort_values('date_start', ascending=False)
                
                # Заголовок досье
                # Берем имя из первой найденной строки, где фамилия совпадает (вдруг частичное совпадение)
                sample = athlete_matches.iloc[0]
                real_name = sample['red_full_name'] if search_f in sample['red_last_name'].lower() else sample['blue_full_name']
                st.header(real_name.upper())
                st.caption(f"📅 Дата рождения: {sample['athlete_dob']}")
                st.divider()

                # Рендеринг карточек
                for _, row in athlete_matches.iterrows():
                    # Определяем сторону атлета (красный или синий)
                    is_red = search_f in str(row['red_last_name']).lower()
                    
                    # Определяем победу
                    win_id = str(row['winner_athlete_id'])
                    is_win = (is_red and win_id == str(row['red_id'])) or (not is_red and win_id == str(row['blue_id']))
                    
                    # Данные оппонента
                    opp_name = row['blue_full_name'] if is_red else row['red_full_name']
                    opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
                    
                    # CSS класс карточки
                    card_class = "match-card win-card" if is_win else "match-card loss-card"
                    status_icon = "✅ ПОБЕДА" if is_win else "❌ ПОРАЖЕНИЕ"
                    
                    # HTML Карточка
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div class="match-header">
                            <span>{row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '????'}</span>
                            <span>{status_icon}</span>
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
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Атлет не найден.")

    elif nav_mode == "🏛️ Пантеон":
        st.subheader("🏛️ Исторический Пантеон")
        t_sel = st.selectbox("Турнир", list(TOURNAMENT_GROUPS.keys()))
        d_sel = st.selectbox("Дивизион", list(DIVISIONS.keys()))
        # (Код Пантеона остается прежним для сохранения функционала)
        pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
        f_data = df[df['tournament_name'].str.contains(pattern, case=False, na=False)]
        f_data = f_data[f_data['category_code'].str.contains(DIVISIONS[d_sel], case=False, na=False)]
        fin_matches = f_data[f_data['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
        if not fin_matches.empty:
            def get_winner_info(row):
                if str(row['winner_athlete_id']) == str(row['red_id']):
                    return row['red_full_name'], str(row['red_nationality_code']).upper()
                return row['blue_full_name'], str(row['blue_nationality_code']).upper()
            fin_matches[['w_name', 'w_country']] = fin_matches.apply(lambda r: pd.Series(get_winner_info(r)), axis=1)
            stats = fin_matches.groupby('w_country').size().reset_index(name='Gold').sort_values('Gold', ascending=False)
            stats['Страна'] = stats['w_country'].apply(lambda x: get_flag(x) + " " + get_full_country(x))
            st.dataframe(stats[['Страна', 'Gold']], use_container_width=True, hide_index=True)

st.sidebar.markdown("---")
st.sidebar.write("FIGHTGURU | МИР САМБО")

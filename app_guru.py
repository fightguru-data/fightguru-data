import streamlit as st
import pandas as pd
import os
import threading
import telebot
from PIL import Image
 
# =============================================================================
# ПАРАМЕТРЫ ТЕЛЕГРАМ-БОТА
# ИСПРАВЛЕНИЕ #9: Токен вынесен в st.secrets (создайте .streamlit/secrets.toml)
# В secrets.toml: [telegram] / bot_token = "ВАШ_ТОКЕН"
# =============================================================================
BOT_TOKEN = st.secrets.get("telegram", {}).get("bot_token", "")
# Резервный вариант для разработки (НИКОГДА не коммитьте токен в git!):
# BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
 
# =============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# =============================================================================
st.set_page_config(page_title="FIGHTGURU DATA CENTER", page_icon="🥋", layout="wide")
 
# =============================================================================
# СТИЛИЗАЦИЯ (PREMIUM MONOLITH UI)
# =============================================================================
st.markdown("""
<style>
  .stApp { background-color: #1e1f22; color: #eeeeee; }
  .main .block-container { padding: 1rem 0.5rem; }
 
  /* Единый Монолитный Блок */
  .match-container {
    background-color: #3a3d42;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid #4f5157;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    position: relative;
  }
  .win-edge  { border-left: 8px solid #28a745; }
  .loss-edge { border-left: 8px solid #e63946; }
 
  /* Шапка блока */
  .m-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .m-date   { font-size: 11px; color: #bbb; font-weight: 700; }
  .m-round  { background: #e63946; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 900; }
 
  /* Турнир и Счёт */
  .m-grid   { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
  .m-tourney { font-size: 13px; font-weight: 800; color: #fff; text-transform: uppercase; flex: 1; line-height: 1.2; }
  .m-score  { font-size: 44px; font-weight: 900; color: #fff; line-height: 0.8; letter-spacing: -2px; }
 
  /* Категория */
  .m-cat { font-size: 11px; color: #e63946; font-weight: 800; margin-top: 5px; margin-bottom: 12px; text-transform: uppercase; }
 
  /* Оппонент */
  .opp-label       { font-size: 10px; color: #999; font-weight: 700; margin-bottom: 4px; text-transform: uppercase; }
  .opp-flag-line   { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
  .opp-country-name { font-size: 12px; font-weight: 700; color: #ddd; text-transform: uppercase; }
 
  /* Инфо-строка внутри блока */
  .m-info-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding-top: 10px; border-top: 1px solid #4f5157; margin-top: 5px;
  }
  .m-time  { font-size: 12px; color: #00ff41; font-weight: 800; }
  .m-warn  { font-size: 11px; color: #ffcc00; font-weight: 700; }
  .m-status { font-size: 12px; font-weight: 900; text-transform: uppercase; }
 
  /* Кнопка оппонента */
  div.stButton > button:first-child {
    background-color: #2b2d31; color: #ffffff !important;
    border: 1px solid #4f5157; font-weight: 700; font-size: 15px;
    width: 100%; text-align: left; border-radius: 0 0 12px 12px;
    margin-top: -12px; margin-bottom: 25px; padding: 10px 15px; transition: 0.2s;
  }
  div.stButton > button:hover { border-color: #e63946; background-color: #1e1f22; }
 
  .profile-card {
    background: #3a3d42; padding: 25px; border-radius: 12px;
    text-align: center; border: 1px solid #4f5157; margin-bottom: 25px;
  }
</style>
""", unsafe_allow_html=True)
 
# =============================================================================
# КОНСТАНТЫ
# =============================================================================
DATABASE_FILE = "AllTournament.csv"
 
ROUND_MAP = {
    'FIN':  (7, 'ФИНАЛ'),       'FNL': (7, 'ФИНАЛ'),
    'SFL':  (6, '1/2 ФИНАЛА'),  'QFL': (5, '1/4 ФИНАЛА'),
    'R16':  (4, '1/8 ФИНАЛА'),  'R32': (3, '1/16 ФИНАЛА'),
    'R64':  (2, '1/32 ФИНАЛА'), 'R128': (1, '1/64 ФИНАЛА'),
}
 
FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬",
    "MGL": "🇲🇳", "GEO": "🇬🇪", "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯",
    "TKM": "🇹🇲", "AIN": "🏳️",  "FRA": "🇫🇷", "SRB": "🇷🇸", "USA": "🇺🇸",
    "UKR": "🇺🇦", "BUL": "🇧🇬", "CRO": "🇭🇷", "MKD": "🇲🇰", "ROU": "🇷🇴",
    "ITA": "🇮🇹", "TUR": "🇹🇷", "LAT": "🇱🇻", "ISR": "🇮🇱",
}
 
COUNTRY_NAMES_RU = {
    "RUS": "РОССИЯ",        "BLR": "БЕЛАРУСЬ",      "KAZ": "КАЗАХСТАН",
    "UZB": "УЗБЕКИСТАН",    "KGZ": "КЫРГЫЗСТАН",    "TKM": "ТУРКМЕНИСТАН",
    "MGL": "МОНГОЛИЯ",      "GEO": "ГРУЗИЯ",         "ARM": "АРМЕНИЯ",
    "AZE": "АЗЕРБАЙДЖАН",   "TJK": "ТАДЖИКИСТАН",   "UKR": "УКРАИНА",
    "SRB": "СЕРБИЯ",        "FRA": "ФРАНЦИЯ",        "AIN": "НЕЙТРАЛЬНЫЙ АТЛЕТ",
}
 
TOURNAMENT_GROUPS = {
    "Чемпионат Мира":       ["World Sambo Championships", "World SAMBO Championships"],
    "Кубок Мира":           ["Cup", "President"],
    "Чемпионат Европы":     ["European Sambo Championships", "European Championships"],
    "ЧМ Азии и Океании":   ["Asia and Oceania Sambo Championships"],
}
 
DIVISIONS = {
    "Спортивное Самбо (М)": "SAMM",
    "Спортивное Самбо (Ж)": "SAMW",
    "Боевое Самбо (М)":     "CSMM",
    "Боевое Самбо (Ж)":     "CSMW",
}
 
# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================
 
def format_time(val):
    """Форматирует время боя из миллисекунд или строки в M:SS."""
    try:
        s = str(val).strip()
        if ':' in s:
            return s
        ms = int(float(s))
        if ms == 0:
            return "0:00"
        ts = ms // 1000
        return f"{ts // 60}:{ts % 60:02d}"
    except Exception:
        return "0:00"
 
 
def get_flag(country_code: str) -> str:
    return FLAG_EMOJIS.get(str(country_code).upper().strip(), "🌍")
 
 
def get_country_full(country_code: str) -> str:
    return COUNTRY_NAMES_RU.get(str(country_code).upper().strip(), str(country_code))
 
 
def get_readable_cat(code: str) -> str:
    c = str(code).upper().strip()
    p = "СПОРТ" if "SAM" in c else ("БОЕВОЕ" if "CSM" in c else "")
    g = "М" if ("SAMM" in c or "CSMM" in c) else ("Ж" if ("SAMW" in c or "CSMW" in c) else "")
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts) > 1:
            w = (parts[1][:-1] + "+") if parts[1].endswith('O') else parts[1]
    return f"{p} {g} {w}КГ".strip()
 
 
# ИСПРАВЛЕНИЕ #3: clean_warn вынесена из цикла
def clean_warn(v) -> int:
    """Безопасно конвертирует значение предупреждений в int."""
    try:
        return int(float(v)) if pd.notna(v) else 0
    except (ValueError, TypeError):
        return 0
 
 
# ИСПРАВЛЕНИЕ #6: безопасное получение счёта
def safe_int(val, default: int = 0) -> int:
    try:
        return int(float(val)) if pd.notna(val) else default
    except (ValueError, TypeError):
        return default
 
 
# =============================================================================
# ЗАГРУЗКА ДАННЫХ
# =============================================================================
 
@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DATABASE_FILE):
        return None
    try:
        df = pd.read_csv(DATABASE_FILE, low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]
 
        for col in ['winner_athlete_id', 'red_id', 'blue_id']:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None
                )
 
        df['red_full_name']  = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
        df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
        df['date_start']     = pd.to_datetime(df['date_start'], errors='coerce')
        df['round_rank']     = df['round_code'].apply(
            lambda x: ROUND_MAP.get(str(x).upper(), (0, str(x)))[0]
        )
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return None
 
 
df = load_data()
 
# =============================================================================
# ЛОГИКА ТЕЛЕГРАМ-БОТА
# ИСПРАВЛЕНИЕ #5: добавлен bot.infinity_polling() внутри потока
# =============================================================================
 
if "bot_active" not in st.session_state:
    st.session_state.bot_active = False
 
if BOT_TOKEN and not st.session_state.bot_active:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
 
        @bot.message_handler(commands=['start'])
        def welcome(m):
            bot.reply_to(m, "FIGHTGURU: Введите фамилию атлета для поиска.")
 
        @bot.message_handler(func=lambda m: True)
        def bot_search(m):
            q = m.text.strip().lower()
            if len(q) < 3:
                bot.reply_to(m, "Введите минимум 3 символа.")
                return
            if df is not None:
                b_res = df[
                    df['red_last_name'].str.lower().str.contains(q, na=False) |
                    df['blue_last_name'].str.lower().str.contains(q, na=False)
                ].copy()
                if not b_res.empty:
                    b_res = b_res.sort_values('date_start', ascending=False).head(5)
                    msg = f"📊 ДОСЬЕ: {q.upper()}\n"
                    for _, r in b_res.iterrows():
                        year = r['date_start'].year if pd.notna(r['date_start']) else "????"
                        msg += (
                            f"\n🗓 {year} | {str(r['tournament_name'])[:30]}\n"
                            f"Счёт: {safe_int(r.get('red_score'))}:{safe_int(r.get('blue_score'))}\n"
                        )
                    bot.send_message(m.chat.id, msg)
                else:
                    bot.reply_to(m, "Атлет не найден.")
 
        def _run_bot():
            # ИСПРАВЛЕНИЕ #5: запускаем polling, чтобы бот реально слушал
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
 
        threading.Thread(target=_run_bot, daemon=True).start()
        st.session_state.bot_active = True
 
    except Exception as e:
        st.warning(f"Бот не запущен: {e}")
 
# =============================================================================
# ИНИЦИАЛИЗАЦИЯ SESSION STATE
# =============================================================================
 
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
 
# =============================================================================
# ИНТЕРФЕЙС — САЙДБАР
# =============================================================================
 
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=200)
    else:
        st.title("FIGHTGURU")
    nav = st.radio("Навигация", ["👤 Досье", "🏛️ Пантеон"])
 
# =============================================================================
# ОСНОВНОЙ ИНТЕРФЕЙС
# =============================================================================
 
if df is None:
    st.error(f"Файл базы данных '{DATABASE_FILE}' не найден. Поместите его в папку с приложением.")
    st.stop()
 
# ─────────────────────────────────────────────────────────
# РАЗДЕЛ: ДОСЬЕ
# ─────────────────────────────────────────────────────────
if nav == "👤 Досье":
    search_input = st.text_input(
        "ПОИСК АТЛЕТА:",
        value=st.session_state.search_query,
        placeholder="Напр. Zinnatov"
    )
 
    if search_input:
        search_low = search_input.lower().strip()
 
        matches = df[
            df['red_last_name'].str.lower().str.contains(search_low, na=False) |
            df['blue_last_name'].str.lower().str.contains(search_low, na=False)
        ].copy()
 
        if matches.empty:
            st.info("Атлет не найден.")
        else:
            matches = matches.sort_values(
                ['date_start', 'round_rank'], ascending=[False, False]
            )
 
            # --- Профильная карточка ---
            dob_list   = []
            final_name = ""
 
            for _, r in matches.iterrows():
                if search_low in str(r['red_last_name']).lower():
                    final_name = r['red_full_name']
                    c_dob = next((c for c in r.index if 'birth' in c and 'red' in c), None)
                    if c_dob and pd.notna(r[c_dob]):
                        dob_list.append(str(r[c_dob]).strip())
                elif search_low in str(r['blue_last_name']).lower():
                    final_name = r['blue_full_name']
                    c_dob = next((c for c in r.index if 'birth' in c and 'blue' in c), None)
                    if c_dob and pd.notna(r[c_dob]):
                        dob_list.append(str(r[c_dob]).strip())
 
            # ИСПРАВЛЕНИЕ #7: безопасная логика определения даты рождения
            athlete_dob = max(set(dob_list), key=dob_list.count) if dob_list else "Н/Д"
 
            st.markdown(f"""
            <div class="profile-card">
              <h2 style="margin:0; color:#e63946; font-size:26px; font-weight:900;">{final_name.upper()}</h2>
              <p style="margin:10px 0 0 0; color:#aaa; font-size:14px; font-weight:700;">
                📅 ДАТА РОЖДЕНИЯ: <span style="color:#fff;">{athlete_dob}</span>
              </p>
            </div>
            """, unsafe_allow_html=True)
 
            # --- ИСПРАВЛЕНИЕ #2: цикл теперь правильно отступлен внутри блока else ---
            for _, row in matches.iterrows():
                is_red = search_low in str(row['red_last_name']).lower()
                win_id = str(row.get('winner_athlete_id', ''))
                is_win = (
                    (is_red     and win_id == str(row.get('red_id',  ''))) or
                    (not is_red and win_id == str(row.get('blue_id', '')))
                )
 
                # Предупреждения
                w_red_val  = row.get('red_warning',  row.get('red_warnings',  0))
                w_blue_val = row.get('blue_warning', row.get('blue_warnings', 0))
                my_w = clean_warn(w_red_val  if is_red else w_blue_val)
                op_w = clean_warn(w_blue_val if is_red else w_red_val)
 
                opp_last    = str(row['blue_last_name']  if is_red else row['red_last_name'])
                opp_full    = str(row['blue_full_name']  if is_red else row['red_full_name'])
                opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']
 
                round_label = ROUND_MAP.get(str(row['round_code']).upper(), (0, str(row['round_code'])))[1]
                cls     = "win-edge" if is_win else "loss-edge"
                res_tag = "WIN"    if is_win else "LOSS"
 
                date_str = row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??.??.????'
                red_sc   = safe_int(row.get('red_score',  0))
                blue_sc  = safe_int(row.get('blue_score', 0))
 
                st.markdown(f"""
                <div class="match-container {cls}">
                  <div class="m-header">
                    <span class="m-date">{date_str}</span>
                    <span class="m-round">{round_label}</span>
                  </div>
                  <div class="m-grid">
                    <div class="m-tourney">{str(row['tournament_name'])}</div>
                    <div class="m-score">{red_sc}:{blue_sc}</div>
                  </div>
                  <div class="m-cat">{get_readable_cat(row['category_code'])}</div>
                  <div class="opp-label">СОПЕРНИК:</div>
                  <div class="opp-flag-line">
                    <span class="flag-txt">{get_flag(opp_country)}</span>
                    <span class="opp-country-name">{get_country_full(opp_country)}</span>
                  </div>
                  <div class="m-info-bar">
                    <div class="m-time">⏱ {format_time(row['fight_time'])}</div>
                    <div class="m-warn">ПРЕД: {my_w} / {op_w}</div>
                    <div class="m-status" style="color: {'#28a745' if is_win else '#e63946'};">{res_tag}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
 
                # ИСПРАВЛЕНИЕ #4: используем on_click вместо rerun после button
                if st.button(f"{opp_full.upper()}", key=f"btn_{row.name}"):
                    st.session_state.search_query = opp_last
                    st.rerun()
 
# ─────────────────────────────────────────────────────────
# РАЗДЕЛ: ПАНТЕОН
# ─────────────────────────────────────────────────────────
elif nav == "🏛️ Пантеон":
    st.header("🏛️ Исторический Пантеон")
 
    t_sel   = st.selectbox("Турнир",    list(TOURNAMENT_GROUPS.keys()))
    div_sel = st.selectbox("Дивизион",  list(DIVISIONS.keys()))
 
    pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
    f_data  = df[
        df['tournament_name'].str.contains(pattern, case=False, na=False) &
        df['category_code'].str.contains(DIVISIONS[div_sel], case=False, na=False)
    ]
 
    fin_matches = f_data[
        f_data['round_code'].str.contains('FNL|FIN', case=False, na=False)
    ].copy()
 
    if fin_matches.empty:
        st.warning("Нет данных по выбранным фильтрам.")
    else:
        def get_w_info(r):
            if str(r['winner_athlete_id']) == str(r['red_id']):
                return r['red_full_name'], str(r['red_nationality_code']).upper()
            return r['blue_full_name'], str(r['blue_nationality_code']).upper()
 
        fin_matches[['w_name', 'w_country']] = fin_matches.apply(
            lambda r: pd.Series(get_w_info(r)), axis=1
        )
 
        st.subheader("📊 Зачёт по странам (GOLD)")
        stats = (
            fin_matches.groupby('w_country').size()
            .reset_index(name='Gold')
            .sort_values('Gold', ascending=False)
        )
        stats['Страна'] = stats['w_country'].apply(
            lambda x: get_flag(x) + " " + get_country_full(x)
        )
        # ИСПРАВЛЕНИЕ #11: используем st.dataframe вместо st.table для интерактивности
        st.dataframe(stats[['Страна', 'Gold']], use_container_width=True, hide_index=True)
 
        for cat in sorted(fin_matches['category_code'].unique()):
            with st.expander(f"Вес: {get_readable_cat(cat)}"):
                cat_df = fin_matches[fin_matches['category_code'] == cat].sort_values(
                    'date_start', ascending=False
                )
                st.dataframe(
                    cat_df[['date_start', 'w_name', 'w_country']].rename(columns={
                        'date_start': 'Дата', 'w_name': 'Победитель', 'w_country': 'Страна'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
 
# =============================================================================
# ПОДВАЛ
# =============================================================================
st.markdown("""
<hr>
<div style="text-align:center; color:#555; font-size:12px;">FIGHTGURU | МИР САМБО</div>
""", unsafe_allow_html=True)

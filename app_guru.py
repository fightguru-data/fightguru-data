import streamlit as st
import pandas as pd
import os
import threading
import telebot

# =============================================================================
# ТОКЕН БОТА — хранить в .streamlit/secrets.toml:
#   [telegram]
#   bot_token = "ВАШ_ТОКЕН"
# =============================================================================
BOT_TOKEN = st.secrets.get("telegram", {}).get("bot_token", "")

# =============================================================================
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# =============================================================================
st.set_page_config(page_title="FIGHTGURU", page_icon="🥋", layout="wide")

# =============================================================================
# CSS — новый дизайн
# =============================================================================
st.markdown("""
<style>
  /* ── базовый фон ── */
  .stApp { background-color: #13141a; color: #e8e8e8; }
  .main .block-container { padding: 1.2rem 1rem 2rem; max-width: 860px; }

  /* ── профильная карточка ── */
  .profile-card {
    background: #1e2029;
    border: 1px solid #2e3040;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .avatar {
    width: 50px; height: 50px; border-radius: 50%;
    background: #c0392b;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; font-weight: 700; color: #fff; flex-shrink: 0;
  }
  .profile-name { font-size: 18px; font-weight: 700; color: #f0f0f0; }
  .profile-meta { font-size: 12px; color: #888; margin-top: 3px; }

  /* ── статы (4 плашки) ── */
  .stat-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }
  .stat-card {
    background: #1e2029;
    border: 1px solid #2e3040;
    border-radius: 10px;
    padding: 11px 14px;
  }
  .stat-label { font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
  .stat-val   { font-size: 22px; font-weight: 700; color: #f0f0f0; }
  .stat-val.green { color: #2ecc71; }
  .stat-val.red   { color: #e74c3c; }

  /* ── фильтры ── */
  .filter-row { display: flex; gap: 7px; margin-bottom: 14px; align-items: center; flex-wrap: wrap; }
  .f-label    { font-size: 11px; color: #555; }
  .f-btn {
    font-size: 11px; padding: 4px 12px; border-radius: 20px;
    border: 1px solid #2e3040; background: #1e2029; color: #888; cursor: pointer;
    transition: all .15s;
  }
  .f-btn.active { background: #c0392b; color: #fff; border-color: #c0392b; }

  /* ── разделитель года ── */
  .year-label {
    font-size: 10px; font-weight: 700; color: #555;
    text-transform: uppercase; letter-spacing: .1em;
    margin: 18px 0 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #2e3040;
  }

  /* ── карточка матча ── */
  .match-card {
    background: #1e2029;
    border: 1px solid #2e3040;
    border-radius: 12px;
    padding: 13px 15px;
    margin-bottom: 7px;
    display: grid;
    grid-template-columns: 56px 1fr auto;
    gap: 0 14px;
    align-items: center;
    border-left: 3px solid transparent;
    transition: border-color .15s;
  }
  .match-card:hover { border-color: #3a3d52; }
  .match-card.win  { border-left-color: #2ecc71; }
  .match-card.loss { border-left-color: #e74c3c; }

  /* значок результата */
  .result-badge {
    width: 50px; height: 50px; border-radius: 10px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 1px; flex-shrink: 0;
  }
  .result-badge.win  { background: #0d2b1a; }
  .result-badge.loss { background: #2b0d0d; }
  .badge-score { font-size: 16px; font-weight: 700; line-height: 1; }
  .badge-score.win  { color: #2ecc71; }
  .badge-score.loss { color: #e74c3c; }
  .badge-label { font-size: 9px; font-weight: 700; letter-spacing: .05em; }
  .badge-label.win  { color: #27ae60; }
  .badge-label.loss { color: #c0392b; }

  /* центральная часть */
  .m-tourney {
    font-size: 11px; color: #555;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    margin-bottom: 4px;
  }
  .m-opponent {
    font-size: 14px; font-weight: 600; color: #e8e8e8;
    display: flex; align-items: center; gap: 7px; margin-bottom: 5px;
  }
  .m-tags { display: flex; gap: 5px; flex-wrap: wrap; }
  .tag {
    font-size: 10px; padding: 2px 8px; border-radius: 20px;
    background: #252831; color: #666; border: 1px solid #2e3040;
  }
  .tag.round   { background: #2b0d0d; color: #c0392b; border-color: #4a1a1a; }
  .tag.penalty { background: #2b2200; color: #b8860b; border-color: #443300; }
  .tag.cat     { color: #555; }

  /* правая часть */
  .m-right      { text-align: right; flex-shrink: 0; }
  .m-date       { font-size: 11px; color: #555; margin-bottom: 4px; }
  .m-time       { font-size: 12px; color: #444; }

  /* кнопка перехода к сопернику — встроена внутри карточки */
  .opp-link {
    font-size: 11px; color: #4a7fa5; cursor: pointer;
    margin-left: 4px; text-decoration: none;
  }
  .opp-link:hover { color: #7ab3d4; }

  /* ── Пантеон ── */
  .pantheon-header {
    font-size: 22px; font-weight: 700; color: #f0f0f0;
    margin-bottom: 20px;
  }
  .gold-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
  .gold-table th {
    font-size: 10px; color: #555; text-transform: uppercase;
    letter-spacing: .06em; text-align: left;
    padding: 6px 10px; border-bottom: 1px solid #2e3040;
  }
  .gold-table td { font-size: 13px; color: #ccc; padding: 8px 10px; border-bottom: 1px solid #1a1c24; }
  .gold-table tr:hover td { background: #1e2029; }
  .gold-num { font-weight: 700; color: #f0d060; }

  /* ── поиск ── */
  div[data-testid="stTextInput"] input {
    background: #1e2029 !important;
    border: 1px solid #2e3040 !important;
    border-radius: 10px !important;
    color: #e8e8e8 !important;
    font-size: 14px !important;
  }

  /* ── сайдбар ── */
  section[data-testid="stSidebar"] {
    background-color: #17181f !important;
    border-right: 1px solid #2e3040 !important;
  }

  /* ── прячем стандартный radio label ── */
  div[data-testid="stSidebar"] .stRadio label { color: #aaa; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# КОНСТАНТЫ
# =============================================================================
DATABASE_FILE = "AllTournament.csv"

ROUND_MAP = {
    'FIN': (7, 'Финал'),    'FNL': (7, 'Финал'),
    'SFL': (6, '1/2'),      'QFL': (5, '1/4'),
    'R16': (4, '1/8'),      'R32': (3, '1/16'),
    'R64': (2, '1/32'),     'R128': (1, '1/64'),
}
FINALS_CODES = {'FIN', 'FNL'}

FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬",
    "MGL": "🇲🇳", "GEO": "🇬🇪", "ARM": "🇦🇲", "AZE": "🇦🇿", "TJK": "🇹🇯",
    "TKM": "🇹🇲", "AIN": "🏳️",  "FRA": "🇫🇷", "SRB": "🇷🇸", "USA": "🇺🇸",
    "UKR": "🇺🇦", "BUL": "🇧🇬", "CRO": "🇭🇷", "MKD": "🇲🇰", "ROU": "🇷🇴",
    "ITA": "🇮🇹", "TUR": "🇹🇷", "LAT": "🇱🇻", "ISR": "🇮🇱", "GBR": "🇬🇧",
    "GER": "🇩🇪", "NED": "🇳🇱", "GRE": "🇬🇷", "LTU": "🇱🇹", "MDA": "🇲🇩",
}

COUNTRY_NAMES_RU = {
    "RUS": "Россия",       "BLR": "Беларусь",     "KAZ": "Казахстан",
    "UZB": "Узбекистан",   "KGZ": "Кыргызстан",   "TKM": "Туркменистан",
    "MGL": "Монголия",     "GEO": "Грузия",        "ARM": "Армения",
    "AZE": "Азербайджан",  "TJK": "Таджикистан",   "UKR": "Украина",
    "SRB": "Сербия",       "FRA": "Франция",       "AIN": "Нейтральный атлет",
    "TUR": "Турция",       "BUL": "Болгария",      "CRO": "Хорватия",
    "GBR": "Великобритания", "GER": "Германия",    "NED": "Нидерланды",
    "GRE": "Греция",       "LTU": "Литва",         "MDA": "Молдова",
    "LAT": "Латвия",       "ISR": "Израиль",
}

TOURNAMENT_GROUPS = {
    "Чемпионат Мира":     ["World Sambo Championships", "World SAMBO Championships"],
    "Кубок Мира":         ["Cup", "President"],
    "Чемпионат Европы":   ["European Sambo Championships", "European Championships"],
    "ЧМ Азии и Океании":  ["Asia and Oceania Sambo Championships"],
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

def format_time(val) -> str:
    try:
        s = str(val).strip()
        if ':' in s:
            return s
        ms = int(float(s))
        if ms == 0:
            return "—"
        ts = ms // 1000
        return f"{ts // 60}:{ts % 60:02d}"
    except Exception:
        return "—"


def get_flag(code: str) -> str:
    return FLAG_EMOJIS.get(str(code).upper().strip(), "🌍")


def get_country(code: str) -> str:
    return COUNTRY_NAMES_RU.get(str(code).upper().strip(), str(code))


def get_cat(code: str) -> str:
    c = str(code).upper().strip()
    p = "Спорт" if "SAM" in c else ("Боевое" if "CSM" in c else "")
    g = "М" if ("SAMM" in c or "CSMM" in c) else ("Ж" if ("SAMW" in c or "CSMW" in c) else "")
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts) > 1:
            w = (parts[1][:-1] + "+") if parts[1].endswith('O') else parts[1]
    return f"{p} {g} {w}кг".strip()


def clean_int(v, default: int = 0) -> int:
    try:
        return int(float(v)) if pd.notna(v) else default
    except (ValueError, TypeError):
        return default


def get_initials(full_name: str) -> str:
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return full_name[:2].upper() if full_name else "??"


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
        df['year']           = df['date_start'].dt.year
        df['round_rank']     = df['round_code'].apply(
            lambda x: ROUND_MAP.get(str(x).upper(), (0, str(x)))[0]
        )
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return None


df = load_data()

# =============================================================================
# ТЕЛЕГРАМ-БОТ
# =============================================================================

if "bot_active" not in st.session_state:
    st.session_state.bot_active = False

if BOT_TOKEN and not st.session_state.bot_active:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

        @bot.message_handler(commands=['start'])
        def welcome(m):
            bot.reply_to(m, "FIGHTGURU: введите фамилию атлета.")

        @bot.message_handler(func=lambda m: True)
        def bot_search(m):
            q = m.text.strip().lower()
            if len(q) < 3:
                bot.reply_to(m, "Минимум 3 символа.")
                return
            if df is not None:
                res = df[
                    df['red_last_name'].str.lower().str.contains(q, na=False) |
                    df['blue_last_name'].str.lower().str.contains(q, na=False)
                ].sort_values('date_start', ascending=False).head(5)
                if not res.empty:
                    msg = f"📊 {q.upper()}\n"
                    for _, r in res.iterrows():
                        yr = r['date_start'].year if pd.notna(r['date_start']) else "????"
                        msg += f"\n🗓 {yr} | {str(r['tournament_name'])[:30]}\n{clean_int(r.get('red_score'))}:{clean_int(r.get('blue_score'))}\n"
                    bot.send_message(m.chat.id, msg)
                else:
                    bot.reply_to(m, "Атлет не найден.")

        def _run_bot():
            bot.infinity_polling(timeout=10, long_polling_timeout=5)

        threading.Thread(target=_run_bot, daemon=True).start()
        st.session_state.bot_active = True
    except Exception as e:
        st.warning(f"Бот не запущен: {e}")

# =============================================================================
# SESSION STATE
# =============================================================================
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'filter_mode' not in st.session_state:
    st.session_state.filter_mode = "Все"

# =============================================================================
# САЙДБАР
# =============================================================================
with st.sidebar:
    st.markdown("## 🥋 FightGuru")
    st.markdown("---")
    nav = st.radio("", ["👤 Досье", "🏛️ Пантеон"], label_visibility="collapsed")

# =============================================================================
# GUARD
# =============================================================================
if df is None:
    st.error(f"Файл '{DATABASE_FILE}' не найден. Поместите его рядом с приложением.")
    st.stop()

# =============================================================================
# РАЗДЕЛ: ДОСЬЕ
# =============================================================================
if nav == "👤 Досье":

    search_input = st.text_input(
        "Поиск атлета",
        value=st.session_state.search_query,
        placeholder="Введите фамилию — напр. Karashtin",
        label_visibility="collapsed",
    )

    if not search_input:
        st.markdown(
            "<p style='color:#444; font-size:13px; margin-top:30px; text-align:center;'>"
            "Введите фамилию атлета для поиска</p>",
            unsafe_allow_html=True,
        )
        st.stop()

    search_low = search_input.lower().strip()

    matches = df[
        df['red_last_name'].str.lower().str.contains(search_low, na=False) |
        df['blue_last_name'].str.lower().str.contains(search_low, na=False)
    ].copy()

    if matches.empty:
        st.info("Атлет не найден. Проверьте написание фамилии.")
        st.stop()

    matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])

    # ── собираем данные атлета ────────────────────────────────────────────────
    dob_list   = []
    final_name = ""
    country_list = []

    for _, r in matches.iterrows():
        if search_low in str(r['red_last_name']).lower():
            final_name = r['red_full_name']
            dob_val = r.get('red_birth_date')
            if dob_val is not None and pd.notna(dob_val):
                dob_list.append(str(dob_val).strip())
            country_list.append(str(r.get('red_nationality_code', '')).upper())
        elif search_low in str(r['blue_last_name']).lower():
            final_name = r['blue_full_name']
            dob_val = r.get('blue_birth_date')
            if dob_val is not None and pd.notna(dob_val):
                dob_list.append(str(dob_val).strip())
            country_list.append(str(r.get('blue_nationality_code', '')).upper())

    athlete_dob     = max(set(dob_list), key=dob_list.count) if dob_list else "Н/Д"
    athlete_country = max(set(country_list), key=country_list.count) if country_list else ""

    # форматируем дату: 2004-01-22 → 22.01.2004
    try:
        from datetime import datetime
        athlete_dob_fmt = datetime.strptime(athlete_dob, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        athlete_dob_fmt = athlete_dob

    # ── считаем статистику ────────────────────────────────────────────────────
    wins   = 0
    losses = 0
    finals = 0

    for _, row in matches.iterrows():
        is_red = search_low in str(row['red_last_name']).lower()
        win_id = str(row.get('winner_athlete_id', ''))
        my_id  = str(row.get('red_id', '')) if is_red else str(row.get('blue_id', ''))
        won    = (win_id == my_id)
        if won:
            wins += 1
        else:
            losses += 1
        if str(row.get('round_code', '')).upper() in FINALS_CODES:
            finals += 1

    total = wins + losses

    # ── профильная карточка ───────────────────────────────────────────────────
    initials = get_initials(final_name)
    flag     = get_flag(athlete_country)
    country  = get_country(athlete_country)

    st.markdown(f"""
    <div class="profile-card">
      <div class="avatar">{initials}</div>
      <div>
        <div class="profile-name">{final_name}</div>
        <div class="profile-meta">{flag} {country} &nbsp;·&nbsp; Дата рождения: {athlete_dob_fmt}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── stat-плашки ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-label">Всего боёв</div>
        <div class="stat-val">{total}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Победы</div>
        <div class="stat-val green">{wins}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Поражения</div>
        <div class="stat-val red">{losses}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Финалы</div>
        <div class="stat-val">{finals}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── фильтры ───────────────────────────────────────────────────────────────
    filter_options = ["Все", "Победы", "Поражения", "Финалы"]
    cols = st.columns(len(filter_options) + 1)
    cols[0].markdown("<span class='f-label'>Показать:</span>", unsafe_allow_html=True)
    for i, opt in enumerate(filter_options):
        if cols[i + 1].button(
            opt,
            key=f"filt_{opt}",
            type="primary" if st.session_state.filter_mode == opt else "secondary",
        ):
            st.session_state.filter_mode = opt
            st.rerun()

    # ── рендер карточек матчей ────────────────────────────────────────────────
    current_year = None

    for _, row in matches.iterrows():
        is_red = search_low in str(row['red_last_name']).lower()
        win_id = str(row.get('winner_athlete_id', ''))
        my_id  = str(row.get('red_id', '')) if is_red else str(row.get('blue_id', ''))
        is_win = (win_id == my_id)

        # применяем фильтр
        fm = st.session_state.filter_mode
        rc = str(row.get('round_code', '')).upper()
        if fm == "Победы"    and not is_win:                  continue
        if fm == "Поражения" and is_win:                      continue
        if fm == "Финалы"    and rc not in FINALS_CODES:      continue

        # счёт: мой : соперника
        my_sc  = clean_int(row.get('red_score')  if is_red else row.get('blue_score'))
        opp_sc = clean_int(row.get('blue_score') if is_red else row.get('red_score'))

        # предупреждения
        my_pen  = clean_int(row.get('red_penalties')  if is_red else row.get('blue_penalties'))
        opp_pen = clean_int(row.get('blue_penalties') if is_red else row.get('red_penalties'))

        opp_full    = str(row['blue_full_name'] if is_red else row['red_full_name'])
        opp_last    = str(row['blue_last_name'] if is_red else row['red_last_name'])
        opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']

        round_label = ROUND_MAP.get(rc, (0, rc))[1]
        cat_label   = get_cat(row.get('category_code', ''))
        date_str    = row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??.??.????'
        year        = row.get('year')
        time_str    = format_time(row.get('fight_time', 0))

        res_cls   = "win" if is_win else "loss"
        res_label = "WIN" if is_win else "LOSS"

        # ── разделитель года ──────────────────────────────────────────────────
        if pd.notna(year) and int(year) != current_year:
            current_year = int(year)
            st.markdown(f'<div class="year-label">{current_year}</div>', unsafe_allow_html=True)

        # ── теги ──────────────────────────────────────────────────────────────
        tags_html = f'<span class="tag round">{round_label}</span>'
        tags_html += f'<span class="tag cat">{cat_label}</span>'
        if my_pen > 0 or opp_pen > 0:
            tags_html += f'<span class="tag penalty">Пред. {my_pen} / {opp_pen}</span>'

        opp_flag = get_flag(opp_country)

        # ── карточка матча ─────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="match-card {res_cls}">
          <div class="result-badge {res_cls}">
            <span class="badge-score {res_cls}">{my_sc}:{opp_sc}</span>
            <span class="badge-label {res_cls}">{res_label}</span>
          </div>
          <div style="min-width:0;">
            <div class="m-tourney">{str(row.get('tournament_name',''))}</div>
            <div class="m-opponent">
              <span style="font-size:15px;">{opp_flag}</span>
              <span>{opp_full}</span>
            </div>
            <div class="m-tags">{tags_html}</div>
          </div>
          <div class="m-right">
            <div class="m-date">{date_str}</div>
            <div class="m-time">⏱ {time_str}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # кнопка перехода к досье соперника — тонкая, под карточкой
        if st.button(f"→ Досье: {opp_full}", key=f"opp_{row.name}", use_container_width=False):
            st.session_state.search_query = opp_last
            st.session_state.filter_mode  = "Все"
            st.rerun()

# =============================================================================
# РАЗДЕЛ: ПАНТЕОН
# =============================================================================
elif nav == "🏛️ Пантеон":

    st.markdown('<div class="pantheon-header">🏛️ Исторический Пантеон</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        t_sel = st.selectbox("Турнир", list(TOURNAMENT_GROUPS.keys()))
    with col2:
        div_sel = st.selectbox("Дивизион", list(DIVISIONS.keys()))

    pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
    f_data  = df[
        df['tournament_name'].str.contains(pattern, case=False, na=False) &
        df['category_code'].str.contains(DIVISIONS[div_sel], case=False, na=False)
    ]
    fin_matches = f_data[
        f_data['round_code'].str.upper().str.contains('FNL|FIN', na=False)
    ].copy()

    if fin_matches.empty:
        st.warning("Нет данных по выбранным фильтрам.")
        st.stop()

    def get_winner(r):
        if str(r['winner_athlete_id']) == str(r['red_id']):
            return r['red_full_name'], str(r['red_nationality_code']).upper()
        return r['blue_full_name'], str(r['blue_nationality_code']).upper()

    fin_matches[['w_name', 'w_country']] = fin_matches.apply(
        lambda r: pd.Series(get_winner(r)), axis=1
    )

    # ── зачёт по странам ─────────────────────────────────────────────────────
    st.markdown("**Зачёт по странам — золото**")
    stats = (
        fin_matches.groupby('w_country').size()
        .reset_index(name='gold')
        .sort_values('gold', ascending=False)
    )

    rows_html = ""
    for _, sr in stats.iterrows():
        f  = get_flag(sr['w_country'])
        cn = get_country(sr['w_country'])
        rows_html += f"<tr><td>{f} {cn}</td><td class='gold-num'>{sr['gold']}</td></tr>"

    st.markdown(f"""
    <table class="gold-table">
      <thead><tr><th>Страна</th><th>Золото</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

    # ── по весовым категориям ─────────────────────────────────────────────────
    st.markdown("**Победители по весам**")
    for cat in sorted(fin_matches['category_code'].unique()):
        cat_df = fin_matches[fin_matches['category_code'] == cat].sort_values(
            'date_start', ascending=False
        )
        with st.expander(get_cat(cat)):
            for _, cr in cat_df.iterrows():
                yr = int(cr['date_start'].year) if pd.notna(cr['date_start']) else "????"
                f  = get_flag(cr['w_country'])
                st.markdown(
                    f"**{yr}** &nbsp; {f} {cr['w_name']}",
                    unsafe_allow_html=True,
                )

# =============================================================================
# ПОДВАЛ
# =============================================================================
st.markdown(
    "<hr style='border-color:#2e3040; margin-top:40px;'>"
    "<p style='text-align:center; color:#333; font-size:11px;'>FIGHTGURU · Мир самбо</p>",
    unsafe_allow_html=True,
)

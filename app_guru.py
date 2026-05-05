import streamlit as st
import pandas as pd
import os
import json
import random
import threading
import requests
from datetime import datetime

try:
    import telebot
    TELEBOT_AVAILABLE = True
except ImportError:
    TELEBOT_AVAILABLE = False

# =============================================================================
# ТОКЕН БОТА — .streamlit/secrets.toml:
#   [telegram]
#   bot_token = "ВАШ_ТОКЕН"
# =============================================================================
BOT_TOKEN = st.secrets.get("telegram", {}).get("bot_token", "")

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
DATABASE_FILE  = "AllTournament.csv"
INTERVIEWS_FILE = "interviews.json"

st.set_page_config(page_title="FIGHTGURU", page_icon="🥋", layout="wide")

# =============================================================================
# CSS
# =============================================================================
st.markdown("""
<style>
  .stApp { background-color: #13141a; color: #e8e8e8; }
  .main .block-container { padding: 1.2rem 1rem 2rem; max-width: 900px; }

  /* ── профиль ── */
  .profile-card {
    background: #1c1e28; border: 1px solid #2a2d3a; border-radius: 16px;
    padding: 22px 24px; margin-bottom: 10px;
    display: flex; align-items: center; gap: 20px;
  }
  .avatar {
    width: 64px; height: 64px; border-radius: 50%; background: #c0392b;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; font-weight: 700; color: #fff; flex-shrink: 0;
  }
  .profile-name { font-size: 24px; font-weight: 700; color: #f2f2f2; line-height: 1.15; }
  .profile-sub  { font-size: 15px; color: #777; margin-top: 5px; }

  /* ── статы ── */
  .stat-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-bottom: 12px; }
  .stat-card {
    background: #1c1e28; border: 1px solid #2a2d3a; border-radius: 12px; padding: 14px 16px;
  }
  .stat-label { font-size: 11px; color: #555; text-transform: uppercase; letter-spacing:.06em; margin-bottom:5px; }
  .stat-val   { font-size: 30px; font-weight: 700; color: #f0f0f0; line-height:1; }
  .stat-val.g { color: #2ecc71; }
  .stat-val.r { color: #e74c3c; }

  /* ── год-разделитель ── */
  .year-sep {
    font-size: 12px; color: #444; text-transform: uppercase; letter-spacing:.1em;
    padding: 16px 0 8px; border-bottom: 1px solid #222531; margin-bottom: 10px;
  }

  /* ── карточка матча ── */
  .match-card {
    background: #1c1e28; border: 1px solid #2a2d3a; border-radius: 13px;
    padding: 16px 18px; margin-bottom: 8px;
    display: grid; grid-template-columns: 64px 1fr auto;
    gap: 0 16px; align-items: center;
    border-left: 3px solid transparent;
  }
  .match-card.win  { border-left-color: #2ecc71; }
  .match-card.loss { border-left-color: #e74c3c; }

  .badge {
    width: 58px; height: 58px; border-radius: 11px;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 2px; flex-shrink: 0;
  }
  .badge.win  { background: #0d2b1a; }
  .badge.loss { background: #2b0d0d; }
  .bscore { font-size: 20px; font-weight: 700; line-height:1; }
  .bscore.win  { color: #2ecc71; }
  .bscore.loss { color: #e74c3c; }
  .blabel { font-size: 10px; font-weight: 700; letter-spacing:.06em; }
  .blabel.win  { color: #27ae60; }
  .blabel.loss { color: #c0392b; }

  .m-tourney  { font-size: 13px; color: #4a4d5e; margin-bottom:5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .m-opponent { font-size: 17px; font-weight:600; color:#e8e8e8; display:flex; align-items:center; gap:9px; margin-bottom:6px; }
  .m-tags     { display:flex; gap:6px; flex-wrap:wrap; }
  .tag { font-size:12px; padding:3px 11px; border-radius:20px; background:#252831; color:#5a5d70; border:1px solid #2a2d3a; }
  .tag.rnd { background:#2b0d0d; color:#c0392b; border-color:#4a1a1a; }
  .tag.pen { background:#2b2200; color:#b8860b; border-color:#443300; }

  .m-right { text-align:right; flex-shrink:0; }
  .m-date  { font-size:13px; color:#4a4d5e; margin-bottom:5px; }
  .m-time  { font-size:13px; color:#5a5d70; }

  /* ── интервью ── */
  .q-card {
    background:#1c1e28; border:1px solid #2a2d3a; border-radius:12px;
    padding:18px 20px; margin-bottom:10px;
    display:flex; align-items:flex-start; gap:14px;
  }
  .q-num {
    width:30px; height:30px; border-radius:50%;
    background:#c0392b22; border:1px solid #c0392b55;
    display:flex; align-items:center; justify-content:center;
    font-size:14px; font-weight:700; color:#c0392b; flex-shrink:0; margin-top:2px;
  }
  .q-text { font-size:17px; color:#d8d8d8; line-height:1.5; }

  /* ── wikipedia ── */
  .wiki-box {
    background:#1c1e28; border:1px solid #2a2d3a; border-radius:12px;
    padding:18px 20px; margin-bottom:12px;
  }
  .wiki-title { font-size:12px; color:#555; text-transform:uppercase; letter-spacing:.07em; margin-bottom:8px; }
  .wiki-text  { font-size:15px; color:#999; line-height:1.65; }
  .wiki-link  { font-size:13px; color:#4a7fa5; margin-top:8px; display:block; }

  /* ── режим камеры ── */
  .camera-card {
    background:#0d0e13; border:2px solid #c0392b; border-radius:20px;
    padding:36px 32px; text-align:center; margin-bottom:16px;
  }
  .cam-name    { font-size:42px; font-weight:800; color:#fff; line-height:1.1; margin-bottom:6px; }
  .cam-sub     { font-size:20px; color:#888; margin-bottom:28px; }
  .cam-scores  { display:flex; justify-content:center; gap:24px; margin-bottom:30px; }
  .cam-stat    { text-align:center; }
  .cam-num     { font-size:52px; font-weight:800; line-height:1; }
  .cam-num.g   { color:#2ecc71; }
  .cam-num.r   { color:#e74c3c; }
  .cam-num.w   { color:#f0f0f0; }
  .cam-slabel  { font-size:13px; color:#555; margin-top:4px; text-transform:uppercase; letter-spacing:.07em; }
  .cam-q       { background:#1c1e28; border:1px solid #2a2d3a; border-radius:12px; padding:18px 22px; margin-bottom:10px; text-align:left; }
  .cam-qnum    { font-size:13px; color:#c0392b; font-weight:700; margin-bottom:6px; }
  .cam-qtext   { font-size:20px; color:#e0e0e0; line-height:1.4; }

  /* ── Пантеон ── */
  .gold-table { width:100%; border-collapse:collapse; margin-bottom:20px; }
  .gold-table th { font-size:11px; color:#555; text-transform:uppercase; letter-spacing:.06em; text-align:left; padding:7px 12px; border-bottom:1px solid #2a2d3a; }
  .gold-table td { font-size:14px; color:#ccc; padding:10px 12px; border-bottom:1px solid #1a1c24; }
  .gold-table tr:hover td { background:#1c1e28; }
  .gold-num { font-weight:700; color:#f0d060; }

  /* ── сайдбар ── */
  section[data-testid="stSidebar"] { background-color:#17181f !important; border-right:1px solid #2a2d3a !important; }
  div[data-testid="stSidebar"] .stRadio label { color:#aaa; font-size:15px; }
  div[data-testid="stTextInput"] input { background:#1c1e28 !important; border:1px solid #2a2d3a !important; border-radius:10px !important; color:#e8e8e8 !important; font-size:15px !important; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# КОНСТАНТЫ
# =============================================================================
ROUND_MAP = {
    'FIN': (7,'Финал'), 'FNL': (7,'Финал'),
    'SFL': (6,'1/2'),   'QFL': (5,'1/4'),
    'R16': (4,'1/8'),   'R32': (3,'1/16'),
    'R64': (2,'1/32'),  'R128':(1,'1/64'),
}
FINALS_CODES = {'FIN','FNL'}

FLAG_EMOJIS = {
    "RUS":"🇷🇺","BLR":"🇧🇾","KAZ":"🇰🇿","UZB":"🇺🇿","KGZ":"🇰🇬","MGL":"🇲🇳",
    "GEO":"🇬🇪","ARM":"🇦🇲","AZE":"🇦🇿","TJK":"🇹🇯","TKM":"🇹🇲","AIN":"🏳️",
    "FRA":"🇫🇷","SRB":"🇷🇸","USA":"🇺🇸","UKR":"🇺🇦","BUL":"🇧🇬","CRO":"🇭🇷",
    "MKD":"🇲🇰","ROU":"🇷🇴","ITA":"🇮🇹","TUR":"🇹🇷","LAT":"🇱🇻","ISR":"🇮🇱",
    "GBR":"🇬🇧","GER":"🇩🇪","NED":"🇳🇱","GRE":"🇬🇷","LTU":"🇱🇹","MDA":"🇲🇩",
    "SVK":"🇸🇰","CZE":"🇨🇿","HUN":"🇭🇺","POL":"🇵🇱","SWE":"🇸🇪","FIN":"🇫🇮",
    "ESP":"🇪🇸","POR":"🇵🇹","JPN":"🇯🇵","KOR":"🇰🇷","CHN":"🇨🇳","MNG":"🇲🇳",
}

COUNTRY_NAMES_RU = {
    "RUS":"Россия","BLR":"Беларусь","KAZ":"Казахстан","UZB":"Узбекистан",
    "KGZ":"Кыргызстан","TKM":"Туркменистан","MGL":"Монголия","GEO":"Грузия",
    "ARM":"Армения","AZE":"Азербайджан","TJK":"Таджикистан","UKR":"Украина",
    "SRB":"Сербия","FRA":"Франция","AIN":"Нейтральный атлет","TUR":"Турция",
    "BUL":"Болгария","CRO":"Хорватия","GBR":"Великобритания","GER":"Германия",
    "NED":"Нидерланды","GRE":"Греция","LTU":"Литва","MDA":"Молдова",
    "LAT":"Латвия","ISR":"Израиль","ITA":"Италия","ROU":"Румыния",
}

TOURNAMENT_GROUPS = {
    "Чемпионат Мира":    ["World Sambo Championships","World SAMBO Championships"],
    "Кубок Мира":        ["Cup","President"],
    "Чемпионат Европы":  ["European Sambo Championships","European Championships"],
    "ЧМ Азии и Океании": ["Asia and Oceania Sambo Championships"],
}

DIVISIONS = {
    "Спортивное Самбо (М)":"SAMM","Спортивное Самбо (Ж)":"SAMW",
    "Боевое Самбо (М)":"CSMM",   "Боевое Самбо (Ж)":"CSMW",
}

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def format_time(val) -> str:
    try:
        s = str(val).strip()
        if ':' in s: return s
        ms = int(float(s))
        if ms == 0: return "—"
        ts = ms // 1000
        return f"{ts//60}:{ts%60:02d}"
    except: return "—"

def get_flag(code:str) -> str:
    return FLAG_EMOJIS.get(str(code).upper().strip(), "🌍")

def get_country(code:str) -> str:
    return COUNTRY_NAMES_RU.get(str(code).upper().strip(), str(code))

def get_cat(code:str) -> str:
    c = str(code).upper().strip()
    p = "Спорт" if "SAM" in c else ("Боевое" if "CSM" in c else "")
    g = "М" if ("SAMM" in c or "CSMM" in c) else ("Ж" if ("SAMW" in c or "CSMW" in c) else "")
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts)>1:
            w = (parts[1][:-1]+"+") if parts[1].endswith('O') else parts[1]
    return f"{p} {g} {w}кг".strip()

def clean_int(v, default:int=0) -> int:
    try: return int(float(v)) if pd.notna(v) else default
    except: return default

def get_initials(name:str) -> str:
    parts = name.strip().split()
    if len(parts)>=2: return (parts[0][0]+parts[-1][0]).upper()
    return name[:2].upper() if name else "??"

def fmt_dob(raw:str) -> str:
    try: return datetime.strptime(raw, "%Y-%m-%d").strftime("%d.%m.%Y")
    except: return raw

def calc_age(raw:str) -> str:
    try:
        dob = datetime.strptime(raw, "%Y-%m-%d")
        age = (datetime.now() - dob).days // 365
        return f"{age} лет"
    except: return ""

# =============================================================================
# WIKIPEDIA API
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_wikipedia(name:str) -> dict:
    """Ищет статью на ru.wikipedia, затем en.wikipedia. Возвращает {title, extract, url}."""
    for lang in ("ru","en"):
        try:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ','_')}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("type") == "standard":
                    return {
                        "title":   data.get("title",""),
                        "extract": data.get("extract","")[:600],
                        "url":     data.get("content_urls",{}).get("desktop",{}).get("page",""),
                    }
        except: pass
    return {}

# =============================================================================
# ГЕНЕРАТОР ВОПРОСОВ ДЛЯ ИНТЕРВЬЮ (локальный, без ИИ)
# =============================================================================

def generate_questions(name:str, country:str, age_str:str, wins:int, losses:int,
                       finals:int, total:int, recent_matches:list) -> list:
    """
    Генерирует 3 персонализированных вопроса на основе данных атлета.
    Использует шаблоны + реальные данные из CSV. Без интернета.
    """
    first_name = name.split()[0] if name else "Спортсмен"
    questions  = []

    # ── блок 1: про последний матч / текущий турнир ──────────────────────────
    if recent_matches:
        last = recent_matches[0]
        opp      = last.get("opp","соперника")
        result   = last.get("result","")
        tourney  = last.get("tourney","")
        round_l  = last.get("round","")
        score    = last.get("score","")
        opp_flag = last.get("opp_flag","")

        if result == "WIN":
            templates_1 = [
                f"{first_name}, только что победил {opp_flag} {opp} со счётом {score} — что почувствовал в момент победы?",
                f"Отличная победа над {opp_flag} {opp}! Что стало ключом к этому бою?",
                f"{first_name}, {score} в {round_l} — выглядело уверенно. Это план был такой или всё шло по ситуации?",
            ]
        else:
            templates_1 = [
                f"{first_name}, поражение от {opp_flag} {opp} — что пошло не так и как быстро приходишь в себя?",
                f"Бой с {opp_flag} {opp} завершился не в твою пользу. Что берёшь из него на будущее?",
                f"{first_name}, счёт {score} — был момент когда чувствовал что можешь переломить?",
            ]
        questions.append(random.choice(templates_1))

    # ── блок 2: про карьеру / статистику ─────────────────────────────────────
    winrate = round(wins / total * 100) if total > 0 else 0

    if finals >= 2:
        q2_pool = [
            f"У тебя уже {finals} финала в карьере — для тебя финал это кайф или стресс?",
            f"{finals} финала — это уже система. Что меняется в голове когда знаешь что снова в финале?",
            f"{first_name}, ты регулярно доходишь до финалов. В чём секрет стабильности?",
        ]
    elif winrate >= 70:
        q2_pool = [
            f"{winrate}% побед — это результат чего: таланта, работы или правильного тренера?",
            f"{first_name}, ты побеждаешь в {winrate}% боёв. Что делает тебя сложным соперником?",
            f"Такой процент побед — это серьёзно. Есть ли соперник которого ты реально опасаешься?",
        ]
    elif losses > wins:
        q2_pool = [
            f"{first_name}, сейчас больше поражений чем побед — что это за период и как работаешь над ошибками?",
            f"В самбо поражения — это тоже опыт. Какое твоё поражение дало больше всего?",
            f"{first_name}, через что сейчас проходишь как спортсмен?",
        ]
    else:
        q2_pool = [
            f"{first_name}, {wins} побед в карьере — какая самая памятная?",
            f"Что мотивирует тебя продолжать выступать на высшем уровне?",
            f"{first_name}, опиши свой обычный день на соревнованиях — от подъёма до ковра.",
        ]
    questions.append(random.choice(q2_pool))

    # ── блок 3: личное / про страну / соцсети ────────────────────────────────
    country_name = get_country(country)
    q3_pool = [
        f"Самбо в {country_name} — это популярный вид спорта или всё ещё приходится объяснять что это?",
        f"{first_name}, есть ли у тебя соцсети? Где тебя можно найти?",
        f"Что в самбо такого что ты выбрал именно его а не другой вид борьбы?",
        f"Есть спортсмен — кумир? На кого равняешься?",
        f"{first_name}, что посоветуешь тем кто только начинает заниматься самбо?",
        f"Самый тяжёлый момент в карьере — и как прошёл через него?",
        f"Ты выступаешь за {country_name} — что значит для тебя защищать цвета своей страны?",
    ]
    questions.append(random.choice(q3_pool))

    return questions

# =============================================================================
# РАБОТА С ИНТЕРВЬЮ (JSON-файл)
# =============================================================================

def load_interviews() -> dict:
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_interview(athlete_name:str, date:str, answers:list):
    data = load_interviews()
    key  = athlete_name.strip().upper()
    if key not in data:
        data[key] = []
    data[key].append({"date": date, "answers": answers})
    with open(INTERVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        for col in ['winner_athlete_id','red_id','blue_id']:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower()!='nan' else None
                )
        df['red_full_name']  = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
        df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
        df['date_start']     = pd.to_datetime(df['date_start'], errors='coerce')
        df['year']           = df['date_start'].dt.year
        df['round_rank']     = df['round_code'].apply(
            lambda x: ROUND_MAP.get(str(x).upper(),(0,str(x)))[0]
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

if BOT_TOKEN and TELEBOT_AVAILABLE and not st.session_state.bot_active:
    try:
        bot    = telebot.TeleBot(BOT_TOKEN, threaded=False)
        _df_bot = df  # явно захватываем df в замыкание — иначе поток его не видит

        @bot.message_handler(commands=['start'])
        def welcome(m):
            bot.reply_to(m,
                "🥋 FIGHTGURU\n\n"
                "Введите фамилию атлета (латиницей).\n"
                "Можно добавить имя через пробел: Kurzhev Ali"
            )

        @bot.message_handler(func=lambda m: True)
        def bot_search(m):
            raw   = m.text.strip()
            parts = raw.lower().split()
            if len(parts[0]) < 3:
                bot.reply_to(m, "Введите минимум 3 символа."); return
            if _df_bot is None:
                bot.reply_to(m, "База данных недоступна."); return

            # ищем по фамилии (первое слово), затем фильтруем по имени если дано
            last_q = parts[0]
            res = _df_bot[
                _df_bot['red_last_name'].str.lower().str.contains(last_q, na=False) |
                _df_bot['blue_last_name'].str.lower().str.contains(last_q, na=False)
            ].copy()

            if len(parts) >= 2:
                first_q = parts[1]
                res = res[
                    res['red_first_name'].str.lower().str.startswith(first_q, na=False) |
                    res['blue_first_name'].str.lower().str.startswith(first_q, na=False)
                ]

            if res.empty:
                bot.reply_to(m, f"Атлет не найден: {raw}"); return

            # определяем имя атлета
            row0   = res.iloc[0]
            if last_q in str(row0['red_last_name']).lower():
                name = str(row0['red_full_name'])
            else:
                name = str(row0['blue_full_name'])

            wins   = 0; losses = 0
            for _, r in res.iterrows():
                is_red = last_q in str(r['red_last_name']).lower()
                wid    = str(r.get('winner_athlete_id',''))
                mid    = str(r.get('red_id','') if is_red else r.get('blue_id',''))
                if wid == mid and wid: wins += 1
                else: losses += 1

            recent = res.sort_values('date_start', ascending=False).head(3)
            msg = (
                f"📊 {name.upper()}\n"
                f"Боёв: {wins+losses} | ✅ {wins} | ❌ {losses}\n\n"
                f"Последние матчи:\n"
            )
            for _, r in recent.iterrows():
                yr     = r['date_start'].year if pd.notna(r['date_start']) else "????"
                is_red = last_q in str(r['red_last_name']).lower()
                wid    = str(r.get('winner_athlete_id',''))
                mid    = str(r.get('red_id','') if is_red else r.get('blue_id',''))
                won    = (wid == mid and wid != '')
                my_sc  = clean_int(r.get('red_score') if is_red else r.get('blue_score'))
                op_sc  = clean_int(r.get('blue_score') if is_red else r.get('red_score'))
                opp    = str(r['blue_full_name'] if is_red else r['red_full_name'])
                res_e  = "✅" if won else "❌"
                msg += f"{res_e} {yr} | {my_sc}:{op_sc} vs {opp[:20]}\n"

            bot.send_message(m.chat.id, msg)

        def _run_bot():
            try:
                bot.infinity_polling(timeout=15, long_polling_timeout=10)
            except Exception as e:
                pass  # тихо перезапустится при следующем старте приложения

        threading.Thread(target=_run_bot, daemon=True).start()
        st.session_state.bot_active = True
    except Exception as e:
        pass

# =============================================================================
# SESSION STATE
# =============================================================================
for key, val in [
    ('search_query', ''), ('filter_mode', 'Все'),
    ('camera_mode', False), ('tab', 'matches'),
    ('questions', []), ('wiki_data', {}),
]:
    if key not in st.session_state:
        st.session_state[key] = val

# =============================================================================
# САЙДБАР
# =============================================================================
with st.sidebar:
    st.markdown("## 🥋 FightGuru")
    st.markdown("---")
    nav = st.radio("", ["👤 Досье", "🏛️ Пантеон"], label_visibility="collapsed")
    st.markdown("---")
    if nav == "👤 Досье":
        st.markdown("**Режим камеры**")
        cam_toggle = st.toggle("📹 Перед эфиром", value=st.session_state.camera_mode)
        if cam_toggle != st.session_state.camera_mode:
            st.session_state.camera_mode = cam_toggle
            st.rerun()
        if st.session_state.camera_mode:
            st.info("Крупный вид для съёмки")

# =============================================================================
# GUARD
# =============================================================================
if df is None:
    st.error(f"Файл '{DATABASE_FILE}' не найден.")
    st.stop()

# =============================================================================
# ═══════════════  РАЗДЕЛ: ДОСЬЕ  ═══════════════
# =============================================================================
if nav == "👤 Досье":

    search_input = st.text_input(
        "Поиск", value=st.session_state.search_query,
        placeholder="Фамилия атлета — напр. Karashtin",
        label_visibility="collapsed",
    )

    if not search_input:
        st.markdown(
            "<p style='color:#333; font-size:15px; margin-top:40px; text-align:center;'>"
            "Введите фамилию атлета</p>", unsafe_allow_html=True)
        st.stop()

    # Сбрасываем выбранного атлета если поисковый запрос изменился
    if st.session_state.get('last_search') != search_input:
        st.session_state.pop('selected_athlete', None)
        st.session_state['last_search'] = search_input

    search_low   = search_input.lower().strip()
    search_parts = search_low.split()

    # ── УМНЫЙ ПОИСК ──────────────────────────────────────────────────────────
    # Если введено два+ слова — ищем по фамилии И имени одновременно.
    # Это решает проблему братьев Куржевых: "kurzhev ali" найдёт только Ali,
    # а не обоих. Одно слово — ищем только по фамилии (точное совпадение).

    def row_matches_search(r, parts):
        """Возвращает (matched: bool, side: str | None)"""
        for side in ("red", "blue"):
            last  = str(r.get(f"{side}_last_name",  "")).lower().strip()
            first = str(r.get(f"{side}_first_name", "")).lower().strip()
            if len(parts) == 1:
                # одно слово → точное совпадение фамилии
                if parts[0] == last:
                    return True, side
            else:
                # два слова → первое = фамилия, второе = начало имени (или наоборот)
                # пробуем оба порядка: "kurzhev ali" и "ali kurzhev"
                comb1 = parts[0] == last and first.startswith(parts[1])
                comb2 = parts[1] == last and first.startswith(parts[0])
                if comb1 or comb2:
                    return True, side
        return False, None

    # Если точный поиск ничего не нашёл — fallback на contains по фамилии
    exact_rows = []
    for _, r in df.iterrows():
        matched, side = row_matches_search(r, search_parts)
        if matched:
            exact_rows.append((r.name, side))

    if exact_rows:
        match_idx = [x[0] for x in exact_rows]
        matches   = df.loc[match_idx].copy()
    else:
        # fallback: contains по фамилии (старое поведение)
        matches = df[
            df['red_last_name'].str.lower().str.contains(search_parts[0], na=False) |
            df['blue_last_name'].str.lower().str.contains(search_parts[0], na=False)
        ].copy()

    if matches.empty:
        st.info("Атлет не найден. Попробуйте ввести фамилию и имя через пробел.")
        st.stop()

    matches = matches.sort_values(['date_start','round_rank'], ascending=[False,False])

    # ── ОПРЕДЕЛЯЕМ УНИКАЛЬНЫХ АТЛЕТОВ в результатах ──────────────────────────
    # Собираем все уникальные полные имена которые нашлись
    found_athletes = {}  # full_name → {'id': athlete_id, 'country': code}
    for _, r in matches.iterrows():
        for side in ("red","blue"):
            last  = str(r.get(f"{side}_last_name","")).lower().strip()
            first = str(r.get(f"{side}_first_name","")).lower().strip()
            # проверяем что эта строка относится к нашему запросу
            if len(search_parts) == 1:
                relevant = search_parts[0] == last
            else:
                comb1 = search_parts[0] == last and first.startswith(search_parts[1])
                comb2 = search_parts[1] == last and first.startswith(search_parts[0])
                relevant = comb1 or comb2
                if not relevant and exact_rows:
                    relevant = False
                elif not relevant:
                    relevant = search_parts[0] in last  # fallback

            if relevant:
                full = str(r.get(f"{side}_full_name","")).strip()
                aid  = str(r.get(f"{side}_id",""))
                if full and full not in found_athletes:
                    found_athletes[full] = {
                        "id":      aid,
                        "country": str(r.get(f"{side}_nationality_code","")).upper(),
                    }

    # ── ЕСЛИ НАЙДЕНО НЕСКОЛЬКО АТЛЕТОВ — показываем выбор ───────────────────
    if len(found_athletes) > 1 and 'selected_athlete' not in st.session_state:
        st.markdown(
            "<p style='font-size:16px; color:#e8e8e8; margin-bottom:14px;'>"
            f"Найдено <b>{len(found_athletes)}</b> атлета с похожей фамилией. Выберите нужного:</p>",
            unsafe_allow_html=True,
        )
        for full_name, info in found_athletes.items():
            flag = get_flag(info["country"])
            cname = get_country(info["country"])
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"<div style='background:#1c1e28;border:1px solid #2a2d3a;border-radius:10px;"
                    f"padding:14px 18px;margin-bottom:8px;font-size:16px;color:#e8e8e8;'>"
                    f"{flag} <b>{full_name}</b> <span style='color:#555;font-size:13px;'>· {cname}</span></div>",
                    unsafe_allow_html=True,
                )
            with col_b:
                if st.button("Выбрать", key=f"sel_{full_name}"):
                    st.session_state.selected_athlete = full_name
                    st.rerun()
        st.stop()

    # Если атлет уже выбран или он один — фильтруем matches только под него
    if 'selected_athlete' in st.session_state:
        chosen_name = st.session_state.selected_athlete
        # Кнопка сброса выбора
        if st.button(f"← Назад к списку", key="back_sel"):
            del st.session_state['selected_athlete']
            st.rerun()
    elif len(found_athletes) == 1:
        chosen_name = list(found_athletes.keys())[0]
        st.session_state.selected_athlete = chosen_name
    else:
        chosen_name = None

    # Фильтруем matches: оставляем только строки где участвует chosen_name
    if chosen_name:
        chosen_low = chosen_name.lower().strip()
        def row_has_athlete(r):
            return (
                str(r.get('red_full_name','')).lower().strip()  == chosen_low or
                str(r.get('blue_full_name','')).lower().strip() == chosen_low
            )
        matches = matches[matches.apply(row_has_athlete, axis=1)].copy()

    if matches.empty:
        st.info("Не найдено матчей для выбранного атлета.")
        st.stop()

    # ── собираем данные атлета ────────────────────────────────────────────────
    dob_list, country_list, final_name = [], [], ""
    chosen_low = chosen_name.lower().strip() if chosen_name else search_low

    for _, r in matches.iterrows():
        for side in ("red","blue"):
            full = str(r.get(f"{side}_full_name","")).lower().strip()
            if full == chosen_low:
                final_name = str(r.get(f"{side}_full_name","")).strip()
                v = r.get(f"{side}_birth_date")
                if v and pd.notna(v): dob_list.append(str(v).strip())
                country_list.append(str(r.get(f"{side}_nationality_code","")).upper())
                break

    raw_dob         = max(set(dob_list), key=dob_list.count) if dob_list else ""
    athlete_dob     = fmt_dob(raw_dob)
    athlete_age     = calc_age(raw_dob)
    athlete_country = max(set(country_list), key=country_list.count) if country_list else ""

    # ── статистика ────────────────────────────────────────────────────────────
    wins = losses = finals = 0
    recent_for_questions = []

    for _, row in matches.iterrows():
        # Определяем сторону по точному совпадению полного имени
        is_red = str(row.get('red_full_name','')).lower().strip() == chosen_low
        win_id = str(row.get('winner_athlete_id',''))
        my_id  = str(row.get('red_id','') if is_red else row.get('blue_id',''))
        won    = (win_id == my_id and win_id != '')
        if won: wins += 1
        else:   losses += 1
        rc = str(row.get('round_code','')).upper()
        if rc in FINALS_CODES: finals += 1

        if len(recent_for_questions) < 3:
            opp_full = str(row['blue_full_name'] if is_red else row['red_full_name'])
            opp_code = row['blue_nationality_code'] if is_red else row['red_nationality_code']
            my_sc    = clean_int(row.get('red_score') if is_red else row.get('blue_score'))
            opp_sc   = clean_int(row.get('blue_score') if is_red else row.get('red_score'))
            recent_for_questions.append({
                "opp":      opp_full,
                "opp_flag": get_flag(opp_code),
                "result":   "WIN" if won else "LOSS",
                "score":    f"{my_sc}:{opp_sc}",
                "tourney":  str(row.get('tournament_name','')),
                "round":    ROUND_MAP.get(rc,(0,rc))[1],
            })

    total = wins + losses

    # ── категория (самая частая) ───────────────────────────────────────────────
    cat_counts = matches['category_code'].value_counts()
    main_cat   = get_cat(cat_counts.index[0]) if not cat_counts.empty else ""

    # ─────────────────────────────────────────────────────────────────────────
    # РЕЖИМ КАМЕРЫ
    # ─────────────────────────────────────────────────────────────────────────
    if st.session_state.camera_mode:

        if not st.session_state.questions:
            st.session_state.questions = generate_questions(
                final_name, athlete_country, athlete_age,
                wins, losses, finals, total, recent_for_questions
            )

        qs = st.session_state.questions
        flag    = get_flag(athlete_country)
        country = get_country(athlete_country)

        st.markdown(f"""
        <div class="camera-card">
          <div class="cam-name">{final_name}</div>
          <div class="cam-sub">{flag} {country} · {athlete_dob} · {athlete_age}</div>
          <div class="cam-scores">
            <div class="cam-stat"><div class="cam-num w">{total}</div><div class="cam-slabel">Боёв</div></div>
            <div class="cam-stat"><div class="cam-num g">{wins}</div><div class="cam-slabel">Победы</div></div>
            <div class="cam-stat"><div class="cam-num r">{losses}</div><div class="cam-slabel">Поражения</div></div>
            <div class="cam-stat"><div class="cam-num w">{finals}</div><div class="cam-slabel">Финалы</div></div>
          </div>
          {"".join(f'<div class="cam-q"><div class="cam-qnum">Вопрос {i+1}</div><div class="cam-qtext">{q}</div></div>' for i,q in enumerate(qs))}
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Новые вопросы", use_container_width=True):
                st.session_state.questions = generate_questions(
                    final_name, athlete_country, athlete_age,
                    wins, losses, finals, total, recent_for_questions
                )
                st.rerun()
        with col2:
            if st.button("✖ Выйти из режима камеры", use_container_width=True):
                st.session_state.camera_mode = False
                st.rerun()
        st.stop()

    # ─────────────────────────────────────────────────────────────────────────
    # ОБЫЧНЫЙ РЕЖИМ
    # ─────────────────────────────────────────────────────────────────────────

    # профиль
    initials = get_initials(final_name)
    flag     = get_flag(athlete_country)
    country  = get_country(athlete_country)

    meta_parts = [f"{flag} {country}"]
    if athlete_dob: meta_parts.append(f"Дата рождения: {athlete_dob}")
    if athlete_age: meta_parts.append(athlete_age)
    if main_cat:    meta_parts.append(main_cat)

    st.markdown(f"""
    <div class="profile-card">
      <div class="avatar">{initials}</div>
      <div>
        <div class="profile-name">{final_name}</div>
        <div class="profile-sub">{" &nbsp;·&nbsp; ".join(meta_parts)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # статы
    winrate = round(wins/total*100) if total else 0
    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card"><div class="stat-label">Всего боёв</div><div class="stat-val">{total}</div></div>
      <div class="stat-card"><div class="stat-label">Победы</div><div class="stat-val g">{wins}</div></div>
      <div class="stat-card"><div class="stat-label">Поражения</div><div class="stat-val r">{losses}</div></div>
      <div class="stat-card"><div class="stat-label">Процент побед</div><div class="stat-val">{winrate}%</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── вкладки ───────────────────────────────────────────────────────────────
    tab_matches, tab_interview, tab_wiki = st.tabs(["🥊 Матчи", "🎙 Интервью", "📖 Справка"])

    # ══════════════════════════════════════════
    # ВКЛАДКА: МАТЧИ
    # ══════════════════════════════════════════
    with tab_matches:

        # Фильтры — HTML-ссылки, не Streamlit-кнопки (те белые на тёмном фоне)
        fm_cur      = st.session_state.filter_mode
        filter_opts = ["Все", "Победы", "Поражения", "Финалы"]
        btns_html   = ""
        for opt in filter_opts:
            if opt == fm_cur:
                sty = "background:#c0392b;color:#fff;border-color:#c0392b;"
            else:
                sty = "background:#1c1e28;color:#999;border-color:#2a2d3a;"
            btns_html += (
                f'<a href="?filter={opt}" style="text-decoration:none;">' +
                f'<span style="display:inline-block;font-size:13px;font-weight:600;' +
                f'padding:8px 18px;border-radius:8px;border:1.5px solid;' +
                f'white-space:nowrap;{sty}">{opt}</span></a> '
            )
        st.markdown(
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">' +
            btns_html + '</div>',
            unsafe_allow_html=True,
        )
        qp = st.query_params.get("filter", fm_cur)
        if qp in filter_opts and qp != st.session_state.filter_mode:
            st.session_state.filter_mode = qp
            st.rerun()

        current_year = None
        for _, row in matches.iterrows():
            # Определяем сторону по точному совпадению полного имени
            is_red = str(row.get('red_full_name','')).lower().strip() == chosen_low
            win_id = str(row.get('winner_athlete_id',''))
            my_id  = str(row.get('red_id','') if is_red else row.get('blue_id',''))
            is_win = (win_id == my_id and win_id != '')

            fm = st.session_state.filter_mode
            rc = str(row.get('round_code','')).upper()
            if fm=="Победы"    and not is_win: continue
            if fm=="Поражения" and is_win:     continue
            if fm=="Финалы"    and rc not in FINALS_CODES: continue

            my_sc   = clean_int(row.get('red_score')  if is_red else row.get('blue_score'))
            opp_sc  = clean_int(row.get('blue_score') if is_red else row.get('red_score'))
            my_pen  = clean_int(row.get('red_penalties')  if is_red else row.get('blue_penalties'))
            opp_pen = clean_int(row.get('blue_penalties') if is_red else row.get('red_penalties'))

            opp_full    = str(row['blue_full_name'] if is_red else row['red_full_name'])
            opp_last    = str(row['blue_last_name'] if is_red else row['red_last_name'])
            opp_country = row['blue_nationality_code'] if is_red else row['red_nationality_code']

            round_label = ROUND_MAP.get(rc,(0,rc))[1]
            cat_label   = get_cat(row.get('category_code',''))
            date_str    = row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??'
            year        = row.get('year')
            time_str    = format_time(row.get('fight_time',0))
            res_cls     = "win" if is_win else "loss"
            res_lbl     = "WIN" if is_win else "LOSS"

            if pd.notna(year) and int(year) != current_year:
                current_year = int(year)
                st.markdown(f'<div class="year-sep">{current_year}</div>', unsafe_allow_html=True)

            tags = f'<span class="tag rnd">{round_label}</span>'
            tags += f'<span class="tag">{cat_label}</span>'
            if my_pen > 0 or opp_pen > 0:
                tags += f'<span class="tag pen">Пред. {my_pen} / {opp_pen}</span>'

            st.markdown(f"""
            <div class="match-card {res_cls}">
              <div class="badge {res_cls}">
                <span class="bscore {res_cls}">{my_sc}:{opp_sc}</span>
                <span class="blabel {res_cls}">{res_lbl}</span>
              </div>
              <div style="min-width:0">
                <div class="m-tourney">{str(row.get('tournament_name',''))}</div>
                <div class="m-opponent"><span style="font-size:17px">{get_flag(opp_country)}</span>{opp_full}</div>
                <div class="m-tags">{tags}</div>
              </div>
              <div class="m-right">
                <div class="m-date">{date_str}</div>
                <div class="m-time">⏱ {time_str}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"→ Досье: {opp_full}", key=f"opp_{row.name}"):
                st.session_state.search_query = opp_last
                st.session_state.filter_mode  = "Все"
                st.rerun()

    # ══════════════════════════════════════════
    # ВКЛАДКА: ИНТЕРВЬЮ
    # ══════════════════════════════════════════
    with tab_interview:

        st.markdown(f"#### 🎙 Блиц-интервью — {final_name}")
        st.caption("Вопросы сгенерированы автоматически на основе карьерных данных атлета")

        # генерируем вопросы если нет или атлет поменялся
        cache_key = f"q_{final_name}"
        if cache_key not in st.session_state or not st.session_state[cache_key]:
            st.session_state[cache_key] = generate_questions(
                final_name, athlete_country, athlete_age,
                wins, losses, finals, total, recent_for_questions
            )

        questions = st.session_state[cache_key]

        # отображаем вопросы
        for i, q in enumerate(questions):
            st.markdown(f"""
            <div class="q-card">
              <div class="q-num">{i+1}</div>
              <div class="q-text">{q}</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 Сгенерировать другие вопросы", key="regen_q"):
            st.session_state[cache_key] = generate_questions(
                final_name, athlete_country, athlete_age,
                wins, losses, finals, total, recent_for_questions
            )
            st.rerun()

        st.markdown("---")
        st.markdown("#### 💾 Записать ответы")
        st.caption("Сохранится в interviews.json рядом с приложением")

        answers = []
        for i, q in enumerate(questions):
            ans = st.text_area(f"Ответ на вопрос {i+1}", key=f"ans_{i}",
                               placeholder="Запишите ответ...", height=80)
            answers.append({"question": q, "answer": ans})

        if st.button("💾 Сохранить интервью", type="primary"):
            filled = [a for a in answers if a["answer"].strip()]
            if filled:
                today = datetime.now().strftime("%d.%m.%Y %H:%M")
                save_interview(final_name, today, answers)
                st.success(f"✅ Интервью сохранено — {today}")
            else:
                st.warning("Заполните хотя бы один ответ.")

        # прошлые интервью с этим атлетом
        all_ivw = load_interviews()
        past    = all_ivw.get(final_name.strip().upper(), [])
        if past:
            st.markdown("---")
            st.markdown(f"#### 📂 Прошлые интервью с {final_name}")
            for ivw in reversed(past):
                with st.expander(f"🗓 {ivw['date']}"):
                    for item in ivw['answers']:
                        if item.get('answer','').strip():
                            st.markdown(f"**В:** {item['question']}")
                            st.markdown(f"**О:** {item['answer']}")
                            st.markdown("---")

    # ══════════════════════════════════════════
    # ВКЛАДКА: СПРАВКА (WIKIPEDIA)
    # ══════════════════════════════════════════
    with tab_wiki:

        st.markdown(f"#### 📖 Справка — {final_name}")

        # пробуем несколько вариантов имени
        name_variants = [
            final_name,
            " ".join(reversed(final_name.split())),   # Фамилия Имя → Имя Фамилия
        ]

        wiki = {}
        for variant in name_variants:
            wiki = fetch_wikipedia(variant)
            if wiki: break

        if wiki:
            st.markdown(f"""
            <div class="wiki-box">
              <div class="wiki-title">Wikipedia — {wiki['title']}</div>
              <div class="wiki-text">{wiki['extract']}</div>
              {"<a class='wiki-link' href='" + wiki['url'] + "' target='_blank'>→ Читать полностью на Wikipedia</a>" if wiki.get('url') else ""}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="wiki-box">
              <div class="wiki-title">Wikipedia</div>
              <div class="wiki-text" style="color:#555;">
                Статья о <b style="color:#888">{final_name}</b> на Wikipedia не найдена.<br><br>
                Возможно, спортсмен ещё не имеет собственной страницы.
              </div>
            </div>
            """, unsafe_allow_html=True)

        # дополнительные ссылки для поиска
        name_enc = final_name.replace(' ', '+')
        st.markdown(f"""
        <div style="margin-top:12px; display:flex; gap:12px; flex-wrap:wrap;">
          <a href="https://www.google.com/search?q={name_enc}+самбо" target="_blank"
             style="font-size:14px; color:#4a7fa5; text-decoration:none;">
            🔍 Google
          </a>
          <a href="https://ru.wikipedia.org/w/index.php?search={name_enc}" target="_blank"
             style="font-size:14px; color:#4a7fa5; text-decoration:none;">
            📖 Wikipedia поиск
          </a>
          <a href="https://www.youtube.com/results?search_query={name_enc}+sambo" target="_blank"
             style="font-size:14px; color:#4a7fa5; text-decoration:none;">
            ▶ YouTube
          </a>
          <a href="https://www.instagram.com/explore/tags/{final_name.replace(' ','').lower()}/" target="_blank"
             style="font-size:14px; color:#4a7fa5; text-decoration:none;">
            📷 Instagram
          </a>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# ═══════════════  РАЗДЕЛ: ПАНТЕОН  ═══════════════
# =============================================================================
elif nav == "🏛️ Пантеон":

    st.markdown('<p style="font-size:26px; font-weight:700; color:#f0f0f0; margin-bottom:20px;">🏛️ Исторический Пантеон</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1: t_sel   = st.selectbox("Турнир",   list(TOURNAMENT_GROUPS.keys()))
    with col2: div_sel = st.selectbox("Дивизион", list(DIVISIONS.keys()))

    pattern = '|'.join(TOURNAMENT_GROUPS[t_sel])
    f_data  = df[
        df['tournament_name'].str.contains(pattern, case=False, na=False) &
        df['category_code'].str.contains(DIVISIONS[div_sel], case=False, na=False)
    ]
    fin_matches = f_data[f_data['round_code'].str.upper().str.contains('FNL|FIN', na=False)].copy()

    if fin_matches.empty:
        st.warning("Нет данных по выбранным фильтрам.")
        st.stop()

    def get_winner(r):
        if str(r['winner_athlete_id']) == str(r['red_id']):
            return r['red_full_name'], str(r['red_nationality_code']).upper()
        return r['blue_full_name'], str(r['blue_nationality_code']).upper()

    fin_matches[['w_name','w_country']] = fin_matches.apply(lambda r: pd.Series(get_winner(r)), axis=1)

    st.markdown("**Зачёт по странам — золото**")
    stats = fin_matches.groupby('w_country').size().reset_index(name='gold').sort_values('gold', ascending=False)
    rows_html = "".join(
        f"<tr><td>{get_flag(r['w_country'])} {get_country(r['w_country'])}</td><td class='gold-num'>{r['gold']}</td></tr>"
        for _, r in stats.iterrows()
    )
    st.markdown(f"""
    <table class="gold-table">
      <thead><tr><th>Страна</th><th>Золото</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

    st.markdown("**Победители по весовым категориям**")
    for cat in sorted(fin_matches['category_code'].unique()):
        cat_df = fin_matches[fin_matches['category_code']==cat].sort_values('date_start', ascending=False)
        with st.expander(get_cat(cat)):
            for _, cr in cat_df.iterrows():
                yr  = int(cr['date_start'].year) if pd.notna(cr['date_start']) else "????"
                f   = get_flag(cr['w_country'])
                st.markdown(f"**{yr}** &nbsp; {f} {cr['w_name']}", unsafe_allow_html=True)

# =============================================================================
# ПОДВАЛ
# =============================================================================
st.markdown(
    "<hr style='border-color:#1e2029; margin-top:40px;'>"
    "<p style='text-align:center; color:#2a2d3a; font-size:12px;'>FIGHTGURU · Мир самбо</p>",
    unsafe_allow_html=True,
)

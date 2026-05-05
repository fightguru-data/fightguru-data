"""
FIGHTGURU v5
Исправления:
  - Фильтры: st.session_state хранит и запрос и фильтр, rerun не сбрасывает поле
  - Бот: запускается через multiprocessing.Process (не Thread), переживает rerun
  - Walrus: убран, поиск переписан чисто
  - Флаги: полный список + название страны везде
  - Дизайн: 2026, glassmorphism, streak, win-rate ring
"""

import streamlit as st
import pandas as pd
import os, json, random, requests, time
from datetime import datetime
from multiprocessing import Process

try:
    import telebot
    TELEBOT_OK = True
except ImportError:
    TELEBOT_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────────────────────────────────────
DB_FILE         = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AllTournament.csv")
BOT_LOG_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot_pid")
INTERVIEWS_FILE = "interviews.json"

try:
    BOT_TOKEN = st.secrets["telegram"]["bot_token"]
except Exception:
    BOT_TOKEN = ""

st.set_page_config(page_title="FightGuru", page_icon="🥋", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;0,14..32,900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.stApp {
  background: #0c0d12 !important;
  color: #dde0ef;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.main .block-container {
  padding: 1.2rem 1.4rem 3rem !important;
  max-width: 880px !important;
}

/* поиск */
div[data-testid="stTextInput"] input {
  background: #161720 !important;
  border: 1px solid #272a3a !important;
  border-radius: 14px !important;
  color: #dde0ef !important;
  font-size: 16px !important;
  padding: 12px 18px !important;
  font-family: inherit !important;
}

/* сайдбар */
section[data-testid="stSidebar"] {
  background: #09090e !important;
  border-right: 1px solid #1a1c28 !important;
}
section[data-testid="stSidebar"] label { color: #9093ab !important; font-size: 15px !important; }

/* скрываем стандартные кнопки фильтров — показываем только наш HTML overlay */
div[data-testid="stHorizontalBlock"] .stButton button {
  opacity: 0 !important;
  position: absolute !important;
  width: 100% !important; height: 100% !important;
  top: 0; left: 0;
  cursor: pointer !important;
  z-index: 10;
}

/* ── профиль ── */
.profile-wrap {
  background: linear-gradient(140deg,#171924 0%,#111318 100%);
  border: 1px solid #272a3a;
  border-radius: 22px;
  padding: 24px;
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  position: relative;
  overflow: hidden;
}
.profile-wrap::after {
  content: '';
  position: absolute; top: -80px; right: -80px;
  width: 220px; height: 220px;
  background: radial-gradient(circle, rgba(192,57,43,.12) 0%, transparent 70%);
  pointer-events: none;
}
.avatar {
  width: 66px; height: 66px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(145deg,#c0392b,#7b1717);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 900; color: #fff;
  box-shadow: 0 6px 24px rgba(192,57,43,.35);
  letter-spacing: -1px;
}
.p-name { font-size: 24px; font-weight: 800; color: #f0f4ff; line-height: 1.15; }
.p-sub  { font-size: 14px; color: #8890b0; margin-top: 6px; line-height: 1.7; }
.p-country {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 15px; color: #9da4c0; margin-top: 6px;
  font-weight: 500;
}
.streak-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 700;
  padding: 4px 12px; border-radius: 20px;
  margin-top: 10px;
}
.sp-win  { background: #071a0f; color: #2ecc71; border: 1px solid #1a4a2a; }
.sp-loss { background: #1a0707; color: #e74c3c; border: 1px solid #4a1515; }

/* ── стат-карточки ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.sc {
  background: #161720;
  border: 1px solid #272a3a;
  border-radius: 16px;
  padding: 16px 14px;
}
.sc-l { font-size: 11px; color: #666a88; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 7px; }
.sc-v { font-size: 30px; font-weight: 900; line-height: 1; color: #edf0ff; }
.sc-v.g { color: #2ecc71; }
.sc-v.r { color: #e74c3c; }
.sc-v.y { color: #f1c40f; }

/* ── фильтр-чипы ── */
.filter-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; position: relative; }
.f-chip {
  font-size: 14px; font-weight: 700;
  padding: 8px 20px; border-radius: 10px;
  border: 1.5px solid #30334a;
  background: #1e2035; color: #7880a8;
  cursor: pointer; white-space: nowrap;
  user-select: none;
  position: relative;
  transition: color .15s, border-color .15s, background .15s;
}
.f-chip.on { background: #c0392b; color: #fff; border-color: #c0392b; }
.f-chip:hover:not(.on) { border-color: #505470; color: #a0a4c0; }

/* ── год ── */
.yr-sep {
  font-size: 12px; font-weight: 800; color: #52566e;
  text-transform: uppercase; letter-spacing: .14em;
  padding: 18px 0 10px;
  border-bottom: 1px solid #1a1c28;
  margin-bottom: 10px;
}

/* ── матч ── */
.mc {
  background: #161720;
  border: 1px solid #272a3a;
  border-radius: 16px;
  padding: 15px 16px;
  margin-bottom: 8px;
  display: grid;
  grid-template-columns: 60px 1fr auto;
  gap: 0 14px;
  align-items: center;
  border-left: 3px solid #272a3a;
}
.mc:hover { background: #1a1c2a; border-color: #35384d; }
.mc.win  { border-left-color: #2ecc71; }
.mc.loss { border-left-color: #e74c3c; }

.badge {
  width: 54px; height: 54px; border-radius: 13px; flex-shrink: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 2px;
}
.badge.win  { background: #071a0f; }
.badge.loss { background: #1a0707; }
.bs { font-size: 18px; font-weight: 900; line-height: 1; }
.bs.win  { color: #2ecc71; }
.bs.loss { color: #e74c3c; }
.bl { font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.bl.win  { color: #1a7a40; }
.bl.loss { color: #7a1a1a; }

.m-tour { font-size: 12px; color: #606480; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-opp  {
  font-size: 16px; font-weight: 700; color: #e8ecff;
  display: flex; align-items: center; gap: 7px; margin-bottom: 5px; flex-wrap: wrap;
}
.m-cnt  { font-size: 12px; color: #7880a0; font-weight: 500; }
.m-tags { display: flex; gap: 5px; flex-wrap: wrap; }
.tag { font-size: 11px; padding: 3px 10px; border-radius: 20px; background: #1e2135; color: #6870a0; border: 1px solid #272a3a; }
.tag.rnd { background: #1a0707; color: #c0392b; border-color: #3d1515; }
.tag.pen { background: #1a1500; color: #b8860b; border-color: #3d3000; }

.m-right { text-align: right; flex-shrink: 0; min-width: 68px; }
.m-date { font-size: 12px; color: #606480; margin-bottom: 5px; }
.m-time { font-size: 12px; color: #505468; }

/* ── досье соперника ── */
.opp-link-btn {
  width: 100%; text-align: left;
  font-size: 14px; color: #6090b8;
  background: #111318; border: 1px solid #1e2130;
  border-radius: 0 0 14px 14px;
  padding: 8px 16px; margin-bottom: 14px;
  cursor: pointer;
}
.opp-link-btn:hover { color: #5a90b8; border-color: #2a3a4d; }

/* ── интервью ── */
.q-card {
  background: #161720; border: 1px solid #272a3a;
  border-radius: 16px; padding: 18px 20px; margin-bottom: 10px;
  display: flex; gap: 16px; align-items: flex-start;
}
.q-num {
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  background: #1a0707; border: 1px solid #4a1515;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 900; color: #c0392b;
}
.q-text { font-size: 17px; color: #ced2e8; line-height: 1.6; }

/* ── wiki ── */
.wiki-box {
  background: #161720; border: 1px solid #272a3a;
  border-radius: 16px; padding: 20px 22px; margin-bottom: 14px;
}
.wiki-lbl  { font-size: 11px; color: #606480; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 10px; }
.wiki-text { font-size: 15px; color: #9095b5; line-height: 1.75; }
.wiki-link { font-size: 13px; color: #4472a0; margin-top: 12px; display: block; }

.ref-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.ref-a {
  font-size: 14px; color: #7090b8;
  background: #161720; border: 1px solid #272a3a;
  border-radius: 10px; padding: 8px 16px;
  text-decoration: none;
}
.ref-a:hover { border-color: #404360; color: #7a90ab; }

/* ── камера ── */
.cam-wrap {
  background: #09090e;
  border: 2px solid #c0392b;
  border-radius: 24px;
  padding: 36px 28px;
  text-align: center;
  margin-bottom: 18px;
  box-shadow: 0 0 60px rgba(192,57,43,.15);
}
.cam-name { font-size: 38px; font-weight: 900; color: #fff; line-height: 1.1; margin-bottom: 6px; }
.cam-sub  { font-size: 16px; color: #8890b0; margin-bottom: 28px; }
.cam-stats { display: flex; justify-content: center; gap: 20px; margin-bottom: 28px; flex-wrap: wrap; }
.cam-s  { text-align: center; min-width: 65px; }
.cam-n  { font-size: 48px; font-weight: 900; line-height: 1; }
.cam-n.g { color: #2ecc71; }
.cam-n.r { color: #e74c3c; }
.cam-n.w { color: #edf0ff; }
.cam-n.y { color: #f1c40f; }
.cam-sl { font-size: 12px; color: #606480; text-transform: uppercase; letter-spacing:.08em; margin-top:4px; }
.cam-q  { background: #161720; border: 1px solid #272a3a; border-radius: 14px; padding: 18px 22px; margin-bottom: 10px; text-align: left; }
.cam-qn { font-size: 12px; color: #e05040; font-weight: 800; margin-bottom: 7px; text-transform: uppercase; letter-spacing:.08em; }
.cam-qt { font-size: 20px; color: #e8ecff; line-height: 1.5; }

/* ── пантеон ── */
.gold-t { width: 100%; border-collapse: collapse; }
.gold-t th { font-size: 10px; color: #2a2d3d; text-transform: uppercase; letter-spacing:.1em; padding: 8px 14px; border-bottom: 1px solid #272a3a; text-align: left; }
.gold-t td { font-size: 15px; color: #b0b4d0; padding: 11px 14px; border-bottom: 1px solid #111318; }
.gold-t tr:hover td { background: #161720; }
.gold-n { font-weight: 900; color: #f1c40f; }

/* скрываем служебное */
#MainMenu, footer { visibility: hidden; }
div[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# СПРАВОЧНИКИ
# ─────────────────────────────────────────────────────────────────────────────
ROUND_MAP = {
    'FIN':(7,'Финал'),    'FNL':(7,'Финал'),
    'SFL':(6,'1/2'),      'QFL':(5,'1/4'),
    'R16':(4,'1/8'),      'R32':(3,'1/16'),
    'R64':(2,'1/32'),     'R128':(1,'1/64'),
    'BR1':(1,'Бронза'),   'BR2':(1,'Бронза'),
    'RP1':(1,'Утешит.'),  'RP2':(1,'Утешит.'),
}
FINALS_CODES = {'FIN','FNL'}

FLAGS = {
    "RUS":"🇷🇺","BLR":"🇧🇾","KAZ":"🇰🇿","UZB":"🇺🇿","KGZ":"🇰🇬","MGL":"🇲🇳",
    "GEO":"🇬🇪","ARM":"🇦🇲","AZE":"🇦🇿","TJK":"🇹🇯","TKM":"🇹🇲","AIN":"🏳️",
    "FRA":"🇫🇷","SRB":"🇷🇸","USA":"🇺🇸","UKR":"🇺🇦","BUL":"🇧🇬","CRO":"🇭🇷",
    "MKD":"🇲🇰","ROU":"🇷🇴","ITA":"🇮🇹","TUR":"🇹🇷","LAT":"🇱🇻","ISR":"🇮🇱",
    "GBR":"🇬🇧","GER":"🇩🇪","NED":"🇳🇱","GRE":"🇬🇷","LTU":"🇱🇹","MDA":"🇲🇩",
    "SVK":"🇸🇰","CZE":"🇨🇿","HUN":"🇭🇺","POL":"🇵🇱","SWE":"🇸🇪","ESP":"🇪🇸",
    "POR":"🇵🇹","JPN":"🇯🇵","KOR":"🇰🇷","CHN":"🇨🇳","BEL":"🇧🇪","AUT":"🇦🇹",
    "SUI":"🇨🇭","NOR":"🇳🇴","DEN":"🇩🇰","FIN":"🇫🇮","EST":"🇪🇪","LVA":"🇱🇻",
    "IRN":"🇮🇷","IND":"🇮🇳","MAS":"🇲🇾","THA":"🇹🇭","PHI":"🇵🇭","BRA":"🇧🇷",
    "ARG":"🇦🇷","MEX":"🇲🇽","CAN":"🇨🇦","AUS":"🇦🇺","MAR":"🇲🇦","EGY":"🇪🇬",
    "ALB":"🇦🇱","BIH":"🇧🇦","MNE":"🇲🇪","KOS":"🇽🇰","SLO":"🇸🇮","CYP":"🇨🇾",
    "MON":"🇲🇨","AND":"🇦🇩","ISL":"🇮🇸","IRL":"🇮🇪","RSA":"🇿🇦","KEN":"🇰🇪",
    "ETH":"🇪🇹","SEN":"🇸🇳","NGR":"🇳🇬","CMR":"🇨🇲","KWT":"🇰🇼","VIE":"🇻🇳",
    "COL":"🇨🇴","VEN":"🇻🇪","NZL":"🇳🇿","PAK":"🇵🇰","AFG":"🇦🇫","TUN":"🇹🇳",
    "ALG":"🇩🇿","SGP":"🇸🇬","HKG":"🇭🇰","TPE":"🇹🇼","LUX":"🇱🇺","MLT":"🇲🇹",
}

COUNTRIES = {
    "RUS":"Россия",         "BLR":"Беларусь",       "KAZ":"Казахстан",
    "UZB":"Узбекистан",     "KGZ":"Кыргызстан",     "TKM":"Туркменистан",
    "MGL":"Монголия",       "GEO":"Грузия",          "ARM":"Армения",
    "AZE":"Азербайджан",    "TJK":"Таджикистан",     "UKR":"Украина",
    "SRB":"Сербия",         "FRA":"Франция",          "AIN":"Нейтр. атлет",
    "TUR":"Турция",         "BUL":"Болгария",         "CRO":"Хорватия",
    "GBR":"Великобр.",      "GER":"Германия",         "NED":"Нидерланды",
    "GRE":"Греция",         "LTU":"Литва",            "MDA":"Молдова",
    "LAT":"Латвия",         "ISR":"Израиль",          "ITA":"Италия",
    "ROU":"Румыния",        "SVK":"Словакия",         "CZE":"Чехия",
    "HUN":"Венгрия",        "POL":"Польша",           "SWE":"Швеция",
    "ESP":"Испания",        "POR":"Португалия",       "JPN":"Япония",
    "KOR":"Корея",          "CHN":"Китай",            "MKD":"Сев. Македония",
    "BEL":"Бельгия",        "AUT":"Австрия",          "SUI":"Швейцария",
    "NOR":"Норвегия",       "DEN":"Дания",            "FIN":"Финляндия",
    "EST":"Эстония",        "IRN":"Иран",             "IND":"Индия",
    "MAS":"Малайзия",       "THA":"Таиланд",          "BRA":"Бразилия",
    "ARG":"Аргентина",      "MEX":"Мексика",          "CAN":"Канада",
    "AUS":"Австралия",      "MAR":"Марокко",          "EGY":"Египет",
    "ALB":"Албания",        "BIH":"Босния",           "MNE":"Черногория",
    "KOS":"Косово",         "SLO":"Словения",         "ISL":"Исландия",
    "IRL":"Ирландия",       "RSA":"ЮАР",              "KEN":"Кения",
    "SEN":"Сенегал",        "NGR":"Нигерия",          "KWT":"Кувейт",
    "VIE":"Вьетнам",        "COL":"Колумбия",         "VEN":"Венесуэла",
    "NZL":"Новая Зел.",     "PAK":"Пакистан",         "TUN":"Тунис",
    "ALG":"Алжир",          "PHI":"Филиппины",        "CYP":"Кипр",
    "MON":"Монако",         "LUX":"Люксембург",       "USA":"США",
}

TOUR_GROUPS = {
    "Чемпионат Мира":    ["World Sambo Championships","World SAMBO Championships"],
    "Кубок Мира":        ["Cup","President"],
    "Чемпионат Европы":  ["European Sambo Championships","European Championships"],
    "ЧМ Азии и Океании": ["Asia and Oceania Sambo Championships"],
}
DIVISIONS = {
    "Спортивное Самбо (М)":"SAMM","Спортивное Самбо (Ж)":"SAMW",
    "Боевое Самбо (М)":"CSMM",   "Боевое Самбо (Ж)":"CSMW",
}

# ─────────────────────────────────────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────────────────────────────────────
def fl(code):
    return FLAGS.get(str(code).upper().strip(), "🌍")

def cn(code):
    c = str(code).upper().strip()
    return COUNTRIES.get(c, c)

def fl_cn(code):
    return f"{fl(code)} {cn(code)}"

def fmt_time(v):
    try:
        s = str(v).strip()
        if ':' in s: return s
        ms = int(float(s))
        if ms == 0: return "—"
        ts = ms // 1000
        return f"{ts//60}:{ts%60:02d}"
    except: return "—"

def get_cat(code):
    c = str(code).upper().strip()
    if "CSM" in c:   p = "Боевое"
    elif "SAM" in c: p = "Спорт"
    else:            p = ""
    if "SAMM" in c or "CSMM" in c:   g = "М"
    elif "SAMW" in c or "CSMW" in c: g = "Ж"
    else:                             g = ""
    w = ""
    if "ADT" in c:
        parts = c.split("ADT")
        if len(parts) > 1:
            w = (parts[1][:-1] + "+") if parts[1].endswith('O') else parts[1]
    return f"{p} {g} {w}кг".strip()

def ci(v, d=0):
    try: return int(float(v)) if pd.notna(v) else d
    except: return d

def inits(name):
    p = name.strip().split()
    if len(p) >= 2: return (p[0][0] + p[-1][0]).upper()
    return name[:2].upper() if name else "?"

def fmt_dob(raw):
    try: return datetime.strptime(raw, "%Y-%m-%d").strftime("%d.%m.%Y")
    except: return raw

def calc_age(raw):
    try:
        dob = datetime.strptime(raw, "%Y-%m-%d")
        return f"{(datetime.now()-dob).days//365} лет"
    except: return ""

# ─────────────────────────────────────────────────────────────────────────────
# WIKIPEDIA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def wiki_get(name):
    for lang in ("ru", "en"):
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ','_')}",
                timeout=6, headers={"User-Agent": "FightGuru/5.0"}
            )
            if r.status_code == 200:
                d = r.json()
                if d.get("type") == "standard":
                    return {
                        "title":   d.get("title", ""),
                        "extract": d.get("extract", "")[:700],
                        "url":     d.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "lang":    lang,
                    }
        except: pass
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# ВОПРОСЫ
# ─────────────────────────────────────────────────────────────────────────────
def gen_q(name, acnt, age, wins, losses, finals, total, recent):
    fn    = name.split()[0] if name else "Спортсмен"
    cname = cn(acnt)
    wr    = round(wins/total*100) if total else 0
    qs    = []

    # Q1 — последний бой
    if recent:
        m   = recent[0]
        opp = m["opp"]; res = m["res"]; sc = m["sc"]; rnd = m["rnd"]; ofl = m["ofl"]
        if res == "W":
            pool = [
                f"{fn}, только что победил {ofl} {opp} со счётом {sc} — что почувствовал?",
                f"Победа над {ofl} {opp}, {sc}. Это тактика или кураж?",
                f"{fn}, {sc} в {rnd} — всё шло по плану или импровизировал?",
            ]
        else:
            pool = [
                f"{fn}, поражение от {ofl} {opp} — что пошло не так?",
                f"Бой с {ofl} {opp} не в твою пользу. Что берёшь из него?",
                f"Счёт {sc} — был момент когда чувствовал что можешь переломить?",
            ]
        qs.append(random.choice(pool))

    # Q2 — карьера
    if finals >= 2:
        pool2 = [
            f"У тебя {finals} финала — финал для тебя кайф или стресс?",
            f"{fn}, ты снова в финале. Что меняется в голове?",
            f"Регулярно доходишь до финалов. В чём секрет стабильности?",
        ]
    elif wr >= 75:
        pool2 = [
            f"{wr}% побед — это талант, труд или тренер?",
            f"Что делает тебя сложным соперником на ковре?",
            f"Такой процент побед — есть соперник которого реально опасаешься?",
        ]
    elif losses > wins:
        pool2 = [
            f"Сложный период в карьере? Как работаешь над ошибками?",
            f"Какое поражение дало тебе больше всего как спортсмену?",
            f"{fn}, через что сейчас проходишь в карьере?",
        ]
    else:
        pool2 = [
            f"{fn}, {wins} побед — какая самая памятная?",
            f"Что мотивирует продолжать выступать на таком уровне?",
            f"Опиши свой день на соревнованиях — от подъёма до ковра.",
        ]
    qs.append(random.choice(pool2))

    # Q3 — личное
    pool3 = [
        f"Самбо в {cname} — популярный спорт или приходится объяснять?",
        f"{fn}, есть соцсети? Где тебя найти?",
        f"Почему самбо а не другая борьба?",
        f"Есть спортсмен-кумир? На кого равняешься?",
        f"{fn}, что посоветуешь тем кто только начинает самбо?",
        f"Самый тяжёлый момент в карьере — и как прошёл через него?",
        f"Что значит защищать цвета {cname}?",
        f"{fn}, следующая большая цель?",
    ]
    qs.append(random.choice(pool3))
    return qs

# ─────────────────────────────────────────────────────────────────────────────
# ИНТЕРВЬЮ (JSON)
# ─────────────────────────────────────────────────────────────────────────────
def load_ivw():
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_ivw(name, date, answers):
    d = load_ivw()
    k = name.strip().upper()
    if k not in d: d[k] = []
    d[k].append({"date": date, "answers": answers})
    with open(INTERVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DB_FILE): return None
    try:
        df = pd.read_csv(DB_FILE, low_memory=False)
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
        st.error(f"Ошибка загрузки: {e}"); return None

df = load_data()

# ─────────────────────────────────────────────────────────────────────────────
# ТЕЛЕГРАМ-БОТ
# Используем Process вместо Thread — переживает st.rerun()
# Запускается ровно один раз через файл-флаг
# ─────────────────────────────────────────────────────────────────────────────
# BOT_LOG_FILE moved to top

def _bot_worker(token, db_path):
    """Запускается в отдельном процессе. Читает CSV сам."""
    import telebot, pandas as pd, time
    from datetime import datetime

    try:
        bdf = pd.read_csv(db_path, low_memory=False)
        bdf.columns = [c.strip().lower() for c in bdf.columns]
        for col in ['winner_athlete_id', 'red_id', 'blue_id']:
            if col in bdf.columns:
                bdf[col] = bdf[col].apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None
                )
        bdf['red_full_name']  = bdf['red_first_name'].fillna('') + " " + bdf['red_last_name'].fillna('')
        bdf['blue_full_name'] = bdf['blue_first_name'].fillna('') + " " + bdf['blue_last_name'].fillna('')
        bdf['date_start']     = pd.to_datetime(bdf['date_start'], errors='coerce')
    except Exception as e:
        print(f"BOT: ошибка загрузки БД: {e}"); return

    RMAP = {
        'FIN':'Финал','FNL':'Финал','SFL':'1/2','QFL':'1/4',
        'R16':'1/8','R32':'1/16','R64':'1/32','R128':'1/64',
        'BR1':'Бронза','BR2':'Бронза','RP1':'Утешит.','RP2':'Утешит.',
    }
    FC = {'FIN','FNL'}

    def _ci(v, d=0):
        try: return int(float(v)) if pd.notna(v) else d
        except: return d

    bot = telebot.TeleBot(token, threaded=True)

    @bot.message_handler(commands=['start', 'help'])
    def on_start(m):
        bot.send_message(m.chat.id,
            "🥋 *FIGHTGURU*\n\n"
            "Введите фамилию атлета латиницей.\n"
            "Для точного поиска — фамилия и имя: `Kurzhev Ali`\n\n"
            "Получите статистику, последние результаты и данные о карьере.",
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: True)
    def on_msg(m):
        raw   = m.text.strip()
        parts = raw.lower().split()
        if not parts or len(parts[0]) < 2:
            bot.reply_to(m, "Введите фамилию (минимум 2 символа)."); return

        last_q  = parts[0]
        first_q = parts[1] if len(parts) >= 2 else None

        # поиск
        mask = (
            bdf['red_last_name'].str.lower().str.contains(last_q, na=False) |
            bdf['blue_last_name'].str.lower().str.contains(last_q, na=False)
        )
        res = bdf[mask].copy()

        if first_q:
            res = res[
                res['red_first_name'].str.lower().str.startswith(first_q, na=False) |
                res['blue_first_name'].str.lower().str.startswith(first_q, na=False)
            ]

        if res.empty:
            bot.reply_to(m, f"❌ Не найден: *{raw}*\nПроверьте написание.", parse_mode="Markdown")
            return

        # имя и страна
        r0 = res.iloc[0]
        if last_q in str(r0.get('red_last_name', '')).lower():
            aname = str(r0['red_full_name']).strip()
            acnt  = str(r0.get('red_nationality_code', '')).upper()
        else:
            aname = str(r0['blue_full_name']).strip()
            acnt  = str(r0.get('blue_nationality_code', '')).upper()

        # статистика
        wins = losses = finals_c = 0
        for _, row in res.iterrows():
            is_r = last_q in str(row.get('red_last_name', '')).lower()
            wid  = str(row.get('winner_athlete_id', ''))
            mid  = str(row.get('red_id', '') if is_r else row.get('blue_id', ''))
            won  = (wid == mid and wid != '')
            if won: wins += 1
            else:   losses += 1
            if str(row.get('round_code', '')).upper() in FC: finals_c += 1

        total = wins + losses
        wr    = round(wins / total * 100) if total else 0

        # последние 5 матчей
        recent = res.sort_values('date_start', ascending=False).head(5)
        lines  = ""
        for _, row in recent.iterrows():
            yr   = int(row['date_start'].year) if pd.notna(row['date_start']) else "?"
            is_r = last_q in str(row.get('red_last_name', '')).lower()
            wid  = str(row.get('winner_athlete_id', ''))
            mid  = str(row.get('red_id', '') if is_r else row.get('blue_id', ''))
            won  = (wid == mid and wid != '')
            msc  = _ci(row.get('red_score') if is_r else row.get('blue_score'))
            osc  = _ci(row.get('blue_score') if is_r else row.get('red_score'))
            opp  = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
            rc   = RMAP.get(str(row.get('round_code', '')).upper(), '?')
            ico  = "✅" if won else "❌"
            lines += f"{ico} {yr} {rc} | {msc}:{osc} vs {opp[:18]}\n"

        flag_emoji = FLAGS.get(acnt, "🌍")
        cname      = COUNTRIES.get(acnt, acnt)

        msg = (
            f"📊 *{aname}*\n"
            f"{flag_emoji} {cname}\n\n"
            f"Боёв: *{total}* | ✅ *{wins}* | ❌ *{losses}* | *{wr}%*"
        )
        if finals_c:
            msg += f" | 🏆 {finals_c} фин."
        msg += f"\n\n*Последние матчи:*\n{lines}"

        try:
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        except Exception:
            # fallback без разметки если Markdown сломался
            bot.send_message(m.chat.id, msg.replace("*",""))

    # пишем PID чтобы не запускать повторно
    with open(BOT_LOG_FILE, "w") as f:
        f.write(str(os.getpid()))

    print(f"BOT started pid={os.getpid()}")
    bot.infinity_polling(timeout=20, long_polling_timeout=15, restart_on_change=False)


def start_bot_if_needed():
    if not BOT_TOKEN or not TELEBOT_OK or not os.path.exists(DB_FILE):
        return
    # проверяем: уже запущен?
    if os.path.exists(BOT_LOG_FILE):
        try:
            pid = int(open(BOT_LOG_FILE).read().strip())
            os.kill(pid, 0)   # проверка — если процесс жив, исключения нет
            return            # бот уже работает
        except (ProcessLookupError, ValueError, OSError):
            pass              # процесс мёртв — запустим заново
    p = Process(target=_bot_worker, args=(BOT_TOKEN, DB_FILE), daemon=False)
    p.start()

start_bot_if_needed()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# Ключевой принцип: sq хранится ТОЛЬКО в session_state.
# st.text_input читает его оттуда через key=, не через value=.
# Это предотвращает сброс поля при rerun от кнопок фильтра.
# ─────────────────────────────────────────────────────────────────────────────
SS_DEFAULTS = {
    'sq':          '',      # текущий поисковый запрос
    '_sq_widget':  '',      # зеркало виджета
    'filter':      'Все',   # активный фильтр матчей
    'sel':         None,    # выбранный атлет (при неоднозначности)
    'prev_sq':     '',      # предыдущий запрос — для детекции смены
    'cam':         False,   # режим камеры
    'questions':   {},      # кэш вопросов по атлету
}
for k, v in SS_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# САЙДБАР
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🥋 FightGuru")
    st.markdown("---")
    nav = st.radio("", ["👤 Досье", "🏛️ Пантеон"], label_visibility="collapsed")
    st.markdown("---")
    if nav == "👤 Досье":
        cam_val = st.toggle("📹 Режим камеры", value=st.session_state.cam)
        if cam_val != st.session_state.cam:
            st.session_state.cam = cam_val
            st.rerun()
    st.markdown("---")
    if BOT_TOKEN:
        st.markdown("<small style='color:#2a2d3d'>🤖 Telegram-бот активен</small>",
                    unsafe_allow_html=True)
    if df is not None:
        st.markdown(f"<small style='color:#2a2d3d'>📊 {len(df):,} матчей</small>",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# GUARD
# ─────────────────────────────────────────────────────────────────────────────
if df is None:
    st.error(f"Файл '{DB_FILE}' не найден."); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ПАНТЕОН
# ─────────────────────────────────────────────────────────────────────────────
if nav == "🏛️ Пантеон":
    st.markdown("<h2 style='color:#edf0ff;margin-bottom:20px'>🏛️ Исторический Пантеон</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: tsel = st.selectbox("Турнир",   list(TOUR_GROUPS.keys()))
    with c2: dsel = st.selectbox("Дивизион", list(DIVISIONS.keys()))

    pat = '|'.join(TOUR_GROUPS[tsel])
    fd  = df[
        df['tournament_name'].str.contains(pat, case=False, na=False) &
        df['category_code'].str.contains(DIVISIONS[dsel], case=False, na=False)
    ]
    fm = fd[fd['round_code'].str.upper().str.contains('FNL|FIN', na=False)].copy()
    if fm.empty:
        st.warning("Нет данных."); st.stop()

    def _gw(r):
        if str(r['winner_athlete_id']) == str(r['red_id']):
            return r['red_full_name'], str(r['red_nationality_code']).upper()
        return r['blue_full_name'], str(r['blue_nationality_code']).upper()

    fm[['wn','wc']] = fm.apply(lambda r: pd.Series(_gw(r)), axis=1)

    st.markdown("**Зачёт по странам — 🥇 Золото**")
    stats = fm.groupby('wc').size().reset_index(name='g').sort_values('g', ascending=False)
    rows  = "".join(
        f"<tr><td>{fl(r['wc'])} {cn(r['wc'])}</td><td class='gold-n'>{r['g']}</td></tr>"
        for _, r in stats.iterrows()
    )
    st.markdown(
        f"<table class='gold-t'><thead><tr><th>Страна</th><th>Золото</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>",
        unsafe_allow_html=True
    )
    st.markdown("**По весовым категориям**")
    for cat in sorted(fm['category_code'].unique()):
        cdf = fm[fm['category_code'] == cat].sort_values('date_start', ascending=False)
        with st.expander(get_cat(cat)):
            for _, cr in cdf.iterrows():
                yr = int(cr['date_start'].year) if pd.notna(cr['date_start']) else "?"
                st.markdown(
                    f"**{yr}** &nbsp; {fl(cr['wc'])} {cr['wn']}",
                    unsafe_allow_html=True
                )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ДОСЬЕ — ПОИСКОВАЯ СТРОКА
# ВАЖНО: используем key='sq' — Streamlit сам читает из session_state['sq']
# и пишет туда при вводе. НЕ используем value= — это вызывает сброс при rerun.
# ─────────────────────────────────────────────────────────────────────────────
# text_input БЕЗ key= — иначе нельзя писать в session_state.sq из кода.
# Используем value= + сохраняем вручную через on_change.
def _on_search_change():
    st.session_state.sq      = st.session_state._sq_widget
    st.session_state.sel     = None
    st.session_state.filter  = "Все"
    st.session_state.prev_sq = st.session_state._sq_widget

st.text_input(
    "",
    value=st.session_state.sq,
    key="_sq_widget",
    placeholder="🔍  Фамилия атлета — или «Фамилия Имя» для точного поиска",
    label_visibility="collapsed",
    on_change=_on_search_change,
)
sq = st.session_state.sq.strip()

# Сброс при смене запроса (на случай прямой установки session_state.sq из кода)
if sq != st.session_state.prev_sq:
    st.session_state.sel     = None
    st.session_state.filter  = "Все"
    st.session_state.prev_sq = sq

if not sq:
    st.markdown(
        "<p style='color:#1e2030;font-size:15px;margin-top:60px;text-align:center'>"
        "Введите фамилию атлета</p>",
        unsafe_allow_html=True
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ПОИСК
# ─────────────────────────────────────────────────────────────────────────────
parts = sq.lower().split()

def match_side(row, pts):
    """Возвращает 'red'/'blue'/None."""
    for side in ("red", "blue"):
        last  = str(row.get(f"{side}_last_name",  "")).lower().strip()
        first = str(row.get(f"{side}_first_name", "")).lower().strip()
        if len(pts) == 1:
            if pts[0] == last: return side
        else:
            ok1 = pts[0] == last  and first.startswith(pts[1])
            ok2 = pts[1] == last  and first.startswith(pts[0])
            if ok1 or ok2: return side
    return None

# точный поиск
exact = []
for idx, row in df.iterrows():
    s = match_side(row, parts)
    if s is not None:
        exact.append((idx, s))

# fallback — contains по первому слову
if not exact:
    for idx, row in df.iterrows():
        for side in ("red", "blue"):
            last = str(row.get(f"{side}_last_name", "")).lower().strip()
            if parts[0] in last:
                exact.append((idx, side))
                break

if not exact:
    st.info("Атлет не найден. Попробуйте фамилию + имя."); st.stop()

idxs    = list(dict.fromkeys([x[0] for x in exact]))   # уникальные, порядок сохранён
matches = df.loc[idxs].copy()
matches = matches.sort_values(['date_start', 'round_rank'], ascending=[False, False])

# ─────────────────────────────────────────────────────────────────────────────
# СЛОВАРЬ НАЙДЕННЫХ АТЛЕТОВ
# ─────────────────────────────────────────────────────────────────────────────
athletes = {}   # full_name → {country, id}
for idx, row in matches.iterrows():
    side = match_side(row, parts)
    if side is None:
        # fallback
        for s in ("red", "blue"):
            if parts[0] in str(row.get(f"{s}_last_name", "")).lower():
                side = s; break
    if side is None: continue
    fn  = str(row.get(f"{side}_full_name", "")).strip()
    cde = str(row.get(f"{side}_nationality_code", "")).upper()
    aid = str(row.get(f"{side}_id", ""))
    if fn and fn not in athletes:
        athletes[fn] = {"country": cde, "id": aid}

# ─────────────────────────────────────────────────────────────────────────────
# ЭКРАН ВЫБОРА ПРИ НЕОДНОЗНАЧНОСТИ
# ─────────────────────────────────────────────────────────────────────────────
if len(athletes) > 1 and st.session_state.sel not in athletes:
    st.markdown(
        f"<p style='font-size:16px;color:#dde0ef;margin-bottom:18px'>"
        f"Найдено <b>{len(athletes)}</b> атлета — выберите нужного:</p>",
        unsafe_allow_html=True
    )
    for aname, info in athletes.items():
        ca, cb = st.columns([5, 1])
        with ca:
            st.markdown(
                f"<div style='background:#161720;border:1px solid #272a3a;"
                f"border-radius:14px;padding:14px 20px;font-size:15px;color:#dde0ef;'>"
                f"{fl(info['country'])} <b>{aname}</b> "
                f"<span style='color:#2a2d3d;font-size:12px'>· {cn(info['country'])}</span></div>",
                unsafe_allow_html=True
            )
        with cb:
            if st.button("Выбрать →", key=f"pick_{aname}"):
                st.session_state.sel = aname
                st.rerun()
    st.stop()

# Определяем chosen
if st.session_state.sel in athletes:
    chosen = st.session_state.sel
else:
    chosen = list(athletes.keys())[0]

chosen_low = chosen.lower().strip()

# Фильтруем matches под выбранного
def has_athlete(row):
    return (
        str(row.get('red_full_name',  '')).lower().strip() == chosen_low or
        str(row.get('blue_full_name', '')).lower().strip() == chosen_low
    )
matches = matches[matches.apply(has_athlete, axis=1)].copy()
if matches.empty:
    st.info("Матчи не найдены."); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ АТЛЕТА
# ─────────────────────────────────────────────────────────────────────────────
dob_list = []; cnt_list = []; final_name = ""
for _, row in matches.iterrows():
    for side in ("red", "blue"):
        if str(row.get(f"{side}_full_name", "")).lower().strip() == chosen_low:
            final_name = str(row.get(f"{side}_full_name", "")).strip()
            v = row.get(f"{side}_birth_date")
            if v and pd.notna(v): dob_list.append(str(v).strip())
            cnt_list.append(str(row.get(f"{side}_nationality_code", "")).upper())
            break

raw_dob  = max(set(dob_list), key=dob_list.count) if dob_list else ""
dob_fmt  = fmt_dob(raw_dob)
age_str  = calc_age(raw_dob)
acountry = max(set(cnt_list), key=cnt_list.count) if cnt_list else ""

# статистика
wins = losses = finals_c = 0
win_seq = []
recent_q = []
for _, row in matches.iterrows():
    is_r = str(row.get('red_full_name', '')).lower().strip() == chosen_low
    wid  = str(row.get('winner_athlete_id', ''))
    mid  = str(row.get('red_id', '') if is_r else row.get('blue_id', ''))
    won  = (wid == mid and wid != '')
    if won: wins += 1
    else:   losses += 1
    rc = str(row.get('round_code', '')).upper()
    if rc in FINALS_CODES: finals_c += 1
    win_seq.append(won)
    if len(recent_q) < 3:
        opp  = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
        ocnt = row['blue_nationality_code'] if is_r else row['red_nationality_code']
        msc  = ci(row.get('red_score')  if is_r else row.get('blue_score'))
        osc  = ci(row.get('blue_score') if is_r else row.get('red_score'))
        rl   = ROUND_MAP.get(rc, (0, '?'))[1]
        recent_q.append({"opp":opp,"ofl":fl(ocnt),"res":"W" if won else "L",
                          "sc":f"{msc}:{osc}","rnd":rl})

total   = wins + losses
winrate = round(wins / total * 100) if total else 0

# streak
s_type = "win"; s_n = 0
if win_seq:
    s_type = "win" if win_seq[0] else "loss"
    for w in win_seq:
        if (w and s_type=="win") or (not w and s_type=="loss"): s_n += 1
        else: break

# категория
main_cat = ""
if 'category_code' in matches.columns:
    cc = matches['category_code'].value_counts()
    if not cc.empty: main_cat = get_cat(cc.index[0])

# ─────────────────────────────────────────────────────────────────────────────
# РЕЖИМ КАМЕРЫ
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.cam:
    qk = f"q_{chosen}"
    if qk not in st.session_state.questions:
        st.session_state.questions[qk] = gen_q(
            final_name, acountry, age_str, wins, losses, finals_c, total, recent_q
        )
    qs = st.session_state.questions[qk]

    streak_h = ""
    if s_n >= 2:
        ico = "🔥" if s_type == "win" else "❄️"
        lbl = f"Серия: {s_n} {'побед' if s_type=='win' else 'поражений'}"
        cls = "sp-win" if s_type == "win" else "sp-loss"
        streak_h = f'<span class="streak-pill {cls}">{ico} {lbl}</span>'

    q_html = "".join(
        f'<div class="cam-q"><div class="cam-qn">Вопрос {i+1}</div>'
        f'<div class="cam-qt">{q}</div></div>'
        for i, q in enumerate(qs)
    )
    st.markdown(f"""
    <div class="cam-wrap">
      <div class="cam-name">{final_name}</div>
      <div class="cam-sub">{fl(acountry)} {cn(acountry)} · {dob_fmt} · {age_str}</div>
      {streak_h}
      <div class="cam-stats" style="margin-top:22px">
        <div class="cam-s"><div class="cam-n w">{total}</div><div class="cam-sl">Боёв</div></div>
        <div class="cam-s"><div class="cam-n g">{wins}</div><div class="cam-sl">Победы</div></div>
        <div class="cam-s"><div class="cam-n r">{losses}</div><div class="cam-sl">Поражения</div></div>
        <div class="cam-s"><div class="cam-n y">{winrate}%</div><div class="cam-sl">% побед</div></div>
      </div>
      {q_html}
    </div>
    """, unsafe_allow_html=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("🔄 Другие вопросы", use_container_width=True):
            st.session_state.questions[qk] = gen_q(
                final_name, acountry, age_str, wins, losses, finals_c, total, recent_q
            )
            st.rerun()
    with cc2:
        if st.button("✖ Выйти из режима камеры", use_container_width=True):
            st.session_state.cam = False; st.rerun()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ОБЫЧНЫЙ РЕЖИМ — ПРОФИЛЬ
# ─────────────────────────────────────────────────────────────────────────────
if len(athletes) > 1:
    if st.button("← Другой атлет"):
        st.session_state.sel = None; st.rerun()

streak_h = ""
if s_n >= 2:
    ico = "🔥" if s_type == "win" else "❄️"
    lbl = f"Серия: {s_n} {'побед' if s_type=='win' else 'поражений'} подряд"
    cls = "sp-win" if s_type == "win" else "sp-loss"
    streak_h = f'<div style="margin-top:10px"><span class="streak-pill {cls}">{ico} {lbl}</span></div>'

meta = []
if dob_fmt: meta.append(f"Дата рождения: {dob_fmt}")
if age_str: meta.append(age_str)
if main_cat: meta.append(main_cat)

st.markdown(f"""
<div class="profile-wrap">
  <div class="avatar">{inits(final_name)}</div>
  <div style="min-width:0;flex:1">
    <div class="p-name">{final_name}</div>
    <div class="p-country">{fl(acountry)} {cn(acountry)}</div>
    <div class="p-sub">{"&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta)}</div>
    {streak_h}
  </div>
</div>
""", unsafe_allow_html=True)

# статы
st.markdown(f"""
<div class="stat-grid">
  <div class="sc"><div class="sc-l">Всего боёв</div><div class="sc-v">{total}</div></div>
  <div class="sc"><div class="sc-l">Победы</div><div class="sc-v g">{wins}</div></div>
  <div class="sc"><div class="sc-l">Поражения</div><div class="sc-v r">{losses}</div></div>
  <div class="sc"><div class="sc-l">% побед</div><div class="sc-v y">{winrate}%</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ВКЛАДКИ
# ─────────────────────────────────────────────────────────────────────────────
tab_m, tab_i, tab_w = st.tabs(["🥊 Матчи", "🎙 Интервью", "📖 Справка"])

# ══════════════════════════  МАТЧИ  ══════════════════════════
with tab_m:

    # ── ФИЛЬТРЫ ──────────────────────────────────────────────
    # Используем st.radio скрытый + HTML-визуал.
    # st.radio надёжно хранит значение в session_state и НЕ сбрасывает sq.
    FILTERS = ["Все", "Победы", "Поражения", "Финалы"]

    # Рисуем HTML-чипы
    chips_html = '<div class="filter-row">'
    for opt in FILTERS:
        cls = "f-chip on" if st.session_state.filter == opt else "f-chip"
        chips_html += f'<span class="{cls}" id="fc_{opt}">{opt}</span>'
    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    # Невидимые кнопки под чипами — каждая занимает своё место
    f_cols = st.columns(len(FILTERS))
    for col, opt in zip(f_cols, FILTERS):
        with col:
            if st.button(opt, key=f"fb_{opt}", use_container_width=True,
                         help=f"Показать: {opt}"):
                st.session_state.filter = opt
                st.rerun()

    cur_year = None
    shown    = 0
    for _, row in matches.iterrows():
        is_r = str(row.get('red_full_name',  '')).lower().strip() == chosen_low
        wid  = str(row.get('winner_athlete_id', ''))
        mid  = str(row.get('red_id', '') if is_r else row.get('blue_id', ''))
        won  = (wid == mid and wid != '')
        rc   = str(row.get('round_code', '')).upper()

        if st.session_state.filter == "Победы"    and not won:           continue
        if st.session_state.filter == "Поражения" and won:               continue
        if st.session_state.filter == "Финалы"    and rc not in FINALS_CODES: continue

        msc  = ci(row.get('red_score')  if is_r else row.get('blue_score'))
        osc  = ci(row.get('blue_score') if is_r else row.get('red_score'))
        mpen = ci(row.get('red_penalties')  if is_r else row.get('blue_penalties'))
        open_= ci(row.get('blue_penalties') if is_r else row.get('red_penalties'))

        opp_full = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
        opp_last = str(row['blue_last_name'] if is_r else row['red_last_name']).strip()
        opp_cnt  = str(row['blue_nationality_code'] if is_r else row['red_nationality_code'])
        rl       = ROUND_MAP.get(rc, (0, rc))[1]
        cat      = get_cat(row.get('category_code', ''))
        ds       = row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??'
        yr       = row.get('year')
        ts       = fmt_time(row.get('fight_time', 0))
        cls      = "win" if won else "loss"
        lbl      = "WIN" if won else "LOSS"

        if pd.notna(yr) and int(yr) != cur_year:
            cur_year = int(yr)
            st.markdown(f'<div class="yr-sep">{cur_year}</div>', unsafe_allow_html=True)

        tags = f'<span class="tag rnd">{rl}</span><span class="tag">{cat}</span>'
        if mpen > 0 or open_ > 0:
            tags += f'<span class="tag pen">Пред. {mpen} / {open_}</span>'

        # флаг + страна соперника
        opp_flag_country = (
            f'<span style="font-size:16px">{fl(opp_cnt)}</span>'
            f'<span class="m-cnt">{cn(opp_cnt)}</span>'
        )

        st.markdown(f"""
        <div class="mc {cls}">
          <div class="badge {cls}">
            <span class="bs {cls}">{msc}:{osc}</span>
            <span class="bl {cls}">{lbl}</span>
          </div>
          <div style="min-width:0;overflow:hidden">
            <div class="m-tour">{str(row.get('tournament_name',''))}</div>
            <div class="m-opp">{opp_flag_country}&nbsp;{opp_full}</div>
            <div class="m-tags">{tags}</div>
          </div>
          <div class="m-right">
            <div class="m-date">{ds}</div>
            <div class="m-time">⏱ {ts}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"→ Досье: {opp_full}", key=f"ob_{row.name}"):
            st.session_state.sq      = opp_last
            st.session_state.prev_sq = ""   # сбросим чтобы детект сработал
            st.session_state.sel     = None
            st.session_state.filter  = "Все"
            st.rerun()

        shown += 1

    if shown == 0:
        st.markdown(
            "<p style='color:#2a2d3d;text-align:center;padding:40px 0'>"
            "Нет матчей по выбранному фильтру</p>",
            unsafe_allow_html=True
        )

# ══════════════════════════  ИНТЕРВЬЮ  ══════════════════════════
with tab_i:
    st.markdown(f"#### 🎙 Блиц-интервью — {final_name}")
    st.caption("Вопросы генерируются автоматически на основе данных карьеры")

    qk = f"q_{chosen}"
    if qk not in st.session_state.questions:
        st.session_state.questions[qk] = gen_q(
            final_name, acountry, age_str, wins, losses, finals_c, total, recent_q
        )
    qs = st.session_state.questions[qk]

    for i, q in enumerate(qs):
        st.markdown(
            f'<div class="q-card">'
            f'<div class="q-num">{i+1}</div>'
            f'<div class="q-text">{q}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    if st.button("🔄 Другие вопросы", key="rq_btn"):
        st.session_state.questions[qk] = gen_q(
            final_name, acountry, age_str, wins, losses, finals_c, total, recent_q
        )
        st.rerun()

    st.markdown("---")
    st.markdown("#### 💾 Записать ответы")
    st.caption("Сохранится локально в interviews.json")

    answers = []
    for i, q in enumerate(qs):
        a = st.text_area(
            f"Ответ {i+1}",
            key=f"ans_{i}_{chosen}",
            placeholder=f"Ответ на: «{q[:55]}…»",
            height=80
        )
        answers.append({"question": q, "answer": a})

    if st.button("💾 Сохранить интервью", type="primary", key="save_btn"):
        filled = [x for x in answers if x["answer"].strip()]
        if filled:
            now = datetime.now().strftime("%d.%m.%Y %H:%M")
            save_ivw(final_name, now, answers)
            st.success(f"✅ Сохранено — {now}")
        else:
            st.warning("Заполните хотя бы один ответ.")

    past = load_ivw().get(final_name.strip().upper(), [])
    if past:
        st.markdown("---")
        st.markdown(f"#### 📂 Прошлые интервью — {final_name}")
        for ivw in reversed(past):
            with st.expander(f"🗓 {ivw['date']}"):
                for item in ivw['answers']:
                    if item.get('answer', '').strip():
                        st.markdown(f"**В:** {item['question']}")
                        st.markdown(f"**О:** {item['answer']}")
                        st.markdown("---")

# ══════════════════════════  СПРАВКА  ══════════════════════════
with tab_w:
    st.markdown(f"#### 📖 Справка — {final_name}")

    wiki = {}
    for variant in [final_name, " ".join(reversed(final_name.split()))]:
        wiki = wiki_get(variant)
        if wiki: break

    if wiki:
        lng = "Wikipedia RU" if wiki.get("lang") == "ru" else "Wikipedia EN"
        url_html = (
            f"<a class='wiki-link' href='{wiki['url']}' target='_blank'>"
            f"→ Читать полностью на Wikipedia</a>"
        ) if wiki.get("url") else ""
        st.markdown(
            f'<div class="wiki-box">'
            f'<div class="wiki-lbl">{lng} — {wiki["title"]}</div>'
            f'<div class="wiki-text">{wiki["extract"]}</div>'
            f'{url_html}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="wiki-box">'
            f'<div class="wiki-lbl">Wikipedia</div>'
            f'<div class="wiki-text" style="color:#2a2d3d">'
            f'Статья о <b style="color:#3d4058">{final_name}</b> не найдена.<br>'
            f'Возможно, страница ещё не создана.</div></div>',
            unsafe_allow_html=True
        )

    ne = final_name.replace(' ', '+')
    nt = final_name.replace(' ', '').lower()
    st.markdown(
        f'<div class="ref-grid">'
        f'<a class="ref-a" href="https://www.google.com/search?q={ne}+самбо+sambo" target="_blank">🔍 Google</a>'
        f'<a class="ref-a" href="https://ru.wikipedia.org/w/index.php?search={ne}" target="_blank">📖 Wikipedia</a>'
        f'<a class="ref-a" href="https://www.youtube.com/results?search_query={ne}+sambo" target="_blank">▶ YouTube</a>'
        f'<a class="ref-a" href="https://www.instagram.com/explore/tags/{nt}/" target="_blank">📷 Instagram</a>'
        f'<a class="ref-a" href="https://t.me/search?query={ne}" target="_blank">✈ Telegram</a>'
        f'</div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────────────────────
# ПОДВАЛ
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:#111318;margin-top:50px'>"
    "<p style='text-align:center;color:#1a1c28;font-size:11px;margin-top:8px'>"
    "FightGuru v5 · Мир самбо</p>",
    unsafe_allow_html=True
)

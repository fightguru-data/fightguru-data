"""
FIGHTGURU v5 — чистая финальная версия
Fixes:
  1. Фильтры: используем st.radio (надёжно, без хаков с невидимыми кнопками)
  2. Выбор атлета: вся карточка кликабельна через st.button с overlay
  3. Бот: threading.Thread + явный snapshot df — multiprocessing ломается на Streamlit Cloud
  4. Поле поиска: value= без key= чтобы можно было писать в session_state.sq из кода
"""

import streamlit as st
import pandas as pd
import os, json, random, threading, requests
from datetime import datetime

try:
    import telebot
    TELEBOT_OK = True
except ImportError:
    TELEBOT_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────────────────────────────────────
DB_FILE         = "AllTournament.csv"
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.stApp {
  background: #0c0d12 !important;
  color: #dde0ef;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.main .block-container {
  padding: 1rem 1.2rem 3rem !important;
  max-width: 880px !important;
}

/* поиск */
div[data-testid="stTextInput"] input {
  background: #161720 !important;
  border: 1px solid #30334a !important;
  border-radius: 14px !important;
  color: #e8ecff !important;
  font-size: 16px !important;
  padding: 12px 18px !important;
  font-family: 'Inter', sans-serif !important;
}

/* сайдбар */
section[data-testid="stSidebar"] {
  background: #09090e !important;
  border-right: 1px solid #1a1c28 !important;
}
section[data-testid="stSidebar"] label {
  color: #9093ab !important;
  font-size: 15px !important;
}

/* radio фильтры — скрываем стандартный вид, показываем только pill-кнопки */
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
  display: flex !important;
  flex-direction: row !important;
  gap: 8px !important;
  flex-wrap: wrap !important;
}
div[data-testid="stRadio"] > div > label {
  display: flex !important;
  align-items: center !important;
  background: #1e2035 !important;
  border: 1.5px solid #30334a !important;
  border-radius: 10px !important;
  padding: 8px 20px !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  color: #7880a8 !important;
  cursor: pointer !important;
  transition: all .15s !important;
}
div[data-testid="stRadio"] > div > label:hover {
  border-color: #505470 !important;
  color: #a0a4c0 !important;
}
div[data-testid="stRadio"] > div > label[data-baseweb="radio"]:has(input:checked),
div[data-testid="stRadio"] > div > label[aria-checked="true"] {
  background: #c0392b !important;
  border-color: #c0392b !important;
  color: #fff !important;
}
/* скрываем сам radio-кружок */
div[data-testid="stRadio"] > div > label > div:first-child { display: none !important; }
div[data-testid="stRadio"] > div > label > div[data-testid="stMarkdownContainer"] p {
  font-size: 14px !important;
  font-weight: 700 !important;
  margin: 0 !important;
}

/* профиль */
.profile-wrap {
  background: linear-gradient(140deg, #171924 0%, #111318 100%);
  border: 1px solid #272a3a;
  border-radius: 22px;
  padding: 22px 24px;
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  gap: 18px;
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
  width: 62px; height: 62px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(145deg, #c0392b, #7b1717);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 900; color: #fff;
  box-shadow: 0 6px 24px rgba(192,57,43,.35);
}
.p-name    { font-size: 22px; font-weight: 800; color: #f0f4ff; line-height: 1.15; }
.p-country { font-size: 15px; color: #9da4c0; margin-top: 5px; display: flex; align-items: center; gap: 6px; }
.p-sub     { font-size: 14px; color: #8890b0; margin-top: 4px; line-height: 1.6; }
.streak-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 700;
  padding: 5px 14px; border-radius: 20px; margin-top: 10px;
}
.sp-win  { background: #071a0f; color: #2ecc71; border: 1px solid #1a4a2a; }
.sp-loss { background: #1a0707; color: #e74c3c; border: 1px solid #4a1515; }

/* статы */
.stat-grid {
  display: grid; grid-template-columns: repeat(4,1fr);
  gap: 8px; margin-bottom: 6px;
}
.sc { background: #161720; border: 1px solid #272a3a; border-radius: 16px; padding: 16px 14px; }
.sc-l { font-size: 11px; color: #666a88; text-transform: uppercase; letter-spacing:.1em; margin-bottom: 7px; }
.sc-v { font-size: 28px; font-weight: 900; line-height: 1; color: #edf0ff; }
.sc-v.g { color: #2ecc71; }
.sc-v.r { color: #e74c3c; }
.sc-v.y { color: #f1c40f; }

/* год-разделитель */
.yr-sep {
  font-size: 12px; font-weight: 800; color: #52566e;
  text-transform: uppercase; letter-spacing: .14em;
  padding: 18px 0 10px;
  border-bottom: 1px solid #1a1c28;
  margin-bottom: 10px;
}

/* карточка матча */
.mc {
  background: #161720; border: 1px solid #272a3a; border-radius: 16px;
  padding: 14px 16px; margin-bottom: 8px;
  display: grid; grid-template-columns: 58px 1fr auto;
  gap: 0 14px; align-items: center;
  border-left: 3px solid #272a3a;
}
.mc:hover { background: #1c1e2a; }
.mc.win  { border-left-color: #2ecc71; }
.mc.loss { border-left-color: #e74c3c; }

.badge { width: 52px; height: 52px; border-radius: 12px; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; }
.badge.win  { background: #071a0f; }
.badge.loss { background: #1a0707; }
.bs { font-size: 17px; font-weight: 900; line-height: 1; }
.bs.win  { color: #2ecc71; }
.bs.loss { color: #e74c3c; }
.bl { font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.bl.win  { color: #1a7a40; }
.bl.loss { color: #7a1a1a; }

.m-tour { font-size: 12px; color: #606480; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-opp  { font-size: 16px; font-weight: 700; color: #e8ecff; display: flex; align-items: center; gap: 7px; margin-bottom: 5px; flex-wrap: wrap; }
.m-cnt  { font-size: 12px; color: #7880a0; font-weight: 500; }
.m-tags { display: flex; gap: 5px; flex-wrap: wrap; }
.tag    { font-size: 11px; padding: 3px 10px; border-radius: 20px; background: #1e2135; color: #6870a0; border: 1px solid #2c2e45; }
.tag.rnd { background: #1a0707; color: #c0392b; border-color: #3d1515; }
.tag.pen { background: #1a1500; color: #b8860b; border-color: #3d3000; }
.m-right { text-align: right; flex-shrink: 0; min-width: 68px; }
.m-date  { font-size: 12px; color: #606480; margin-bottom: 5px; }
.m-time  { font-size: 12px; color: #505468; }

/* кнопки досье и выбора атлета — переопределяем Streamlit */
div[data-testid="stButton"] > button {
  background: #111318 !important;
  border: 1px solid #1e2130 !important;
  border-radius: 10px !important;
  color: #6090b8 !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  font-family: 'Inter', sans-serif !important;
  width: 100% !important;
  text-align: left !important;
  padding: 10px 16px !important;
  margin-bottom: 12px !important;
  transition: all .15s !important;
}
div[data-testid="stButton"] > button:hover {
  border-color: #2a4a6a !important;
  color: #80b0d8 !important;
  background: #141820 !important;
}

/* карточки выбора атлета */
.athlete-card {
  background: #161720; border: 1px solid #272a3a; border-radius: 14px;
  padding: 16px 20px; margin-bottom: 4px;
  font-size: 15px; color: #dde0ef;
  cursor: pointer;
}
.athlete-card:hover { background: #1c1e2a; border-color: #404360; }

/* вопросы */
.q-card {
  background: #161720; border: 1px solid #272a3a; border-radius: 16px;
  padding: 18px 20px; margin-bottom: 10px;
  display: flex; gap: 16px; align-items: flex-start;
}
.q-num {
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  background: #1a0707; border: 1px solid #4a1515;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 900; color: #c0392b;
}
.q-text { font-size: 17px; color: #ced2e8; line-height: 1.6; }

/* wikipedia */
.wiki-box { background: #161720; border: 1px solid #272a3a; border-radius: 16px; padding: 20px 22px; margin-bottom: 14px; }
.wiki-lbl  { font-size: 11px; color: #606480; text-transform: uppercase; letter-spacing:.1em; margin-bottom: 10px; }
.wiki-text { font-size: 15px; color: #9095b5; line-height: 1.75; }
.wiki-link { font-size: 14px; color: #4472a0; margin-top: 12px; display: block; }

.ref-grid  { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.ref-a { font-size: 14px; color: #7090b8; background: #161720; border: 1px solid #272a3a; border-radius: 10px; padding: 8px 16px; text-decoration: none; }
.ref-a:hover { border-color: #404360; }

/* камера */
.cam-wrap {
  background: #09090e; border: 2px solid #c0392b; border-radius: 24px;
  padding: 36px 28px; text-align: center; margin-bottom: 18px;
  box-shadow: 0 0 60px rgba(192,57,43,.15);
}
.cam-name  { font-size: 38px; font-weight: 900; color: #fff; line-height: 1.1; margin-bottom: 6px; }
.cam-sub   { font-size: 16px; color: #8890b0; margin-bottom: 24px; }
.cam-stats { display: flex; justify-content: center; gap: 20px; margin-bottom: 28px; flex-wrap: wrap; }
.cam-s  { text-align: center; min-width: 65px; }
.cam-n  { font-size: 46px; font-weight: 900; line-height: 1; }
.cam-n.g { color: #2ecc71; } .cam-n.r { color: #e74c3c; }
.cam-n.w { color: #edf0ff; } .cam-n.y { color: #f1c40f; }
.cam-sl { font-size: 11px; color: #606480; text-transform: uppercase; letter-spacing:.08em; margin-top:4px; }
.cam-q  { background: #161720; border: 1px solid #272a3a; border-radius: 14px; padding: 18px 22px; margin-bottom: 10px; text-align: left; }
.cam-qn { font-size: 12px; color: #e05040; font-weight: 800; margin-bottom: 7px; text-transform: uppercase; letter-spacing:.08em; }
.cam-qt { font-size: 20px; color: #e8ecff; line-height: 1.5; }

/* пантеон */
.gold-t { width: 100%; border-collapse: collapse; }
.gold-t th { font-size: 11px; color: #606480; text-transform: uppercase; letter-spacing:.1em; padding: 8px 14px; border-bottom: 1px solid #272a3a; text-align: left; }
.gold-t td { font-size: 15px; color: #b0b4d0; padding: 11px 14px; border-bottom: 1px solid #111318; }
.gold-t tr:hover td { background: #161720; }
.gold-n { font-weight: 900; color: #f1c40f; }

#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# СПРАВОЧНИКИ
# ─────────────────────────────────────────────────────────────────────────────
ROUND_MAP = {
    'FIN':(7,'Финал'),'FNL':(7,'Финал'),
    'SFL':(6,'1/2'),  'QFL':(5,'1/4'),
    'R16':(4,'1/8'),  'R32':(3,'1/16'),
    'R64':(2,'1/32'), 'R128':(1,'1/64'),
    'BR1':(1,'Бронза'),'BR2':(1,'Бронза'),
    'RP1':(1,'Утешит.'),'RP2':(1,'Утешит.'),
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
    "SUI":"🇨🇭","NOR":"🇳🇴","DEN":"🇩🇰","FIN":"🇫🇮","EST":"🇪🇪",
    "IRN":"🇮🇷","IND":"🇮🇳","MAS":"🇲🇾","THA":"🇹🇭","PHI":"🇵🇭","BRA":"🇧🇷",
    "ARG":"🇦🇷","MEX":"🇲🇽","CAN":"🇨🇦","AUS":"🇦🇺","MAR":"🇲🇦","EGY":"🇪🇬",
    "ALB":"🇦🇱","BIH":"🇧🇦","MNE":"🇲🇪","KOS":"🇽🇰","SLO":"🇸🇮","CYP":"🇨🇾",
    "ISL":"🇮🇸","IRL":"🇮🇪","RSA":"🇿🇦","KEN":"🇰🇪","SEN":"🇸🇳","NGR":"🇳🇬",
    "KWT":"🇰🇼","VIE":"🇻🇳","COL":"🇨🇴","VEN":"🇻🇪","NZL":"🇳🇿","TUN":"🇹🇳",
    "ALG":"🇩🇿","PAK":"🇵🇰","LUX":"🇱🇺","MLT":"🇲🇹","MON":"🇲🇨",
}

COUNTRIES = {
    "RUS":"Россия","BLR":"Беларусь","KAZ":"Казахстан","UZB":"Узбекистан",
    "KGZ":"Кыргызстан","TKM":"Туркменистан","MGL":"Монголия","GEO":"Грузия",
    "ARM":"Армения","AZE":"Азербайджан","TJK":"Таджикистан","UKR":"Украина",
    "SRB":"Сербия","FRA":"Франция","AIN":"Нейтр. атлет","TUR":"Турция",
    "BUL":"Болгария","CRO":"Хорватия","GBR":"Великобр.","GER":"Германия",
    "NED":"Нидерланды","GRE":"Греция","LTU":"Литва","MDA":"Молдова",
    "LAT":"Латвия","ISR":"Израиль","ITA":"Италия","ROU":"Румыния",
    "SVK":"Словакия","CZE":"Чехия","HUN":"Венгрия","POL":"Польша",
    "SWE":"Швеция","ESP":"Испания","POR":"Португалия","JPN":"Япония",
    "KOR":"Корея","CHN":"Китай","MKD":"Сев. Македония","BEL":"Бельгия",
    "AUT":"Австрия","SUI":"Швейцария","NOR":"Норвегия","DEN":"Дания",
    "FIN":"Финляндия","EST":"Эстония","IRN":"Иран","IND":"Индия",
    "MAS":"Малайзия","THA":"Таиланд","BRA":"Бразилия","ARG":"Аргентина",
    "MEX":"Мексика","CAN":"Канада","AUS":"Австралия","MAR":"Марокко",
    "EGY":"Египет","ALB":"Албания","BIH":"Босния","MNE":"Черногория",
    "KOS":"Косово","SLO":"Словения","ISL":"Исландия","IRL":"Ирландия",
    "RSA":"ЮАР","KEN":"Кения","SEN":"Сенегал","NGR":"Нигерия",
    "KWT":"Кувейт","VIE":"Вьетнам","COL":"Колумбия","VEN":"Венесуэла",
    "NZL":"Новая Зел.","TUN":"Тунис","ALG":"Алжир","PAK":"Пакистан",
    "PHI":"Филиппины","CYP":"Кипр","MON":"Монако","LUX":"Люксембург","USA":"США",
}

TOUR_GROUPS = {
    "Чемпионат Мира":    ["World Sambo Championships","World SAMBO Championships"],
    "Кубок Мира":        ["Cup","President"],
    "Чемпионат Европы":  ["European Sambo Championships","European Championships"],
    "ЧМ Азии и Океании": ["Asia and Oceania Sambo Championships"],
}
DIVISIONS = {
    "Спортивное Самбо (М)":"SAMM","Спортивное Самбо (Ж)":"SAMW",
    "Боевое Самбо (М)":"CSMM","Боевое Самбо (Ж)":"CSMW",
}

# ─────────────────────────────────────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────────────────────────────────────
def fl(code):    return FLAGS.get(str(code).upper().strip(), "🌍")
def cn(code):
    c = str(code).upper().strip()
    return COUNTRIES.get(c, c)

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
    p = "Боевое" if "CSM" in c else ("Спорт" if "SAM" in c else "")
    g = "М" if ("SAMM" in c or "CSMM" in c) else ("Ж" if ("SAMW" in c or "CSMW" in c) else "")
    w = ""
    if "ADT" in c:
        pts = c.split("ADT")
        if len(pts) > 1:
            w = (pts[1][:-1]+"+") if pts[1].endswith('O') else pts[1]
    return f"{p} {g} {w}кг".strip()

def ci(v, d=0):
    try: return int(float(v)) if pd.notna(v) else d
    except: return d

def inits(name):
    p = name.strip().split()
    if len(p) >= 2: return (p[0][0]+p[-1][0]).upper()
    return name[:2].upper() if name else "?"

def fmt_dob(raw):
    try: return datetime.strptime(raw, "%Y-%m-%d").strftime("%d.%m.%Y")
    except: return raw

def calc_age(raw):
    try: return f"{(datetime.now()-datetime.strptime(raw,'%Y-%m-%d')).days//365} лет"
    except: return ""

# ─────────────────────────────────────────────────────────────────────────────
# WIKIPEDIA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def wiki_get(name):
    for lang in ("ru","en"):
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ','_')}",
                timeout=6, headers={"User-Agent":"FightGuru/5"}
            )
            if r.status_code == 200:
                d = r.json()
                if d.get("type") == "standard":
                    return {"title":d.get("title",""),
                            "extract":d.get("extract","")[:700],
                            "url":d.get("content_urls",{}).get("desktop",{}).get("page",""),
                            "lang":lang}
        except: pass
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# ВОПРОСЫ
# ─────────────────────────────────────────────────────────────────────────────
def gen_q(name, acnt, age, wins, losses, finals, total, recent):
    fn = name.split()[0] if name else "Спортсмен"
    cname = cn(acnt)
    wr = round(wins/total*100) if total else 0
    qs = []

    if recent:
        m = recent[0]
        opp,res,sc,rnd,ofl = m["opp"],m["res"],m["sc"],m["rnd"],m["ofl"]
        if res == "W":
            pool = [f"{fn}, только что победил {ofl} {opp} со счётом {sc} — что почувствовал?",
                    f"Победа над {ofl} {opp}, {sc}. Это тактика или кураж?",
                    f"{fn}, {sc} в {rnd} — всё шло по плану или импровизировал?"]
        else:
            pool = [f"{fn}, поражение от {ofl} {opp} — что пошло не так?",
                    f"Бой с {ofl} {opp} не в твою пользу. Что берёшь из него?",
                    f"Счёт {sc} — был момент когда чувствовал что можешь переломить?"]
        qs.append(random.choice(pool))

    if finals >= 2:
        p2 = [f"У тебя {finals} финала — финал для тебя кайф или стресс?",
              f"{fn}, ты снова в финале. Что меняется в голове?",
              f"Регулярно доходишь до финалов. В чём секрет стабильности?"]
    elif wr >= 75:
        p2 = [f"{wr}% побед — это талант, труд или тренер?",
              f"Что делает тебя сложным соперником?",
              f"Такой процент — есть соперник которого реально опасаешься?"]
    elif losses > wins:
        p2 = [f"Сложный период? Как работаешь над ошибками?",
              f"Какое поражение дало тебе больше всего?",
              f"{fn}, через что сейчас проходишь в карьере?"]
    else:
        p2 = [f"{fn}, {wins} побед — какая самая памятная?",
              f"Что мотивирует продолжать выступать на таком уровне?",
              f"Опиши свой день на соревнованиях — от подъёма до ковра."]
    qs.append(random.choice(p2))

    p3 = [f"Самбо в {cname} — популярный спорт или приходится объяснять?",
          f"{fn}, есть соцсети? Где тебя найти?",
          f"Почему самбо а не другая борьба?",
          f"Есть спортсмен-кумир? На кого равняешься?",
          f"{fn}, что посоветуешь тем кто только начинает самбо?",
          f"Самый тяжёлый момент — и как прошёл через него?",
          f"Что значит защищать цвета {cname}?",
          f"{fn}, следующая большая цель?"]
    qs.append(random.choice(p3))
    return qs

# ─────────────────────────────────────────────────────────────────────────────
# ИНТЕРВЬЮ
# ─────────────────────────────────────────────────────────────────────────────
def load_ivw():
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def save_ivw(name, date, answers):
    d = load_ivw()
    k = name.strip().upper()
    if k not in d: d[k] = []
    d[k].append({"date":date,"answers":answers})
    with open(INTERVIEWS_FILE,"w",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DB_FILE): return None
    try:
        df = pd.read_csv(DB_FILE, low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]
        for col in ['winner_athlete_id','red_id','blue_id']:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower()!='nan' else None
                )
        df['red_full_name']  = df['red_first_name'].fillna('')+" "+df['red_last_name'].fillna('')
        df['blue_full_name'] = df['blue_first_name'].fillna('')+" "+df['blue_last_name'].fillna('')
        df['date_start']     = pd.to_datetime(df['date_start'], errors='coerce')
        df['year']           = df['date_start'].dt.year
        df['round_rank']     = df['round_code'].apply(
            lambda x: ROUND_MAP.get(str(x).upper(),(0,str(x)))[0]
        )
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}"); return None

df = load_data()

# ─────────────────────────────────────────────────────────────────────────────
# ТЕЛЕГРАМ-БОТ
# Используем threading.Thread (не Process) — Process не работает на Streamlit Cloud.
# df передаётся как snapshot через замыкание.
# bot_started хранится в session_state — НЕ перезапускаем при rerun.
# ─────────────────────────────────────────────────────────────────────────────
if "bot_started" not in st.session_state:
    st.session_state.bot_started = False

if BOT_TOKEN and TELEBOT_OK and df is not None and not st.session_state.bot_started:

    _snapshot = df.copy()  # snapshot данных для потока

    def _run_bot(token, data):
        RMAP = {
            'FIN':'Финал','FNL':'Финал','SFL':'1/2','QFL':'1/4',
            'R16':'1/8','R32':'1/16','R64':'1/32','R128':'1/64',
            'BR1':'Бронза','BR2':'Бронза','RP1':'Утешит.','RP2':'Утешит.',
        }
        FC = {'FIN','FNL'}

        def _ci(v, d=0):
            try: return int(float(v)) if pd.notna(v) else d
            except: return d

        try:
            bot = telebot.TeleBot(token, threaded=False)
        except Exception as e:
            print(f"BOT init error: {e}"); return

        @bot.message_handler(commands=['start','help'])
        def on_start(m):
            try:
                bot.send_message(m.chat.id,
                    "🥋 FIGHTGURU\n\n"
                    "Введите фамилию атлета латиницей.\n"
                    "Точный поиск: фамилия и имя через пробел.\n"
                    "Пример: Zinnatov или Kurzhev Ali"
                )
            except: pass

        @bot.message_handler(func=lambda m: True)
        def on_msg(m):
            try:
                raw   = m.text.strip()
                parts = raw.lower().split()
                if not parts or len(parts[0]) < 2:
                    bot.reply_to(m, "Введите фамилию (минимум 2 символа)."); return

                last_q  = parts[0]
                first_q = parts[1] if len(parts) >= 2 else None

                mask = (
                    data['red_last_name'].str.lower().str.contains(last_q, na=False) |
                    data['blue_last_name'].str.lower().str.contains(last_q, na=False)
                )
                res = data[mask].copy()

                if first_q:
                    res = res[
                        res['red_first_name'].str.lower().str.startswith(first_q, na=False) |
                        res['blue_first_name'].str.lower().str.startswith(first_q, na=False)
                    ]

                if res.empty:
                    bot.reply_to(m, f"Не найден: {raw}\nПроверьте написание."); return

                r0 = res.iloc[0]
                if last_q in str(r0.get('red_last_name','')).lower():
                    aname = str(r0['red_full_name']).strip()
                    acnt  = str(r0.get('red_nationality_code','')).upper()
                else:
                    aname = str(r0['blue_full_name']).strip()
                    acnt  = str(r0.get('blue_nationality_code','')).upper()

                wins=losses=finals_c=0
                for _, row in res.iterrows():
                    is_r = last_q in str(row.get('red_last_name','')).lower()
                    wid  = str(row.get('winner_athlete_id',''))
                    mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
                    won  = (wid==mid and wid!='')
                    if won: wins+=1
                    else:   losses+=1
                    if str(row.get('round_code','')).upper() in FC: finals_c+=1

                total = wins+losses
                wr = round(wins/total*100) if total else 0

                recent = res.sort_values('date_start',ascending=False).head(5)
                lines = ""
                for _, row in recent.iterrows():
                    yr   = int(row['date_start'].year) if pd.notna(row['date_start']) else "?"
                    is_r = last_q in str(row.get('red_last_name','')).lower()
                    wid  = str(row.get('winner_athlete_id',''))
                    mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
                    won  = (wid==mid and wid!='')
                    msc  = _ci(row.get('red_score') if is_r else row.get('blue_score'))
                    osc  = _ci(row.get('blue_score') if is_r else row.get('red_score'))
                    opp  = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
                    rc   = RMAP.get(str(row.get('round_code','')).upper(),'?')
                    ico  = "✅" if won else "❌"
                    lines += f"{ico} {yr} {rc} | {msc}:{osc} vs {opp[:18]}\n"

                flag_e = FLAGS.get(acnt,"🌍")
                cname  = COUNTRIES.get(acnt, acnt)
                msg = (f"📊 {aname}\n{flag_e} {cname}\n\n"
                       f"Боёв: {total} | ✅ {wins} | ❌ {losses} | {wr}%")
                if finals_c: msg += f" | 🏆 {finals_c} фин."
                msg += f"\n\nПоследние матчи:\n{lines}"

                bot.send_message(m.chat.id, msg)
            except Exception as ex:
                print(f"BOT on_msg error: {ex}")
                try: bot.reply_to(m, "Ошибка при обработке запроса.")
                except: pass

        print(f"BOT polling start, token={token[:10]}...")
        while True:
            try:
                bot.infinity_polling(timeout=25, long_polling_timeout=20)
            except Exception as ex:
                print(f"BOT polling error: {ex}, restarting in 5s...")
                import time; time.sleep(5)

    t = threading.Thread(target=_run_bot, args=(BOT_TOKEN, _snapshot), daemon=True)
    t.start()
    st.session_state.bot_started = True

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for k,v in [('sq',''),('prev_sq',''),('filter','Все'),('sel',None),
             ('cam',False),('questions',{})]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# САЙДБАР
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🥋 FightGuru")
    st.markdown("---")
    nav = st.radio("nav", ["👤 Досье","🏛️ Пантеон"], label_visibility="collapsed")
    st.markdown("---")
    if nav == "👤 Досье":
        cam_val = st.toggle("📹 Режим камеры", value=st.session_state.cam)
        if cam_val != st.session_state.cam:
            st.session_state.cam = cam_val
            st.rerun()
    st.markdown("---")
    status_parts = []
    if BOT_TOKEN and st.session_state.bot_started:
        status_parts.append("🤖 Бот активен")
    if df is not None:
        status_parts.append(f"📊 {len(df):,} матчей")
    for s in status_parts:
        st.markdown(f"<small style='color:#52566e'>{s}</small>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# GUARD
# ─────────────────────────────────────────────────────────────────────────────
if df is None:
    st.error(f"Файл '{DB_FILE}' не найден."); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ПАНТЕОН
# ─────────────────────────────────────────────────────────────────────────────
if nav == "🏛️ Пантеон":
    st.markdown("<h2 style='color:#f0f4ff;margin-bottom:20px'>🏛️ Исторический Пантеон</h2>",
                unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1: tsel = st.selectbox("Турнир",   list(TOUR_GROUPS.keys()))
    with c2: dsel = st.selectbox("Дивизион", list(DIVISIONS.keys()))

    pat = '|'.join(TOUR_GROUPS[tsel])
    fd  = df[df['tournament_name'].str.contains(pat,case=False,na=False) &
             df['category_code'].str.contains(DIVISIONS[dsel],case=False,na=False)]
    fm  = fd[fd['round_code'].str.upper().str.contains('FNL|FIN',na=False)].copy()

    if fm.empty: st.warning("Нет данных."); st.stop()

    def _gw(r):
        if str(r['winner_athlete_id'])==str(r['red_id']):
            return r['red_full_name'], str(r['red_nationality_code']).upper()
        return r['blue_full_name'], str(r['blue_nationality_code']).upper()

    fm[['wn','wc']] = fm.apply(lambda r: pd.Series(_gw(r)), axis=1)

    st.markdown("**Зачёт по странам — 🥇 Золото**")
    stats = fm.groupby('wc').size().reset_index(name='g').sort_values('g',ascending=False)
    rows  = "".join(f"<tr><td>{fl(r['wc'])} {cn(r['wc'])}</td><td class='gold-n'>{r['g']}</td></tr>"
                    for _,r in stats.iterrows())
    st.markdown(f"<table class='gold-t'><thead><tr><th>Страна</th><th>Золото</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>", unsafe_allow_html=True)

    st.markdown("**По весам**")
    for cat in sorted(fm['category_code'].unique()):
        cdf = fm[fm['category_code']==cat].sort_values('date_start',ascending=False)
        with st.expander(get_cat(cat)):
            for _,cr in cdf.iterrows():
                yr = int(cr['date_start'].year) if pd.notna(cr['date_start']) else "?"
                st.markdown(f"**{yr}** &nbsp; {fl(cr['wc'])} {cr['wn']}", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ДОСЬЕ — ПОИСК
# Используем value= без key= чтобы можно было писать в session_state.sq из кода.
# on_change сбрасывает фильтр и выбор при новом вводе.
# ─────────────────────────────────────────────────────────────────────────────
def _on_change():
    new_val = st.session_state.get("_sq_inp","").strip()
    if new_val != st.session_state.sq:
        st.session_state.sq      = new_val
        st.session_state.prev_sq = new_val
        st.session_state.sel     = None
        st.session_state.filter  = "Все"

st.text_input("", value=st.session_state.sq, key="_sq_inp",
              placeholder="🔍  Фамилия атлета — или «Фамилия Имя»",
              label_visibility="collapsed", on_change=_on_change)

sq = st.session_state.sq.strip()

if not sq:
    st.markdown("<p style='color:#2a2d3d;font-size:15px;margin-top:60px;text-align:center'>"
                "Введите фамилию атлета</p>", unsafe_allow_html=True)
    st.stop()

parts = sq.lower().split()

# ─────────────────────────────────────────────────────────────────────────────
# ПОИСК
# ─────────────────────────────────────────────────────────────────────────────
def match_side(row, pts):
    for side in ("red","blue"):
        last  = str(row.get(f"{side}_last_name","")).lower().strip()
        first = str(row.get(f"{side}_first_name","")).lower().strip()
        if len(pts)==1:
            if pts[0]==last: return side
        else:
            if (pts[0]==last and first.startswith(pts[1])) or \
               (pts[1]==last and first.startswith(pts[0])): return side
    return None

exact = []
for idx, row in df.iterrows():
    s = match_side(row, parts)
    if s is not None:
        exact.append((idx, s))

if not exact:
    for idx, row in df.iterrows():
        for side in ("red","blue"):
            if parts[0] in str(row.get(f"{side}_last_name","")).lower():
                exact.append((idx, side)); break

if not exact:
    st.info("Атлет не найден."); st.stop()

idxs    = list(dict.fromkeys([x[0] for x in exact]))
matches = df.loc[idxs].copy().sort_values(['date_start','round_rank'],ascending=[False,False])

# ─────────────────────────────────────────────────────────────────────────────
# СПИСОК НАЙДЕННЫХ АТЛЕТОВ
# ─────────────────────────────────────────────────────────────────────────────
athletes = {}
for idx, row in matches.iterrows():
    side = match_side(row, parts)
    if side is None:
        for s in ("red","blue"):
            if parts[0] in str(row.get(f"{s}_last_name","")).lower():
                side = s; break
    if side is None: continue
    fn  = str(row.get(f"{side}_full_name","")).strip()
    cde = str(row.get(f"{side}_nationality_code","")).upper()
    if fn and fn not in athletes:
        athletes[fn] = {"country": cde}

# ─────────────────────────────────────────────────────────────────────────────
# ЭКРАН ВЫБОРА — ВСЯ КАРТОЧКА КЛИКАБЕЛЬНА
# ─────────────────────────────────────────────────────────────────────────────
if len(athletes) > 1 and st.session_state.sel not in athletes:
    st.markdown(
        f"<p style='font-size:16px;color:#dde0ef;margin-bottom:16px'>"
        f"Найдено <b>{len(athletes)}</b> атлета — выберите:</p>",
        unsafe_allow_html=True
    )
    for aname, info in athletes.items():
        # st.button занимает всю ширину — это и есть кликабельная карточка
        label = f"{fl(info['country'])}  {aname}  ·  {cn(info['country'])}"
        if st.button(label, key=f"pick_{aname}", use_container_width=True):
            st.session_state.sel = aname
            st.rerun()
    st.stop()

# Выбор
if st.session_state.sel in athletes:
    chosen = st.session_state.sel
else:
    chosen = list(athletes.keys())[0]

chosen_low = chosen.lower().strip()

matches = matches[matches.apply(
    lambda r: str(r.get('red_full_name','')).lower().strip()==chosen_low or
              str(r.get('blue_full_name','')).lower().strip()==chosen_low,
    axis=1
)].copy()

if matches.empty: st.info("Матчи не найдены."); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ АТЛЕТА
# ─────────────────────────────────────────────────────────────────────────────
dob_list=[]; cnt_list=[]; final_name=""
for _,r in matches.iterrows():
    for side in ("red","blue"):
        if str(r.get(f"{side}_full_name","")).lower().strip()==chosen_low:
            final_name = str(r.get(f"{side}_full_name","")).strip()
            v = r.get(f"{side}_birth_date")
            if v and pd.notna(v): dob_list.append(str(v).strip())
            cnt_list.append(str(r.get(f"{side}_nationality_code","")).upper())
            break

raw_dob  = max(set(dob_list),key=dob_list.count) if dob_list else ""
dob_fmt  = fmt_dob(raw_dob)
age_str  = calc_age(raw_dob)
acountry = max(set(cnt_list),key=cnt_list.count) if cnt_list else ""

wins=losses=finals_c=0; win_seq=[]; recent_q=[]
for _,row in matches.iterrows():
    is_r = str(row.get('red_full_name','')).lower().strip()==chosen_low
    wid  = str(row.get('winner_athlete_id',''))
    mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
    won  = (wid==mid and wid!='')
    if won: wins+=1
    else:   losses+=1
    rc = str(row.get('round_code','')).upper()
    if rc in FINALS_CODES: finals_c+=1
    win_seq.append(won)
    if len(recent_q)<3:
        opp  = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
        ocnt = row['blue_nationality_code'] if is_r else row['red_nationality_code']
        msc  = ci(row.get('red_score') if is_r else row.get('blue_score'))
        osc  = ci(row.get('blue_score') if is_r else row.get('red_score'))
        rl   = ROUND_MAP.get(rc,(0,'?'))[1]
        recent_q.append({"opp":opp,"ofl":fl(ocnt),"res":"W" if won else "L",
                          "sc":f"{msc}:{osc}","rnd":rl})

total   = wins+losses
winrate = round(wins/total*100) if total else 0

s_type="win"; s_n=0
if win_seq:
    s_type = "win" if win_seq[0] else "loss"
    for w in win_seq:
        if (w and s_type=="win") or (not w and s_type=="loss"): s_n+=1
        else: break

main_cat=""
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
            final_name,acountry,age_str,wins,losses,finals_c,total,recent_q)
    qs = st.session_state.questions[qk]
    streak_h=""
    if s_n>=2:
        ico="🔥" if s_type=="win" else "❄️"
        lbl=f"Серия: {s_n} {'побед' if s_type=='win' else 'поражений'}"
        cls="sp-win" if s_type=="win" else "sp-loss"
        streak_h=f'<span class="streak-pill {cls}">{ico} {lbl}</span>'
    qhtml="".join(f'<div class="cam-q"><div class="cam-qn">Вопрос {i+1}</div>'
                  f'<div class="cam-qt">{q}</div></div>' for i,q in enumerate(qs))
    st.markdown(f"""
    <div class="cam-wrap">
      <div class="cam-name">{final_name}</div>
      <div class="cam-sub">{fl(acountry)} {cn(acountry)} · {dob_fmt} · {age_str}</div>
      {streak_h}
      <div class="cam-stats" style="margin-top:20px">
        <div class="cam-s"><div class="cam-n w">{total}</div><div class="cam-sl">Боёв</div></div>
        <div class="cam-s"><div class="cam-n g">{wins}</div><div class="cam-sl">Победы</div></div>
        <div class="cam-s"><div class="cam-n r">{losses}</div><div class="cam-sl">Пораж.</div></div>
        <div class="cam-s"><div class="cam-n y">{winrate}%</div><div class="cam-sl">% побед</div></div>
      </div>
      {qhtml}
    </div>
    """, unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🔄 Другие вопросы",use_container_width=True):
            st.session_state.questions[qk]=gen_q(
                final_name,acountry,age_str,wins,losses,finals_c,total,recent_q)
            st.rerun()
    with c2:
        if st.button("✖ Выйти",use_container_width=True):
            st.session_state.cam=False; st.rerun()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ПРОФИЛЬ
# ─────────────────────────────────────────────────────────────────────────────
if len(athletes)>1:
    if st.button("← Другой атлет"):
        st.session_state.sel=None; st.rerun()

streak_h=""
if s_n>=2:
    ico="🔥" if s_type=="win" else "❄️"
    lbl=f"Серия: {s_n} {'побед' if s_type=='win' else 'поражений'} подряд"
    cls="sp-win" if s_type=="win" else "sp-loss"
    streak_h=f'<div style="margin-top:10px"><span class="streak-pill {cls}">{ico} {lbl}</span></div>'

meta=[]
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

st.markdown(f"""
<div class="stat-grid">
  <div class="sc"><div class="sc-l">Боёв</div><div class="sc-v">{total}</div></div>
  <div class="sc"><div class="sc-l">Победы</div><div class="sc-v g">{wins}</div></div>
  <div class="sc"><div class="sc-l">Пораж.</div><div class="sc-v r">{losses}</div></div>
  <div class="sc"><div class="sc-l">% побед</div><div class="sc-v y">{winrate}%</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ВКЛАДКИ
# ─────────────────────────────────────────────────────────────────────────────
tab_m, tab_i, tab_w = st.tabs(["🥊 Матчи","🎙 Интервью","📖 Справка"])

# ═══════════════  МАТЧИ  ═══════════════
with tab_m:
    # ФИЛЬТР — st.radio с CSS-стилизацией под pill-кнопки (надёжнее любых хаков)
    cur_filter = st.radio(
        "Фильтр",
        ["Все","Победы","Поражения","Финалы"],
        index=["Все","Победы","Поражения","Финалы"].index(st.session_state.filter),
        horizontal=True,
        label_visibility="collapsed",
        key="filter_radio"
    )
    if cur_filter != st.session_state.filter:
        st.session_state.filter = cur_filter
        st.rerun()

    cur_year=None; shown=0
    for _,row in matches.iterrows():
        is_r = str(row.get('red_full_name','')).lower().strip()==chosen_low
        wid  = str(row.get('winner_athlete_id',''))
        mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
        won  = (wid==mid and wid!='')
        rc   = str(row.get('round_code','')).upper()

        if st.session_state.filter=="Победы"    and not won:          continue
        if st.session_state.filter=="Поражения" and won:              continue
        if st.session_state.filter=="Финалы"    and rc not in FINALS_CODES: continue

        msc  = ci(row.get('red_score')  if is_r else row.get('blue_score'))
        osc  = ci(row.get('blue_score') if is_r else row.get('red_score'))
        mpen = ci(row.get('red_penalties')  if is_r else row.get('blue_penalties'))
        open_= ci(row.get('blue_penalties') if is_r else row.get('red_penalties'))
        opp_full = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
        opp_last = str(row['blue_last_name'] if is_r else row['red_last_name']).strip()
        opp_cnt  = str(row['blue_nationality_code'] if is_r else row['red_nationality_code'])
        rl   = ROUND_MAP.get(rc,(0,rc))[1]
        cat  = get_cat(row.get('category_code',''))
        ds   = row['date_start'].strftime('%d.%m.%Y') if pd.notna(row['date_start']) else '??'
        yr   = row.get('year')
        ts   = fmt_time(row.get('fight_time',0))
        cls  = "win" if won else "loss"
        lbl  = "WIN" if won else "LOSS"

        if pd.notna(yr) and int(yr)!=cur_year:
            cur_year=int(yr)
            st.markdown(f'<div class="yr-sep">{cur_year}</div>',unsafe_allow_html=True)

        tags=f'<span class="tag rnd">{rl}</span><span class="tag">{cat}</span>'
        if mpen>0 or open_>0:
            tags+=f'<span class="tag pen">Пред. {mpen}/{open_}</span>'

        st.markdown(f"""
        <div class="mc {cls}">
          <div class="badge {cls}">
            <span class="bs {cls}">{msc}:{osc}</span>
            <span class="bl {cls}">{lbl}</span>
          </div>
          <div style="min-width:0;overflow:hidden">
            <div class="m-tour">{str(row.get('tournament_name',''))}</div>
            <div class="m-opp">
              <span style="font-size:16px">{fl(opp_cnt)}</span>
              <span class="m-cnt">{cn(opp_cnt)}</span>
              {opp_full}
            </div>
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
            st.session_state.prev_sq = ""
            st.session_state.sel     = None
            st.session_state.filter  = "Все"
            st.rerun()

        shown+=1

    if shown==0:
        st.markdown("<p style='color:#3d4058;text-align:center;padding:40px 0'>"
                    "Нет матчей по выбранному фильтру</p>", unsafe_allow_html=True)

# ═══════════════  ИНТЕРВЬЮ  ═══════════════
with tab_i:
    st.markdown(f"#### 🎙 Блиц-интервью — {final_name}")
    st.caption("Вопросы генерируются автоматически на основе данных карьеры")
    qk = f"q_{chosen}"
    if qk not in st.session_state.questions:
        st.session_state.questions[qk]=gen_q(
            final_name,acountry,age_str,wins,losses,finals_c,total,recent_q)
    qs=st.session_state.questions[qk]
    for i,q in enumerate(qs):
        st.markdown(f'<div class="q-card"><div class="q-num">{i+1}</div>'
                    f'<div class="q-text">{q}</div></div>',unsafe_allow_html=True)
    if st.button("🔄 Другие вопросы",key="rq"):
        st.session_state.questions[qk]=gen_q(
            final_name,acountry,age_str,wins,losses,finals_c,total,recent_q)
        st.rerun()
    st.markdown("---")
    st.markdown("#### 💾 Записать ответы")
    answers=[]
    for i,q in enumerate(qs):
        a=st.text_area(f"Ответ {i+1}",key=f"ans_{i}_{chosen}",
                       placeholder=f"«{q[:55]}…»",height=80)
        answers.append({"question":q,"answer":a})
    if st.button("💾 Сохранить интервью",type="primary",key="save"):
        filled=[x for x in answers if x["answer"].strip()]
        if filled:
            now=datetime.now().strftime("%d.%m.%Y %H:%M")
            save_ivw(final_name,now,answers)
            st.success(f"✅ Сохранено — {now}")
        else: st.warning("Заполните хотя бы один ответ.")
    past=load_ivw().get(final_name.strip().upper(),[])
    if past:
        st.markdown("---")
        st.markdown(f"#### 📂 Прошлые интервью — {final_name}")
        for ivw in reversed(past):
            with st.expander(f"🗓 {ivw['date']}"):
                for item in ivw['answers']:
                    if item.get('answer','').strip():
                        st.markdown(f"**В:** {item['question']}")
                        st.markdown(f"**О:** {item['answer']}")
                        st.markdown("---")

# ═══════════════  СПРАВКА  ═══════════════
with tab_w:
    st.markdown(f"#### 📖 Справка — {final_name}")
    wiki={}
    for variant in [final_name," ".join(reversed(final_name.split()))]:
        wiki=wiki_get(variant)
        if wiki: break
    if wiki:
        lng="Wikipedia RU" if wiki.get("lang")=="ru" else "Wikipedia EN"
        url_html=(f"<a class='wiki-link' href='{wiki['url']}' target='_blank'>"
                  f"→ Читать полностью на Wikipedia</a>") if wiki.get("url") else ""
        st.markdown(f'<div class="wiki-box"><div class="wiki-lbl">{lng} — {wiki["title"]}</div>'
                    f'<div class="wiki-text">{wiki["extract"]}</div>{url_html}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="wiki-box"><div class="wiki-lbl">Wikipedia</div>'
                    f'<div class="wiki-text" style="color:#3d4058">Статья о <b style="color:#606480">'
                    f'{final_name}</b> не найдена.</div></div>',unsafe_allow_html=True)
    ne=final_name.replace(' ','+'); nt=final_name.replace(' ','').lower()
    st.markdown(f'<div class="ref-grid">'
                f'<a class="ref-a" href="https://www.google.com/search?q={ne}+самбо" target="_blank">🔍 Google</a>'
                f'<a class="ref-a" href="https://ru.wikipedia.org/w/index.php?search={ne}" target="_blank">📖 Wikipedia</a>'
                f'<a class="ref-a" href="https://www.youtube.com/results?search_query={ne}+sambo" target="_blank">▶ YouTube</a>'
                f'<a class="ref-a" href="https://www.instagram.com/explore/tags/{nt}/" target="_blank">📷 Instagram</a>'
                f'<a class="ref-a" href="https://t.me/search?query={ne}" target="_blank">✈ Telegram</a>'
                f'</div>', unsafe_allow_html=True)

st.markdown("<hr style='border-color:#111318;margin-top:50px'>"
            "<p style='text-align:center;color:#1a1c28;font-size:11px'>FightGuru v5</p>",
            unsafe_allow_html=True)

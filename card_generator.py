# FIGHTGURU — Card Generator
# Публичный генератор карточек для спортсменов самбо
# Деплоить как отдельный Streamlit app: fightguru-cards.streamlit.app

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────────────────────────────────────
DB_FILE = "AllTournament.csv"

st.set_page_config(
    page_title="FightGuru Cards",
    page_icon="🥋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — тёмный минимализм, никакого лишнего интерфейса
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.stApp {
  background: #06070d !important;
  color: #dde0ef;
  font-family: 'Barlow', sans-serif !important;
}
.main .block-container {
  padding: 2rem 1.2rem 4rem !important;
  max-width: 600px !important;
}

/* Поиск */
div[data-testid="stTextInput"] input {
  background: #0f1020 !important;
  border: 1px solid #1e2135 !important;
  border-radius: 12px !important;
  color: #ffffff !important;
  font-size: 18px !important;
  padding: 14px 20px !important;
  font-family: 'Barlow', sans-serif !important;
}
div[data-testid="stTextInput"] input::placeholder {
  color: #30334a !important;
}

/* Radio */
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
  display: flex !important; flex-direction: row !important;
  gap: 8px !important; flex-wrap: wrap !important;
}
div[data-testid="stRadio"] > div > label {
  display: flex !important; align-items: center !important;
  background: #0f1020 !important; border: 1.5px solid #1e2135 !important;
  border-radius: 10px !important; padding: 8px 20px !important;
  font-size: 14px !important; font-weight: 700 !important;
  color: #52566e !important; cursor: pointer !important;
}
div[data-testid="stRadio"] > div > label[aria-checked="true"] {
  background: #c0392b !important; border-color: #c0392b !important;
  color: #fff !important;
}
div[data-testid="stRadio"] > div > label > div:first-child { display: none !important; }

/* Кнопки */
div[data-testid="stButton"] > button {
  background: #c0392b !important;
  border: none !important;
  border-radius: 12px !important;
  color: #fff !important;
  font-size: 18px !important;
  font-weight: 800 !important;
  font-family: 'Bebas Neue', sans-serif !important;
  letter-spacing: .14em !important;
  width: 100% !important;
  padding: 16px !important;
  margin-top: 8px !important;
  transition: all .15s !important;
}
div[data-testid="stButton"] > button:hover {
  background: #a93226 !important;
  transform: translateY(-1px) !important;
}

/* Выбор атлета */
div[data-testid="stButton"] > button.pick {
  background: #0f1020 !important;
  border: 1px solid #1e2135 !important;
  color: #8890b8 !important;
  font-size: 15px !important;
  font-family: 'Barlow', sans-serif !important;
  letter-spacing: 0 !important;
  text-align: left !important;
  padding: 12px 18px !important;
}

#MainMenu, footer, header { visibility: hidden; }
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
    "ALG":"🇩🇿","PAK":"🇵🇰","LUX":"🇱🇺","MLT":"🇲🇹","MON":"🇲🇨","USA":"🇺🇸",
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
DISC_MAP = {'SAM':'Спортивное самбо','CSM':'Боевое самбо','BSM':'Пляжное самбо'}

# ─────────────────────────────────────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────────────────────────────────────
def fl(code):  return FLAGS.get(str(code).upper().strip(), "🌍")
def cn(code):
    c = str(code).upper().strip()
    return COUNTRIES.get(c, c)

def ci(v, d=0):
    try: return int(float(v)) if pd.notna(v) else d
    except: return d

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

def get_disc(cat_code):
    c = str(cat_code).upper()
    if 'BSM' in c: return 'BSM'
    if 'CSM' in c: return 'CSM'
    if 'SAM' in c: return 'SAM'
    return None

def age_word(n):
    if 11 <= n % 100 <= 14: return f"{n} лет"
    r = n % 10
    if r == 1:      return f"{n} год"
    if 2 <= r <= 4: return f"{n} года"
    return f"{n} лет"

def calc_age(raw):
    try:
        n = (datetime.now() - datetime.strptime(raw, '%Y-%m-%d')).days // 365
        return age_word(n)
    except: return ""

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    if not __import__('os').path.exists(DB_FILE): return None
    try:
        df = pd.read_csv(DB_FILE, low_memory=False)
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
    except: return None

df = load_data()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for k, v in [('sq',''),('sel',None),('card_html',''),('card_css',''),('card_body',''),('show_card',False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# ЕСЛИ НУЖНО ПОКАЗАТЬ КАРТОЧКУ — показываем ТОЛЬКО её, весь UI скрыт
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.show_card and st.session_state.card_html:
    # Скрываем Streamlit UI — показываем только карточку
    st.markdown("""
    <style>
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    footer { display: none !important; }
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    .stApp { background: #06070d !important; }
    </style>
    """, unsafe_allow_html=True)

    # Вычисляем ширину экрана через JS и показываем карточку
    # масштабированную точно под экран — без обрезки по бокам
    card_embed = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
        background: #06070d;
        overflow: hidden;
        width: 100%;
    }}
    #wrap {{
        width: 1080px;
        transform-origin: top left;
        position: absolute;
        top: 0; left: 0;
    }}
    {st.session_state.card_css}
    </style>
    </head>
    <body>
    <div id="wrap">
    {st.session_state.card_body}
    </div>
    <script>
    function scale() {{
        var w = window.innerWidth || document.documentElement.clientWidth;
        var s = w / 1080;
        var cardH = Math.round(1920 * s);
        var el = document.getElementById('wrap');
        el.style.transform = 'scale(' + s + ')';
        // Сообщаем Streamlit реальную высоту карточки
        window.parent.postMessage({{
            type: 'streamlit:setFrameHeight',
            height: cardH
        }}, '*');
        document.documentElement.style.height = cardH + 'px';
        document.body.style.height = cardH + 'px';
    }}
    // Запускаем сразу и после загрузки шрифтов
    scale();
    document.fonts.ready.then(scale);
    window.addEventListener('resize', scale);
    </script>
    </body>
    </html>
    """

    components.html(card_embed, height=700, scrolling=False)

    st.markdown("<div style='height:8px;background:#06070d'></div>",
                unsafe_allow_html=True)

    # Кнопка назад
    if st.button("← Другой атлет"):
        st.session_state.show_card = False
        st.rerun()

    st.markdown("""
    <div style='background:#0a0b14;border:1px solid #1e2135;border-radius:12px;
    padding:14px 18px;margin-top:8px'>
    <div style='font-family:Bebas Neue,sans-serif;font-size:16px;letter-spacing:.12em;
    color:#c0392b;margin-bottom:8px'>КАК СОХРАНИТЬ КАРТОЧКУ</div>
    <div style='font-size:13px;color:#52566e;line-height:2;font-family:Barlow,sans-serif'>
    📱 <b style='color:#8890b8'>iPhone:</b> Боковая + громкость ↑ — скриншот всего экрана<br>
    📱 <b style='color:#8890b8'>Android:</b> Питание + громкость ↓<br>
    💻 <b style='color:#8890b8'>Компьютер:</b> Скачай HTML кнопкой ниже → Chrome → PDF
    </div>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ОСНОВНОЙ UI — ПОИСК
# ─────────────────────────────────────────────────────────────────────────────
if df is None:
    st.error("База данных не найдена."); st.stop()

# Заголовок
st.markdown("""
<div style='text-align:center;padding:32px 0 24px'>
  <div style='font-family:Bebas Neue,sans-serif;font-size:52px;
  letter-spacing:.22em;color:#c0392b;line-height:1'>FIGHTGURU</div>
  <div style='font-family:Barlow,sans-serif;font-size:14px;font-weight:700;
  letter-spacing:.18em;text-transform:uppercase;color:#30334a;margin-top:4px'>
  Sambo Stats Card Generator</div>
</div>
""", unsafe_allow_html=True)

# Поиск
def _on_change():
    st.session_state.sq    = st.session_state.get("_sq","").strip()
    st.session_state.sel   = None
    st.session_state.show_card = False
    st.session_state.card_html = ""

st.text_input("", value=st.session_state.sq, key="_sq",
              placeholder="🔍  Введи свою фамилию",
              label_visibility="collapsed", on_change=_on_change)

sq = st.session_state.sq.strip()

if not sq:
    st.markdown("""
    <div style='text-align:center;padding:40px 0'>
      <div style='font-size:40px;margin-bottom:12px'>🥋</div>
      <div style='font-family:Bebas Neue,sans-serif;font-size:22px;letter-spacing:.14em;
      color:#1e2135'>ВВЕДИ ФАМИЛИЮ — ПОЛУЧИ КАРТОЧКУ</div>
      <div style='font-size:13px;color:#30334a;margin-top:8px;font-family:Barlow,sans-serif'>
      Данные FIAS · турниры 2021–2026</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ПОИСК АТЛЕТА
# ─────────────────────────────────────────────────────────────────────────────
parts = sq.lower().split()

def match_side(row, pts):
    for side in ("red","blue"):
        last  = str(row.get(f"{side}_last_name","")).lower().strip()
        first = str(row.get(f"{side}_first_name","")).lower().strip()
        if len(pts) == 1:
            if pts[0] == last: return side
        else:
            if (pts[0]==last and first.startswith(pts[1])) or \
               (pts[1]==last and first.startswith(pts[0])): return side
    return None

exact = []
for idx, row in df.iterrows():
    s = match_side(row, parts)
    if s: exact.append((idx, s))

if not exact:
    for idx, row in df.iterrows():
        for side in ("red","blue"):
            if parts[0] in str(row.get(f"{side}_last_name","")).lower():
                exact.append((idx, side)); break

if not exact:
    st.markdown(f"""
    <div style='text-align:center;padding:30px 0'>
      <div style='font-size:32px;margin-bottom:10px'>😔</div>
      <div style='font-family:Bebas Neue,sans-serif;font-size:20px;letter-spacing:.12em;
      color:#52566e'>Атлет не найден в базе FIAS</div>
      <div style='font-size:12px;color:#30334a;margin-top:8px;font-family:Barlow,sans-serif'>
      База содержит участников официальных турниров FIAS 2021–2026
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

idxs    = list(dict.fromkeys([x[0] for x in exact]))
matches = df.loc[idxs].copy().sort_values(
    ['date_start','round_rank'], ascending=[False,False]
)

# Собираем список найденных атлетов
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

# Выбор атлета если несколько
if len(athletes) > 1 and st.session_state.sel not in athletes:
    st.markdown(f"""
    <div style='font-family:Bebas Neue,sans-serif;font-size:18px;letter-spacing:.12em;
    color:#52566e;margin-bottom:12px'>НАЙДЕНО {len(athletes)} АТЛЕТА — ВЫБЕРИ СЕБЯ:</div>
    """, unsafe_allow_html=True)
    for aname, info in athletes.items():
        label = f"{fl(info['country'])}  {aname}  ·  {cn(info['country'])}"
        if st.button(label, key=f"pick_{aname}", use_container_width=True):
            st.session_state.sel = aname
            st.rerun()
    st.stop()

chosen = st.session_state.sel if st.session_state.sel in athletes else list(athletes.keys())[0]
chosen_low = chosen.lower().strip()

matches = matches[matches.apply(
    lambda r: str(r.get('red_full_name','')).lower().strip() == chosen_low or
              str(r.get('blue_full_name','')).lower().strip() == chosen_low,
    axis=1
)].copy()

if matches.empty:
    st.info("Матчи не найдены."); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ АТЛЕТА
# ─────────────────────────────────────────────────────────────────────────────
dob_list = []; cnt_list = []; final_name = ""
for _, r in matches.iterrows():
    for side in ("red","blue"):
        if str(r.get(f"{side}_full_name","")).lower().strip() == chosen_low:
            final_name = str(r.get(f"{side}_full_name","")).strip()
            v = r.get(f"{side}_birth_date")
            if v and pd.notna(v): dob_list.append(str(v).strip())
            cnt_list.append(str(r.get(f"{side}_nationality_code","")).upper())
            break

raw_dob  = max(set(dob_list), key=dob_list.count) if dob_list else ""
age_str  = calc_age(raw_dob)
acountry = max(set(cnt_list), key=cnt_list.count) if cnt_list else ""

# ─────────────────────────────────────────────────────────────────────────────
# ВЫБОР ДИСЦИПЛИНЫ
# ─────────────────────────────────────────────────────────────────────────────
avail_discs = {}
for _, row in matches.iterrows():
    cc   = str(row.get('category_code', '')).upper()
    disc = get_disc(cc)
    if disc and disc not in avail_discs:
        avail_discs[disc] = DISC_MAP.get(disc, disc)

if len(avail_discs) > 1:
    disc_options  = list(avail_discs.values())
    disc_keys     = list(avail_discs.keys())
    sel_disc_name = st.radio("Дисциплина:", disc_options, horizontal=True, key="disc_radio")
    sel_disc      = disc_keys[disc_options.index(sel_disc_name)]
elif len(avail_discs) == 1:
    sel_disc = list(avail_discs.keys())[0]
else:
    sel_disc = None

disc_matches = matches[
    matches['category_code'].str.upper().str.contains(sel_disc, na=False)
].copy() if sel_disc else matches.copy()

if disc_matches.empty:
    st.warning("Нет матчей."); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# СТАТИСТИКА
# ─────────────────────────────────────────────────────────────────────────────
disc_wins = disc_losses = disc_finals = 0
for _, row in disc_matches.iterrows():
    is_r = str(row.get('red_full_name','')).lower().strip() == chosen_low
    wid  = str(row.get('winner_athlete_id',''))
    mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
    won  = (wid == mid and wid != '')
    if won: disc_wins += 1
    else:   disc_losses += 1
    if str(row.get('round_code','')).upper() in FINALS_CODES: disc_finals += 1

disc_total   = disc_wins + disc_losses
disc_winrate = round(disc_wins / disc_total * 100) if disc_total else 0

# Категория — из последнего боя
disc_cat_raw = str(disc_matches.iloc[0]['category_code']).upper()
disc_cat     = get_cat(disc_matches.iloc[0]['category_code'])

# Доп. статистика
fastest = "—"
try:
    win_times = []
    for _, row in disc_matches.iterrows():
        is_r = str(row.get('red_full_name','')).lower().strip() == chosen_low
        wid  = str(row.get('winner_athlete_id',''))
        mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
        if wid == mid and wid != '':
            try:
                ms = int(float(row.get('fight_time', 0)))
                if ms > 0: win_times.append(ms)
            except: pass
    if win_times:
        ts = min(win_times) // 1000
        fastest = f"{ts//60}:{ts%60:02d}"
except: pass

avg_score = "—"
try:
    scores = []
    for _, row in disc_matches.iterrows():
        is_r = str(row.get('red_full_name','')).lower().strip() == chosen_low
        sc = ci(row.get('red_score') if is_r else row.get('blue_score'))
        scores.append(sc)
    if scores: avg_score = f"{sum(scores)/len(scores):.1f}"
except: pass

last_title_year = "—"
try:
    for _, row in disc_matches.iterrows():
        rc = str(row.get('round_code', '')).upper()
        if rc in FINALS_CODES:
            ds = row.get('date_start')
            if pd.notna(ds):
                last_title_year = str(pd.to_datetime(ds).year)
                break
except: pass

# Streak
_streak_n = 0
_win_seq  = []
for _, row in disc_matches.iterrows():
    is_r = str(row.get('red_full_name','')).lower().strip() == chosen_low
    wid  = str(row.get('winner_athlete_id',''))
    mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
    _win_seq.append(wid == mid and wid != '')
if _win_seq and _win_seq[0]:
    for w in _win_seq:
        if w: _streak_n += 1
        else: break

# Данные для карточки
_is_combat  = 'CSM' in disc_cat_raw
_fight_word = "Боёв" if _is_combat else "Схваток"
_wins       = disc_wins
_losses     = disc_losses
_total      = disc_total
_winrate    = disc_winrate
_finals_c   = disc_finals
_main_cat   = disc_cat

fname_parts  = final_name.strip().split()
first_n      = fname_parts[0] if len(fname_parts) >= 2 else ""
last_n       = " ".join(fname_parts[1:]) if len(fname_parts) >= 2 else final_name
_last_n_main = last_n[:-2] if len(last_n) >= 2 else last_n
_last_n_end  = last_n[-2:] if len(last_n) >= 2 else ""
flag_emoji   = fl(acountry)
country_name = cn(acountry)

# Streak HTML
_streak_block = (
    '<div class="streak">'
    '<div class="s-dots">'
    + "".join('<div class="s-dot"></div>' for _ in range(min(_streak_n, 8)))
    + '</div>'
    f'<div class="s-txt">{_streak_n} WIN STREAK &#128293;</div>'
    '</div>'
) if _streak_n >= 2 else '<div class="streak-empty"></div>'

# ─────────────────────────────────────────────────────────────────────────────
# ЛОГОТИП — грузим logo.png из репо, кодируем в base64
# ─────────────────────────────────────────────────────────────────────────────
import base64 as _b64, glob as _glob
_logo_b64 = ""
_logo_paths = ["logo.png",
               __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), "logo.png"),
               __import__('os').path.join(__import__('os').getcwd(), "logo.png")]
for _lp in _logo_paths:
    if __import__('os').path.exists(_lp):
        with open(_lp, "rb") as _lf: _logo_b64 = _b64.b64encode(_lf.read()).decode()
        break
if not _logo_b64:
    _found = _glob.glob("**/logo.png", recursive=True)
    if _found:
        with open(_found[0], "rb") as _lf: _logo_b64 = _b64.b64encode(_lf.read()).decode()

_logo_src = f"data:image/png;base64,{_logo_b64}" if _logo_b64 else ""
_logo_tag = (f'<img src="{_logo_src}" class="logo-img">' if _logo_src
             else '<div class="logo-ph">FG</div>')
_logo_tag_topbar = (f'<img src="{_logo_src}" class="topbar-logo">' if _logo_src
                    else '<div class="topbar-logo-ph">FG</div>')

# ─────────────────────────────────────────────────────────────────────────────
# ПРЕВЬЮ МИНИ-КАРТОЧКИ В UI (чтобы атлет видел что получится)
# ─────────────────────────────────────────────────────────────────────────────
if len(athletes) > 1:
    if st.button("← Другой атлет", key="back_btn"):
        st.session_state.sel = None; st.rerun()

st.markdown(f"""
<div style='background:#0a0b14;border:1px solid #1e2135;border-radius:14px;
padding:16px 20px;margin:16px 0;display:flex;align-items:center;gap:14px'>
  <div style='font-size:32px'>{flag_emoji}</div>
  <div>
    <div style='font-family:Bebas Neue,sans-serif;font-size:28px;letter-spacing:.06em;
    color:#ffffff;line-height:1'>{final_name}</div>
    <div style='font-family:Barlow,sans-serif;font-size:13px;font-weight:700;
    color:#52566e;text-transform:uppercase;letter-spacing:.1em;margin-top:3px'>
    {country_name} · {_main_cat} · {_total} боёв · {_wins}W {_losses}L</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# КНОПКА — ОТКРЫТЬ КАРТОЧКУ
# ─────────────────────────────────────────────────────────────────────────────

# Генерируем HTML карточки
card_html = f"""<div class="card">
  <div class="photo-col">
    <div class="photo-icon">
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4zm0 0"/>
        <path d="M9 3L7.17 5H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.17L15 3H9zm3 15a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"/>
      </svg>
    </div>
    <div class="photo-lbl">Место<br>для<br>фото</div>
  </div>
  <div class="info-col">
    <div class="topbar">
      <div class="topbar-left">
        {_logo_tag_topbar}
        <div>
          <div class="topbar-brand">FIGHTGURU</div>
          <div class="topbar-sub">Sambo Stats Portal</div>
        </div>
      </div>
      <div class="topbar-right">Официальная<br>статистика FIAS</div>
    </div>
    <div class="name-block">
      <div class="f-disc">{_main_cat}</div>
      <div class="f-first">{first_n}</div>
      <div class="f-last">{_last_n_main}<span class="red">{_last_n_end}</span></div>
      <div class="f-meta">
        <span class="f-flag">{flag_emoji}</span>
        <span class="f-cname">{country_name}</span>
        <span class="f-age">{age_str}</span>
      </div>
    </div>
    <div class="record">
      <div class="rec"><div class="rv n">{_total}</div><div class="rl">{_fight_word}</div></div>
      <div class="rec"><div class="rv g">{_wins}</div><div class="rl">Победы</div></div>
      <div class="rec"><div class="rv r">{_losses}</div><div class="rl">Пораж.</div></div>
      <div class="rec"><div class="rv y">{_winrate}%</div><div class="rl">% побед</div></div>
    </div>
    <div class="pbar">
      <div class="pbar-row">
        <span class="pbar-wins">{_wins} побед из {_total}</span>
        <span class="pbar-src">FIAS · 2021–2026</span>
      </div>
      <div class="pbar-track"><div class="pbar-fill"></div></div>
    </div>
    {_streak_block}
    <div class="extra">
      <div class="ec"><div class="ev r">{fastest}</div><div class="el">Быстрейшая победа</div></div>
      <div class="ec"><div class="ev g">{_finals_c}</div><div class="el">Финалы в карьере</div></div>
      <div class="ec"><div class="ev w">{avg_score}</div><div class="el">Ср. балл / бой</div></div>
      <div class="ec"><div class="ev y">{last_title_year}</div><div class="el">Последний финал</div></div>
    </div>
    <div class="footer">
      <div class="footer-left">
        {_logo_tag}
        <div>
          <div class="brand">FIGHTGURU</div>
          <div class="brand-sub">@guru.fight</div>
        </div>
      </div>
      <div class="socials">
        <div class="soc">
          <div class="soc-icon ig">
            <svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
          </div>
          <div class="soc-handle ig">@guru.fight</div>
        </div>
        <div class="soc">
          <div class="soc-icon vk">
            <svg viewBox="0 0 24 24"><path d="M15.684 0H8.316C1.592 0 0 1.592 0 8.316v7.368C0 22.408 1.592 24 8.316 24h7.368C22.408 24 24 22.408 24 15.684V8.316C24 1.592 22.408 0 15.684 0zm3.692 17.123h-1.744c-.66 0-.864-.525-2.05-1.727-1.033-1-1.49-1.135-1.744-1.135-.356 0-.458.102-.458.593v1.575c0 .424-.135.678-1.253.678-1.846 0-3.896-1.118-5.335-3.202C4.624 10.857 4.03 8.57 4.03 8.096c0-.254.102-.491.593-.491h1.744c.44 0 .61.203.78.677.863 2.49 2.303 4.675 2.896 4.675.22 0 .322-.102.322-.66V9.721c-.068-1.186-.695-1.287-.695-1.71 0-.204.17-.407.44-.407h2.743c.372 0 .508.203.508.643v3.473c0 .372.17.508.271.508.22 0 .407-.136.813-.542 1.27-1.422 2.168-3.608 2.168-3.608.119-.254.322-.491.763-.491h1.744c.525 0 .644.27.525.643-.22 1.017-2.354 4.031-2.354 4.031-.186.305-.254.44 0 .78.186.254.796.779 1.203 1.253.745.847 1.32 1.558 1.473 2.05.17.491-.085.745-.576.745z"/></svg>
          </div>
          <div class="soc-handle vk">fightguru</div>
        </div>
        <div class="soc">
          <div class="soc-icon yt">
            <svg viewBox="0 0 24 24"><path d="M23.495 6.205a3.007 3.007 0 0 0-2.088-2.088c-1.87-.501-9.396-.501-9.396-.501s-7.507-.01-9.396.501A3.007 3.007 0 0 0 .527 6.205a31.247 31.247 0 0 0-.522 5.805 31.247 31.247 0 0 0 .522 5.783 3.007 3.007 0 0 0 2.088 2.088c1.868.502 9.396.502 9.396.502s7.506 0 9.396-.502a3.007 3.007 0 0 0 2.088-2.088 31.247 31.247 0 0 0 .5-5.783 31.247 31.247 0 0 0-.5-5.805zM9.609 15.601V8.408l6.264 3.602z"/></svg>
          </div>
          <div class="soc-handle yt">fightguru</div>
        </div>
        <div class="soc">
          <div class="soc-icon tt">
            <svg viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.28 6.28 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.78 1.52V6.75a4.85 4.85 0 01-1.01-.06z"/></svg>
          </div>
          <div class="soc-handle tt">fight.guru</div>
        </div>
      </div>
    </div>
  </div>
</div>"""

# CSS карточки — идентичен app_guru.py
card_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;700;800&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
.card{{width:1080px;height:1920px;background:#06070d;display:flex;flex-direction:row;overflow:hidden;}}
.photo-col{{width:360px;min-width:360px;height:1920px;flex-shrink:0;background:#0a0b14;border-right:6px solid #c0392b;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;}}
.photo-icon{{width:120px;height:120px;border-radius:50%;border:3px dashed #1a1d2e;display:flex;align-items:center;justify-content:center;opacity:.18;}}
.photo-icon svg{{width:56px;height:56px;fill:#444;}}
.photo-lbl{{font-family:'Bebas Neue',sans-serif;font-size:20px;letter-spacing:.26em;color:#1a1d2e;text-align:center;line-height:2;}}
.info-col{{width:720px;height:1920px;display:flex;flex-direction:column;}}
.name-block{{height:564px;flex-shrink:0;display:flex;flex-direction:column;justify-content:flex-end;padding:0 52px 44px 52px;border-bottom:4px solid #c0392b;}}
.f-disc{{font-family:'Bebas Neue',sans-serif;font-size:32px;letter-spacing:.28em;color:#c0392b;margin-bottom:20px;line-height:1;}}
.f-first{{font-family:'Barlow',sans-serif;font-size:38px;font-weight:800;text-transform:uppercase;letter-spacing:.22em;color:#ffffff;line-height:1;margin-bottom:6px;}}
.f-last{{font-family:'Bebas Neue',sans-serif;font-size:148px;color:#ffffff;line-height:.9;letter-spacing:.03em;white-space:nowrap;overflow:hidden;text-overflow:clip;margin-bottom:34px;}}
.f-last .red{{color:#c0392b;}}
.f-meta{{display:flex;align-items:center;gap:16px;flex-wrap:wrap;}}
.f-flag{{font-size:44px;line-height:1;flex-shrink:0;}}
.f-cname{{font-family:'Barlow',sans-serif;font-size:28px;font-weight:700;text-transform:uppercase;letter-spacing:.14em;color:#8890b8;}}
.f-age{{font-family:'Bebas Neue',sans-serif;font-size:34px;color:#c0392b;letter-spacing:.08em;}}
.record{{height:364px;flex-shrink:0;display:grid;grid-template-columns:repeat(4,1fr);border-bottom:2px solid #0f1020;}}
.rec{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;border-right:2px solid #0f1020;}}
.rec:last-child{{border-right:none;}}
.rv{{font-family:'Bebas Neue',sans-serif;font-size:120px;line-height:1;letter-spacing:.02em;}}
.rv.n{{color:#ffffff;}}.rv.g{{color:#2ecc71;}}.rv.r{{color:#c0392b;}}.rv.y{{color:#f1c40f;}}
.rl{{font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:.22em;color:#6870a0;}}
.pbar{{height:115px;flex-shrink:0;display:flex;flex-direction:column;justify-content:center;padding:0 52px;gap:14px;border-bottom:2px solid #0f1020;}}
.pbar-row{{display:flex;justify-content:space-between;align-items:baseline;}}
.pbar-wins{{font-family:'Bebas Neue',sans-serif;font-size:28px;letter-spacing:.1em;color:#2ecc71;}}
.pbar-src{{font-family:'Barlow',sans-serif;font-size:18px;font-weight:500;color:#3a3d54;letter-spacing:.1em;}}
.pbar-track{{height:6px;background:#0f1020;border-radius:3px;overflow:hidden;}}
.pbar-fill{{height:100%;background:#2ecc71;border-radius:3px;width:{_winrate}%;}}
.streak{{height:134px;flex-shrink:0;background:#040d07;border-bottom:2px solid #091509;display:flex;align-items:center;padding:0 52px;gap:18px;}}
.streak-empty{{height:134px;flex-shrink:0;border-bottom:2px solid #0f1020;}}
.s-dots{{display:flex;gap:8px;align-items:center;}}
.s-dot{{width:14px;height:14px;border-radius:50%;background:#2ecc71;flex-shrink:0;}}
.s-txt{{font-family:'Bebas Neue',sans-serif;font-size:52px;letter-spacing:.12em;color:#2ecc71;line-height:1;}}
.extra{{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:2px;background:#0a0b14;flex:1;}}
.ec{{background:#06070d;display:flex;flex-direction:column;justify-content:center;padding:0 52px;gap:10px;}}
.ev{{font-family:'Bebas Neue',sans-serif;font-size:92px;line-height:1;letter-spacing:.02em;}}
.ev.r{{color:#c0392b;}}.ev.g{{color:#2ecc71;}}.ev.w{{color:#ffffff;}}.ev.y{{color:#f1c40f;}}
.el{{font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:.22em;color:#6870a0;}}
.topbar{{height:88px;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:0 52px;border-bottom:2px solid #0f1020;background:#08090f;}}
.topbar-left{{display:flex;align-items:center;gap:18px;}}
.topbar-logo{{width:60px;height:60px;border-radius:50%;object-fit:cover;flex-shrink:0;}}
.topbar-logo-ph{{width:60px;height:60px;border-radius:50%;background:#c0392b;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-family:'Bebas Neue',sans-serif;font-size:18px;color:#fff;letter-spacing:.04em;}}
.topbar-brand{{font-family:'Bebas Neue',sans-serif;font-size:38px;letter-spacing:.2em;color:#c0392b;line-height:1;}}
.topbar-sub{{font-family:'Barlow',sans-serif;font-size:16px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#1e2030;margin-top:4px;}}
.topbar-right{{font-family:'Barlow',sans-serif;font-size:18px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#1e2030;text-align:right;line-height:2;}}
.footer{{height:192px;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:0 52px;border-top:3px solid #0f1020;background:#08090f;}}
.footer-left{{display:flex;align-items:center;gap:20px;}}
.logo-img{{width:80px;height:80px;border-radius:50%;object-fit:cover;flex-shrink:0;}}
.logo-ph{{width:80px;height:80px;border-radius:50%;background:#c0392b;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-family:'Bebas Neue',sans-serif;font-size:24px;color:#fff;letter-spacing:.04em;}}
.brand{{font-family:'Bebas Neue',sans-serif;font-size:44px;letter-spacing:.22em;color:#c0392b;line-height:1;}}
.brand-sub{{font-family:'Barlow',sans-serif;font-size:16px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#30334a;margin-top:4px;}}
.socials{{display:flex;align-items:center;gap:22px;}}
.soc{{display:flex;flex-direction:column;align-items:center;gap:8px;}}
.soc-icon{{width:52px;height:52px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
.soc-icon.ig{{background:#833ab4;}}
.soc-icon.vk{{background:#0077ff;}}
.soc-icon.yt{{background:#ff0000;}}
.soc-icon.tt{{background:#010101;border:1px solid #2a2a2a;}}
.soc-icon svg{{width:28px;height:28px;fill:#fff;}}
.soc-handle{{font-family:'Barlow',sans-serif;font-size:18px;font-weight:800;letter-spacing:.02em;white-space:nowrap;}}
.soc-handle.ig{{color:#c77dff;}}
.soc-handle.vk{{color:#60a5ff;}}
.soc-handle.yt{{color:#ff6b6b;}}
.soc-handle.tt{{color:#ffffff;}}
</style>
"""

# Полная HTML страница — используется и для открытия в новой вкладке и для скачивания
full_html_page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;700;800&display=swap" rel="stylesheet">
<title>{final_name} - FightGuru</title>
{card_css}
<style>
html, body {{
    margin: 0; padding: 0;
    background: #06070d;
    width: 100vw;
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
}}
.scale-wrap {{
    width: 1080px;
    transform-origin: top left;
}}
</style>
</head>
<body>
<div class="scale-wrap">
{card_html}
</div>
<script>
function resize() {{
    var wrap = document.querySelector('.scale-wrap');
    var scale = window.innerWidth / 1080;
    wrap.style.transform = 'scale(' + scale + ')';
    wrap.style.height = (1920 * scale) + 'px';
    document.body.style.height = (1920 * scale) + 'px';
}}
resize();
window.addEventListener('resize', resize);
</script>
</body>
</html>"""

if st.button("📱 ОТКРЫТЬ КАРТОЧКУ", key="open_card"):
    st.session_state.card_css  = card_css
    st.session_state.card_body = card_html
    st.session_state.card_html = full_html_page  # для скачивания
    st.session_state.show_card = True
    st.rerun()

st.download_button(
    label="💻 Скачать HTML (для Фотошопа)",
    data=full_html_page.encode('utf-8'),
    file_name=f"{final_name.replace(' ','_')}_fightguru.html",
    mime="text/html",
    use_container_width=True,
)

st.markdown("""
<div style='margin-top:16px;padding:14px 18px;background:#0a0b14;
border:1px solid #1e2135;border-radius:12px;font-family:Barlow,sans-serif'>
<div style='font-family:Bebas Neue,sans-serif;font-size:16px;letter-spacing:.14em;
color:#52566e;margin-bottom:8px'>КАК СОХРАНИТЬ</div>
<div style='font-size:13px;color:#30334a;line-height:2'>
📱 <b style='color:#52566e'>Телефон:</b> Нажми «Открыть карточку» → сделай скриншот<br>
💻 <b style='color:#52566e'>Компьютер:</b> Скачай HTML → открой в Chrome → ⌘P → PDF → Фотошоп
</div>
</div>
""", unsafe_allow_html=True)

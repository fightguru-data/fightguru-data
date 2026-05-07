"""
FIGHTGURU Bot v3
- Богатая карточка атлета: дисциплина, серия, доп.статы
- Кириллица через транслитерацию
- Inline-кнопки выбора атлета
- Соцсети 2x2 кнопки
"""

import os, sys, time, logging
import pandas as pd
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [BOT] %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГ
# ─────────────────────────────────────────────────────────────────────────────
def get_token():
    t = os.environ.get("BOT_TOKEN", "")
    if t: return t
    p = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(p):
        try:
            with open(p) as f:
                for line in f:
                    if "bot_token" in line:
                        return line.split("=")[1].strip().strip('"\'')
        except: pass
    return ""

TOKEN   = get_token()
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AllTournament.csv")

if not TOKEN:
    log.error("BOT_TOKEN не найден!"); sys.exit(1)
if not os.path.exists(DB_FILE):
    log.error(f"База не найдена: {DB_FILE}"); sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# СПРАВОЧНИКИ
# ─────────────────────────────────────────────────────────────────────────────
RMAP = {
    'FIN':'Финал','FNL':'Финал','SFL':'1/2','QFL':'1/4',
    'R16':'1/8','R32':'1/16','R64':'1/32','R128':'1/64',
    'BR1':'Бронза','BR2':'Бронза','RP1':'Утешит.','RP2':'Утешит.',
}
FINALS = {'FIN','FNL'}

FLAGS = {
    "RUS":"🇷🇺","BLR":"🇧🇾","KAZ":"🇰🇿","UZB":"🇺🇿","KGZ":"🇰🇬","MGL":"🇲🇳",
    "GEO":"🇬🇪","ARM":"🇦🇲","AZE":"🇦🇿","TJK":"🇹🇯","TKM":"🇹🇲","AIN":"🏳️",
    "FRA":"🇫🇷","SRB":"🇷🇸","USA":"🇺🇸","UKR":"🇺🇦","BUL":"🇧🇬","CRO":"🇭🇷",
    "MKD":"🇲🇰","ROU":"🇷🇴","ITA":"🇮🇹","TUR":"🇹🇷","LAT":"🇱🇻","ISR":"🇮🇱",
    "GBR":"🇬🇧","GER":"🇩🇪","NED":"🇳🇱","GRE":"🇬🇷","LTU":"🇱🇹","MDA":"🇲🇩",
    "SVK":"🇸🇰","CZE":"🇨🇿","HUN":"🇭🇺","POL":"🇵🇱","SWE":"🇸🇪","ESP":"🇪🇸",
    "POR":"🇵🇹","JPN":"🇯🇵","KOR":"🇰🇷","CHN":"🇨🇳","BEL":"🇧🇪","AUT":"🇦🇹",
    "SUI":"🇨🇭","NOR":"🇳🇴","DEN":"🇩🇰","FIN":"🇫🇮","EST":"🇪🇪","IRN":"🇮🇷",
    "IND":"🇮🇳","MAS":"🇲🇾","THA":"🇹🇭","BRA":"🇧🇷","ARG":"🇦🇷","MEX":"🇲🇽",
    "CAN":"🇨🇦","AUS":"🇦🇺","MAR":"🇲🇦","EGY":"🇪🇬","ALB":"🇦🇱","BIH":"🇧🇦",
    "MNE":"🇲🇪","KOS":"🇽🇰","SLO":"🇸🇮","KWT":"🇰🇼","VIE":"🇻🇳","COL":"🇨🇴",
    "NZL":"🇳🇿","TUN":"🇹🇳","ALG":"🇩🇿","PAK":"🇵🇰","PHI":"🇵🇭",
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
    "KOR":"Корея","CHN":"Китай","BEL":"Бельгия","AUT":"Австрия",
    "SUI":"Швейцария","NOR":"Норвегия","DEN":"Дания","FIN":"Финляндия",
    "EST":"Эстония","IRN":"Иран","IND":"Индия","MAS":"Малайзия",
    "BRA":"Бразилия","ARG":"Аргентина","MEX":"Мексика","CAN":"Канада",
    "AUS":"Австралия","MAR":"Марокко","EGY":"Египет","ALB":"Албания",
    "BIH":"Босния","MNE":"Черногория","KOS":"Косово","SLO":"Словения",
    "KWT":"Кувейт","VIE":"Вьетнам","COL":"Колумбия","NZL":"Новая Зел.",
    "TUN":"Тунис","ALG":"Алжир","USA":"США","MKD":"Сев. Македония",
    "THA":"Таиланд","PHI":"Филиппины",
}

def fl(c):  return FLAGS.get(str(c).upper().strip(), "🌍")
def cn(c):
    c2 = str(c).upper().strip()
    return COUNTRIES.get(c2, c2)
def ci(v, d=0):
    try: return int(float(v)) if pd.notna(v) else d
    except: return d

def get_disc(cat_code):
    c = str(cat_code).upper()
    if 'BSM' in c: return 'Пляжное'
    if 'CSM' in c: return 'Боевое'
    if 'SAM' in c: return 'Спортивное'
    return ''

def get_weight(cat_code):
    c = str(cat_code).upper()
    if 'ADT' in c:
        parts = c.split('ADT')
        if len(parts) > 1:
            w = parts[1]
            return (w[:-1] + '+') if w.endswith('O') else w
    return ''

def fmt_time(ms):
    try:
        ms = int(float(ms))
        if ms <= 0: return None
        s = ms // 1000
        return f"{s//60}:{s%60:02d}"
    except: return None

# ─────────────────────────────────────────────────────────────────────────────
# ТРАНСЛИТЕРАЦИЯ
# ─────────────────────────────────────────────────────────────────────────────
TMAP = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
    'щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}
TMAP.update({k.upper(): v.capitalize() for k, v in TMAP.items()})

def translit(s): return ''.join(TMAP.get(c, c) for c in s)

def norm(s):
    s = s.strip()
    if any('\u0400' <= c <= '\u04ff' for c in s):
        s = translit(s)
    return s.lower()

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────────────────────────────────────
log.info("Загружаю базу...")
df = pd.read_csv(DB_FILE, low_memory=False)
df.columns = [c.strip().lower() for c in df.columns]
for col in ['winner_athlete_id','red_id','blue_id']:
    if col in df.columns:
        df[col] = df[col].apply(
            lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower()!='nan' else None)
df['red_full_name']  = df['red_first_name'].fillna('') + " " + df['red_last_name'].fillna('')
df['blue_full_name'] = df['blue_first_name'].fillna('') + " " + df['blue_last_name'].fillna('')
df['date_start']     = pd.to_datetime(df['date_start'], errors='coerce')
df['red_last_norm']  = df['red_last_name'].fillna('').str.lower()
df['blue_last_norm'] = df['blue_last_name'].fillna('').str.lower()
log.info(f"База: {len(df):,} матчей")

# ─────────────────────────────────────────────────────────────────────────────
# ПОИСК
# ─────────────────────────────────────────────────────────────────────────────
def find_athletes(last_q, first_q=None):
    q = norm(last_q)
    mask = (df['red_last_norm'].str.contains(q, na=False, regex=False) |
            df['blue_last_norm'].str.contains(q, na=False, regex=False))
    res = df[mask].copy()
    if first_q and not res.empty:
        fq = norm(first_q)
        fm = (res['red_first_name'].fillna('').str.lower().str.startswith(fq) |
              res['blue_first_name'].fillna('').str.lower().str.startswith(fq))
        if fm.any(): res = res[fm]
    athletes = {}
    for _, row in res.iterrows():
        for side in ("red", "blue"):
            ln = str(row.get(f"{side}_last_name", "")).lower().strip()
            if q in ln:
                fn  = str(row.get(f"{side}_full_name", "")).strip()
                cnt = str(row.get(f"{side}_nationality_code", "")).upper()
                if fn and fn not in athletes:
                    athletes[fn] = cnt
    return athletes

# ─────────────────────────────────────────────────────────────────────────────
# КАРТОЧКА АТЛЕТА
# ─────────────────────────────────────────────────────────────────────────────
def build_card(athlete_name: str) -> str:
    name_low = athlete_name.lower().strip()
    rows = df[df.apply(lambda r:
        str(r.get('red_full_name','')).lower().strip() == name_low or
        str(r.get('blue_full_name','')).lower().strip() == name_low,
    axis=1)].sort_values('date_start', ascending=False)

    if rows.empty:
        return f"Данные для *{athlete_name}* не найдены."

    # Базовые данные
    wins = losses = finals_c = 0
    dob = acnt = ""
    disciplines = {}
    win_seq = []
    fastest_ms = None
    scores = []
    last_final_year = ""

    for _, row in rows.iterrows():
        is_r = str(row.get('red_full_name','')).lower().strip() == name_low
        wid  = str(row.get('winner_athlete_id',''))
        mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
        won  = (wid == mid and wid != '')

        if won: wins += 1
        else:   losses += 1
        win_seq.append(won)

        rc = str(row.get('round_code','')).upper()
        if rc in FINALS:
            finals_c += 1
            if not last_final_year:
                ds = row.get('date_start')
                if pd.notna(ds):
                    last_final_year = str(pd.to_datetime(ds).year)

        # Быстрейшая победа
        if won:
            try:
                ft = int(float(row.get('fight_time', 0)))
                if ft > 0:
                    if fastest_ms is None or ft < fastest_ms:
                        fastest_ms = ft
            except: pass

        # Средний балл
        sc = ci(row.get('red_score') if is_r else row.get('blue_score'))
        scores.append(sc)

        # Дисциплина
        cc = str(row.get('category_code','')).upper()
        disc = get_disc(cc)
        weight = get_weight(cc)
        if disc:
            if disc not in disciplines:
                disciplines[disc] = weight

        # Данные профиля
        if not dob:
            v = row.get(f"{'red' if is_r else 'blue'}_birth_date")
            if v and pd.notna(v):
                try: dob = datetime.strptime(str(v).strip(), "%Y-%m-%d").strftime("%d.%m.%Y")
                except: dob = str(v).strip()
        if not acnt:
            acnt = str(row.get(f"{'red' if is_r else 'blue'}_nationality_code","")).upper()

    total   = wins + losses
    wr      = round(wins / total * 100) if total else 0
    avg_sc  = f"{sum(scores)/len(scores):.1f}" if scores else "—"
    fastest = fmt_time(fastest_ms) if fastest_ms else "—"

    # Серия
    streak_n = 0
    if win_seq and win_seq[0]:
        for w in win_seq:
            if w: streak_n += 1
            else: break

    # Дисциплины строкой
    disc_str = " · ".join(
        f"{d} {w}кг" if w else d
        for d, w in disciplines.items()
    )

    # Возраст
    age_str = ""
    if dob:
        try:
            age = (datetime.now() - datetime.strptime(dob, "%d.%m.%Y")).days // 365
            age_str = f" · {age} лет"
        except: pass

    # ── Строим сообщение ──────────────────────────────────────────────────────
    flag = fl(acnt)
    country = cn(acnt)

    # Заголовок
    text = f"{flag} *{athlete_name}*\n"
    text += f"{country}"
    if dob: text += f" · {dob}{age_str}"
    text += "\n"
    if disc_str: text += f"_{disc_str}_\n"
    text += "\n"

    # Статистика блоком
    bar_filled = "█" * round(wr / 10)
    bar_empty  = "░" * (10 - round(wr / 10))
    text += f"*{wins}* победы  *{losses}* поражения  *{total}* боёв\n"
    text += f"{bar_filled}{bar_empty} *{wr}%* побед\n"

    if finals_c:
        text += f"🏆 Финалов: *{finals_c}*"
        if last_final_year: text += f"  · последний: *{last_final_year}*"
        text += "\n"

    # Серия
    if streak_n >= 2:
        dots = "🟢" * min(streak_n, 8)
        text += f"\n{dots}\n"
        text += f"🔥 *{streak_n} WIN STREAK* — серия побед подряд\n"

    # Доп.статистика
    if fastest != "—" or avg_sc != "—":
        text += "\n"
        if fastest != "—": text += f"⚡️ Быстрейшая победа: *{fastest}*\n"
        if avg_sc != "—":  text += f"📊 Средний балл / бой: *{avg_sc}*\n"

    # Последние матчи
    text += "\n*Последние матчи:*\n"
    for _, row in rows.head(5).iterrows():
        yr   = int(row['date_start'].year) if pd.notna(row['date_start']) else "?"
        is_r = str(row.get('red_full_name','')).lower().strip() == name_low
        wid  = str(row.get('winner_athlete_id',''))
        mid  = str(row.get('red_id','') if is_r else row.get('blue_id',''))
        won  = (wid == mid and wid != '')
        msc  = ci(row.get('red_score') if is_r else row.get('blue_score'))
        osc  = ci(row.get('blue_score') if is_r else row.get('red_score'))
        opp  = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
        ocnt = str(row['blue_nationality_code'] if is_r else row['red_nationality_code'])
        rc   = RMAP.get(str(row.get('round_code','')).upper(), '?')
        ico  = "✅" if won else "❌"
        text += f"{ico} {yr} · {rc} · {msc}:{osc}  {fl(ocnt)} {opp[:18]}\n"

    # Соцсети
    text += (
        "\n─────────────────\n"
        "📹 *Видео с турниров:*\n"
        "[Instagram](https://instagram.com/guru.fight) · "
        "[TikTok](https://tiktok.com/@fight.guru) · "
        "[YouTube](https://youtube.com/@sambovideo)"
    )

    return text

# ─────────────────────────────────────────────────────────────────────────────
# КЛАВИАТУРЫ
# ─────────────────────────────────────────────────────────────────────────────
def kb_main():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔍 Найти бойца",       callback_data="help_search"),
        InlineKeyboardButton("🏆 Последние турниры", callback_data="recent"),
    )
    kb.add(
        InlineKeyboardButton("📸 Instagram",  url="https://instagram.com/guru.fight"),
        InlineKeyboardButton("▶️ YouTube",    url="https://youtube.com/@sambovideo"),
    )
    kb.add(
        InlineKeyboardButton("🎵 TikTok",     url="https://tiktok.com/@fight.guru"),
        InlineKeyboardButton("✈️ Telegram",   url="https://t.me/Fightguruofficial"),
    )
    kb.add(InlineKeyboardButton("💬 ВКонтакте", url="https://vk.com/fightguru"))
    return kb

def kb_social():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📸 Instagram",  url="https://instagram.com/guru.fight"),
        InlineKeyboardButton("▶️ YouTube",    url="https://youtube.com/@sambovideo"),
    )
    kb.add(
        InlineKeyboardButton("🎵 TikTok",     url="https://tiktok.com/@fight.guru"),
        InlineKeyboardButton("✈️ Telegram",   url="https://t.me/Fightguruofficial"),
    )
    kb.add(InlineKeyboardButton("💬 ВКонтакте", url="https://vk.com/fightguru"))
    return kb

def kb_select(athletes):
    kb = InlineKeyboardMarkup(row_width=1)
    for name, cnt in list(athletes.items())[:8]:
        kb.add(InlineKeyboardButton(
            f"{fl(cnt)}  {name}  ·  {cn(cnt)}",
            callback_data=f"pick:{name}"
        ))
    return kb

# ─────────────────────────────────────────────────────────────────────────────
# БОТ
# ─────────────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN, threaded=True)

WELCOME = (
    "🥋 *FIGHTGURU* — статистика самбо\n\n"
    "Привет! Ищу любого самбиста из базы FIAS.\n\n"
    "*Как искать:*\n"
    "Напиши фамилию — по\\-русски или латиницей:\n"
    "`Зиннатов`  или  `Zinnatov`\n"
    "Точный поиск: `Зиннатов Ролан`\n\n"
    "📊 База: турниры FIAS с 2021 года\n"
    "Автор: [@guru\\.fight](https://instagram.com/guru.fight)"
)

@bot.message_handler(commands=['start','help'])
def on_start(m):
    bot.send_message(m.chat.id, WELCOME,
                     parse_mode="MarkdownV2",
                     reply_markup=kb_main(),
                     disable_web_page_preview=True)

@bot.message_handler(commands=['social'])
def on_social(m):
    bot.send_message(m.chat.id,
                     "📱 *Подписывайся на FightGuru:*",
                     parse_mode="Markdown",
                     reply_markup=kb_social())

@bot.callback_query_handler(func=lambda c: c.data == "help_search")
def cb_help(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id,
        "🔍 Напиши фамилию бойца:\n\n"
        "По\\-русски: `Зиннатов`\n"
        "Латиницей: `Zinnatov`\n"
        "С именем: `Зиннатов Ролан`",
        parse_mode="MarkdownV2")

@bot.callback_query_handler(func=lambda c: c.data == "recent")
def cb_recent(c):
    bot.answer_callback_query(c.id)
    try:
        tours = (df[['tournament_name','date_start']].dropna()
                 .drop_duplicates('tournament_name')
                 .sort_values('date_start', ascending=False).head(6))
        text = "🏆 *Последние турниры в базе:*\n\n"
        for _, row in tours.iterrows():
            d = row['date_start']
            text += f"📅 {d.strftime('%m.%Y')} — {row['tournament_name']}\n"
        bot.send_message(c.message.chat.id, text,
                         parse_mode="Markdown",
                         reply_markup=kb_social(),
                         disable_web_page_preview=True)
    except Exception as e:
        log.error(f"recent: {e}")
        bot.send_message(c.message.chat.id, "Не удалось загрузить.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pick:"))
def cb_pick(c):
    bot.answer_callback_query(c.id)
    name = c.data[5:]
    try:
        text = build_card(name)
        bot.send_message(c.message.chat.id, text,
                         parse_mode="Markdown",
                         reply_markup=kb_social(),
                         disable_web_page_preview=True)
    except Exception as e:
        log.error(f"pick: {e}")
        bot.send_message(c.message.chat.id, "Ошибка при загрузке данных.")

@bot.message_handler(func=lambda m: True)
def on_msg(m):
    raw   = m.text.strip()
    parts = raw.split()
    if not parts or len(parts[0]) < 2:
        bot.reply_to(m,
            "Введи фамилию \\(минимум 2 символа\\)\nПример: `Зиннатов`",
            parse_mode="MarkdownV2")
        return

    last_q  = parts[0]
    first_q = parts[1] if len(parts) >= 2 else None
    log.info(f"Search '{raw}' from @{m.from_user.username}")

    athletes = find_athletes(last_q, first_q)

    if not athletes:
        q4 = norm(last_q)[:4]
        sugg = set()
        for col in ['red_last_norm','blue_last_norm']:
            for v in df[df[col].str.contains(q4, na=False, regex=False)][col]:
                if len(str(v)) > 2: sugg.add(str(v).strip().title())
        if sugg:
            sl = ", ".join(sorted(sugg)[:5])
            bot.reply_to(m,
                f"❌ *{raw}* не найден\n\n"
                f"Похожие фамилии: _{sl}_\n\n"
                f"Уточни запрос.",
                parse_mode="Markdown")
        else:
            bot.reply_to(m,
                f"❌ *{raw}* не найден\n\n"
                f"Проверь написание — можно по\\-русски или латиницей\\.",
                parse_mode="MarkdownV2")
        return

    if len(athletes) > 1:
        bot.reply_to(m,
            f"Найдено *{len(athletes)}* атлета — выбери нужного 👇",
            parse_mode="Markdown",
            reply_markup=kb_select(athletes))
        return

    name = list(athletes.keys())[0]
    try:
        text = build_card(name)
        bot.reply_to(m, text,
                     parse_mode="Markdown",
                     reply_markup=kb_social(),
                     disable_web_page_preview=True)
    except Exception as e:
        log.error(f"msg: {e}")
        bot.reply_to(m, "Ошибка при загрузке данных.")

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("FightGuru Bot v3 запущен")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            log.error(f"Polling: {e}")
            time.sleep(10)

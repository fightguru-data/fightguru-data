"""
FIGHTGURU — Telegram Bot
Запускается ОТДЕЛЬНО от Streamlit:
  python bot.py

На сервере (например Railway, VPS, или локально):
  nohup python bot.py &

Требует установки:
  pip install pyTelegramBotAPI pandas
"""

import os, sys, time, logging
import pandas as pd
import telebot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [BOT] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# КОНФИГ
# Токен можно задать через:
#   1. Переменную окружения: BOT_TOKEN=xxx python bot.py
#   2. Файл .streamlit/secrets.toml (если запускать рядом с приложением)
#   3. Прямо здесь (не рекомендуется для production)
# ─────────────────────────────────────────────────────────────────────────────
def get_token():
    # 1. Переменная окружения
    t = os.environ.get("BOT_TOKEN", "")
    if t: return t

    # 2. secrets.toml рядом со скриптом
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r") as f:
                for line in f:
                    if "bot_token" in line:
                        return line.split("=")[1].strip().strip('"').strip("'")
        except: pass

    return ""

TOKEN   = get_token()
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AllTournament.csv")

if not TOKEN:
    log.error("Токен не найден! Задайте BOT_TOKEN в переменных окружения.")
    sys.exit(1)

if not os.path.exists(DB_FILE):
    log.error(f"База данных не найдена: {DB_FILE}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────────────────────────────────────
log.info("Загружаю базу данных...")
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

log.info(f"База загружена: {len(df):,} матчей")

# ─────────────────────────────────────────────────────────────────────────────
# СПРАВОЧНИКИ
# ─────────────────────────────────────────────────────────────────────────────
ROUND_MAP = {
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
    "NZL":"🇳🇿","TUN":"🇹🇳","ALG":"🇩🇿","PAK":"🇵🇰",
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
    "TUN":"Тунис","ALG":"Алжир","PAK":"Пакистан","USA":"США",
    "MKD":"Сев. Македония","THA":"Таиланд","PHI":"Филиппины",
}

def fl(code):  return FLAGS.get(str(code).upper().strip(), "🌍")
def cn(code):
    c = str(code).upper().strip()
    return COUNTRIES.get(c, c)

def ci(v, d=0):
    try: return int(float(v)) if pd.notna(v) else d
    except: return d

# ─────────────────────────────────────────────────────────────────────────────
# БОТ
# ─────────────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN, threaded=True)

HELP_TEXT = (
    "🥋 FIGHTGURU — база данных самбо\n\n"
    "Поиск по фамилии (латиницей):\n"
    "  Zinnatov\n\n"
    "Точный поиск (фамилия + начало имени):\n"
    "  Kurzhev Ali\n\n"
    "Команды:\n"
    "  /start — это сообщение\n"
    "  /help  — помощь"
)

@bot.message_handler(commands=['start', 'help'])
def on_start(m):
    bot.send_message(m.chat.id, HELP_TEXT)
    log.info(f"START from {m.chat.id} @{m.from_user.username}")

@bot.message_handler(func=lambda m: True)
def on_search(m):
    raw   = m.text.strip()
    parts = raw.lower().split()

    if not parts or len(parts[0]) < 2:
        bot.reply_to(m, "Введите фамилию латиницей (минимум 2 символа).\nПример: Zinnatov")
        return

    last_q  = parts[0]
    first_q = parts[1] if len(parts) >= 2 else None

    log.info(f"Search: '{raw}' from @{m.from_user.username}")

    # ── поиск ────────────────────────────────────────────────────────────────
    mask = (
        df['red_last_name'].str.lower().str.contains(last_q, na=False, regex=False) |
        df['blue_last_name'].str.lower().str.contains(last_q, na=False, regex=False)
    )
    res = df[mask].copy()

    if first_q:
        mask2 = (
            res['red_first_name'].str.lower().str.startswith(first_q, na=False) |
            res['blue_first_name'].str.lower().str.startswith(first_q, na=False)
        )
        res = res[mask2]

    if res.empty:
        bot.reply_to(m,
            f"Атлет не найден: {raw}\n\n"
            "Проверьте написание. Фамилия вводится латиницей.\n"
            "Для точного поиска: Фамилия Имя"
        )
        return

    # ── определяем уникальных атлетов ────────────────────────────────────────
    found = {}
    for _, row in res.iterrows():
        for side in ("red", "blue"):
            ln = str(row.get(f"{side}_last_name", "")).lower().strip()
            if last_q in ln:
                fn  = str(row.get(f"{side}_full_name", "")).strip()
                cnt = str(row.get(f"{side}_nationality_code", "")).upper()
                if fn and fn not in found:
                    found[fn] = cnt
                break

    # ── если несколько атлетов — показываем список ────────────────────────────
    if len(found) > 1 and not first_q:
        msg = f"Найдено {len(found)} атлета с фамилией {raw.upper()}:\n\n"
        for name, cnt in found.items():
            msg += f"{fl(cnt)} {name} ({cn(cnt)})\n"
        msg += "\nДля точного поиска введите фамилию и имя:\nнапример: " + \
               list(found.keys())[0].split()[0] + " " + list(found.keys())[0].split()[-1][:3]
        bot.reply_to(m, msg)
        return

    # ── берём первого / единственного ────────────────────────────────────────
    chosen_name = list(found.keys())[0]
    chosen_cnt  = list(found.values())[0]
    chosen_low  = chosen_name.lower().strip()

    # фильтруем только его матчи
    athlete_rows = res[res.apply(
        lambda r: str(r.get('red_full_name','')).lower().strip() == chosen_low or
                  str(r.get('blue_full_name','')).lower().strip() == chosen_low,
        axis=1
    )]

    # ── статистика ────────────────────────────────────────────────────────────
    wins = losses = finals_c = 0
    dob = ""
    for _, row in athlete_rows.iterrows():
        is_r = str(row.get('red_full_name','')).lower().strip() == chosen_low
        wid  = str(row.get('winner_athlete_id', ''))
        mid  = str(row.get('red_id', '') if is_r else row.get('blue_id', ''))
        won  = (wid == mid and wid != '')
        if won: wins += 1
        else:   losses += 1
        rc = str(row.get('round_code', '')).upper()
        if rc in FINALS: finals_c += 1
        if not dob:
            v = row.get(f"{'red' if is_r else 'blue'}_birth_date")
            if v and pd.notna(v):
                try:
                    from datetime import datetime
                    dob = datetime.strptime(str(v).strip(), "%Y-%m-%d").strftime("%d.%m.%Y")
                except: dob = str(v).strip()

    total = wins + losses
    wr    = round(wins / total * 100) if total else 0

    # ── последние 5 матчей ────────────────────────────────────────────────────
    recent = athlete_rows.sort_values('date_start', ascending=False).head(5)
    lines  = ""
    for _, row in recent.iterrows():
        yr   = int(row['date_start'].year) if pd.notna(row['date_start']) else "?"
        is_r = str(row.get('red_full_name','')).lower().strip() == chosen_low
        wid  = str(row.get('winner_athlete_id', ''))
        mid  = str(row.get('red_id', '') if is_r else row.get('blue_id', ''))
        won  = (wid == mid and wid != '')
        msc  = ci(row.get('red_score')  if is_r else row.get('blue_score'))
        osc  = ci(row.get('blue_score') if is_r else row.get('red_score'))
        opp  = str(row['blue_full_name'] if is_r else row['red_full_name']).strip()
        opp_cnt = str(row['blue_nationality_code'] if is_r else row['red_nationality_code'])
        rc   = ROUND_MAP.get(str(row.get('round_code', '')).upper(), '?')
        ico  = "✅" if won else "❌"
        lines += f"{ico} {yr} | {rc} | {msc}:{osc}\n    vs {fl(opp_cnt)} {opp[:20]}\n"

    # ── формируем сообщение ───────────────────────────────────────────────────
    msg = (
        f"📊 {chosen_name}\n"
        f"{fl(chosen_cnt)} {cn(chosen_cnt)}"
    )
    if dob:
        msg += f" · {dob}"
    msg += (
        f"\n\n"
        f"Боёв:     {total}\n"
        f"Победы:   {wins} ({wr}%)\n"
        f"Пораж.:   {losses}\n"
    )
    if finals_c:
        msg += f"Финалы:   {finals_c}\n"

    msg += f"\nПоследние матчи:\n{lines}"

    bot.send_message(m.chat.id, msg)
    log.info(f"Sent stats for {chosen_name} to @{m.from_user.username}")

# ─────────────────────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"Бот запущен. Token: {TOKEN[:10]}...")
    log.info(f"База данных: {DB_FILE}")

    while True:
        try:
            log.info("Polling started...")
            bot.infinity_polling(timeout=30, long_polling_timeout=25)
        except Exception as e:
            log.error(f"Polling error: {e}")
            log.info("Перезапуск через 10 секунд...")
            time.sleep(10)

import telebot
import pandas as pd
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = '8677319918:AAHqlbO9FnZ1lcLkM1WLWfZ2vC9q_8gyc6c'
DATABASE_FILE = "AllTournament.csv"

bot = telebot.TeleBot(TOKEN)

# --- СПРАВОЧНИКИ (Протокол №3 - Текстовые коды) ---
FLAG_TEXT = {
    "RUS": "[RUS]", "BLR": "[BLR]", "KAZ": "[KAZ]", "UZB": "[UZB]", "KGZ": "[KGZ]",
    "MGL": "[MGL]", "GEO": "[GEO]", "ARM": "[ARM]", "AZE": "[AZE]", "TJK": "[TJK]",
    "TKM": "[TKM]", "UKR": "[UKR]", "MDA": "[MDA]", "FRA": "[FRA]", "SRB": "[SRB]",
    "ROU": "[ROU]", "BUL": "[BUL]", "GRE": "[GRE]", "NED": "[NED]", "ESP": "[ESP]",
    "ITA": "[ITA]", "GER": "[GER]", "AIN": "[AIN]", "TUR": "[TUR]", "USA": "[USA]"
}

def get_flag_txt(c):
    return FLAG_TEXT.get(str(c).upper().strip(), f"[{c}]")

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
            w = raw[:-1] + "+" if raw.endswith('O') else raw
    return f"{p} {w}кг" if p else c

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "FIGHTGURU DATA CENTER\nВведите ФАМИЛИЮ атлета на латинице (например: Osipenko):")

@bot.message_handler(func=lambda message: True)
def search_athlete(message):
    query = message.text.strip().lower()
    
    if len(query) < 3:
        bot.send_message(message.chat.id, "Введите минимум 3 буквы фамилии.")
        return

    if not os.path.exists(DATABASE_FILE):
        bot.send_message(message.chat.id, "Ошибка: Файл базы AllTournament.csv не найден в системе.")
        return

    try:
        # Загрузка данных (Протокол №5 - Унификация)
        df = pd.read_csv(DATABASE_FILE, low_memory=False)
        df.columns = [col.strip().lower() for col in df.columns]
        
        # Поиск (Протокол №5 - Регстронезависимость)
        res = df[
            (df['red_last_name'].str.lower().str.contains(query, na=False)) |
            (df['blue_last_name'].str.lower().str.contains(query, na=False))
        ].copy()

        if res.empty:
            bot.send_message(message.chat.id, f"Атлет '{}' не найден.")
            return

        res['date_start'] = pd.to_datetime(res['date_start'], errors='coerce')
        res = res.sort_values('date_start', ascending=False).head(10)

        response = f"📊 ДОСЬЕ: {query.upper()}\n" + "="*20 + "\n"
        
        for _, row in res.iterrows():
            date = row['date_start'].year if pd.notna(row['date_start']) else "????"
            cat = get_readable_cat(row['category_code'])
            
            win_id = str(row['winner_athlete_id']).split('.')[0] if pd.notna(row['winner_athlete_id']) else ""
            red_id = str(row['red_id']).split('.')[0]
            
            # Определяем, был ли атлет красным или синим в этой схватке
            is_red = query in str(row['red_last_name']).lower()
            won = (win_id == red_id and is_red) or (win_id != red_id and not is_red)
            status = "✅ WIN" if won else "❌ LOSS"
            
            red_c = get_flag_txt(row['red_nationality_code'])
            blue_c = get_flag_txt(row['blue_nationality_code'])
            
            line = f"{status} | {} | {}\n"
            line += f"{} {row['red_last_name']} vs {row['blue_last_name']} {}\n"
            line += f"Счет: {int(row['red_score']) if pd.notna(row['red_score']) else 0}:{int(row['blue_score']) if pd.notna(row['blue_score']) else 0}\n"
            line += "-"*15 + "\n"
            
            if len(response + line) > 4000: break
            response += line

        bot.send_message(message.chat.id, response)

    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка при обработке базы данных.")

if __name__ == "__main__":
    print("Бот FIGHTGURU запущен...")
    bot.infinity_polling()
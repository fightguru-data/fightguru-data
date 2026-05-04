# --- СКРИПТ "АНАЛИЗАТОР GURU.FIGHT" (v47.0 - Historical Leaderboard) ---
import streamlit as st
import pandas as pd
import os
from PIL import Image, ImageDraw, ImageFont
import io

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
try:
    logo_img = Image.open("logo.png")
except:
    logo_img = "🥋" 

st.set_page_config(page_title="FIGHTGURU DATA CENTER", page_icon=logo_img, layout="wide")

# --- СТИЛИЗАЦИЯ (CSS) ---
st.markdown("""
<style>
    .stDownloadButton { display: flex; justify-content: center; margin-top: -15px; margin-bottom: 50px; }
    .stDownloadButton button { background-color: #e63946 !important; color: white !important; font-weight: bold !important; width: 320px; border-radius: 8px !important; }
    .poster-card {
        background: #000000; border-left: 12px solid #e63946; outline: 1px solid rgba(255,255,255,0.3);
        width: 500px; height: 680px; padding: 40px; color: white; font-family: 'Inter', sans-serif;
        display: flex; flex-direction: column; margin: 0 auto 20px auto; box-shadow: 0 40px 100px rgba(0,0,0,0.9); box-sizing: border-box;
    }
    .p-header { border-bottom: 1px solid #222; margin-bottom: 20px; padding-bottom: 10px; }
    .p-title { font-size: 24px; font-weight: 900; text-transform: uppercase; margin: 0; letter-spacing: -0.5px; }
    .p-weight { font-size: 18px; color: #e63946; font-weight: 700; margin-top: 5px; text-transform: uppercase; }
    .p-label { font-size: 10px; text-transform: uppercase; color: #555; letter-spacing: 2px; margin: 20px 0 10px 0; font-weight: 800; }
    .p-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #111; }
    .p-country { font-size: 15px; font-weight: 700; text-transform: uppercase; color: #fff; }
    .gold-box { color: #e63946; font-weight: 900; font-size: 16px; }
    .p-athlete { font-size: 14px; margin-bottom: 6px; color: #ddd; }
    .p-footer { margin-top: auto; padding-top: 15px; display: flex; justify-content: space-between; border-top: 1px solid #111; align-items: center;}
    .p-brand { font-size: 11px; font-weight: 900; color: #444; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
DATABASE_FILE = "AllTournament.csv"
CODE_TRANSLATIONS = {"FIAS1": "RUS", "FIAS2": "BLR", "FIAS3": "FRA", "FIAS4": "AIN"}
COUNTRY_NAMES_RU = {
    "RUS": "РОССИЯ", "BLR": "БЕЛАРУСЬ", "KAZ": "КАЗАХСТАН", "UZB": "УЗБЕКИСТАН", "KGZ": "КЫРГЫЗСТАН", 
    "MGL": "МОНГОЛИЯ", "GEO": "ГРУЗИЯ", "ARM": "АРМЕНИЯ", "AZE": "АЗЕРБАЙДЖАН", "TJK": "ТАДЖИКИСТАН", 
    "TKM": "ТУРКМЕНИСТАН", "UKR": "УКРАИНА", "MDA": "МОЛДОВА", "SRB": "СЕРБИЯ", "ROU": "РУМЫНИЯ", 
    "BUL": "БОЛГАРИЯ", "GRE": "ГРЕЦИЯ", "FRA": "ФРАНЦИЯ", "NED": "НИДЕРЛАНДЫ", "ESP": "ИСПАНИЯ", 
    "ITA": "ИТАЛИЯ", "GER": "ГЕРМАНИЯ", "ISR": "ИЗРАИЛЬ", "USA": "США", "MAR": "МАРОККО", 
    "CMR": "КАМЕРУН", "EGY": "ЕГИПЕТ", "AIN": "НЕЙТР. АТЛЕТ", "TUR": "ТУРЦИЯ", "LAT": "ЛАТВИЯ", "LTU": "ЛИТВА", "EST": "ЭСТОНИЯ"
}
FLAG_EMOJIS = {
    "RUS": "🇷🇺", "BLR": "🇧🇾", "KAZ": "🇰🇿", "UZB": "🇺🇿", "KGZ": "🇰🇬", "MGL": "🇲🇳", "GEO": "🇬🇪", "ARM": "🇦🇲", "AZE": "🇦🇿", 
    "TJK": "🇹🇯", "TKM": "🇹🇲", "UKR": "🇺🇦", "MDA": "🇲🇩", "FRA": "🇫🇷", "SRB": "🇷🇸", "ROU": "🇷🇴", "BUL": "🇧🇬", "GRE": "🇬🇷", 
    "NED": "🇳🇱", "ESP": "🇪🇸", "ITA": "🇮🇹", "GER": "🇩🇪", "CRO": "🇭🇷", "MKD": "🇲🇰", "MAR": "🇲🇦", "USA": "🇺🇸", "AIN": "🏳️",
    "TUR": "🇹🇷", "LAT": "🇱🇻", "LVA": "🇱🇻", "CMR": "🇨🇲", "EGY": "🇪🇬", "ISR": "🇮🇱"
}
ROUND_ORDER = {'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QFL': 5, 'SFL': 6, 'FNL': 7, 'FIN': 7}
TOURNAMENT_GROUPS = {
    "Чемпионат Мира": ["World Sambo Championships", "World SAMBO Championships"],
    "Кубок Мира": ["Cup", "President"], 
    "Чемпионат Европы": ["European Sambo Championships", "European Championships"],
    "ЧМ Азии и Океании": ["Asia and Oceania Sambo Championships"]
}
DIVISIONS = {"Спортивное Самбо (М)": "samm", "Спортивное Самбо (Ж)": "samw", "Боевое Самбо (М)": "csmm", "Боевое Самбо (Ж)": "csmw"}

# --- ФУНКЦИИ ---
def get_flag(c): return FLAG_EMOJIS.get(c, "🌍")
def get_full_country(c): return COUNTRY_NAMES_RU.get(c, c)
def trans_c(c): 
    if pd.isna(c): return "UNK"
    code = str(c).upper().strip()
    return CODE_TRANSLATIONS.get(code, code)

def get_readable_cat(cat_code):
    if pd.isna(cat_code): return "Unknown"
    code = str(cat_code).upper().strip()
    prefix = ""
    if "SAMM" in code: prefix = "Спортивное Самбо Мужчины"
    elif "SAMW" in code: prefix = "Спортивное Самбо Женщины"
    elif "CSMM" in code: prefix = "Боевое Самбо Мужчины"
    elif "CSMW" in code: prefix = "Боевое Самбо Женщины"
    elif "SVI" in code: prefix = "Самбо Слепых"
    weight = ""
    if "ADT" in code:
        parts = code.split("ADT")
        if len(parts) > 1:
            w_raw = parts[1]
            weight = (w_raw[:-1] + "+ кг") if w_raw.endswith('O') else (w_raw + " кг")
    return f"{prefix} {weight}" if prefix else code

def create_jpeg_card(tournament, weight, countries, athletes, period_str):
    img = Image.new('RGB', (1080, 1350), color='#000000')
    draw = ImageDraw.Draw(img)
    draw.rectangle([5, 5, 1075, 1345], outline='#ffffff', width=2)
    draw.rectangle([5, 5, 35, 1345], fill='#e63946')
    f_p = next((p for p in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"] if os.path.exists(p)), None)
    try:
        f_title = ImageFont.truetype(f_p, 65); f_weight = ImageFont.truetype(f_p, 40); f_label = ImageFont.truetype(f_p, 24); f_row = ImageFont.truetype(f_p, 38); f_brand = ImageFont.truetype(f_p, 28); f_period = ImageFont.truetype(f_p, 20)
    except:
        f_title = f_weight = f_label = f_row = f_brand = f_period = ImageFont.load_default()
    draw.text((120, 120), tournament.upper(), font=f_title, fill="#ffffff")
    draw.text((120, 210), weight.upper(), font=f_weight, fill="#e63946")
    draw.line((120, 280, 960, 280), fill="#222222", width=3)
    draw.text((120, 340), "СТРАНЫ-ЛИДЕРЫ", font=f_label, fill="#555555")
    y = 400
    for c_code, gold in countries.items():
        draw.text((120, y), get_full_country(c_code), font=f_row, fill="#ffffff")
        draw.text((800, y), f"{gold} GOLD", font=f_row, fill="#e63946")
        y += 90; draw.line((120, y-15, 960, y-15), fill="#111111", width=1)
    y += 40; draw.text((120, y), "ТОП ЧЕМПИОНОВ", font=f_label, fill="#555555")
    y += 60
    for name, data in athletes.items():
        draw.text((120, y), f"{name} ({data['country']}) — {data['count']} мед.", font=f_row, fill="#cccccc"); y += 75
    draw.text((120, 1270), "FIGHTGURU | МИР САМБО", font=f_brand, fill="#555555")
    draw.text((750, 1270), period_str, font=f_period, fill="#333333")
    buf = io.BytesIO(); img.save(buf, format='JPEG', quality=100); return buf.getvalue()

@st.cache_data
def load_data():
    if not os.path.exists(DATABASE_FILE): return None
    try:
        df = pd.read_csv(DATABASE_FILE, sep=',', on_bad_lines='skip', low_memory=False)
        df.columns = [col.strip().replace('"', '').lower() for col in df.columns]
        for col in ['winner_athlete_id', 'red_id', 'blue_id']:
            df[col] = df[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).lower() != 'nan' else None)
        df['tournament_name'] = df['tournament_name'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        df['red_full_name'] = df['red_first_name'].astype(str).str.strip() + " " + df['red_last_name'].astype(str).str.strip()
        df['blue_full_name'] = df['blue_first_name'].astype(str).str.strip() + " " + df['blue_last_name'].astype(str).str.strip()
        df['red_name_clean'] = df['red_full_name'].str.lower().str.strip()
        df['blue_name_clean'] = df['blue_full_name'].str.lower().str.strip()
        df['red_last_name_clean'] = df['red_last_name'].astype(str).str.lower().str.strip()
        df['blue_last_name_clean'] = df['blue_last_name'].astype(str).str.lower().str.strip()
        df['seconds'] = df['fight_time'].apply(lambda x: (parts:=str(x).split(':'), float(parts[0])*60 + float(parts[1]))[1] if ':' in str(x) else (float(x)/1000 if pd.notna(x) else None))
        df['Human_Category'] = df['category_code'].apply(get_readable_cat)
        df['date_start'] = pd.to_datetime(df['date_start'], errors='coerce')
        df['round_order'] = df['round_code'].apply(lambda x: ROUND_ORDER.get(str(x).upper(), 99))
        return df
    except Exception as e: st.error(f"Error: {e}"); return None

df = load_data()

# --- ЛОГИКА СБОРА ДАННЫХ ---
def get_pantheon_data(dataframe, t_group_name, div_code):
    pattern = '|'.join(TOURNAMENT_GROUPS[t_group_name])
    filtered = dataframe[dataframe['tournament_name'].str.contains(pattern, case=False, na=False)]
    if div_code: filtered = filtered[filtered['category_code'].str.contains(div_code, case=False, na=False)]
    finals = filtered[filtered['round_code'].str.contains('FNL|FIN', case=False, na=False)].copy()
    if finals.empty: return pd.DataFrame()
    def get_wi(row):
        if str(row['winner_athlete_id']) == str(row['red_id']): return row['red_full_name'], trans_c(row['red_nationality_code'])
        if str(row['winner_athlete_id']) == str(row['blue_id']): return row['blue_full_name'], trans_c(row['blue_nationality_code'])
        return None, None
    finals[['winner_name', 'winner_country']] = finals.apply(lambda r: pd.Series(get_wi(r)), axis=1)
    res = []
    for cat in sorted(finals['category_code'].unique()):
        cat_f = finals[finals['category_code'] == cat].dropna(subset=['winner_name'])
        for name in cat_f['winner_name'].unique():
            wins = cat_f[cat_f['winner_name'] == name]
            res.append({"Атлет": name, "Страна": wins.iloc[0]['winner_country'], "Категория": get_readable_cat(cat), "Медалей": len(wins), "Турниры": [f"{r['date_start'].year} {r['tournament_name']}" for _, r in wins.iterrows()]})
    return pd.DataFrame(res)

# --- ИНТЕРФЕЙС ---
st.sidebar.title("FIGHTGURU STUDIO v47")
mode = st.sidebar.radio("Навигация:", ["🏛️ Пантеон", "🌍 Глобальный", "🏆 Легенды", "👤 Досье"])

if mode == "🏛️ Пантеон":
    st.header("🏛️ Пантеон Дивизиона")
    t_group = st.sidebar.selectbox("Турнир:", list(TOURNAMENT_GROUPS.keys()))
    div_choice = st.sidebar.selectbox("Дивизион:", list(DIVISIONS.keys()))
    report_df = get_pantheon_data(df, t_group, DIVISIONS[div_choice])
    
    if report_df.empty: st.warning("Нет данных.")
    else:
        # 1. ОБЩИЙ ИСТОРИЧЕСКИЙ ЗАЧЕТ ПО СТРАНАМ
        st.subheader(f"📊 Итоговый зачет за все годы: {div_choice}")
        overall = report_df.groupby('Страна')['Медалей'].sum().reset_index().sort_values('Медалей', ascending=False)
        overall['Страна_Display'] = overall['Страна'].apply(lambda x: f"{get_flag(x)} {get_full_country(x)}")
        st.dataframe(overall[['Страна_Display', 'Медалей']], use_container_width=True, hide_index=True)
        
        # --- ТЕКСТОВЫЙ БЛОК ОБЩЕГО ЗАЧЕТА ДЛЯ ИИ ---
        ai_overall_text = f"ИСТОРИЧЕСКИЙ ЗАЧЕТ СТРАН ({t_group} - {div_choice})\n"
        ai_overall_text += "="*40 + "\n"
        for _, row in overall.iterrows():
            ai_overall_text += f"{get_full_country(row['Страна'])}: {int(row['Медалей'])} золотых медалей\n"
        st.code(ai_overall_text, language="text")
        
        st.divider()

        # 2. ПОКАТЕГОРИЙНЫЙ РАЗБОР
        visual_mode = st.toggle("🎨 ВКЛЮЧИТЬ ВИЗУАЛЬНЫЙ РЕЖИМ (JPEG)")
        for cat_name in sorted(report_df['Категория'].unique()):
            cat_data = report_df[report_df['Категория'] == cat_name].sort_values('Медалей', ascending=False)
            
            if visual_mode:
                c_dict = cat_data.groupby('Страна')['Медалей'].sum().sort_values(ascending=False).to_dict()
                country_html = "".join([f'<div class="p-row"><span class="p-country">{get_flag(k)} {get_full_country(k)}</span><span class="p-gold">{v} GOLD</span></div>' for k,v in c_dict.items()])
                ath_dict = {r['Атлет']: {"count": r['Медалей'], "country": r['Страна']} for _, r in cat_data.head(5).iterrows()}
                athlete_html = "".join([f'<div class="p-athlete"><b>{n}</b> ({d["country"]}) — {d["count"]} мед.</div>' for n, d in ath_dict.items()])
                st.markdown(f'<div class="poster-card"><div class="p-header"><div class="p-title">{t_group}</div><div class="p-weight">{cat_name}</div></div><div class="p-label">Страны-лидеры</div>{country_html}<div class="p-label">Топ чемпионов</div><div class="athlete-list">{athlete_html}</div><div class="p-footer"><span class="p-brand">FIGHTGURU | МИР САМБО</span></div></div>', unsafe_allow_html=True)
                jpeg_data = create_jpeg_card(t_group, cat_name, c_dict, ath_dict, "FIGHTGURU ANALYTICS")
                st.download_button(label=f"💾 СКАЧАТЬ JPEG ({cat_name})", data=jpeg_data, key=f"dl_{cat_name}", file_name=f"GURU_{cat_name}.jpg")
            else:
                with st.expander(f"🏆 {cat_name}"):
                    st.dataframe(cat_data[['Атлет', 'Страна', 'Медалей']], hide_index=True, use_container_width=True)
            
            # Текст для ИИ по конкретному весу
            ai_text = f"ТУРНИР: {t_group}\nКАТЕГОРИЯ: {cat_name}\n\nСТРАНЫ В ЭТОМ ВЕСЕ:\n"
            c_dict_cat = cat_data.groupby('Страна')['Медалей'].sum().sort_values(ascending=False).to_dict()
            for k,v in c_dict_cat.items(): ai_text += f"- {get_full_country(k)}: {v} золота\n"
            ai_text += "\nАТЛЕТЫ В ЭТОМ ВЕСЕ:\n"
            for _, r in cat_data.iterrows(): ai_text += f"- {r['Атлет']} ({r['Страна']}): {r['Медалей']} мед. ({', '.join(r['Турниры'])})\n"
            st.code(ai_text, language="text")

elif mode == "🌍 Глобальный":
    st.header("🌍 Глобальный Анализ")
    t_group = st.sidebar.selectbox("Турнир:", list(TOURNAMENT_GROUPS.keys()))
    f_df = df[df['tournament_name'].str.contains('|'.join(TOURNAMENT_GROUPS[t_group]), case=False, na=False)]
    years = ["Все года"] + sorted(f_df['date_start'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    sel_y = st.sidebar.selectbox("Год:", years)
    wc_df = f_df.copy() if sel_y == "Все года" else f_df[f_df['date_start'].dt.year == sel_y]
    if wc_df.empty: st.warning("Нет данных.")
    else:
        st.metric("Всего схваток", len(wc_df))
        st.subheader("⚡ Самые быстрые победы")
        speed = wc_df[wc_df['seconds'] > 2.0].sort_values('seconds')[['Human_Category', 'red_full_name', 'blue_full_name', 'seconds']].head(15)
        st.dataframe(speed, use_container_width=True)

elif mode == "🏆 Легенды":
    st.header("🏆 Победные серии")
    t_group = st.sidebar.selectbox("Турнир:", list(TOURNAMENT_GROUPS.keys()))
    wc_df = df[df['tournament_name'].str.contains('|'.join(TOURNAMENT_GROUPS[t_group]), case=False, na=False)].sort_values(['date_start', 'round_order'])
    all_ath = pd.concat([wc_df['red_full_name'], wc_df['blue_full_name']]).unique()
    streaks = []
    for a in all_ath:
        curr = 0; mx = 0; matches = wc_df[(wc_df['red_full_name'] == a) | (wc_df['blue_full_name'] == a)]
        for _, m in matches.iterrows():
            win = m['red_full_name'] if str(m['winner_athlete_id']) == str(m['red_id']) else m['blue_full_name']
            if win == a: curr += 1
            else: mx = max(mx, curr); curr = 0
        mx = max(mx, curr)
        if mx > 4: streaks.append({"Атлет": a, "Серия": mx})
    st.dataframe(pd.DataFrame(streaks).sort_values("Серия", ascending=False), use_container_width=True)

elif mode == "👤 Досье":
    st.header("👤 Досье Спортсмена")
    name = st.text_input("Введите фамилию:").lower().strip()
    if name:
        res = df[(df['red_last_name_clean'].str.contains(name, na=False)) | (df['blue_last_name_clean'].str.contains(name, na=False))].copy()
        if not res.empty:
            res['Победитель'] = res.apply(lambda r: r['red_full_name'] if str(r['winner_athlete_id'])==str(r['red_id']) else r['blue_full_name'], axis=1)
            res['К_Страна'] = res['red_nationality_code'].apply(lambda x: f"{get_flag(trans_c(x))} {trans_c(x)}")
            res['С_Страна'] = res['blue_nationality_code'].apply(lambda x: f"{get_flag(trans_c(x))} {trans_c(x)}")
            st.dataframe(res[['tournament_name', 'date_start', 'Human_Category', 'red_full_name', 'К_Страна', 'blue_full_name', 'С_Страна', 'Победитель', 'red_score', 'blue_score']].sort_values('date_start', ascending=False), use_container_width=True)
        else: st.info("Атлет не найден.")
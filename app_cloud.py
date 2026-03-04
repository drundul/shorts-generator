
import streamlit as st
import os
import subprocess
from datetime import timedelta
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np
import pandas as pd
import tempfile

# ========================
# AUTH: Password Gate
# ========================
def check_password():
    """Simple password gate using Streamlit secrets."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Shorts Generator")
    password = st.text_input("Введите пароль:", type="password")
    if st.button("Войти"):
        if password == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Неправильный пароль")
    return False

if not check_password():
    st.stop()

# ========================
# CONFIG (Cloud-safe)
# ========================
WORK_DIR = tempfile.mkdtemp()
ASSETS_DIR = os.path.join(WORK_DIR, "assets")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
OVERLAY_PATH = os.path.join(ASSETS_DIR, "shorts_overlay.png")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# OpenAI key from Streamlit Secrets
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# --- FUNC: SMART RESIZE ---
def resize_to_shorts(image):
    return ImageOps.fit(image, (1080, 1920), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

# --- FUNC: CREATE OVERLAY ---
def ensure_overlay_exists():
    if os.path.exists(OVERLAY_PATH):
        return
    os.makedirs(ASSETS_DIR, exist_ok=True)
    W, H = 1080, 1920
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    icon_x = W - 130
    start_y = H - 800
    spacing = 160
    for i in range(5):
        y = start_y + (i * spacing)
        draw.ellipse([icon_x, y, icon_x + 90, y + 90], fill=(0, 0, 0, 120))
        center_x, center_y = icon_x + 45, y + 45
        draw.rectangle([center_x - 15, center_y - 15, center_x + 15, center_y + 15], fill=(255, 255, 255, 220))

    avatar_y = H - 250
    draw.ellipse([40, avatar_y, 120, avatar_y + 80], fill=(255, 255, 255, 255))
    draw.rectangle([140, avatar_y + 20, 500, avatar_y + 60], fill=(255, 255, 255, 180))
    draw.rectangle([40, avatar_y + 100, 800, avatar_y + 140], fill=(255, 255, 255, 100))
    draw.rectangle([0, H - 10, W, H], fill=(255, 0, 0, 255))

    img.save(OVERLAY_PATH)

# --- FUNC: WHISPER & ASS ---
def time_to_ass_format(seconds):
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    centiseconds = td.microseconds // 10000
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

def get_word_timestamps(audio_path, prompt_text=""):
    with open(audio_path, "rb") as audio:
        params = {
            "model": "whisper-1",
            "response_format": "verbose_json",
            "timestamp_granularities": ["word"]
        }
        if prompt_text:
            params["prompt"] = prompt_text[:400]

        transcript = client.audio.transcriptions.create(**params, file=audio)

    return transcript.words

# --- FUNC: HELPER ---
def hex_to_ass_color(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r, g, b = hex_str[:2], hex_str[2:4], hex_str[4:]
        return f"&H00{b}{g}{r}"
    return "&H00FFFFFF"

def generate_karaoke_ass(words, output_ass_path, font_name, font_size, max_words_per_screen, offset_y,
                         static_text="", static_font="Arial", static_size=60, static_color="#FFFFFF", static_pos_y=500):
    center_y = int(960 + offset_y)
    highlight_color = "&H0000FFFF"
    ass_static_color = hex_to_ass_color(static_color)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0 

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BaseStyle,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,5,50,50,0,1
Style: StaticStyle,{static_font},{static_size},{ass_static_color},&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    if static_text:
        formatted_static = static_text.replace("\n", "\\N")
        static_event = f"Dialogue: 0,0:00:00.00,1:00:00.00,StaticStyle,,0,0,0,,{{\\pos(540,{static_pos_y})}}{formatted_static}"
        events.append(static_event)

    chunks = []
    current_chunk = []

    for w in words:
        txt = str(w.get('word', ''))
        is_capital = txt[0].isupper() if txt else False

        if len(current_chunk) >= max_words_per_screen or (is_capital and len(current_chunk) > 0):
            chunks.append(current_chunk)
            current_chunk = []

        current_chunk.append(w)

    if current_chunk:
        chunks.append(current_chunk)

    for chunk in chunks:
        if not chunk: continue
        line_start = chunk[0]['start']
        line_end = chunk[-1]['end'] + 0.2

        ass_start = time_to_ass_format(line_start)
        ass_end = time_to_ass_format(line_end)

        text_line = ""
        for w_obj in chunk:
            w_text = w_obj['word']
            rel_start = int((w_obj['start'] - line_start) * 1000)
            rel_end = int((w_obj['end'] - line_start) * 1000)

            effect = (
                f"{{\\t({rel_start},{rel_start+1},\\1c{highlight_color})}}"
                f"{{\\t({rel_end},{rel_end+1},\\1c&HFFFFFF&)}}"
                f"{w_text} "
            )
            text_line += effect

        full_line = f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{{\\fad(100,100)\\pos(540,{center_y})}}{text_line}"
        events.append(full_line)

    with open(output_ass_path, "w", encoding="utf-8-sig") as f:
        f.write(header + "\n".join(events))

# --- FUNC: PREVIEW ---
def create_preview_image(bg_image_path, font_name, font_size, offset_y, text_sample="ВАШ ТЕКСТ ТУТ\nСМОТРИТСЯ ТАК",
                         static_text="", static_font="Arial", static_size=60, static_color="#FFFFFF", static_pos_y=500):
    bg = Image.open(bg_image_path).convert("RGBA")
    bg = resize_to_shorts(bg)

    txt_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(txt_layer)

    def draw_centered(text, center_y_pos, f_name, f_sz, color=(255, 255, 255, 255)):
        font = ImageFont.load_default()
        # Try common Linux font paths (for cloud), then Windows
        font_paths = [
            f"/usr/share/fonts/truetype/dejavu/{f_name}",
            f"/usr/share/fonts/truetype/{f_name}",
            f"C:\\Windows\\Fonts\\{f_name}",
            f"C:\\Windows\\Fonts\\{f_name}.ttf",
            f_name
        ]
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, f_sz)
                break
            except:
                continue

        bbox = d.multiline_textbbox((0, 0), text, font=font, align="center")
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (1080 - w) / 2
        y = center_y_pos - (h / 2)

        d.multiline_text((x + 4, y + 4), text, font=font, fill=(0, 0, 0, 180), align="center")
        d.multiline_text((x, y), text, font=font, fill=color, align="center")

    dyn_y = (1920 / 2) + offset_y
    draw_centered(text_sample, dyn_y, font_name, font_size)

    if static_text:
        if static_color.startswith('#'):
            h = static_color.lstrip('#')
            rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        else:
            rgb = (255, 255, 255, 255)
        draw_centered(static_text, static_pos_y, static_font, static_size, color=rgb)

    combined = Image.alpha_composite(bg, txt_layer)

    ensure_overlay_exists()
    if os.path.exists(OVERLAY_PATH):
        overlay = Image.open(OVERLAY_PATH).convert("RGBA")
        combined = Image.alpha_composite(combined, overlay)

    return combined

# ========================
# APP UI
# ========================
st.set_page_config(page_title="Shorts Maker", layout="wide")

with st.sidebar:
    st.write("🔧 Управление")
    if st.button("🗑️ СБРОСИТЬ ВСЁ (Начать заново)", type="primary"):
        for key in list(st.session_state.keys()):
            if key != "authenticated":
                del st.session_state[key]
        st.rerun()

st.markdown("""
<style>
    [data-testid="stImage"] {
        max-width: 350px; 
        margin: 0 auto;
    }
    .main .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("📱 Shorts Generator")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Файлы")

    uploaded_img = st.file_uploader("📷 Загрузить фото (фон)", type=['jpg', 'png', 'jpeg'])
    img_path = None
    if uploaded_img:
        img_path = os.path.join(WORK_DIR, "uploaded_bg.png")
        with open(img_path, "wb") as f:
            f.write(uploaded_img.getbuffer())

    audio_file = st.file_uploader("🎵 Аудио (Обязательно)", type=['mp3', 'wav', 'm4a'])

    with st.expander("🎤 Улучшить распознавание (Сложные песни)", expanded=False):
        voice_file = st.file_uploader("Чистый голос (без музыки)", type=['mp3', 'wav', 'm4a'],
                                      help="Загрузи сюда акапеллу, чтобы Whisper не сбивался из-за музыки")
        prompt_input = st.text_area("Текст песни (Подсказка)",
                                    placeholder="Вставьте сюда текст песни, чтобы нейросеть знала слова заранее...",
                                    height=100)

    csv_file = st.file_uploader("📝 Субтитры (CSV, если есть)", type=['csv'])

with col2:
    st.subheader("2. Вид")

    FONTS = [
        "DejaVuSans", "DejaVuSans-Bold", "DejaVuSerif", "DejaVuSerif-Bold",
        "LiberationSans-Regular", "LiberationSans-Bold",
        "NotoSans-Regular", "NotoSans-Bold",
        "Roboto-Regular", "Roboto-Bold",
        "Ubuntu-Regular", "Ubuntu-Bold",
        "OpenSans-Regular", "OpenSans-Bold",
    ]

    font = st.selectbox("Шрифт", FONTS, index=0)
    size = st.slider("Размер", 40, 150, 75)
    offset = st.slider("↕️ Положение", -800, 800, 0, step=20)

    with st.expander("📌 Настройки заголовка (Статичный текст)", expanded=False):
        static_text = st.text_area("Текст заголовка (постоянно висит)", placeholder="Например: Стихи Есенина")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st_font = st.selectbox("Шрифт заголовка", FONTS, index=0)
            st_color = st.color_picker("Цвет заголовка", "#FFFF00")
        with s_col2:
            st_size = st.slider("Размер заголовка", 30, 150, 60)
            st_pos = st.slider("Позиция Y (0-верх, 1920-низ)", 0, 1920, 500)

    if img_path:
        st.caption("Превью (Прим. масштаб)")
        prev = create_preview_image(img_path, font + ".ttf", size, offset, "ВАШ ТЕКСТ ТУТ",
                                    static_text, st_font + ".ttf", st_size, st_color, st_pos)
        prev.thumbnail((350, 622))
        st.image(prev)

# --- MAIN LOGIC ---
if not img_path or not audio_file:
    st.info("👈 Загрузите картинку и аудио слева, чтобы начать.")
else:
    aud_path = os.path.join(WORK_DIR, "input_audio.mp3")

    if "current_audio_name" not in st.session_state or st.session_state["current_audio_name"] != audio_file.name:
        st.session_state["words_data"] = None
        st.session_state["current_audio_name"] = audio_file.name
        with open(aud_path, "wb") as f:
            f.write(audio_file.getbuffer())

    st.divider()

    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            df.columns = df.columns.str.strip()
            required = {'start', 'end', 'word'}
            if required.issubset(df.columns) and st.session_state.get("words_data") is None:
                st.session_state["words_data"] = df.to_dict('records')
                st.success(f"✅ Субтитры загружены из {csv_file.name}")
                st.rerun()
        except Exception as e:
            st.error(f"Ошибка CSV: {e}")

    if st.session_state.get("words_data") is None:
        if st.button("🎧 1. РАСПОЗНАТЬ ТЕКСТ (Whisper)", type="primary"):
            with st.spinner("Слушаю аудио..."):
                try:
                    target_audio = aud_path
                    if voice_file:
                        v_path = os.path.join(WORK_DIR, "temp_voice.mp3")
                        with open(v_path, "wb") as f:
                            f.write(voice_file.getbuffer())
                        target_audio = v_path
                        st.toast("Используем файл с чистым голосом для распознавания!")

                    words_raw = get_word_timestamps(target_audio, prompt_input)
                    st.session_state["words_data"] = [
                        {"start": w.start, "end": w.end, "word": w.word}
                        for w in words_raw
                    ]
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка Whisper: {e}")

    if st.session_state.get("words_data") is not None:
        st.subheader("📝 2. Проверка текста")
        st.caption("Whisper мог ошибиться. Исправьте слова в таблице (тайминги лучше не трогать).")

        edited_words = st.data_editor(
            st.session_state["words_data"],
            column_config={
                "start": st.column_config.NumberColumn("Начало", format="%.2f", disabled=False),
                "end": st.column_config.NumberColumn("Конец", format="%.2f", disabled=False),
                "word": st.column_config.TextColumn("Слово (Кликни чтобы править)", width="large")
            },
            use_container_width=True,
            num_rows="dynamic",
            height=300,
            key="editor"
        )

        if st.button("🔄 Упорядочить строки по времени"):
            if isinstance(st.session_state["words_data"], list):
                st.session_state["words_data"] = sorted(st.session_state["words_data"], key=lambda x: x.get('start', 0))
                st.rerun()

        st.divider()

        if st.button("🎬 3. СОЗДАТЬ ВИДЕО (РЕНДЕР)", type="primary"):
            with st.status("Создание видео...", expanded=True):
                try:
                    words_sorted = sorted(edited_words, key=lambda x: x.get('start', 0))

                    st.write("Генерация субтитров...")
                    ass_path = os.path.join(OUTPUT_DIR, "subs.ass")
                    generate_karaoke_ass(words_sorted, ass_path, font, size, 4, offset,
                                        static_text, st_font, st_size, st_color, st_pos)

                    final_img_path = os.path.join(OUTPUT_DIR, "final_bg.jpg")
                    with Image.open(img_path) as im:
                        im_resized = resize_to_shorts(im).convert("RGB")
                        im_resized.save(final_img_path, quality=95)

                    st.write("Склейка (FFmpeg)...")
                    out_file = os.path.join(OUTPUT_DIR, "FINAL_SHORT.mp4")

                    cmd = [
                        "ffmpeg", "-y", "-loop", "1", "-i", final_img_path, "-i", aud_path,
                        "-vf", f"ass={os.path.basename(ass_path)}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest",
                        "FINAL_SHORT.mp4"
                    ]

                    process = subprocess.Popen(cmd, cwd=OUTPUT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.communicate()

                    if process.returncode == 0:
                        st.success("ГОТОВО!")
                        st.balloons()

                        with open(out_file, "rb") as f:
                            st.download_button("📩 Скачать файл", f, "FINAL_SHORT.mp4")
                    else:
                        st.error("Ошибка при рендере FFmpeg")

                except Exception as e:
                    st.error(f"Ошибка: {e}")

        if st.button("🔄 Сбросить и загрузить другое аудио"):
            del st.session_state["words_data"]
            st.rerun()

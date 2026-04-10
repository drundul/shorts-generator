
import streamlit as st
import os
import subprocess
from datetime import timedelta
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np
import pandas as pd
import tempfile
import re
import shutil

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
WORK_DIR = "/tmp/shorts_gen"
ASSETS_DIR = os.path.join(WORK_DIR, "assets")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
OVERLAY_PATH = os.path.join(ASSETS_DIR, "shorts_overlay.png")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Копируем шрифты в рабочую папку (путь без пробелов и спецсимволов — безопасно для FFmpeg)
FFMPEG_FONTS_DIR = os.path.join(OUTPUT_DIR, "fonts")
os.makedirs(FFMPEG_FONTS_DIR, exist_ok=True)
repo_fonts_dir = "fonts"
if os.path.exists(repo_fonts_dir):
    linux_fonts_dir = os.path.expanduser("~/.fonts")
    os.makedirs(linux_fonts_dir, exist_ok=True)
    fonts_copied = False
    for f in os.listdir(repo_fonts_dir):
        if f.endswith(".ttf") or f.endswith(".otf"):
            src = os.path.join(repo_fonts_dir, f)
            # Копируем в системную папку Linux (для fontconfig)
            dst = os.path.join(linux_fonts_dir, f)
            if not os.path.exists(dst):
                try:
                    shutil.copy(src, dst)
                    fonts_copied = True
                except:
                    pass
            # Копируем в рабочую папку FFmpeg (путь без пробелов)
            dst_ffmpeg = os.path.join(FFMPEG_FONTS_DIR, f)
            if not os.path.exists(dst_ffmpeg):
                try:
                    shutil.copy(src, dst_ffmpeg)
                except:
                    pass
    if fonts_copied:
        try:
            subprocess.run(["fc-cache", "-f", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

# OpenAI key from Streamlit Secrets
api_key = st.secrets.get("OPENAI_API_KEY", "")
if not api_key:
    st.error("🔑 Ошибка: OPENAI_API_KEY не найден в secrets.toml!")
    st.stop()

# Инициализируем клиента с таймаутом, чтобы избежать бесконечного ожидания при плохом соединении
client = OpenAI(
    api_key=api_key,
    timeout=60.0,  # 60 секунд на запрос
    max_retries=3  # автоматический повтор при сетевых сбоях
)

# --- FUNC: SMART RESIZE ---
def resize_to_video(image, width=1080, height=1920, scale_mode="Обрезать (Без краев)"):
    if scale_mode == "Вписать (Черные края)":
        return ImageOps.pad(image, (width, height), method=Image.Resampling.LANCZOS, color=(0, 0, 0))
    return ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

# --- FUNC: CREATE OVERLAY ---
def ensure_overlay_exists(width=1080, height=1920):
    # Only create/use overlay for vertical shorts right now
    if width != 1080 or height != 1920:
        return ""
    
    if os.path.exists(OVERLAY_PATH):
        return OVERLAY_PATH
    os.makedirs(ASSETS_DIR, exist_ok=True)
    W, H = width, height
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
    return OVERLAY_PATH

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

def fix_whisper_timings(words):
    """
    Создает "микро-паузы" между слипшимися словами.
    Если слова накладываются или конец одного = начало другого, 
    то немного подрезает конец первого слова.
    """
    if not words:
        return words
        
    res = [{"start": w.start, "end": w.end, "word": w.word} for w in words]
    
    for i in range(len(res) - 1):
        curr_w = res[i]
        next_w = res[i+1]
        
        # Проверяем зазор между словами
        if next_w['start'] - curr_w['end'] < 0.04:
            new_end = next_w['start'] - 0.04
            # Оставляем минимальную длину для текущего слова 0.05с
            if new_end - curr_w['start'] >= 0.05:
                curr_w['end'] = new_end
            else:
                curr_w['end'] = curr_w['start'] + 0.05
                # Сдвигаем начало следующего слова, если оно наползает
                if next_w['start'] <= curr_w['end']:
                    next_w['start'] = curr_w['end'] + 0.02
                    # Предотвращаем инверсию (начало > конец)
                    if next_w['end'] <= next_w['start']:
                        next_w['end'] = next_w['start'] + 0.05

    return res

# --- FUNC: HELPER ---
def wrap_text_to_width(text, font, max_width):
    if not text:
        return []
    dummy_img = Image.new("RGBA", (1, 1))
    draw_obj = ImageDraw.Draw(dummy_img)
    lines = []
    for paragraph in str(text).split('\n'):
        words = paragraph.split(' ')
        current_line = []
        for word in list(filter(None, words)): # ignore empty spaces
            test_line = ' '.join(current_line + [word]) if current_line else word
            bbox = draw_obj.textbbox((0, 0), test_line, font=font)
            length = bbox[2] - bbox[0]
            if length <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
    return lines

def hex_to_ass_color(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r, g, b = hex_str[:2], hex_str[2:4], hex_str[4:]
        return f"&H00{b}{g}{r}"
    return "&H00FFFFFF"

def split_phrases_to_words(words):
    """
    Если элементы содержат пробелы (фразы из SRT), разбивает их на отдельные слова
    с пропорциональным распределением тайминга по количеству символов.
    """
    result = []
    for entry in words:
        text = str(entry.get('word', '')).strip()
        parts = text.split()
        if len(parts) <= 1:
            result.append(entry)
            continue
        # Distribute timing proportionally by character count
        start = float(entry['start'])
        end = float(entry['end'])
        total_dur = end - start
        total_chars = sum(len(p) for p in parts)
        if total_chars == 0:
            result.append(entry)
            continue
        cursor = start
        for p in parts:
            word_dur = total_dur * (len(p) / total_chars)
            result.append({"start": round(cursor, 3), "end": round(cursor + word_dur, 3), "word": p})
            cursor += word_dur
    return result

# --- FUNC: AUDIO VISUALIZER ---
def build_viz_filter(viz_style, vid_w, vid_h, viz_h, viz_margin, viz_color_hex):
    """
    Возвращает (viz_part, overlay_part) — части filter_complex для аудио-визуализатора.
    viz_part: фильтр извлечения аудио-данных -> [viz]
    overlay_part: наложение [viz] на [bg] -> [v_out_label]
    """
    color = viz_color_hex.lstrip('#')
    y_pos = vid_h - viz_h - viz_margin

    if viz_style == "bars":
        viz = f"[1:a]showfreqs=s={vid_w}x{viz_h}:mode=bar:ascale=sqrt:fscale=log:colors=0x{color},format=rgba,colorkey=0x000000:0.1:0.5[viz]"
        overlay = f"[bg][viz]overlay=0:{y_pos}:format=auto"
    elif viz_style == "wave":
        viz = f"[1:a]showwaves=s={vid_w}x{viz_h}:mode=line:colors=0x{color}:draw=full,format=rgba,colorkey=0x000000:0.1:0.1[viz]"
        overlay = f"[bg][viz]overlay=0:{y_pos}:format=auto"
    elif viz_style == "cqt":
        viz = f"[1:a]showcqt=s={vid_w}x{viz_h}:text=0:axis=0:sono_h=0:bar_g=2:bar_v=15:bar_t=0.5,format=rgba,colorkey=0x000000:0.1:0.5[viz]"
        overlay = f"[bg][viz]overlay=0:{y_pos}:format=auto"
    elif viz_style == "fire":
        viz = f"[1:a]showspectrum=s={vid_w}x{viz_h}:slide=scroll:mode=separate:color=magma:scale=sqrt,format=rgba,colorkey=0x000000:0.1:0.5[viz]"
        overlay = f"[bg][viz]overlay=0:{y_pos}:format=auto"
    elif viz_style == "smoke":
        viz = f"[1:a]showspectrum=s={vid_w}x{viz_h}:slide=scroll:mode=separate:color=intensity:scale=log:saturation=0:win_func=hann,format=rgba,colorkey=0x000000:0.02:0.3[viz]"
        overlay = f"[bg][viz]overlay=0:{y_pos}:format=auto"
    elif viz_style == "reactor":
        r_size = min(vid_w, viz_h)
        x_pos = (vid_w - r_size) // 2
        viz = f"[1:a]avectorscope=s={r_size}x{r_size}:zoom=1.5:rc=255:gc=255:bc=255:rf=0:gf=0:bf=0:draw=line,format=rgba,colorkey=0x000000:0.1:0.5[viz]"
        overlay = f"[bg][viz]overlay={x_pos}:{vid_h - r_size - viz_margin}:format=auto"
    elif viz_style == "line_center":
        viz = f"[1:a]showwaves=s={vid_w}x{viz_h}:mode=cline:colors=0x{color}:draw=full,format=rgba,colorkey=0x000000:0.1:0.1[viz]"
        overlay = f"[bg][viz]overlay=0:{y_pos}:format=auto"
    else:
        return None, None

    return viz, overlay

# --- FUNC: GRADIENT OVERLAY (Cinematic Vignette) ---
def create_gradient_overlay_png(path, width, height, dark_zone_ratio=0.5, max_opacity=0.65):
    """
    Создаёт PNG с плавным тёмным градиентом снизу (как в кино).
    Полностью прозрачный вверху — тёмный внизу.
    """
    grad_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_g = ImageDraw.Draw(grad_img)
    grad_start_y = int(height * (1 - dark_zone_ratio))
    zone_height = height - grad_start_y
    for y in range(grad_start_y, height):
        # Кубическое затухание (**3) делает градиент очень мягким сверху и плотным только в самом низу
        progress = (y - grad_start_y) / max(zone_height, 1)
        progress = progress ** 3.0
        alpha = int(255 * max_opacity * progress)
        draw_g.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    grad_img.save(path, "PNG")
    return path


def build_image_render_cmd(final_img_path, aud_path, audio_dur, vid_w, vid_h,
                           viz_style, viz_h, viz_margin, viz_color,
                           gradient_png_path=None, ass_basename=None, max_duration=None):
    """
    Строит FFmpeg-команду для рендера на фото-фоне.
    Обрабатывает все комбинации: градиент + визуализатор + субтитры.
    max_duration: если задан (секунды), обрезает видео до этой длины (но не длиннее аудио).
    """
    use_viz = viz_style != "none"
    use_gradient = gradient_png_path is not None
    use_ass = ass_basename is not None

    # Эффективная длина: не длиннее аудио и не длиннее лимита пользователя
    if max_duration is not None:
        effective_dur = str(min(float(audio_dur), float(max_duration)))
    else:
        effective_dur = audio_dur

    base_in = ["ffmpeg", "-y", "-loop", "1", "-t", audio_dur, "-i", final_img_path, "-i", aud_path]
    # Явные настройки качества: CRF 23, tune stillimage (для фото), битрейт звука 128k
    # -map_metadata -1 — очищаем все метаданные из итогового файла
    # -t effective_dur — ограничиваем длину (если задан max_duration)
    encode = ["-c:v", "libx264", "-crf", "26", "-preset", "faster", "-tune", "stillimage",
              "-level", "4.1", "-r", "24", "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
              "-map_metadata", "-1", "-t", effective_dur, "FINAL_SHORT.mp4"]

    # Простой случай: без градиента и визуализатора
    if not use_gradient and not use_viz:
        if use_ass:
            return base_in + ["-vf", f"ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'"] + encode
        else:
            return base_in + encode

    # Сложный случай → filter_complex
    # цепочка: scale → gradient → visualizer → ASS
    fc = [f"[0:v]scale={vid_w}:{vid_h}[bg_s]"]
    cur = "bg_s"
    extra_inputs = []

    if use_gradient:
        # ВАЖНО: -t audio_dur ограничивает длину PNG-инпута, иначе FFmpeg висит бесконечно
        extra_inputs = ["-loop", "1", "-t", audio_dur, "-i", gradient_png_path]
        # format=auto нужен для корректного наложения RGBA (альфа-канал градиента)
        fc.append(f"[{cur}][2:v]overlay=0:0:format=auto[bg_g]")
        cur = "bg_g"

    if use_viz:
        viz_flt, overlay_flt = build_viz_filter(viz_style, vid_w, vid_h, viz_h, viz_margin, viz_color)
        if viz_flt:
            adj_ov = overlay_flt.replace("[bg]", f"[{cur}]")
            fc.append(viz_flt)
            fc.append(f"{adj_ov}[bg_v]")
            cur = "bg_v"

    if use_ass:
        fc.append(f"[{cur}]ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]")
        cur = "vout"

    return base_in + extra_inputs + [
        "-filter_complex", ";".join(fc),
        "-map", f"[{cur}]", "-map", "1:a"
    ] + encode


def generate_karaoke_ass(words, output_ass_path, font_name, font_size, max_words_per_screen, offset_y,
                         static_text="", static_font="Arial", static_size=60, static_color="#FFFFFF", static_pos_y=500,
                         base_color_hex="#FFFFFF", highlight_color_hex="#FFFF00", uppercase=False, width=1080, height=1920,
                         sub_style="karaoke",
                         cta_text="", cta_font="Arial", cta_size=35, cta_color="#FFFFFF", cta_pos_y=1800,
                         cta_emoji="", cta_animate=False):
    # For karaoke, one_word, box, and teleprompter modes, split phrases into individual words
    if sub_style in ("karaoke", "one_word", "box", "teleprompter"):
        words = split_phrases_to_words(words)

    def get_ass_font_info(fname):
        base_name = fname.replace('.ttf', '').replace('.TTF', '')
        font_paths = [
            f"fonts/{base_name}.ttf",
            f"{base_name}.ttf",
            f"C:\\Windows\\Fonts\\{base_name}.ttf",
            f"C:\\Windows\\Fonts\\{base_name}",
            "fonts/arial.ttf"
        ]
        family = base_name
        is_bold = False
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    f = ImageFont.truetype(fp, 20)
                    family, style = f.getname()
                    is_bold = ("Bold" in style or "Black" in style)
                    break
                except:
                    pass
        return family, is_bold

    main_family, main_bold = get_ass_font_info(font_name)
    static_family, static_bold = get_ass_font_info(static_font)
    cta_family, cta_bold = get_ass_font_info(cta_font)
    
    main_bold_flag = "-1" if main_bold else "0"
    static_bold_flag = "-1" if static_bold else "0"
    cta_bold_flag = "-1" if cta_bold else "0"
    ass_cta_color = hex_to_ass_color(cta_color)

    center_y = int(height/2 + offset_y)
    center_x = int(width/2)
    base_color = hex_to_ass_color(base_color_hex)
    highlight_color = hex_to_ass_color(highlight_color_hex)
    ass_static_color = hex_to_ass_color(static_color)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BaseStyle,{main_family},{font_size},{base_color},&H00FFFFFF,&H00000000,&H80000000,{main_bold_flag},0,0,0,100,100,0,0,1,3,0,5,50,50,0,1
Style: BoxStyle,{main_family},{font_size},&H00FFFFFF,&H00FFFFFF,{highlight_color},&H00000000,{main_bold_flag},0,0,0,100,100,0,0,3,12,0,5,50,50,0,1
Style: StaticStyle,{static_family},{static_size},{ass_static_color},&H00FFFFFF,&H00000000,&H80000000,{static_bold_flag},0,0,0,100,100,0,0,1,2,0,5,50,50,0,1
Style: CTAStyle,{cta_family},{cta_size},{ass_cta_color},&H00FFFFFF,&H00000000,&H80000000,{cta_bold_flag},0,0,0,100,100,0,0,1,2,0,5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    if static_text:
        font = None
        st_base = static_font.replace('.ttf', '').replace('.TTF', '')
        font_paths = [
            f"fonts/{st_base}.ttf",
            f"{st_base}.ttf",
            f"C:\\Windows\\Fonts\\{st_base}.ttf",
            f"C:\\Windows\\Fonts\\{st_base}",
            st_base.replace("Regular", "Bold") + ".ttf",
            "fonts/arial.ttf",
            "arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]
        for fp in font_paths:
            try: font = ImageFont.truetype(fp, static_size); break
            except: continue
        if not font: font = ImageFont.load_default()
        
        wrapped_lines = wrap_text_to_width(static_text, font, width - 100)
        formatted_static = "\\N".join(wrapped_lines)
        static_event = f"Dialogue: 0,0:00:00.00,1:00:00.00,StaticStyle,,0,0,0,,{{\\pos({center_x},{static_pos_y})}}{formatted_static}"
        events.append(static_event)

    # === MODE: ONE WORD AT A TIME ===
    if sub_style == "one_word":
        for w_obj in words:
            w_text = str(w_obj.get('word', '')).strip()
            if uppercase:
                w_text = w_text.upper()
            if not w_text:
                continue
            ass_start = time_to_ass_format(w_obj['start'])
            ass_end = time_to_ass_format(w_obj['end'])
            line = f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{{\\fad(50,50)\\pos({center_x},{center_y})}}{w_text}"
            events.append(line)

    # === MODE: CLASSIC SUBTITLES (show/hide blocks) ===
    elif sub_style == "classic":
        for w_obj in words:
            w_text = str(w_obj.get('word', '')).strip()
            if uppercase:
                w_text = w_text.upper()
            if not w_text:
                continue
            # Replace newlines for ASS format
            w_text = w_text.replace("\n", "\\N")
            ass_start = time_to_ass_format(w_obj['start'])
            ass_end = time_to_ass_format(w_obj['end'])
            line = f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{{\\fad(100,100)\\pos({center_x},{center_y})}}{w_text}"
            events.append(line)

    # === MODE: BOX HIGHLIGHT (colored box behind active word) ===
    elif sub_style == "box":
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
                if uppercase:
                    w_text = w_text.upper()
                rel_start = int((w_obj['start'] - line_start) * 1000)
                rel_end = int((w_obj['end'] - line_start) * 1000)

                # Explicitly manage base state and transition border thickness and color mid-flight
                # \bord16 creates a thick outline representing a box pill behind the text.
                effect = (
                    f"{{\\bord3\\3c&H00000000}}"
                    f"{{\\t({rel_start},{rel_start+1},\\bord16\\3c{highlight_color})}}"
                    f"{{\\t({rel_end},{rel_end+1},\\bord3\\3c&H00000000)}}"
                    f"{w_text} "
                )
                text_line += effect

            full_line = f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{{\\fad(100,100)\\pos({center_x},{center_y})}}{text_line.strip()}"
            events.append(full_line)

    # === MODE: KARAOKE (word-by-word highlight in groups) ===
    elif sub_style == "karaoke":
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
                if uppercase:
                    w_text = w_text.upper()
                rel_start = int((w_obj['start'] - line_start) * 1000)
                rel_end = int((w_obj['end'] - line_start) * 1000)

                effect = (
                    f"{{\\1c{base_color}\\t({rel_start},{rel_start+1},\\1c{highlight_color})}}"
                    f"{{\\t({rel_end},{rel_end+1},\\1c{base_color})}}"
                    f"{w_text} "
                )
                text_line += effect

            full_line = f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{{\\fad(100,100)\\pos({center_x},{center_y})}}{text_line.strip()}"
            events.append(full_line)

    # === MODE: TELEPROMPTER (SMOOTH SCROLL) ===
    elif sub_style == "teleprompter":
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

        g = int(font_size * 1.8)  # Увеличенный интервал между строками (был 1.4)
        d = 250  # Время анимации сдвига (ms)

        for i, chunk in enumerate(chunks):
            if not chunk: continue
            line_start = chunk[0]['start']
            # Строка висит на экране, пока не начнется следующая (или +0.5с в конце видео)
            if i + 1 < len(chunks) and chunks[i+1]:
                line_end = chunks[i+1][0]['start']
            else:
                line_end = chunk[-1]['end'] + 0.5

            ass_start = time_to_ass_format(line_start)
            ass_end = time_to_ass_format(line_end)

            # --- АКТИВНАЯ СТРОКА (i) — в центре ---
            text_line = ""
            for w_obj in chunk:
                w_text = w_obj['word']
                if uppercase: w_text = w_text.upper()
                rel_start = int((w_obj['start'] - line_start) * 1000)
                rel_end = int((w_obj['end'] - line_start) * 1000)
                effect = f"{{\\1c{base_color}\\t({rel_start},{rel_start+1},\\1c{highlight_color})}}{{\\t({rel_end},{rel_end+1},\\1c{base_color})}}{w_text} "
                text_line += effect
            
            x, y = center_x, center_y
            
            # Для самого первого кадра просто появляемся, для остальных — эффект всплытия снизу
            if i == 0:
                act_prefix = f"{{\\pos({x},{y})\\alpha&HFF&\\t(0,{d},\\alpha&H00&)}}"
            else:
                act_prefix = f"{{\\move({x},{y+g},{x},{y},0,{d})\\alpha&H80&\\t(0,{d},\\alpha&H00&)}}"
            
            events.append(f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{act_prefix}{text_line.strip()}")

            # --- ПРЕДЫДУЩАЯ СТРОКА (i-1) — уходит вверх ---
            if i - 1 >= 0:
                prev_text = " ".join([w['word'].upper() if uppercase else w['word'] for w in chunks[i-1]])
                prv_prefix = f"{{\\move({x},{y},{x},{y-g},0,{d})\\alpha&H00&\\t(0,{d},\\alpha&H80&)}}"
                events.append(f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{prv_prefix}{prev_text}")

            # --- СЛЕДУЮЩАЯ СТРОКА (i+1) — готовится снизу ---
            if i + 1 < len(chunks):
                next_text = " ".join([w['word'].upper() if uppercase else w['word'] for w in chunks[i+1]])
                if i == 0:
                    nxt_prefix = f"{{\\pos({x},{y+g})\\alpha&HFF&\\t(0,{d},\\alpha&H80&)}}"
                else:
                    nxt_prefix = f"{{\\move({x},{y+2*g},{x},{y+g},0,{d})\\alpha&HFF&\\t(0,{d},\\alpha&H80&)}}"
                events.append(f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{nxt_prefix}{next_text}")

            # --- ИСЧЕЗАЮЩАЯ СТРОКА (i-2) — растворяется в самом верху ---
            if i - 2 >= 0:
                old_text = " ".join([w['word'].upper() if uppercase else w['word'] for w in chunks[i-2]])
                old_prefix = f"{{\\move({x},{y-g},{x},{y-2*g},0,{d})\\alpha&H80&\\t(0,{d},\\alpha&HFF&)}}"
                events.append(f"Dialogue: 0,{ass_start},{ass_end},BaseStyle,,0,0,0,,{old_prefix}{old_text}")


    # === CTA TEXT (Call to Action в нижней чёрной полосе) ===
    if cta_text:
        full_cta = cta_text
        if cta_emoji:
            full_cta = f"{cta_text}\\N{cta_emoji}"

        if cta_animate and cta_emoji:
            # Статичный текст CTA (без эмодзи)
            cta_event = f"Dialogue: 0,0:00:00.00,1:00:00.00,CTAStyle,,0,0,0,,{{\\pos({center_x},{cta_pos_y})}}{cta_text}"
            events.append(cta_event)
            # Пульсирующий эмодзи — цикл из коротких интервалов
            emoji_y = cta_pos_y + cta_size + 10
            for sec in range(120):  # покрываем до 2 минут видео
                t_start = time_to_ass_format(sec * 0.8)
                t_end = time_to_ass_format((sec + 1) * 0.8)
                pulse = (
                    f"{{\\pos({center_x},{emoji_y})"
                    f"\\fscx100\\fscy100"
                    f"\\t(0,400,\\fscx130\\fscy130)"
                    f"\\t(400,800,\\fscx100\\fscy100)}}"
                )
                emoji_event = f"Dialogue: 0,{t_start},{t_end},CTAStyle,,0,0,0,,{pulse}{cta_emoji}"
                events.append(emoji_event)
        else:
            # Простой статичный CTA (текст + эмодзи без анимации)
            cta_event = f"Dialogue: 0,0:00:00.00,1:00:00.00,CTAStyle,,0,0,0,,{{\\pos({center_x},{cta_pos_y})}}{full_cta}"
            events.append(cta_event)

    with open(output_ass_path, "w", encoding="utf-8-sig") as f:
        f.write(header + "\n".join(events))

def generate_srt_string(words):
    def format_srt_time(seconds):
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = td.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    lines = []
    chunks = []
    current_chunk = []
    for w in words:
        txt = str(w.get('word', ''))
        is_capital = txt[0].isupper() if txt else False
        if len(current_chunk) >= 4 or (is_capital and len(current_chunk) > 0):
            chunks.append(current_chunk)
            current_chunk = []
        current_chunk.append(w)
    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks, 1):
        if not chunk: continue
        line_start = format_srt_time(chunk[0]['start'])
        line_end = format_srt_time(chunk[-1]['end'])
        text = " ".join([str(w['word']).strip() for w in chunk])
        lines.append(f"{i}\n{line_start} --> {line_end}\n{text}\n")
    return "\n".join(lines)

def parse_srt_content(srt_text):
    blocks = re.split(r'\n\s*\n', srt_text.strip())
    words_data = []
    
    def time_to_sec(t):
        t = t.strip()
        h, m, s_ms = t.split(':')
        s, ms = s_ms.replace('.', ',').split(',')
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
        
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            if '-->' in time_line:
                start_str, end_str = time_line.split('-->')
                start_sec = time_to_sec(start_str)
                end_sec = time_to_sec(end_str)
                text = " ".join(lines[2:]).strip()
                words_data.append({"start": start_sec, "end": end_sec, "word": text})
    return words_data

# --- FUNC: PREVIEW ---
def create_preview_image(bg_image_path, font_name, font_size, offset_y, text_sample="ВАШ ТЕКСТ ТУТ\nСМОТРИТСЯ ТАК",
                         static_text="", static_font="Arial", static_size=60, static_color="#FFFFFF", static_pos_y=500,
                         base_color_hex="#FFFFFF", uppercase_text=False, width=1080, height=1920,
                         no_subs=False, viz_style="none", viz_h=250, viz_margin=0, viz_color_hex="#FFFFFF",
                         use_gradient=False, gradient_zone=50, gradient_opacity=65, sub_style="karaoke",
                         video_scale="Обрезать (Без краев)",
                         cta_text="", cta_font="Arial", cta_size=35, cta_color="#FFFFFF", cta_pos_y=1800, cta_emoji=""):
    bg = Image.open(bg_image_path).convert("RGBA")
    bg = resize_to_video(bg, width, height, scale_mode=video_scale)

    # Градиентная виньетка (улучшенная кривая)
    if use_gradient:
        g_start = int(height * (1 - gradient_zone / 100))
        grad_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad_layer)
        g_zone_h = height - g_start
        for gy in range(g_start, height):
            gprog = ((gy - g_start) / max(g_zone_h, 1)) ** 2.2
            galpha = int(255 * (gradient_opacity / 100) * gprog)
            gd.line([(0, gy), (width, gy)], fill=(0, 0, 0, galpha))
        bg = Image.alpha_composite(bg, grad_layer)

    if uppercase_text:
        text_sample = text_sample.upper()

    txt_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(txt_layer)

    def draw_centered_on_layer(draw_obj, text, target_y, f_name, f_sz, color=(255, 255, 255, 255)):
        font = None
        # Убираем .ttf если уже есть, чтобы не дублировать
        base_name = f_name.replace('.ttf', '').replace('.TTF', '')
        font_paths = [
            f"fonts/{base_name}.ttf",
            f"{base_name}.ttf",
            f"C:\\Windows\\Fonts\\{base_name}.ttf",
            f"C:\\Windows\\Fonts\\{base_name}",
            base_name.replace("Regular", "Bold") + ".ttf",
            "fonts/arial.ttf",
            "arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]
        for fp in font_paths:
            try: font = ImageFont.truetype(fp, f_sz); break
            except: continue
        if not font: font = ImageFont.load_default()

        # Используем встроенное центрирование Pillow, чтобы оно на 100% совпадало с Alignment 5 в ASS (libass)
        # stroke_width=3 имитирует параметр Outline=3 в ASS (прибавка к ширине)
        draw_obj.multiline_text((width / 2, target_y), text, font=font, fill=color, align="center", anchor="mm",
                                stroke_width=3, stroke_fill=(0,0,0,160))

    if base_color_hex.startswith('#'):
        h_b = base_color_hex.lstrip('#')
        rgb_base = tuple(int(h_b[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    else:
        rgb_base = (255, 255, 255, 255)

    dyn_y = (height / 2) + offset_y
    if not no_subs:
        if sub_style == "teleprompter":
            gap = int(font_size * 1.8)
            p_color = (rgb_base[0], rgb_base[1], rgb_base[2], 80) # Полупрозрачный для соседей
            draw_centered_on_layer(d, "ПРЕДЫДУЩАЯ СТРОКА ТЕКСТА", dyn_y - gap, font_name, font_size, color=p_color)
            draw_centered_on_layer(d, "ТЕКУЩАЯ АКТИВНАЯ СТРОКА", dyn_y, font_name, font_size, color=rgb_base)
            draw_centered_on_layer(d, "СЛЕДУЮЩАЯ СТРОКА ТЕКСТА", dyn_y + gap, font_name, font_size, color=p_color)
        else:
            draw_centered_on_layer(d, text_sample, dyn_y, font_name, font_size, color=rgb_base)


    if static_text:
        if static_color.startswith('#'):
            h = static_color.lstrip('#')
            rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        else:
            rgb = (255, 255, 255, 255)
            
        font = None
        st_base = static_font.replace('.ttf', '').replace('.TTF', '')
        font_paths = [
            f"fonts/{st_base}.ttf",
            f"{st_base}.ttf",
            f"C:\\Windows\\Fonts\\{st_base}.ttf",
            f"C:\\Windows\\Fonts\\{st_base}",
            st_base.replace("Regular", "Bold") + ".ttf",
            "fonts/arial.ttf",
            "arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]
        for fp in font_paths:
            try: font = ImageFont.truetype(fp, static_size); break
            except: continue
        if not font: font = ImageFont.load_default()
        
        wrapped_lines = wrap_text_to_width(static_text, font, width - 100)
        wrapped_text = "\n".join(wrapped_lines)

        draw_centered_on_layer(d, wrapped_text, static_pos_y, static_font, static_size, color=rgb)

    if viz_style != "none":
        viz_y = height - viz_h - viz_margin
        v_h_hex = viz_color_hex.lstrip('#')
        if len(v_h_hex) == 6:
            v_rgb = tuple(int(v_h_hex[i:i + 2], 16) for i in (0, 2, 4))
        else:
            v_rgb = (255, 255, 255)
            
        # Рисуем полупрозрачную плашку визуализатора
        d.rectangle([0, viz_y, width, viz_y + viz_h], fill=v_rgb + (80,))
        
        # Подпись
        try:
            fnt = ImageFont.truetype("Arial", 40)
        except:
            fnt = ImageFont.load_default()
        d.text((40, viz_y + 20), f"🎵 ЭФФЕКТ: {viz_style}", font=fnt, fill=(255,255,255,255))

    # CTA-текст в нижней чёрной полосе
    if cta_text:
        if cta_color.startswith('#'):
            h_cta = cta_color.lstrip('#')
            rgb_cta = tuple(int(h_cta[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        else:
            rgb_cta = (255, 255, 255, 255)
        
        cta_display = cta_text
        if cta_emoji:
            cta_display = f"{cta_text}\n{cta_emoji}"
        draw_centered_on_layer(d, cta_display, cta_pos_y, cta_font, cta_size, color=rgb_cta)

    combined = Image.alpha_composite(bg, txt_layer)

    overlay_img_path = ensure_overlay_exists(width, height)
    if overlay_img_path and os.path.exists(overlay_img_path):
        overlay = Image.open(overlay_img_path).convert("RGBA")
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

st.title("📱 Shorts Generator V3")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Файлы")

    orientation = st.radio("Формат видео:", ["📱 Вертикальное 9:16 (Shorts, Reels)", "🖥️ Горизонтальное 16:9 (YouTube)"], horizontal=True)
    if "🖥" in orientation:
        vid_w, vid_h = 1920, 1080
    else:
        vid_w, vid_h = 1080, 1920

    bg_type = st.radio("Тип фона:", ["📷 Фото", "🎥 Видео"], horizontal=True)
    img_path = None
    video_path = None
    mute_video = False

    if bg_type == "📷 Фото":
        uploaded_img = st.file_uploader("📷 Загрузить фото (фон)", type=['jpg', 'png', 'jpeg'])
        if uploaded_img:
            img_path = os.path.join(WORK_DIR, "uploaded_bg.png")
            with open(img_path, "wb") as f:
                f.write(uploaded_img.getbuffer())
        video_scale = "Вписать (Черные края)" # default for logic
    else:
        uploaded_vid = st.file_uploader("🎥 Загрузить видео (вертикальное)", type=['mp4', 'mov', 'webm'])
        if uploaded_vid:
            video_path = os.path.join(WORK_DIR, "uploaded_bg.mp4")
            with open(video_path, "wb") as f:
                f.write(uploaded_vid.getbuffer())
        mute_video = st.checkbox("🔇 Убрать оригинальный звук из видео", value=True)
        video_scale = st.radio("Масштаб видео:", ["Обрезать (Без краев)", "Вписать (Черные края)", "Размытый фон"])

    audio_file = st.file_uploader("🎵 Аудио (Опционально, если есть видео)", type=['mp3', 'wav', 'm4a'])

    with st.expander("🎤 Улучшить распознавание (Сложные песни)", expanded=False):
        voice_file = st.file_uploader("Чистый голос (без музыки)", type=['mp3', 'wav', 'm4a'],
                                      help="Загрузи сюда акапеллу, чтобы Whisper не сбивался из-за музыки")
        prompt_input = st.text_area("Текст песни (Подсказка)",
                                    placeholder="Вставьте сюда текст песни, чтобы нейросеть знала слова заранее...",
                                    height=100)

    subs_file = st.file_uploader("📝 Предзагруженные субтитры (SRT или CSV)", type=['csv', 'srt'])

    with st.expander("⏱️ Ограничить длительность ролика", expanded=False):
        use_duration_limit = st.checkbox("Обрезать видео по времени", value=False,
                                         help="Финальное видео будет не длиннее указанного значения. Если аудио короче — видео всё равно остановится по аудио.")
        if use_duration_limit:
            target_duration = st.slider("Длительность (сек)", 5.0, 60.0, 10.0, step=1.0)
        else:
            target_duration = None

with col2:
    st.subheader("2. Вид")

    FONTS = [
        "Montserrat-Bold", "Montserrat-Regular",
        "Roboto-Black", "Roboto-Bold",
        "Oswald-Bold", "RussoOne-Regular", 
        "Comfortaa-Bold", "Arial"
    ]

    font = st.selectbox("Шрифт", FONTS, index=0)
    size = st.slider("Размер", 40, 150, 75)
    c1, c2 = st.columns(2)
    with c1:
        base_hex = st.color_picker("⬜ Основной цвет", "#FFFFFF")
    with c2:
        highlight_hex = st.color_picker("🎯 Цвет подсветки", "#FFFF00")
    uppercase_cb = st.checkbox("АБВ Весь текст заглавными (CAPS LOCK)", value=False)

    STYLES_MAP = {
        "🎤 Караоке (подсветка слов)": "karaoke", 
        "💬 По 1 слову (TikTok)": "one_word", 
        "🟩 Бокс-подсветка": "box", 
        "📺 Классические субтитры": "classic",
        "📜 Телесуфлер (Скролл строк)": "teleprompter"
    }

    no_subs = st.checkbox("🚫 Без субтитров (только аудио на фоне)", value=False,
                          help="Режим для подкастов: фото/видео + аудио без распознавания речи")
    if not no_subs:
        sub_style_label = st.selectbox("Стиль субтитров", list(STYLES_MAP.keys()), index=0)
        sub_style = STYLES_MAP[sub_style_label]
        words_per_line = st.slider("Слов в каждой строке", 2, 8, 5, help="4-5 — стандарт, 6-8 — для плотного текста подкаста")
    else:
        sub_style, words_per_line = "karaoke", 5

    offset = st.slider("↕️ Положение", -800, 800, 0, step=20)

    with st.expander("🌑 Контраст (виньетка под текстом)", expanded=False):
        use_gradient = st.checkbox(
            "Тёмная подложка (виньетка)", value=False,
            help="Полупрозрачное киноматическое затемнение снизу — текст читается на любом фоне"
        )
        if use_gradient:
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                gradient_opacity = st.slider("Интенсивность (%)", 20, 90, 65, step=5,
                                            help="65-75% для светлых фонов, 40-50% для тёмных")
            with g_col2:
                gradient_zone = st.slider("Зона (%)", 20, 80, 50, step=5,
                                         help="50 = нижняя половина экрана")
        else:
            gradient_opacity, gradient_zone = 65, 50

    with st.expander("📌 Настройки заголовка (Статичный текст)", expanded=False):
        static_text = st.text_area("Текст заголовка (постоянно висит)", placeholder="Например: Стихи Есенина")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st_font = st.selectbox("Шрифт заголовка", FONTS, index=0)
            st_color = st.color_picker("Цвет заголовка", "#FFFF00")
        with s_col2:
            st_size = st.slider("Размер заголовка", 30, 150, 60)
            st_pos = st.slider(f"Позиция Y (0-верх, {vid_h}-низ)", 0, vid_h, int(vid_h/4))

    with st.expander("🎵 Аудио-визуализатор (только для фото)", expanded=False):
        VIZ_STYLES = {
            "Нет": "none",
            "📊 Бары (Эквалайзер)": "bars",
            "🌊 Волна (Осциллоскоп)": "wave",
            "🎼 CQT (Хроматика)": "cqt",
            "〰️ Струна": "line_center",
            "🔥 Огонь (Спектрограмма)": "fire",
            "💨 Дым (Спектр)": "smoke",
            "🔵 Реактор (Фазовый скоп)": "reactor",
        }
        viz_style_label = st.selectbox("Стиль визуализатора", list(VIZ_STYLES.keys()), index=0)
        viz_style = VIZ_STYLES[viz_style_label]
        if viz_style != "none":
            viz_h = st.slider("Высота эффекта (px)", 80, 600, 250, step=20)
            viz_margin = st.slider("Отступ от низа (px)", 0, 400, 0, step=10)
            viz_color = st.color_picker("Цвет (для Баров, Волны, Струны)", "#FFFFFF")
        else:
            viz_h, viz_margin, viz_color = 250, 0, "#FFFFFF"

    # --- CTA (Call to Action) в нижней чёрной полосе ---
    cta_text = ""
    cta_emoji = ""
    cta_animate = False
    cta_font_sel = "Arial"
    cta_size_sel = 35
    cta_color_sel = "#FFFFFF"
    cta_pos_y_sel = int(vid_h * 0.92)  # ~92% высоты — нижняя чёрная полоса

    if video_scale == "Вписать (Черные края)":
        with st.expander("👇 CTA-текст (нижняя чёрная полоса)", expanded=False):
            cta_text = st.text_input("Текст призыва", placeholder="read caption",
                                     help="Текст, который будет постоянно висеть в нижней чёрной полосе")
            cta_emoji = st.text_input("Эмодзи / символ (опционально)", value="👇",
                                      help="Оставьте пустым, чтобы убрать. Можно использовать: 👇 ⬇️ 📖 🔥 и т.д.")
            if cta_emoji:
                cta_animate = st.checkbox("✨ Анимировать эмодзи (пульсация)", value=True)
            ct_col1, ct_col2 = st.columns(2)
            with ct_col1:
                cta_font_sel = st.selectbox("Шрифт CTA", FONTS, index=0, key="cta_font_sel")
                cta_color_sel = st.color_picker("Цвет CTA", "#FFFFFF", key="cta_color_pick")
            with ct_col2:
                cta_size_sel = st.slider("Размер CTA", 20, 80, 35, key="cta_size_sl")
                cta_pos_y_sel = st.slider(f"Позиция Y CTA (0-верх, {vid_h}-низ)", 0, vid_h, int(vid_h * 0.92), step=10, key="cta_pos_sl")


    # Preview with text overlay
    preview_img_path = None
    if img_path:
        preview_img_path = img_path
    elif video_path:
        # Extract a frame from video for preview
        frame_path = os.path.join(WORK_DIR, "preview_frame.jpg")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-ss", "1", "-frames:v", "1",
            "-q:v", "2", frame_path
        ], capture_output=True)
        if os.path.exists(frame_path):
            preview_img_path = frame_path

    if preview_img_path:
        st.caption("Превью текста на фоне")
        prev = create_preview_image(preview_img_path, font + ".ttf", size, offset, "ваш текст\nтут смотрится так",
                                    static_text, st_font + ".ttf", st_size, st_color, st_pos,
                                    base_color_hex=base_hex, uppercase_text=uppercase_cb, width=vid_w, height=vid_h,
                                    no_subs=no_subs, viz_style=viz_style, viz_h=viz_h, viz_margin=viz_margin, viz_color_hex=viz_color,
                                    use_gradient=use_gradient, gradient_zone=gradient_zone, gradient_opacity=gradient_opacity,
                                    sub_style=sub_style, video_scale=video_scale,
                                    cta_text=cta_text, cta_font=cta_font_sel + ".ttf", cta_size=cta_size_sel,
                                    cta_color=cta_color_sel, cta_pos_y=cta_pos_y_sel, cta_emoji=cta_emoji)
        # Scale preview to fit Streamlit column nicely
        prev_ratio = vid_w / vid_h
        prev.thumbnail((350, int(350 / prev_ratio)))
        st.image(prev)

# --- MAIN LOGIC ---
has_bg = img_path or video_path
if not has_bg and not audio_file:
    st.info("👈 Загрузите фон (фото или видео) слева, чтобы начать.")
elif not audio_file and not video_path:
    st.warning("👈 Загрузите либо отдельное аудио, либо видео со звуком.")
else:
    aud_path = os.path.join(WORK_DIR, "input_audio.mp3")

    current_audio_name = audio_file.name if audio_file else (uploaded_vid.name if video_path else "unknown")

    if "current_audio_name" not in st.session_state or st.session_state["current_audio_name"] != current_audio_name:
        st.session_state["words_data"] = None
        st.session_state["current_audio_name"] = current_audio_name
        
        if audio_file:
            with open(aud_path, "wb") as f:
                f.write(audio_file.getbuffer())
        elif video_path:
            with st.spinner("Извлекаем звук из видео..."):
                subprocess.run(["ffmpeg", "-y", "-i", video_path, "-q:a", "0", "-map", "a", aud_path], capture_output=True)
                if not os.path.exists(aud_path):
                    st.warning("⚠️ В этом видео нет звука. Будет сгенерировано видео без звука.")

    st.divider()

    # ============================
    # РЕЖИМ БЕЗ СУБТИТРОВ
    # ============================
    if no_subs:
        if st.button("🎬 СОЗДАТЬ ВИДЕО (без субтитров)", type="primary"):
            with st.status("Создание видео...", expanded=True):
                try:
                    out_file = os.path.join(OUTPUT_DIR, "FINAL_SHORT.mp4")
                    st.write("Подготовка файлов...")

                    ass_basename = None
                    if static_text or cta_text:
                        st.write("Генерация текстовых элементов...")
                        ass_path = os.path.join(OUTPUT_DIR, "subs_static.ass")
                        generate_karaoke_ass([], ass_path, font, size, words_per_line, offset,
                                            static_text, st_font, st_size, st_color, st_pos,
                                            base_color_hex=base_hex, highlight_color_hex=highlight_hex, uppercase=uppercase_cb,
                                            width=vid_w, height=vid_h, sub_style=sub_style,
                                            cta_text=cta_text, cta_font=cta_font_sel, cta_size=cta_size_sel,
                                            cta_color=cta_color_sel, cta_pos_y=cta_pos_y_sel,
                                            cta_emoji=cta_emoji, cta_animate=cta_animate)
                        ass_basename = os.path.basename(ass_path)

                    if video_path:
                        if video_scale == "Размытый фон":
                            base_vf = f"[0:v:0]split[a][b];[a]scale={vid_w}:{vid_h},boxblur=20:20[1];[b]scale={vid_w}:{vid_h}:force_original_aspect_ratio=decrease[2];[1][2]overlay=(W-w)/2:(H-h)/2"
                            if ass_basename:
                                base_vf += f",ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]"
                            else:
                                base_vf += "[vout]"
                        elif video_scale == "Обрезать (Без краев)":
                            base_vf = f"[0:v:0]scale={vid_w}:{vid_h}:force_original_aspect_ratio=increase,crop={vid_w}:{vid_h}"
                            if ass_basename:
                                base_vf += f",ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]"
                            else:
                                base_vf += "[vout]"
                        else:  # Вписать (Черные края)
                            base_vf = f"[0:v:0]scale={vid_w}:{vid_h}:force_original_aspect_ratio=decrease,pad={vid_w}:{vid_h}:(ow-iw)/2:(oh-ih)/2"
                            if ass_basename:
                                base_vf += f",ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]"
                            else:
                                base_vf += "[vout]"

                        audio_map = []
                        if mute_video:
                            if audio_file is not None:
                                audio_map = ["-map", "1:a"]
                            else:
                                audio_map = ["-an"]
                        else:
                            if audio_file is not None:
                                base_vf += ";[0:a][1:a]amix=inputs=2:duration=shortest[aout]"
                                audio_map = ["-map", "[aout]"]
                            else:
                                audio_map = ["-map", "0:a"]
                        
                        cmd = ["ffmpeg", "-y", "-i", video_path]
                        if os.path.exists(aud_path):
                            cmd.extend(["-i", aud_path])
                        
                        cmd.extend([
                            "-filter_complex", base_vf,
                            "-map", "[vout]"
                        ])
                        cmd.extend(audio_map)
                        cmd.extend([
                            "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-r", "24",
                            "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest",
                            "-map_metadata", "-1",
                        ])
                        if target_duration:
                            cmd.extend(["-t", str(target_duration)])
                        cmd.append("FINAL_SHORT.mp4")
                    else:
                        # IMAGE background
                        final_img_path = os.path.join(OUTPUT_DIR, "final_bg.jpg")
                        with Image.open(img_path) as im:
                            im_resized = resize_to_video(im, width=vid_w, height=vid_h, scale_mode=video_scale).convert("RGB")
                            im_resized.save(final_img_path, quality=95)
                        # Точная длительность аудио (избегаем хвостовой тишины)
                        probe = subprocess.run(
                            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", aud_path],
                            capture_output=True, text=True
                        )
                        audio_dur = probe.stdout.strip() or "0"
                        # Градиент (если включён)
                        grad_png = None
                        if use_gradient:
                            grad_path = os.path.join(OUTPUT_DIR, "gradient_overlay.png")
                            create_gradient_overlay_png(grad_path, vid_w, vid_h,
                                                        dark_zone_ratio=gradient_zone / 100,
                                                        max_opacity=gradient_opacity / 100)
                            grad_png = grad_path
                        cmd = build_image_render_cmd(
                            final_img_path, aud_path, audio_dur, vid_w, vid_h,
                            viz_style, viz_h, viz_margin, viz_color,
                            gradient_png_path=grad_png, ass_basename=ass_basename,
                            max_duration=target_duration
                        )

                    st.write("Склейка (FFmpeg)...")
                    process = subprocess.Popen(cmd, cwd=OUTPUT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()

                    if process.returncode == 0:
                        st.success("ГОТОВО!")
                        st.balloons()
                        with open(out_file, "rb") as f:
                            st.download_button("📩 Скачать файл", f, "FINAL_SHORT.mp4")
                    else:
                        st.error("Ошибка при рендере FFmpeg")
                        st.code(stderr.decode("utf-8", errors="ignore")[-1500:], language="text")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        st.stop()  # не показываем блок Whisper/редактора субтитров

    # ============================
    # РЕЖИМ С СУБТИТРАМИ (Whisper)
    # ============================
    if subs_file:
        try:
            if subs_file.name.endswith('.csv'):
                df = pd.read_csv(subs_file)
                df.columns = df.columns.str.strip()
                required = {'start', 'end', 'word'}
                if required.issubset(df.columns) and st.session_state.get("words_data") is None:
                    st.session_state["words_data"] = df.to_dict('records')
                    st.success(f"✅ Субтитры загружены из {subs_file.name}")
                    st.rerun()
            elif subs_file.name.endswith('.srt'):
                if st.session_state.get("words_data") is None:
                    srt_text = subs_file.getvalue().decode('utf-8')
                    st.session_state["words_data"] = parse_srt_content(srt_text)
                    st.success(f"✅ Субтитры загружены из {subs_file.name}")
                    st.rerun()
        except Exception as e:
            st.error(f"Ошибка чтения субтитров: {e}")

    if st.session_state.get("words_data") is None:
        button_text = "🎧 1. РАСПОЗНАТЬ ИЗ АУДИО (Whisper)" if audio_file else "🎥 1. РАСПОЗНАТЬ ИЗ ВИДЕО (Whisper)"
        if st.button(button_text, type="primary"):
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
                    fixed_words = fix_whisper_timings(words_raw)
                    st.session_state["words_data"] = fixed_words
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

        srt_content = generate_srt_string(st.session_state["words_data"])
        st.download_button("📝 Скачать субтитры (.srt)", data=srt_content.encode("utf-8"), file_name="subtitles.srt", mime="text/plain")

        st.divider()

        if st.button("🎬 3. СОЗДАТЬ ВИДЕО (РЕНДЕР)", type="primary"):
            with st.status("Создание видео...", expanded=True):
                try:
                    words_sorted = sorted(edited_words, key=lambda x: x.get('start', 0))

                    st.write("Генерация субтитров...")
                    ass_path = os.path.join(OUTPUT_DIR, "subs.ass")
                    generate_karaoke_ass(words_sorted, ass_path, font, size, words_per_line, offset,
                                        static_text, st_font, st_size, st_color, st_pos,
                                        base_color_hex=base_hex, highlight_color_hex=highlight_hex, uppercase=uppercase_cb,
                                        width=vid_w, height=vid_h, sub_style=sub_style,
                                        cta_text=cta_text, cta_font=cta_font_sel, cta_size=cta_size_sel,
                                        cta_color=cta_color_sel, cta_pos_y=cta_pos_y_sel,
                                        cta_emoji=cta_emoji, cta_animate=cta_animate)

                    st.write("Склейка (FFmpeg)...")
                    out_file = os.path.join(OUTPUT_DIR, "FINAL_SHORT.mp4")
                    ass_basename = os.path.basename(ass_path)

                    if video_path:
                        if video_scale == "Размытый фон":
                            base_vf = f"[0:v:0]split[a][b];[a]scale={vid_w}:{vid_h},boxblur=20:20[1];[b]scale={vid_w}:{vid_h}:force_original_aspect_ratio=decrease[2];[1][2]overlay=(W-w)/2:(H-h)/2,ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]"
                        elif video_scale == "Обрезать (Без краев)":
                            base_vf = f"[0:v:0]scale={vid_w}:{vid_h}:force_original_aspect_ratio=increase,crop={vid_w}:{vid_h},ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]"
                        else:
                            # Вписать (Черные края)
                            base_vf = f"[0:v:0]scale={vid_w}:{vid_h}:force_original_aspect_ratio=decrease,pad={vid_w}:{vid_h}:(ow-iw)/2:(oh-ih)/2,ass={ass_basename}:fontsdir='{FFMPEG_FONTS_DIR}'[vout]"

                        audio_map = []
                        if mute_video:
                            if audio_file is not None:
                                audio_map = ["-map", "1:a"]
                            else:
                                audio_map = ["-an"]
                        else:
                            if audio_file is not None:
                                base_vf += ";[0:a][1:a]amix=inputs=2:duration=shortest[aout]"
                                audio_map = ["-map", "[aout]"]
                            else:
                                audio_map = ["-map", "0:a"]
                        
                        cmd = ["ffmpeg", "-y", "-i", video_path]
                        if os.path.exists(aud_path):
                            cmd.extend(["-i", aud_path])
                            
                        cmd.extend([
                            "-filter_complex", base_vf,
                            "-map", "[vout]"
                        ])
                        cmd.extend(audio_map)
                        cmd.extend([
                            "-c:v", "libx264", "-crf", "23", "-preset", "fast", "-r", "24",
                            "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest",
                            "-map_metadata", "-1",
                        ])
                        if target_duration:
                            cmd.extend(["-t", str(target_duration)])
                        cmd.append("FINAL_SHORT.mp4")
                    else:
                        # IMAGE background
                        final_img_path = os.path.join(OUTPUT_DIR, "final_bg.jpg")
                        with Image.open(img_path) as im:
                            im_resized = resize_to_video(im, width=vid_w, height=vid_h).convert("RGB")
                            im_resized.save(final_img_path, quality=95)
                        # Точная длительность аудио (избегаем хвостовой тишины)
                        probe = subprocess.run(
                            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", aud_path],
                            capture_output=True, text=True
                        )
                        audio_dur = probe.stdout.strip() or "0"
                        # Градиент (если включён)
                        grad_png = None
                        if use_gradient:
                            grad_path = os.path.join(OUTPUT_DIR, "gradient_overlay.png")
                            create_gradient_overlay_png(grad_path, vid_w, vid_h,
                                                        dark_zone_ratio=gradient_zone / 100,
                                                        max_opacity=gradient_opacity / 100)
                            grad_png = grad_path
                        cmd = build_image_render_cmd(
                            final_img_path, aud_path, audio_dur, vid_w, vid_h,
                            viz_style, viz_h, viz_margin, viz_color,
                            gradient_png_path=grad_png, ass_basename=ass_basename,
                            max_duration=target_duration
                        )

                    process = subprocess.Popen(cmd, cwd=OUTPUT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()

                    if process.returncode == 0:
                        st.success("ГОТОВО!")
                        st.balloons()

                        with open(out_file, "rb") as f:
                            st.download_button("📩 Скачать файл", f, "FINAL_SHORT.mp4")
                    else:
                        st.error("Ошибка при рендере FFmpeg")
                        st.code(stderr.decode("utf-8", errors="ignore")[-1500:], language="text")

                except Exception as e:
                    st.error(f"Ошибка: {e}")

        if st.button("🔄 Сбросить и загрузить другое аудио"):
            del st.session_state["words_data"]
            st.rerun()

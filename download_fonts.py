import os
import urllib.request
import shutil

FONTS_DIR = "fonts"
os.makedirs(FONTS_DIR, exist_ok=True)

# Проверенные прямые ссылки на TTF файлы
URLS = {
    "Montserrat-Bold.ttf": "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf",
    "Montserrat-Regular.ttf": "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Regular.ttf",
    "Roboto-Bold.ttf": "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf",
    "Roboto-Black.ttf": "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Black.ttf",
    "Oswald-Bold.ttf": "https://raw.githubusercontent.com/googlefonts/OswaldFont/master/fonts/ttf/Oswald-Bold.ttf",
    "Comfortaa-Bold.ttf": "https://raw.githubusercontent.com/googlefonts/comfortaa/master/fonts/TTF/Comfortaa-Bold.ttf",
    "RussoOne-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/russoone/RussoOne-Regular.ttf",
}

print("Скачиваю шрифты для Shorts Generator...")
for name, url in URLS.items():
    dest = os.path.join(FONTS_DIR, name)
    if os.path.exists(dest):
        print(f"  {name} — уже есть, пропускаю")
        continue
    try:
        urllib.request.urlretrieve(url, dest)
        size_kb = os.path.getsize(dest) // 1024
        print(f"  {name} — скачан ({size_kb} KB)")
    except Exception as e:
        print(f"  {name} — ОШИБКА: {e}")

# Копируем Arial из Windows как fallback
win = "C:\\Windows\\Fonts"
for f in ["arial.ttf", "arialbd.ttf"]:
    dst = os.path.join(FONTS_DIR, f)
    src = os.path.join(win, f)
    if not os.path.exists(dst) and os.path.exists(src):
        shutil.copy(src, dst)
        print(f"  {f} — скопирован из Windows")

print(f"\nГотово! В папке fonts/ {len(os.listdir(FONTS_DIR))} файлов.")

import os

target_dir = "shorts"
if not os.path.exists(target_dir):
    print(f"Directory {target_dir} not found!")
    exit()

os.chdir(target_dir)
print(f"Working in: {os.getcwd()}")

# Map: The start of the broken filename -> The correct new name
# We match by the number prefix "1. ", "2. " etc to be safe,
# because the broken characters might vary depending on system codepage.

correct_names = {
    "1": "1. Ловушка вечного позитива.mp4",
    "2": "2. Принятие тьмы и света.mp4",
    "3": "3. Зачем нам нужны проблемы.mp4",
    "4": "4. Техника СТОП при кризисе.mp4",
    "5": "5. Как менять линии жизни.mp4",
    "6": "6. Секрет Негативной благодарности.mp4"
}

files = os.listdir(".")
print("files found:", files)

for filename in files:
    if not filename.endswith(".mp4"):
        continue
    
    # Check if file starts with "1. ", "2. " etc.
    prefix = filename.split(".")[0] # gets "1", "2"
    
    if prefix in correct_names:
        new_name = correct_names[prefix]
        if filename != new_name:
            try:
                os.rename(filename, new_name)
                print(f"Renamed: {filename} -> {new_name}")
            except Exception as e:
                print(f"Error renaming {filename}: {e}")
        else:
            print(f"Skipping {filename}, already correct.")

print("Done.")

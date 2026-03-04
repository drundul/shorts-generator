# Force Output Encoding for Cyrillic
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$dir = "shorts"
if (-not (Test-Path $dir)) { Write-Error "Shorts directory not found!"; return }
cd $dir

Write-Host "Renaming files to Russian (Fix Encoding)..."

# Rename from English temp names (Option 1)
Rename-Item "1_Positiv_Trap.mp4" -NewName "1. Ловушка вечного позитива.mp4" -ErrorAction SilentlyContinue
Rename-Item "2_Accept_Dark_Light.mp4" -NewName "2. Принятие тьмы и света.mp4" -ErrorAction SilentlyContinue
Rename-Item "3_Why_Need_Problems.mp4" -NewName "3. Зачем нам нужны проблемы.mp4" -ErrorAction SilentlyContinue
Rename-Item "4_STOP_Technique.mp4" -NewName "4. Техника СТОП при кризисе.mp4" -ErrorAction SilentlyContinue
Rename-Item "5_Change_Life_Lines.mp4" -NewName "5. Как менять линии жизни.mp4" -ErrorAction SilentlyContinue
Rename-Item "6_Negative_Gratitude.mp4" -NewName "6. Секрет Негативной благодарности.mp4" -ErrorAction SilentlyContinue

# Rename from BROKEN Cyrillic names (Option 2 - if already messed up)
# We find files starting with "1. " but having weird chars and rename them properly
Get-ChildItem -Filter "1. *.mp4" | Rename-Item -NewName "1. Ловушка вечного позитива.mp4" -ErrorAction SilentlyContinue
Get-ChildItem -Filter "2. *.mp4" | Rename-Item -NewName "2. Принятие тьмы и света.mp4" -ErrorAction SilentlyContinue
Get-ChildItem -Filter "3. *.mp4" | Rename-Item -NewName "3. Зачем нам нужны проблемы.mp4" -ErrorAction SilentlyContinue
Get-ChildItem -Filter "4. *.mp4" | Rename-Item -NewName "4. Техника СТОП при кризисе.mp4" -ErrorAction SilentlyContinue
Get-ChildItem -Filter "5. *.mp4" | Rename-Item -NewName "5. Как менять линии жизни.mp4" -ErrorAction SilentlyContinue
Get-ChildItem -Filter "6. *.mp4" | Rename-Item -NewName "6. Секрет Негативной благодарности.mp4" -ErrorAction SilentlyContinue

Write-Host "Done! Please check the folder." -ForegroundColor Green

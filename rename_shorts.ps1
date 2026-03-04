# Script to rename TEMP names to RUSSIAN final titles
$dir = "shorts"
if (-not (Test-Path $dir)) { Write-Error "Shorts directory not found!"; return }
cd $dir

Write-Host "Renaming files to Russian..."

Rename-Item "1_Positiv_Trap.mp4" -NewName "1. Ловушка вечного позитива.mp4" -ErrorAction SilentlyContinue
Rename-Item "2_Accept_Dark_Light.mp4" -NewName "2. Принятие тьмы и света.mp4" -ErrorAction SilentlyContinue
Rename-Item "3_Why_Need_Problems.mp4" -NewName "3. Зачем нам нужны проблемы.mp4" -ErrorAction SilentlyContinue
Rename-Item "4_STOP_Technique.mp4" -NewName "4. Техника СТОП при кризисе.mp4" -ErrorAction SilentlyContinue
Rename-Item "5_Change_Life_Lines.mp4" -NewName "5. Как менять линии жизни.mp4" -ErrorAction SilentlyContinue
Rename-Item "6_Negative_Gratitude.mp4" -NewName "6. Секрет Негативной благодарности.mp4" -ErrorAction SilentlyContinue

Get-ChildItem -Filter "*.mp4" | Select-Object Name | ft
Write-Host "Done! All files renamed." -ForegroundColor Green

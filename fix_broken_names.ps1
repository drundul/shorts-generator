$shortPath = "shorts"
if (-not (Test-Path $shortPath)) { Write-Error "Shorts directory not found"; exit }
cd $shortPath

# Target exact broken names as seen in the directory listing
Rename-Item -LiteralPath "1. Р›РѕРІСѓС€РєР° РІРµС‡РЅРѕРіРѕ РїРѕР·РёС‚РёРІР°.mp4" -NewName "1. Ловушка вечного позитива.mp4" -ErrorAction SilentlyContinue
Rename-Item -LiteralPath "2. РџСЂРёРЅСЏС‚РёРµ С‚СЊРјС‹ Рё СЃРІРµС‚Р°.mp4" -NewName "2. Принятие тьмы и света.mp4" -ErrorAction SilentlyContinue
Rename-Item -LiteralPath "3. Р—Р°С‡РµРј РЅР°Рј РЅСѓР¶РЅС‹ РїСЂРѕР±Р»РµРјС‹.mp4" -NewName "3. Зачем нам нужны проблемы.mp4" -ErrorAction SilentlyContinue
Rename-Item -LiteralPath "4. РўРµС…РЅРёРєР° РЎРўРћРџ РїСЂРё РєСЂРёР·РёСЃРµ.mp4" -NewName "4. Техника СТОП при кризисе.mp4" -ErrorAction SilentlyContinue
Rename-Item -LiteralPath "5. РљР°Рє РјРµРЅСЏС‚СЊ Р»РёРЅРёРё Р¶РёР·РЅРё.mp4" -NewName "5. Как менять линии жизни.mp4" -ErrorAction SilentlyContinue
Rename-Item -LiteralPath "6. РЎРµРєСЂРµС‚ РќРµРіР°С‚РёРІРЅРѕР№ Р±Р»Р°РіРѕРґР°СЂРЅРѕСЃС‚Рё.mp4" -NewName "6. Секрет Негативной благодарности.mp4" -ErrorAction SilentlyContinue

Write-Host "Renaming complete. Check folder."

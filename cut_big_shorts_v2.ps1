# Script to split "big shorts.mp4" into 6 specific shorts (CORRECTED TIMINGS)
$input = "big shorts.mp4"
$output = "shorts"

if (-not (Test-Path $output)) {
    New-Item -ItemType Directory -Path $output | Out-Null
}

$clips = @(
    @{Start = "00:00:00"; End = "00:00:43"; Name = "1. Ловушка вечного позитива.mp4" },
    @{Start = "00:00:43"; End = "00:01:16"; Name = "2. Принятие тьмы и света.mp4" },
    @{Start = "00:01:16"; End = "00:02:02"; Name = "3. Зачем нам нужны проблемы.mp4" },
    @{Start = "00:02:11"; End = "00:02:54"; Name = "4. Техника СТОП при кризисе.mp4" },
    @{Start = "00:02:54"; End = "00:03:48"; Name = "5. Как менять линии жизни.mp4" },
    @{Start = "00:03:48"; End = "00:04:28"; Name = "6. Секрет Негативной благодарности.mp4" }
)

Write-Host "Creating 6 Shorts from '$input' with FIXED ENDINGS..."

foreach ($clip in $clips) {
    $outPath = Join-Path $output $clip.Name
    Write-Host "Processing: $($clip.Name) ($($clip.Start) - $($clip.End))"
    
    # Using re-encoding to ensure precise cuts
    $cmd = "ffmpeg -y -ss $($clip.Start) -to $($clip.End) -i `"$input`" -c:v libx264 -preset medium -c:a aac -b:a 192k `"$outPath`""
    
    Invoke-Expression $cmd
}

Write-Host "Done! Check the '$output' folder." -ForegroundColor Green

# Script to split "big shorts.mp4" (TIMINGS FIXED + SAFE NAMES)
$input = "big shorts.mp4"
$output = "shorts"

if (-not (Test-Path $output)) {
    New-Item -ItemType Directory -Path $output | Out-Null
}

$clips = @(
    @{Start = "00:00:00"; End = "00:00:43"; Name = "1_Positiv_Trap.mp4" },
    @{Start = "00:00:43"; End = "00:01:16"; Name = "2_Accept_Dark_Light.mp4" },
    @{Start = "00:01:16"; End = "00:02:02"; Name = "3_Why_Need_Problems.mp4" },
    @{Start = "00:02:11"; End = "00:02:54"; Name = "4_STOP_Technique.mp4" },
    @{Start = "00:02:54"; End = "00:03:48"; Name = "5_Change_Life_Lines.mp4" },
    @{Start = "00:03:48"; End = "00:04:28"; Name = "6_Negative_Gratitude.mp4" }
)

Write-Host "Creating 6 Shorts from '$input' (English temp names)..."

foreach ($clip in $clips) {
    $outPath = Join-Path $output $clip.Name
    Write-Host "Processing: $($clip.Name) ($($clip.Start) - $($clip.End))"
    $cmd = "ffmpeg -y -ss $($clip.Start) -to $($clip.End) -i `"$input`" -c:v libx264 -preset medium -c:a aac -b:a 192k `"$outPath`""
    Invoke-Expression $cmd
}

Write-Host "Cuts done! Now run the rename script." -ForegroundColor Green

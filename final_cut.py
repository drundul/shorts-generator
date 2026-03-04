import os
import subprocess

# CONFIG
WORK_DIR = r"c:\Users\User\Documents\Antigravity work\Youshorts"
SOURCE_VIDEO = "JIJq-29DpzG_KUCoQMrXY.mp4"

# OUTPUT PREFIX
OUT_PREFIX = "Final_Short"

# SHORTS DEFINITIONS
# (Start Sec, End Sec, Name)
SHORTS = [
    (0.0, 38.0, "1_Exposition"),      # 00:00 - 00:38
    (44.0, 80.0, "2_Aperture"),       # 00:44 - 01:20 ( Chorus)
    (81.0, 107.0, "3_Mirrors"),       # 01:21 - 01:47
    (109.0, 137.0, "4_Verdict")       # 01:49 - 02:17
]

def make_shorts():
    video_path = os.path.join(WORK_DIR, SOURCE_VIDEO)
    
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found")
        return

    for start, end, name in SHORTS:
        duration = end - start
        out_name = f"{OUT_PREFIX}_{name}.mp4"
        out_path = os.path.join(WORK_DIR, out_name)
        
        print(f"--- Processing {name} ({duration}s) ---")
        
        # FFmpeg Command
        # 1. Trim Video (-ss -t)
        # 2. Generate BARS from Audio of the trimmed portion
        # 3. Overlay BARS
        
        # FILTER COMPLEX:
        # [0:a]showfreqs...[bars] -> Generate bars from input audio
        # [0:v][bars]overlay...[v] -> Put bars on top of video
        
        # NOTE: We must trim inside the filter or trim input first?
        # Better to trim input timings with -ss before -i for speed, 
        # BUT for accuracy with filters, it's safer to trim.
        
        # bars size: 1080x400 (lower third)
        # position: (H-h)/2 + 400? Or just bottom?
        # User said: "Center or slightly lower".
        # 1920 height. Center is 960. 
        # Let's put BARS bottom at 1400 (slightly below center).
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(duration), "-i", video_path, # Input (Trimmed)
            "-filter_complex", 
            # 1. BARS GENERATION (White, Transparent BG)
            "[0:a]showfreqs=s=1080x400:mode=bar:ascale=sqrt:fscale=log:colors=white,format=rgba,colorkey=0x000000:0.1:0.5[bars];"
            # 2. OVERLAY (Position: X=0, Y=1200)
            "[0:v][bars]overlay=0:1200:format=auto[v]",
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy", # Copy audio (no re-encode if possible? No, showfreqs needs access, but we map 0:a for output. Wait, if we trim with -ss before -i, we re-encode anyway).
            # Actually -c:a copy works for output stream, but input was decoded for filter.
            # Ideally re-encode audio to be safe with cuts
            "-c:a", "aac", "-b:a", "192k",
            out_path
        ]
        
        subprocess.run(cmd, cwd=WORK_DIR)
        print(f"Done: {out_name}")

if __name__ == "__main__":
    make_shorts()

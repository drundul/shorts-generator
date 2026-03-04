import os
import subprocess

# Settings
work_dir = r"C:\Users\User\Documents\Antigravity work\Youshorts"
source_file = "За гранью обычной (Out of the Ordinary) — Atmospheric Alt-Hip-Hop .mp4"
temp_source = "source_music.mp4"

clips = [
    {"start": "00:00:00", "end": "00:00:51", "name": "1. Город надежд (Назло ветрам).mp4"},
    {"start": "00:00:59", "end": "00:01:50", "name": "2. За гранью обычной (Я пьян без вина).mp4"},
    {"start": "00:03:29", "end": "00:04:08", "name": "3. Ангелы сгорают с тоски (Финал).mp4"}
]

def run_ffmpeg(start, end, input_f, output_f):
    # Using re-encoding for precision
    cmd = [
        "ffmpeg", "-y",
        "-ss", start,
        "-to", end,
        "-i", input_f,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        output_f
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    if not os.path.exists(work_dir):
        print("Directory not found!")
        exit(1)
        
    os.chdir(work_dir)
    print(f"Processing in: {os.getcwd()}")
    
    # 1. Rename bad filename text temporarily
    if os.path.exists(source_file):
        print(f"Renaming source to {temp_source}...")
        os.rename(source_file, temp_source)
    elif not os.path.exists(temp_source):
        print(f"Source file not found: {source_file}")
        exit(1)

    # 2. Cut clips
    try:
        if not os.path.exists("shorts"):
            os.mkdir("shorts")
            
        for clip in clips:
            out_path = os.path.join("shorts", clip["name"])
            print(f"Cutting: {clip['name']}...")
            run_ffmpeg(clip["start"], clip["end"], temp_source, out_path)
            
        print("All clips created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # 3. Rename back
        if os.path.exists(temp_source):
            print("Restoring original filename...")
            os.rename(temp_source, source_file)

    print("Done.")

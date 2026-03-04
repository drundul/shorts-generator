import os
import subprocess

# Settings
work_dir = r"C:\Users\User\Documents\Antigravity work\Youshorts"
source_file = "За гранью обычной (Out of the Ordinary) — Atmospheric Alt-Hip-Hop .mp4"
temp_source = "source_music.mp4"
output_dir = "shorts_v2"

# NEW TIMINGS based on filename (2).srt logic
clips = [
    # 1. Intro verse
    {"start": "00:00:16", "end": "00:00:51", "name": "1. Город надежд (Назло ветрам).mp4"},
    
    # 2. Chorus + Verse 2 (The most emotional part)
    {"start": "00:00:59", "end": "00:01:46", "name": "2. Я пьян без вина (За гранью).mp4"},
    
    # 3. Chorus 2 (Pure emotion)
    {"start": "00:02:01", "end": "00:02:29", "name": "3. Люби меня до скончания веков.mp4"},
    
    # 4. Outro (Final chorus + ending)
    {"start": "00:03:29", "end": "00:04:08", "name": "4. Мы вышли за грань (Финал).mp4"}
]

if __name__ == "__main__":
    if not os.path.exists(work_dir):
        print(f"Directory {work_dir} not found!")
        exit(1)
        
    os.chdir(work_dir)
    print(f"Working in: {os.getcwd()}")
    
    # Rename source temporarily to avoid encoding hell
    if os.path.exists(source_file):
        print(f"Renaming source to {temp_source}...")
        try:
            os.rename(source_file, temp_source)
        except OSError as e:
            print(f"Error renaming source: {e}")
            exit(1)
    elif not os.path.exists(temp_source):
        print(f"Source file '{source_file}' not found!")
        # If renamed previously but crashed, maybe temp_source exists? check below.
        if not os.path.exists(temp_source):
             exit(1)

    # Creating output dir
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    try:
        for clip in clips:
            out_path = os.path.join(output_dir, clip["name"])
            print(f"Cutting clip: {clip['name']} ({clip['start']} -> {clip['end']})")
            
            cmd = [
                "ffmpeg", "-y",
                "-ss", clip["start"],
                "-to", clip["end"],
                "-i", temp_source,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "aac", "-b:a", "192k",
                out_path
            ]
            subprocess.run(cmd, check=True)
            
        print(f"Done! {len(clips)} shorts created in '{output_dir}'.")
        
    except Exception as e:
        print(f"Error during ffmpeg processing: {e}")
        
    finally:
        # Restore filename
        if os.path.exists(temp_source):
            print("Restoring original filename...")
            os.rename(temp_source, source_file)

    print("Finished.")

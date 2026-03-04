import os
import glob
import subprocess

# Settings
work_dir = r"C:\Users\User\Documents\Antigravity work\Youshorts"
output_dir = "shorts_v3"

# TIMINGS (Corrected based on SRT analysis)
clips = [
    {"start": "00:00:16", "end": "00:00:51", "name": "1. Город надежд (Назло ветрам).mp4"},
    {"start": "00:00:59", "end": "00:01:46", "name": "2. Я пьян без вина (За гранью).mp4"},
    {"start": "00:02:01", "end": "00:02:29", "name": "3. Люби меня до скончания веков.mp4"},
    {"start": "00:03:29", "end": "00:04:08", "name": "4. Мы вышли за грань (Финал).mp4"}
]

if __name__ == "__main__":
    if not os.path.exists(work_dir):
        print(f"Directory {work_dir} not found!")
        exit(1)
        
    os.chdir(work_dir)
    print(f"Working in: {os.getcwd()}")
    
    # 1. Find the source file automatically
    # Look for ANY mp4 containing 'Ordinary' or 'Atmospheric'
    candidates = glob.glob("*Ordinary*.mp4") + glob.glob("*Atmospheric*.mp4")
    
    if not candidates:
        print("Could not find the music video file! Please rename it to something simple like 'music.mp4'")
        print("Files found:", glob.glob("*.mp4"))
        exit(1)
        
    source_file = candidates[0]
    print(f"Found source file: '{source_file}'")
    
    temp_source = "temp_source_music.mp4"

    # Rename temporary to concise name for ffmpeg
    try:
        os.rename(source_file, temp_source)
    except OSError as e:
        print(f"Error renaming source: {e}")
        exit(1)

    # Create output dir
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
            
        print(f"Done! Created 4 shorts in '{output_dir}'.")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Restore filename
        if os.path.exists(temp_source):
            print("Restoring original filename...")
            os.rename(temp_source, source_file)

    print("Finished.")

import os
import re
import subprocess
from datetime import timedelta

# CONFIG
WORK_DIR = r"c:\Users\User\Documents\Antigravity work\Youshorts"
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
SOURCE_ASS = os.path.join(OUTPUT_DIR, "subs.ass")
SOURCE_AUDIO = os.path.join(WORK_DIR, "input_audio.mp3")
SOURCE_IMAGE = os.path.join(OUTPUT_DIR, "final_bg.jpg")

# SHORTS DEFINITIONS (Start, End in seconds)
# SHORTS DEFINITIONS (Start, End in seconds)
SHORTS = [
    # 1. INTRO
    # Trimming end to remove silence (was 40.5)
    {"name": "Short_1_Intro", "start": 16.0, "end": 39.8},
    
    # 2. CONFLICT
    # Trimming end to remove silence (was 67.0)
    {"name": "Short_2_Conflict", "start": 41.5, "end": 65.5},

    # 3. DRAMA
    # Trimming end to remove silence (was 202.0)
    {"name": "Short_3_Drama", "start": 128.0, "end": 200.0}
]

def parse_time(time_str):
    """Converts H:MM:SS.cs to seconds."""
    # format: 0:00:16.66
    h, m, s = time_str.split(':')
    return float(h) * 3600 + float(m) * 60 + float(s)

def format_time(seconds):
    """Converts seconds to H:MM:SS.cs for ASS."""
    # Ensure seconds is positive
    seconds = max(0, seconds)
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, sec = divmod(remainder, 60)
    centiseconds = td.microseconds // 10000
    return f"{hours}:{minutes:02d}:{sec:02d}.{centiseconds:02d}"

def shift_ass_content(content, time_offset_seconds):
    """Parses ASS content and shifts all timestamps by -time_offset_seconds."""
    new_lines = []
    events_started = False
    
    for line in content.splitlines():
        if line.strip() == "[Events]":
            events_started = True
            new_lines.append(line)
            continue
            
        if not events_started or not line.startswith("Dialogue:"):
            new_lines.append(line)
            continue
            
        # Parse Dialogue line
        # Dialogue: 0,0:00:16.66,0:00:17.82,BaseStyle,,0,0,0,,Text
        # We need to split carefuly because Text can have commas
        parts = line.split(',', 9) 
        if len(parts) < 10:
            new_lines.append(line)
            continue
            
        start_str = parts[1]
        end_str = parts[2]
        
        try:
            start_sec = parse_time(start_str)
            end_sec = parse_time(end_str)
            
            # Shift
            new_start = start_sec - time_offset_seconds
            new_end = end_sec - time_offset_seconds
            
            # If the entire line is before the start time (negative end), specific logic:
            # But here we filter logically outside, ASS render handles negatives usually by not showing, 
            # BUT we want to keep static text starting at 0.
            
            # Special handling for LOGO/STATIC which starts at 0 initially
            if "StaticStyle" in parts[3]:
                # Static text should stay at 0 to duration
                # We just reset it to 0 -> Duration of short
                new_start = 0
                new_end = 3600 # 1 hour
            
            parts[1] = format_time(new_start)
            parts[2] = format_time(new_end)
            
            new_lines.append(",".join(parts))
            
        except Exception as e:
            print(f"Error parsing line: {line} - {e}")
            new_lines.append(line)
            
    return "\n".join(new_lines)

def main():
    if not os.path.exists(SOURCE_ASS):
        print(f"Error: {SOURCE_ASS} not found")
        return

    with open(SOURCE_ASS, "r", encoding="utf-8-sig") as f:
        ass_content = f.read()

    for item in SHORTS:
        print(f"--- Processing {item['name']} ---")
        
        # 1. Prepare Shifted ASS
        # Cut start time is the offset
        shifted_ass = shift_ass_content(ass_content, item['start'])
        temp_ass_name = f"{item['name']}.ass"
        temp_ass_path = os.path.join(OUTPUT_DIR, temp_ass_name)
        
        with open(temp_ass_path, "w", encoding="utf-8-sig") as f:
            f.write(shifted_ass)
            
        # 2. Render FFmpeg
        # We cut audio/video using -ss and -t
        # And burn the SHIFTED subtitles
        
        duration = item['end'] - item['start']
        output_mp4 = os.path.join(OUTPUT_DIR, f"{item['name']}.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", SOURCE_IMAGE,  # Input 0: Image
            "-ss", str(item['start']), "-t", str(duration), "-i", SOURCE_AUDIO, # Input 1: Audio (Cut)
            "-vf", f"ass={temp_ass_name}",     # Subtitles
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", # Stop when audio stops
            output_mp4
        ]
        
        print(f"Rendering {item['name']}...")
        subprocess.run(cmd, cwd=OUTPUT_DIR, check=True)
        print(f"Done: {output_mp4}")

if __name__ == "__main__":
    main()

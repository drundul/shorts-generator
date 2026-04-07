import re
import os
import subprocess

def parse_srt(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match SRT blocks
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.|\n)*?)(?=\n\d+\n|\n\Z)', re.MULTILINE)
    
    segments = []
    for match in pattern.finditer(content):
        start_str = match.group(2)
        end_str = match.group(3)
        text = match.group(4).strip()
        
        start_ms = time_to_ms(start_str)
        end_ms = time_to_ms(end_str)
        
        segments.append({
            'start': start_ms,
            'end': end_ms,
            'text': text
        })
    return segments

def time_to_ms(time_str):
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)

def ms_to_time(ms):
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def group_segments(segments, min_dur_ms=25000, max_dur_ms=40000):
    chunks = []
    if not segments:
        return chunks
    
    i = 0
    while i < len(segments):
        start_ms = segments[i]['start']
        current_end_ms = segments[i]['end']
        j = i + 1
        
        while j < len(segments):
            next_end_ms = segments[j]['end']
            duration = next_end_ms - start_ms
            
            if duration > max_dur_ms:
                # If we stop at j-1, is it at least min_dur?
                prev_duration = segments[j-1]['end'] - start_ms
                if prev_duration >= min_dur_ms:
                    # Stop at j-1
                    chunks.append((start_ms, segments[j-1]['end']))
                    i = j
                    break
                else:
                    # Dilemma: Prev is too short, current is too long.
                    # Usually we pick the one closer to the range.
                    # But the user said 25-40. Let's pick current if it's not too much over.
                    # For now, let's just take j-1 and move on, or take j if it's the only way.
                    chunks.append((start_ms, next_end_ms))
                    i = j + 1
                    break
            elif duration >= min_dur_ms:
                # We are in range. We could stop or try to add more.
                # Let's peek at the next one.
                if j + 1 < len(segments):
                    if segments[j+1]['end'] - start_ms > max_dur_ms:
                        # Next one would be too much. Stop here.
                        chunks.append((start_ms, next_end_ms))
                        i = j + 1
                        break
                    else:
                        # Keep adding
                        j += 1
                else:
                    # Last segment
                    chunks.append((start_ms, next_end_ms))
                    i = j + 1
                    break
            else:
                # Still too short
                j += 1
        
        if j >= len(segments) and i < len(segments):
            # Remaining segments that didn't form a full chunk
            final_start = start_ms
            final_end = segments[-1]['end']
            # If it's too short, maybe append to last chunk if possible?
            if chunks and (final_end - final_start) < min_dur_ms:
                last_chunk = chunks.pop()
                chunks.append((last_chunk[0], final_end))
            else:
                chunks.append((final_start, final_end))
            break
            
    return chunks

def main():
    srt_file = "filename (2).srt"
    video_file = "мороз мороз shorts.mp4"
    
    if not os.path.exists(srt_file) or not os.path.exists(video_file):
        print(f"Files not found: {srt_file}, {video_file}")
        # Try to find any .srt and .mp4 if names are different
        files = os.listdir('.')
        srt_files = [f for f in files if f.endswith('.srt')]
        mp4_files = [f for f in files if f.endswith('.mp4') and not f.startswith('short_')]
        if srt_files and mp4_files:
            srt_file = srt_files[0]
            video_file = mp4_files[0]
            print(f"Using found files: {srt_file}, {video_file}")
        else:
            return
        
    segments = parse_srt(srt_file)
    if not segments:
        print("No segments found in SRT.")
        return
        
    # Manual chunks as suggested and approved by the user
    manual_chunks = [
        ("00:00:00.600", "00:00:39.800"),
        ("00:00:42.000", "00:01:16.000"),
        ("00:01:27.500", "00:02:00.000"),
        ("00:02:06.000", "00:02:35.000"),
        ("00:01:26.500", "00:02:25.500")  # New requested clip, 59 seconds
    ]
    
    # Convert manual strings to ms and duration for consistency with the rest of the script
    chunks = []
    def str_to_ms(s):
        h, m, s_ms = s.split(':')
        return int(h) * 3600000 + int(m) * 60000 + int(float(s_ms) * 1000)

    for s, e in manual_chunks:
        chunks.append((str_to_ms(s), str_to_ms(e)))

    print(f"Applying manual chunks: {len(chunks)} chunks.")
    for i, (start, end) in enumerate(chunks):
        dur = (end - start) / 1000
        print(f"Chunk {i+1}: {ms_to_time(start)} -> {ms_to_time(end)} ({dur:.2f}s)")
        
    try:
        for i, (start, end) in enumerate(chunks):
            output_file = f"short_{i+1}.mp4"
            if os.path.exists(output_file):
                print(f"Skipping {output_file}, already exists.")
                continue
                
            start_time = ms_to_time(start)
            duration_ms = end - start
            duration_time = ms_to_time(duration_ms)
            
            cmd = [
                "ffmpeg", "-y",
                "-ss", start_time,
                "-t", duration_time,
                "-i", video_file,
                "-c:v", "libx264", "-c:a", "aac", "-preset", "veryfast", "-crf", "22",
                output_file
            ]
            print(f"Executing: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error processing {output_file}: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

if __name__ == "__main__":
    main()

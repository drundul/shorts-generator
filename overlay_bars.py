import os
import subprocess

# CONFIG
WORK_DIR = r"c:\Users\User\Documents\Antigravity work\Youshorts"
SOURCE_VIDEO = "подкаст таня.mp4"
OUTPUT_VIDEO = "podcast_tanya_visualized_TEST.mp4"
TEST_DURATION = 6 # Set to None for full video

def make_visualizer():
    video_path = os.path.join(WORK_DIR, SOURCE_VIDEO)
    output_path = os.path.join(WORK_DIR, OUTPUT_VIDEO)
    
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found")
        return

    print(f"Rendering BARS on {SOURCE_VIDEO}...")

    # FILTER COMPLEX Chain:
    # 1. Generate BARS from audio [0:a]
    #    (Size 1080x300, White, Transparent BG)
    # 2. Overlay BARS on Video [0:v] at y=1500 (Lower third)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-filter_complex", 
        # Increase size to 1920x300 (Full Width for horizontal). Position at Bottom (y=500).
        "[0:a]showfreqs=s=1920x300:mode=bar:ascale=sqrt:fscale=log:colors=white,format=rgba,colorkey=0x000000:0.1:0.5[bars];"
        "[0:v][bars]overlay=0:500:format=auto[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k"
    ]
    
    # Add Duration Logic
    if TEST_DURATION:
       cmd.extend(["-t", str(TEST_DURATION)])
       
    cmd.append(output_path)
    
    subprocess.run(cmd, cwd=WORK_DIR)
    print(f"Done! Saved to: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    make_visualizer()

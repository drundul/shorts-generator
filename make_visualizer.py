import os
import subprocess

# CONFIG
WORK_DIR = r"c:\Users\User\Documents\Antigravity work\Youshorts"
AUDIO_FILE = "song  12 (1).wav"
IMAGE_FILE = "A_grainy_black_2k_202602060649.jpeg"
OUTPUT_FILE = "visualizer_reactor.mp4"

def make_visualizer():
    audio_path = os.path.join(WORK_DIR, AUDIO_FILE)
    image_path = os.path.join(WORK_DIR, IMAGE_FILE)
    output_path = os.path.join(WORK_DIR, OUTPUT_FILE)
    
    if not os.path.exists(audio_path):
        print(f"Error: {audio_path} not found")
        return

    print("Rendering REACTOR Visualizer... (This takes about 20-40 sec)")
    
    # FFmpeg REACTOR Style
    # 1. showfreqs: Generate frequency bars (s=1920x200) - wide strip
    # 2. amix: mix channels if stereo? (showfreqs usually handles it)
    # 3. colors: White|Silver
    # 4. format=yuv420p
    # CRITICAL STEP: v360 or geq filter to twist it into a circle? 
    # Actually, simpler way: 'vectorscope' is cool but circular freq is harder.
    # BEST WAY: 'showcqt' (Constant Q Transform) allows circular axis? No.
    # The trick: use 'shifttb' or polar coordinates filter?
    # No, standard FFmpeg 'showfreqs' + 'avectorscope' is usually for X-Y.
    
    # SIMPLIFIED CIRCLE:
    # We create a line spectrum, then apply coordinate transformation 'polar'.
    # Filter chain: showspectrum -> scale -> v360 (fisheye)? No.
    
    # Let's use 'avectorscope' (Lissajous) - it looks like a ball of yarn reacting to sound.
    # OR 'showcqt' with bar graph.
    
    # Let's stick to the prompt: Circular Pulsar.
    # We will use 'showfreqs' to make a horizontal mirrored bar, then warp it into a circle using 'geq' (Polar).
    # But that's slow.
    # FASTEST WAY: 'showspectrum' with 'polar' mode!
    # showspectrum=mode=combined:slide=scroll:scale=sqrt:color=intensity:saturation=0:win_func=hann
    # Wait, showspectrum is a heatmap.
    
    # LET'S DO: AVECOTRSCOPE (Lissajous) - Looks like a chaotic glowing core in the center. Very reactive.
    # s=1080x1080: Size.
    # zoom=2: Zoom in to see details.
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,       # [0] BG
        "-i", audio_path,                     # [1] Audio
        "-filter_complex",
        "[1:a]avectorscope=s=1080x1080:zoom=1.5:rc=255:gc=255:bc=255:rf=1:gf=1:bf=1:mirror=2:draw=line[vs];" # White Lissajous
        "[0:v]scale=1080:1920[bg];" # BG Full
        "[bg][vs]overlay=(W-w)/2:(H-h)/2:format=auto[v]", # Center overlay
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest",
        output_path
    ]
    
    subprocess.run(cmd, cwd=WORK_DIR)
    print(f"Done! Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    make_visualizer()

import os
import subprocess

# --- CONFIGURATION ---
WORK_DIR = r"c:\Users\User\Documents\Antigravity work\Youshorts"
AUDIO_FILE = "song  12 (1).wav"
IMAGE_FILE = "A_grainy_black_2k_202602060649.jpeg"
OUTPUT_FILE = "visualizer_v2.mp4"

# ВЫБЕРИТЕ СТИЛЬ ЗДЕСЬ: "WAVE", "CQT", "FIRE", "BARS", "REACTOR", "LINE_CENTER", "SMOKE"
STYLE = "SMOKE" 
TEST_DURATION = 7 # 7 seconds test. Set to None for full audio.

def make_visualizer():
    audio_path = os.path.join(WORK_DIR, AUDIO_FILE)
    image_path = os.path.join(WORK_DIR, IMAGE_FILE)
    output_path = os.path.join(WORK_DIR, OUTPUT_FILE)
    
    if not os.path.exists(audio_path):
        print(f"Error: {audio_path} not found")
        return

    print(f"Rendering Style: {STYLE}... (Duration: {TEST_DURATION}s)")

    # FILTER CHAINS
    
    # 1. WAVE (Oscilloscope Line)
    # Added format=rgba and colorkey to make background transparent
    if STYLE == "WAVE":
        filter_complex = (
            "[1:a]showwaves=s=1080x400:mode=line:colors=white:draw=full,format=rgba,colorkey=0x000000:0.1:0.1[wave];"
            "[0:v]scale=1080:1920[bg];"
            "[bg][wave]overlay=0:(H-h)/2:format=auto[v]" 
        )

    # 4. BARS (Classic Frequency Bars)
    # mode=bar: Classic bars
    # ascale=sqrt: Better visualization of volume
    # fscale=log: Better distribution of frequencies (like real ears hear)
    # colors=white: White bars
    elif STYLE == "BARS":
        filter_complex = (
            "[1:a]showfreqs=s=1080x500:mode=bar:ascale=sqrt:fscale=log:colors=white,format=rgba,colorkey=0x000000:0.1:0.5[bars];"
            "[0:v]scale=1080:1920[bg];"
            "[bg][bars]overlay=0:1300:format=auto[v]"
        )

    # 5. REACTOR (Lissajous Phase Scope)
    # avectorscope creates a ball of yarn / star phase effect
    # draw=line: draw lines
    # zoom=1.5: zoom in
    # rc=255: White color
    elif STYLE == "REACTOR":
        filter_complex = (
            "[1:a]avectorscope=s=1080x1080:zoom=1.5:rc=255:gc=255:bc=255:rf=0:gf=0:bf=0:draw=line,format=rgba,colorkey=0x000000:0.1:0.5[reac];"
            "[0:v]scale=1080:1920[bg];"
            "[bg][reac]overlay=(W-w)/2:(H-h)/2:format=auto[v]" # Exact Center
        )

    # 6. LINE_CENTER (Single vibrating string)
    # showwaves with mode=cline (centered line)
    # s=1080x300
    elif STYLE == "LINE_CENTER":
        filter_complex = (
            "[1:a]showwaves=s=1080x300:mode=cline:colors=white:draw=full,format=rgba,colorkey=0x000000:0.1:0.1[ln];"
            "[0:v]scale=1080:1920[bg];"
            "[bg][ln]overlay=0:(H-h)/2:format=auto[v]"
        )

    # 7. SMOKE (White Spectral Fog)
    # showspectrum with 'intensity' colormap (B&W) or 'cool'?
    # intensity: Black -> White. Perfect for smoke.
    # scale=log: Looks more like natural dispersion.
    # slide=scroll: Moving up constantly.
    # win_func=hann: smooth edges.
    elif STYLE == "SMOKE":
        filter_complex = (
            "[1:a]showspectrum=s=1080x800:slide=scroll:mode=separate:color=intensity:scale=log:saturation=0:win_func=hann,format=rgba,colorkey=0x000000:0.02:0.3[smoke];"
            "[0:v]scale=1080:1920[bg];"
            "[bg][smoke]overlay=0:(H-h)/2:format=auto[v]" # Center/Bottom? Let's center it, it flows up.
        )
    elif STYLE == "CQT":
        # FIX: colorkey on CQT to remove black background
        filter_complex = (
           "[1:a]showcqt=s=1080x500:text=0:axis=0:sono_h=0:bar_g=2:bar_v=15:bar_t=0.5,format=rgba,colorkey=0x000000:0.1:0.5[cqt];"
           "[0:v]scale=1080:1920[bg];"
           "[bg][cqt]overlay=0:1300:format=auto[v]"
        )
        
    # 3. FIRE (Spectrogram)
    elif STYLE == "FIRE":
        filter_complex = (
            "[1:a]showspectrum=s=1080x600:slide=scroll:mode=separate:color=magma:scale=sqrt,format=rgba,colorkey=0x000000:0.1:0.5[spec];"
            "[0:v]scale=1080:1920[bg];"
            "[bg][spec]overlay=0:1320:format=auto[v]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p"
    ]
    
    # Add duration limit if set
    if TEST_DURATION:
        cmd.extend(["-t", str(TEST_DURATION)])
    else:
        cmd.append("-shortest")
        
    cmd.append(output_path)
    
    subprocess.run(cmd, cwd=WORK_DIR)
    print(f"Done! Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    make_visualizer()


from PIL import Image, ImageDraw, ImageFont
import os

def create_shorts_overlay(output_path="assets/shorts_overlay.png"):
    # Shorts resolution: 1080x1920
    W, H = 1080, 1920
    
    # Create transparent image
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # --- RIGHT SIDEBAR ICONS (Mockup) ---
    # Icons are roughly circular, on the right side
    icon_x = W - 130
    start_y = H - 800
    spacing = 160
    
    for i in range(5):
        # Draw circle background for icon
        y = start_y + (i * spacing)
        bbox = [icon_x, y, icon_x + 90, y + 90]
        draw.ellipse(bbox, fill=(0, 0, 0, 120)) # Semi-transparent black
        
        # Draw fake "icon" inside (white)
        center_x = icon_x + 45
        center_y = y + 45
        draw.rectangle([center_x - 15, center_y - 15, center_x + 15, center_y + 15], fill=(255, 255, 255, 220))
        
        # Label below icon
        draw.text((icon_x + 15, y + 100), "123K", fill=(255, 255, 255, 255), font_size=30)

    # --- BOTTOM AREA (Channel info) ---
    # Gradient or darker area at bottom
    # Draw simple rectangles for text
    
    # Channel Avatar
    avatar_y = H - 250
    draw.ellipse([40, avatar_y, 120, avatar_y + 80], fill=(255, 255, 255, 255))
    
    # Channel Name
    draw.text((140, avatar_y + 20), "@ChannelName", fill=(255, 255, 255, 255), font_size=40)
    
    # Description
    draw.text((40, avatar_y + 100), "Shorts description goes here... #tag #viral", fill=(255, 255, 255, 200), font_size=35)
    
    # Music sliding text
    draw.text((40, avatar_y + 160), "♫ Original Sound - Artist Name", fill=(255, 255, 255, 180), font_size=30)
    
    # --- PROGRESS BAR ---
    draw.rectangle([0, H - 10, W, H], fill=(200, 0, 0, 255))

    # Save
    img.save(output_path)
    print(f"Overlay saved to {output_path}")

if __name__ == "__main__":
    if not os.path.exists("assets"):
        os.makedirs("assets")
    create_shorts_overlay()

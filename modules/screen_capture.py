# modules/screen_capture.py

import mss
import io
from PIL import Image

def take_screenshot():
    with mss.mss() as sct:
        screenshot = sct.grab(sct.monitors[0])
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60, optimize=True)
        return buffer.getvalue()

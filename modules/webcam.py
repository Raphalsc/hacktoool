# modules/webcam.py

import cv2
import io

def capture_webcam():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    cam.release()

    if not ret:
        return None

    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()

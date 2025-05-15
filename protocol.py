import base64

END_MARKER = b"<END>"

def send_data(sock, data):
    if isinstance(data, str):
        data = data.encode()
    sock.sendall(data + END_MARKER)

def receive_data(sock):
    data = b""
    while True:
        part = sock.recv(4096)
        if part.endswith(END_MARKER):
            data += part[:-len(END_MARKER)]
            break
        data += part
    return data

def send_base64(sock, binary_data):
    encoded = base64.b64encode(binary_data)
    send_data(sock, encoded)

def receive_base64(sock):
    try:
        encoded = receive_data(sock)
        # Ajout de padding si nécessaire
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += b'=' * (4 - missing_padding)
        return base64.b64decode(encoded)
    except Exception as e:
        print("[Erreur base64 decode]:", e)
        return b""

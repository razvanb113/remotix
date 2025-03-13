import mss
import cv2
import numpy as np
import socket
import struct
import time
import firebase_admin
from firebase_admin import credentials, firestore
from pyngrok import ngrok
import uuid
import threading
import tkinter as tk
from tkinter import messagebox

cred = credentials.Certificate("remot-14184-be6cab1a58b3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

PORT = 5005
ngrok_tunnel = ngrok.connect(PORT, "tcp")
public_url = ngrok_tunnel.public_url.replace("tcp://", "")
print(f"Ngrok tunnel: {public_url}")

unique_id = str(uuid.uuid4())[:8]
db.collection("servers").document(unique_id).set({"ip": public_url})

server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.bind(("0.0.0.0", PORT))
server_sock.listen(1)
print("[INFO] Astept conexiuni...")

running = True

def stop_stream():
    global running
    running = False
    server_sock.close()
    ngrok.kill()
    messagebox.showinfo("Info", "Conexiunea a fost oprită!")
    root.destroy()

def refresh_info():
    doc = db.collection("servers").document(unique_id).get()
    ip_label.config(text=f"IP: {doc.to_dict().get('ip', 'Necunoscut')}")

root = tk.Tk()
root.title("Remotix Server")
root.geometry("300x200")
id_label = tk.Label(root, text=f"ID: {unique_id}", font=("Arial", 12))
id_label.pack(pady=10)
ip_label = tk.Label(root, text=f"IP: {public_url}", font=("Arial", 12))
ip_label.pack(pady=10)
refresh_button = tk.Button(root, text="Refresh", command=refresh_info)
refresh_button.pack(pady=5)
stop_button = tk.Button(root, text="Oprește", command=stop_stream, bg="red", fg="white")
stop_button.pack(pady=5)

def recv_all(sock, size):
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(client_sock):
    global running
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while running:
            start_time = time.time()
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            img = cv2.resize(img, (800, 450))
            _, img_encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
            try:
                client_sock.sendall(struct.pack("!I", len(img_encoded)) + img_encoded.tobytes())
            except:
                print("[INFO] Client deconectat.")
                break
            time.sleep(max(1/60 - (time.time() - start_time), 0))

def start_server():
    while running:
        try:
            client_sock, addr = server_sock.accept()
            print(f"[INFO] Client conectat: {addr}")
            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
        except Exception as e:
            print(f"[EROARE] {e}")
            break

threading.Thread(target=start_server, daemon=True).start()
root.mainloop()

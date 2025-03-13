import socket
import struct
import numpy as np
import cv2
import tkinter as tk
from PIL import Image, ImageTk
import threading
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("remot-14184-be6cab1a58b3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

root = tk.Tk()
root.title("Remotix client")
root.geometry("820x550")

running = False
sock = None

canvas = tk.Canvas(root, width=800, height=450, bg="black")
canvas.pack()

code_label = tk.Label(root, text="Introduceți codul unic:")
code_label.pack()

code_entry = tk.Entry(root)
code_entry.pack(pady=5)

def connect_to_stream():
    global sock, running

    code = code_entry.get().strip()
    if not code:
        print("[EROARE] Codul introdus este gol!")
        status_label.config(text="Introduceți un cod valid!", fg="red")
        return

    doc = db.collection("servers").document(code).get()
    if not doc.exists:
        print("[EROARE] Cod invalid!")
        status_label.config(text="Cod invalid!", fg="red")
        return

    full_address = doc.to_dict()["ip"].replace("tcp://", "")
    print(f"[INFO] Conectare la server: {full_address}")
    TCP_IP, TCP_PORT = full_address.split(":")
    TCP_PORT = int(TCP_PORT)
    print(f"[DEBUG] TCP_IP: {TCP_IP}, TCP_PORT: {TCP_PORT}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TCP_IP, TCP_PORT))
        print("[INFO] Conexiune reușită!")
        sock.sendall(b"HELLO_SERVER")
        running = True
        start_receiving()
        status_label.config(text=f"Conectat la {TCP_IP}:{TCP_PORT}", fg="green")
    except Exception as e:
        print(f"[EROARE] Eroare la conectare: {e}")
        status_label.config(text="Eroare la conectare!", fg="red")

def recv_all(sock, size):
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None #conexiune pierduta
        data += packet
    return data

def receive_frames():
    global running
    img_tk = None

    placeholder = Image.new("RGB", (800, 450), "black")
    img_tk = ImageTk.PhotoImage(placeholder)
    image_container = canvas.create_image(0, 0, anchor="nw", image=img_tk)

    while running:
        try:
            size = recv_all(sock, 4)
            if size is None:
                print("[EROARE] Conexiunea s-a întrerupt!")
                return

            size = struct.unpack("!I", size)[0]
            frame_data = b""

            while len(frame_data) < size:
                packet = sock.recv(size - len(frame_data))
                if not packet:
                    break
                frame_data += packet

            img = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue

            img_pil = Image.fromarray(img)
            img_tk = ImageTk.PhotoImage(img_pil)

            canvas.itemconfig(image_container, image=img_tk)
            canvas.img_tk = img_tk

        except Exception as e:
            print(f"[EROARE] {e}")
            break

def start_receiving():
    threading.Thread(target=receive_frames, daemon=True).start()

def stop_capture():
    global running
    running = False
    print("[INFO] Captura oprită.")
    root.quit()

connect_button = tk.Button(root, text="Conectează", command=connect_to_stream, padx=10, pady=5)
connect_button.pack(pady=5)

status_label = tk.Label(root, text="", fg="blue")
status_label.pack()

stop_button = tk.Button(root, text="Oprește Captura", command=stop_capture, padx=10, pady=5, bg="red", fg="white")
stop_button.pack(pady=10)

root.mainloop()

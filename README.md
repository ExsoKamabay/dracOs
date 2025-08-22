# Dokumentasi Server & Client (dracOs Control)

kode program ini terdiri dari **dua file utama**: `server.py` dan `client.py`.  
Keduanya membentuk sistem komunikasi berbasis **TCP Socket** antara server dan client dengan protokol JSON.

---

## 🔹 Alur Kerja

### 1. Server (`server.py`)
- **Konfigurasi**  
  - Server mengambil **host** dan **port** dari file JSON di URL:
    ```
    https://raw.githubusercontent.com/ExsoKamabay/dracOs/refs/heads/main/CONFIG_URL.json
    ```
    Bagian `server` di JSON menentukan host & port yang digunakan untuk listen.

- **Proses utama**
  1. Menjalankan socket server (listen).
  2. Saat ada koneksi masuk → menjalankan `handle_client` di thread terpisah.
  3. Menyimpan informasi client ke dictionary global `clients`.
  4. Menunggu input dari operator melalui command line (`dracOs>`).

- **Pesan yang diterima server**
  - `dracOs`: identitas & informasi perangkat client (hostname, OS, RAM, storage, dll).
  - `status`: pesan status dari client (misalnya output perintah).
  - `file`: file hasil kiriman client (base64 → disimpan di server).

- **Perintah utama server**
  - `list` → Menampilkan daftar client yang terhubung & detail perangkat.
  - `connect <hostname[IP]>` → Masuk ke **shell remote** client. Bisa kirim perintah OS.
  - `<hostname[IP]> cfile "isi" "/path/file.txt"` → Membuat file di client.
  - `<hostname[IP]> import "/path/client.txt" "./downloads"` → Meminta client mengirim file.
  - `<hostname[IP]> export "./server.txt" "/sdcard/"` → Mengirim file dari server ke client.
  - `help` → Menampilkan menu bantuan.
  - `quit()` → Mematikan server.

---

### 2. Client (`client.py`)
- **Konfigurasi**
  - Client membaca **host** dan **port** dari bagian `client` di file JSON yang sama.
  - Contoh JSON:
    ```json
    {
      "server": {"host": "0.0.0.0", "port": 8080},
      "client": {"host": "0.0.0.0", "port": 8080}
    }
    ```

- **Proses utama**
  1. Membuat koneksi ke server.
  2. Mengirim informasi perangkat (`dracOs`) saat pertama kali connect.
  3. Menunggu instruksi dari server dan mengeksekusinya.

- **Pesan yang diproses client**
  - `command` → Menjalankan perintah shell (cd, ls, dir, dll) lalu mengirim output ke server.
  - `cfile` → Membuat file dengan isi tertentu di path yang ditentukan.
  - `import` → Membaca file lokal client → mengirim ke server.
  - `export` → Menerima file dari server → simpan di client.

- **Deteksi perangkat**
  - Client otomatis mendeteksi **Windows**, **Linux**, atau **Android/Termux**.
  - Informasi dikumpulkan: hostname, IP publik, MAC, RAM, storage, CPU, OS version, working directory, dll.



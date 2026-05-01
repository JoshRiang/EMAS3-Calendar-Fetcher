# EMAS UI Task API
API sederhana berbasis FastAPI untuk mengonversi data kalender iCal dari EMAS UI (Moodle) menjadi format JSON yang rapi dan sudah difilter berdasarkan waktu.

# ✨ Fitur
- Auto-Fetch: Mengambil data langsung dari URL EMAS UI.
- iCal Unfolding: Memperbaiki baris deskripsi yang terpotong secara otomatis.
- Smart Filter: Hanya menampilkan tugas yang deadline-nya belum terlewati (DTEND >= current_time).
- FastAPI Powered: Performa tinggi dan dokumentasi otomatis via Swagger UI.

# 🛠️ Tech Stack
- Python 3.10+
- FastAPI & Uvicorn
- Standard Libraries: re, urllib, datetime (Tanpa parser iCal berat).

# 🚀 Cara Pakai
1. Clone repo ini.
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn
   ```
3. Jalankan server:
   ```bash
    uvicorn main:app --reload
    ```
4. Akses endpoint:
    ```
    GET http://localhost:8000/tasks?url=YOUR_EMAS_ICAL_URL
    ``` 
5. Lihat hasil JSON yang sudah difilter berdasarkan waktu.

# 📄 Lisensi
MIT License. Bebas digunakan, dimodifikasi, dan didistribusikan dengan atribusi yang sesuai. Lihat LICENSE untuk detail.
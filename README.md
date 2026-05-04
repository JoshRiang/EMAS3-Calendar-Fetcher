# EMAS UI Task API

API FastAPI untuk mengambil tugas EMAS, mengubahnya menjadi checklist plaintext, lalu menyinkronkannya ke Google Keep.

# ✨ Fitur

- Auto-Fetch: Mengambil data tugas dari source API EMAS.
- Normalisasi teks: Menghapus prefix `Submission` dan suffix `is due`.
- Mapping kategori: Mengubah kode matkul ke nama yang human-readable.
- Google Keep sync: Menambah atau memperbarui note tanpa duplikasi judul.
- FastAPI Powered: Swagger UI aktif bawaan.

# 🛠️ Tech Stack

- Python 3.10+
- FastAPI & Uvicorn
- `gkeepapi` untuk integrasi Google Keep.
- Standard Libraries: `re`, `urllib`, `json`, `datetime`.

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
4. Set environment variable di `.env`:
   - `CALENDAR_KEY`
   - `GOOGLE_KEEP_EMAIL`
   - `GOOGLE_KEEP_MASTER_TOKEN` atau `GOOGLE_KEEP_APP_PASSWORD`
5. Sinkronkan ke Google Keep:

   ```bash
   GET http://localhost:8000/keep?key=https://emas3.ui.ac.id/calendar/export_execute.php?userid=...&authtoken=...&preset_what=all&preset_time=recentupcoming&title=Tugas%20EMAS%20UI%20Joshua
   ```

6. Hasil sukses mengembalikan JSON `200 OK` dengan jumlah item yang ditambahkan.

# 📌 Format Note Google Keep

```
Tugas EMAS UI Joshua
[ ] [Nama Tugas] ([Mata Kuliah]) - Deadline: [Tanggal/Waktu]
```

# 🔐 Credential

- `GOOGLE_KEEP_MASTER_TOKEN` adalah jalur yang paling stabil untuk `gkeepapi`.
- `GOOGLE_KEEP_APP_PASSWORD` disediakan sebagai fallback bila flow akun memungkinkan.
- Simpan semua secret di `.env`, jangan di-hardcode.

# ⏱ Otomasi

- Jika ingin sinkron otomatis, jalankan endpoint `/keep` lewat cron server atau scheduler seperti `APScheduler`.
- Contoh jadwal yang relevan: jam 08:00 dan 20:00 setiap hari.

# 📄 Lisensi

MIT License. Bebas digunakan, dimodifikasi, dan didistribusikan dengan atribusi yang sesuai. Lihat LICENSE untuk detail.

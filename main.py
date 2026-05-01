from fastapi import FastAPI, HTTPException
import re
import urllib.request
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Inisialisasi FastAPI dan Load .env
app = FastAPI(title="EMAS UI Task API")
load_dotenv()

def fetch_and_filter():
    # 1. Cek ketersediaan URL di Environment Variable
    url = os.getenv("CALENDAR_KEY")
    if not url:
        raise HTTPException(status_code=500, detail="CALENDAR_KEY tidak ditemukan di environment variables.")

    try:
        # 2. Ambil data dari EMAS UI
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal mengambil data dari EMAS: {str(e)}")

    # 3. Pre-processing: Unfolding baris yang terpotong
    unfolded = re.sub(r'\r?\n[ \t]', '', content)
    
    events = []
    current_event = None
    # Menggunakan timezone-aware UTC untuk akurasi di server hosting
    now = datetime.now(timezone.utc)

    # 4. Parsing iCalendar
    for line in unfolded.splitlines():
        line = line.strip()
        if not line:
            continue

        if line == "BEGIN:VEVENT":
            current_event = {}
        elif line == "END:VEVENT":
            if current_event:
                dt_end_str = current_event.get('DTEND', '')
                try:
                    # Parse string iCal (20260501T165500Z) ke object datetime
                    # Kita asumsikan format selalu diakhiri 'Z' (UTC)
                    dt_end_obj = datetime.strptime(dt_end_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                    
                    # Filter: Masukkan hanya jika belum melewati deadline
                    if dt_end_obj >= now:
                        events.append(current_event)
                except ValueError:
                    # Jika DTEND tidak valid, kita tetap masukkan atau abaikan
                    pass
            current_event = None
            
        elif ":" in line and current_event is not None:
            # Hanya isi data jika kita sedang berada di dalam blok VEVENT
            key, value = line.split(":", 1)
            # Membersihkan karakter escape umum di format iCal
            clean_value = value.replace('\\n', '\n').replace('\\,', ',').replace('\\;', ';').strip()
            current_event[key] = clean_value

    return events

@app.get("/")
def read_root():
    return {
        "status": "online", 
        "server_time": datetime.now(timezone.utc).isoformat(),
        "message": "EMAS UI Task API is running"
    }

@app.get("/tugas")
def get_tugas():
    data = fetch_and_filter()
    if not data:
        return {"message": "Tidak ada tugas mendatang.", "data": []}
    return data
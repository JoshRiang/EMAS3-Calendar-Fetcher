from fastapi import FastAPI, HTTPException, Query
import re
import urllib.request
from datetime import datetime, timezone
import os

app = FastAPI(title="EMAS UI Task API (Multi-User)")

def fetch_and_filter(url: str):
    try:
        # 1. Ambil data dari EMAS UI menggunakan URL dari parameter
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=502, detail="URL EMAS tidak valid atau gagal dihubungi.")

    # 2. Pre-processing: Unfolding
    unfolded = re.sub(r'\r?\n[ \t]', '', content)
    
    events = []
    current_event = None
    now = datetime.now(timezone.utc)

    # 3. Parsing iCalendar
    for line in unfolded.splitlines():
        line = line.strip()
        if not line: continue

        if line == "BEGIN:VEVENT":
            current_event = {}
        elif line == "END:VEVENT":
            if current_event:
                dt_end_str = current_event.get('DTEND', '')
                try:
                    dt_end_obj = datetime.strptime(dt_end_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                    if dt_end_obj >= now:
                        events.append(current_event)
                except ValueError:
                    pass
            current_event = None
        elif ":" in line and current_event is not None:
            key, value = line.split(":", 1)
            clean_value = value.replace('\\n', '\n').replace('\\,', ',').replace('\\;', ';').strip()
            current_event[key] = clean_value

    return events

@app.get("/")
def read_root():
    return {"message": "Gunakan endpoint /tugas?key=URL_KALENDER_KAMU"}

@app.get("/tugas")
def get_tugas(key: str = Query(..., description="URL Export dari EMAS UI")):
    # Validasi sederhana apakah ini URL EMAS
    if "emas3.ui.ac.id" not in key:
        raise HTTPException(status_code=400, detail="URL harus berasal dari emas3.ui.ac.id")
    
    data = fetch_and_filter(key)
    return data
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import re
import urllib.request
from datetime import datetime, timezone
import os

app = FastAPI(title="EMAS UI Task API")

# Tambahkan CORS biar bisa di-hit dari Svelte/React kamu nanti
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_and_filter(url: str):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')
            
        # Cek apakah isinya HTML (halaman login) bukannya iCal
        if "<html" in content.lower():
            raise HTTPException(status_code=401, detail="URL/Token salah atau kadaluarsa (EMAS mengembalikan halaman login).")
            
    except HTTPException as he: raise he
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal koneksi ke EMAS: {str(e)}")

    # Unfolding lebih kuat (menangani spasi biasa, tab, dan non-breaking space)
    unfolded = re.sub(r'\r?\n[ \t\u00a0]', '', content)
    
    events = []
    current_event = None
    now = datetime.now(timezone.utc)

    for line in unfolded.splitlines():
        line = line.strip()
        if not line: continue

        if line == "BEGIN:VEVENT":
            current_event = {}
        elif line == "END:VEVENT":
            if current_event:
                # Ambil DTEND atau DTSTART jika DTEND tidak ada
                dt_str = current_event.get('DTEND') or current_event.get('DTSTART', '')
                # Bersihkan Z untuk parsing manual agar lebih fleksibel
                clean_dt = dt_str.replace('Z', '')
                
                try:
                    # Coba parse format lengkap atau hanya tanggal
                    if 'T' in clean_dt:
                        dt_obj = datetime.strptime(clean_dt, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                    else:
                        dt_obj = datetime.strptime(clean_dt, "%Y%m%d").replace(tzinfo=timezone.utc)
                    
                    if dt_obj >= now:
                        events.append(current_event)
                except: pass
            current_event = None
        elif ":" in line and current_event is not None:
            # Handle key yang punya parameter (misal: DTEND;VALUE=DATE:...)
            raw_key, value = line.split(":", 1)
            key = raw_key.split(";")[0] 
            current_event[key] = value.replace('\\n', '\n').replace('\\,', ',').strip()

    return events

@app.get("/")
def read_root():
    return {"status": "online", "guide": "Gunakan /tugas?key=URL_FULL_EMAS"}

@app.get("/tugas")
def get_tugas(key: str = Query(..., description="URL Export EMAS UI")):
    # Pastikan URL tidak terpotong
    if "authtoken=" not in key:
        raise HTTPException(status_code=400, detail="Token tidak ditemukan. Pastikan copy URL secara utuh.")
        
    data = fetch_and_filter(key)
    return data
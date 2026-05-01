from fastapi import FastAPI
import re
import urllib.request
from datetime import datetime
import json
import os
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()

def fetch_and_filter():
    url = os.getenv("CALENDAR_KEY")
    if not url:
        return []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
    except Exception:
        return []

    unfolded = re.sub(r'\r?\n[ \t]', '', content)
    events = []
    now = datetime.utcnow()

    for line in unfolded.splitlines():
        line = line.strip()
        if not line or "BEGIN:VEVENT" == line:
            current_event = {}
        elif line == "END:VEVENT":
            dt_end_str = current_event.get('DTEND', '')
            try:
                dt_end_obj = datetime.strptime(dt_end_str, "%Y%m%dT%H%M%SZ")
                if dt_end_obj >= now:
                    events.append(current_event)
            except: pass
        elif ":" in line:
            key, value = line.split(":", 1)
            current_event[key] = value.replace('\\n', '\n').replace('\\,', ',').strip()
    return events

@app.get("/")
def read_root():
    return {"status": "online", "message": "EMAS UI Task API"}

@app.get("/tugas")
def get_tugas():
    data = fetch_and_filter()
    return data
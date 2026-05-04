import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import gkeepapi

app = FastAPI(title="EMAS UI Task API")
load_dotenv()

KEEP_NOTE_TITLE = os.getenv("KEEP_NOTE_TITLE", "Tugas EMAS UI Joshua")
SOURCE_API_BASE_URL = os.getenv(
    "SOURCE_API_BASE_URL",
    "https://emas3-calendar-fetcher.onrender.com/tugas",
)
SOURCE_API_TIMEOUT_SECONDS = int(os.getenv("SOURCE_API_TIMEOUT_SECONDS", "60"))
SOURCE_API_RETRY_COUNT = int(os.getenv("SOURCE_API_RETRY_COUNT", "2"))

CATEGORY_MAP = {
"ENFE600003": "Dasar Analitik Data",
  "ENCE604014": "DMJK",
  "ENCE604015": "Komputasi Numerik",
  "ENCE604013": "Matematika Lanjut",
  "ENCE606033": "Profesionalisme dan Etika",
  "ENCE604016": "Sistem Basis Data",
  "ENCE604017": "Sistem Embedded",
  "ENCE604018": "Sistem Operasi"
}

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


def fetch_tasks_from_source_api(calendar_key: str):
    source_url = f"{SOURCE_API_BASE_URL.rstrip('/')}?key={urllib.parse.quote(calendar_key, safe='')}"

    last_error = None
    for attempt in range(SOURCE_API_RETRY_COUNT + 1):
        try:
            req = urllib.request.Request(source_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=SOURCE_API_TIMEOUT_SECONDS) as response:
                raw_payload = response.read().decode("utf-8")
            payload = json.loads(raw_payload)
            if not isinstance(payload, list):
                raise RuntimeError("Format respons source API tidak valid")
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < SOURCE_API_RETRY_COUNT:
                continue

    try:
        return fetch_and_filter(calendar_key)
    except Exception as fallback_exc:
        raise RuntimeError(
            f"Gagal mengambil data dari source API ({last_error}); fallback EMAS langsung juga gagal: {fallback_exc}"
        ) from fallback_exc


def clean_summary(summary: str) -> str:
    cleaned = re.sub(r"(?i)^\s*submission\s+", "", summary or "")
    cleaned = re.sub(r"(?i)\s+is due\s*$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -:") or "Tugas tanpa judul"


def resolve_category_label(category_value) -> str:
    if isinstance(category_value, list):
        category_value = next((item for item in category_value if item), "")
    if category_value is None:
        category_value = ""

    raw_category = str(category_value).split(",")[0].strip()
    return CATEGORY_MAP.get(raw_category, raw_category or "Tanpa Mata Kuliah")


def parse_deadline(value: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return "Deadline tidak diketahui"

    if raw_value.endswith("Z"):
        parsed = datetime.strptime(raw_value[:-1], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if re.search(r"[+-]\d{4}$", raw_value):
        parsed = datetime.strptime(raw_value, "%Y%m%dT%H%M%S%z")
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if "T" in raw_value:
        parsed = datetime.strptime(raw_value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return parsed.strftime("%Y-%m-%d %H:%M UTC")

    parsed = datetime.strptime(raw_value, "%Y%m%d")
    return parsed.strftime("%Y-%m-%d")


def build_keep_line(event: dict) -> str:
    summary = clean_summary(event.get("SUMMARY", ""))
    category = resolve_category_label(event.get("CATEGORIES", ""))
    deadline_value = event.get("DTSTART") or event.get("DTEND") or ""
    deadline = parse_deadline(deadline_value)
    return f"[ ] {summary} ({category}) - Deadline: {deadline}"


def normalize_keep_line(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().lower()


def merge_keep_text(existing_text: str, new_lines: list[str]) -> tuple[str, int]:
    merged_lines = []
    seen = set()

    for line in (existing_text or "").splitlines():
        normalized = normalize_keep_line(line)
        if not normalized or normalized in seen:
            continue
        merged_lines.append(line.strip())
        seen.add(normalized)

    added_count = 0
    for line in new_lines:
        normalized = normalize_keep_line(line)
        if not normalized or normalized in seen:
            continue
        merged_lines.append(line)
        seen.add(normalized)
        added_count += 1

    return "\n".join(merged_lines), added_count


def load_keep_client() -> gkeepapi.Keep:
    keep_email = os.getenv("GOOGLE_KEEP_EMAIL")
    master_token = os.getenv("GOOGLE_KEEP_MASTER_TOKEN")
    app_password = os.getenv("GOOGLE_KEEP_APP_PASSWORD")

    if not keep_email:
        raise RuntimeError("GOOGLE_KEEP_EMAIL belum diatur")

    keep = gkeepapi.Keep()

    if master_token:
        keep.authenticate(keep_email, master_token)
        return keep

    if app_password:
        keep.login(keep_email, app_password)
        return keep

    raise RuntimeError("GOOGLE_KEEP_MASTER_TOKEN atau GOOGLE_KEEP_APP_PASSWORD belum diatur")


def find_note_by_title(keep: gkeepapi.Keep, title: str):
    matches = keep.find(func=lambda node: not node.deleted and getattr(node, "title", "") == title)
    return next(iter(matches), None)

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


@app.get("/keep")
def sync_to_keep(key: str = Query(..., description="URL kalender EMAS full"), title: str = Query(default=KEEP_NOTE_TITLE, description="Judul note Google Keep")):
    try:
        tasks = fetch_tasks_from_source_api(key)
        checklist_lines = [build_keep_line(task) for task in tasks]

        if not checklist_lines:
            return {
                "status": "ok",
                "note_title": title,
                "added": 0,
                "total_tasks": 0,
                "message": "Tidak ada tugas baru untuk disinkronkan",
            }

        keep = load_keep_client()
        existing_note = find_note_by_title(keep, title)

        if existing_note is None:
            keep.createNote(title, "\n".join(checklist_lines))
            action = "created"
            added_count = len(checklist_lines)
        else:
            merged_text, added_count = merge_keep_text(existing_note.text or "", checklist_lines)
            if merged_text and merged_text != (existing_note.text or ""):
                existing_note.text = merged_text
            action = "updated"

        keep.sync()

        return {
            "status": "ok",
            "note_title": title,
            "action": action,
            "added": added_count,
            "total_tasks": len(checklist_lines),
        }
    except HTTPException as exc:
        raise HTTPException(status_code=500, detail=exc.detail)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
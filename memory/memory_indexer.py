import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from rapidfuzz.utils import default_process  # Add this at the top if needed
import re
import spacy
nlp = spacy.load("en_core_web_sm")

def extract_named_entities(text: str) -> List[str]:
    doc = nlp(text)
    return [ent.text.lower() for ent in doc.ents if ent.label_ in {"GPE", "ORG", "PERSON"}]


# Constants
LOGS_BASE = Path("memory/session_logs")
INDEX_BASE = Path("memory/session_summaries_index")
META_FILE = INDEX_BASE / ".index_meta.json"
INDEX_BASE.mkdir(parents=True, exist_ok=True)

# Load or initialize metadata
if META_FILE.exists():
    with open(META_FILE, "r", encoding="utf-8") as f:
        folder_meta = json.load(f)
else:
    folder_meta = {}

def normalize_query(text: str) -> str:
    text = re.sub(r"query\s*\d+:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()

def is_valid_logfile(file_path: Path) -> bool:
    return file_path.suffix == ".json" and file_path.is_file()

def extract_summary_entry(file_path: Path) -> List[Dict]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        session = data.get("session", {})
        session_id = session.get("session_id")
        original_query = session.get("original_query")
        snapshots = session.get("summarizer_snapshots", [])

        entries = []
        for snap in snapshots:
            summary = snap.get("summary_output")
            timestamp = snap.get("timestamp", "unknown")
            if summary:
                entries.append({
                    "session_id": session_id,
                    "original_query": original_query,
                    "normalized_query": normalize_query(original_query or ""),
                    "named_entities": extract_named_entities(original_query or ""),
                    "summary_output": summary,
                    "timestamp": timestamp
                })
        return entries
    except Exception as e:
        print(f"[ERROR] Failed to parse {file_path}: {e}")
        return []

def get_month_key_from_path(path: Path) -> str:
    try:
        parts = path.parts
        year = parts[-4]
        month = parts[-3]
        return f"{year}-{month}"
    except Exception:
        return "unknown"

def build_or_update_index():
    indexed_files = set()
    index_data: Dict[str, List[Dict]] = {}
    updated_folders = {}

    for root, _, files in os.walk(LOGS_BASE):
        root_path = Path(root)
        if len(root_path.parts) < 4:
            continue  # Skip malformed folders

        month_key = get_month_key_from_path(root_path)
        if month_key == "unknown":
            continue

        folder_key = str(root_path.relative_to(LOGS_BASE))
        latest_mtime = max((os.path.getmtime(root_path / f) for f in files if is_valid_logfile(root_path / f)), default=0)

        if folder_key in folder_meta and latest_mtime <= folder_meta[folder_key]:
            continue  # Skip already indexed folder

        index_file = INDEX_BASE / f"{month_key}.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    index_data[month_key] = existing
                    for entry in existing:
                        indexed_files.add(entry["session_id"])
            except Exception:
                index_data[month_key] = []

        for file in files:
            file_path = root_path / file
            if not is_valid_logfile(file_path):
                continue

            entries = extract_summary_entry(file_path)
            if not entries:
                continue

            if month_key not in index_data:
                index_data[month_key] = []

            for entry in entries:
                if entry["session_id"] not in indexed_files:
                    index_data[month_key].append(entry)
                    indexed_files.add(entry["session_id"])

        updated_folders[folder_key] = latest_mtime

    for month_key, data in index_data.items():
        out_path = INDEX_BASE / f"{month_key}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Save updated metadata
    folder_meta.update(updated_folders)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(folder_meta, f, indent=2)

    return index_data

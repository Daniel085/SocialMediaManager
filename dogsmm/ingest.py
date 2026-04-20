from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dogsmm import queue
from dogsmm.dedupe import compute_phash

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def ingest(media_dir: Path, queue_path: Path) -> int:
    entries = queue.load(queue_path)
    existing = {e["path"] for e in entries}
    added = 0
    for p in sorted(media_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        rel = str(p.relative_to(media_dir))
        if rel in existing:
            continue
        entry = {
            "path": rel,
            "kind": "image",
            "status": "pending",
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            entry["phash"] = compute_phash(p)
        except Exception as err:
            print(f"  WARN could not hash {rel}: {err}")
        entries.append(entry)
        added += 1
    queue.save(queue_path, entries)
    return added

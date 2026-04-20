"""Read/write the queue.json state file.

Each entry is a dict:
  path:        relative path under media/
  kind:        "image" (videos are a TODO)
  status:      pending | rejected | captioned | approved | posted
  added_at:    ISO timestamp
  score:       int 1-10 (after filter)
  score_reason: str
  caption:     str (after caption)
  hashtags:    str (after caption)
  reviewed_at: ISO timestamp (after manual review, later)
  posted_at:   ISO timestamp (after posting, later)
"""
from __future__ import annotations

import json
from pathlib import Path


def load(queue_path: Path) -> list[dict]:
    if not queue_path.exists():
        return []
    return json.loads(queue_path.read_text())


def save(queue_path: Path, entries: list[dict]) -> None:
    queue_path.write_text(json.dumps(entries, indent=2) + "\n")


def find(entries: list[dict], path: str) -> dict | None:
    for e in entries:
        if e["path"] == path:
            return e
    return None

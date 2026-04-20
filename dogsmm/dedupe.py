"""Near-duplicate detection via perceptual hashing.

pHash catches burst-mode duplicates, resizes, crops, and minor edits.
It does NOT catch semantically similar photos (same dog, same pose, different
burst) — that would need vision embeddings. See README roadmap.
"""
from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image, ImageOps

from dogsmm import queue

# 64-bit hash (hash_size=8). Hamming distance 0..64.
DEFAULT_THRESHOLD = 6

# Statuses that mean "already committed to post / already posted" — new
# candidates must not duplicate these.
COMMITTED_STATUSES = {"approved", "posted"}

# Statuses that are eligible candidates for deduping.
CANDIDATE_STATUSES = {"pending", "captioned"}


def compute_phash(path: Path) -> str:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return str(imagehash.phash(img))


def _distance(a: str, b: str) -> int:
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


def ensure_hashes(media_dir: Path, entries: list[dict]) -> int:
    """Compute phash for any entry missing one. Returns count computed."""
    computed = 0
    for e in entries:
        if e.get("phash"):
            continue
        try:
            e["phash"] = compute_phash(media_dir / e["path"])
            computed += 1
        except Exception as err:
            print(f"  ERROR hashing {e['path']}: {err}")
    return computed


def dedupe_queue(media_dir: Path, queue_path: Path, threshold: int) -> dict:
    entries = queue.load(queue_path)
    ensure_hashes(media_dir, entries)
    queue.save(queue_path, entries)

    committed = [e for e in entries if e["status"] in COMMITTED_STATUSES and e.get("phash")]
    candidates = [e for e in entries if e["status"] in CANDIDATE_STATUSES and e.get("phash")]
    candidates.sort(key=lambda e: e["path"])

    stats = {"vs_posted": 0, "vs_siblings": 0, "checked": len(candidates)}

    # Reject candidates that duplicate anything already approved/posted.
    for c in candidates:
        for k in committed:
            if _distance(c["phash"], k["phash"]) <= threshold:
                c["status"] = "rejected"
                c["score_reason"] = f"near-duplicate of posted/approved: {k['path']}"
                stats["vs_posted"] += 1
                print(f"  REJECT {c['path']} — duplicate of posted {k['path']}")
                break

    # Collapse clusters among remaining candidates; first (alphabetical) wins.
    kept: list[dict] = []
    for c in candidates:
        if c["status"] == "rejected":
            continue
        match = next(
            (k for k in kept if _distance(c["phash"], k["phash"]) <= threshold),
            None,
        )
        if match is None:
            kept.append(c)
        else:
            c["status"] = "rejected"
            c["score_reason"] = f"near-duplicate of {match['path']}"
            stats["vs_siblings"] += 1
            print(f"  REJECT {c['path']} — duplicate of {match['path']}")

    queue.save(queue_path, entries)
    return stats

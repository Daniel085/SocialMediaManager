from __future__ import annotations

import re
from pathlib import Path

from anthropic import Anthropic

from dogsmm import queue
from dogsmm.vision import image_block

SCORING_PROMPT = """You are rating a candidate photo of a dog for posting on Instagram.

Rate 1-10 based on:
- Is the dog clearly visible, in focus, well-framed?
- Is the lighting/exposure decent?
- Is there something cute, funny, expressive, or interesting?
- Would this plausibly earn likes on a pet account?

Auto-rejects (score <= 3): blurry, dog barely visible, eyes closed badly, near-duplicates of obvious throwaways, accidental shots.

Respond in EXACTLY this format, nothing else:
SCORE: <integer 1-10>
REASON: <one short sentence>
"""

_SCORE_RE = re.compile(r"SCORE:\s*(\d+)", re.IGNORECASE)
_REASON_RE = re.compile(r"REASON:\s*(.+)", re.IGNORECASE)


def _parse(text: str) -> tuple[int, str]:
    score_match = _SCORE_RE.search(text)
    reason_match = _REASON_RE.search(text)
    if not score_match:
        raise ValueError(f"no SCORE in response: {text!r}")
    score = max(1, min(10, int(score_match.group(1))))
    reason = reason_match.group(1).strip() if reason_match else ""
    return score, reason


def score_image(client: Anthropic, path: Path, model: str) -> tuple[int, str]:
    resp = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [image_block(path), {"type": "text", "text": SCORING_PROMPT}],
        }],
    )
    return _parse(resp.content[0].text)


def filter_pending(
    media_dir: Path,
    queue_path: Path,
    threshold: int,
    model: str,
) -> dict:
    client = Anthropic()
    entries = queue.load(queue_path)
    stats = {"scored": 0, "rejected": 0, "kept": 0, "errors": 0}
    for e in entries:
        if e["status"] != "pending":
            continue
        path = media_dir / e["path"]
        try:
            score, reason = score_image(client, path, model)
        except Exception as err:
            print(f"  ERROR scoring {e['path']}: {err}")
            stats["errors"] += 1
            continue
        e["score"] = score
        e["score_reason"] = reason
        stats["scored"] += 1
        if score < threshold:
            e["status"] = "rejected"
            stats["rejected"] += 1
            print(f"  [{score}/10] REJECT  {e['path']} — {reason}")
        else:
            # leave status as "pending"; caption step will promote it
            stats["kept"] += 1
            print(f"  [{score}/10] keep    {e['path']} — {reason}")
        # save after each so an interrupted run isn't lost
        queue.save(queue_path, entries)
    return stats

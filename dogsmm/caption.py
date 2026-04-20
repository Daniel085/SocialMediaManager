from __future__ import annotations

import re
from pathlib import Path

import yaml
from anthropic import Anthropic

from dogsmm import queue
from dogsmm.vision import image_block

SYSTEM_TEMPLATE = """You write Instagram captions for {name}, a dog, in the first person from {pronouns} point of view.

Persona voice:
{voice}

Things {pronouns} loves:
{favorite_things}

Things {pronouns} dislikes (fodder for jokes):
{dislikes}

Caption style:
{caption_style}

Hashtag style:
{hashtag_style}

Example captions that nail the voice:
{examples}

When given a photo, respond in EXACTLY this format, nothing else:
CAPTION: <the caption text>
HASHTAGS: <space-separated hashtags, each starting with #>
"""

USER_PROMPT = "Write a caption and hashtags for this photo."

_CAPTION_RE = re.compile(r"CAPTION:\s*(.+?)(?=\nHASHTAGS:|\Z)", re.IGNORECASE | re.DOTALL)
_HASHTAGS_RE = re.compile(r"HASHTAGS:\s*(.+)", re.IGNORECASE | re.DOTALL)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "- (none)"


def build_system(persona: dict) -> str:
    return SYSTEM_TEMPLATE.format(
        name=persona.get("name", "the dog"),
        pronouns=persona.get("pronouns", "they/them"),
        voice=_bullets(persona.get("voice", [])),
        favorite_things=_bullets(persona.get("favorite_things", [])),
        dislikes=_bullets(persona.get("dislikes", [])),
        caption_style=persona.get("caption_style", "").strip() or "1-3 sentences, playful.",
        hashtag_style=persona.get("hashtag_style", "").strip() or "5-10 relevant hashtags.",
        examples=_bullets(persona.get("example_captions", [])),
    )


def _parse(text: str) -> tuple[str, str]:
    cap = _CAPTION_RE.search(text)
    tags = _HASHTAGS_RE.search(text)
    if not cap or not tags:
        raise ValueError(f"could not parse caption response: {text!r}")
    return cap.group(1).strip(), tags.group(1).strip()


def caption_image(
    client: Anthropic,
    path: Path,
    system: str,
    model: str,
) -> tuple[str, str]:
    resp = client.messages.create(
        model=model,
        max_tokens=400,
        system=[{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": [image_block(path), {"type": "text", "text": USER_PROMPT}],
        }],
    )
    return _parse(resp.content[0].text)


def caption_pending(
    media_dir: Path,
    queue_path: Path,
    persona_path: Path,
    model: str,
) -> dict:
    persona = yaml.safe_load(persona_path.read_text())
    system = build_system(persona)
    client = Anthropic()
    entries = queue.load(queue_path)
    stats = {"captioned": 0, "errors": 0, "skipped": 0}
    for e in entries:
        # Only caption items that passed filtering (status still "pending" and have a score)
        if e["status"] != "pending" or "score" not in e:
            stats["skipped"] += 1
            continue
        path = media_dir / e["path"]
        try:
            cap, tags = caption_image(client, path, system, model)
        except Exception as err:
            print(f"  ERROR captioning {e['path']}: {err}")
            stats["errors"] += 1
            continue
        e["caption"] = cap
        e["hashtags"] = tags
        e["status"] = "captioned"
        stats["captioned"] += 1
        print(f"  captioned {e['path']}")
        print(f"    {cap}")
        queue.save(queue_path, entries)
    return stats

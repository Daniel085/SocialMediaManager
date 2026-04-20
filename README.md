# Dog Social Media Manager

A local pipeline that turns a folder of dog photos into captioned, ready-to-post
Instagram content. Claude picks the good photos and writes captions in your
dog's persona. You approve, then post manually (for now).

## Pipeline

```
media/  ── ingest ──►  queue.json  ── filter ──►  scored  ── caption ──►  captioned
                                                (low scores rejected)      (ready to review)
```

State lives in a single `queue.json` at the repo root — diffable, hand-editable,
no database.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

Drop photos into `./media/` (JPEG, PNG, WEBP). Videos aren't supported yet.

Edit `persona.yaml` so captions sound like your dog.

## Usage

```bash
python -m dogsmm ingest                       # scan media/ into queue
python -m dogsmm filter --threshold 7         # score & auto-reject bad shots
python -m dogsmm caption                      # write captions for the keepers
python -m dogsmm status                       # show counts by status
```

Each command is resumable — it skips items already processed. `queue.json` is
saved after every item, so an interrupted run doesn't lose work.

## Statuses

- `pending` — ingested, not yet scored
- `rejected` — scored below threshold
- `captioned` — ready for review
- `approved` — (future) marked for posting
- `posted` — (future) already on Instagram

## Roadmap

- Review UI (local web app to approve / edit / reject captioned items)
- Video support (extract a frame with ffmpeg for vision scoring)
- Posting — manual for now; later, either an "export for Buffer/Later" step or
  automated posting via `instagrapi` (carries ban risk on personal accounts)

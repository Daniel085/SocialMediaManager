from __future__ import annotations

from collections import Counter
from pathlib import Path

import click

from dogsmm import queue as queue_mod
from dogsmm.caption import caption_pending
from dogsmm.filter import filter_pending
from dogsmm.ingest import ingest as ingest_fn

DEFAULT_QUEUE = "queue.json"
DEFAULT_MEDIA = "media"
DEFAULT_PERSONA = "persona.yaml"

SCORE_MODEL = "claude-sonnet-4-6"
CAPTION_MODEL = "claude-sonnet-4-6"


@click.group()
def cli() -> None:
    """Dog social media manager — ingest, filter, caption."""


@cli.command()
@click.option("--media-dir", default=DEFAULT_MEDIA, type=click.Path(path_type=Path))
@click.option("--queue", "queue_path", default=DEFAULT_QUEUE, type=click.Path(path_type=Path))
def ingest(media_dir: Path, queue_path: Path) -> None:
    """Scan media/ and add new files to the queue."""
    if not media_dir.exists():
        raise click.ClickException(f"{media_dir} does not exist — drop photos there first.")
    added = ingest_fn(media_dir, queue_path)
    click.echo(f"Added {added} new file(s) to {queue_path}.")


@cli.command(name="filter")
@click.option("--media-dir", default=DEFAULT_MEDIA, type=click.Path(path_type=Path))
@click.option("--queue", "queue_path", default=DEFAULT_QUEUE, type=click.Path(path_type=Path))
@click.option("--threshold", default=7, show_default=True, help="Reject scores below this.")
@click.option("--model", default=SCORE_MODEL, show_default=True)
def filter_cmd(media_dir: Path, queue_path: Path, threshold: int, model: str) -> None:
    """Score pending photos with Claude; reject low scores."""
    stats = filter_pending(media_dir, queue_path, threshold, model)
    click.echo(
        f"scored={stats['scored']} kept={stats['kept']} "
        f"rejected={stats['rejected']} errors={stats['errors']}"
    )


@cli.command()
@click.option("--media-dir", default=DEFAULT_MEDIA, type=click.Path(path_type=Path))
@click.option("--queue", "queue_path", default=DEFAULT_QUEUE, type=click.Path(path_type=Path))
@click.option("--persona", default=DEFAULT_PERSONA, type=click.Path(path_type=Path))
@click.option("--model", default=CAPTION_MODEL, show_default=True)
def caption(media_dir: Path, queue_path: Path, persona: Path, model: str) -> None:
    """Generate a caption + hashtags for each photo that passed filter."""
    stats = caption_pending(media_dir, queue_path, persona, model)
    click.echo(
        f"captioned={stats['captioned']} skipped={stats['skipped']} errors={stats['errors']}"
    )


@cli.command()
@click.option("--queue", "queue_path", default=DEFAULT_QUEUE, type=click.Path(path_type=Path))
def status(queue_path: Path) -> None:
    """Show queue counts by status."""
    entries = queue_mod.load(queue_path)
    counts = Counter(e["status"] for e in entries)
    click.echo(f"total: {len(entries)}")
    for k in ["pending", "captioned", "approved", "posted", "rejected"]:
        click.echo(f"  {k}: {counts.get(k, 0)}")

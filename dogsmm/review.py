"""Local review UI. Bind to 127.0.0.1 only — no auth."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_from_directory, url_for

from dogsmm import queue

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _stats(entries: list[dict]) -> dict:
    c = Counter(e["status"] for e in entries)
    return {
        "captioned": c.get("captioned", 0),
        "approved": c.get("approved", 0),
        "rejected": c.get("rejected", 0),
        "posted": c.get("posted", 0),
        "total": len(entries),
    }


def _next_entry(entries: list[dict]) -> dict | None:
    captioned = [e for e in entries if e["status"] == "captioned"]
    # Highest-scored first so you see the best candidates while attention is fresh.
    captioned.sort(key=lambda e: (-e.get("score", 0), e["path"]))
    return captioned[0] if captioned else None


def create_app(media_dir: Path, queue_path: Path) -> Flask:
    media_dir = media_dir.resolve()
    queue_path = queue_path.resolve()
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

    @app.route("/")
    def index() -> "Response":
        return redirect(url_for("review"))

    @app.route("/review")
    def review() -> str:
        entries = queue.load(queue_path)
        entry = _next_entry(entries)
        return render_template(
            "review.html",
            entry=entry,
            stats=_stats(entries),
        )

    @app.route("/media/<path:subpath>")
    def media(subpath: str) -> "Response":
        return send_from_directory(media_dir, subpath)

    @app.route("/action/<action>", methods=["POST"])
    def action(action: str) -> "Response":
        path = request.form["path"]
        entries = queue.load(queue_path)
        entry = queue.find(entries, path)
        if entry is None:
            return ("not found", 404)
        now = datetime.now(timezone.utc).isoformat()
        if action == "approve":
            entry["caption"] = request.form.get("caption", entry.get("caption", ""))
            entry["hashtags"] = request.form.get("hashtags", entry.get("hashtags", ""))
            entry["status"] = "approved"
            entry["reviewed_at"] = now
        elif action == "reject":
            entry["status"] = "rejected"
            entry["score_reason"] = "rejected in review"
            entry["reviewed_at"] = now
        else:
            return (f"unknown action: {action}", 400)
        queue.save(queue_path, entries)
        return redirect(url_for("review"))

    return app

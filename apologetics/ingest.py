from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import store
from .chunk import chunk
from .config import DATA_DIR, MANIFEST
from .parsers import PARSERS

LOGGER = logging.getLogger(__name__)


def _load_sources(path: str | Path = "sources.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["sources"]


def _fingerprint(source: dict) -> str:
    payload = json.dumps(source, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _read_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def ingest_sources(
    sources: list[dict],
    *,
    only: list[str] | None = None,
    refresh: bool = False,
    force: bool = False,
    max_pages: int | None = None,
    dry_run: bool = False,
) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest()
    selected = {s for s in only} if only else None
    active = {
        s["id"]: s
        for s in sources
        if s.get("enabled", True) and (selected is None or s["id"] in selected)
    }
    for source_id in list(manifest):
        if source_id not in {s["id"] for s in sources if s.get("enabled", True)}:
            LOGGER.info("Removing stale source %s", source_id)
            if not dry_run:
                store.delete_source(source_id)
            manifest.pop(source_id, None)
    for source_id, source in active.items():
        fingerprint = _fingerprint(source)
        if not force and manifest.get(source_id, {}).get("fingerprint") == fingerprint:
            LOGGER.info("Skipping unchanged source %s", source_id)
            continue
        start = time.monotonic()
        parser = PARSERS[source["kind"]]
        kwargs = {"refresh": refresh, "max_pages": max_pages}
        passages = list(parser(source, **kwargs))
        chunks = chunk(passages)
        pages = len({p.url for p in passages})
        LOGGER.info(
            "%s: pages fetched=%d passages=%d chunks=%d elapsed=%.1fs",
            source_id,
            pages,
            len(passages),
            len(chunks),
            time.monotonic() - start,
        )
        if not dry_run:
            store.delete_source(source_id)
            store.upsert(chunks)
            manifest[source_id] = {
                "fingerprint": fingerprint,
                "chunks": len(chunks),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ingest_sources(
        _load_sources(),
        only=args.only,
        refresh=args.refresh,
        force=args.force,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

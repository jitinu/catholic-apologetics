from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .parsers import Passage


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict


def _make_chunk(passages: list[Passage], ordinal: int, section: str | None = None) -> Chunk:
    first = passages[0]
    label = section or first.section
    body = "\n".join(
        f"{p.section.rsplit(' ', 1)[-1]} {p.text}" if p.kind == "verse" else p.text
        for p in passages
    )
    text = f"{label}\n{body}"
    digest = hashlib.sha1(f"{first.url}{label}{ordinal}".encode()).hexdigest()[:16]
    metadata = {
        "source_id": first.source_id,
        "source_title": first.source_title,
        "section": label,
        "url": first.url,
        "ordinal": ordinal,
    }
    for key in ("work", "author"):
        if getattr(first, key):
            metadata[key] = getattr(first, key)
    return Chunk(f"{first.source_id}:{digest}", text, metadata)


def chunk(passages: list[Passage]) -> list[Chunk]:
    if not passages:
        return []
    result: list[Chunk] = []
    current: list[Passage] = []
    current_group = None
    ordinal = 0
    carried = False
    for passage in passages:
        group = passage.group or passage.section
        if current and group != current_group:
            if not (carried and len(current) == 1):
                label = (
                    verse_range_label(current[0].section, current[-1].section)
                    if current[0].kind == "verse"
                    else None
                )
                result.append(_make_chunk(current, ordinal, label))
                ordinal += 1
            current = []
            carried = False
        current_group = group
        bible_group = passage.kind == "verse"
        if (
            current
            and not bible_group
            and (len("\n".join(p.text for p in current + [passage])) > 1200)
        ):
            result.append(_make_chunk(current, ordinal))
            ordinal += 1
            current = [current[-1], passage]
            if len("\n".join(p.text for p in current)) > 1800:
                current = [passage]
        else:
            current.append(passage)
        if passage.kind == "verse" and len(current) >= 8:
            first, last = current[0], current[-1]
            label = verse_range_label(first.section, last.section)
            result.append(_make_chunk(current, ordinal, label))
            ordinal += 1
            current = [last]
            carried = True
    if current and not (carried and len(current) == 1):
        label = None
        if current[0].kind == "verse":
            label = verse_range_label(current[0].section, current[-1].section)
        result.append(_make_chunk(current, ordinal, label))
    return result


def verse_range_label(first: str, last: str) -> str:
    book, first_ref = first.rsplit(" ", 1)
    _, last_ref = last.rsplit(" ", 1)
    chapter, verse = first_ref.split(":")
    last_chapter, last_verse = last_ref.split(":")
    if chapter == last_chapter:
        return f"{book} {chapter}:{verse}–{last_verse}"
    return first

from __future__ import annotations

import hashlib
import re
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
        f"{p.section.rsplit(' ', 1)[-1]} {p.text}" if ":" in p.section else p.text for p in passages
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
    for passage in passages:
        group = passage.group or passage.section
        if current and group != current_group:
            result.append(_make_chunk(current, ordinal))
            ordinal += 1
            current = []
        current_group = group
        bible_group = re_chapter_verse_group(group)
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
        if group and re_chapter_verse_group(group) and len(current) >= 8:
            first, last = current[0], current[-1]
            label = verse_range_label(first.section, last.section)
            result.append(_make_chunk(current, ordinal, label))
            ordinal += 1
            current = [last]
    if current:
        label = None
        if re_chapter_verse_group(current[0].group or ""):
            label = verse_range_label(current[0].section, current[-1].section)
        result.append(_make_chunk(current, ordinal, label))
    return result


def re_chapter_verse_group(value: str) -> bool:
    return bool(re.match(r".+\s+\d+$", value))


def verse_range_label(first: str, last: str) -> str:
    book, first_ref = first.rsplit(" ", 1)
    _, last_ref = last.rsplit(" ", 1)
    chapter, verse = first_ref.split(":")
    last_chapter, last_verse = last_ref.split(":")
    if chapter == last_chapter:
        return f"{book} {chapter}:{verse}–{last_verse}"
    return first

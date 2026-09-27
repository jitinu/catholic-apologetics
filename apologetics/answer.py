from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import anthropic

from . import store
from .config import CLAUDE_MODEL, ROOT_DIR, TOP_K


@dataclass
class Hit:
    tag: str
    text: str
    section: str
    source_title: str
    url: str
    distance: float


@dataclass
class Answer:
    text: str
    hits: list[Hit]
    model: str


@lru_cache(maxsize=1)
def _system_prompt() -> str:
    return (ROOT_DIR / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")


def retrieve(question: str, k: int = TOP_K) -> list[Hit]:
    return [
        Hit(
            tag=f"S{i}",
            text=item["text"],
            section=item["metadata"].get("section", ""),
            source_title=item["metadata"].get("source_title", ""),
            url=item["metadata"].get("url", ""),
            distance=item["distance"],
        )
        for i, item in enumerate(store.query(question, k), 1)
    ]


def build_user_message(mode: Literal["ask", "rebut"], user_text: str, hits: list[Hit]) -> str:
    if hits:
        passages = "\n".join(
            f"[{h.tag}] {h.source_title} — {h.section} ({h.url})\n{h.text}\n" for h in hits
        )
    else:
        passages = (
            "(No passages retrieved — the local library is empty or returned nothing relevant.)"
        )
    if mode == "rebut":
        prompt = (
            f"Argument to rebut:\n{user_text}\n\n"
            "Produce a sourced, steel-manned counter-argument following Rebut mode."
        )
    else:
        prompt = f"Question:\n{user_text}"
    return f"Retrieved passages:\n{passages}\n\n{prompt}"


def link_citations(text: str, hits: list[Hit]) -> str:
    by_tag = {h.tag: h for h in hits}

    def repl(match: re.Match) -> str:
        tag = match.group(1)
        hit = by_tag.get(tag)
        if not hit:
            return match.group(0)
        title = f"{hit.source_title} — {hit.section}".replace('"', "&quot;")
        return f'[{tag}]({hit.url} "{title}")'

    return re.sub(r"\[(S\d+)\]", repl, text)


def sources_table(hits: list[Hit]) -> list[Hit]:
    return hits


def answer(
    mode: Literal["ask", "rebut"],
    user_text: str,
    k: int = TOP_K,
    client=None,
) -> Answer:
    hits = retrieve(user_text, k)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    client = client or anthropic.Anthropic()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=_system_prompt(),
        messages=[{"role": "user", "content": build_user_message(mode, user_text, hits)}],
    )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", "text") == "text"
    )
    return Answer(link_citations(text, hits), hits, CLAUDE_MODEL)

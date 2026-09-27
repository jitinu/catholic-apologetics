from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from google import genai
from google.genai import types

from . import store
from .config import GEMINI_API_KEY, GEMINI_MODEL, ROOT_DIR, TOP_K


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


def build_user_message(user_text: str, hits: list[Hit]) -> str:
    if hits:
        passages = "\n".join(
            f"[{h.tag}] {h.source_title} — {h.section} ({h.url})\n{h.text}\n" for h in hits
        )
    else:
        passages = (
            "(No passages retrieved — the local library is empty or returned nothing relevant.)"
        )
    return f"Retrieved passages:\n{passages}\n\nUser input:\n{user_text}"


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


def answer(user_text: str, k: int = TOP_K, client=None) -> Answer:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set — get a free key at https://aistudio.google.com/apikey"
        )
    hits = retrieve(user_text, k)
    client = client or genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=build_user_message(user_text, hits),
        config=types.GenerateContentConfig(
            system_instruction=_system_prompt(),
            max_output_tokens=4000,
        ),
    )
    text = response.text or ""
    return Answer(link_citations(text, hits), hits, GEMINI_MODEL)

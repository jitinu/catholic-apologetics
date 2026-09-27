from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import requests
from google import genai
from google.genai import types

from . import store
from .config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_BACKEND,
    OLLAMA_MODEL,
    OLLAMA_URL,
    ROOT_DIR,
    TOP_K,
)


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


def _generate_gemini(system: str, user: str, client=None) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set — get a free key at https://aistudio.google.com/apikey"
        )
    client = client or genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=4000,
        ),
    )
    return response.text or ""


def _generate_ollama(system: str, user: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL.rstrip('/')}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"num_ctx": 16384, "temperature": 0.3},
            },
            timeout=600,
        )
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Ollama is not running. Install it from https://ollama.com/download, "
            "then run `ollama serve` (it usually starts automatically)."
        ) from exc
    if response.status_code == 404 or "model not found" in response.text.lower():
        raise RuntimeError(
            f"Model {OLLAMA_MODEL} is not downloaded. Run: ollama pull {OLLAMA_MODEL}"
        )
    response.raise_for_status()
    return response.json()["message"]["content"]


def answer(user_text: str, k: int = TOP_K, client=None, backend: str = LLM_BACKEND) -> Answer:
    hits = retrieve(user_text, k)
    user = build_user_message(user_text, hits)
    system = _system_prompt()
    if backend == "gemini":
        text = _generate_gemini(system, user, client)
        model = GEMINI_MODEL
    elif backend == "ollama":
        text = _generate_ollama(system, user)
        model = f"ollama/{OLLAMA_MODEL}"
    else:
        raise RuntimeError(f"Unsupported LLM_BACKEND: {backend}")
    return Answer(link_citations(text, hits), hits, model)

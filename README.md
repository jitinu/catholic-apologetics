# Catholic Apologetics Q&A

## What it is

This is a personal, local, single-user retrieval-augmented Catholic apologetics
assistant. It has no authentication and keeps its downloaded sources and vector
index on your machine, then uses Google Gemini to write cited answers.

## Requirements

Python 3.10 or newer.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...
```

Get a free Gemini API key at https://aistudio.google.com/apikey. The free tier
has daily and per-minute rate limits. Optionally set `GEMINI_MODEL` or
`APOLOGETICS_DATA_DIR`.

## Ingest

```bash
python -m apologetics.ingest
```

The first run downloads the sources and the Chroma embedding model and can take
on the order of tens of minutes depending on network speed. For a quick test:

```bash
python -m apologetics.ingest --only ccc fathers --max-pages 3
```

## Run

```bash
streamlit run app.py
```

Use the single input box to ask a question or paste an argument to rebut; the
assistant detects which kind of response is appropriate.

## Adding sources

Edit `sources.yaml`, then run ingestion again. Entries are fingerprinted, so
unchanged sources are skipped.

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit interface |
| `apologetics/fetch.py` | HTTP cache and retry handling |
| `apologetics/parsers.py` | Source-specific parsers |
| `apologetics/chunk.py` | Passage grouping and metadata |
| `apologetics/store.py` | Chroma persistence and queries |
| `apologetics/ingest.py` | Ingestion CLI and manifest |
| `apologetics/answer.py` | Retrieval, Gemini prompt, and citations |
| `sources.yaml` | Source catalog |
| `STYLE.md` | Answer style guide |
| `SYSTEM_PROMPT.md` | Gemini system instructions |

## Dev

```bash
ruff check . && pytest
```

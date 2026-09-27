# Catholic Apologetics Q&A

## What it is

This is a personal, local, single-user retrieval-augmented Catholic apologetics
assistant. It has no authentication and keeps its downloaded sources and vector
index on your machine, then uses a local Ollama model or Google Gemini to write
cited answers.

## Requirements

Python 3.10 or newer.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Choosing a model

### Option A: Ollama (default, recommended)

Ollama is free, local, and requires no account. Install it from
https://ollama.com/download, then pull the default model:

```bash
ollama pull llama3.1:8b
```

An 8B model needs roughly 8 GB of RAM. On a weaker machine, use
`OLLAMA_MODEL=llama3.2:3b`. The first answer may take a minute on a CPU.
Set `OLLAMA_URL` if Ollama is running somewhere other than its default
`http://localhost:11434`.

### Option B: Google Gemini

Gemini is a free-tier alternative, but requires a Google account and users
must be 18 or older. Get a key at https://aistudio.google.com/apikey:

```bash
export LLM_BACKEND=gemini
export GEMINI_API_KEY=...
```

The free tier has daily and per-minute rate limits. Optionally set
`GEMINI_MODEL` or `APOLOGETICS_DATA_DIR`.

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
| `apologetics/answer.py` | Retrieval, Ollama/Gemini generation, and citations |
| `sources.yaml` | Source catalog |
| `STYLE.md` | Answer style guide |
| `SYSTEM_PROMPT.md` | Gemini system instructions |

## Dev

```bash
ruff check . && pytest
```

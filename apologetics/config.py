import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("APOLOGETICS_DATA_DIR", ROOT_DIR / "data"))
CHROMA_DIR = DATA_DIR / "chroma"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST = DATA_DIR / "manifest.json"
COLLECTION = "apologetics"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TOP_K = 8
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
LLM_BACKEND = os.environ.get("LLM_BACKEND") or ("gemini" if GEMINI_API_KEY else "ollama")

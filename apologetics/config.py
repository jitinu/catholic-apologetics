import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("APOLOGETICS_DATA_DIR", ROOT_DIR / "data"))
CHROMA_DIR = DATA_DIR / "chroma"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST = DATA_DIR / "manifest.json"
COLLECTION = "apologetics"
CLAUDE_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
TOP_K = 8
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

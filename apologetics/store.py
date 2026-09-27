from __future__ import annotations

from .config import CHROMA_DIR, COLLECTION


def _collection():
    import chromadb
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        COLLECTION,
        metadata={"hnsw:space": "cosine"},
        embedding_function=DefaultEmbeddingFunction(),
    )


def upsert(chunks):
    collection = _collection()
    for i in range(0, len(chunks), 256):
        batch = chunks[i : i + 256]
        collection.upsert(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[c.metadata for c in batch],
        )


def delete_source(source_id: str):
    _collection().delete(where={"source_id": source_id})


def query(text: str, k: int = 8):
    result = _collection().query(query_texts=[text], n_results=k)
    hits = []
    for values in zip(
        result.get("documents", [[]])[0],
        result.get("metadatas", [[]])[0],
        result.get("distances", [[]])[0],
    ):
        hits.append({"text": values[0], "metadata": values[1], "distance": values[2]})
    return hits


def count() -> int:
    try:
        return _collection().count()
    except (OSError, RuntimeError):
        return 0

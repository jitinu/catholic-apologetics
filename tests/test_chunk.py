from apologetics.chunk import chunk
from apologetics.parsers import Passage


def test_bible_chunks_do_not_cross_chapters():
    passages = [
        Passage("b", "Bible", f"Genesis 1:{i}", "u", "verse " * 30, group="Genesis 1")
        for i in range(1, 10)
    ] + [Passage("b", "Bible", "Genesis 2:1", "u", "new chapter", group="Genesis 2")]
    chunks = chunk(passages)
    assert all(
        not ("Genesis 1:" in c.metadata["section"] and "Genesis 2:" in c.text) for c in chunks
    )
    assert chunks[0].metadata["section"] == "Genesis 1:1–8"
    assert all(len(c.text) <= 1800 for c in chunks)

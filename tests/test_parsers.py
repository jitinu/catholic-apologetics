from pathlib import Path

from apologetics.parsers import (
    parse_catechism_vatican,
    parse_catholic_answers,
    parse_douay_rheims,
    parse_newadvent_fathers,
    parse_newadvent_summa,
)

FIXTURES = Path(__file__).parent / "fixtures"


def source(kind, title="Fixture", **extra):
    return {"id": kind, "title": title, "kind": kind, **extra}


def test_bible_parser():
    passages = list(
        parse_douay_rheims(
            source("douay_rheims_gutenberg", url="fixture://dr"),
            (FIXTURES / "dr_excerpt.txt").read_text(),
        )
    )
    assert passages[0].section == "Genesis 1:1"
    assert "In the beginning" in passages[0].text
    assert any("[Note:" in p.text for p in passages)
    assert any(p.section == "Genesis 2:1" for p in passages)


def test_ccc_parser():
    passages = list(
        parse_catechism_vatican(
            source("catechism_vatican", index_url="fixture://ccc"),
            (FIXTURES / "ccc_excerpt.htm").read_text(),
        )
    )
    assert [p.section for p in passages] == ["CCC 27", "CCC 28", "CCC 29", "CCC 30"]
    assert "1" not in passages[0].text
    assert "soul of man" in passages[1].text


def test_fathers_parser():
    passages = list(
        parse_newadvent_fathers(
            source("newadvent_fathers", urls=["fixture://fathers"]),
            (FIXTURES / "fathers_excerpt.htm").read_text(),
        )
    )
    assert passages[0].source_title == "St. Ignatius, Epistle to the Smyrnaeans"
    assert passages[0].section.endswith("Chapter 1. Thanks to God for your faith")
    assert all("support the mission" not in p.text for p in passages)


def test_summa_parser():
    passages = list(
        parse_newadvent_summa(
            source("newadvent_summa", index_urls=["fixture://1.htm"]),
            (FIXTURES / "summa_excerpt.htm").read_text(),
        )
    )
    assert (
        passages[0].section == "ST I, Q. 2, Art. 1 — Whether the existence of God is self-evident?"
    )
    assert len(passages) == 4


def test_catholic_answers_parser():
    passages = list(
        parse_catholic_answers(
            source("catholic_answers", urls=["fixture://ca"]),
            (FIXTURES / "ca_excerpt.htm").read_text(),
        )
    )
    assert passages[0].source_title == "Catholic Answers"
    assert passages[-1].section.endswith("Ignatius of Antioch")
    assert passages[-1].author == "Jimmy Akin"

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .fetch import fetch as default_fetch

LOGGER = logging.getLogger(__name__)
FetchFn = Callable[[str, bool], str]


@dataclass
class Passage:
    source_id: str
    source_title: str
    section: str
    url: str
    text: str
    work: str | None = None
    author: str | None = None
    group: str | None = None


def _text(node: Tag) -> str:
    for sup in node.find_all("sup"):
        sup.decompose()
    return " ".join(node.get_text(" ", strip=True).split())


def parse_douay_rheims(
    source: dict, content: str | None = None, fetch_fn: FetchFn = default_fetch, **kwargs
) -> Iterable[Passage]:
    text = content if content is not None else fetch_fn(source["url"], kwargs.get("refresh", False))
    text = re.split(r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", text, 1)[-1]
    text = re.split(r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK", text, 1)[0]
    chapter_re = re.compile(r"^(.+?) Chapter (\d+)\s*$")
    verse_re = re.compile(r"^(\d+):(\d+)\.\s+(.*)$")
    book = chapter = None
    current_ref = None
    current_text: list[str] = []
    verses: list[Passage] = []

    def emit() -> None:
        nonlocal current_ref, current_text
        if current_ref and book and chapter:
            verses.append(
                Passage(
                    source["id"],
                    source["title"],
                    f"{book} {current_ref}",
                    source["url"],
                    " ".join(current_text).strip(),
                    group=f"{book} {chapter}",
                )
            )
        current_ref, current_text = None, []

    for raw in text.replace("\r\n", "\n").splitlines():
        line = raw.strip()
        chapter_match = chapter_re.match(line)
        verse_match = verse_re.match(line)
        if chapter_match:
            emit()
            book, chapter = chapter_match.groups()
            continue
        if verse_match and book and chapter:
            emit()
            current_ref = verse_match.group(1) + ":" + verse_match.group(2)
            current_text = [verse_match.group(3)]
        elif current_ref and line:
            current_text.append(f"[Note: {line}]")
        elif line and verses and book and chapter:
            verses[-1].text += f" [Note: {line}]"
        elif not line:
            emit()
    emit()
    return verses


def parse_catechism_vatican(
    source: dict,
    content: str | None = None,
    fetch_fn: FetchFn = default_fetch,
    **kwargs,
) -> Iterable[Passage]:
    refresh = kwargs.get("refresh", False)
    index_url = source["index_url"]
    index_html = content if content is not None else fetch_fn(index_url, refresh)
    soup = BeautifulSoup(index_html, "html.parser")
    urls = [
        urljoin(index_url, a.get("href"))
        for a in soup.find_all("a", href=True)
        if re.search(r"__P[^/]+\.HTM$", a["href"], re.IGNORECASE)
    ]
    if content is not None:
        urls = [index_url]
    max_pages = kwargs.get("max_pages")
    if max_pages:
        urls = urls[:max_pages]
    for page_url in urls:
        page_html = index_html if page_url == index_url else fetch_fn(page_url, refresh)
        page = BeautifulSoup(page_html, "html.parser")
        heading = None
        footnote_started = False
        for element in page.find_all(["hr", "p"]):
            if element.name == "hr":
                if page.find_all("p") and any(
                    re.match(r"^\d{1,4}\s+", _text(previous))
                    for previous in element.find_all_previous("p")
                ):
                    footnote_started = True
                continue
            if footnote_started:
                continue
            p = element
            value = _text(p)
            if not value:
                continue
            if p.find("b") and not re.match(r"^\d{1,4}\s", value):
                heading = value
                continue
            match = re.match(r"^(\d{1,4})\s+(.*)$", value)
            if not match:
                continue
            number, body = match.groups()
            for sibling in p.find_next_siblings("p"):
                sib_text = _text(sibling)
                style = sibling.get("style", "")
                if "margin-left:35.4pt" in style and not re.match(r"^\d{1,4}\s", sib_text):
                    body += " " + sib_text
                else:
                    break
            section = f"CCC {number}"
            if heading:
                body = f"{heading}: {body}" if heading not in body else body
            yield Passage(source["id"], source["title"], section, page_url, body, group=number)


def _same_prefix_links(soup: BeautifulSoup, url: str, code: str) -> list[str]:
    found = []
    pattern = re.compile(rf"^(?:\.\./fathers/)?{re.escape(code)}\d+\.htm$", re.IGNORECASE)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if pattern.match(href):
            absolute = urljoin(url, href)
            if absolute not in found:
                found.append(absolute)
    return found


def _newadvent_title(title: str, fallback: str) -> tuple[str, str]:
    title = title.removeprefix("CHURCH FATHERS: ").strip()
    match = re.match(r"(.+?)\s+\(([^()]+)\)\s*$", title)
    if not match:
        return fallback, fallback
    work, author = match.groups()
    author = author.replace("St. ", "St. ").strip()
    return f"{author}, {work}", work


def parse_newadvent_fathers(
    source: dict,
    content: str | None = None,
    fetch_fn: FetchFn = default_fetch,
    **kwargs,
) -> Iterable[Passage]:
    refresh = kwargs.get("refresh", False)
    max_pages = kwargs.get("max_pages")
    pages_seen = 0
    for landing_url in source.get("urls", []):
        landing_html = content if content is not None else fetch_fn(landing_url, refresh)
        landing = BeautifulSoup(landing_html, "html.parser")
        code = PathLikeCode(landing_url)
        subpages = _same_prefix_links(landing, landing_url, code)
        pages = subpages or [landing_url]
        if content is not None:
            pages = [landing_url]
        for page_url in pages:
            if max_pages and pages_seen >= max_pages:
                return
            page_html = landing_html if page_url == landing_url else fetch_fn(page_url, refresh)
            pages_seen += 1
            soup = BeautifulSoup(page_html, "html.parser")
            root = soup.find(id="springfield2")
            if not root:
                continue
            title, work = _newadvent_title(
                soup.title.get_text(" ", strip=True) if soup.title else "",
                source["title"],
            )
            h1 = root.find("h1")
            work_title = _text(h1) if h1 else work
            current_h2 = None
            skipped_support = False
            for node in root.find_all(["h2", "p"]):
                if node.name == "h2":
                    if _text(node).lower() == "about this page":
                        break
                    current_h2 = _text(node)
                    continue
                value = _text(node)
                if not value or (
                    not skipped_support
                    and value.startswith("Please help support the mission of New Advent")
                ):
                    skipped_support = True
                    continue
                if node.get("id") in {"src", "contactus"}:
                    continue
                section = work_title + (f" — {current_h2}" if current_h2 else "")
                yield Passage(
                    source["id"],
                    title,
                    section,
                    page_url,
                    value,
                    work=title,
                    group=section,
                )


def PathLikeCode(url: str) -> str:
    name = urlparse(url).path.rsplit("/", 1)[-1]
    code = name.rsplit(".", 1)[0]
    if code:
        return code
    match = re.search(r"(\d+)\.htm", url, re.IGNORECASE)
    return match.group(1) if match else ""


def parse_newadvent_summa(
    source: dict,
    content: str | None = None,
    fetch_fn: FetchFn = default_fetch,
    **kwargs,
) -> Iterable[Passage]:
    refresh = kwargs.get("refresh", False)
    max_pages = kwargs.get("max_pages")
    part_names = {1: "I", 2: "I-II", 3: "II-II", 4: "III", 5: "Suppl."}
    seen = 0
    for index_url in source.get("index_urls", []):
        index_html = content if content is not None else fetch_fn(index_url, refresh)
        index = BeautifulSoup(index_html, "html.parser")
        part_num = int(PathLikeCode(index_url))
        part = part_names.get(part_num, str(part_num))
        links = []
        pattern = re.compile(r"^\.\./summa/1\d{3}\.htm$", re.IGNORECASE)
        for a in index.find_all("a", href=True):
            if pattern.match(a["href"]):
                url = urljoin(index_url, a["href"])
                if url not in links:
                    links.append(url)
        if content is not None or not links:
            links = [index_url]
        for page_url in links:
            if max_pages and seen >= max_pages:
                return
            page_html = index_html if page_url == index_url else fetch_fn(page_url, refresh)
            seen += 1
            soup = BeautifulSoup(page_html, "html.parser")
            root = soup.find(id="springfield2")
            if not root:
                continue
            h1 = root.find("h1")
            h1_text = _text(h1) if h1 else ""
            qmatch = re.match(r"Question\s+(\d+)\.\s*(.*)", h1_text)
            qlabel = f"Q. {qmatch.group(1)}" if qmatch else h1_text
            current_h2 = None
            for node in root.find_all(["h1", "h2", "p"]):
                if node.name == "h2":
                    if node.get("id", "").startswith("article"):
                        current_h2 = _text(node)
                    continue
                if node.name != "p" or not current_h2:
                    continue
                value = _text(node)
                if not value or value.startswith("Please help support"):
                    continue
                article = re.sub(
                    r"^Article (\d+)\.\s*",
                    r"Art. \1 — ",
                    current_h2,
                )
                section = f"ST {part}, {qlabel}, {article}"
                yield Passage(
                    source["id"], source["title"], section, page_url, value, group=section
                )


def parse_catholic_answers(
    source: dict,
    content: str | None = None,
    fetch_fn: FetchFn = default_fetch,
    **kwargs,
) -> Iterable[Passage]:
    refresh = kwargs.get("refresh", False)
    max_pages = kwargs.get("max_pages")
    urls = source.get("urls", [])
    if content is not None:
        urls = urls[:1] or [source.get("url", "fixture://catholic-answers")]
    for i, url in enumerate(urls):
        if max_pages and i >= max_pages:
            break
        try:
            raw = content if content is not None and i == 0 else fetch_fn(url, refresh)
        except (OSError, RuntimeError, ValueError) as exc:
            LOGGER.warning("Skipping Catholic Answers URL %s: %s", url, exc)
            continue
        soup = BeautifulSoup(raw, "html.parser")
        article = soup.find("article")
        if not article:
            continue
        h1 = article.find("h1") or soup.find("h1")
        title = _text(h1) if h1 else source["title"]
        author_tag = soup.find("meta", attrs={"name": "author"})
        author = author_tag.get("content") if author_tag else None
        body = article.find("div", class_="body-half") or article
        current_heading = None
        for node in body.find_all(["h2", "h3", "p"]):
            if node.name in {"h2", "h3"}:
                current_heading = _text(node)
                continue
            value = _text(node)
            if not value:
                continue
            section = title + (f" — {current_heading}" if current_heading else "")
            yield Passage(
                source["id"],
                "Catholic Answers",
                section,
                url,
                value,
                author=author,
                group=section,
            )


PARSERS = {
    "douay_rheims_gutenberg": parse_douay_rheims,
    "catechism_vatican": parse_catechism_vatican,
    "newadvent_fathers": parse_newadvent_fathers,
    "newadvent_summa": parse_newadvent_summa,
    "catholic_answers": parse_catholic_answers,
}

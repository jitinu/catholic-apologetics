from types import SimpleNamespace

from apologetics.answer import Hit, answer, build_user_message, link_citations


def hits():
    return [Hit("S1", "Evidence text", "CCC 27", "Catechism", "https://example.test", 0.1)]


def test_user_message():
    message = build_user_message("ask", "What is faith?", hits())
    assert "Retrieved passages:" in message
    assert "[S1] Catechism — CCC 27" in message
    assert "Question:\nWhat is faith?" in message


def test_citation_linking():
    linked = link_citations("See [S1] and [S99].", hits())
    assert "[S1](https://example.test" in linked
    assert "[S99]" in linked


def test_answer_fake_client(monkeypatch):
    monkeypatch.setattr("apologetics.answer.retrieve", lambda question, k: hits())
    fake = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Answer [S1]")]
            )
        )
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    result = answer("ask", "question", client=fake)
    assert "[S1](https://example.test" in result.text

from types import SimpleNamespace

from apologetics.answer import Hit, answer, build_user_message, link_citations


def hits():
    return [Hit("S1", "Evidence text", "CCC 27", "Catechism", "https://example.test", 0.1)]


def test_user_message():
    message = build_user_message("What is faith?", hits())
    assert "Retrieved passages:" in message
    assert "[S1] Catechism — CCC 27" in message
    assert "User input:\nWhat is faith?" in message


def test_citation_linking():
    linked = link_citations("See [S1] and [S99].", hits())
    assert "[S1](https://example.test" in linked
    assert "[S99]" in linked


def test_answer_fake_client(monkeypatch):
    monkeypatch.setattr("apologetics.answer.retrieve", lambda question, k: hits())
    fake = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: assert_generate_content_kwargs(kwargs)
        )
    )
    monkeypatch.setattr("apologetics.answer.GEMINI_API_KEY", "test")
    result = answer("question", client=fake)
    assert "[S1](https://example.test" in result.text


def assert_generate_content_kwargs(kwargs):
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["contents"].endswith("User input:\nquestion")
    assert kwargs["config"].system_instruction
    assert kwargs["config"].max_output_tokens == 4000
    return SimpleNamespace(text="Answer [S1]")

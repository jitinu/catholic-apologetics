from types import SimpleNamespace

import pytest
import requests

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
    result = answer("question", client=fake, backend="gemini")
    assert "[S1](https://example.test" in result.text


def assert_generate_content_kwargs(kwargs):
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["contents"].endswith("User input:\nquestion")
    assert kwargs["config"].system_instruction
    assert kwargs["config"].max_output_tokens == 4000
    return SimpleNamespace(text="Answer [S1]")


def test_ollama_success(monkeypatch):
    monkeypatch.setattr("apologetics.answer.retrieve", lambda question, k: hits())
    calls = {}

    def post(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return SimpleNamespace(
            status_code=200,
            text="",
            json=lambda: {"message": {"content": "Ollama answer [S1]"}},
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr("apologetics.answer.requests.post", post)
    result = answer("question", backend="ollama")
    assert result.model.startswith("ollama/")
    assert "[S1](https://example.test" in result.text
    assert calls["url"].endswith("/api/chat")
    assert calls["kwargs"]["json"]["stream"] is False
    assert calls["kwargs"]["json"]["options"] == {"num_ctx": 16384, "temperature": 0.3}


def test_ollama_connection_error(monkeypatch):
    monkeypatch.setattr("apologetics.answer.retrieve", lambda question, k: [])
    monkeypatch.setattr(
        "apologetics.answer.requests.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.ConnectionError()),
    )
    with pytest.raises(RuntimeError, match="ollama.com"):
        answer("question", backend="ollama")


def test_ollama_missing_model(monkeypatch):
    monkeypatch.setattr("apologetics.answer.retrieve", lambda question, k: [])
    response = SimpleNamespace(status_code=404, text="model not found")
    monkeypatch.setattr("apologetics.answer.requests.post", lambda *args, **kwargs: response)
    with pytest.raises(RuntimeError, match="ollama pull"):
        answer("question", backend="ollama")

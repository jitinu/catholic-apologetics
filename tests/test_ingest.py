import json

from apologetics import ingest


def test_manifest_skip_force_and_stale(monkeypatch, tmp_path):
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(ingest, "MANIFEST", manifest_path)
    monkeypatch.setattr(ingest, "DATA_DIR", tmp_path)
    calls = []

    class FakeStore:
        def delete_source(self, source_id):
            calls.append(("delete", source_id))

        def upsert(self, chunks):
            calls.append(("upsert", len(chunks)))

    monkeypatch.setattr(ingest, "store", FakeStore())
    monkeypatch.setitem(ingest.PARSERS, "fake", lambda source, **kwargs: [])
    source = {"id": "one", "title": "One", "kind": "fake"}
    manifest_path.write_text(json.dumps({"stale": {"fingerprint": "x"}}))
    ingest.ingest_sources([source], force=True)
    assert ("delete", "stale") in calls
    assert any(call[0] == "upsert" for call in calls)
    calls.clear()
    ingest.ingest_sources([source])
    assert calls == []

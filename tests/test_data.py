from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

import acled_viz.data.acled as acled_module
from acled_viz.data.acled import (
    REQUIRED_COLUMNS,
    _get_access_token,
    _read_credentials_file,
    _resolve_acled_credentials,
    fetch_gaza_events,
)


def test_fetch_gaza_events_demo_writes_cache(tmp_path) -> None:
    result = fetch_gaza_events(
        start=date(2023, 10, 1),
        end=date(2023, 10, 14),
        mode="demo",
        out_dir=tmp_path / "acled" / "gaza",
    )

    assert result.events_path.exists()
    assert result.meta_path.exists()

    frame = pd.read_parquet(result.events_path)
    for col in REQUIRED_COLUMNS:
        assert col in frame.columns

    meta = json.loads(result.meta_path.read_text(encoding="utf-8"))
    assert meta["query"]["start"] == "2023-10-01"
    assert meta["query"]["end"] == "2023-10-14"
    assert len(meta["content_hash"]) == 64


def test_read_credentials_file_plaintext(tmp_path: Path) -> None:
    creds = tmp_path / "acledcred"
    creds.write_text("[email protected]\nsuper-secret\n", encoding="utf-8")

    email, password = _read_credentials_file(creds)

    assert email == "[email protected]"
    assert password == "super-secret"


def test_read_credentials_file_json(tmp_path: Path) -> None:
    creds = tmp_path / "oauth_credentials.json"
    creds.write_text(
        json.dumps({"email": "[email protected]", "password": "secret"}),
        encoding="utf-8",
    )

    email, password = _read_credentials_file(creds)

    assert email == "[email protected]"
    assert password == "secret"


def test_resolve_acled_credentials_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ACLED_EMAIL", "[email protected]")
    monkeypatch.setenv("ACLED_PASSWORD", "from-env")

    email, password = _resolve_acled_credentials()

    assert email == "[email protected]"
    assert password == "from-env"


def test_resolve_acled_credentials_from_legacy_downloads_path(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ACLED_EMAIL", raising=False)
    monkeypatch.delenv("ACLED_PASSWORD", raising=False)
    monkeypatch.delenv("ACLED_CREDENTIALS_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    legacy_path = tmp_path / "Downloads" / "acledcred"
    legacy_path.parent.mkdir()
    legacy_path.write_text("[email protected]\nfrom-downloads\n", encoding="utf-8")

    email, password = _resolve_acled_credentials()

    assert email == "[email protected]"
    assert password == "from-downloads"


def test_request_json_sends_acled_headers(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout=30):
        captured["headers"] = {
            key.lower(): value for key, value in request.header_items()
        }
        captured["data"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(acled_module, "urlopen", fake_urlopen)

    acled_module._request_json(
        url="https://example.test/oauth/token",
        method="POST",
        data={"client_id": "acled"},
    )

    assert captured["headers"]["user-agent"] == acled_module.ACLED_USER_AGENT
    assert captured["headers"]["accept"] == "application/json"
    assert captured["headers"]["content-type"] == "application/x-www-form-urlencoded"
    assert captured["data"] == "client_id=acled"
    assert captured["timeout"] == 30


def test_get_access_token_uses_in_memory_cache(monkeypatch) -> None:
    acled_module._ACLED_TOKEN_CACHE["email"] = None
    acled_module._ACLED_TOKEN_CACHE["access_token"] = None
    acled_module._ACLED_TOKEN_CACHE["expires_at"] = 0.0

    calls = {"count": 0}
    token_request_data = {}

    def fake_request_json(*, url, method="GET", headers=None, data=None, timeout=30):
        calls["count"] += 1
        token_request_data.update(data or {})
        return {"access_token": "token-123", "expires_in": 3600}

    monkeypatch.setattr(acled_module, "_request_json", fake_request_json)

    first = _get_access_token(email="[email protected]", password="pw")
    second = _get_access_token(email="[email protected]", password="pw")

    assert first == "token-123"
    assert second == "token-123"
    assert calls["count"] == 1
    assert token_request_data["scope"] == "authenticated"

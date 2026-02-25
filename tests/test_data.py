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


def test_get_access_token_uses_in_memory_cache(monkeypatch) -> None:
    acled_module._ACLED_TOKEN_CACHE["email"] = None
    acled_module._ACLED_TOKEN_CACHE["access_token"] = None
    acled_module._ACLED_TOKEN_CACHE["expires_at"] = 0.0

    calls = {"count": 0}

    def fake_request_json(*, url, method="GET", headers=None, data=None, timeout=30):
        calls["count"] += 1
        return {"access_token": "token-123", "expires_in": 3600}

    monkeypatch.setattr(acled_module, "_request_json", fake_request_json)

    first = _get_access_token(email="[email protected]", password="pw")
    second = _get_access_token(email="[email protected]", password="pw")

    assert first == "token-123"
    assert second == "token-123"
    assert calls["count"] == 1

"""ACLED ingestion wrappers with demo and lightweight ACLED API integration."""

from __future__ import annotations

import json
import os
import time
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from acled_viz.core.paths import acled_dir
from acled_viz.core.provenance import file_sha256, write_meta
from acled_viz.data.cache import write_events
from acled_viz.data.demo import demo_events

REQUIRED_COLUMNS = [
    "event_id",
    "event_date",
    "latitude",
    "longitude",
    "event_type",
    "sub_event_type",
    "fatalities",
    "source",
]

ACLED_TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_EVENTS_URL = "https://acleddata.com/api/acled/read"
ACLED_FIELDS = (
    "event_id_cnty|event_date|latitude|longitude|event_type|sub_event_type|"
    "fatalities|source|country|admin1"
)
ACLED_TOKEN_REFRESH_BUFFER_SECONDS = 30
_ACLED_TOKEN_CACHE: dict[str, Any] = {
    "email": None,
    "access_token": None,
    "expires_at": 0.0,
}


@dataclass(frozen=True)
class AcledCacheResult:
    events_path: Path
    meta_path: Path


def cache_paths(region: str = "gaza", out_dir: Path | None = None) -> AcledCacheResult:
    target_dir = (out_dir or acled_dir(region=region)).resolve()
    return AcledCacheResult(
        events_path=target_dir / "events.parquet",
        meta_path=target_dir / "meta.json",
    )


def _canonicalize_events(frame: pd.DataFrame, start: date) -> pd.DataFrame:
    normalized = frame.copy()
    rename_map = {
        "event_id_cnty": "event_id",
        "event_id_no_cnty": "event_id",
    }
    normalized = normalized.rename(columns=rename_map)

    if "event_id" not in normalized.columns:
        normalized["event_id"] = [f"ROW-{idx}" for idx in range(len(normalized))]

    normalized["event_date"] = pd.to_datetime(normalized.get("event_date"), errors="coerce")
    normalized["latitude"] = pd.to_numeric(normalized.get("latitude"), errors="coerce")
    normalized["longitude"] = pd.to_numeric(normalized.get("longitude"), errors="coerce")
    normalized["fatalities"] = (
        pd.to_numeric(normalized.get("fatalities"), errors="coerce").fillna(0)
    )
    if "event_type" not in normalized.columns:
        normalized["event_type"] = "Unknown"
    if "sub_event_type" not in normalized.columns:
        normalized["sub_event_type"] = None

    normalized["source"] = "ACLED"
    normalized = normalized.dropna(subset=["event_date", "latitude", "longitude"])

    normalized = normalized[REQUIRED_COLUMNS].sort_values("event_date").reset_index(drop=True)
    normalized["day_index"] = (normalized["event_date"] - pd.Timestamp(start)).dt.days.astype(int)
    normalized["week_index"] = (normalized["day_index"] // 7).astype(int)

    marks = {name: idx for idx, name in enumerate(sorted(normalized["event_type"].unique()))}
    normalized["mark"] = normalized["event_type"].map(marks).astype(int)
    return normalized


def _load_snapshot_if_available() -> pd.DataFrame | None:
    local_snapshot_candidates = [
        Path(__file__).resolve().parents[3] / "acled_example.csv",
        Path(__file__).resolve().parents[4]
        / "trace"
        / "src"
        / "trace"
        / "data_files"
        / "acled_example.csv",
        Path(__file__).resolve().parents[4]
        / "motac"
        / "tests"
        / "fixtures"
        / "acled"
        / "acled_events_example.csv",
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "acled_events_example.csv",
    ]
    for snapshot in local_snapshot_candidates:
        if snapshot.exists():
            warnings.warn(
                f"Using local ACLED snapshot at {snapshot}.",
                RuntimeWarning,
                stacklevel=2,
            )
            result = pd.read_csv(snapshot)
            if "event_date" in result.columns:
                result["event_date"] = pd.to_datetime(result["event_date"], errors="coerce")
            return result
    return None


def _read_credentials_file(path: Path) -> tuple[str | None, str | None]:
    if not path.exists() or not path.is_file():
        return None, None

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, None
        email = data.get("email") or data.get("username")
        password = data.get("password")
        return email, password

    try:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return None, None
    if len(lines) < 2:
        return None, None
    return lines[0], lines[1]


def _resolve_acled_credentials() -> tuple[str, str]:
    email = os.getenv("ACLED_EMAIL")
    password = os.getenv("ACLED_PASSWORD")
    if email and password:
        return email, password

    candidate_paths: list[Path] = []
    if os.getenv("ACLED_CREDENTIALS_FILE"):
        candidate_paths.append(Path(os.environ["ACLED_CREDENTIALS_FILE"]).expanduser())
    candidate_paths.extend(
        [
            Path.home() / ".config" / "acled" / "oauth_credentials.json",
        ]
    )
    for candidate in candidate_paths:
        found_email, found_password = _read_credentials_file(candidate)
        if found_email and found_password:
            return found_email, found_password

    raise RuntimeError(
        "ACLED credentials are required for full mode. Set ACLED_EMAIL and ACLED_PASSWORD, "
        "or point ACLED_CREDENTIALS_FILE to a file containing email/password."
    )


def _request_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict[str, Any] | list[dict[str, Any]]:
    payload: bytes | None = None
    request_headers = headers.copy() if headers else {}
    if data is not None:
        payload = urlencode(data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    request = Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"ACLED request failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ACLED response was not valid JSON") from exc


def _get_access_token(email: str, password: str) -> str:
    cached_email = _ACLED_TOKEN_CACHE.get("email")
    cached_token = _ACLED_TOKEN_CACHE.get("access_token")
    cached_expiry = float(_ACLED_TOKEN_CACHE.get("expires_at") or 0.0)
    now = time.time()
    if (
        cached_email == email
        and isinstance(cached_token, str)
        and cached_token
        and now < cached_expiry - ACLED_TOKEN_REFRESH_BUFFER_SECONDS
    ):
        return cached_token

    token_payload = _request_json(
        url=ACLED_TOKEN_URL,
        method="POST",
        data={
            "username": email,
            "password": password,
            "grant_type": "password",
            "client_id": "acled",
        },
    )
    if not isinstance(token_payload, dict) or "access_token" not in token_payload:
        raise RuntimeError("Failed to get ACLED OAuth token")

    access_token = str(token_payload["access_token"])
    expires_in_raw = token_payload.get("expires_in", 300)
    try:
        expires_in = int(expires_in_raw)
    except (TypeError, ValueError):
        expires_in = 300

    _ACLED_TOKEN_CACHE["email"] = email
    _ACLED_TOKEN_CACHE["access_token"] = access_token
    _ACLED_TOKEN_CACHE["expires_at"] = now + max(expires_in, 1)
    return access_token


def _fetch_with_acled_api(start: date, end: date) -> pd.DataFrame:
    email, password = _resolve_acled_credentials()
    access_token = _get_access_token(email=email, password=password)

    query = urlencode(
        {
            "_format": "json",
            "country": "Palestine",
            "event_date": f"{start.isoformat()}|{end.isoformat()}",
            "event_date_where": "BETWEEN",
            "fields": ACLED_FIELDS,
            "limit": "50000",
        }
    )
    payload = _request_json(
        url=f"{ACLED_EVENTS_URL}?{query}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )

    if isinstance(payload, dict):
        if str(payload.get("status")) not in {"200", "None"}:
            raise RuntimeError(f"ACLED API returned status={payload.get('status')}")
        records = payload.get("data", [])
    elif isinstance(payload, list):
        records = payload
    else:
        records = []

    if not isinstance(records, list):
        raise RuntimeError("ACLED API returned an unexpected payload shape")
    return pd.DataFrame(records)


def _fetch_full_events(start: date, end: date) -> pd.DataFrame:
    try:
        return _fetch_with_acled_api(start=start, end=end)
    except RuntimeError as exc:
        if "credentials" not in str(exc).lower():
            raise

    snapshot = _load_snapshot_if_available()
    if snapshot is not None:
        return snapshot

    raise RuntimeError(
        "Full mode requires ACLED credentials (ACLED_EMAIL and ACLED_PASSWORD) "
        "or an available local ACLED snapshot."
    )


def fetch_gaza_events(
    *,
    start: date,
    end: date,
    mode: str = "demo",
    region: str = "gaza",
    out_dir: Path | None = None,
) -> AcledCacheResult:
    if end < start:
        raise ValueError("end must be on or after start")

    target_dir = (out_dir or acled_dir(region=region)).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if mode == "demo":
        raw = demo_events(start=start, end=end)
    elif mode == "full":
        raw = _fetch_full_events(start=start, end=end)
    else:
        raise ValueError("mode must be 'demo' or 'full'")

    if "country" in raw.columns:
        raw = raw[raw["country"].eq("Palestine")]
    if "admin1" in raw.columns:
        raw = raw[raw["admin1"].eq("Gaza Strip")]

    raw["event_date"] = pd.to_datetime(raw.get("event_date"), errors="coerce")
    raw = raw[(raw["event_date"].dt.date >= start) & (raw["event_date"].dt.date <= end)]

    canonical = _canonicalize_events(raw, start=start)
    events_path = target_dir / "events.parquet"
    write_events(canonical, events_path)

    meta_path = target_dir / "meta.json"
    write_meta(
        meta_path,
        {
            "region": region,
            "mode": mode,
            "query": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "required_columns": REQUIRED_COLUMNS,
            "rows": int(len(canonical)),
            "content_hash": file_sha256(events_path),
        },
    )

    return AcledCacheResult(events_path=events_path, meta_path=meta_path)


def load_cached_events(path: Path | None = None) -> pd.DataFrame:
    resolved = path or (acled_dir() / "events.parquet")
    return pd.read_parquet(resolved)


def events_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.to_dict(orient="records")

"""ACLED ingestion wrappers with demo and optional trace integration."""

from __future__ import annotations

import importlib
import importlib.util
import os
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

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


def _fetch_with_trace(start: date, end: date) -> pd.DataFrame:
    fetch_acled_data = None
    try:
        trace_data_module = importlib.import_module("trace.data")
        fetch_acled_data = getattr(trace_data_module, "fetch_acled_data", None)
    except Exception:  # pragma: no cover - optional dependency path
        fetch_acled_data = None

    if not callable(fetch_acled_data):
        local_trace_data = (
            Path(__file__).resolve().parents[4] / "trace" / "src" / "trace" / "data.py"
        )
        if local_trace_data.exists():
            spec = importlib.util.spec_from_file_location("trace_data_local", local_trace_data)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                fetch_acled_data = getattr(module, "fetch_acled_data", None)

    if not callable(fetch_acled_data):
        raise RuntimeError(
            "trace dependency is unavailable; use --mode demo or install trace/motac deps"
        )

    api_token = os.getenv("ACLED_API_KEY") or os.getenv("ACLED_API_TOKEN")
    api_email = os.getenv("ACLED_EMAIL")

    if api_token and api_email:
        try:
            result = fetch_acled_data(
                country="Palestine",
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                api_token=api_token,
                api_email=api_email,
            )
        except Exception as exc:
            raise RuntimeError(f"Trace ACLED fetch failed: {exc}") from exc
        if not isinstance(result, pd.DataFrame):
            raise RuntimeError("trace fetch_acled_data did not return a DataFrame")
        return result

    local_snapshot_candidates = [
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
                (
                    f"Using local ACLED snapshot at {snapshot} because "
                    "ACLED_API_KEY/ACLED_EMAIL are not set."
                ),
                RuntimeWarning,
                stacklevel=2,
            )
            result = pd.read_csv(snapshot)
            if "event_date" in result.columns:
                result["event_date"] = pd.to_datetime(result["event_date"], errors="coerce")
            return result

    raise RuntimeError(
        "Full mode requires ACLED credentials (ACLED_API_KEY and ACLED_EMAIL) "
        "or a local ACLED snapshot from motac fixtures."
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
        raw = _fetch_with_trace(start=start, end=end)
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

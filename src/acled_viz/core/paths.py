"""Shared path helpers for project outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def data_root(base: Path | None = None) -> Path:
    root = base or Path("data")
    root.mkdir(parents=True, exist_ok=True)
    return root


def acled_dir(region: str = "gaza", base: Path | None = None) -> Path:
    path = data_root(base=base) / "acled" / region
    path.mkdir(parents=True, exist_ok=True)
    return path


def forecasts_dir(base: Path | None = None) -> Path:
    path = data_root(base=base) / "forecasts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def osm_dir(region: str = "gaza", base: Path | None = None) -> Path:
    path = data_root(base=base) / "osm" / region
    path.mkdir(parents=True, exist_ok=True)
    return path


def gallery_assets_dir() -> Path:
    path = Path("docs") / "_static" / "gallery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def forecast_assets_dir(run_id: str) -> Path:
    path = Path("docs") / "_static" / "forecasts" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_run_id(prefix: str = "run") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{timestamp}"

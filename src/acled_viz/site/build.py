"""High-level site build orchestration."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from acled_viz.core.paths import forecast_assets_dir, forecasts_dir
from acled_viz.data.acled import cache_paths, fetch_gaza_events
from acled_viz.data.demo import demo_actual_counts
from acled_viz.forecasts.eval import evaluate_predictions
from acled_viz.forecasts.ingest_motac import ingest_demo
from acled_viz.forecasts.registry import (
    get_run_predictions_path,
    init_registry,
    list_runs,
    write_metrics,
)
from acled_viz.forecasts.viz import plot_map_compare_h1, plot_perf_timeseries
from acled_viz.site.assets import build_gallery_assets


@dataclass(frozen=True)
class SiteBuildResult:
    docs_index: Path
    run_id: str


def _parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _cache_needs_refresh(
    *,
    mode: str,
    start: date | None,
    end: date | None,
    region: str,
) -> bool:
    cache = cache_paths(region=region)
    if not cache.events_path.exists() or not cache.meta_path.exists():
        return True

    try:
        payload = json.loads(cache.meta_path.read_text(encoding="utf-8"))
    except Exception:
        return True

    cached_mode = payload.get("mode")
    if cached_mode != mode:
        return True

    query = payload.get("query", {})
    cached_start = _parse_iso_date(query.get("start"))
    cached_end = _parse_iso_date(query.get("end"))

    if start is None or end is None:
        if mode == "full":
            default_full_start = date(2023, 9, 4)
            if cached_start is None or cached_start > default_full_start:
                return True
            if cached_end is None or cached_end < date.today():
                return True
        return False

    return cached_start != start or cached_end != end


def ensure_event_cache(
    *,
    mode: str,
    region: str = "gaza",
    start: date | None = None,
    end: date | None = None,
) -> None:
    if not _cache_needs_refresh(mode=mode, start=start, end=end, region=region):
        return

    if start is not None:
        resolved_start = start
    elif mode == "full":
        resolved_start = date(2023, 9, 4)
    else:
        resolved_start = date(2023, 10, 1)
    if end is not None:
        resolved_end = end
    elif mode == "full":
        resolved_end = date.today()
    else:
        resolved_end = date(2023, 11, 30)

    fetch_gaza_events(
        start=resolved_start,
        end=resolved_end,
        mode=mode,
        region=region,
    )


def build_forecast_report(run_id: str) -> Path:
    registry = init_registry(forecasts_dir())
    pred_path = get_run_predictions_path(registry.db_path, run_id)
    preds = pd.read_parquet(pred_path)
    actuals = demo_actual_counts()

    metrics = evaluate_predictions(preds, actuals)
    write_metrics(registry.db_path, metrics)

    out_dir = forecast_assets_dir(run_id)
    metrics_json = out_dir / "metrics.json"
    plot_perf_timeseries(metrics, out_dir / "perf_timeseries.png")
    plot_map_compare_h1(preds, actuals, out_dir / "map_compare_h1.png")
    metrics_json.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "nll_poisson": float(metrics["nll_poisson"].mean()),
                "mae": float(metrics["mae"].mean()),
                "rmse": float(metrics["rmse"].mean()),
                "hotspot_hitrate_k": float(metrics["hotspot_hitrate_k"].mean()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    latest_dir = Path("docs") / "_static" / "forecasts" / "demo_latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    for name in ("perf_timeseries.png", "map_compare_h1.png", "metrics.json"):
        shutil.copy2(out_dir / name, latest_dir / name)
    return out_dir


def build_site(
    mode: str = "demo",
    start: date | None = None,
    end: date | None = None,
    tail_days: int = 30,
) -> SiteBuildResult:
    ensure_event_cache(mode=mode, start=start, end=end)
    build_gallery_assets(tail_days=tail_days)

    registry = init_registry(forecasts_dir())
    runs = list_runs(registry.db_path)
    run_id = ingest_demo(forecasts_dir()) if runs.empty else str(runs.iloc[0]["run_id"])
    build_forecast_report(run_id)

    subprocess.run(["make", "html"], cwd="docs", check=True)
    docs_index = Path("docs") / "_build" / "html" / "index.html"
    return SiteBuildResult(docs_index=docs_index, run_id=run_id)

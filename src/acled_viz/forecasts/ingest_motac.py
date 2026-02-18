"""Ingest motac outputs (demo-first)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from acled_viz.core.paths import make_run_id
from acled_viz.data.demo import demo_forecast_predictions
from acled_viz.forecasts.registry import init_registry, register_run


def ingest_demo(base_dir: Path) -> str:
    paths = init_registry(base_dir)
    run_id = make_run_id(prefix="demo")
    predictions = demo_forecast_predictions(run_id=run_id)
    predictions_path = paths.predictions_dir / f"{run_id}.parquet"
    predictions.to_parquet(predictions_path, index=False)
    register_run(
        paths.db_path,
        run_id=run_id,
        source="motac-demo",
        mode="demo",
        predictions_path=predictions_path,
    )
    return run_id


def ingest_run_dir(base_dir: Path, run_dir: Path) -> str:
    paths = init_registry(base_dir)
    candidates = [
        run_dir / "predictions.parquet",
        run_dir / "predictions.csv",
    ]
    existing = next((path for path in candidates if path.exists()), None)
    if existing is None:
        raise FileNotFoundError("Expected predictions.parquet or predictions.csv in run dir")

    if existing.suffix == ".csv":
        frame = pd.read_csv(existing)
    else:
        frame = pd.read_parquet(existing)

    run_id = str(frame.get("run_id", pd.Series([make_run_id(prefix="motac")])).iloc[0])
    out_path = paths.predictions_dir / f"{run_id}.parquet"
    frame.to_parquet(out_path, index=False)
    register_run(
        paths.db_path,
        run_id=run_id,
        source="motac",
        mode="full",
        predictions_path=out_path,
    )
    return run_id

"""DuckDB-backed forecast registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd


@dataclass(frozen=True)
class RegistryPaths:
    db_path: Path
    predictions_dir: Path


def init_registry(base_dir: Path) -> RegistryPaths:
    base_dir.mkdir(parents=True, exist_ok=True)
    db_path = base_dir / "registry.duckdb"
    predictions_dir = base_dir / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS forecast_runs (
                run_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                predictions_path TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_metrics (
                run_id TEXT NOT NULL,
                issue_date DATE,
                horizon INTEGER,
                nll_poisson DOUBLE,
                mae DOUBLE,
                rmse DOUBLE,
                hotspot_hitrate_k DOUBLE,
                runtime_s DOUBLE,
                PRIMARY KEY (run_id, issue_date, horizon)
            )
            """
        )
    return RegistryPaths(db_path=db_path, predictions_dir=predictions_dir)


def register_run(
    db_path: Path,
    *,
    run_id: str,
    source: str,
    mode: str,
    predictions_path: Path,
) -> None:
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO forecast_runs
            (run_id, source, mode, created_at, predictions_path)
            VALUES (?, ?, ?, now(), ?)
            """,
            [run_id, source, mode, str(predictions_path)],
        )


def list_runs(db_path: Path) -> pd.DataFrame:
    with duckdb.connect(str(db_path), read_only=True) as conn:
        return conn.execute(
            "SELECT run_id, source, mode, created_at, predictions_path "
            "FROM forecast_runs ORDER BY created_at DESC"
        ).fetchdf()


def get_run_predictions_path(db_path: Path, run_id: str) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as conn:
        result = conn.execute(
            "SELECT predictions_path FROM forecast_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
    if result is None:
        raise KeyError(f"Run not found: {run_id}")
    return Path(result[0])


def write_metrics(db_path: Path, metrics: pd.DataFrame) -> None:
    with duckdb.connect(str(db_path)) as conn:
        conn.register("metrics_df", metrics)
        conn.execute(
            """
            INSERT OR REPLACE INTO eval_metrics
            SELECT run_id, issue_date, horizon, nll_poisson, mae, rmse, hotspot_hitrate_k, runtime_s
            FROM metrics_df
            """
        )

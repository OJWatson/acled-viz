"""Forecast schema contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ForecastRun:
    run_id: str
    source: str
    mode: str
    created_at: datetime


@dataclass(frozen=True)
class PredictionRow:
    run_id: str
    issue_date: str
    target_date: str
    horizon: int
    cell_id: int
    pred_mean: float

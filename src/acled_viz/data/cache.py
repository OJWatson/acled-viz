"""Parquet cache IO."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_events(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def read_events(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)

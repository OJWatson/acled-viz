"""Shared event transformation helpers for visualisations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_event_frame(events: pd.DataFrame) -> pd.DataFrame:
    frame = events.copy()
    frame["event_date"] = pd.to_datetime(frame.get("event_date"), errors="coerce")
    frame["latitude"] = pd.to_numeric(frame.get("latitude"), errors="coerce")
    frame["longitude"] = pd.to_numeric(frame.get("longitude"), errors="coerce")
    if "fatalities" in frame.columns:
        fatalities = pd.to_numeric(frame["fatalities"], errors="coerce").fillna(0)
    else:
        fatalities = pd.Series(np.zeros(len(frame)), index=frame.index, dtype=float)
    frame["fatalities"] = fatalities
    frame = frame.dropna(subset=["event_date", "latitude", "longitude"]).copy()
    frame["event_day"] = frame["event_date"].dt.floor("D")

    if "event_id" not in frame.columns:
        frame["event_id"] = [f"ROW-{idx}" for idx in range(len(frame))]
    frame["event_id"] = frame["event_id"].astype(str)
    return frame.sort_values(["event_day", "event_id"]).reset_index(drop=True)


def add_deterministic_jitter(
    frame: pd.DataFrame,
    *,
    scale: float = 0.0032,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> pd.DataFrame:
    """Add deterministic jitter so repeated ACLED coordinates are readable.

    ACLED points often share the exact same lat/lon. This keeps visual density honest
    while avoiding complete overplotting.
    """

    out = frame.copy()
    ids = out["event_id"].astype(str)
    hashes = pd.util.hash_pandas_object(ids, index=False).to_numpy(dtype=np.uint64)

    angle = (hashes % 3600) / 3600.0 * (2.0 * np.pi)
    radius = ((hashes >> 12) % 1000) / 1000.0 * scale

    out["latitude_jitter"] = out[lat_col].to_numpy() + np.cos(angle) * radius
    out["longitude_jitter"] = out[lon_col].to_numpy() + np.sin(angle) * radius
    return out

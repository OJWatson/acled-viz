"""Density map and animation helpers."""

from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from acled_viz.spatial.geometry import gaza_bbox
from acled_viz.viz.styling import apply_style


def _frame_from_figure(fig: plt.Figure) -> np.ndarray:
    fig.canvas.draw()
    buffer = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    width, height = fig.canvas.get_width_height()
    return buffer.reshape((height, width, 4))[..., :3]


def _normalize_events(events: pd.DataFrame) -> pd.DataFrame:
    frame = events.copy()
    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce")
    frame = frame.dropna(subset=["event_date", "latitude", "longitude"])
    return frame.sort_values("event_date").reset_index(drop=True)


def _heat_grid(frame: pd.DataFrame, bins: int = 30) -> np.ndarray:
    hist, _, _ = np.histogram2d(frame["latitude"], frame["longitude"], bins=bins)
    return hist


def _build_horizon_slices(events: pd.DataFrame, by: str) -> list[tuple[str, pd.DataFrame]]:
    if events.empty:
        return []

    event_day = events["event_date"].dt.floor("D")
    first_day = event_day.min()
    last_day = event_day.max()

    if by == "week":
        day_offsets = (event_day - first_day).dt.days
        week_index = (day_offsets // 7).astype(int)
        max_week = int(week_index.max())
        slices: list[tuple[str, pd.DataFrame]] = []
        for week in range(max_week + 1):
            slices.append((f"Week {week + 1}", events[week_index == week]))
        return slices

    days = pd.date_range(first_day, last_day, freq="D")
    slices = []
    for day in days:
        slices.append((day.date().isoformat(), events[event_day == day]))
    return slices


def animate_kde(events: pd.DataFrame, output_path: Path, fps: int = 8, by: str = "week") -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clean = _normalize_events(events)
    lon_min, lon_max, lat_min, lat_max = gaza_bbox()
    frames: list[np.ndarray] = []

    slices = _build_horizon_slices(clean, by=by)
    if not slices:
        fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)
        ax.set_title("Event Density (No Data)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        frames.append(_frame_from_figure(fig))
        plt.close(fig)
    else:
        for label, subset in slices:
            fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
            heat = _heat_grid(subset)
            ax.imshow(
                heat,
                origin="lower",
                extent=(lon_min, lon_max, lat_min, lat_max),
                cmap="inferno",
                aspect="auto",
            )
            ax.set_title(f"Event Density {label}")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            frames.append(_frame_from_figure(fig))
            plt.close(fig)

    imageio.mimsave(output_path, frames, fps=fps)
    return output_path

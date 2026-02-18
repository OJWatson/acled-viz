"""Point map and animation helpers."""

from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from acled_viz.spatial.geometry import gaza_bbox
from acled_viz.viz.styling import PALETTE, apply_style


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


def _build_horizon_labels(events: pd.DataFrame, by: str) -> list[tuple[str, pd.Series]]:
    if events.empty:
        return []

    event_day = events["event_date"].dt.floor("D")
    first_day = event_day.min()
    last_day = event_day.max()

    if by == "week":
        day_offsets = (event_day - first_day).dt.days
        week_index = (day_offsets // 7).astype(int)
        max_week = int(week_index.max())
        labels_masks: list[tuple[str, pd.Series]] = []
        for week in range(max_week + 1):
            labels_masks.append((f"Week {week + 1}", week_index <= week))
        return labels_masks

    days = pd.date_range(first_day, last_day, freq="D")
    labels_masks = []
    for day in days:
        labels_masks.append((day.date().isoformat(), event_day <= day))
    return labels_masks


def animate_points(events: pd.DataFrame, output_path: Path, fps: int = 8, by: str = "day") -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clean = _normalize_events(events)
    lon_min, lon_max, lat_min, lat_max = gaza_bbox()
    frames: list[np.ndarray] = []

    labels_masks = _build_horizon_labels(clean, by=by)
    if not labels_masks:
        fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)
        ax.set_title("Gaza Conflict Events (No Data)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(alpha=0.15)
        frames.append(_frame_from_figure(fig))
        plt.close(fig)
    else:
        for label, mask in labels_masks:
            subset = clean[mask]
            fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
            ax.scatter(
                subset["longitude"],
                subset["latitude"],
                c=PALETTE["accent"],
                s=18,
                alpha=0.65,
                edgecolor="none",
            )
            ax.set_xlim(lon_min, lon_max)
            ax.set_ylim(lat_min, lat_max)
            ax.set_title(f"Gaza Conflict Events Through {label}")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.grid(alpha=0.15)
            frames.append(_frame_from_figure(fig))
            plt.close(fig)

    imageio.mimsave(output_path, frames, fps=fps)
    return output_path

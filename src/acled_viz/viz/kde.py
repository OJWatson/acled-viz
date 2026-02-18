"""Density map and animation helpers."""

from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from acled_viz.spatial.osm import OSMOverlay
from acled_viz.viz.styling import apply_style
from acled_viz.viz.transforms import normalize_event_frame


def _frame_from_figure(fig: plt.Figure) -> np.ndarray:
    fig.canvas.draw()
    buffer = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    width, height = fig.canvas.get_width_height()
    return buffer.reshape((height, width, 4))[..., :3]


def _normalize_events(events: pd.DataFrame) -> pd.DataFrame:
    return normalize_event_frame(events)


def _build_horizon_slices(events: pd.DataFrame, by: str) -> list[tuple[str, pd.DataFrame]]:
    if events.empty:
        return []

    first_day = events["event_day"].min()
    last_day = events["event_day"].max()

    if by == "week":
        day_offsets = (events["event_day"] - first_day).dt.days
        week_index = (day_offsets // 7).astype(int)
        max_week = int(week_index.max())
        slices: list[tuple[str, pd.DataFrame]] = []
        for week in range(max_week + 1):
            slices.append((f"Week {week + 1}", events[week_index == week]))
        return slices

    days = pd.date_range(first_day, last_day, freq="D")
    return [(day.date().isoformat(), events[events["event_day"] == day]) for day in days]


def _build_frame_days(events: pd.DataFrame, by: str) -> pd.DatetimeIndex:
    if events.empty:
        return pd.DatetimeIndex([])

    first_day = events["event_day"].min()
    last_day = events["event_day"].max()

    if by == "week":
        weekly = pd.date_range(first_day, last_day, freq="7D")
        if len(weekly) == 0 or weekly[-1] != last_day:
            weekly = weekly.append(pd.DatetimeIndex([last_day]))
        return weekly

    return pd.date_range(first_day, last_day, freq="D")


def _window_subset(events: pd.DataFrame, frame_day: pd.Timestamp, tail_days: int) -> pd.DataFrame:
    ages = (frame_day - events["event_day"]).dt.days
    return events[(ages >= 0) & (ages < tail_days)].copy()


def _gaussian_kernel1d(sigma: float = 1.1) -> np.ndarray:
    radius = max(1, int(np.ceil(sigma * 3.0)))
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-(x**2) / (2.0 * sigma**2))
    kernel /= kernel.sum()
    return kernel


def _smooth2d(values: np.ndarray, sigma: float = 1.1) -> np.ndarray:
    kernel = _gaussian_kernel1d(sigma=sigma)
    smoothed_x = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 0, values)
    smoothed = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 1, smoothed_x)
    return smoothed


def _density_surface(
    frame: pd.DataFrame,
    *,
    lat_edges: np.ndarray,
    lon_edges: np.ndarray,
    sigma: float = 1.15,
) -> np.ndarray:
    hist, _, _ = np.histogram2d(frame["latitude"], frame["longitude"], bins=[lat_edges, lon_edges])
    smooth = _smooth2d(hist, sigma=sigma)
    return smooth.T


def _draw_osm_overlay(
    *,
    ax: plt.Axes,
    overlay: OSMOverlay | None,
    show_roads: bool,
    show_poi: bool,
) -> None:
    if overlay is None:
        return

    if show_roads:
        for line in overlay.roads:
            if len(line) < 2:
                continue
            lat = [pt[0] for pt in line]
            lon = [pt[1] for pt in line]
            ax.plot(lat, lon, color="#dce4ec", linewidth=0.7, alpha=0.55, zorder=4)

    if show_poi and not overlay.poi.empty:
        ax.scatter(
            overlay.poi["latitude"],
            overlay.poi["longitude"],
            s=10,
            marker="^",
            c="#8ac2ff",
            alpha=0.5,
            linewidths=0,
            zorder=5,
        )


def animate_kde(
    events: pd.DataFrame,
    output_path: Path,
    fps: int = 8,
    by: str = "week",
    tail_days: int = 35,
    overlay: OSMOverlay | None = None,
    show_roads: bool = False,
    show_poi: bool = False,
) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clean = _normalize_events(events)
    frames: list[np.ndarray] = []

    if clean.empty:
        fig, ax = plt.subplots(figsize=(9, 6), dpi=128)
        _draw_osm_overlay(ax=ax, overlay=overlay, show_roads=show_roads, show_poi=show_poi)
        ax.set_title("Gaza Event Density (No Data)")
        ax.set_xlabel("latitude")
        ax.set_ylabel("longitude")
        frames.append(_frame_from_figure(fig))
        plt.close(fig)
        imageio.mimsave(output_path, frames, fps=fps)
        return output_path

    lat_min = float(clean["latitude"].min())
    lat_max = float(clean["latitude"].max())
    lon_min = float(clean["longitude"].min())
    lon_max = float(clean["longitude"].max())
    lat_margin = max((lat_max - lat_min) * 0.06, 0.02)
    lon_margin = max((lon_max - lon_min) * 0.06, 0.02)

    lat_edges = np.linspace(lat_min - lat_margin, lat_max + lat_margin, 95)
    lon_edges = np.linspace(lon_min - lon_margin, lon_max + lon_margin, 95)
    frame_days = _build_frame_days(clean, by=by)

    for frame_day in frame_days:
        subset = _window_subset(clean, frame_day, tail_days=max(1, tail_days))
        fig, ax = plt.subplots(figsize=(9, 6), dpi=128)
        ax.set_facecolor("#f7f3ea")

        if subset.empty:
            surface = np.zeros((len(lon_edges) - 1, len(lat_edges) - 1), dtype=float)
        else:
            surface = _density_surface(subset, lat_edges=lat_edges, lon_edges=lon_edges)

        vmax = max(float(surface.max()), 1e-6)
        ax.imshow(
            surface,
            origin="lower",
            extent=(lat_edges[0], lat_edges[-1], lon_edges[0], lon_edges[-1]),
            cmap="magma",
            aspect="auto",
            vmin=0,
            vmax=vmax,
            alpha=0.92,
            interpolation="bilinear",
        )

        if not subset.empty:
            ax.scatter(
                subset["latitude"],
                subset["longitude"],
                s=8,
                c="#d7e0e8",
                alpha=0.22,
                linewidths=0,
            )

        _draw_osm_overlay(ax=ax, overlay=overlay, show_roads=show_roads, show_poi=show_poi)

        ax.set_xlim(lat_edges[0], lat_edges[-1])
        ax.set_ylim(lon_edges[0], lon_edges[-1])
        ax.set_xlabel("latitude")
        ax.set_ylabel("longitude")
        overlay_label = []
        if show_roads and overlay is not None and overlay.roads:
            overlay_label.append("roads")
        if show_poi and overlay is not None and not overlay.poi.empty:
            overlay_label.append("POI")
        overlay_text = f" | overlays: {', '.join(overlay_label)}" if overlay_label else ""
        ax.set_title(
            f"Gaza event density through {frame_day.date().isoformat()} "
            f"(trailing {tail_days} days){overlay_text}",
            fontsize=12,
            pad=8,
        )
        ax.grid(alpha=0.07)
        ax.text(
            0.012,
            0.985,
            f"events in window: {len(subset):,}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            color="#f7f3ea",
        )

        frames.append(_frame_from_figure(fig))
        plt.close(fig)

    imageio.mimsave(output_path, frames, fps=fps)
    return output_path

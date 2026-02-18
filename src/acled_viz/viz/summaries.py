"""Summary charts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm

from acled_viz.viz.styling import PALETTE, apply_style


def _normalized_event_frame(events: pd.DataFrame) -> pd.DataFrame:
    frame = events.copy()
    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce")
    frame["latitude"] = pd.to_numeric(frame.get("latitude"), errors="coerce")
    frame["longitude"] = pd.to_numeric(frame.get("longitude"), errors="coerce")
    frame["fatalities"] = pd.to_numeric(frame.get("fatalities"), errors="coerce").fillna(0)
    frame = frame.dropna(subset=["event_date", "latitude", "longitude"])
    frame["event_day"] = frame["event_date"].dt.floor("D")
    return frame.sort_values("event_day").reset_index(drop=True)


def _time_breaks_from_unique_days(frame: pd.DataFrame, n_breaks: int = 10) -> pd.DatetimeIndex:
    unique_days = pd.DatetimeIndex(sorted(frame["event_day"].unique()))
    if len(unique_days) == 0:
        return pd.DatetimeIndex([])
    if len(unique_days) == 1:
        return pd.DatetimeIndex([unique_days[0], unique_days[0] + pd.Timedelta(days=1)])

    count = max(2, min(int(n_breaks), len(unique_days)))
    indices = np.linspace(0, len(unique_days) - 1, num=count)
    rounded = np.rint(indices).astype(int)
    selected = pd.DatetimeIndex(unique_days[rounded]).unique().sort_values()

    if selected[-1] < unique_days[-1]:
        selected = selected.append(pd.DatetimeIndex([unique_days[-1]]))

    if len(selected) < 2:
        selected = pd.DatetimeIndex([unique_days[0], unique_days[-1]])
    return selected


def _assign_time_bins(frame: pd.DataFrame, breaks: pd.DatetimeIndex) -> pd.Series:
    return pd.cut(
        frame["event_day"],
        bins=breaks,
        include_lowest=True,
        duplicates="drop",
    )


def plot_timeseries(events: pd.DataFrame, output_path: Path) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame = _normalized_event_frame(events)
    daily = frame.groupby(frame["event_day"].dt.date).size()

    fig, ax = plt.subplots(figsize=(9, 4), dpi=120)
    ax.plot(daily.index, daily.values, color=PALETTE["accent"], linewidth=2.5)
    ax.fill_between(daily.index, daily.values, color=PALETTE["accent"], alpha=0.2)
    ax.set_title("Daily Event Counts")
    ax.set_ylabel("Events")
    ax.set_xlabel("Date")
    ax.grid(alpha=0.2)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_fatalities_facet_grid(
    events: pd.DataFrame,
    output_path: Path,
    *,
    n_breaks: int = 10,
    ncols: int = 3,
) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame = _normalized_event_frame(events)
    if frame.empty:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=140)
        ax.set_title("Fatalities Facet Grid (No Data)")
        ax.set_xlabel("latitude")
        ax.set_ylabel("longitude")
        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        return output_path

    breaks = _time_breaks_from_unique_days(frame, n_breaks=n_breaks)
    frame["date_bin"] = _assign_time_bins(frame, breaks)
    frame = frame.dropna(subset=["date_bin"]).copy()

    categories = list(frame["date_bin"].cat.categories)
    n_panels = len(categories)
    nrows = int(np.ceil(n_panels / ncols))

    fatalities_plot = frame["fatalities"].clip(lower=1)
    vmax = float(fatalities_plot.quantile(0.99))
    if vmax < 1.0:
        vmax = 1.0
    norm = LogNorm(vmin=1.0, vmax=vmax)

    x_margin = (frame["latitude"].max() - frame["latitude"].min()) * 0.05
    y_margin = (frame["longitude"].max() - frame["longitude"].min()) * 0.05
    if x_margin == 0:
        x_margin = 0.02
    if y_margin == 0:
        y_margin = 0.02

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4.7 * ncols, 4.0 * nrows), dpi=140)
    axes_array = np.atleast_1d(axes).ravel()

    scatter_artist = None
    for idx, interval in enumerate(categories):
        ax = axes_array[idx]
        subset = frame[frame["date_bin"] == interval]
        scatter_artist = ax.scatter(
            subset["latitude"],
            subset["longitude"],
            c=subset["fatalities"].clip(lower=1),
            cmap="Blues",
            norm=norm,
            s=18,
            alpha=0.9,
            linewidths=0,
        )
        ax.set_title(interval.right.date().isoformat(), fontsize=10, pad=5)
        ax.set_xlim(frame["latitude"].min() - x_margin, frame["latitude"].max() + x_margin)
        ax.set_ylim(frame["longitude"].min() - y_margin, frame["longitude"].max() + y_margin)
        ax.grid(alpha=0.2)
        ax.set_xlabel("latitude")
        ax.set_ylabel("longitude")

    for idx in range(n_panels, len(axes_array)):
        axes_array[idx].axis("off")

    if scatter_artist is not None:
        cax = fig.add_axes([0.91, 0.18, 0.02, 0.64])
        cbar = fig.colorbar(scatter_artist, cax=cax)
        cbar.set_label("fatalities (log scale)")

    fig.suptitle("Gaza Strip ACLED Events by Time Bin", y=0.995, fontsize=14)
    fig.subplots_adjust(left=0.06, right=0.88, bottom=0.07, top=0.92, wspace=0.25, hspace=0.3)
    fig.savefig(output_path)
    plt.close(fig)
    return output_path

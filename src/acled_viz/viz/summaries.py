"""Summary charts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from acled_viz.viz.styling import PALETTE, apply_style
from acled_viz.viz.transforms import add_deterministic_jitter, normalize_event_frame


def _normalized_event_frame(events: pd.DataFrame) -> pd.DataFrame:
    return normalize_event_frame(events)


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
    return pd.cut(frame["event_day"], bins=breaks, include_lowest=True, duplicates="drop")


def plot_timeseries(events: pd.DataFrame, output_path: Path) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame = _normalized_event_frame(events)
    daily = frame.groupby(frame["event_day"].dt.date).size()
    rolling = daily.rolling(window=14, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=130)
    ax.fill_between(daily.index, daily.values, color="#95a8ba", alpha=0.28, linewidth=0)
    ax.plot(daily.index, daily.values, color="#5b7693", linewidth=1.1, alpha=0.8, label="Daily")
    ax.plot(
        rolling.index,
        rolling.values,
        color=PALETTE["accent"],
        linewidth=2.4,
        label="14-day mean",
    )
    ax.set_title("Gaza ACLED Event Intensity Through Time")
    ax.set_ylabel("Events per day")
    ax.set_xlabel("Date")
    ax.grid(alpha=0.22)
    ax.legend(loc="upper left", frameon=False)
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
    frame = add_deterministic_jitter(frame, scale=0.0034)

    if frame.empty:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
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

    x_margin = max((frame["latitude_jitter"].max() - frame["latitude_jitter"].min()) * 0.05, 0.02)
    y_margin = max((frame["longitude_jitter"].max() - frame["longitude_jitter"].min()) * 0.05, 0.02)

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(4.8 * ncols, 4.2 * nrows),
        dpi=150,
        sharex=True,
        sharey=True,
    )
    axes_array = np.atleast_1d(axes).ravel()

    for idx, interval in enumerate(categories):
        ax = axes_array[idx]
        subset = frame[frame["date_bin"] == interval]
        fatal = subset[subset["fatalities"] > 0]

        ax.set_facecolor("#f7f3ea")
        ax.scatter(
            subset["latitude_jitter"],
            subset["longitude_jitter"],
            c="#8f9aa5",
            s=11,
            alpha=0.25,
            linewidths=0,
        )

        if not fatal.empty:
            size = 12 + np.minimum(42, np.sqrt(fatal["fatalities"].to_numpy(dtype=float)) * 3.8)
            ax.scatter(
                fatal["latitude_jitter"],
                fatal["longitude_jitter"],
                c="#e2573e",
                s=size,
                alpha=0.82,
                linewidths=0.25,
                edgecolors="#fff3e8",
            )

        ax.set_title(interval.right.date().isoformat(), fontsize=10, pad=5)
        ax.set_xlim(
            frame["latitude_jitter"].min() - x_margin,
            frame["latitude_jitter"].max() + x_margin,
        )
        ax.set_ylim(
            frame["longitude_jitter"].min() - y_margin,
            frame["longitude_jitter"].max() + y_margin,
        )
        ax.grid(alpha=0.17)

        if idx % ncols == 0:
            ax.set_ylabel("longitude")
        if idx >= n_panels - ncols:
            ax.set_xlabel("latitude")

        ax.text(
            0.03,
            0.95,
            f"n={len(subset)}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            color="#506073",
        )

    for idx in range(n_panels, len(axes_array)):
        axes_array[idx].axis("off")

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#8f9aa5",
            alpha=0.6,
            markersize=7,
            label="fatalities = 0",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#e2573e",
            alpha=0.9,
            markersize=9,
            label="fatalities > 0 (size scales with count)",
        ),
    ]

    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.97),
    )
    fig.suptitle("Gaza Strip ACLED Events by Time Bin", y=0.995, fontsize=14)
    fig.subplots_adjust(left=0.055, right=0.985, bottom=0.065, top=0.9, wspace=0.14, hspace=0.2)
    fig.savefig(output_path)
    plt.close(fig)
    return output_path

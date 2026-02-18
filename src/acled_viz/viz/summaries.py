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

    if frame.empty:
        fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
        ax.set_title("Gaza ACLED Activity Through Time (No Data)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Events")
        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        return output_path

    daily_index = pd.date_range(frame["event_day"].min(), frame["event_day"].max(), freq="D")
    daily_events = (
        frame.groupby("event_day", observed=True).size().reindex(daily_index, fill_value=0)
    )
    daily_fatalities = (
        frame.groupby("event_day", observed=True)["fatalities"]
        .sum()
        .reindex(daily_index, fill_value=0)
    )

    events_rolling = daily_events.rolling(window=14, min_periods=1).mean()
    fatalities_rolling = daily_fatalities.rolling(window=14, min_periods=1).mean()
    cumulative_fatalities = daily_fatalities.cumsum()

    fig, axes = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(11.2, 6.9),
        dpi=140,
        sharex=True,
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.25, 1.0], "hspace": 0.08},
    )

    ax0, ax1 = axes

    ax0.bar(daily_events.index, daily_events.values, width=1.0, color="#9fb1c2", alpha=0.32)
    ax0.plot(
        events_rolling.index,
        events_rolling.values,
        color="#2f5276",
        linewidth=2.0,
        label="14-day events mean",
    )
    ax0.set_ylabel("events/day")
    ax0.grid(alpha=0.18)
    ax0.legend(loc="upper left", frameon=False)

    ax1.bar(
        daily_fatalities.index,
        daily_fatalities.values,
        width=1.0,
        color="#d47867",
        alpha=0.38,
        label="daily fatalities",
    )
    ax1.plot(
        fatalities_rolling.index,
        fatalities_rolling.values,
        color=PALETTE["accent"],
        linewidth=1.9,
        label="14-day fatalities mean",
    )

    ax1_right = ax1.twinx()
    ax1_right.plot(
        cumulative_fatalities.index,
        cumulative_fatalities.values,
        color="#4d677f",
        linewidth=1.6,
        alpha=0.9,
        label="cumulative fatalities",
    )
    ax1_right.set_ylabel("cumulative fatalities")

    ax1.set_ylabel("fatalities/day")
    ax1.set_xlabel("date")
    ax1.grid(alpha=0.18)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_right.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)

    start = frame["event_day"].min().date().isoformat()
    end = frame["event_day"].max().date().isoformat()
    fig.suptitle("Gaza ACLED Conflict Intensity and Fatalities", y=0.99, fontsize=14)
    fatal_events = int((frame["fatalities"] > 0).sum())
    coverage_text = (
        f"Coverage: {start} to {end} | events={len(frame):,} | "
        f"fatal events={fatal_events:,}"
    )
    fig.text(
        0.012,
        0.01,
        coverage_text,
        ha="left",
        va="bottom",
        fontsize=9,
        color="#465d74",
    )
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
            alpha=0.22,
            linewidths=0,
        )

        if not fatal.empty:
            size = 11 + np.minimum(44, np.sqrt(fatal["fatalities"].to_numpy(dtype=float)) * 3.9)
            ax.scatter(
                fatal["latitude_jitter"],
                fatal["longitude_jitter"],
                c="#e2573e",
                s=size,
                alpha=0.84,
                linewidths=0.24,
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
        ax.grid(alpha=0.15)

        if idx % ncols == 0:
            ax.set_ylabel("longitude")
        if idx >= n_panels - ncols:
            ax.set_xlabel("latitude")

        ax.text(
            0.03,
            0.95,
            f"n={len(subset):,}",
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

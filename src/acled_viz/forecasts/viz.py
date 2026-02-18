"""Forecast report visualisations."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from acled_viz.viz.styling import PALETTE, apply_style


def plot_perf_timeseries(metrics: pd.DataFrame, output_path: Path) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 4), dpi=120)
    ax.plot(metrics["horizon"], metrics["mae"], marker="o", color=PALETTE["accent"], label="MAE")
    ax.plot(metrics["horizon"], metrics["rmse"], marker="s", color=PALETTE["fg"], label="RMSE")
    ax.set_xlabel("Horizon")
    ax.set_ylabel("Error")
    ax.set_title("Forecast Error by Horizon")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_map_compare_h1(
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    output_path: Path,
) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pred_h1 = predictions[predictions["horizon"] == 1].sort_values("cell_id")
    obs_h1 = actuals[actuals["horizon"] == 1].sort_values("cell_id")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=120)
    axes[0].bar(pred_h1["cell_id"], pred_h1["pred_mean"], color=PALETTE["accent"])
    axes[0].set_title("Predicted (H+1)")
    axes[0].set_xlabel("Cell")
    axes[0].set_ylabel("Count")

    axes[1].bar(obs_h1["cell_id"], obs_h1["observed"], color=PALETTE["fg"])
    axes[1].set_title("Observed (H+1)")
    axes[1].set_xlabel("Cell")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path

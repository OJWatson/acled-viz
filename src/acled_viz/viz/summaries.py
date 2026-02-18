"""Summary charts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

from acled_viz.viz.styling import PALETTE, apply_style


def plot_timeseries(events: pd.DataFrame, output_path: Path) -> Path:
    apply_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    daily = events.groupby(events["event_date"].dt.date).size()
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

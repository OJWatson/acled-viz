"""Simple grid indexing helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def grid_counts(frame: pd.DataFrame, bins: int = 12) -> np.ndarray:
    hist, _, _ = np.histogram2d(frame["latitude"], frame["longitude"], bins=bins)
    return hist

from __future__ import annotations

import json
from datetime import date

import pandas as pd

from acled_viz.data.acled import REQUIRED_COLUMNS, fetch_gaza_events


def test_fetch_gaza_events_demo_writes_cache(tmp_path) -> None:
    result = fetch_gaza_events(
        start=date(2023, 10, 1),
        end=date(2023, 10, 14),
        mode="demo",
        out_dir=tmp_path / "acled" / "gaza",
    )

    assert result.events_path.exists()
    assert result.meta_path.exists()

    frame = pd.read_parquet(result.events_path)
    for col in REQUIRED_COLUMNS:
        assert col in frame.columns

    meta = json.loads(result.meta_path.read_text(encoding="utf-8"))
    assert meta["query"]["start"] == "2023-10-01"
    assert meta["query"]["end"] == "2023-10-14"
    assert len(meta["content_hash"]) == 64

from __future__ import annotations

from datetime import date

import pandas as pd

from acled_viz.data.acled import fetch_gaza_events
from acled_viz.data.demo import demo_events
from acled_viz.site.assets import build_gallery_assets
from acled_viz.viz.kde import _build_horizon_slices
from acled_viz.viz.kde import _normalize_events as normalize_kde_events
from acled_viz.viz.points import _build_horizon_labels
from acled_viz.viz.points import _normalize_events as normalize_point_events


def test_build_gallery_demo_outputs_files() -> None:
    fetch_gaza_events(start=date(2023, 10, 1), end=date(2023, 10, 14), mode="demo")
    assets = build_gallery_assets(fps=6, by="week")

    assert assets.hero_points_mp4.exists()
    assert assets.kde_weekly_mp4.exists()
    assert assets.summary_counts_png.exists()

    assert assets.hero_points_mp4.stat().st_size > 1000
    assert assets.kde_weekly_mp4.stat().st_size > 1000
    assert assets.summary_counts_png.stat().st_size > 1000


def test_demo_events_respects_requested_date_range() -> None:
    frame = demo_events(start=date(2023, 10, 1), end=date(2023, 10, 5))
    assert frame["event_date"].min().date().isoformat() == "2023-10-01"
    assert frame["event_date"].max().date().isoformat() == "2023-10-05"


def test_horizon_helpers_include_gap_days() -> None:
    frame = pd.DataFrame(
        {
            "event_date": ["2023-10-01", "2023-10-03"],
            "latitude": [31.4, 31.5],
            "longitude": [34.3, 34.4],
        }
    )
    point_labels = _build_horizon_labels(normalize_point_events(frame), by="day")
    kde_slices = _build_horizon_slices(normalize_kde_events(frame), by="day")

    assert len(point_labels) == 3
    assert len(kde_slices) == 3

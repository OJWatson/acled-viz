from __future__ import annotations

from datetime import date

import pandas as pd

from acled_viz.data.demo import demo_events
from acled_viz.site.assets import build_gallery_assets
from acled_viz.spatial.osm import OSMOverlay
from acled_viz.viz.kde import _build_horizon_slices
from acled_viz.viz.kde import _normalize_events as normalize_kde_events
from acled_viz.viz.points import _build_frame_days, _window_subset
from acled_viz.viz.summaries import _assign_time_bins, _time_breaks_from_unique_days
from acled_viz.viz.summaries import _normalized_event_frame as normalize_summary_events
from acled_viz.viz.transforms import normalize_event_frame as normalize_point_events


def test_build_gallery_demo_outputs_files(tmp_path, monkeypatch) -> None:
    frame = demo_events(start=date(2023, 10, 1), end=date(2023, 10, 14))
    overlay = OSMOverlay(
        roads=[[[31.28, 34.25], [31.55, 34.50]]],
        poi=pd.DataFrame(
            [{"latitude": 31.45, "longitude": 34.39, "name": "Hospital", "category": "hospital"}]
        ),
    )
    monkeypatch.setattr("acled_viz.site.assets.load_cached_events", lambda: frame)
    monkeypatch.setattr("acled_viz.site.assets.gallery_assets_dir", lambda: tmp_path)
    monkeypatch.setattr("acled_viz.site.assets.get_overlay", lambda **kwargs: overlay)
    assets = build_gallery_assets(fps=6, by="week", show_roads=True, show_poi=True)

    assert assets.hero_points_mp4.exists()
    assert assets.kde_weekly_mp4.exists()
    assert assets.summary_counts_png.exists()
    assert assets.fatalities_facets_png.exists()
    assert assets.points_windowed_html.exists()

    assert assets.hero_points_mp4.stat().st_size > 1000
    assert assets.kde_weekly_mp4.stat().st_size > 1000
    assert assets.summary_counts_png.stat().st_size > 1000
    assert assets.fatalities_facets_png.stat().st_size > 1000
    assert assets.points_windowed_html.stat().st_size > 1000
    widget_html = assets.points_windowed_html.read_text(encoding="utf-8")
    assert "roadsToggle" in widget_html
    assert "poiToggle" in widget_html


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
    point_frame = normalize_point_events(frame)
    point_days = _build_frame_days(point_frame, by="day")
    week_days = _build_frame_days(point_frame, by="week")
    kde_slices = _build_horizon_slices(normalize_kde_events(frame), by="day")

    assert len(point_days) == 3
    assert len(week_days) == 2
    assert len(kde_slices) == 3


def test_point_window_subset_respects_tail_days() -> None:
    frame = pd.DataFrame(
        {
            "event_id": ["a", "b", "c"],
            "event_date": ["2023-10-01", "2023-10-03", "2023-10-10"],
            "latitude": [31.3, 31.4, 31.5],
            "longitude": [34.3, 34.4, 34.5],
            "fatalities": [0, 1, 10],
        }
    )
    normalized = normalize_point_events(frame)
    subset = _window_subset(normalized, pd.Timestamp("2023-10-10"), tail_days=5)
    assert set(subset["event_id"]) == {"c"}


def test_facet_time_bins_cover_full_horizon() -> None:
    frame = pd.DataFrame(
        {
            "event_date": ["2023-10-01", "2023-10-03", "2023-10-10"],
            "latitude": [31.3, 31.4, 31.5],
            "longitude": [34.3, 34.4, 34.5],
            "fatalities": [0, 1, 10],
        }
    )
    normalized = normalize_summary_events(frame)
    breaks = _time_breaks_from_unique_days(normalized, n_breaks=4)
    bins = _assign_time_bins(normalized, breaks)
    assert bins.notna().all()
    assert breaks[0].date().isoformat() == "2023-10-01"
    assert breaks[-1].date().isoformat() == "2023-10-10"

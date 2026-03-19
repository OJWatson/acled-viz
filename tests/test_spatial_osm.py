from __future__ import annotations

import pandas as pd

from acled_viz.spatial import osm
from acled_viz.spatial.osm import OSMOverlay


def test_osm_cache_roundtrip(tmp_path) -> None:
    paths = osm.cache_paths(base=tmp_path)
    overlay = OSMOverlay(
        roads=[[[31.28, 34.25], [31.30, 34.27]], [[31.40, 34.35], [31.44, 34.39]]],
        poi=pd.DataFrame(
            [
                {
                    "latitude": 31.41,
                    "longitude": 34.38,
                    "name": "Clinic",
                    "category": "healthcare",
                }
            ]
        ),
    )

    osm.write_overlay_cache(paths, overlay)
    loaded = osm.load_overlay_cache(paths)

    assert len(loaded.roads) == 2
    assert len(loaded.poi) == 1
    assert loaded.poi.iloc[0]["name"] == "Clinic"


def test_get_overlay_uses_cached_when_osmnx_unavailable(tmp_path, monkeypatch) -> None:
    paths = osm.cache_paths(base=tmp_path)
    cached = OSMOverlay(
        roads=[[[31.28, 34.25], [31.30, 34.27]]],
        poi=pd.DataFrame(
            [{"latitude": 31.35, "longitude": 34.31, "name": "School", "category": "amenity"}]
        ),
    )
    osm.write_overlay_cache(paths, cached)

    monkeypatch.setattr("acled_viz.spatial.osm.has_osmnx", lambda: False)

    loaded = osm.get_overlay(
        include_roads=True,
        include_poi=True,
        refresh=True,
        base=tmp_path,
    )

    assert len(loaded.roads) == 1
    assert len(loaded.poi) == 1


def test_get_overlay_fetch_failure_returns_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("acled_viz.spatial.osm.has_osmnx", lambda: True)

    def _explode(**kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("acled_viz.spatial.osm._fetch_overlay_osmnx", _explode)

    loaded = osm.get_overlay(
        include_roads=True,
        include_poi=True,
        refresh=True,
        base=tmp_path,
    )

    assert loaded.roads == []
    assert loaded.poi.empty


def test_clip_line_to_bbox_keeps_disjoint_segments_separate() -> None:
    line = [
        [31.25, 34.25],
        [31.30, 34.30],
        [31.95, 34.95],
        [31.31, 34.31],
        [31.35, 34.35],
    ]

    clipped = osm._clip_line_to_bbox(
        line,
        lat_min=31.2,
        lat_max=31.6,
        lon_min=34.2,
        lon_max=34.6,
    )

    assert clipped == [
        [[31.25, 34.25], [31.30, 34.30]],
        [[31.31, 34.31], [31.35, 34.35]],
    ]

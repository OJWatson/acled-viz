"""Build website visual assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from acled_viz.core.paths import gallery_assets_dir
from acled_viz.data.acled import load_cached_events
from acled_viz.spatial.osm import get_overlay
from acled_viz.viz.kde import animate_kde
from acled_viz.viz.points import animate_points, build_points_tail_widget
from acled_viz.viz.summaries import plot_fatalities_facet_grid, plot_timeseries


@dataclass(frozen=True)
class GalleryAssets:
    hero_points_mp4: Path
    kde_weekly_mp4: Path
    summary_counts_png: Path
    fatalities_facets_png: Path
    points_windowed_html: Path


def build_gallery_assets(
    *,
    fps: int = 8,
    by: str = "week",
    tail_days: int = 30,
    show_roads: bool = False,
    show_poi: bool = False,
    osm_refresh: bool = False,
) -> GalleryAssets:
    events = load_cached_events()
    out = gallery_assets_dir()
    overlay = get_overlay(
        include_roads=show_roads,
        include_poi=show_poi,
        refresh=osm_refresh,
    )

    hero = animate_points(
        events,
        out / "hero_points.mp4",
        fps=fps,
        by=by,
        tail_days=tail_days,
        overlay=overlay,
        show_roads=show_roads,
        show_poi=show_poi,
    )
    kde = animate_kde(
        events,
        out / "kde_weekly.mp4",
        fps=fps,
        by=by,
        tail_days=tail_days,
        overlay=overlay,
        show_roads=show_roads,
        show_poi=show_poi,
    )
    summary = plot_timeseries(events, out / "summary_counts.png")
    facets = plot_fatalities_facet_grid(events, out / "fatalities_facets.png")
    widget = build_points_tail_widget(
        events,
        out / "points_windowed.html",
        by="day",
        default_tail_days=tail_days,
        overlay=overlay,
        show_roads=show_roads,
        show_poi=show_poi,
    )

    return GalleryAssets(
        hero_points_mp4=hero,
        kde_weekly_mp4=kde,
        summary_counts_png=summary,
        fatalities_facets_png=facets,
        points_windowed_html=widget,
    )

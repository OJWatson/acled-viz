"""Build website visual assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from acled_viz.core.paths import gallery_assets_dir
from acled_viz.data.acled import load_cached_events
from acled_viz.viz.kde import animate_kde
from acled_viz.viz.points import animate_points
from acled_viz.viz.summaries import plot_timeseries


@dataclass(frozen=True)
class GalleryAssets:
    hero_points_mp4: Path
    kde_weekly_mp4: Path
    summary_counts_png: Path


def build_gallery_assets(*, fps: int = 8, by: str = "week") -> GalleryAssets:
    events = load_cached_events()
    out = gallery_assets_dir()

    hero = animate_points(events, out / "hero_points.mp4", fps=fps, by="day")
    kde = animate_kde(events, out / "kde_weekly.mp4", fps=fps, by=by)
    summary = plot_timeseries(events, out / "summary_counts.png")

    return GalleryAssets(hero_points_mp4=hero, kde_weekly_mp4=kde, summary_counts_png=summary)

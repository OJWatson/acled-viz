"""Geometry helpers used by visual modules."""

from __future__ import annotations

from acled_viz.data.region import gaza_region


def gaza_bbox() -> tuple[float, float, float, float]:
    region = gaza_region()
    return (region.lon_min, region.lon_max, region.lat_min, region.lat_max)

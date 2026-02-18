"""Project configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RegionConfig:
    name: str = "gaza"
    lon_min: float = 34.2
    lon_max: float = 34.7
    lat_min: float = 31.2
    lat_max: float = 31.7


@dataclass(frozen=True)
class FetchConfig:
    start: date
    end: date
    mode: str = "demo"

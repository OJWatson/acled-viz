"""OSM roads/POI extraction with cache-backed fallback."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from acled_viz.core.paths import osm_dir
from acled_viz.data.region import gaza_region


@dataclass(frozen=True)
class OSMCachePaths:
    roads_path: Path
    poi_path: Path
    meta_path: Path


@dataclass(frozen=True)
class OSMOverlay:
    roads: list[list[list[float]]]
    poi: pd.DataFrame


_IGNORED_HIGHWAY = {
    "bridleway",
    "bus_guideway",
    "construction",
    "corridor",
    "cycleway",
    "elevator",
    "escalator",
    "footway",
    "path",
    "pedestrian",
    "platform",
    "planned",
    "proposed",
    "raceway",
    "service_area",
    "steps",
    "track",
}


def has_osmnx() -> bool:
    try:
        import osmnx  # noqa: F401

        return True
    except Exception:
        return False


def cache_paths(region: str = "gaza", base: Path | None = None) -> OSMCachePaths:
    root = osm_dir(region=region, base=base)
    return OSMCachePaths(
        roads_path=root / "roads.json",
        poi_path=root / "poi.json",
        meta_path=root / "meta.json",
    )


def _empty_overlay() -> OSMOverlay:
    return OSMOverlay(
        roads=[],
        poi=pd.DataFrame(columns=["latitude", "longitude", "name", "category"]),
    )


def _region_bbox(
    region: str = "gaza",
    bounds: tuple[float, float, float, float] | None = None,
) -> tuple[float, float, float, float]:
    if bounds is not None:
        return bounds
    if region != "gaza":
        raise ValueError(f"Unsupported region for OSM overlay: {region}")
    cfg = gaza_region()
    return (cfg.lat_min, cfg.lat_max, cfg.lon_min, cfg.lon_max)


def _clip_line_to_bbox(
    line: list[list[float]],
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> list[list[float]]:
    clipped = [
        [lat, lon]
        for lat, lon in line
        if (lat_min <= lat <= lat_max) and (lon_min <= lon <= lon_max)
    ]
    return clipped


def _geometry_points(geom: Any) -> list[tuple[float, float]]:
    if geom is None:
        return []

    geom_type = getattr(geom, "geom_type", "")

    if geom_type in {"LineString", "LinearRing"} and hasattr(geom, "coords"):
        return [(float(y), float(x)) for x, y in geom.coords]

    if geom_type.startswith("Multi") and hasattr(geom, "geoms"):
        points: list[tuple[float, float]] = []
        for sub in geom.geoms:
            points.extend(_geometry_points(sub))
        return points

    if geom_type in {"Polygon", "MultiPolygon"} and hasattr(geom, "centroid"):
        centroid = geom.centroid
        return [(float(centroid.y), float(centroid.x))]

    if geom_type == "Point" and hasattr(geom, "x") and hasattr(geom, "y"):
        return [(float(geom.y), float(geom.x))]

    return []


def _geometry_lines(geom: Any) -> list[list[tuple[float, float]]]:
    if geom is None:
        return []

    geom_type = getattr(geom, "geom_type", "")

    if geom_type in {"LineString", "LinearRing"} and hasattr(geom, "coords"):
        return [[(float(y), float(x)) for x, y in geom.coords]]

    if geom_type == "MultiLineString" and hasattr(geom, "geoms"):
        lines: list[list[tuple[float, float]]] = []
        for sub in geom.geoms:
            if hasattr(sub, "coords"):
                points = [(float(y), float(x)) for x, y in sub.coords]
                if len(points) >= 2:
                    lines.append(points)
        return lines

    if geom_type.startswith("Multi") and hasattr(geom, "geoms"):
        lines: list[list[tuple[float, float]]] = []
        for sub in geom.geoms:
            lines.extend(_geometry_lines(sub))
        return lines

    return []


def _resample_line(line: list[list[float]], max_points: int = 40) -> list[list[float]]:
    if len(line) <= max_points:
        return line
    indices = np.linspace(0, len(line) - 1, num=max_points).round().astype(int)
    out = [line[idx] for idx in indices]
    return out


def _line_length(line: list[list[float]]) -> float:
    if len(line) < 2:
        return 0.0
    total = 0.0
    for idx in range(1, len(line)):
        lat0, lon0 = line[idx - 1]
        lat1, lon1 = line[idx]
        total += float(np.hypot(lat1 - lat0, lon1 - lon0))
    return total


def _downsample_roads(
    roads: list[list[list[float]]],
    *,
    max_lines: int = 3200,
    keep_major: int = 1200,
    grid_size: int = 24,
) -> list[list[list[float]]]:
    if len(roads) <= max_lines:
        return roads

    lengths = np.array([_line_length(line) for line in roads], dtype=float)
    order = np.argsort(-lengths)

    major_count = min(keep_major, max_lines, len(order))
    selected_idx = list(order[:major_count].astype(int))
    selected = set(selected_idx)

    lat_mid = np.array([line[len(line) // 2][0] for line in roads], dtype=float)
    lon_mid = np.array([line[len(line) // 2][1] for line in roads], dtype=float)
    lat_min = float(lat_mid.min())
    lon_min = float(lon_mid.min())
    lat_span = max(float(lat_mid.max() - lat_min), 1e-9)
    lon_span = max(float(lon_mid.max() - lon_min), 1e-9)

    spatial_target = min(max_lines - len(selected_idx), 900)
    covered_cells: set[tuple[int, int]] = set()
    for idx in order[major_count:]:
        idx_i = int(idx)
        if idx_i in selected:
            continue
        row = int(((lat_mid[idx_i] - lat_min) / lat_span) * (grid_size - 1))
        col = int(((lon_mid[idx_i] - lon_min) / lon_span) * (grid_size - 1))
        cell = (row, col)
        if cell in covered_cells:
            continue
        covered_cells.add(cell)
        selected.add(idx_i)
        selected_idx.append(idx_i)
        if len(selected_idx) >= major_count + spatial_target:
            break

    remaining = np.array([int(idx) for idx in order if int(idx) not in selected], dtype=int)
    extra_count = max(0, min(max_lines - len(selected_idx), len(remaining)))
    if extra_count > 0:
        rng = np.random.default_rng(20260218)
        selected_idx.extend(rng.choice(remaining, size=extra_count, replace=False).astype(int))

    keep_sorted = np.sort(np.array(selected_idx, dtype=int))
    return [roads[int(idx)] for idx in keep_sorted]


def _highway_allowed(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set)):
        tags = [str(v).strip().lower() for v in value if str(v).strip()]
    else:
        raw = str(value).strip().lower()
        tags = [part.strip() for part in raw.split(";") if part.strip()]

    if not tags:
        return False
    return any(tag not in _IGNORED_HIGHWAY for tag in tags)


def _fetch_roads_features_osmnx(
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> list[list[list[float]]]:
    import osmnx as ox  # type: ignore

    old_max_area = ox.settings.max_query_area_size
    old_timeout = ox.settings.requests_timeout
    ox.settings.max_query_area_size = max(float(old_max_area), 2_000_000_000.0)
    ox.settings.requests_timeout = max(int(old_timeout), 180)
    bbox = (lon_min, lat_min, lon_max, lat_max)
    tags = {"highway": True}
    try:
        try:
            features = ox.features_from_bbox(
                north=lat_max,
                south=lat_min,
                east=lon_max,
                west=lon_min,
                tags=tags,
            )
        except Exception:
            try:
                features = ox.features_from_bbox(bbox, tags=tags)
            except Exception:
                features = ox.geometries_from_bbox(
                    lat_max,
                    lat_min,
                    lon_max,
                    lon_min,
                    tags=tags,
                )

        if features.empty:
            return []
        roads: list[list[list[float]]] = []
        for record in features.reset_index(drop=True).to_dict(orient="records"):
            if not _highway_allowed(record.get("highway")):
                continue
            for points in _geometry_lines(record.get("geometry")):
                line = [[lat, lon] for lat, lon in points]
                line = _clip_line_to_bbox(
                    line,
                    lat_min=lat_min,
                    lat_max=lat_max,
                    lon_min=lon_min,
                    lon_max=lon_max,
                )
                if len(line) < 2:
                    continue
                roads.append(_resample_line(line, max_points=48))

        return _downsample_roads(roads)
    finally:
        ox.settings.max_query_area_size = old_max_area
        ox.settings.requests_timeout = old_timeout


def _fetch_roads_graph_osmnx(
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> list[list[list[float]]]:
    import osmnx as ox  # type: ignore

    old_max_area = ox.settings.max_query_area_size
    old_timeout = ox.settings.requests_timeout
    ox.settings.max_query_area_size = max(float(old_max_area), 2_000_000_000.0)
    ox.settings.requests_timeout = max(int(old_timeout), 180)
    bbox = (lon_min, lat_min, lon_max, lat_max)

    try:
        try:
            graph = ox.graph_from_bbox(
                north=lat_max,
                south=lat_min,
                east=lon_max,
                west=lon_min,
                network_type="all_public",
                simplify=True,
            )
        except TypeError:
            try:
                graph = ox.graph_from_bbox(bbox, network_type="all_public", simplify=True)
            except TypeError:
                graph = ox.graph_from_bbox(bbox, network_type="all_public")

        edges = ox.graph_to_gdfs(graph, nodes=False, edges=True, fill_edge_geometry=True)

        roads: list[list[list[float]]] = []
        for geom in edges.get("geometry", []):
            for points in _geometry_lines(geom):
                line = [[lat, lon] for lat, lon in points]
                line = _clip_line_to_bbox(
                    line,
                    lat_min=lat_min,
                    lat_max=lat_max,
                    lon_min=lon_min,
                    lon_max=lon_max,
                )
                if len(line) < 2:
                    continue
                roads.append(_resample_line(line, max_points=36))

        return _downsample_roads(roads)
    finally:
        ox.settings.max_query_area_size = old_max_area
        ox.settings.requests_timeout = old_timeout


def _fetch_roads_osmnx(
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> list[list[list[float]]]:
    try:
        roads = _fetch_roads_features_osmnx(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
        )
        if roads:
            return roads
    except Exception:
        pass

    return _fetch_roads_graph_osmnx(
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
    )


def _fetch_poi_osmnx(
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> pd.DataFrame:
    import osmnx as ox  # type: ignore

    old_max_area = ox.settings.max_query_area_size
    old_timeout = ox.settings.requests_timeout
    ox.settings.max_query_area_size = max(float(old_max_area), 2_000_000_000.0)
    ox.settings.requests_timeout = max(int(old_timeout), 180)
    bbox = (lon_min, lat_min, lon_max, lat_max)

    tags = {
        "amenity": True,
        "healthcare": True,
        "shop": True,
        "tourism": True,
        "public_transport": True,
    }

    try:
        try:
            features = ox.features_from_bbox(
                north=lat_max,
                south=lat_min,
                east=lon_max,
                west=lon_min,
                tags=tags,
            )
        except Exception:
            try:
                features = ox.features_from_bbox(bbox, tags=tags)
            except Exception:
                try:
                    features = ox.geometries_from_bbox(
                        lat_max,
                        lat_min,
                        lon_max,
                        lon_min,
                        tags=tags,
                    )
                except Exception:
                    return pd.DataFrame(columns=["latitude", "longitude", "name", "category"])

        rows: list[dict[str, Any]] = []
        for record in features.reset_index(drop=True).to_dict(orient="records"):
            points = _geometry_points(record.get("geometry"))
            if not points:
                continue
            lat, lon = points[0]
            if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                continue

            category = None
            for key in ("amenity", "healthcare", "shop", "tourism", "public_transport"):
                value = record.get(key)
                if value is not None and str(value).strip() and str(value).lower() != "nan":
                    category = str(value)
                    break

            name = record.get("name")
            if name is None or not str(name).strip() or str(name).lower() == "nan":
                name = category or "POI"

            rows.append(
                {
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "name": str(name),
                    "category": str(category or "unknown"),
                }
            )

        if not rows:
            return pd.DataFrame(columns=["latitude", "longitude", "name", "category"])

        poi = pd.DataFrame.from_records(rows)
        poi["lat_round"] = poi["latitude"].round(5)
        poi["lon_round"] = poi["longitude"].round(5)
        poi = poi.drop_duplicates(subset=["lat_round", "lon_round", "name"]).drop(
            columns=["lat_round", "lon_round"]
        )
        if len(poi) > 500:
            poi = poi.head(500)
        return poi.reset_index(drop=True)
    finally:
        ox.settings.max_query_area_size = old_max_area
        ox.settings.requests_timeout = old_timeout


def _fetch_overlay_osmnx(
    *,
    region: str,
    include_roads: bool,
    include_poi: bool,
    bounds: tuple[float, float, float, float] | None = None,
) -> OSMOverlay:
    lat_min, lat_max, lon_min, lon_max = _region_bbox(region, bounds=bounds)

    roads: list[list[list[float]]] = []
    poi = pd.DataFrame(columns=["latitude", "longitude", "name", "category"])

    if include_roads:
        roads = _fetch_roads_osmnx(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
        )

    if include_poi:
        poi = _fetch_poi_osmnx(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
        )

    return OSMOverlay(roads=roads, poi=poi)


def write_overlay_cache(
    paths: OSMCachePaths,
    overlay: OSMOverlay,
    *,
    source: str = "osmnx",
) -> None:
    paths.roads_path.parent.mkdir(parents=True, exist_ok=True)

    paths.roads_path.write_text(
        json.dumps({"roads": overlay.roads}, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    poi_payload = overlay.poi[["latitude", "longitude", "name", "category"]].to_dict(
        orient="records"
    )
    paths.poi_path.write_text(
        json.dumps({"poi": poi_payload}, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    meta = {
        "source": source,
        "roads_count": len(overlay.roads),
        "poi_count": int(len(overlay.poi)),
    }
    paths.meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_overlay_cache(paths: OSMCachePaths) -> OSMOverlay:
    roads: list[list[list[float]]] = []
    poi = pd.DataFrame(columns=["latitude", "longitude", "name", "category"])

    if paths.roads_path.exists():
        payload = json.loads(paths.roads_path.read_text(encoding="utf-8"))
        cached_roads = payload.get("roads", [])
        if isinstance(cached_roads, list):
            roads = cached_roads

    if paths.poi_path.exists():
        payload = json.loads(paths.poi_path.read_text(encoding="utf-8"))
        cached_poi = payload.get("poi", [])
        if isinstance(cached_poi, list):
            poi = pd.DataFrame.from_records(cached_poi)

    if poi.empty:
        poi = pd.DataFrame(columns=["latitude", "longitude", "name", "category"])
    else:
        for col in ("latitude", "longitude"):
            poi[col] = pd.to_numeric(poi[col], errors="coerce")
        for col in ("name", "category"):
            if col not in poi.columns:
                poi[col] = ""
        poi = poi.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

    return OSMOverlay(roads=roads, poi=poi)


def get_overlay(
    *,
    region: str = "gaza",
    include_roads: bool = False,
    include_poi: bool = False,
    refresh: bool = False,
    base: Path | None = None,
    bounds: tuple[float, float, float, float] | None = None,
) -> OSMOverlay:
    if not include_roads and not include_poi:
        return _empty_overlay()

    paths = cache_paths(region=region, base=base)

    if not refresh and (paths.roads_path.exists() or paths.poi_path.exists()):
        cached = load_overlay_cache(paths)
        roads_ok = (not include_roads) or bool(cached.roads)
        poi_ok = (not include_poi) or (not cached.poi.empty)
        if roads_ok and poi_ok:
            return OSMOverlay(
                roads=cached.roads if include_roads else [],
                poi=cached.poi if include_poi else _empty_overlay().poi,
            )

    if not has_osmnx():
        warnings.warn(
            "OSM overlay requested but osmnx is unavailable; falling back to cache/empty overlay.",
            RuntimeWarning,
            stacklevel=2,
        )
        cached = load_overlay_cache(paths)
        return OSMOverlay(
            roads=cached.roads if include_roads else [],
            poi=cached.poi if include_poi else _empty_overlay().poi,
        )

    try:
        fetched = _fetch_overlay_osmnx(
            region=region,
            include_roads=include_roads,
            include_poi=include_poi,
            bounds=bounds,
        )
        write_overlay_cache(paths, fetched, source="osmnx")
        return fetched
    except Exception as exc:
        warnings.warn(
            f"OSM fetch failed ({exc}); falling back to cache/empty overlay.",
            RuntimeWarning,
            stacklevel=2,
        )
        cached = load_overlay_cache(paths)
        return OSMOverlay(
            roads=cached.roads if include_roads else [],
            poi=cached.poi if include_poi else _empty_overlay().poi,
        )

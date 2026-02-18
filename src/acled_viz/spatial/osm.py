"""Optional OSM integration placeholder."""

from __future__ import annotations


def has_osmnx() -> bool:
    try:
        import osmnx  # noqa: F401

        return True
    except Exception:
        return False

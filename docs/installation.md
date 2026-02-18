# Installation

## Install

```bash
uv sync --extra dev --extra docs
uv sync --extra dev --extra docs --extra osm
```

For full-mode integrations, install the `trace` and `motac` packages from the `ojwatson` GitHub repos in your environment.
If ACLED credentials are not set, full mode can fall back to a local ACLED snapshot from the `motac` fixture path when present.
OSM overlays require `osmnx` and network access on first fetch, then reuse local cache files in `data/osm/`.

For GitHub Pages in this repo, gallery assets are expected to be generated and committed first; CI then builds Sphinx HTML without regenerating demo visuals.

## Local gates

```bash
./scripts/ci.sh
./scripts/test.sh
```

## CLI examples

```bash
acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo
acled-viz viz build-gallery --mode demo --tail-days 30
acled-viz viz build-gallery --mode full --start 2023-09-04 --end 2026-02-18 --by week --tail-days 45
acled-viz viz build-gallery --mode full --show-roads --show-poi --tail-days 45
acled-viz site build --mode full --start 2023-09-04 --end 2026-02-18 --tail-days 45
acled-viz site build --mode full --show-roads --show-poi --tail-days 45
acled-viz forecasts init-db
acled-viz forecasts ingest-motac --mode demo
acled-viz forecasts list-runs
acled-viz forecasts build-report --run-id <id>
```

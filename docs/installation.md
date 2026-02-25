# Installation

## Install the package

```bash
uv sync --extra dev --extra docs
uv sync --extra dev --extra docs --extra osm
```

## ACLED credentials for full mode

The package includes a lightweight built-in ACLED OAuth wrapper.

Provide credentials via either:

- `ACLED_EMAIL` + `ACLED_PASSWORD` environment variables, or
- `ACLED_CREDENTIALS_FILE` pointing to a local credential file, or
- `~/.config/acled/oauth_credentials.json`

If credentials are unavailable, full mode can fall back to a local ACLED snapshot
(for example, `acled_example.csv` in repo root).

OSM overlays require `osmnx` and network access on first fetch, then reuse local cache files in `data/osm/`.

## Local tests and checks

```bash
uv run --extra dev ruff check .
uv run --extra dev pytest -q
```

Equivalent helper scripts:

```bash
./scripts/ci.sh
./scripts/test.sh
```

## GitHub Pages build flow

This repository expects gallery assets to be generated and committed first. The docs workflow then
builds Sphinx HTML for GitHub Pages without regenerating visualization artifacts during CI.

Local example:

```bash
uv run acled-viz site build --mode demo
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

# acled-viz

`acled-viz` is a Gaza conflict visualisation + forecast tracking package.

Internal source package is `acled_viz`.

## What works now

- ACLED cache pipeline with canonical `events.parquet` + `meta.json`
- Gallery asset generation (`hero_points.mp4`, `kde_weekly.mp4`, `summary_counts.png`, `fatalities_facets.png`, `points_windowed.html`)
- Forecast registry in DuckDB with demo `motac` ingestion
- Forecast evaluation and report assets (`metrics.json`, `perf_timeseries.png`, `map_compare_h1.png`)
- End-to-end site build for GitHub Pages via Sphinx

## Quickstart

```bash
uv sync --extra dev --extra docs
uv run acled-viz site build --mode full --start 2023-09-04 --end 2026-02-18 --tail-days 45
```

After build, open `docs/_build/html/index.html`.

## CLI surface

```bash
acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo
acled-viz viz build-gallery --mode demo --tail-days 30
acled-viz viz build-gallery --mode full --by week --tail-days 45
acled-viz viz build-gallery --mode full --show-roads --show-poi --tail-days 45
acled-viz forecasts init-db
acled-viz forecasts ingest-motac --mode demo
acled-viz forecasts list-runs
acled-viz forecasts build-report --run-id <id>
acled-viz site build --mode full --start 2023-09-04 --end 2026-02-18 --tail-days 45
```

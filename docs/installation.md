# Installation

## Install

```bash
uv sync --extra dev --extra docs
```

For full-mode integrations, install the `trace` and `motac` packages from the `ojwatson` GitHub repos in your environment.

## Local gates

```bash
./scripts/ci.sh
./scripts/test.sh
```

## CLI examples

```bash
acled-viz data fetch-acled --region gaza --start 2023-10-01 --end 2023-10-14 --mode demo
acled-viz viz build-gallery --mode demo
acled-viz forecasts init-db
acled-viz forecasts ingest-motac --mode demo
acled-viz forecasts list-runs
acled-viz forecasts build-report --run-id <id>
acled-viz site build --mode demo
```

# Forecast Ingestion and Evaluation Quickstart

```bash
acled-viz forecasts init-db
acled-viz forecasts ingest-motac --mode demo
acled-viz forecasts list-runs
acled-viz forecasts build-report --run-id <run_id>
```

Then run `acled-viz site build --mode demo` to regenerate docs with current assets.

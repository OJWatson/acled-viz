from __future__ import annotations

import json

from acled_viz.core.paths import forecasts_dir
from acled_viz.forecasts.ingest_motac import ingest_demo
from acled_viz.forecasts.registry import init_registry, list_runs
from acled_viz.site.build import build_forecast_report


def test_forecast_registry_and_report_outputs() -> None:
    registry = init_registry(forecasts_dir())
    assert registry.db_path.exists()

    run_id = ingest_demo(forecasts_dir())
    runs = list_runs(registry.db_path)
    assert run_id in set(runs["run_id"])

    out = build_forecast_report(run_id)
    perf = out / "perf_timeseries.png"
    compare = out / "map_compare_h1.png"
    metrics_path = out / "metrics.json"

    assert perf.exists()
    assert compare.exists()
    assert metrics_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    for key in ["nll_poisson", "mae", "rmse", "hotspot_hitrate_k"]:
        assert key in metrics
